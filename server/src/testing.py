# pip install python-dotenv supabase requests openai beautifulsoup4

# 1. Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# 2. Standard library imports
import os
import time
import datetime
import requests
import re
import json

# 3. HTML parsing
from bs4 import BeautifulSoup

# 4. OpenAI import & configure
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 5. Supabase & error handling imports
from postgrest.exceptions import APIError
from supabase import create_client, Client

# 6. Define processing order and groups (including RW withdrawals)
FILE_ORDER = {
    "RW":       0,
    "S-1":      1,
    "F-1":      1,
    "S-1/A":    2,
    "F-1/A":    2,
    "S-1MEF":   3,
    "F-1MEF":   3,
    "POS AM":   4,
    "POS462B":  5,
    "424B1":    6,
    "424B4":    7
}
INITIAL_FORMS = {"S-1", "F-1"}
AMENDMENT_FORMS = set(FILE_ORDER.keys()) - INITIAL_FORMS

def null_if_unknown(val, cast_type=str):
    if isinstance(val, str) and val.lower() == "unknown":
        return None
    try:
        return cast_type(val)
    except:
            return None

def null_if_unknown_numeric(val):
    if isinstance(val, str):
        if val.lower() == "unknown":
            return None
        val = val.replace(",", "").replace("$", "").strip()
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return None

