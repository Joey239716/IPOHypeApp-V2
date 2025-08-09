import datetime
import re
from typing import Any, List
import requests

from ..config import settings
from ..utils.html import clean_html

# The daily master index file contains pipe-delimited rows after a header:
# CIK|Company Name|Form Type|Date Filed|Filename
# We'll parse it, filter to forms of interest, and (for initial forms) confirm IPO via doc text.

class DailyIndexChecker:
    BASE_TMPL = "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{qtr}/master.{ds}.idx"

    def __init__(self):
        self.session = requests.Session()
        self.headers = {"User-Agent": settings.USER_AGENT, "Accept": "text/plain"}

    @staticmethod
    def _qtr(month: int) -> int:
        return (month - 1) // 3 + 1

    @staticmethod
    def _adsh_from_filename(filename: str) -> str | None:
        # filename like: edgar/data/0000320193/0000320193-24-000066.txt
        try:
            last = filename.rsplit('/', 1)[-1]
            return last.replace('.txt', '')
        except Exception:
            return None

    def fetch_for_date(self, ds: str) -> List[dict[str, Any]]:
        # ds = YYYYMMDD
        y = int(ds[:4]); m = int(ds[4:6]); d = int(ds[6:8])
        url = self.BASE_TMPL.format(year=y, qtr=self._qtr(m), ds=ds)
        print(f"[DAILY] Fetching master index {url}")
        r = self.session.get(url, headers=self.headers, timeout=30)
        if r.status_code != 200:
            print(f"[DAILY] Index not found for {ds} (HTTP {r.status_code})")
            return []

        lines = r.text.splitlines()
        # Find header line
        try:
            start = next(i for i, line in enumerate(lines) if line.startswith("CIK|Company Name|Form Type|Date Filed|Filename")) + 1
        except StopIteration:
            print("[DAILY] Unexpected index format: header not found")
            return []

        filings: List[dict[str, Any]] = []
        for line in lines[start:]:
            if not line.strip():
                continue
            parts = line.split('|')
            if len(parts) < 5:
                continue
            cik, company, form, date_filed, filename = parts[:5]
            if form not in settings.FORMS:
                continue
            mainlink = f"https://www.sec.gov/Archives/{filename}"
            adsh = self._adsh_from_filename(filename)

            is_ipo = False
            if form in settings.INITIAL_FORMS:
                # Best-effort confirmation by scanning the filing text
                try:
                    rr = self.session.get(mainlink, headers=self.headers, timeout=30)
                    rr.raise_for_status()
                    text = rr.text
                    is_ipo = bool(re.search(r"initial public offering", clean_html(text), re.IGNORECASE))
                except Exception:
                    is_ipo = False

            filings.append({
                'cik': str(int(cik)) if cik else None,
                'company_name': company,
                'ticker': None,
                'form_type': form,
                'date_filed': date_filed,
                'mainlink': mainlink,
                'is_ipo': is_ipo,
                'analyzed': False,
                'accession_number': adsh,
            })
        return filings