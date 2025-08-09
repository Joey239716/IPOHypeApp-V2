import os
import hmac
import hashlib
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# --- Config ---
BUCKET_NAME = "logos"
LOGO_NAME_SALT = os.getenv("LOGO_NAME_SALT")  # must be in .env
if not LOGO_NAME_SALT:
    raise RuntimeError("Missing LOGO_NAME_SALT in env file")

# --- Setup ---
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing Supabase URL or Service Role Key")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bucket = supabase.storage.from_(BUCKET_NAME)

# --- Helper to make hashed filename ---
def object_name_for_cik(cik: str | int) -> str:
    msg = str(cik).encode()
    key = LOGO_NAME_SALT.encode()
    digest = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return f"{digest}.webp"

# --- Migration ---
def migrate_logo_urls():
    # Fetch all rows that have a logo_url (you could filter to only ones matching CIK pattern)
    resp = supabase.table("ipo").select("cik, logo_url").not_.is_("logo_url", None).execute()
    rows = resp.data or []
    print(f"Found {len(rows)} rows with logos to migrate.")

    for row in rows:
        cik = row["cik"]
        old_url = row["logo_url"]
        old_name = old_url.split("/")[-1]  # filename from old URL

        new_name = object_name_for_cik(cik)
        if old_name == new_name:
            print(f"Skipping CIK {cik}, already hashed.")
            continue

        print(f"CIK {cik}: {old_name} -> {new_name}")

        try:
            # Download old file
            file_bytes = bucket.download(old_name)
        except Exception as e:
            print(f"❌ Failed to download old file for CIK {cik}: {e}")
            continue

        try:
            # Upload with new name (overwrite if exists)
            bucket.upload(new_name, file_bytes, {"content-type": "image/webp"})
        except Exception as e:
            print(f"❌ Failed to upload new file for CIK {cik}: {e}")
            continue

        try:
            # Delete old file
            bucket.remove([old_name])
        except Exception as e:
            print(f"⚠️ Could not delete old file for CIK {cik}: {e}")

        # Get public URL for new file
        public_url = bucket.get_public_url(new_name)
        if isinstance(public_url, dict):
            public_url = public_url.get("publicUrl") or public_url.get("public_url")

        # Update database
        try:
            supabase.table("ipo").update({"logo_url": public_url}).eq("cik", cik).execute()
            print(f"✅ Updated DB for CIK {cik} -> {public_url}")
        except Exception as e:
            print(f"❌ Failed to update DB for CIK {cik}: {e}")

if __name__ == "__main__":
    migrate_logo_urls()
