import argparse
import datetime
from zoneinfo import ZoneInfo
from .pipeline.pipeline import Pipeline

"""
Nightly safety pass:
- By default, reconciles the SEC master daily index for **yesterday in ET**
- Optional: override the date with --ds YYYYMMDD
Usage:
    python nightly.py               # uses yesterday (ET)
    python nightly.py --ds 20250808 # specific date
"""

def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile SEC master daily index for a given ET date")
    parser.add_argument("--ds", help="Date string YYYYMMDD (default=yesterday in ET)")
    args = parser.parse_args()

    if args.ds:
        ds = args.ds
    else:
        et_now = datetime.datetime.now(ZoneInfo("America/Toronto"))
        prev_day = et_now.date() - datetime.timedelta(days=1)
        ds = prev_day.strftime("%Y%m%d")

    Pipeline().reconcile_daily_index(ds)

if __name__ == "__main__":
    main()