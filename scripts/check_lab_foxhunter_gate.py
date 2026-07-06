#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.lab_foxhunter.gates import (  # noqa: E402
    validate_lab_paper_probe_manifest,
)


FORBIDDEN_OUTPUT_MARKERS = (
    '"execution_enabled": true',
    '"generate_signals": true',
    '"generate_previews": true',
    '"live_allowed": true',
    '"paper_orders_allowed_now": true',
    '"order_preview_allowed": true',
    '"signals_allowed": true',
    '"ibkr_operational_use": true',
    "LIVE_APPROVED",
    "submitted_order_id",
    "order_preview_id",
)

FORBIDDEN_PATH_PARTS = (
    ".env",
    "MEMORY.md",
    "/memory/",
    "artifacts/",
    "runtime/",
    "logs/",
    "__pycache__",
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _scan_json_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*.json")):
        try:
            _load_json(path)
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid_json:{exc.lineno}:{exc.colno}")
    return errors


def _scan_security(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        if any(part in relative for part in FORBIDDEN_PATH_PARTS):
            errors.append(f"{relative}: forbidden_tracked_path")
        if path.suffix.lower() not in {".json", ".md", ".py"}:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_OUTPUT_MARKERS:
            if marker in text:
                errors.append(f"{relative}: forbidden_marker:{marker}")
        lowered = text.lower()
        for marker in ("password", "private key", "api_token", "secret_key"):
            if marker in lowered:
                errors.append(f"{relative}: possible_secret_marker:{marker}")
    return errors


def build_report(research_root: Path) -> dict[str, Any]:
    manifest_path = research_root / "lab_paper_probe_manifest.example.json"
    decision_path = research_root / "LAB_FOXHUNTER_001_DECISION.json"
    errors: list[str] = []
    errors.extend(_scan_json_files(research_root))
    if not manifest_path.is_file():
        errors.append(f"{manifest_path}: missing_lab_paper_probe_manifest")
        manifest_decision = None
    else:
        manifest_decision = validate_lab_paper_probe_manifest(_load_json(manifest_path))
        errors.extend(manifest_decision.blockers)
    if not decision_path.is_file():
        errors.append(f"{decision_path}: missing_decision_json")
        decision = {}
    else:
        decision = _load_json(decision_path)
        if decision.get("decision") != "LAB_FOXHUNTER_GATE_READY_NO_EXECUTION":
            errors.append("decision_not_ready_no_execution")
        for key in (
            "live_allowed",
            "paper_orders_allowed_now",
            "paper_probe_execution_enabled",
            "order_preview_allowed",
            "signals_allowed",
            "ibkr_operational_use",
            "data_downloads_performed",
            "cron_trading_enabled",
        ):
            if decision.get(key) is not False:
                errors.append(f"{key}_must_be_false")
        if decision.get("foxhunter_candidates_created") != 0:
            errors.append("foxhunter_candidates_created_must_be_zero")
        if decision.get("live_candidates_created") != 0:
            errors.append("live_candidates_created_must_be_zero")
        if decision.get("initial_probes_disabled_by_default") is not True:
            errors.append("initial_probes_disabled_by_default_required")
    errors.extend(_scan_security(research_root))
    return {
        "status": "PASS" if not errors else "FAIL",
        "research_root": str(research_root),
        "manifest_valid": bool(manifest_decision and manifest_decision.allowed),
        "no_execution_outputs": bool(manifest_decision and manifest_decision.no_execution_outputs),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Lab/FoxHunter gate framework without generating orders or signals."
    )
    parser.add_argument("--research-root", default=str(ROOT / "research" / "lab_foxhunter"))
    parser.add_argument("--json-out")
    args = parser.parse_args()

    report = build_report(Path(args.research_root))
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.json_out:
        Path(args.json_out).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
