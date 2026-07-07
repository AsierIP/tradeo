#!/usr/bin/env python3
"""Build the Daily Swing Universe v2 runtime CSV and audit summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing.universe_v2 import (  # noqa: E402
    DEFAULT_BUCKET_SUMMARY_CSV,
    DEFAULT_BUCKET_SUMMARY_JSON,
    DEFAULT_RUNTIME_OUTPUT_PATH,
    DailySwingUniverseV2Config,
    DailySwingUniverseV2Builder,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--seed-file",
        action="append",
        default=[],
        help="Local candidate CSV with symbol and bucket columns. Can be repeated.",
    )
    parser.add_argument("--output", default=DEFAULT_RUNTIME_OUTPUT_PATH, type=Path)
    parser.add_argument("--summary-csv", default=DEFAULT_BUCKET_SUMMARY_CSV, type=Path)
    parser.add_argument("--summary-json", default=DEFAULT_BUCKET_SUMMARY_JSON, type=Path)
    parser.add_argument("--max-symbols-per-bucket", default=8, type=int)
    parser.add_argument("--rotation-salt", default=None)
    parser.add_argument(
        "--market-cap-pit-source",
        default=None,
        help="Verified point-in-time market-cap source. Omit to mark source unavailable/proxy.",
    )
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args(argv)

    result = DailySwingUniverseV2Builder(
        DailySwingUniverseV2Config(
            max_symbols_per_bucket=args.max_symbols_per_bucket,
            market_cap_point_in_time_source=args.market_cap_pit_source,
            rotation_salt=args.rotation_salt,
        )
    ).build(
        seed_files=args.seed_file,
        output_path=args.output,
        summary_csv_path=args.summary_csv,
        summary_json_path=args.summary_json,
    )

    payload = {
        "output_path": str(result.output_path),
        "summary_csv_path": str(result.summary_csv_path),
        "summary_json_path": str(result.summary_json_path),
        "selected_count": result.metadata["selected_count"],
        "missing_required_buckets": result.metadata["missing_required_buckets"],
        "market_cap_point_in_time": result.metadata["market_cap_point_in_time"],
        "selected_preview": result.metadata["selected_symbols"][:24],
    }
    if not args.json_only:
        print(
            "built daily swing universe v2 "
            f"selected={payload['selected_count']} "
            f"missing_required_buckets={payload['missing_required_buckets']} "
            f"output={payload['output_path']}"
        )
        print("JSON:")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not result.metadata["missing_required_buckets"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
