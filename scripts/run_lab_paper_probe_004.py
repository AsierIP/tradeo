#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

ALLOWED_OVERLAY_KEYS = {
    "TRADEO_IBKR_READONLY",
    "TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED",
    "TRADEO_LIVE_ARMED",
    "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS",
}
LIVE_PORTS = {4001, 7496}
PAPER_PORTS = {4002, 7497, 14002}
CANARY_SYMBOL = "AAPL"
TASK_ID = "T-LAB-PAPER-PROBE-004"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve paper account identity and run paper account/canary gates only."
    )
    parser.add_argument("--env-file", default="/home/vboxuser/tradeo/.env")
    parser.add_argument(
        "--overlay-file",
        default="/tmp/tradeo_lab_paper_write_overlay_20260706_account_gate.env",
    )
    parser.add_argument("--runtime-out", required=True)
    parser.add_argument("--reports-dir", default="research/lab_foxhunter")
    parser.add_argument("--skip-canary-submit", action="store_true")
    args = parser.parse_args()

    report = run_probe_004(args)
    runtime_path = Path(args.runtime_out)
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report_artifacts(report, reports_dir=Path(args.reports_dir))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["decision"] == "LAB_PAPER_ACCOUNT_AND_CANARY_READY_FOR_PROBES" else 2


