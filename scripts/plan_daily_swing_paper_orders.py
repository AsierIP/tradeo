#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing import build_daily_swing_artifacts, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Daily Swing paper order preview artifacts.")
    parser.add_argument("--config", type=Path, default=Path("configs/daily_swing_paper_probe.yaml"))
    args = parser.parse_args()
    result = build_daily_swing_artifacts(config=load_config(args.config))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
