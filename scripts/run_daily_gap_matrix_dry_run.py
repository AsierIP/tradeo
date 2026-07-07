#!/usr/bin/env python3
"""Run the DSS-GAP-004 matrix dry-run in cache-only research mode."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing.gap_matrix_dry_run import (  # noqa: E402
    GapDryRunConfig,
    GapMatrixDryRunError,
    run_gap_matrix_dry_run,
)
from tradeo.core.config import get_settings  # noqa: E402
from tradeo.modules.resource_policy.enforcement import (  # noqa: E402
    blocked_job_status,
    decide_with_market_session_policy,
)
from tradeo.modules.resource_policy.market_session_resource_policy import JobType  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--no-ibkr", action="store_true")
    parser.add_argument("--no-signals", action="store_true")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--no-orders", action="store_true")
    parser.add_argument("--ibkr", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--signals", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preview", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--orders", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if any((args.ibkr, args.signals, args.preview, args.orders)):
        print("DSS-GAP-004 refuses IBKR, signals, preview, and orders.", file=sys.stderr)
        return 2
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
    config = GapDryRunConfig(
        ledger_path=args.ledger,
        matrix_path=args.matrix,
        output_dir=args.output_dir,
        cache_only=args.cache_only,
        no_ibkr=args.no_ibkr,
        no_signals=args.no_signals,
        no_preview=args.no_preview,
        no_orders=args.no_orders,
    )
    try:
        result = run_gap_matrix_dry_run(config)
    except GapMatrixDryRunError as exc:
        print(f"{exc.decision}: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
