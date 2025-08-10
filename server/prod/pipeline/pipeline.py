# prod/pipeline/pipeline.py
from __future__ import annotations

import datetime
from typing import Any, List

from ..config import settings
from ..services.db import Database
from ..services.logo_service import LogoService
from ..efts.fetcher import EFTSFetcher
from ..edgar.daily_index import DailyIndexChecker


class Pipeline:
    def __init__(self) -> None:
        self.db = Database()
        self.logo = LogoService(self.db)
        self.fetcher = EFTSFetcher()
        self.daily = DailyIndexChecker()

    # ----- shared processing for both EFTS and daily-index -----
    def _process_filings(self, filings: List[dict[str, Any]]) -> None:
        if not filings:
            print("[INFO] No filings to process.")
            return

        active = self.db.get_ipo_snapshot()

        for f in filings:
            cik = f.get("cik")
            form = f.get("form_type")
            date = f.get("date_filed")
            acc = f.get("accession_number")
            name = f.get("company_name")
            ticker = f.get("ticker")
            mainlink = f.get("mainlink")
            is_ipo_flag = f.get("is_ipo")

            if not cik or not form or not date:
                continue

            existing = active.get(str(cik))

            # Ignore non-initial forms if we haven't seen this CIK before
            if not existing and form not in settings.INITIAL_FORMS:
                continue

            # For initial forms, require IPO phrase detection
            if form in settings.INITIAL_FORMS and not is_ipo_flag:
                continue

            # Prospectus -> move to public companies (carry/refresh logo)
            if form in {"424B1", "424B4"} and existing:
                print(f"[DEBUG] Prospectus {form} for CIK {cik}, moving to public_companies")

                # Start with existing IPO logo fields
                logo_url = existing.get("logo_url") if isinstance(existing, dict) else None
                logo_date = existing.get("updated_logo_date") if isinstance(existing, dict) else None

                # Decide if we should refresh (missing or stale)
                stale = False
                if logo_date:
                    try:
                        last = datetime.date.fromisoformat(str(logo_date)[:10])
                        stale = (datetime.date.today() - last).days >= settings.REFRESH_AFTER_DAYS
                    except Exception:
                        stale = True
                else:
                    stale = True

                # Fetch/upload if missing or stale
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

                # Build public_companies record (include logo if available)
                pub = {
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

                # Move: delete from ipo, upsert into public_companies
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
                    "analyzed": False,
                    "accession_number": acc,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                self.db.upsert_ipo(rec)
                print(f"[UPSERT] {cik} latest={form} ticker={ticker}")
                active[str(cik)] = rec

                # Add/refresh logo if missing or stale (≥ REFRESH_AFTER_DAYS)
                try:
                    self.logo.add_logo_if_missing_or_stale(cik, name or "")
                except Exception as e:
                    print(f"[WARN] Logo update failed for {cik}: {e}")

    # ----- daytime EFTS run (start/end inclusive, YYYY-MM-DD) -----
    def fetch_and_push(self, start_date: str, end_date: str) -> None:
        filings = self.fetcher.fetch(start_date, end_date)
        self._process_filings(filings)

    # ----- nightly master daily-index reconcile (ds = YYYYMMDD) -----
    def reconcile_daily_index(self, ds: str) -> None:
        filings = self.daily.fetch_for_date(ds)

        # Skip anything already captured during the day (by accession_number)
        date_iso = f"{ds[:4]}-{ds[4:6]}-{ds[6:]}"
        seen = self.db.get_accessions_for_date(date_iso)
        if seen:
            before = len(filings)
            filings = [
                f for f in filings
                if not f.get("accession_number") or f["accession_number"] not in seen
            ]
            skipped = before - len(filings)
            if skipped:
                print(f"[DAILY] Skipping {skipped} filings already captured during the day (by accession).")

        self._process_filings(filings)
