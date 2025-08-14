from __future__ import annotations

import datetime
from typing import Any, List

from openai import OpenAI

from ..config import settings
from ..services.db import Database
from ..services.logo_service import LogoService
from ..services.ai_analysis import AnalyzeIPO
from ..efts.fetcher import EFTSFetcher
from ..edgar.daily_index import DailyIndexChecker

# Only analyze these amendment forms with GPT (kept for future use)
FORMS_TO_ANALYZE = {"S-1/A", "F-1/A"}


class Pipeline:
    def __init__(self) -> None:
        self.db = Database()
        self.logo = LogoService(self.db)
        self.fetcher = EFTSFetcher()
        self.daily = DailyIndexChecker()

        # --- AI clients (minimal integration) ---
        self.openai = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.ai = AnalyzeIPO(self.db.client, self.openai)

    @staticmethod
    def build_sec_html_url(cik: str, accession_number: str, primary_document: str) -> str:
        """Build a SEC Archives HTML URL from cik, accession_number, and primary_document."""
        cik_nozero = str(int(cik))  # remove leading zeros
        acc_nodash = accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik_nozero}/{acc_nodash}/{primary_document}"

    # ----- shared processing for both EFTS and daily-index -----
    def _process_filings(self, filings: List[dict[str, Any]]) -> None:
        if not filings:
            print("[INFO] No filings to process.")
            return

        active = self.db.get_ipo_snapshot()  # dict keyed by normalized str(CIK)

        for f in filings:
            cik = f.get("cik")
            form = f.get("form_type")
            date = f.get("date_filed")
            acc = f.get("accession_number")
            name = f.get("company_name")
            ticker = f.get("ticker")
            mainlink = f.get("mainlink")
            is_ipo_flag = f.get("is_ipo")

            # Ensure mainlink is built if missing and we have primary_document
            if not mainlink and cik and acc and f.get("primary_document"):
                mainlink = self.build_sec_html_url(cik, acc, f["primary_document"])
                f["mainlink"] = mainlink

            if not cik or not form or not date:
                continue

            existing = active.get(str(cik))

            # Skip amendments if CIK already tracked (prevents re-parsing root initial forms)
            if form in {"S-1/A", "F-1/A"} and existing:
                print(f"[SKIP] Amendment {form} for existing CIK {cik} — will be handled in amendments pass.")
                # If you DO want to analyze amendments here, remove this `continue` and call AI below
                # continue

            # Skip initial S-1 / F-1 if already processed
            if form in {"S-1", "F-1"} and existing:
                print(f"[SKIP] Initial form {form} for existing CIK {cik} — already processed.")
                continue

            # Ignore non-initial forms for new CIKs
            if not existing and form not in settings.INITIAL_FORMS:
                print(f"[SKIP] Non-initial form {form} for new CIK {cik} — not tracked.")
                continue

            # For initial forms, require IPO phrase detection
            if form in settings.INITIAL_FORMS and not is_ipo_flag:
                print(f"[SKIP] {form} for CIK {cik} — failed IPO phrase detection.")
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

                if stale:
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

                self.db.delete_ipo(cik)
                self.db.move_to_public(pub)
                print(f"[MOVE] {cik} → public_companies form={form} ticker={ticker}")
                continue

            # Withdrawals remove from IPO table
            if form == "RW" and existing:
                self.db.delete_ipo(cik)
                print(f"[DELETE] {cik} withdrawn")
                continue

            # Upsert IPO row (new or update)
            if existing or form in settings.INITIAL_FORMS:
                rec: dict[str, Any] = {
                    "cik": cik,
                    "company_name": name,
                    "ticker": ticker,
                    "latest_filing_type": form,
                    "latest_filing_date": date,
                    "mainlink": mainlink,
                    "is_ipo": True,
                    "analyzed": False,  # flip to True after AI pipeline if you enable it
                    "accession_number": acc,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                self.db.upsert_ipo(rec)
                print(f"[UPSERT] {cik} latest={form} ticker={ticker}")
                active[str(cik)] = rec

                try:
                    self.logo.add_logo_if_missing_or_stale(cik, name or "")
                except Exception as e:
                    print(f"[WARN] Logo update failed for {cik}: {e}")

                # --- Optional AI integration (currently off) ---
                # if form in FORMS_TO_ANALYZE and mainlink:
                #     try:
                #         already = self.db.get_ipo_by_cik(str(cik))
                #         if already and already.get("analyzed"):
                #             print(f"[AI] Skip analyze for CIK={cik} form={form}: already analyzed.")
                #         else:
                #             self.ai.analyze_one(cik=str(cik), filing_url=mainlink, company_name=name or "")
                #     except Exception as e:
                #         print(f"[AI] Analyze failed for CIK={cik} form={form}: {e}")

    # ----- daytime EFTS run (start/end inclusive, YYYY-MM-DD) -----
    def fetch_and_push(self, start_date: str, end_date: str) -> None:
        # Build the existing CIK set (normalized) to pass to the fetcher
        active_snapshot = self.db.get_ipo_snapshot()  # { "1872195": {...}, ... }
        existing_ciks = {str(int(c)) for c in active_snapshot.keys() if c is not None}

        filings = self.fetcher.fetch(start_date, end_date, existing_ciks=existing_ciks)

        # Global accession de-dupe (keep ones with no accession or not seen yet)
        try:
            seen_accessions = {
                r["accession_number"]
                for r in self.db.client.table("ipo")
                .select("accession_number")
                .execute().data
                if r.get("accession_number")
            }
            before = len(filings)
            filings = [
                f
                for f in filings
                if not f.get("accession_number")
                or f["accession_number"] not in seen_accessions
            ]
            skipped = before - len(filings)
            if skipped:
                print(f"[EFTS] Skipping {skipped} filings already in database (global accession check).")
        except Exception as e:
            print(f"[WARN] Daytime global de-dupe failed: {e}")

        self._process_filings(filings)

    # ----- nightly master daily-index reconcile (ds = YYYYMMDD) -----
    def reconcile_daily_index(self, ds: str) -> None:
        filings = self.daily.fetch_for_date(ds)

        try:
            seen_accessions = {
                r["accession_number"]
                for r in self.db.client.table("ipo")
                .select("accession_number")
                .execute().data
                if r.get("accession_number")
            }
            before = len(filings)
            filings = [
                f
                for f in filings
                if not f.get("accession_number")
                or f["accession_number"] not in seen_accessions
            ]
            skipped = before - len(filings)
            if skipped:
                print(f"[DAILY] Skipping {skipped} filings already in database (global accession check).")
        except Exception as e:
            print(f"[WARN] Nightly global de-dupe failed: {e}")

        self._process_filings(filings)
