# prod/main.py
import datetime
from zoneinfo import ZoneInfo
from .pipeline.pipeline import Pipeline

if __name__ == "__main__":
    # Get today's date in Eastern Time (Toronto timezone)
    et_today = datetime.datetime.now(ZoneInfo("America/Toronto")).date().isoformat()
    
    # Use the same day as start and end
    Pipeline().fetch_and_push(et_today, et_today)