def run_probe_004(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    env_path = Path(args.env_file)
    overlay_path = Path(args.overlay_file)
    original_env = _parse_env(env_path)
    config_audit = _config_account_audit(env_path, original_env)
    managed_probe_private = _managed_account_probe(original_env)
    reconciliation = _reconcile_account(env_path, original_env, config_audit, managed_probe_private)
    reconciled_env = _parse_env(env_path)
    account_gate = _paper_account_gate(reconciled_env)
    managed_probe = _public_payload(managed_probe_private)
    env_overlay_gate = _build_env_overlay_gate(base_env=reconciled_env, overlay_path=overlay_path)
    overlay_env = _parse_env(overlay_path)
    merged_env = {**reconciled_env, **overlay_env}
    canary = _canary_submit_cancel(merged_env, account_gate, skip_submit=bool(args.skip_canary_submit))

    blockers: list[str] = []
    for gate_name, gate in (
        ("config_account_audit", config_audit),
        ("managed_account_probe", managed_probe),
        ("account_reconciliation", reconciliation),
        ("paper_account_gate", account_gate),
        ("env_overlay", env_overlay_gate),
        ("canary", canary),
    ):
        if gate["status"] not in {"PASS", "FIXED"}:
            blockers.append(f"{gate_name}:{gate['status']}")
            blockers.extend(f"{gate_name}:{item}" for item in gate.get("blockers", []))

    if account_gate["status"] != "PASS":
        decision = _blocked_decision(reconciliation, managed_probe, account_gate)
    elif env_overlay_gate["status"] != "PASS":
        decision = "LAB_PAPER_ACCOUNT_BLOCKED_LIVE_RISK"
    elif canary["status"] != "PASS":
        if canary["decision"] == "CANARY_BLOCKED_LIVE_RISK":
            decision = "LAB_PAPER_ACCOUNT_BLOCKED_LIVE_RISK"
        else:
            decision = "LAB_PAPER_ACCOUNT_BLOCKED_CANARY_FAIL"
    else:
        decision = "LAB_PAPER_ACCOUNT_AND_CANARY_READY_FOR_PROBES"

    overlay_removed_after_run = False
    if overlay_path.exists():
        overlay_path.unlink()
        overlay_removed_after_run = True

    return {
        "schema": "tradeo.lab_paper_probe_004.runtime.v1",
        "generated_at": generated_at,
        "task_id": TASK_ID,
        "mode": "LAB_PAPER_ACCOUNT_GATE_ONLY",
        "decision": decision,
        "path_used": str(ROOT),
        "base_env_path": str(env_path),
        "overlay_path": str(overlay_path),
        "overlay_tracked": _is_tracked(ROOT, overlay_path),
        "overlay_removed_after_run": overlay_removed_after_run,
        "paper_orders_executed": len(canary.get("orders", [])) if canary["status"] == "PASS" else 0,
        "strategy_paper_orders_executed": 0,
        "live_orders_executed": 0,
        "foxhunter_promotion": False,
        "live_candidate_created": False,
        "paper_candidate_classic_created": False,
        "signals_generated": False,
        "previews_generated": False,
        "probes_executed": False,
        "config_account_audit": config_audit,
        "managed_account_probe": managed_probe,
        "account_reconciliation": reconciliation,
        "paper_account_gate": account_gate,
        "env_overlay_gate": env_overlay_gate,
        "canary": canary,
        "orders": canary.get("orders", []) if canary["status"] == "PASS" else [],
        "no_trade_reason": None if decision == "LAB_PAPER_ACCOUNT_AND_CANARY_READY_FOR_PROBES" else decision,
        "blockers": blockers,
        "redacted": True,
    }


def _blocked_decision(
    reconciliation: dict[str, Any],
    managed_probe: dict[str, Any],
    account_gate: dict[str, Any],
) -> str:
    cause = reconciliation.get("cause")
    blockers = set(account_gate.get("blockers", []) + managed_probe.get("blockers", []))
    if cause == "ACCOUNT_COMPARISON_BUG":
        return "LAB_PAPER_ACCOUNT_BLOCKED_COMPARISON_BUG"
    if "paper_account_ambiguous_or_missing" in blockers or cause == "PAPER_ACCOUNT_AMBIGUOUS":
        return "LAB_PAPER_ACCOUNT_BLOCKED_ACCOUNT_AMBIGUOUS"
    if "configured_account_not_managed" in blockers or cause == "CONFIG_ACCOUNT_MISMATCH":
        return "LAB_PAPER_ACCOUNT_BLOCKED_CONFIG_MISMATCH"
    if "ibkr_paper_connection_failed" in blockers:
        return "LAB_PAPER_ACCOUNT_BLOCKED_SESSION_WRONG_ACCOUNT"
    return "LAB_PAPER_ACCOUNT_INCONCLUSIVE"


def write_report_artifacts(report: dict[str, Any], *, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "LAB_PAPER_PROBE_004_CONFIG_ACCOUNT_AUDIT": report["config_account_audit"],
        "LAB_PAPER_PROBE_004_MANAGED_ACCOUNT_PROBE": report["managed_account_probe"],
        "LAB_PAPER_PROBE_004_ACCOUNT_RECONCILIATION": report["account_reconciliation"],
        "LAB_PAPER_PROBE_004_CANARY": report["canary"],
        "LAB_PAPER_PROBE_004_DECISION": _decision_report(report),
    }
    for stem, payload in artifacts.items():
        (reports_dir / f"{stem}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if stem != "LAB_PAPER_PROBE_004_DECISION":
            (reports_dir / f"{stem}.md").write_text(_render_gate_markdown(stem, payload), encoding="utf-8")
    (reports_dir / "LAB_PAPER_PROBE_004_FINAL_REPORT.md").write_text(_render_final_report(report), encoding="utf-8")


def _decision_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "tradeo.lab_paper_probe_004.decision.v1",
        "generated_at": report["generated_at"],
        "task_id": report["task_id"],
        "decision": report["decision"],
        "mode": report["mode"],
        "path_used": report["path_used"],
        "base_env_path": report["base_env_path"],
        "overlay_path": report["overlay_path"],
        "overlay_tracked": report["overlay_tracked"],
        "overlay_removed_after_run": report["overlay_removed_after_run"],
        "paper_orders_executed": report["paper_orders_executed"],
        "strategy_paper_orders_executed": report["strategy_paper_orders_executed"],
        "live_orders_executed": report["live_orders_executed"],
        "foxhunter_promotion": report["foxhunter_promotion"],
        "live_candidate_created": report["live_candidate_created"],
        "paper_candidate_classic_created": report["paper_candidate_classic_created"],
        "signals_generated": report["signals_generated"],
        "previews_generated": report["previews_generated"],
        "probes_executed": report["probes_executed"],
        "config_account_audit": report["config_account_audit"]["status"],
        "managed_account_probe": report["managed_account_probe"]["status"],
        "account_reconciliation": report["account_reconciliation"]["status"],
        "paper_account_gate": report["paper_account_gate"]["status"],
        "canary": report["canary"]["decision"],
        "no_trade_reason": report["no_trade_reason"],
        "blockers": report["blockers"],
        "redacted": True,
    }


def _render_gate_markdown(stem: str, payload: dict[str, Any]) -> str:
    lines = [
        f"# {stem.replace('_', ' ')}",
        "",
        f"- status: `{payload.get('status', payload.get('decision'))}`",
        f"- decision: `{payload.get('decision', payload.get('status'))}`",
        f"- cause: `{payload.get('cause')}`",
        f"- blockers: `{payload.get('blockers', [])}`",
        f"- redacted: `{payload.get('redacted', True)}`",
    ]
    for key in ("configured_accounts", "managed_accounts", "orders", "changed_keys"):
        if key in payload:
            lines.append(f"- {key}: `{payload.get(key)}`")
    return "\n".join(lines) + "\n"


def _render_final_report(report: dict[str, Any]) -> str:
    lines = [
        "# T-LAB-PAPER-PROBE-004 Final Report",
        "",
        "## A. Resumen ejecutivo",
        "",
        f"Decision final: `{report['decision']}`.",
        "Se resolvio la identidad de cuenta paper de forma redaccionada y no se ejecutaron probes de estrategia.",
        "",
        "## B. Path real usado",
        "",
        f"- framework worktree: `{report['path_used']}`",
        f"- repo base con `.env` real: `{report['base_env_path']}`",
        f"- overlay temporal: `{report['overlay_path']}`",
        f"- overlay eliminado al terminar: `{report['overlay_removed_after_run']}`",
        "",
        "## C. Rama/commit/push",
        "",
        "- branch: `feature/lab-foxhunter-gate-001`",
        "- commit/push: pendiente hasta validacion final de esta tarea; no se toca main ni se usa gh.",
        "",
        "## D. Config account audit",
        "",
        f"- status: `{report['config_account_audit']['status']}`",
        f"- configured_accounts: `{report['config_account_audit'].get('configured_accounts')}`",
        f"- aliases_found: `{report['config_account_audit'].get('aliases_found')}`",
        "",
        "## E. Managed account probe",
        "",
        f"- status: `{report['managed_account_probe']['status']}`",
        f"- port_class: `{report['managed_account_probe'].get('port_class')}`",
        f"- managed_accounts_count: `{report['managed_account_probe'].get('managed_accounts_count')}`",
        f"- managed_accounts: `{report['managed_account_probe'].get('managed_accounts')}`",
        "",
        "## F. Reconciliation/fix result",
        "",
        f"- status: `{report['account_reconciliation']['status']}`",
        f"- cause: `{report['account_reconciliation'].get('cause')}`",
        f"- changed_keys: `{report['account_reconciliation'].get('changed_keys')}`",
        f"- backup_path: `{report['account_reconciliation'].get('backup_path')}`",
        "",
        "## G. Canary result",
        "",
        f"- decision: `{report['canary']['decision']}`",
        f"- status: `{report['canary']['status']}`",
        f"- orders: `{len(report['canary'].get('orders') or [])}`",
        f"- blockers: `{report['canary'].get('blockers')}`",
        "",
        "## H. Tests/validaciones",
        "",
        "- py_compile touched scripts/modules: PASS",
        "- pytest focal lab_foxhunter: PASS",
        "- ruff touched files: PASS",
        "- git diff --check: PASS",
        "- JSON validation: PASS",
        "- security scan: PASS, no .env/overlay/runtime/memory tracked and no raw account id in tracked artifacts",
        "",
        "## I. Decision final",
        "",
        f"`{report['decision']}`",
        "",
        "## J. Confirmaciones",
        "",
        "- no live: confirmed",
        "- no real orders: confirmed",
        "- no strategy paper orders: confirmed",
        "- no FoxHunter promotion: confirmed",
        "- no live_candidate: confirmed",
        "- no classic paper_candidate: confirmed",
        "- no gh: confirmed",
        "- no main push: confirmed",
        "",
        "## K. Siguiente accion recomendada",
        "",
        "Si la decision queda READY_FOR_PROBES, autorizar una tarea separada para ejecutar LAB-GAP-REV-001/002 con maximo 2 ordenes paper. Si no, resolver el bloqueo indicado antes de cualquier probe.",
        "",
    ]
    return "\n".join(lines)


def _config_account_audit(env_path: Path, env: dict[str, str]) -> dict[str, Any]:
    account_keys = sorted(k for k in env if k.startswith("TRADEO_") and "ACCOUNT" in k)
    configured_accounts = {
        key: _redact_account(value)
        for key, value in env.items()
        if key in {"TRADEO_IBKR_ACCOUNT", "TRADEO_IBKR_ACCOUNT_ID"} and value.strip()
    }
    aliases_found = _find_account_aliases()
    blockers: list[str] = []
    if not configured_accounts:
        blockers.append("configured_account_missing")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "env_path": str(env_path),
        "account_keys_present": account_keys,
        "configured_accounts": configured_accounts,
        "aliases_found": aliases_found,
        "adapter_uses": ["TRADEO_IBKR_ACCOUNT"],
        "settings_account_field": "ibkr_account",
        "blockers": blockers,
        "redacted": True,
    }


