# server/prod/pipeline/pipeline.py
from __future__ import annotations

import datetime
import time
import random
from typing import Any, List
from zoneinfo import ZoneInfo

from openai import OpenAI

from ..config import settings
from ..services.db import Database
from ..services.logo_service import LogoService
from ..services.ai_analysis import AnalyzeIPO
from ..services.daily_cache import DailyCache  # Redis daily cache
from ..efts.fetcher import EFTSFetcher
from ..edgar.daily_index import DailyIndexChecker
from ..services.kv_sync_service import KVSyncService

# Only analyze these amendment forms with GPT
FORMS_TO_ANALYZE = {"S-1/A", "F-1/A"}

ET = ZoneInfo("America/Toronto")


def _retry(callable_fn, *, retries: int = 3, base_delay: float = 0.5, max_delay: float = 8.0):
    """
    Minimal retry helper with exponential backoff + jitter (no external deps).
    - callable_fn: zero-arg function to execute (wrap your call in a lambda).
    - retries: total attempts (including first).
    Raises the last exception if all attempts fail.
    """
    attempt = 1
    delay = base_delay
    while True:
        try:
            return callable_fn()
        except Exception as e:
            if attempt >= retries:
                raise
            sleep_for = min(max_delay, delay * random.uniform(0.5, 1.5))
            print(f"[RETRY] Attempt {attempt} failed: {e}. Retrying in {sleep_for:.2f}s...")
            time.sleep(sleep_for)
            delay = min(max_delay, delay * 2)
            attempt += 1


def _is_acquisition_corp(name: str | None) -> bool:
    return bool(name) and ("acquisition" in name.lower())


def _cap_ok(market_cap: Any, threshold: float = 50_000_000.0) -> bool:
    """
    Returns True if market_cap is present and >= threshold.
    Safely parses strings/decimals; None/0/parse errors -> False.
    """
    if market_cap is None:
        return False
    try:
        return float(market_cap) >= threshold
    except Exception:
        return False


