# server/services/kv_sync_service.py

import os
import json
import requests
import datetime

class KVSyncService:
    def __init__(self, db_client):
        self.db = db_client
        self.cf_account_id = os.getenv("CF_ACCOUNT_ID")
        self.cf_api_token = os.getenv("CF_API_TOKEN")
        self.cf_namespace_id = os.getenv("CF_KV_NAMESPACE_ID")

        if not all([self.cf_account_id, self.cf_api_token, self.cf_namespace_id]):
            raise EnvironmentError("Missing one or more Cloudflare KV config vars")

    def push_ipo_table(self):
        print("[📤] Uploading filtered IPO table to Cloudflare KV...")

        try:
            print("[📦] Fetching IPO rows from Supabase...")

            all_rows = self.db.table("ipo").select("*").eq("is_ipo", True).execute().data

            today = datetime.date.today().isoformat()

            # Filter rows with upcoming or null IPO dates
            filtered = [
                row for row in all_rows
                if row.get("estimated_ipo_date") is None or row.get("estimated_ipo_date") > today
            ]

            # Sort: nulls last, date ascending, market_cap descending
            sorted_rows = sorted(
                filtered,
                key=lambda x: (
                    x.get("estimated_ipo_date") is None,
                    x.get("estimated_ipo_date") or "9999-12-31",
                    -float(x.get("market_cap") or 0)
                )
            )

            # Limit to 100
            limited = sorted_rows[:100]

            # Upload
            url = f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account_id}/storage/kv/namespaces/{self.cf_namespace_id}/values/ipo_table"

            headers = {
                "Authorization": f"Bearer {self.cf_api_token}",
                "Content-Type": "application/json"
            }

            res = requests.put(url, headers=headers, data=json.dumps(limited))

            if res.status_code == 200:
                print(f"[✅] Uploaded {len(limited)} IPOs to KV.")
            else:
                print(f"[❌] Failed to upload to KV: {res.status_code}")
                print(res.text)

        except Exception as e:
            print(f"[❌] KV upload failed: {e}")
