# prod/main.py
import datetime
from zoneinfo import ZoneInfo
from .pipeline.pipeline import Pipeline

if __name__ == "__main__":
    et_today = datetime.datetime.now(ZoneInfo("America/Toronto")).date().isoformat()
    Pipeline().fetch_and_push("2025-08-07", et_today)