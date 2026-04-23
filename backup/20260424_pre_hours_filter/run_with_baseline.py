"""Wrapper that computes the RF analysis baseline based on the weekday,
then invokes analyze_sectors.py with --start/--end arguments.

Baseline rule (reference = latest trading day considered):
- Mon-Thu: baseline = previous week's Friday close (Weekly RF)
- Fri:     baseline = last day of previous month close (Monthly RF)

Reference date resolution:
- MARKET_TYPE=US (default): JST today - 1 day (US close belongs to prior JST day)
- MARKET_TYPE=JP:           JST today (same-day JP close)

Manual overrides (workflow_dispatch inputs, Google Form triggers) are passed
through to analyze_sectors.py untouched; the weekday logic only kicks in when
no start/end is supplied.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta

import pytz


def compute_auto_baseline(market_type: str = "US"):
    jst = pytz.timezone("Asia/Tokyo")
    now_jst = datetime.now(jst)

    if market_type.upper() == "US":
        ref_date = (now_jst - timedelta(days=1)).date()
    else:
        ref_date = now_jst.date()

    while ref_date.weekday() >= 5:
        ref_date -= timedelta(days=1)

    wd = ref_date.weekday()
    if wd == 4:
        first_of_month = ref_date.replace(day=1)
        baseline = first_of_month - timedelta(days=1)
        while baseline.weekday() >= 5:
            baseline -= timedelta(days=1)
        label = "前月末終値基点 (Previous Month Close)"
    else:
        baseline = ref_date - timedelta(days=wd + 3)
        label = "前週末終値基点 (Previous Week Close)"

    return baseline, ref_date, label


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", default=os.environ.get("MARKET_TYPE", "US"))
    parser.add_argument("--start", type=str)
    parser.add_argument("--end", type=str)
    parser.add_argument("--script", default="analyze_sectors.py")
    args, _ = parser.parse_known_args()

    if args.start or args.end:
        cmd = [sys.executable, args.script]
        if args.start:
            cmd += ["--start", args.start]
        if args.end:
            cmd += ["--end", args.end]
        print(f"[MANUAL] Forwarding: {' '.join(cmd)}")
    else:
        baseline, ref, label = compute_auto_baseline(args.market)
        start_str = baseline.strftime("%Y-%m-%d")
        end_str = ref.strftime("%Y-%m-%d")
        print(f"[AUTO] {label}")
        print(f"[AUTO] market={args.market} baseline={start_str} ref={end_str} weekday={ref.weekday()}")
        cmd = [sys.executable, args.script, "--start", start_str, "--end", end_str]

    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()
