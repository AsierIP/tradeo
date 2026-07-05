#!/usr/bin/env python3
"""Validate the DSS-GAP-003 backtest matrix without running any backtest."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing.gap_backtest_matrix import (  # noqa: E402
    SCHEMA_VERSION,
    GapBacktestMatrixError,
    default_gap_backtest_matrix,
    matrix_audit,
    read_gap_backtest_matrix_json,
    validate_gap_backtest_matrix,
    write_gap_backtest_matrix,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix-json", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("research/daily_swing/gap"))
    parser.add_argument("--write-default", action="store_true")
    parser.add_argument("--execute", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--orders", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preview", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--signals", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--paper", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--live", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--ibkr", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if any((args.execute, args.orders, args.preview, args.signals, args.paper, args.live, args.ibkr)):
        print("DSS-GAP-003 refuses execution, orders, preview, signals, paper, live, and IBKR.", file=sys.stderr)
        return 2

    if args.matrix_json:
        rows = read_gap_backtest_matrix_json(args.matrix_json)
        paths: dict[str, str] = {"json": str(args.matrix_json)}
    else:
        rows = default_gap_backtest_matrix()
        paths = {}
        if args.write_default:
            paths = {key: str(value) for key, value in write_gap_backtest_matrix(rows, args.output_dir).items()}

    try:
        validation = validate_gap_backtest_matrix(rows)
        audit = matrix_audit(rows)
    except GapBacktestMatrixError as exc:
        print(str(exc), file=sys.stderr)
        return 3

    if args.write_default:
        (args.output_dir / "DSS_GAP_003_NO_LOOKAHEAD_MATRIX_AUDIT.json").write_text(
            json.dumps(audit, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "validation": asdict(validation),
        "audit": audit,
        "paths": paths,
        "security": {
            "no_orders": True,
            "no_paper": True,
            "no_live": True,
            "no_preview": True,
            "no_signals": True,
            "no_backtest": True,
            "no_ibkr": True,
            "no_downloads": True,
            "no_cron": True,
            "no_gh": True,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
