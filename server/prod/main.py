import datetime
from zoneinfo import ZoneInfo
from pipeline.pipeline import Pipeline

if __name__ == '__main__':
    # Daytime run: query only "today" in Eastern Time via EFTS
    et_today = datetime.datetime.now(ZoneInfo("America/Toronto")).date().isoformat()
    Pipeline().fetch_and_push(et_today, et_today)