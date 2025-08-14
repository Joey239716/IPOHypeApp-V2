from typing import Any, Optional
import time
import httpx
from supabase import create_client, Client
from ..config import settings

# Optional knobs (or put these in settings)
DB_MAX_RETRIES     = getattr(settings, "DB_MAX_RETRIES", 3)
DB_RETRY_BACKOFF_S = getattr(settings, "DB_RETRY_BACKOFF", 1.0)  # base seconds for exponential backoff


class Database:
    def __init__(self) -> None:
        self._client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )

    @property
    def client(self) -> Client:
        return self._client

    # ------------- internal retry helper -------------

    def _retry(self, fn, *, what: str):
        last_err = None
        for i in range(DB_MAX_RETRIES):
            try:
                return fn()
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_err = e
                wait = DB_RETRY_BACKOFF_S * (2 ** i)
                print(f"[WARN] {what} retry {i+1}/{DB_MAX_RETRIES} after {e!s} (sleep {wait:.1f}s)")
                time.sleep(wait)
            except Exception as e:
                # Non-transient or unexpected – log and break.
                print(f"[ERROR] {what} failed: {e}")
                last_err = e
                break
        print(f"[WARN] {what}: giving up after retries: {last_err}")
        return None

    # ------------- reads with retries -------------

    def get_accessions_for_date(self, date_iso: str) -> set[str]:
        """
        Return all accession_numbers already stored in ipo for the given YYYY-MM-DD date.
        Safe on transient network failures (falls back to empty set).
        """
        def _do():
            return (
                self._client.table('ipo')
                .select('accession_number')
                .eq('latest_filing_date', date_iso)
                .execute()
            )

        resp = self._retry(_do, what="get_accessions_for_date")
        rows = (resp.data if resp and hasattr(resp, "data") else []) or []
        return {r['accession_number'] for r in rows if r.get('accession_number')}

    def get_ipo_snapshot(self) -> dict[str, dict[str, Any]]:
        """
        Returns a dict keyed by normalized CIK strings.
        Safe on transient network failures (falls back to empty dict).
        """
        def _do():
            return (
                self._client.table('ipo')
                .select('cik, latest_filing_date, is_ipo, company_name, logo_url, updated_logo_date')
                .execute()
            )

        resp = self._retry(_do, what="get_ipo_snapshot")
        rows = (resp.data if resp and hasattr(resp, "data") else []) or []

        snap: dict[str, dict[str, Any]] = {}
        for r in rows:
            cik = r.get("cik")
            if cik is None:
                continue
            try:
                # normalize e.g. "0001872195" -> "1872195"
                key = str(int(cik))
            except Exception:
                key = str(cik)
            snap[key] = r
        return snap

    # ------------- other helpers (unchanged writes) -------------

    def get_ipo_by_cik(self, cik: str) -> Optional[dict[str, Any]]:
        """
        Return a single IPO row for the given CIK, including the 'analyzed' field.
        """
        resp = self._client.table('ipo') \
            .select('*') \
            .eq('cik', cik) \
            .limit(1) \
            .execute()
        rows = resp.data or []
        return rows[0] if rows else None

    def upsert_ipo(self, rec: dict[str, Any]) -> None:
        if settings.DRY_RUN:
            print(f"[DRY-RUN] upsert_ipo: {rec['cik']} {rec.get('latest_filing_type')} {rec.get('latest_filing_date')}")
            return
        self._client.table('ipo').upsert(rec, on_conflict='cik').execute()

    def delete_ipo(self, cik: str) -> None:
        if settings.DRY_RUN:
            print(f"[DRY-RUN] delete_ipo: {cik}")
            return
        self._client.table('ipo').delete().eq('cik', cik).execute()

    def move_to_public(self, pub: dict[str, Any]) -> None:
        if settings.DRY_RUN:
            print(f"[DRY-RUN] move_to_public: {pub['cik']} form={pub.get('form_type')}")
            return
        self._client.table('public_companies').upsert(pub, on_conflict='cik').execute()

    def get_logo_fields(self, cik: str) -> Optional[dict[str, Any]]:
        resp = self._client.table('ipo').select('logo_url, updated_logo_date').eq('cik', cik).limit(1).execute()
        data = resp.data or []
        return data[0] if data else None

    def set_logo_fields(self, cik: str, logo_url: str, date_iso: str) -> None:
        if settings.DRY_RUN:
            print(f"[DRY-RUN] set_logo_fields: {cik} -> {logo_url} ({date_iso})")
            return
        self._client.table('ipo').update({'logo_url': logo_url, 'updated_logo_date': date_iso}).eq('cik', cik).execute()
