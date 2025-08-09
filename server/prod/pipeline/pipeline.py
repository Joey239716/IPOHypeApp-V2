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

    # --- shared processor ---
    def _process_filings(self, filings: List[dict[str, Any]]) -> None:
        if not filings:
            print("[INFO] No filings to process.")
            return

        active = self.db.get_ipo_snapshot()

        for f in filings:
            cik = f['cik']
            form = f['form_type']
            date = f['date_filed']
            acc  = f.get('accession_number')
            existing = active.get(str(cik))

            # Ignore non-initial if not seen before
            if not existing and form not in settings.INITIAL_FORMS:
                continue

            # For initial forms, require IPO phrase detection flag
            if form in settings.INITIAL_FORMS and not f.get('is_ipo'):
                continue

            # Prospectus -> move to public companies
            if form in {'424B1','424B4'} and existing:
                print(f"[DEBUG] Processing prospectus {form} for CIK {cik}, existing={bool(existing)}")
                self.db.delete_ipo(cik)
                pub = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'ticker': f.get('ticker'),
                    'effective_date': date,
                    'form_type': form,
                    'document_url': f['mainlink'],
                    'accession_number': acc,
                }
                self.db.move_to_public(pub)
                print(f"[MOVE] {cik}→public_companies form={form} ticker={f.get('ticker')}")
                continue

            # Withdrawals
            if form == 'RW' and existing:
                self.db.delete_ipo(cik)
                print(f"[DELETE] {cik} withdrawn")
                continue

            # Upsert IPO row
            if existing or form in settings.INITIAL_FORMS:
                rec: dict[str, Any] = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'ticker': f.get('ticker'),
                    'latest_filing_type': form,
                    'latest_filing_date': date,
                    'mainlink': f['mainlink'],
                    'is_ipo': True,
                    'analyzed': False,
                    'accession_number': acc,
                    'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                self.db.upsert_ipo(rec)
                print(f"[UPSERT] {cik} latest={form} ticker={f.get('ticker')}")
                active[str(cik)] = rec

                # Add/refresh logo if missing or stale (>= 6 months)
                try:
                    self.logo.add_logo_if_missing_or_stale(cik, f['company_name'])
                except Exception as e:
                    print(f"[WARN] Logo update failed for {cik}: {e}")

    # --- daytime EFTS run ---
    def fetch_and_push(self, start_date: str, end_date: str) -> None:
        filings = self.fetcher.fetch(start_date, end_date)
        self._process_filings(filings)

    # --- nightly master index reconcile ---
    def reconcile_daily_index(self, ds: str) -> None:
        filings = self.daily.fetch_for_date(ds)
        self._process_filings(filings)

import datetime
from typing import Any

from ..config import settings
from ..services.db import Database
from ..services.logo_service import LogoService
from ..efts.fetcher import EFTSFetcher

class Pipeline:
    def __init__(self) -> None:
        self.db = Database()
        self.logo = LogoService(self.db)
        self.fetcher = EFTSFetcher()

    def fetch_and_push(self, start_date: str, end_date: str) -> None:
        filings = self.fetcher.fetch(start_date, end_date)
        if not filings:
            print("[INFO] No filings to upsert.")
            return

        active = self.db.get_ipo_snapshot()

        for f in filings:
            cik = f['cik']
            form = f['form_type']
            date = f['date_filed']
            acc  = f['accession_number']
            existing = active.get(str(cik))

            # Ignore non-initial if not seen before
            if not existing and form not in settings.INITIAL_FORMS:
                continue

            # For initial forms, require IPO phrase detection
            if form in settings.INITIAL_FORMS and not f['is_ipo']:
                continue

            # Prospectus -> move to public companies
            if form in {'424B1','424B4'} and existing:
                print(f"[DEBUG] Processing prospectus {form} for CIK {cik}, existing={bool(existing)}")
                self.db.delete_ipo(cik)
                pub = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'ticker': f['ticker'],
                    'effective_date': date,
                    'form_type': form,
                    'document_url': f['mainlink'],
                    'accession_number': acc,
                }
                self.db.move_to_public(pub)
                print(f"[MOVE] {cik}→public_companies form={form} ticker={f['ticker']}")
                continue

            # Withdrawals
            if form == 'RW' and existing:
                self.db.delete_ipo(cik)
                print(f"[DELETE] {cik} withdrawn")
                continue

            # Upsert IPO row
            if existing or form in settings.INITIAL_FORMS:
                rec: dict[str, Any] = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'ticker': f['ticker'],
                    'latest_filing_type': form,
                    'latest_filing_date': date,
                    'mainlink': f['mainlink'],
                    'is_ipo': True,
                    'analyzed': False,
                    'accession_number': acc,
                    'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
                self.db.upsert_ipo(rec)
                print(f"[UPSERT] {cik} latest={form} ticker={f['ticker']}")
                active[str(cik)] = rec

                # Add/refresh logo if missing or stale (>= 6 months)
                try:
                    self.logo.add_logo_if_missing_or_stale(cik, f['company_name'])
                except Exception as e:
                    print(f"[WARN] Logo update failed for {cik}: {e}")