class Pipeline:
    def __init__(self) -> None:
        self.db = Database()
        self.logo = LogoService(self.db)
        self.fetcher = EFTSFetcher()
        self.daily = DailyIndexChecker()
        self.cache = DailyCache()

        # --- AI clients (minimal integration) ---
        self.openai = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.ai = AnalyzeIPO(self.db.client, self.openai)

        # --- KV sync for public data API ---
        self.kv = KVSyncService(self.db.client)

    @staticmethod
    def build_sec_html_url(cik: str, accession_number: str, primary_document: str) -> str:
        """Build a SEC Archives HTML URL from cik, accession_number, and primary_document."""
        cik_nozero = str(int(cik))  # remove leading zeros / normalize
        acc_nodash = accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik_nozero}/{acc_nodash}/{primary_document}"

    # ----- shared processing for both EFTS and daily-index -----
    def _process_filings(self, filings: List[dict[str, Any]]) -> None:
        if not filings:
            print("[INFO] No filings to process.")
            return

        # Snapshot of current IPO table state (keyed by normalized str(CIK))
        active = self.db.get_ipo_snapshot()

        for f in filings:
            cik_raw = f.get("cik")
            form = f.get("form_type")
            date = f.get("date_filed")
            acc = f.get("accession_number")
            name = f.get("company_name")
            ticker = f.get("ticker")
            mainlink = f.get("mainlink")
            is_ipo_flag = f.get("is_ipo")
            market_cap = f.get("market_cap")  # <— used for logo gating

            # --- BASIC FIELD CHECK + LOG FULL RECORD (Fix #6) ---
            if not cik_raw or not form or not date:
                print(f"[SKIP] Missing fields: {f}")
                if acc:
                    try:
                        _retry(lambda: self.cache.mark_processed(acc))
                    except Exception as e:
                        print(f"[WARN] Could not mark incomplete filing {acc} as processed: {e}")
                continue

            # Normalize CIK everywhere (Fix #5)
            try:
                cik = str(int(cik_raw))
            except Exception:
                print(f"[SKIP] Invalid CIK '{cik_raw}' in filing: {f}")
                if acc:
                    try:
                        _retry(lambda: self.cache.mark_processed(acc))
                    except Exception as e:
                        print(f"[WARN] Could not mark invalid-cik filing {acc} as processed: {e}")
                continue

            # Ensure mainlink is built if missing and we have primary_document (Fix #4)
            if not mainlink and acc and f.get("primary_document"):
                mainlink = self.build_sec_html_url(cik, acc, f["primary_document"])
                f["mainlink"] = mainlink  # keep source dict consistent too

            # --- READ REDIS FIRST; SKIP IF ALREADY HANDLED TODAY ---
            if acc and self.cache.seen_today(acc):
                print(f"[CACHE] skip (seen today): {acc} CIK={cik} form={form}")
                continue

            existing = active.get(cik)

            # Skip initial S-1 / F-1 if already processed (DB state) (still needed for transitions)
            if form in {"S-1", "F-1"} and existing:
                print(f"[SKIP] Initial form {form} for existing CIK {cik} — already processed.")
                if acc:
                    try:
                        _retry(lambda: self.cache.mark_processed(acc))
                    except Exception as e:
                        print(f"[WARN] Could not mark {acc} processed after initial skip: {e}")
                continue

            # Ignore non-initial forms for new CIKs
            if not existing and form not in settings.INITIAL_FORMS:
                print(f"[SKIP] Non-initial form {form} for new CIK {cik} — not tracked.")
                if acc:
                    try:
                        _retry(lambda: self.cache.mark_processed(acc))
                    except Exception as e:
                        print(f"[WARN] Could not mark {acc} processed after non-initial skip: {e}")
                continue

            # For initial forms, require IPO phrase detection (is_ipo_flag)
            if form in settings.INITIAL_FORMS and not is_ipo_flag:
                print(f"[SKIP] {form} for CIK {cik} — failed IPO phrase detection.")
                if acc:
                    try:
                        _retry(lambda: self.cache.mark_processed(acc))
                    except Exception as e:
                        print(f"[WARN] Could not mark {acc} processed after phrase skip: {e}")
                continue

            # If we made it here, it's a valid new/updated IPO record
            print(f"[DETECT] {form} for CIK {cik} — new IPO detection.")

            # Prospectus -> move to public companies (carry/refresh logo)
            if form in {"424B1", "424B4"} and existing:
                print(f"[DEBUG] Prospectus {form} for CIK {cik}, moving to public_companies")

                logo_url = existing.get("logo_url") if isinstance(existing, dict) else None
                logo_date = existing.get("updated_logo_date") if isinstance(existing, dict) else None

                stale = False
                if logo_date:
                    try:
                        last = datetime.date.fromisoformat(str(logo_date)[:10])
                        stale = (datetime.date.today() - last).days >= settings.REFRESH_AFTER_DAYS
                    except Exception:
                        stale = True
                else:
                    stale = True

                # Try to refresh the logo BEFORE move (Fix #9) — but only if not an acquisition corp and cap >= $50M
                if stale and not _is_acquisition_corp(name) and _cap_ok(market_cap, 50_000_000.0):
                    try:
                        cleaned = self.logo.clean_company_name(name or "")
                        domain = self.logo.search_domain(name or "", cleaned)
                        if domain:
                            img_bytes = self.logo.download_webp_bytes(domain)
                            if img_bytes:
                                object_name = self.logo.hashed_object_name(cik)
                                maybe_url = self.logo.upload_and_get_url(object_name, img_bytes)
                                if maybe_url:
                                    logo_url = maybe_url
                                    logo_date = datetime.date.today().isoformat()
                    except Exception as e:
                        print(f"[WARN] Logo refresh before move failed for {cik}: {e}")
                else:
                    reason = []
                    if not stale:
                        reason.append("not stale")
                    if _is_acquisition_corp(name):
                        reason.append("acquisition corp")
                    if not _cap_ok(market_cap, 50_000_000.0):
                        reason.append("market_cap missing/<$50M")
                    if reason:
                        print(f"[LOGO] Skipping refresh before move for {name}: {', '.join(reason)}")

                pub: dict[str, Any] = {
                    "cik": cik,
                    "company_name": name,
                    "ticker": ticker,
                    "effective_date": date,
                    "form_type": form,
                    "document_url": mainlink,
                    "accession_number": acc,
                }
                if logo_url:
                    pub["logo_url"] = logo_url
                if logo_date:
                    pub["updated_logo_date"] = str(logo_date)[:10]

                # Move (delete from IPO -> insert into public)
                try:
                    self.db.delete_ipo(cik)
                    self.db.move_to_public(pub)
                    print(f"[MOVE] {cik} → public_companies form={form} ticker={ticker}")
                    if acc:
                        _retry(lambda: self.cache.mark_processed(acc))
                except Exception as e:
                    print(f"[ERROR] Failed to move {cik} to public companies: {e}")
                continue

            # Withdrawals remove from IPO table
            if form == "RW" and existing:
                try:
                    self.db.delete_ipo(cik)
                    print(f"[DELETE] {cik} withdrawn")
                    if acc:
                        _retry(lambda: self.cache.mark_processed(acc))
                except Exception as e:
                    print(f"[ERROR] Failed to delete IPO {cik}: {e}")
                continue

            # Upsert IPO row (new or update)
            # Preserve current analyzed flag (Fix #2 part 1)
            already_analyzed = existing.get("analyzed", False) if existing and isinstance(existing, dict) else False

            rec: dict[str, Any] = {
                "cik": cik,
                "company_name": name,
                "ticker": ticker,
                "latest_filing_type": form,
                "latest_filing_date": date,
                "mainlink": mainlink,    # ensure mainlink is passed forward (Fix #4)
                "is_ipo": True,
                "analyzed": already_analyzed,
                "accession_number": acc,
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

            # NOTE: upsert_ipo should be implemented with ON CONFLICT (accession_number) DO UPDATE
            try:
                _retry(lambda: self.db.upsert_ipo(rec))
                print(f"[UPSERT] {cik} latest={form} ticker={ticker}")
                active[cik] = rec  # keep in-memory snapshot fresh
                if acc:
                    _retry(lambda: self.cache.mark_processed(acc))  # mark only after successful write (Fix #7)
            except Exception as e:
                print(f"[ERROR] Failed to upsert IPO {cik}: {e}")
                continue  # do not proceed to logo or AI on failed upsert

            # Logo add/refresh (best-effort) — enforce acquisition + market_cap gate
            try:
                if not _is_acquisition_corp(name) and _cap_ok(market_cap, 50_000_000.0):
                    self.logo.add_logo_if_missing_or_stale(cik, name or "")
                else:
                    reason = []
                    if _is_acquisition_corp(name):
                        reason.append("acquisition corp")
                    if not _cap_ok(market_cap, 50_000_000.0):
                        reason.append("market_cap missing/<$50M")
                    if reason:
                        print(f"[LOGO] Skipping add/refresh for {name}: {', '.join(reason)}")
            except Exception as e:
                print(f"[WARN] Logo update failed for {cik}: {e}")

            # --- AI integration (enabled) ---
            if form in FORMS_TO_ANALYZE and mainlink and not already_analyzed:
                try:
                    # Optional retry to make AI more resilient
                    _retry(lambda: self.ai.analyze_one(
                        cik=str(cik),
                        filing_url=mainlink,
                        company_name=name or "",
                    ), retries=2, base_delay=1.0)
                    print(f"[AI] Analyze complete for CIK={cik} form={form}")

                    # Persist analyzed=True to DB (Fix #2 part 2) + guard in-memory map (Fix #1)
                    rec["analyzed"] = True  # so any subsequent upserts in this run carry the flag
                    try:
                        _retry(lambda: self.db.client.table("ipo").update(
                            {
                                "analyzed": True,
                                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            }
                        ).eq("cik", cik).execute())
                        if cik in active and isinstance(active[cik], dict):
                            active[cik]["analyzed"] = True  # guard to avoid KeyError (Fix #1)
                    except Exception as e:
                        print(f"[WARN] Could not set analyzed=True for CIK={cik}: {e}")

                except Exception as e:
                    print(f"[AI] Analyze failed for CIK={cik} form={form}: {e}")
            elif already_analyzed:
                print(f"[AI] Skip analyze for CIK={cik} form={form}: already analyzed.")

    # ----- daytime EFTS run (start/end inclusive, YYYY-MM-DD) -----
    def fetch_and_push(self, start_date: str, end_date: str) -> None:
        # Optional: warm today's cache once from DB so restarts don't reprocess earlier items
        try:
            today_iso = datetime.datetime.now(ET).date().isoformat()
            warmed = self.db.get_accessions_for_date(today_iso)
            if warmed:
                added = self.cache.bulk_seed_processed(warmed)
                if added:
                    print(f"[CACHE] Warmed {added} accessions for {today_iso}")
        except Exception as e:
            print(f"[WARN] Cache warm-up skipped: {e}")

        # Build the existing CIK set (normalized) to pass to the fetcher
        active_snapshot = self.db.get_ipo_snapshot()  # { "1872195": {...}, ... }
        existing_ciks = {str(int(c)) for c in active_snapshot.keys() if c is not None}

        filings = self.fetcher.fetch(start_date, end_date, existing_ciks=existing_ciks)

        # Direct call — rely on Redis for day-scope dedupe, DB for state transitions
        self._process_filings(filings)
        self.kv.push_ipo_table()

    # ----- nightly master daily-index reconcile (ds = YYYYMMDD) -----
    def reconcile_daily_index(self, ds: str) -> None:
        filings = self.daily.fetch_for_date(ds)
        # Direct call — rely on Redis for day-scope dedupe, DB for state transitions
        self._process_filings(filings)
