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

FORMS = "S-1,F-1,S-1/A,F-1/A,424B1,424B4,S-1MEF,F-1MEF,RW"
INITIAL_FORMS = {"S-1", "F-1"}
LIMIT_WORDS = 2000
BYTE_CHUNK_SIZE = 8192
IPO_REGEX = re.compile(r"\binitial public offering\b", re.IGNORECASE)


def normalize_cik(cik):
    """Normalize CIKs to strip leading zeros so DB and SEC match."""
    if not cik:
        return None
    return str(int(cik))


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
        text = soup.get_text(separator=" ")
        return " ".join(text.split())

    def fetch(self, start_date, end_date):
        print(f"[INFO] Fetching filings from {start_date} to {end_date} using EFTS JSON")
        filings = []
        base_url = "https://efts.sec.gov/LATEST/search-index"

        params = {
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date,
            "forms": FORMS,
            "from": 0,
            "size": 100,
        }

        while True:
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
                    print(f"[WARN] Retry {retries}/{self.max_retries} failed for offset {params['from']}: {e}")
                    time.sleep(self.rate_limit * (2**retries))
            else:
                print("[ERROR] Max retries exceeded, stopping fetch.")
                break

            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                print("[INFO] No filings returned by EFTS.")
                break

            for hit in hits:
                src = hit.get("_source", {})
                form = src.get("file_type") or src.get("form") or src.get("formType")
                cik = normalize_cik(src.get("ciks", [None])[0])
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

                ipo_detected = False
                if form in INITIAL_FORMS and link:
                    try:
                        r = requests.get(link, headers=self.headers, timeout=30, stream=True)
                        r.raise_for_status()
                        buffer = ""
                        for chunk in r.iter_content(BYTE_CHUNK_SIZE, decode_unicode=True):
                            buffer += chunk
                            if len(buffer) > 200000:
                                break

                        cleaned_text = self.clean_html(buffer)
                        words = cleaned_text.split()
                        snippet = " ".join(words[:LIMIT_WORDS])

                        if IPO_REGEX.search(snippet):
                            ipo_detected = True
                            print(f"[INFO] IPO language detected in {form} for {company} (CIK {cik})")
                        else:
                            print(f"[INFO] IPO language NOT found in {form} for {company} (CIK {cik})")
                    except Exception as e:
                        print(f"[ERROR] Failed to fetch filing text for {company} (CIK {cik}): {e}")

                filings.append(
                    {
                        "cik": cik,
                        "company_name": company,
                        "form_type": form,
                        "date_filed": src.get("file_date", "")[:10],
                        "mainlink": link or f"https://www.sec.gov/Archives/{src.get('file_name') or src.get('fileName')}",
                        "is_ipo": ipo_detected,
                        "analyzed": False,
                        "accession_number": adsh,
                    }
                )

            if len(hits) < params["size"]:
                break

            params["from"] += params["size"]
            time.sleep(self.rate_limit)

        # Sort filings by date then accession number
        filings.sort(key=lambda f: (f["date_filed"], f["accession_number"] or ""), reverse=False)
        return filings

    def fetch_and_push(self, start_date, end_date):
        filings = self.fetch(start_date, end_date)
        if not filings:
            print("[INFO] No filings to insert.")
            return

        resp = self.supabase.table("ipo").select(
            "cik", "latest_filing_date", "latest_filing_type", "is_ipo"
        ).execute()
        active_rows = {normalize_cik(r["cik"]): r for r in (resp.data or [])}

        for f in filings:
            cik = f["cik"]
            form = f["form_type"]
            new_date = f["date_filed"]
            new_acc = f["accession_number"]
            existing_row = active_rows.get(cik)

            if not existing_row and form not in INITIAL_FORMS:
                print(f"[SKIP] {form} for {f['company_name']} (CIK {cik}) skipped — no initial filing on record")
                continue

            if form in INITIAL_FORMS:
                if not f["is_ipo"]:
                    print(f"[SKIP] Skipping {form} for CIK {cik} — IPO not detected")
                    continue
                print(f"[UPSERT] New IPO filing {form} for {f['company_name']} (CIK {cik})")
            elif form in {"424B1", "424B4"}:
                if existing_row:
                    try:
                        self.supabase.table("ipo").delete().eq("cik", cik).execute()
                        pub = {
                            "cik": cik,
                            "company_name": f["company_name"],
                            "effective_date": new_date,
                            "form_type": form,
                            "document_url": f["mainlink"],
                            "accession_number": f["accession_number"],
                        }
                        self.supabase.table("public_companies").upsert(pub, on_conflict="cik").execute()
                        print(
                            f"[MOVE] Moved {f['company_name']} (CIK {cik}) to public_companies after {form} "
                            f"with accession_number {pub['accession_number']}"
                        )
                    except APIError as err:
                        print(f"[ERROR] Failed to move {cik} to public_companies: {err}")
                continue
            elif form == "RW":
                if existing_row:
                    try:
                        self.supabase.table("ipo").delete().eq("cik", cik).execute()
                        print(f"[DELETE] Removed {f['company_name']} (CIK {cik}) from ipo after withdrawal (RW)")
                    except APIError as err:
                        print(f"[ERROR] Failed to delete RW for {cik}: {err}")
                continue
            else:
                if not existing_row:
                    print(f"[SKIP] {form} for {f['company_name']} (CIK {cik}) skipped — no initial filing on record")
                    continue
                print(f"[UPSERT] Amendment {form} for {f['company_name']} (CIK {cik})")

            # Date-only check since accession_number may be null in DB
            if existing_row:
                existing_date = existing_row.get("latest_filing_date")

                if existing_date == new_date:
                    print(
                        f"[INFO] Filing {form} for {f['company_name']} (CIK {cik}) "
                        f"is on the same date as existing {existing_date}, updating anyway."
                    )

            rec = {
                "cik": cik,
                "company_name": f["company_name"],
                "latest_filing_type": form,
                "latest_filing_date": new_date,
                "mainlink": f["mainlink"],
                "is_ipo": True,
                "analyzed": False,
                "accession_number": new_acc,
            }

            try:
                self.supabase.table("ipo").upsert(rec, on_conflict="cik").execute()
                print(
                    f"[SUCCESS] Upserted filing for {f['company_name']} (CIK {cik}) "
                    f"with accession {new_acc} and set analyzed=False"
                )
                active_rows[cik] = rec
            except APIError as err:
                print(f"[ERROR] Upsert failed for {cik}: {err}")


if __name__ == "__main__":
    fetcher = EFTSFetcher()
    today = datetime.date.today().isoformat()
    fetcher.fetch_and_push(today, today)
