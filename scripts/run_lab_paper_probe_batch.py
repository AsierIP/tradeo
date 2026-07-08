#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.laboratory.paper_readiness import settings_from_env_file  # noqa: E402

ALLOWED_PROBES = {"LAB-GAP-REV-001", "LAB-GAP-REV-002"}
BLOCKED_DECISIONS = {
    "READONLY_WRITE_REQUIRED": "LAB_PAPER_PROBE_BLOCKED_READONLY_WRITE_REQUIRED",
    "PAPER_ACCOUNT": "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT",
    "KILL_SWITCH": "LAB_PAPER_PROBE_BLOCKED_KILL_SWITCH",
    "SAFETY": "LAB_PAPER_PROBE_BLOCKED_SAFETY",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the supervised Lab Paper Probe batch gate. This script never submits live orders."
    )
    parser.add_argument("--lab-paper-probe", action="store_true", required=True)
    parser.add_argument("--probe-manifest", action="append", required=True)
    parser.add_argument("--paper-only", action="store_true", required=True)
    parser.add_argument("--no-live", action="store_true", required=True)
    parser.add_argument("--max-orders-total", type=int, required=True)
    parser.add_argument("--env-file", default="/home/vboxuser/tradeo/.env")
    parser.add_argument("--runtime-out", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifests = [_load_json(Path(item)) for item in args.probe_manifest]
    settings = settings_from_env_file(args.env_file)
    result = evaluate_batch(args=args, manifests=manifests, settings=settings)
    runtime_path = Path(args.runtime_out)
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["decision"] in {"LAB_PAPER_PROBE_PREMARKET_GO", "LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER"} else 2


def evaluate_batch(*, args: argparse.Namespace, manifests: list[dict[str, Any]], settings: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    now = datetime.now(timezone.utc).isoformat()

    if not args.lab_paper_probe:
        blockers.append("lab_paper_probe_flag_required")
    if not args.paper_only:
        blockers.append("paper_only_flag_required")
    if not args.no_live:
        blockers.append("no_live_flag_required")
    if args.max_orders_total > 2:
        blockers.append("max_orders_total_gt_2")
    if len(manifests) > 2:
        blockers.append("max_two_probes")

    for manifest in manifests:
        blockers.extend(_manifest_blockers(manifest))

    live_armed = _bool(settings.get("live_trading_enabled")) or str(settings.get("trading_mode", "")).lower() == "live"
    auto_submit_general = _bool(settings.get("laboratory_auto_submit_paper_orders"))
    readonly = _bool(settings.get("ibkr_readonly", True))
    paper_verified = _paper_account_verified(settings)
    kill_switch_ready = _kill_switch_ready(settings)

    if live_armed:
        blockers.append("live_armed_true")
    if auto_submit_general:
        blockers.append("auto_submit_general_true")
    if not kill_switch_ready:
        blockers.append("kill_switch_not_ready")
    if not paper_verified:
        blockers.append("paper_account_not_verified")
    if readonly:
        blockers.append("readonly_write_required_for_paper_submit")

    decision = _decision_from_blockers(blockers)
    orders: list[dict[str, Any]] = []
    if decision == "LAB_PAPER_PROBE_PREMARKET_GO":
        warnings.append("dry_run_only_no_market_trigger_evaluated" if args.dry_run else "submit_adapter_not_connected")
        decision = "LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER"

    return {
        "schema": "tradeo.lab_paper_probe_batch.v1",
        "generated_at": now,
        "decision": decision,
        "mode": "LAB_PAPER_PROBE_ONLY",
        "dry_run": bool(args.dry_run),
        "paper_only": bool(args.paper_only),
        "no_live": bool(args.no_live),
        "max_orders_total": args.max_orders_total,
        "probe_ids": [item.get("probe_id") for item in manifests],
        "blockers": blockers,
        "warnings": warnings,
        "orders": orders,
        "no_trade_reason": decision if decision != "LAB_PAPER_PROBE_PREMARKET_GO" else "NO_TRADE_NO_TRIGGER",
        "redacted": True,
        "safety": {
            "live_armed": live_armed,
            "auto_submit_general": auto_submit_general,
            "ibkr_readonly": readonly,
            "paper_account_verified": paper_verified,
            "kill_switch_ready": kill_switch_ready,
        },
    }


def _manifest_blockers(manifest: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    probe_id = str(manifest.get("probe_id", ""))
    if probe_id not in ALLOWED_PROBES:
        blockers.append(f"{probe_id or 'missing_probe'}:non_allowlisted_probe")
    if manifest.get("taxonomy") != "lab_paper_probe":
        blockers.append(f"{probe_id}:taxonomy_not_lab_paper_probe")
    if manifest.get("status") != "enabled_lab_paper_probe":
        blockers.append(f"{probe_id}:probe_not_enabled_for_lab")
    if manifest.get("execution_enabled") is not True:
        blockers.append(f"{probe_id}:execution_not_enabled")
    if manifest.get("disabled_by_default") is not False:
        blockers.append(f"{probe_id}:probe_disabled")
    for key in ("generate_signals", "generate_previews", "live_allowed", "foxhunter_candidate", "live_candidate", "paper_candidate"):
        if manifest.get(key) is not False:
            blockers.append(f"{probe_id}:{key}_must_be_false")
    if int(manifest.get("max_today_orders", 0) or 0) > 1:
        blockers.append(f"{probe_id}:max_today_orders_gt_1")
    if float(manifest.get("max_order_notional_usd", 0) or 0) > 100:
        blockers.append(f"{probe_id}:max_order_notional_gt_100")
    return blockers


def _decision_from_blockers(blockers: list[str]) -> str:
    if not blockers:
        return "LAB_PAPER_PROBE_PREMARKET_GO"
    joined = " ".join(blockers)
    if "readonly_write_required" in joined:
        return BLOCKED_DECISIONS["READONLY_WRITE_REQUIRED"]
    if "paper_account_not_verified" in joined:
        return BLOCKED_DECISIONS["PAPER_ACCOUNT"]
    if "kill_switch" in joined:
        return BLOCKED_DECISIONS["KILL_SWITCH"]
    return BLOCKED_DECISIONS["SAFETY"]


def _paper_account_verified(settings: dict[str, Any]) -> bool:
    mode = str(settings.get("trading_mode", "paper")).lower()
    port = int(settings.get("ibkr_port", 0) or 0)
    return mode == "paper" and port not in {4001, 7496}


def _kill_switch_ready(settings: dict[str, Any]) -> bool:
    return not _bool(settings.get("kill_switch_enabled"))


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
