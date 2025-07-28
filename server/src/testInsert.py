# pip install python-dotenv supabase requests

# 1. Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# 2. Standard library imports
import os
import time
import datetime
import requests

# 3. Supabase & error handling imports
from postgrest.exceptions import APIError
from supabase import create_client, Client

# 4. Define processing order and groups
FILE_ORDER = {
    "S-1":      1,  # Initial registration
    "F-1":      1,  # Foreign registration (if re-enabled)
    "S-1/A":    2,  # Pre-effective amendment
    "F-1/A":    2,
    "S-1MEF":   3,  # Rule 462(b) follow-on
    "F-1MEF":   3,
    "POS AM":   4,  # Post-effective amendment
    "POS462B":  5,  # Post-effective 462(b) amendment
    "424B1":    6,
    "424B4":    7
}
INITIAL_FORMS = {"S-1", "F-1"}
AMENDMENT_FORMS = set(FILE_ORDER.keys()) - INITIAL_FORMS

class S1Fetcher:
    """
    Two-pass processor: First ingest initial S-1/F-1 filings to populate ipo table.
    Then process amendments (S-1/A, 424B*, etc.) only for those CIKs in ipo table.
    """
    def __init__(self, user_agent: str = "youremail@example.com", rate_limit_seconds: float = 0.5):
        self.headers = {"User-Agent": user_agent}
        self.rate_limit = rate_limit_seconds

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise RuntimeError("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env")
        self.supabase: Client = create_client(supabase_url, supabase_key)

    @staticmethod
    def parse_date(date_str: str) -> datetime.date:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

    def fetch(self, start_date: str, end_date: str) -> list[dict]:
        """
        Fetch daily EDGAR index filings, returning list of dicts with keys:
        cik, company_name, form_type, date_filed (YYYY-MM-DD), link, accession_number
        """
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end   = datetime.datetime.strptime(end_date,   "%Y-%m-%d")
        filings = []
        date = start
        while date <= end:
            ds = date.strftime("%Y%m%d")
            print(f"Checking date: {date.strftime('%Y-%m-%d')}")
            qtr = (date.month - 1) // 3 + 1
            idx_url = f"https://www.sec.gov/Archives/edgar/daily-index/{date.year}/QTR{qtr}/master.{ds}.idx"
            try:
                resp = requests.get(idx_url, headers=self.headers)
                resp.raise_for_status()
                for line in resp.text.splitlines():
                    parts = line.split("|")
                    if len(parts) < 5:
                        continue
                    cik, comp, form, filed_raw, fname = parts
                    if form in FILE_ORDER:
                        # normalize date
                        if len(filed_raw) == 8 and filed_raw.isdigit():
                            filed = f"{filed_raw[:4]}-{filed_raw[4:6]}-{filed_raw[6:]}"
                        else:
                            filed = filed_raw
                        # accession number from filename
                        fn = fname.rsplit('/',1)[-1]
                        acc = fn[:-4] if fn.lower().endswith('.txt') else fn
                        link = f"https://www.sec.gov/Archives/{fname}"
                        filings.append({
                            'cik': cik,
                            'company_name': comp,
                            'form_type': form,
                            'date_filed': filed,
                            'link': link,
                            'accession_number': acc
                        })
            except Exception as e:
                print(f"⚠️ Error fetching {idx_url}: {e}")
            time.sleep(self.rate_limit)
            date += datetime.timedelta(days=1)
        return filings

    def fetch_and_push(self, start_date: str, end_date: str):
        filings = self.fetch(start_date, end_date)
        if not filings:
            print("No filings found.")
            return
        # sort by order then date
        filings.sort(key=lambda f: (FILE_ORDER[f['form_type']], f['date_filed']))

        # First pass: initial registrations
        print("\n--- First pass: Initial registrations (S-1/F-1) ---")
        for f in filings:
            if f['form_type'] in INITIAL_FORMS:
                rec = {
                    'cik': f['cik'],
                    'company_name': f['company_name'],
                    'latest_filing_type': f['form_type'],
                    'latest_filing_date': f['date_filed'],
                    'mainlink': f['link']
                }
                print(f"UPSERT ipo initial: {rec}")
                try:
                    self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()
                except APIError as err:
                    print(f"❌ Failed initial upsert for {f['cik']}: {err}")
        # reload existing CIKs
        resp = self.supabase.table('ipo').select('cik').execute()
        initial_ciks = {r['cik'] for r in (resp.data or [])}

        # Second pass: amendments
        print("\n--- Second pass: Amendments ---")
        for f in filings:
            form = f['form_type']
            cik = f['cik']
            if form not in AMENDMENT_FORMS:
                continue
            if cik not in initial_ciks:
                print(f"⏭️ Skipping amendment {form} for unknown CIK {cik}")
                continue
            # process amendment or prospectus
            print(f"Processing amendment {form} for CIK {cik}")
            if form.startswith('424B'):
                # move to public_companies
                self.supabase.table('ipo').delete().eq('cik', cik).execute()
                pub = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'effective_date': f['date_filed'],
                    'accession_number': f['accession_number'],
                    'form_type': form,
                    'document_url': f['link']
                }
                print(f"UPSERT public_companies: {pub}")
                try:
                    self.supabase.table('public_companies').upsert(pub, on_conflict='cik').execute()
                except APIError as err:
                    print(f"❌ Failed public upsert for {cik}: {err}")
            else:
                # S-1/A, S-1MEF, POS AM, POS462B
                rec = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'latest_filing_type': form,
                    'latest_filing_date': f['date_filed'],
                    'mainlink': f['link']
                }
                print(f"UPSERT ipo amendment: {rec}")
                try:
                    self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()
                except APIError as err:
                    print(f"❌ Failed amendment upsert for {cik}: {err}")

if __name__ == '__main__':
    fetcher = S1Fetcher(rate_limit_seconds=0.5)
    today = datetime.date.today()
    three_months_ago = today - datetime.timedelta(days=180)
    fetcher.fetch_and_push(three_months_ago.isoformat(), today.isoformat())
