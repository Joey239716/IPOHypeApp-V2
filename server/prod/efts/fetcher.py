import re
import time
import datetime
from typing import Any
import requests

from ..config import settings
from ..utils.html import clean_html

IPO_REGEX = re.compile(r"\binitial public offering\b", re.IGNORECASE)

class EFTSFetcher:
    BASE_URL = "https://efts.sec.gov/LATEST/search-index"

    def __init__(self, user_agent: str | None = None):
        self.headers = {"User-Agent": user_agent or settings.USER_AGENT, "Accept": "application/json"}
        self.session = requests.Session()

    @staticmethod
    def normalize_cik(cik: str | None) -> str | None:
        if not cik:
            return None
        return str(int(cik))

    @staticmethod
    def extract_name_and_ticker(display_name: str | None) -> tuple[str, str | None]:
        display_name = display_name or ""
        cik_match = re.search(r"\s+\(CIK\s*\d+\)$", display_name)
        base = display_name[:cik_match.start()] if cik_match else display_name
        ticker_match = re.search(r"\s+\(([^)]+)\)\s*$", base)
        if ticker_match:
            first_ticker = ticker_match.group(1).split(",")[0].strip()
            company = base[:ticker_match.start()].strip()
            return company, first_ticker
        return base.strip(), None

    def fetch(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        print(f"[INFO] Fetching filings from {start_date} to {end_date} by form type")
        all_filings: list[dict[str, Any]] = []

        for form_type in settings.FORMS:
            offset = 0
            print(f"[INFO] Querying form {form_type}")
            while True:
                params = [
                    ("dateRange", "custom"),
                    ("startdt", start_date),
                    ("enddt", end_date),
                    ("forms", form_type),
                    ("from", offset),
                    ("size", settings.PAGE_SIZE),
                ]

                retries = 0
                while retries < settings.MAX_RETRIES:
                    try:
                        resp = self.session.get(self.BASE_URL, headers=self.headers, params=params, timeout=30)
                        print("[QUERY]", resp.url)
                        resp.raise_for_status()
                        data = resp.json()
                        break
                    except Exception as e:
                        retries += 1
                        print(f"[WARN] Retry {retries}/{settings.MAX_RETRIES} for {form_type} offset {offset}: {e}")
                        time.sleep(settings.RATE_LIMIT * (2 ** retries))
                else:
                    print("[ERROR] Max retries exceeded—stopping form fetch.")
                    break

                hits = data.get("hits", {}).get("hits", [])
                if not hits:
                    print(f"[INFO] No more {form_type} filings.")
                    break

                for hit in hits:
                    src = hit.get("_source", {})
                    cik = self.normalize_cik((src.get("ciks") or [None])[0])
                    adsh = src.get("adsh")
                    display_name = (src.get("display_names") or [""])[0]
                    company_name, ticker = self.extract_name_and_ticker(display_name)

                    link = None
                    if adsh and cik:
                        adsh_nodash = adsh.replace("-", "")
                        link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh_nodash}/{adsh}.txt"

                    ipo_detected = False
                    if form_type in settings.INITIAL_FORMS and link:
                        try:
                            r = self.session.get(link, headers=self.headers, timeout=30, stream=True)
                            r.raise_for_status()
                            buffer = ""
                            for chunk in r.iter_content(8192, decode_unicode=True):
                                buffer += chunk
                                if len(buffer) > 200000:
                                    break
                            if IPO_REGEX.search(clean_html(buffer)):
                                ipo_detected = True
                                print(f"[INFO] IPO detected in {form_type} for {company_name} ({ticker})")
                        except Exception as e:
                            print(f"[ERROR] Failed to fetch text for {company_name}: {e}")

                    all_filings.append({
                        'cik': cik,
                        'company_name': company_name,
                        'ticker': ticker,
                        'form_type': form_type,
                        'date_filed': (src.get('file_date') or '')[:10],
                        'mainlink': link or f"https://www.sec.gov/Archives/{src.get('file_name')}",
                        'is_ipo': ipo_detected,
                        'analyzed': False,
                        'accession_number': adsh,
                    })

                if len(hits) < settings.PAGE_SIZE:
                    break
                offset += settings.PAGE_SIZE
                time.sleep(settings.RATE_LIMIT)

        all_filings.sort(key=lambda f: (f['date_filed'], f['accession_number'] or ''), reverse=False)
        return all_filings