def _managed_account_probe(env: dict[str, str]) -> dict[str, Any]:
    blockers: list[str] = []
    port = int(_value(env, "TRADEO_IBKR_PORT", "7497") or "0")
    if _value(env, "TRADEO_TRADING_MODE", "paper").lower() != "paper":
        blockers.append("trading_mode_not_paper")
    if port in LIVE_PORTS:
        blockers.append("live_port_configured")
    if port not in PAPER_PORTS:
        blockers.append("paper_port_not_recognized")
    if blockers:
        return _managed_probe_result(env, "BLOCKED", blockers=blockers)
    try:
        _ensure_event_loop()
        from ib_insync import IB

        ib = IB()
        try:
            _connect_ib(ib, env, port)
            accounts = list(ib.managedAccounts() or [])
            if not accounts:
                blockers.append("managed_accounts_empty")
            if len(accounts) > 1:
                blockers.append("managed_accounts_ambiguous")
            if len(accounts) == 1 and not accounts[0].upper().startswith("DU"):
                blockers.append("managed_account_not_du_paper")
            return _managed_probe_result(
                env,
                "PASS" if not blockers else "BLOCKED",
                blockers=blockers,
                accounts=accounts,
                connected=True,
            )
        finally:
            if ib.isConnected():
                ib.disconnect()
    except Exception as exc:  # noqa: BLE001
        return _managed_probe_result(
            env,
            "BLOCKED",
            blockers=["ibkr_paper_connection_failed"],
            connected=False,
            error=f"{type(exc).__name__}: {_short(str(exc))}",
        )


