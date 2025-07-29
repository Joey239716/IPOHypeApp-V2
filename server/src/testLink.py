import os
import time
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

FORMS = "S-1,F-1,S-1/A,F-1/A,424B1,424B4,S-1MEF,F-1MEF,RW"

class EFTSFetcher:
    def __init__(self, user_agent="youremail@example.com", rate_limit=0.5, max_retries=3):
        self.headers = {"User-Agent": user_agent, "Accept": "application/json"}
        self.rate_limit = rate_limit
        self.max_retries = max_retries

    def fetch(self, date):
        print(f"Fetching filings for {date} using EFTS JSON")
        filings = []
        base_url = "https://efts.sec.gov/LATEST/search-index"

        params = {
            "dateRange": "custom",
            "startdt": date,
            "enddt": date,
            "forms": FORMS,
            "from": 0,
            "size": 100
        }

        while True:
            retries = 0
            while retries < self.max_retries:
                try:
                    resp = requests.get(base_url, headers=self.headers, params=params, timeout=30)
                    print("Querying:", resp.url)
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except Exception as e:
                    retries += 1
                    print(f"Retry {retries}/{self.max_retries} failed for offset {params['from']}: {e}")
                    time.sleep(self.rate_limit * (2 ** retries))
            else:
                print("Max retries exceeded, stopping fetch.")
                break

            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                print("No filings returned by EFTS.")
                break

            for hit in hits:
                src = hit.get("_source", {})
                form = src.get("file_type") or src.get("form") or src.get("formType")
                filing = {
                    'cik': src.get("ciks", [None])[0],
                    'company_name': src.get("display_names", [None])[0],
                    'form_type': form,
                    'date_filed': src.get("file_date", "")[:10],
                    'link': f"https://www.sec.gov/Archives/{src.get('file_name') or src.get('fileName')}",
                    'accession_number': src.get("adsh"),
                    'description': src.get("file_description"),
                    'size': src.get("size"),
                    'filing_id': hit.get("_id")
                }
                filings.append(filing)
                print(f"Read filing: {filing}")

            print(f"Fetched {len(hits)} new filings, total so far: {len(filings)}")

            if len(hits) < params["size"]:
                break

            params["from"] += params["size"]
            time.sleep(self.rate_limit)

        # Print a breakdown by form type
        form_counts = {}
        for f in filings:
            form_counts[f['form_type']] = form_counts.get(f['form_type'], 0) + 1
        print("Form type breakdown:", form_counts)

        print(f"Total filings fetched: {len(filings)}")
        return filings

if __name__ == '__main__':
    fetcher = EFTSFetcher()
    today = datetime.date.today()
    fetcher.fetch(today.isoformat())