# === File 1: fetch_and_push.py ===
# Purpose: Fetch SEC filings and upload relevant IPO/public data to Supabase

import os
import time
import datetime
import requests
import re
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError

load_dotenv()

FILE_ORDER = {
    "RW": 0, "S-1": 1, "F-1": 1,
    "S-1/A": 2, "F-1/A": 2,
    "S-1MEF": 3, "F-1MEF": 3,
    "POS AM": 4, "POS462B": 5,
    "424B1": 6, "424B4": 7
}
INITIAL_FORMS = {"S-1", "F-1"}
AMENDMENT_FORMS = set(FILE_ORDER.keys()) - INITIAL_FORMS

class FilingFetcher:
    def __init__(self, user_agent="youremail@example.com", rate_limit=0.5):
        self.headers = {"User-Agent": user_agent}
        self.rate_limit = rate_limit

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("Missing Supabase credentials")
        self.supabase: Client = create_client(url, key)

    def fetch(self, start_date, end_date):
        print(f"Fetching filings from {start_date} to {end_date}")
        filings = []
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        date = start
        while date <= end:
            ds = date.strftime("%Y%m%d")
            qtr = (date.month - 1) // 3 + 1
            idx_url = f"https://www.sec.gov/Archives/edgar/daily-index/{date.year}/QTR{qtr}/master.{ds}.idx"
            try:
                print(f"Requesting index file: {idx_url}")
                resp = requests.get(idx_url, headers=self.headers)
                resp.raise_for_status()
                for line in resp.text.splitlines():
                    parts = line.split("|")
                    if len(parts) < 5:
                        continue
                    cik, comp, form, filed_raw, fname = parts
                    if form in FILE_ORDER:
                        filed = f"{filed_raw[:4]}-{filed_raw[4:6]}-{filed_raw[6:]}"
                        filings.append({
                            'cik': cik, 'company_name': comp, 'form_type': form,
                            'date_filed': filed, 'link': f"https://www.sec.gov/Archives/{fname}"
                        })
                print(f"Found {len(filings)} relevant filings on {date.strftime('%Y-%m-%d')}")
            except:
                print(f"Skipped {idx_url}")
            time.sleep(self.rate_limit)
            date += datetime.timedelta(days=1)
        return filings

    def fetch_and_push(self, start_date, end_date):
        print("Starting fetch_and_push process")
        filings = self.fetch(start_date, end_date)
        if not filings:
            print("No filings found.")
            return
        print(f"Total filings to process: {len(filings)}")
        filings.sort(key=lambda f: (FILE_ORDER[f['form_type']], f['date_filed']))
        resp = self.supabase.table('ipo').select('cik').execute()
        active_ciks = {r['cik'] for r in (resp.data or [])}

        print("Processing initial S-1 and F-1 forms")
        for f in filings:
            cik = f['cik']; form = f['form_type']
            if form in INITIAL_FORMS:
                rec = {
                    'cik': f['cik'],
                    'company_name': f['company_name'],
                    'latest_filing_type': form,
                    'latest_filing_date': f['date_filed'],
                    'mainlink': f['link']
                }
                try:
                    self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()
                    print(f"Upserted initial filing for CIK {cik}")
                    active_ciks.add(cik)
                except APIError as err:
                    print(f"Initial upsert failed for {cik}: {err}")

        print("Processing amendments and withdrawals")
        for f in filings:
            cik = f['cik']; form = f['form_type']
            if form == 'RW' and cik in active_ciks:
                print(f"Deleting withdrawn filing for CIK {cik}")
                self.supabase.table('ipo').delete().eq('cik', cik).execute()
                active_ciks.remove(cik)
            elif form in INITIAL_FORMS and cik not in active_ciks:
                print(f"Re-inserting new initial filing for CIK {cik}")
                rec = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'latest_filing_type': form,
                    'latest_filing_date': f['date_filed'],
                    'mainlink': f['link']
                }
                self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()
                active_ciks.add(cik)
            elif form.startswith('424B') and cik in active_ciks:
                print(f"Moving CIK {cik} to public_companies table")
                self.supabase.table('ipo').delete().eq('cik', cik).execute()
                self.supabase.table('public_companies').upsert({
                    'cik': cik,
                    'company_name': f['company_name'],
                    'effective_date': f['date_filed'],
                    'form_type': form,
                    'document_url': f['link']
                }, on_conflict='cik').execute()
            elif form in AMENDMENT_FORMS and cik in active_ciks:
                print(f"Updating amendment for CIK {cik} with form {form}")
                rec = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'latest_filing_type': form,
                    'latest_filing_date': f['date_filed'],
                    'mainlink': f['link']
                }
                self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()

if __name__ == '__main__':
    fetcher = FilingFetcher()
    today = datetime.date.today()
    start = today - datetime.timedelta(days=4)
    fetcher.fetch_and_push(start.isoformat(), today.isoformat())
