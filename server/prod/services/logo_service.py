import re
import hmac
import hashlib
import datetime
from io import BytesIO
from typing import Optional
import requests
from PIL import Image

from ..config import settings
from .db import Database

IPO_SUFFIXES = (
    "inc", "incorporated", "corp", "corporation", "company", "co", "ltd", "limited", "llc", "plc",
    "holdco", "holding", "holdings", "mgmt", "management", "group", "trust",
    "partner", "partners", "capital", "capitals", "venture", "ventures",
    "acquisition", "acquisitions", "spac", "etf", "fund",
    "gmbh", "s.a.", "s.a", "n.v.", "n.v", "b.v.", "b.v", "a/s", "ab", "ag", "nv", "bv",
    "sarl", "spa", "pty", "oyj", "kk", "sas", "llp", "lp",
)

SUFFIX_RE = re.compile(rf"\b({'|'.join(map(re.escape, IPO_SUFFIXES))})\b", re.IGNORECASE)
ROMAN_RE = re.compile(r"\b(i|ii|iii|iv|v|vi|vii|viii|ix|x)\b$", re.IGNORECASE)

class LogoService:
    def __init__(self, db: Database) -> None:
        self.db = db
        self.session = requests.Session()

    # ---------- name cleaning ----------
    @staticmethod
    def clean_company_name(name: str) -> str:
        s = name.lower().replace('&', ' and ')
        s = re.sub(r"[.,'()/]", " ", s)
        s = re.sub(r"[-_]", " ", s)
        s = SUFFIX_RE.sub(" ", s)
        s = ROMAN_RE.sub(" ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    # ---------- filename (unguessable, deterministic) ----------
    @staticmethod
    def hashed_object_name(cik: str | int) -> str:
        digest = hmac.new(settings.LOGO_NAME_SALT.encode(), str(cik).encode(), hashlib.sha256).hexdigest()
        return f"{digest}.webp"

    # ---------- logo search/download/upload ----------
    def search_domain(self, original_name: str, cleaned_name: str) -> Optional[str]:
        candidates: list[str] = []
        if original_name and original_name.strip():
            candidates.append(original_name.strip())
        if cleaned_name and cleaned_name.strip():
            candidates.append(cleaned_name.strip())
        parts = cleaned_name.split()
        if len(parts) > 2:
            candidates.append(" ".join(parts[:2]))

        # dedupe preserve order
        seen: set[str] = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]

        url = "https://api.logo.dev/search"
        headers = {"Authorization": f"Bearer {settings.LOGO_DEV_KEY}"}
        for q in candidates:
            try:
                resp = self.session.get(url, headers=headers, params={"q": q}, timeout=settings.HTTP_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                if data and isinstance(data, list):
                    for item in data:
                        domain = item.get("domain")
                        if domain:
                            return domain
            except Exception:
                pass
        return None

    def download_webp_bytes(self, domain: str) -> Optional[bytes]:
        img_url = f"https://img.logo.dev/{domain}?token={settings.LOGO_DEV_KEY}"
        try:
            r = self.session.get(img_url, timeout=settings.HTTP_TIMEOUT)
            r.raise_for_status()
            img = Image.open(BytesIO(r.content)).convert("RGBA")
            img = img.resize(settings.LOGO_SIZE, Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format="WEBP", quality=80)
            return buf.getvalue()
        except Exception:
            return None

    def upload_and_get_url(self, object_name: str, image_bytes: bytes) -> Optional[str]:
        if settings.DRY_RUN:
            # Skip actual upload; return the would-be public URL
            try:
                host = settings.SUPABASE_URL.split("//")[1]
            except Exception:
                host = "example.local"
            return f"https://{host}/storage/v1/object/public/{settings.BUCKET_NAME}/{object_name}"
        
        bucket = self.db.client.storage.from_(settings.BUCKET_NAME)
            # try upsert via file_options, fallback to overwrite
        try:
            bucket.upload(object_name, image_bytes, file_options={"content-type": "image/webp", "upsert": True})
        except TypeError:
            try:
                bucket.upload(object_name, image_bytes, {"content-type": "image/webp"})
            except Exception as e:
                msg = str(e).lower()
                if any(k in msg for k in ("exists", "already", "conflict")):
                    try:
                        if hasattr(bucket, "update"):
                            bucket.update(object_name, image_bytes, {"content-type": "image/webp"})
                        else:
                            bucket.remove([object_name])
                            bucket.upload(object_name, image_bytes, {"content-type": "image/webp"})
                    except Exception:
                        return None
                else:
                    return None
        except Exception:
            return None

        try:
            public_url = bucket.get_public_url(object_name)
            if isinstance(public_url, dict):
                public_url = public_url.get("publicUrl") or public_url.get("public_url")
            return public_url
        except Exception:
            host = settings.SUPABASE_URL.split("//")[1]
            return f"https://{host}/storage/v1/object/public/{settings.BUCKET_NAME}/{object_name}"

    # ---------- public entrypoint ----------
    def add_logo_if_missing_or_stale(self, cik: str, company_name: str) -> None:
        row = self.db.get_logo_fields(cik)
        needs_refresh = False
        if not row or not row.get("logo_url") or not row.get("updated_logo_date"):
            needs_refresh = True
        else:
            try:
                last = datetime.date.fromisoformat(str(row["updated_logo_date"])[:10])
                if (datetime.date.today() - last).days >= settings.REFRESH_AFTER_DAYS:
                    needs_refresh = True
            except Exception:
                needs_refresh = True

        if not needs_refresh:
            return

        cleaned = self.clean_company_name(company_name or "")
        domain = self.search_domain(company_name or "", cleaned)
        if not domain:
            return

        img_bytes = self.download_webp_bytes(domain)
        if not img_bytes:
            return

        object_name = self.hashed_object_name(cik)
        public_url = self.upload_and_get_url(object_name, img_bytes)
        if not public_url:
            return

        today = datetime.date.today().isoformat()
        self.db.set_logo_fields(cik, public_url, today)