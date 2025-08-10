import requests, re
from datetime import datetime
from supabase import create_client, Client
import os

BASE_URL = "https://api.nasdaq.com/api/ipo/calendar"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nasdaq.com/market-activity/ipos",
    "Origin": "https://www.nasdaq.com",
}

# Load Supabase credentials from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def normalize_date(v: str) -> str | None:
    """Convert mm/dd/yyyy to ISO, keep 'TBD'/'Week of ...' as-is."""
    if not v:
        return None
    v = re.sub(r"\s+", " ", v.strip())
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", v):
        try:
            return datetime.strptime(v, "%m/%d/%Y").date().isoformat()
        except Exception:
            return v
    return v

def fetch_upcoming():
    """Fetch upcoming IPO data from Nasdaq API for the current month."""
    month = datetime.now().strftime("%Y-%m")
    r = requests.get(BASE_URL, headers=HEADERS, params={"date": month}, timeout=30)
    r.raise_for_status()
    j = r.json()

    rows = (j.get("data", {})
              .get("upcoming", {})
              .get("upcomingTable", {})
              .get("rows", []))

    results = []
    for row in rows:
        company = (row.get("companyName") or "").strip()
        expected = normalize_date(row.get("expectedPriceDate"))
        if company:
            results.append({
                "company_name": company,
                "estimated_ipo_date": expected
            })
    return results

def upsert_to_supabase():
    """Upsert Nasdaq IPO estimated dates into the 'ipo' table without overwriting with TBD/week-of."""
    nasdaq_data = fetch_upcoming()
    print(f"✅ Found {len(nasdaq_data)} upcoming IPOs from Nasdaq")

    for ipo in nasdaq_data:
        # Get current value from DB
        current = supabase.table("ipo").select("estimated_ipo_date").eq("company_name", ipo["company_name"]).execute()
        current_date = current.data[0]["estimated_ipo_date"] if current.data else None

        new_date = ipo["estimated_ipo_date"]
        # Update only if empty or a new specific date
        if not current_date or (new_date and not str(new_date).lower().startswith("tbd") and new_date != current_date):
            print(f"Updating: {ipo['company_name']} → {new_date}")
            supabase.table("ipo").upsert(
                ipo,
                on_conflict="company_name"
            ).execute()
        else:
            print(f"Skipping: {ipo['company_name']} (current={current_date}, new={new_date})")

if __name__ == "__main__":
    upsert_to_supabase()
