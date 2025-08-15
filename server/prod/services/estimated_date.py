# prod/services/estimated_date.py
from __future__ import annotations

import os
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from dotenv import load_dotenv
from supabase import create_client, Client

BASE_URL = "https://api.nasdaq.com/api/ipo/calendar"
HEADERS = {
    # Keep a modern UA; Nasdaq can be picky
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nasdaq.com/market-activity/ipos",
    "Origin": "https://www.nasdaq.com",
}

# --- Load env early (prod/.env first, then CWD). OS envs win (override=False). ---
load_dotenv(dotenv_path=(Path(__file__).resolve().parents[1] / ".env"), override=False)
load_dotenv(override=False)

# --- Supabase credentials (match your config.py naming) ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")  # IMPORTANT: service role key

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in environment.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def normalize_date(v: Optional[str]) -> Optional[str]:
    """
    Convert 'mm/dd/yyyy' to ISO 'YYYY-MM-DD'.
    Keep non-specific texts like 'TBD' or 'Week of ...' as-is.
    """
    if not v:
        return None
    v = re.sub(r"\s+", " ", v.strip())

    # Strict US date like 08/12/2025
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", v):
        try:
            return datetime.strptime(v, "%m/%d/%Y").date().isoformat()
        except Exception:
            return v  # fallback to original on parse failure

    # Any non-specific text (e.g., TBD, Week of ...)
    return v


def is_specific_date(val: Optional[str]) -> bool:
    """True if the value is a concrete ISO date like 2025-08-12."""
    if not val:
        return False
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(val)))


def fetch_upcoming() -> List[Dict[str, Optional[str]]]:
    """Fetch upcoming IPOs from Nasdaq for the current month."""
    month = datetime.now().strftime("%Y-%m")
    r = requests.get(
        BASE_URL,
        headers=HEADERS,
        params={"date": month},
        timeout=30,
    )
    r.raise_for_status()

    try:
        j = r.json()
    except Exception as e:
        raise RuntimeError(f"Nasdaq API did not return JSON: {e}")

    rows = (
        j.get("data", {})
         .get("upcoming", {})
         .get("upcomingTable", {})
         .get("rows", [])
    )

    results: List[Dict[str, Optional[str]]] = []
    for row in rows:
        company = (row.get("companyName") or "").strip()
        expected = normalize_date(row.get("expectedPriceDate"))
        if company:
            results.append({
                "company_name": company,
                "estimated_ipo_date": expected or None,
            })
    return results


def upsert_to_supabase() -> None:
    """
    Update 'ipo.estimated_ipo_date' using Nasdaq data.

    Rules:
      - If the company is NOT already in 'ipo', SKIP (we require CIK there).
      - If DB has no date, write whatever Nasdaq has (including TBD/week-of).
      - If DB has TBD/week-of and Nasdaq provides a concrete date, upgrade.
      - If DB has a concrete date, only update if Nasdaq gives a DIFFERENT concrete date.
      - Never downgrade a concrete date to TBD/week-of.
    """
    print("=== Updating estimated IPO dates from Nasdaq ===")
    data = fetch_upcoming()
    print(f"✅ Found {len(data)} upcoming IPOs from Nasdaq")

    for item in data:
        company = item["company_name"]
        new_date = item["estimated_ipo_date"]

        # Ensure company exists in 'ipo' (so we don't violate NOT NULL CIK)
        exists_resp = supabase.table("ipo").select("estimated_ipo_date").eq("company_name", company).limit(1).execute()
        if not exists_resp.data:
            print(f"[SKIP/NO-INSERT] {company}: not in 'ipo' table (requires CIK).")
            continue

        current_date = exists_resp.data[0]["estimated_ipo_date"]

        cur_specific = is_specific_date(current_date)
        new_specific = is_specific_date(new_date)

        do_update = False
        reason = ""

        if current_date is None:
            do_update = True
            reason = "no current date"
        elif not cur_specific and new_specific:
            do_update = True
            reason = "upgrade TBD/week-of -> concrete date"
        elif cur_specific and new_specific and new_date != current_date:
            do_update = True
            reason = "change concrete date"

        if do_update:
            print(f"[UPDATE] {company}: {current_date} -> {new_date} ({reason})")
            supabase.table("ipo").update(
                {"estimated_ipo_date": new_date}
            ).eq("company_name", company).execute()
        else:
            print(f"[SKIP]   {company}: keep {current_date} (new={new_date})")


if __name__ == "__main__":
    upsert_to_supabase()