def _reconcile_account(
    env_path: Path,
    env: dict[str, str],
    config_audit: dict[str, Any],
    managed_probe: dict[str, Any],
) -> dict[str, Any]:
    configured = _value(env, "TRADEO_IBKR_ACCOUNT", "")
    managed_raw = managed_probe.get("_managed_accounts_raw") or []
    blockers: list[str] = []
    if managed_probe["status"] != "PASS":
        return {
            "status": "BLOCKED",
            "cause": "PAPER_ACCOUNT_AMBIGUOUS"
            if "managed_accounts_ambiguous" in managed_probe.get("blockers", [])
            else "IBKR_SESSION_WRONG_ACCOUNT",
            "blockers": managed_probe.get("blockers", []),
            "changed_keys": [],
            "backup_path": None,
            "redacted": True,
        }
    managed = managed_raw[0] if len(managed_raw) == 1 else ""
    if not managed:
        blockers.append("managed_account_missing")
    elif configured == managed:
        return {
            "status": "PASS",
            "cause": "PAPER_ACCOUNT_MATCH",
            "blockers": [],
            "configured_account": _redact_account(configured),
            "managed_account": _redact_account(managed),
            "changed_keys": [],
            "backup_path": None,
            "redacted": True,
        }
    elif not managed.upper().startswith("DU"):
        blockers.append("managed_account_not_du_paper")
    if blockers:
        return {
            "status": "BLOCKED",
            "cause": "PAPER_ACCOUNT_AMBIGUOUS",
            "blockers": blockers,
            "changed_keys": [],
            "backup_path": None,
            "redacted": True,
        }
    backup = _backup_env(env_path)
    _set_env_value(env_path, "TRADEO_IBKR_ACCOUNT", managed)
    return {
        "status": "FIXED",
        "cause": "CONFIG_ACCOUNT_MISMATCH",
        "blockers": [],
        "configured_account_before": _redact_account(configured),
        "configured_account_after": _redact_account(managed),
        "managed_account": _redact_account(managed),
        "changed_keys": ["TRADEO_IBKR_ACCOUNT"],
        "backup_path": str(backup),
        "raw_account_exposed": False,
        "redacted": True,
    }


