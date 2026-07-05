#!/usr/bin/env python3
"""Emit the inert DSS-GAP-001 protocol summary.

This runner is intentionally documentation/scaffold only. It does not read
market data, call IBKR, run a backtest, generate signals, or create previews.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing.gap_protocol import protocol_summary, validate_protocol_inert


def main() -> int:
    validation = validate_protocol_inert()
    payload = protocol_summary()
    payload["validation"] = validation
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if validation["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
