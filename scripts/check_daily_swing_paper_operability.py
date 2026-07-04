#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing import check_daily_swing_operability, load_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Daily Swing paper-probe safety gates.")
    parser.add_argument("--config", type=Path, default=Path("configs/daily_swing_paper_probe.yaml"))
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    result = check_daily_swing_operability(env_file=args.env_file, config=load_config(args.config))
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
