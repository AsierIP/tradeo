#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.research_capacity.capacity_metrics import (  # noqa: E402
    collect_research_surface,
    metric_schema,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect CAPACITY-001 metric schema and research surface inventory.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--runtime-root", type=Path, default=Path("artifacts/runtime"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/runtime/research_capacity/capacity_001_inventory.json"))
    args = parser.parse_args()
    payload = {
        "schema": metric_schema(),
        "surface_inventory": collect_research_surface(args.repo_root, args.runtime_root),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

