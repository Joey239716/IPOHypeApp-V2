from __future__ import annotations

import re
import time
from typing import Any, Iterable
import requests

from ..config import settings
from ..utils.html import clean_html

IPO_REGEX = re.compile(r"\binitial public offering\b", re.IGNORECASE)


class EFTSFetcher:
    BASE_URL = "https://efts.sec.gov/LATEST/search-index"

    def __init__(self, user_agent: str | None = None) -> None:
        self.headers = {
            "User-Agent": user_agent or settings.USER_AGENT,
            "Accept": "application/json",
        }
        self.session = requests.Session()

    @staticmethod
    def normalize_cik(cik: str | None) -> str | None:
        if not cik:
            return None
        # remove leading zeros by coercing to int, then back to str
        return str(int(cik))

    @staticmethod
    def extract_name_and_ticker(display_name: str | None) -> tuple[str, str | None]:
        """
        EFTS display_name looks like:
          "Bullish  (BLSH)  (CIK 0001872195)"
        Return ("Bullish", "BLSH")  or ("Bullish", None) if no ticker.
        """
        display_name = display_name or ""
        # Trim trailing "(CIK NNNNNNN)" if present
        cik_match = re.search(r"\s+\(CIK\s*\d+\)\s*$", display_name)
        base = display_name[:cik_match.start()] if cik_match else display_name
        # Extract the final "(TICKER)" if present
        ticker_match = re.search(r"\s+\(([^)]+)\)\s*$", base)
        if ticker_match:
            first_ticker = ticker_match.group(1).split(",")[0].strip()
            company = base[:ticker_match.start()].strip()
            return company, first_ticker
        return base.strip(), None

    def _iter_form_hits(
        self,
        form_type: str,
        start_date: str,
        end_date: str,
    ) -> Iterable[dict[str, Any]]:
        """Generator over EFTS 'hits' for a given form_type and date range, with paging + retries."""
        offset = 0
        while True:
            params = [
                ("dateRange", "custom"),
                ("startdt", start_date),
                ("enddt", end_date),
                ("forms", form_type),
                ("from", offset),
                ("size", settings.PAGE_SIZE),
            ]
            print(f"[INFO] Querying form {form_type}")
            retries = 0
            while retries < settings.MAX_RETRIES:
                try:
                    resp = self.session.get(
                        self.BASE_URL, headers=self.headers, params=params, timeout=30
                    )
                    print("[QUERY]", resp.url)
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except Exception as e:
                    retries += 1
                    print(f"[WARN] Retry {retries}/{settings.MAX_RETRIES} for {form_type} offset {offset}: {e}")
                    time.sleep(settings.RATE_LIMIT * (2**retries))
            else:
                print("[ERROR] Max retries exceeded—stopping form fetch.")
                return

            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                print(f"[INFO] No more {form_type} filings.")
                return

            for hit in hits:
                yield hit

            if len(hits) < settings.PAGE_SIZE:
                return

            offset += settings.PAGE_SIZE
            time.sleep(settings.RATE_LIMIT)

    def fetch(
        self,
        start_date: str,
        end_date: str,
        existing_ciks: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch filings from EFTS for a given date range and return a filtered list.
        IMPORTANT: If `existing_ciks` is provided, we will:
          - SKIP fetching/parsing S-1 / F-1 text entirely for those CIKs (early bail).
          - Still include S-1/A and F-1/A for those CIKs (so amendments flow through).
        """
        existing_ciks = {str(int(c)) for c in (existing_ciks or set()) if c is not None}

        print(f"[INFO] Fetching filings from {start_date} to {end_date} by form type")
        all_filings: list[dict[str, Any]] = []

        for form_type in settings.FORMS:
            for hit in self._iter_form_hits(form_type, start_date, end_date):
                src = hit.get("_source", {}) or {}
                cik = self.normalize_cik((src.get("ciks") or [None])[0])
                adsh = src.get("adsh")
                display_name = (src.get("display_names") or [""])[0]
                company_name, maybe_ticker = self.extract_name_and_ticker(display_name)

                # Build a safe link:
                # Prefer the raw TXT (guaranteed), fall back to Archives/file_name if present.
                link = None
                if adsh and cik:
                    adsh_nodash = adsh.replace("-", "")
                    link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh_nodash}/{adsh}.txt"
                fallback = src.get("file_name")
                mainlink = link or (f"https://www.sec.gov/Archives/{fallback}" if fallback else None)

                # Early skip for **initial forms** already in DB (no .txt request, no regex)
                if form_type in settings.INITIAL_FORMS and cik and cik in existing_ciks:
                    print(f"[SKIP-FETCH] Initial {form_type} for {company_name} ({maybe_ticker}) — already tracked; skipping SEC text fetch.")
                    continue

                ipo_detected = False
                # Only do regex detection on initial forms we haven't seen before
                if form_type in settings.INITIAL_FORMS and link:
                    try:
                        r = self.session.get(link, headers=self.headers, timeout=30, stream=True)
                        r.raise_for_status()
                        buffer = ""
                        for chunk in r.iter_content(8192, decode_unicode=True):
                            buffer += chunk
                            if len(buffer) > 200_000:  # ~200KB is usually enough for phrase detection
                                break
                        if IPO_REGEX.search(clean_html(buffer)):
                            ipo_detected = True
                        else:
                            # For visibility: log non-IPO initial forms here
                            print(f"[SKIP-FETCH] {form_type} for {company_name} ({maybe_ticker}) — regex did not find IPO phrasing.")
                            # We still append the record with is_ipo=False so pipeline can decide.
                    except Exception as e:
                        print(f"[ERROR] Failed to fetch text for {company_name}: {e}")

                all_filings.append(
                    {
                        "cik": cik,
                        "company_name": company_name,
                        "ticker": maybe_ticker,
                        "form_type": form_type,
                        "date_filed": (src.get("file_date") or "")[:10],
                        "mainlink": mainlink,
                        "is_ipo": ipo_detected,
                        "analyzed": False,
                        "accession_number": adsh,
                        # Pass through primary document if present so pipeline can construct HTML URL if needed
                        "primary_document": src.get("primary_document"),
                    }
                )

        # Return in ascending date order (oldest first)
        all_filings.sort(key=lambda f: (f["date_filed"], f.get("accession_number") or ""), reverse=False)
        return all_filings
