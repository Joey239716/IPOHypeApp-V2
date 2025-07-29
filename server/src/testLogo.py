import time
import datetime
import requests
from bs4 import BeautifulSoup
import re

FORMS = "S-1,F-1,S-1/A,F-1/A,424B1,424B4,S-1MEF,F-1MEF,RW"
LIMIT_WORDS = 2000
BYTE_CHUNK_SIZE = 8192  # ~8KB chunks

IPO_REGEX = re.compile(r"\binitial public offering\b", re.IGNORECASE)

class EFTSFetcher:
    def __init__(self, user_agent="joeydaspam@gmail.com", rate_limit=0.5, max_retries=3):
        self.headers = {"User-Agent": user_agent, "Accept": "application/json"}
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.results = []  # store results for summary

    def clean_html(self, raw_html):
        """Remove tags & ensure proper spacing."""
        soup = BeautifulSoup(raw_html, "html.parser")

        # Remove non-text elements
        for tag in soup(["script", "style", "head", "meta", "title"]):
            tag.decompose()

        # Extract text with spacing
        text = soup.get_text(separator=" ")

        # Normalize spaces
        return ' '.join(text.split())

    def fetch(self, date):
        print(f"Fetching filings for {date} using EFTS JSON")
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
                return

            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                print("No filings returned by EFTS.")
                return

            for i, hit in enumerate(hits, start=1):
                src = hit.get("_source", {})
                form = src.get("file_type") or src.get("form") or src.get("formType")
                cik = src.get("ciks", [None])[0]
                adsh = src.get("adsh")
                company = src.get("display_names", [None])[0]

                link = None
                if adsh and cik:
                    try:
                        cik_stripped = str(int(cik))
                        adsh_nodash = adsh.replace("-", "")
                        link = f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{adsh_nodash}/{adsh}.txt"
                    except Exception:
                        link = None

                print(f"\n[{i}] {company} ({form}) - CIK {cik}")
                ipo_detected = False
                if link:
                    try:
                        r = requests.get(link, headers=self.headers, timeout=30, stream=True)
                        r.raise_for_status()

                        buffer = ""
                        for chunk in r.iter_content(BYTE_CHUNK_SIZE, decode_unicode=True):
                            buffer += chunk
                            if len(buffer) > 200000:  # stop early (~200KB)
                                break

                        cleaned_text = self.clean_html(buffer)
                        words = cleaned_text.split()
                        snippet = ' '.join(words[:LIMIT_WORDS])

                        if IPO_REGEX.search(snippet):
                            ipo_detected = True

                        print(f"--- First {LIMIT_WORDS} words (cleaned) ---")
                        print(snippet)
                        print("-" * 80)

                    except Exception as e:
                        print(f"Failed to fetch filing text: {e}")
                else:
                    print("No link available for this filing.")

                # Save result for summary
                self.results.append({
                    "company": company,
                    "form": form,
                    "cik": cik,
                    "ipo_detected": ipo_detected
                })

            if len(hits) < params["size"]:
                break

            params["from"] += params["size"]
            time.sleep(self.rate_limit)

    def print_summary(self):
        print("\n========== IPO DETECTION SUMMARY ==========")
        for result in self.results:
            status = "✅ IPO detected" if result["ipo_detected"] else "❌ Not an IPO"
            print(f"{result['company']} ({result['form']}, CIK {result['cik']}): {status}")
        print("==========================================")

if __name__ == '__main__':
    fetcher = EFTSFetcher()
    today = datetime.date.today().isoformat()
    fetcher.fetch(today)
    fetcher.print_summary()
