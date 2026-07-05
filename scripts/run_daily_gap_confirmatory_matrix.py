#!/usr/bin/env python3
"""Run DSS-GAP-007 confirmatory matrix in cache-only research mode."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing.gap_confirmatory_run import (  # noqa: E402
    GapConfirmatoryRunConfig,
    GapConfirmatoryRunError,
    run_gap_confirmatory_matrix,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--criteria", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--research-output-dir", type=Path)
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--no-ibkr", action="store_true")
    parser.add_argument("--no-signals", action="store_true")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--no-orders", action="store_true")
    parser.add_argument("--ibkr", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--signals", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preview", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--orders", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--paper", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--live", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if any((args.ibkr, args.signals, args.preview, args.orders, args.paper, args.live)):
        print("DSS-GAP-007 refuses IBKR, signals, preview, orders, paper, and live.", file=sys.stderr)
        return 2
    config = GapConfirmatoryRunConfig(
        ledger_path=args.ledger,
        matrix_path=args.matrix,
        criteria_path=args.criteria,
        output_dir=args.output_dir,
        research_output_dir=args.research_output_dir,
        cache_only=args.cache_only,
        no_ibkr=args.no_ibkr,
        no_signals=args.no_signals,
        no_preview=args.no_preview,
        no_orders=args.no_orders,
    )
    try:
        result = run_gap_confirmatory_matrix(config)
    except GapConfirmatoryRunError as exc:
        print(f"{exc.decision}: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
