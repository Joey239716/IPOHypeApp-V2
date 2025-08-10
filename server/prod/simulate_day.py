import argparse
import datetime as dt
from .pipeline.pipeline import Pipeline


def main() -> None:
    ap = argparse.ArgumentParser(description="Simulate one day's IPO pipeline runs")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (the day to simulate)")
    ap.add_argument("--daytime-only", action="store_true", help="Run only the daytime EFTS pass")
    ap.add_argument("--nightly-only", action="store_true", help="Run only the nightly index reconcile")
    args = ap.parse_args()

    try:
        d = dt.date.fromisoformat(args.date)
    except Exception as e:
        raise SystemExit(f"Invalid --date format, expected YYYY-MM-DD: {e}")

    pipe = Pipeline()

    # Daytime EFTS pass (start=end=given date)
    if not args.nightly_only:
        print(f"[SIM] Daytime EFTS pass for {d.isoformat()}")
        pipe.fetch_and_push(d.isoformat(), d.isoformat())

    # Nightly master index reconcile for the same date
    if not args.daytime_only:
        ds = d.strftime("%Y%m%d")
        print(f"[SIM] Nightly Daily Index reconcile for {ds}")
        pipe.reconcile_daily_index(ds)

if __name__ == "__main__":
    main()