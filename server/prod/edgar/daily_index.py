# prod/edgar/daily_index.py
from __future__ import annotations

import re
from typing import Any, List, Optional

import requests

from ..config import settings
from ..utils.html import clean_html


class DailyIndexChecker:
    """
    Parse the SEC master daily index:
      https://www.sec.gov/Archives/edgar/daily-index/{YYYY}/QTR{q}/master.{YYYYMMDD}.idx

    Output records match EFTS fetcher so Pipeline can process uniformly:
      {
        'cik': '0000123456',
        'company_name': 'Example Corp',
        'ticker': None,                     # not in master index
        'form_type': 'S-1',
        'date_filed': '2025-08-07',         # ISO (YYYY-MM-DD)
        'mainlink': 'https://www.sec.gov/Archives/.../0000123456-25-000001.txt',
        'is_ipo': True/False,               # confirmed for initial forms by scanning text
        'analyzed': False,
        'accession_number': '0000123456-25-000001',
      }
    """

    BASE_TMPL = "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{qtr}/master.{ds}.idx"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.headers = {"User-Agent": settings.USER_AGENT, "Accept": "text/plain"}

    @staticmethod
    def _qtr(month: int) -> int:
        return (month - 1) // 3 + 1

    @staticmethod
    def _adsh_from_filename(filename: str) -> Optional[str]:
        # example filename: edgar/data/0000320193/0000320193-24-000066.txt
        try:
            last = filename.rsplit("/", 1)[-1]
            return last.replace(".txt", "")
        except Exception:
            return None

    def fetch_for_date(self, ds: str) -> List[dict[str, Any]]:
        """
        ds: 'YYYYMMDD' (Eastern calendar day you want to reconcile)
        """
        y = int(ds[:4])
        m = int(ds[4:6])
        url = self.BASE_TMPL.format(year=y, qtr=self._qtr(m), ds=ds)
        print(f"[DAILY] Fetching master index {url}")

        r = self.session.get(url, headers=self.headers, timeout=settings.HTTP_TIMEOUT)
        if r.status_code != 200:
            print(f"[DAILY] Index not found for {ds} (HTTP {r.status_code})")
            return []

        ctype = (r.headers.get("Content-Type") or "").lower()
        text = r.text

        # If we got HTML, likely throttled or missing/weak User-Agent
        if "text/plain" not in ctype and text.lstrip().startswith("<"):
            preview = text[:200].replace("\n", " ")
            print("[DAILY] Got HTML instead of text/plain (throttled or invalid User-Agent). Preview:")
            print(preview)
            return []

        # Strip BOM if present and normalize lines
        if text and text[0] == "\ufeff":
            text = text.lstrip("\ufeff")
        lines = [ln.rstrip("\r\n") for ln in text.splitlines()]

        # Find the header line flexibly (accept both "Filename" and "File Name")
        header_idx = -1
        for i, ln in enumerate(lines):
            h = " ".join(ln.strip().lower().split())
            if "cik|company name|form type|date filed|filename" in h or \
               "cik|company name|form type|date filed|file name" in h:
                header_idx = i
                break

        if header_idx == -1:
            preview = "\n".join(lines[:20])
            print("[DAILY] Unexpected index format: header not found. First 20 lines preview:")
            print(preview)
            return []

        start = header_idx + 1  # data starts after header
        filings: List[dict[str, Any]] = []

        for line in lines[start:]:
            if not line.strip():
                continue
            if set(line.strip()) == {"-"}:  # skip dashed separator line
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 5:
                continue

            cik, company, form, date_filed_raw, filename = parts[:5]
            if form not in settings.FORMS:
                continue

            # Convert YYYYMMDD -> YYYY-MM-DD when possible
            if len(date_filed_raw) == 8 and date_filed_raw.isdigit():
                date_filed = f"{date_filed_raw[:4]}-{date_filed_raw[4:6]}-{date_filed_raw[6:]}"
            else:
                date_filed = date_filed_raw

            mainlink = f"https://www.sec.gov/Archives/{filename}"
            adsh = self._adsh_from_filename(filename)

            # For initial forms, confirm IPO language in the doc (best-effort)
            is_ipo = False
            if form in settings.INITIAL_FORMS:
                try:
                    rr = self.session.get(
                        mainlink,
                        headers=self.headers,
                        timeout=settings.HTTP_TIMEOUT,
                    )
                    rr.raise_for_status()
                    is_ipo = bool(
                        re.search(r"\binitial public offering\b", clean_html(rr.text), re.IGNORECASE)
                    )
                except Exception:
                    is_ipo = False

            filings.append(
                {
                    "cik": str(int(cik)) if cik else None,
                    "company_name": company,
                    "ticker": None,
                    "form_type": form,
                    "date_filed": date_filed,  # ISO
                    "mainlink": mainlink,
                    "is_ipo": is_ipo,
                    "analyzed": False,
                    "accession_number": adsh,
                }
            )

        return filings