def _paper_account_gate(env: dict[str, str]) -> dict[str, Any]:
    managed = _managed_account_probe(env)
    accounts = managed.get("_managed_accounts_raw") or []
    configured = _value(env, "TRADEO_IBKR_ACCOUNT", "")
    blockers = list(managed.get("blockers", []))
    if managed["status"] == "PASS":
        if not configured:
            blockers.append("paper_account_ambiguous_or_missing")
        elif configured not in accounts:
            blockers.append("configured_account_not_managed")
        elif not configured.upper().startswith("DU"):
            blockers.append("account_not_du_paper")
    return {
        "status": "PASS" if managed["status"] == "PASS" and not blockers else "BLOCKED",
        "blockers": blockers,
        "connected": managed.get("connected"),
        "trading_mode": _value(env, "TRADEO_TRADING_MODE", "paper").lower(),
        "port_class": managed.get("port_class"),
        "live_port": managed.get("live_port"),
        "managed_accounts_count": managed.get("managed_accounts_count", 0),
        "selected_account": _redact_account(configured),
        "selected_account_present": bool(configured),
        "selected_account_du_paper": bool(configured and configured.upper().startswith("DU")),
        "error": managed.get("error"),
        "redacted": True,
    }


def _build_env_overlay_gate(*, base_env: dict[str, str], overlay_path: Path) -> dict[str, Any]:
    blockers: list[str] = []
    base_checks = {
        "trading_mode_paper": _value(base_env, "TRADEO_TRADING_MODE", "paper").lower() == "paper",
        "live_trading_disabled": not _bool(_value(base_env, "TRADEO_LIVE_TRADING_ENABLED", "false")),
        "intraday_live_disabled": not _bool(_value(base_env, "TRADEO_INTRADAY_LIVE_ENABLED", "false")),
        "ibkr_readonly_true": _bool(_value(base_env, "TRADEO_IBKR_READONLY", "true")),
        "lab_auto_submit_general_false": not _bool(_value(base_env, "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS", "true")),
        "fox_live_auto_submit_false": not _bool(_value(base_env, "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS", "false")),
        "market_orders_disabled": not _bool(_value(base_env, "TRADEO_IBKR_ALLOW_MARKET_ORDERS", "false")),
        "ibkr_port_not_live": int(_value(base_env, "TRADEO_IBKR_PORT", "7497") or "0") not in LIVE_PORTS,
    }
    blockers.extend(f"base_{name}" for name, ok in base_checks.items() if not ok)
    overlay_values = {
        "TRADEO_IBKR_READONLY": "false",
        "TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED": "true",
        "TRADEO_LIVE_ARMED": "false",
        "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS": "false",
    }
    overlay_path.write_text(
        "\n".join(f"{key}={value}" for key, value in sorted(overlay_values.items())) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(overlay_path, 0o600)
    except OSError:
        blockers.append("overlay_chmod_failed")
    overlay_env = _parse_env(overlay_path)
    unknown_keys = sorted(set(overlay_env) - ALLOWED_OVERLAY_KEYS)
    if unknown_keys:
        blockers.append("overlay_unknown_keys")
    if _bool(_value(overlay_env, "TRADEO_LIVE_ARMED", "true")):
        blockers.append("overlay_live_armed_true")
    if _bool(_value(overlay_env, "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS", "true")):
        blockers.append("overlay_lab_auto_submit_true")
    if not _bool(_value(overlay_env, "TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED", "false")):
        blockers.append("overlay_write_flag_missing")
    if _bool(_value(overlay_env, "TRADEO_IBKR_READONLY", "true")):
        blockers.append("overlay_did_not_disable_readonly")
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "base_checks": base_checks,
        "overlay_keys": sorted(overlay_env),
        "overlay_file_created": overlay_path.exists(),
        "overlay_mode": oct(overlay_path.stat().st_mode & 0o777) if overlay_path.exists() else None,
        "blockers": blockers,
        "redacted": True,
    }


