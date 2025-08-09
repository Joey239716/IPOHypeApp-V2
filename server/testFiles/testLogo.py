import os
import re
import datetime
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv
from supabase import create_client

# -------------------------------
# Config
# -------------------------------
BUCKET_NAME = "logos"  # your actual Supabase Storage bucket name
HTTP_TIMEOUT = 10
LOGO_SIZE = (32, 32)

# -------------------------------
# Setup
# -------------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # MUST be service role for bucket upload
LOGO_DEV_SECRET_KEY = os.getenv("LOGO_DEV_KEY")

if not (SUPABASE_URL and SUPABASE_KEY and LOGO_DEV_SECRET_KEY):
    raise RuntimeError("Missing required env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, or LOGO_DEV_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
session = requests.Session()

# -------------------------------
# Helpers
# -------------------------------
def clean_company_name(name: str) -> str:
    original = name
    name = name.lower().replace("&", " and ")
    name = re.sub(r"[.,'()/]", " ", name)
    name = re.sub(r"[-_]", " ", name)
    keywords = (
        "inc|incorporated|corp|corporation|company|co|ltd|limited|llc|plc|"
        "holdco|holding|holdings|mgmt|management|group|trust|"
        "partner|partners|capital|capitals|venture|ventures|"
        "acquisition|acquisitions|spac|etf|fund|"
        "gmbh|s\\.a\\.|s\\.a|n\\.v\\.|n\\.v|b\\.v\\.|b\\.v|a/s|ab|ag|nv|bv|"
        "sarl|spa|pty|oyj|kk|sas|llp|lp"
    )
    name = re.sub(rf"\b({keywords})\b", " ", name)
    name = re.sub(r"\b(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b$", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    print(f"🧹 Cleaned '{original}' to '{name}'")
    return name

def search_logo(original_name: str, cleaned_name: str):
    candidates = []
    if original_name and original_name.strip():
        candidates.append(original_name.strip())
    if cleaned_name and cleaned_name.strip():
        candidates.append(cleaned_name.strip())
    parts = cleaned_name.split()
    if len(parts) > 2:
        candidates.append(" ".join(parts[:2]))
    seen = set()
    candidates = [c for c in candidates if not (c in seen or seen.add(c))]

    url = "https://api.logo.dev/search"
    headers = {"Authorization": f"Bearer {LOGO_DEV_SECRET_KEY}"}

    for q in candidates:
        try:
            resp = session.get(url, headers=headers, params={"q": q}, timeout=HTTP_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            if data and isinstance(data, list):
                for item in data:
                    domain = item.get("domain")
                    if domain:
                        print(f"🔎 Query '{q}' → domain: {domain}")
                        return domain
            print(f"ℹ️ Query '{q}' returned no domain")
        except requests.exceptions.RequestException as e:
            print(f"❌ Query '{q}' failed: {e}")
    return None

def download_and_resize_to_webp(domain: str, size=LOGO_SIZE) -> bytes | None:
    img_url = f"https://img.logo.dev/{domain}?token={LOGO_DEV_SECRET_KEY}"
    try:
        r = session.get(img_url, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        img = img.resize(size, Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=80)
        return buf.getvalue()
    except Exception as e:
        print(f"❌ Failed to download/resize for {domain}: {e}")
        return None

def upload_webp(image_bytes: bytes, object_name: str) -> str | None:
    """Upload to Supabase Storage and return public URL."""
    bucket = supabase.storage.from_(BUCKET_NAME)
    try:
        bucket.upload(object_name, image_bytes, {"content-type": "image/webp"})
    except Exception as e:
        msg = str(e).lower()
        if "exists" in msg or "already" in msg or "conflict" in msg:
            try:
                if hasattr(bucket, "update"):
                    bucket.update(object_name, image_bytes, {"content-type": "image/webp"})
                else:
                    bucket.remove([object_name])
                    bucket.upload(object_name, image_bytes, {"content-type": "image/webp"})
            except Exception as e2:
                print(f"❌ Failed to overwrite upload: {e2}")
                return None
        else:
            print(f"❌ Upload failed: {e}")
            return None

    try:
        public_url = bucket.get_public_url(object_name)
        if isinstance(public_url, dict):
            public_url = public_url.get("publicUrl") or public_url.get("public_url")
        return public_url
    except Exception as e:
        print(f"❌ Failed to get public URL: {e}")
        host = SUPABASE_URL.split("//")[1]
        return f"https://{host}/storage/v1/object/public/{BUCKET_NAME}/{object_name}"

# -------------------------------
# Main job
# -------------------------------
def update_company_logos():
    resp = supabase.table("ipo").select("cik, company_name").is_("updated_logo_date", None).execute()
    rows = resp.data or []
    print(f"Found {len(rows)} rows to update.")

    for row in rows:
        company_name = row.get("company_name")
        cik = row.get("cik")
        if not company_name or cik is None:
            continue

        cleaned = clean_company_name(company_name)
        domain = search_logo(company_name, cleaned)
        if not domain:
            print(f"⚠️ No domain found for {company_name}")
            continue

        webp_bytes = download_and_resize_to_webp(domain)
        if not webp_bytes:
            print(f"⚠️ Could not prepare image for {company_name}")
            continue

        object_name = f"{str(cik)}.webp"
        public_url = upload_webp(webp_bytes, object_name)
        if not public_url:
            print(f"⚠️ Upload failed for {company_name}")
            continue

        today = datetime.date.today().isoformat()
        supabase.table("ipo").update({
            "logo_url": public_url,
            "updated_logo_date": today
        }).eq("cik", cik).execute()
        print(f"✅ Updated {company_name}: {public_url} (date {today})")

if __name__ == "__main__":
    update_company_logos()
