#!/usr/bin/env python3
"""Run DSS-004D DSS-CO-001 contraction audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing.dss_004d import DSSCOConfig, run_dss_004d, write_markdown_reports  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=Path("artifacts/runtime/daily_swing/daily_ohlcv"), type=Path)
    parser.add_argument("--universe", default=Path("artifacts/runtime/daily_swing/dss_003d_pilot_universe_checked.csv"), type=Path)
    parser.add_argument("--start-date", default="2023-07-05")
    parser.add_argument("--end-date", default="2026-07-02")
    parser.add_argument("--is-end-date", default="2024-12-31")
    parser.add_argument("--oos-start-date", default="2025-01-01")
    parser.add_argument("--output-dir", default=Path("artifacts/runtime/daily_swing"), type=Path)
    parser.add_argument("--research-dir", default=Path("research/daily_swing"), type=Path)
    args = parser.parse_args()
    result = run_dss_004d(
        DSSCOConfig(
            cache_dir=args.cache_dir,
            universe_path=args.universe,
            start_date=args.start_date,
            end_date=args.end_date,
            is_end_date=args.is_end_date,
            oos_start_date=args.oos_start_date,
            output_dir=args.output_dir,
        )
    )
    write_markdown_reports(result, args.research_dir)
    print(json.dumps({"decision": result["decision"]["decision"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