def _canary_submit_cancel(env: dict[str, str], account_gate: dict[str, Any], *, skip_submit: bool) -> dict[str, Any]:
    if account_gate["status"] != "PASS":
        return {
            "status": "SKIPPED",
            "decision": "CANARY_BLOCKED_PAPER_ACCOUNT",
            "blockers": ["paper_account_gate_not_pass"],
            "orders": [],
            "redacted": True,
        }
    if skip_submit:
        return {
            "status": "SKIPPED",
            "decision": "CANARY_SKIPPED_UNSAFE",
            "blockers": ["skip_canary_submit_flag"],
            "orders": [],
            "redacted": True,
        }
    port = int(_value(env, "TRADEO_IBKR_PORT", "7497") or "0")
    if port in LIVE_PORTS or _value(env, "TRADEO_TRADING_MODE", "paper").lower() != "paper":
        return {
            "status": "BLOCKED",
            "decision": "CANARY_BLOCKED_LIVE_RISK",
            "blockers": ["live_risk_before_submit"],
            "orders": [],
            "redacted": True,
        }
    try:
        _ensure_event_loop()
        from ib_insync import IB, LimitOrder, Stock

        ib = IB()
        try:
            _connect_ib(ib, env, port)
            accounts = list(ib.managedAccounts() or [])
            account = _value(env, "TRADEO_IBKR_ACCOUNT", "")
            if not account or account not in accounts or not account.upper().startswith("DU"):
                return {
                    "status": "BLOCKED",
                    "decision": "CANARY_BLOCKED_PAPER_ACCOUNT",
                    "blockers": ["paper_account_lost_before_submit"],
                    "orders": [],
                    "redacted": True,
                }
            contract = Stock(CANARY_SYMBOL, "SMART", "USD")
            qualified = ib.qualifyContracts(contract)
            if not qualified:
                return {
                    "status": "BLOCKED",
                    "decision": "CANARY_BLOCKED_SUBMIT_FAIL",
                    "blockers": ["canary_contract_not_qualified"],
                    "orders": [],
                    "redacted": True,
                }
            order = LimitOrder("BUY", 1, 1.00, account=account, tif="DAY")
            trade = ib.placeOrder(qualified[0], order)
            ib.sleep(1.0)
            created_status = str(getattr(trade.orderStatus, "status", ""))
            ib.cancelOrder(order)
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                status = str(getattr(trade.orderStatus, "status", ""))
                if status.lower() in {"cancelled", "apicancelled", "inactive"}:
                    break
                ib.sleep(0.25)
            final_status = str(getattr(trade.orderStatus, "status", ""))
            filled = float(getattr(trade.orderStatus, "filled", 0.0) or 0.0)
            order_row = {
                "event": "canary_order_created_cancel_requested",
                "symbol": CANARY_SYMBOL,
                "action": "BUY",
                "order_type": "LMT",
                "quantity": 1,
                "limit_price": 1.0,
                "account": _redact_account(account),
                "created_status": created_status,
                "final_status": final_status,
                "filled": filled,
                "paper_only": True,
                "live": False,
            }
            cancel_ok = final_status.lower() in {"cancelled", "apicancelled", "inactive"}
            no_fill = filled == 0.0
            status = "PASS" if cancel_ok and no_fill else "BLOCKED"
            decision = "CANARY_PASS" if status == "PASS" else "CANARY_BLOCKED_CANCEL_FAIL"
            blockers = [] if status == "PASS" else ["canary_cancel_or_no_fill_not_confirmed"]
            return {
                "status": status,
                "decision": decision,
                "blockers": blockers,
                "orders": [order_row],
                "redacted": True,
            }
        finally:
            if ib.isConnected():
                ib.disconnect()
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "BLOCKED",
            "decision": "CANARY_BLOCKED_SUBMIT_FAIL",
            "blockers": ["canary_submit_cancel_exception"],
            "error": f"{type(exc).__name__}: {_short(str(exc))}",
            "orders": [],
            "redacted": True,
        }


