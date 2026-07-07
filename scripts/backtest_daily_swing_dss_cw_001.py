#!/usr/bin/env python3
"""Run DSS-004G-B DSS-CW-001 research-only cache backtest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.core.config import get_settings
from tradeo.modules.daily_swing.dss_004g_b import DSS004GBConfig, run_dss_004g_b  # noqa: E402
from tradeo.modules.resource_policy.enforcement import blocked_job_status, decide_with_market_session_policy
from tradeo.modules.resource_policy.market_session_resource_policy import JobType


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", default=Path("artifacts/runtime/daily_swing/daily_ohlcv_research"), type=Path)
    parser.add_argument(
        "--universe",
        default=Path("artifacts/runtime/daily_swing/dss_003e_research_universe_checked.csv"),
        type=Path,
    )
    parser.add_argument("--start-date", default="2023-07-05")
    parser.add_argument("--end-date", default="2026-07-02")
    parser.add_argument("--is-end-date", default="2024-12-31")
    parser.add_argument("--oos-start-date", default="2025-01-01")
    parser.add_argument("--output-dir", default=Path("artifacts/runtime/daily_swing"), type=Path)
    parser.add_argument("--research-dir", default=Path("research/daily_swing"), type=Path)
    parser.add_argument("--bootstrap-iterations", default=100, type=int)
    args = parser.parse_args()
    policy_decision = decide_with_market_session_policy(
        JobType.HEAVY_BACKTEST,
        "research",
        settings=get_settings(),
    )
    if not policy_decision.allowed:
        print(
            json.dumps(
                {
                    "decision": "blocked_resource_policy",
                    "resource_policy": policy_decision.to_dict(),
                    "research_result": blocked_job_status(policy_decision),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 5
    result = run_dss_004g_b(
        DSS004GBConfig(
            cache_dir=args.cache_dir,
            universe_path=args.universe,
            start_date=args.start_date,
            end_date=args.end_date,
            is_end_date=args.is_end_date,
            oos_start_date=args.oos_start_date,
            output_dir=args.output_dir,
            research_dir=args.research_dir,
            bootstrap_iterations=args.bootstrap_iterations,
        )
    )
    print(json.dumps(result["decision"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
