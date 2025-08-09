from typing import Any, Optional
from supabase import create_client, Client
from ..config import settings

class Database:
    def __init__(self) -> None:
        self._client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

    @property
    def client(self) -> Client:
        return self._client

    # IPO table helpers
    def get_ipo_snapshot(self) -> dict[str, dict[str, Any]]:
        resp = self._client.table('ipo').select('cik, latest_filing_date, is_ipo, company_name, logo_url, updated_logo_date').execute()
        rows = resp.data or []
        return {str(r['cik']): r for r in rows}

    def upsert_ipo(self, rec: dict[str, Any]) -> None:
        self._client.table('ipo').upsert(rec, on_conflict='cik').execute()

    def delete_ipo(self, cik: str) -> None:
        self._client.table('ipo').delete().eq('cik', cik).execute()

    def move_to_public(self, pub: dict[str, Any]) -> None:
        self._client.table('public_companies').upsert(pub, on_conflict='cik').execute()

    def get_logo_fields(self, cik: str) -> Optional[dict[str, Any]]:
        resp = self._client.table('ipo').select('logo_url, updated_logo_date').eq('cik', cik).limit(1).execute()
        data = resp.data or []
        return data[0] if data else None

    def set_logo_fields(self, cik: str, logo_url: str, date_iso: str) -> None:
        self._client.table('ipo').update({'logo_url': logo_url, 'updated_logo_date': date_iso}).eq('cik', cik).execute()