class S1Fetcher:
    """
    Two-pass processor:
      1) Ingest initial S-1/F-1 filings into `ipo` table.
      2) Process amendments, RW withdrawals, allow re-entry on new S-1/F-1.
      3) Analyze latest IPO filings with OpenAI 4o-mini.
    """
    def __init__(self,
                 user_agent: str = "youremail@example.com",
                 rate_limit_seconds: float = 0.5):
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
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end   = datetime.datetime.strptime(end_date,   "%Y-%m-%d")
        filings = []
        date = start
        while date <= end:
            ds = date.strftime("%Y%m%d")
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
                        if len(filed_raw) == 8 and filed_raw.isdigit():
                            filed = f"{filed_raw[:4]}-{filed_raw[4:6]}-{filed_raw[6:]}"
                        else:
                            filed = filed_raw
                        fn = fname.rsplit('/', 1)[-1]
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
                print(f"Skipped {idx_url}")
            time.sleep(self.rate_limit)
            date += datetime.timedelta(days=1)
        return filings

    def fetch_and_push(self, start_date: str, end_date: str):
        filings = self.fetch(start_date, end_date)
        if not filings:
            print("No filings found.")
            return

        filings.sort(key=lambda f: (FILE_ORDER[f['form_type']], f['date_filed']))

        # First pass: initial
        resp = self.supabase.table('ipo').select('cik').execute()
        active_ciks = {r['cik'] for r in (resp.data or [])}
        for f in filings:
            if f['form_type'] in INITIAL_FORMS:
                rec = {
                    'cik': f['cik'],
                    'company_name': f['company_name'],
                    'latest_filing_type': f['form_type'],
                    'latest_filing_date': f['date_filed'],
                    'mainlink': f['link']
                }
                try:
                    self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()
                    active_ciks.add(f['cik'])
                except APIError as err:
                    print(f"❌ Initial upsert failed for {f['cik']}: {err}")

        # Second pass: amendments & withdrawals
        for f in filings:
            cik = f['cik']; form = f['form_type']
            if form == 'RW' and cik in active_ciks:
                self.supabase.table('ipo').delete().eq('cik', cik).execute()
                active_ciks.remove(cik)
                continue
            if form in INITIAL_FORMS and cik not in active_ciks:
                rec = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'latest_filing_type': form,
                    'latest_filing_date': f['date_filed'],
                    'mainlink': f['link']
                }
                self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()
                active_ciks.add(cik)
                continue
            if form not in AMENDMENT_FORMS or cik not in active_ciks:
                continue
            if form.startswith('424B'):
                self.supabase.table('ipo').delete().eq('cik', cik).execute()
                pub = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'effective_date': f['date_filed'],
                    'accession_number': f['accession_number'],
                    'form_type': form,
                    'document_url': f['link']
                }
                self.supabase.table('public_companies').upsert(pub, on_conflict='cik').execute()
            else:
                rec = {
                    'cik': cik,
                    'company_name': f['company_name'],
                    'latest_filing_type': form,
                    'latest_filing_date': f['date_filed'],
                    'mainlink': f['link']
                }
                self.supabase.table('ipo').upsert(rec, on_conflict='cik').execute()

    def analyze_latest(self):
        resp = self.supabase.table('ipo').select('cik', 'mainlink').execute()
        rows = resp.data or []
        for row in rows:
            time.sleep(3)  # Respect rate limit
            cik = row['cik']
            url = row['mainlink']
            try:
                doc_resp = requests.get(url, headers=self.headers)
                doc_resp.raise_for_status()
                try:
                    soup = BeautifulSoup(doc_resp.text, 'lxml')
                except Exception:
                    soup = BeautifulSoup(doc_resp.text, 'html.parser')  # fallback
                for tag in soup(['script', 'style', 'head', 'title', 'meta', '[document]']):
                    tag.decompose()
                text = re.sub(r'\s+', ' ', soup.get_text(separator=' ')).strip()
                snippet = ' '.join(text.split()[:1000])

                prompt = (
                    f"Given this provided text: {snippet} "
                    "Tell me if this is an initial public offering, or something else like a SPAC merger. "
                    "If this is an IPO, tell me how many shares are being offered, and at what price. "
                    "The prices can be standalone, or if there is a range provide that range. "
                    "Also ask whether you can find an IPO date or week-of date; "
                    "if it's unclear, respond with 'unknown' for the IPO date. "
                    "Also ask if you can identify the ticker symbol; "
                    "if it's unclear, respond with 'unknown' for the ticker. "
                    "Also ask if you can identify the exchange; "
                    "if it's unclear, respond with 'unknown' for the exchange. "
                    "If both the total number of shares outstanding (after the IPO) and the share price are found, multiply them to compute the estimated market cap. "
                    "If the price is a range, use the midpoint of the range to estimate market cap. "
                    "If either the total shares outstanding or price is unknown, respond with 'unknown' for the market cap. "
                    "Format share_price so that if it's a range (e.g., between 20 and 25), you return '20$ - 25$'; and if it's a single value (e.g., 25), you return '25$'. "
                    "Your answer should be formatted into a JSON object. "
                    "The keys should be: "
                    "'IPO': 'yes or no', "
                    "'Shares Offered': 'shares offered in doc if possible, or unknown if not stated', "
                    "'share_price': 'Either state the price per share with $ suffix or unknown', "
                    "'estimated_ipo_date': 'Date or week-of date if found, or unknown', "
                    "'ticker': 'Ticker symbol if found, or unknown', "
                    "'exchange': 'Exchange if found, or unknown', "
                    "'market_cap': 'Total shares outstanding × share price (use midpoint if price is a range), or unknown if either is not found'. "
                    "Also try to find a link to the company's homepage from the text or context. "
                    "Return that link under the key 'logo_url'; if it is not found, return 'unknown'."
                )

                ai_resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )

                content = ai_resp.choices[0].message.content
                if content.strip().startswith("```json"):
                    content = content.strip().removeprefix("```json").removesuffix("```").strip()
                elif content.strip().startswith("```"):
                    content = content.strip().removeprefix("```").removesuffix("```").strip()
                print(f"\n{content}\n")
                parsed = json.loads(content)

                update_data = {
                    'is_ipo': parsed.get('IPO', '').lower() == 'yes',
                    'shares_offered': null_if_unknown_numeric(parsed.get('Shares Offered')),
                    'share_price': parsed.get('share_price', 'unknown'),  # still text
                    'estimated_ipo_date': null_if_unknown(parsed.get('estimated_ipo_date'), str),
                    'ticker': parsed.get('ticker', 'unknown'),
                    'exchange': parsed.get('exchange', 'unknown'),
                    'market_cap': null_if_unknown_numeric(parsed.get('market_cap')),
                    'logo_url': parsed.get('logo_url', 'unknown')
                }
                print(f"📤 Updating Supabase with:\n{json.dumps(update_data, indent=2)}\n")

                self.supabase.table('ipo').update(update_data).eq('cik', cik).execute()

            except Exception as e:
                print(f"⚠️ Analysis failed for {cik}: {e}")

if __name__ == '__main__':
    fetcher = S1Fetcher(rate_limit_seconds=0.5)
    three_months_ago = datetime.date.today() - datetime.timedelta(days=1)
    fetcher.fetch_and_push(three_months_ago.isoformat(), datetime.date.today().isoformat())
    fetcher.analyze_latest()
