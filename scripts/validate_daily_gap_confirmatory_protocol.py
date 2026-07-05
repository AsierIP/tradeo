#!/usr/bin/env python3
"""Validate the DSS-GAP-006 confirmatory protocol without running GAP-007."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing.gap_confirmatory_protocol import (  # noqa: E402
    GapConfirmatoryProtocolError,
    read_confirmatory_matrix_csv,
    read_confirmatory_matrix_json,
    validation_payload,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--matrix-json",
        type=Path,
        default=Path("research/daily_swing/gap/dss_gap_006_confirmatory_matrix.json"),
    )
    parser.add_argument("--matrix-csv", type=Path)
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
        print("DSS-GAP-006 refuses execution, orders, preview, signals, paper, live, and IBKR.", file=sys.stderr)
        return 2

    try:
        rows = read_confirmatory_matrix_csv(args.matrix_csv) if args.matrix_csv else read_confirmatory_matrix_json(args.matrix_json)
        payload = validation_payload(rows)
    except (GapConfirmatoryProtocolError, FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 3

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
