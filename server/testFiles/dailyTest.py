import os
import time
import datetime
import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError

load_dotenv()

# Individual form types to iterate over
FORMS = ["S-1", "F-1", "S-1/A", "F-1/A", "424B1", "424B4", "S-1MEF", "F-1MEF", "RW"]
INITIAL_FORMS = {"S-1", "F-1"}
LIMIT_WORDS = 2000
BYTE_CHUNK_SIZE = 8192
PAGE_SIZE = 100
IPO_REGEX = re.compile(r"\binitial public offering\b", re.IGNORECASE)


def normalize_cik(cik):
    if not cik:
        return None
    return str(int(cik))


def extract_name_and_ticker(display_name):
    cik_match = re.search(r"\s+\(CIK\s*\d+\)$", display_name or "")
    base = display_name[:cik_match.start()] if cik_match else display_name or ""
    ticker_match = re.search(r"\s+\(([^)]+)\)\s*$", base)
    if ticker_match:
        first_ticker = ticker_match.group(1).split(",")[0].strip()
        company = base[:ticker_match.start()].strip()
        return company, first_ticker
    return base.strip(), None


class EFTSFetcher:
    def __init__(self, user_agent="youremail@example.com", rate_limit=0.5, max_retries=3):
        self.headers = {"User-Agent": user_agent, "Accept": "application/json"}
        self.rate_limit = rate_limit
        self.max_retries = max_retries

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not supabase_key:
            raise RuntimeError("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env")
        self.supabase: Client = create_client(supabase_url, supabase_key)

    def clean_html(self, raw_html):
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "head", "meta", "title"]):
            tag.decompose()
        return " ".join(soup.get_text(separator=" ").split())

    def fetch(self, start_date, end_date):
        print(f"[INFO] Fetching filings from {start_date} to {end_date} by form type")
        all_filings = []
        base_url = "https://efts.sec.gov/LATEST/search-index"

        for form_type in FORMS:
            offset = 0
            print(f"[INFO] Querying form {form_type}")
            while True:
                params = [
                    ("dateRange", "custom"),
                    ("startdt", start_date),
                    ("enddt", end_date),
                    ("forms", form_type),
                    ("from", offset),
                    ("size", PAGE_SIZE),
                ]

                retries = 0
                while retries < self.max_retries:
                    try:
                        resp = requests.get(base_url, headers=self.headers, params=params, timeout=30)
                        print("[QUERY]", resp.url)
                        resp.raise_for_status()
                        data = resp.json()
                        break
                    except Exception as e:
                        retries += 1
                        print(f"[WARN] Retry {retries}/{self.max_retries} for {form_type} offset {offset}: {e}")
                        time.sleep(self.rate_limit * (2 ** retries))
                else:
                    print("[ERROR] Max retries exceeded—stopping form fetch.")
                    break

                hits = data.get("hits", {}).get("hits", [])
                if not hits:
                    print(f"[INFO] No more {form_type} filings.")
                    break

                for hit in hits:
                    src = hit.get("_source", {})
                    cik = normalize_cik(src.get("ciks", [None])[0])
                    adsh = src.get("adsh")
                    display_name = src.get("display_names", [""])[0]
                    company_name, ticker = extract_name_and_ticker(display_name)

                    link = None
                    if adsh and cik:
                        adsh_nodash = adsh.replace("-", "")
                        link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh_nodash}/{adsh}.txt"

                    ipo_detected = False
                    if form_type in INITIAL_FORMS and link:
                        try:
                            r = requests.get(link, headers=self.headers, timeout=30, stream=True)
                            r.raise_for_status()
                            buffer = ""
                            for chunk in r.iter_content(BYTE_CHUNK_SIZE, decode_unicode=True):
                                buffer += chunk
                                if len(buffer) > 200000:
                                    break
                            if IPO_REGEX.search(self.clean_html(buffer)):
                                ipo_detected = True
                                print(f"[INFO] IPO detected in {form_type} for {company_name} ({ticker})")
                        except Exception as e:
                            print(f"[ERROR] Failed to fetch text for {company_name}: {e}")

                    all_filings.append({
                        'cik': cik,
                        'company_name': company_name,
                        'ticker': ticker,
                        'form_type': form_type,
                        'date_filed': src.get('file_date', '')[:10],
                        'mainlink': link or f"https://www.sec.gov/Archives/{src.get('file_name')}",
                        'is_ipo': ipo_detected,
                        'analyzed': False,
                        'accession_number': adsh
                    })

                if len(hits) < PAGE_SIZE:
                    break
                offset += PAGE_SIZE
                time.sleep(self.rate_limit)

        # sort by date and accession
        all_filings.sort(key=lambda f: (f['date_filed'], f['accession_number'] or ''), reverse=False)
        return all_filings

    def fetch_and_push(self, start_date, end_date):
        filings = self.fetch(start_date, end_date)
        if not filings:
            print("[INFO] No filings to upsert.")
            return

        resp = self.supabase.table('ipo').select('cik','latest_filing_date','is_ipo').execute()
        active = {r['cik']: r for r in (resp.data or [])}

        for f in filings:
            cik, form, date, acc = f['cik'], f['form_type'], f['date_filed'], f['accession_number']
            existing = active.get(cik)
            if not existing and form not in INITIAL_FORMS:
                continue
            if form in INITIAL_FORMS and not f['is_ipo']:
                continue
            if form in {'424B1','424B4'} and existing:
                print(f"[DEBUG] Processing prospectus {form} for CIK {cik}, existing={bool(existing)}")
                self.supabase.table('ipo').delete().eq('cik',cik).execute()
                pub = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'ticker': f['ticker'],
                    'effective_date': date,
                    'form_type': form,
                    'document_url': f['mainlink'],
                    'accession_number': acc
                }
                self.supabase.table('public_companies').upsert(pub, on_conflict='cik').execute()
                print(f"[MOVE] {cik}→public_companies form={form} ticker={f['ticker']}")
                continue
            if form == 'RW' and existing:
                self.supabase.table('ipo').delete().eq('cik',cik).execute()
                print(f"[DELETE] {cik} withdrawn")
                continue
            if existing or form in INITIAL_FORMS:
                rec = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'ticker': f['ticker'],
                    'latest_filing_type': form,
                    'latest_filing_date': date,
                    'mainlink': f['mainlink'],
                    'is_ipo': True,
                    'analyzed': False,
                    'accession_number': acc,
                    'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()
                print(f"[UPSERT] {cik} latest={form} ticker={f['ticker']}")
                active[cik] = rec

if __name__=='__main__':
    fetcher = EFTSFetcher()
    fetcher.fetch_and_push('2025-07-28', datetime.date.today().isoformat())
