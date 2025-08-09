import datetime
from zoneinfo import ZoneInfo
from pipeline.pipeline import Pipeline

if __name__ == '__main__':
    # Run nightly at ~00:35 ET; reconcile the previous ET day’s master index
    et_now = datetime.datetime.now(ZoneInfo("America/Toronto"))
    prev_day = (et_now.date() - datetime.timedelta(days=1))
    ds = prev_day.strftime("%Y%m%d")
    Pipeline().reconcile_daily_index(ds)