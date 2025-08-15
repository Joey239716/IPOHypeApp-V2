import os, datetime as dt
from zoneinfo import ZoneInfo
try:
    import redis
except Exception:
    redis = None  # fail-open if lib missing

ET = ZoneInfo("America/Toronto")

def _ds() -> str:
    return dt.datetime.now(ET).strftime("%Y%m%d")

def _next_et_midnight_epoch() -> int:
    today = dt.datetime.now(ET).date()
    nm = dt.datetime.combine(today + dt.timedelta(days=1), dt.time(0, 0, 0, tzinfo=ET))
    return int(nm.timestamp())

class DailyCache:
    def __init__(self) -> None:
        self.enabled = os.getenv("ENABLE_REDIS_CACHE", "false").lower() == "true"
        self.r = None
        if self.enabled and redis:
            try:
                self.r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
                self.r.ping()
            except Exception:
                self.enabled, self.r = False, None  # fail-open

    def _key(self) -> str:
        return f"ipo:processed:{_ds()}"

    def _ensure_ttl(self, key: str) -> None:
        if not (self.enabled and self.r): return
        try:
            ttl = self.r.ttl(key)
            if ttl in (-1, None):
                self.r.expireat(key, _next_et_midnight_epoch())
        except Exception:
            pass

    def seen_today(self, adsh: str) -> bool:
        if not (self.enabled and self.r): return False
        try:
            return bool(self.r.sismember(self._key(), adsh))
        except Exception:
            return False

    def mark_processed(self, adsh: str) -> None:
        if not (self.enabled and self.r): return
        try:
            key = self._key()
            self.r.sadd(key, adsh)
            self._ensure_ttl(key)
        except Exception:
            pass

    def bulk_seed_processed(self, accessions: set[str]) -> int:
        if not (self.enabled and self.r) or not accessions: return 0
        key = self._key()
        added = self.r.sadd(key, *accessions) or 0
        self._ensure_ttl(key)
        return int(added)
