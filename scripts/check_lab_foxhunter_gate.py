#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from tradeo.modules.lab_foxhunter.gates import (  # noqa: E402
    validate_foxhunter_to_live_gate,
    validate_lab_to_foxhunter_gate,
    validate_manifest,
    validate_research_to_lab_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Lab Paper Probe, FoxHunter, and live promotion gates."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--live-review", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    manifests = _read_manifests(args.manifest)
    decisions = []
    for manifest in manifests:
        decisions.append(validate_manifest(manifest).to_dict())
        decisions.append(validate_research_to_lab_gate(manifest).to_dict())
    if args.metrics:
        decisions.append(validate_lab_to_foxhunter_gate(_read_json(args.metrics)).to_dict())
    if args.live_review:
        decisions.append(validate_foxhunter_to_live_gate(_read_json(args.live_review)).to_dict())

    report = {
        "schema_version": "tradeo.lab_foxhunter_gate_check.v1",
        "orders_allowed": False,
        "paper_orders_generated": False,
        "live_orders_generated": False,
        "previews_generated": False,
        "signals_generated": False,
        "ibkr_used": False,
        "downloads_used": False,
        "decisions": decisions,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if any(decision["status"] == "BLOCK" for decision in decisions) else 0


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_manifests(path: Path) -> list[dict[str, object]]:
    raw = _read_json(path)
    probes = raw.get("probes")
    if isinstance(probes, list):
        return [probe for probe in probes if isinstance(probe, dict)]
    return [raw]


if __name__ == "__main__":
    raise SystemExit(main())