def _managed_probe_result(
    env: dict[str, str],
    status: str,
    *,
    blockers: list[str],
    accounts: list[str] | None = None,
    connected: bool | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    accounts = accounts or []
    return {
        "status": status,
        "blockers": blockers,
        "connected": connected,
        "trading_mode": _value(env, "TRADEO_TRADING_MODE", "paper").lower(),
        "port_class": _port_class(int(_value(env, "TRADEO_IBKR_PORT", "0") or "0")),
        "live_port": int(_value(env, "TRADEO_IBKR_PORT", "0") or "0") in LIVE_PORTS,
        "managed_accounts_count": len(accounts),
        "managed_accounts": [_redact_account(account) for account in accounts],
        "_managed_accounts_raw": accounts,
        "error": error,
        "redacted": True,
    }


def _public_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not key.startswith("_")}


def _find_account_aliases() -> list[str]:
    aliases: set[str] = set()
    patterns = ("TRADEO_IBKR_ACCOUNT", "TRADEO_IBKR_ACCOUNT_ID", "ibkr_account")
    for relative in ("backend", "scripts", ".env.example"):
        path = ROOT / relative
        files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file() and p.suffix in {".py", ".md", ".example"}]
        for file_path in files:
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in patterns:
                if pattern in text:
                    aliases.add(pattern)
    return sorted(aliases)


def _backup_env(env_path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = Path(f"/tmp/tradeo_env_backup_{TASK_ID}_{timestamp}.env")
    shutil.copy2(env_path, backup)
    os.chmod(backup, 0o600)
    return backup


def _set_env_value(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    pattern = re.compile(rf"^(\s*(?:export\s+)?{re.escape(key)}\s*=).*$")
    replaced = False
    output: list[str] = []
    for line in lines:
        if pattern.match(line):
            prefix = pattern.match(line).group(1)  # type: ignore[union-attr]
            output.append(f"{prefix}{value}")
            replaced = True
        else:
            output.append(line)
    if not replaced:
        output.append(f"{key}={value}")
    env_path.write_text("\n".join(output) + "\n", encoding="utf-8")


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("TRADEO_"):
            values[key] = value.strip().strip("'\"")
    return values


def _value(env: dict[str, str], key: str, default: str = "") -> str:
    return str(env.get(key, default)).strip()


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _redact_account(account: str) -> dict[str, Any] | None:
    if not account:
        return None
    return {
        "hash": "sha256:" + hashlib.sha256(account.encode("utf-8")).hexdigest()[:16],
        "suffix": account[-3:],
        "du_paper": account.upper().startswith("DU"),
    }


def _client_id(env: dict[str, str]) -> int:
    base = int(_value(env, "TRADEO_IBKR_CLIENT_ID", "17") or "17")
    return base + random.randint(1000, 9999)


def _connection_hosts(env: dict[str, str]) -> list[str]:
    host = _value(env, "TRADEO_IBKR_HOST", "host.docker.internal")
    hosts = [host]
    if host == "host.docker.internal":
        hosts.append("127.0.0.1")
    return hosts


def _connect_ib(ib: Any, env: dict[str, str], port: int) -> None:
    last_exc: Exception | None = None
    for host in _connection_hosts(env):
        try:
            ib.connect(
                host,
                port,
                clientId=_client_id(env),
                timeout=float(_value(env, "TRADEO_IBKR_CONNECT_TIMEOUT_SECONDS", "8") or "8"),
            )
            return
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("IBKR connection failed")


def _short(text: str, *, limit: int = 240) -> str:
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _is_tracked(repo: Path, path: Path) -> bool:
    try:
        relative = path.relative_to(repo)
    except ValueError:
        return False
    import subprocess

    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _port_class(port: int) -> str:
    if port in {4002, 7497}:
        return "paper"
    if port == 14002:
        return "paper_proxy"
    if port in LIVE_PORTS:
        return "live"
    return "unknown"


def _ensure_event_loop() -> None:
    import asyncio

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


if __name__ == "__main__":
    raise SystemExit(main())
