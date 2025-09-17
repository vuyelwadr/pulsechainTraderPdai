#!/usr/bin/env python3
"""CLI helper to collect pDAI → DAI OHLCV candles via PulseX swaps."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from pdai_trader.data.collector import PdaiDataCollector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect pDAI/WPLS/DAI routed OHLCV candles")
    parser.add_argument("--days", type=float, default=1.0, help="Number of days to backfill from now")
    parser.add_argument("--interval", type=str, default="8H", help="Aggregation interval (pandas frequency string)")
    parser.add_argument("--out", type=Path, default=Path("data/pdai_ohlcv_export.csv"), help="Destination CSV path")
    parser.add_argument("--volume-asset", type=str, choices=["pDAI", "DAI"], default="pDAI")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    collector = PdaiDataCollector()

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)

    df = collector.collect_ohlcv_from_swaps(
        start_time=start,
        end_time=end,
        interval_minutes=max(1, int(pd.Timedelta(args.interval).total_seconds() // 60)),
        volume_asset=args.volume_asset,
    )

    if df is None or df.empty:
        print("No swap data returned for that window.")
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df)} candles to {args.out}")


if __name__ == "__main__":
    main()
