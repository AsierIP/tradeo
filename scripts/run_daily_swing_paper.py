#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.daily_swing import check_daily_swing_operability, generate_daily_swing_preview, load_config, preview_spec_hash


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run guarded Daily Swing paper execution.")
    parser.add_argument("--config", type=Path, default=Path("configs/daily_swing_paper_probe.yaml"))
    parser.add_argument("--preview-json", type=Path, default=Path("artifacts/runtime/daily_swing/paper_orders_preview_2026-07-06.json"))
    parser.add_argument("--execute", action="store_true", help="Submit paper orders only after all gates pass.")
    args = parser.parse_args()

    config = load_config(args.config)
    orders = generate_daily_swing_preview(config)
    execution_hash = preview_spec_hash(orders, config)
    preview_hash = None
    if args.preview_json.exists():
        preview_hash = json.loads(args.preview_json.read_text(encoding="utf-8")).get("spec_hash")
    if preview_hash != execution_hash:
        print(json.dumps({"status": "BLOCKED", "reason": "preview_hash_mismatch", "execution_hash": execution_hash, "preview_hash": preview_hash}, indent=2))
        return 2
    operability = check_daily_swing_operability(config=config)
    if operability["status"] != "OK":
        print(json.dumps({"status": "BLOCKED", "reason": "operability_failed", "operability": operability}, indent=2, sort_keys=True))
        return 2
    if not args.execute:
        print(json.dumps({"status": "DRY_RUN_OK", "orders": len(orders), "execution_hash": execution_hash}, indent=2, sort_keys=True))
        return 0
    print(json.dumps({"status": "BLOCKED", "reason": "paper submission adapter intentionally not armed in this branch"}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
