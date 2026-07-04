#!/usr/bin/env python3
"""Run DSS-004C DSS-BO-001 specificity autopsy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing.dss_004c import AutopsyConfig, run_dss_004c_autopsy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", required=True, type=Path)
    parser.add_argument("--universe", required=True, type=Path)
    parser.add_argument("--start-date", default="2023-07-05")
    parser.add_argument("--end-date", default="2026-07-02")
    parser.add_argument("--is-end-date", default="2024-12-31")
    parser.add_argument("--oos-start-date", default="2025-01-01")
    parser.add_argument("--output-dir", default=Path("artifacts/runtime/daily_swing"), type=Path)
    args = parser.parse_args()
    result = run_dss_004c_autopsy(
        AutopsyConfig(
            cache_dir=args.cache_dir,
            universe_path=args.universe,
            start_date=args.start_date,
            end_date=args.end_date,
            is_end_date=args.is_end_date,
            oos_start_date=args.oos_start_date,
            output_dir=args.output_dir,
        )
    )
    print(json.dumps(result["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
