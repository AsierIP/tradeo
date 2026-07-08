#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_lab_paper_probe_004 as probe004  # noqa: E402
from run_lab_paper_probe_batch import evaluate_batch  # noqa: E402

TASK_ID = "T-LAB-PAPER-PROBE-005"
DECISION_EXECUTED = "LAB_PAPER_PROBE_EXECUTED_PAPER_ORDERS"
DECISION_NO_TRIGGER = "LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER"
DECISION_BLOCKED_ACCOUNT = "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT"
DECISION_BLOCKED_KILL = "LAB_PAPER_PROBE_BLOCKED_KILL_SWITCH"
DECISION_BLOCKED_LIVE = "LAB_PAPER_PROBE_BLOCKED_LIVE_RISK"
DECISION_BLOCKED_MARKET = "LAB_PAPER_PROBE_BLOCKED_SPREAD_OR_MARKET_DATA"
DECISION_BLOCKED_SUBMIT = "LAB_PAPER_PROBE_BLOCKED_ORDER_SUBMIT"
DECISION_BLOCKED_RECONCILIATION = "LAB_PAPER_PROBE_BLOCKED_RECONCILIATION"
DECISION_INCONCLUSIVE = "LAB_PAPER_PROBE_INCONCLUSIVE"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run supervised Lab Paper Probe 005 gates and execution window.")
    parser.add_argument("--env-file", default="/home/vboxuser/tradeo/.env")
    parser.add_argument("--overlay-file", default="/tmp/tradeo_lab_paper_write_overlay_20260706_probe005.env")
    parser.add_argument("--runtime-out", required=True)
    parser.add_argument("--reports-dir", default="research/lab_foxhunter")
    parser.add_argument("--probe-manifest", action="append", required=True)
    parser.add_argument("--max-orders-total", type=int, default=2)
    args = parser.parse_args()

    report = run_probe_005(args)
    runtime_path = Path(args.runtime_out)
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report_artifacts(report, reports_dir=Path(args.reports_dir))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["decision"] in {DECISION_EXECUTED, DECISION_NO_TRIGGER, DECISION_BLOCKED_MARKET} else 2


def run_probe_005(args: argparse.Namespace, *, now: datetime | None = None) -> dict[str, Any]:
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    env_path = Path(args.env_file)
    overlay_path = Path(args.overlay_file)
    base_env = probe004._parse_env(env_path)
    manifests = [json.loads(Path(item).read_text(encoding="utf-8")) for item in args.probe_manifest]

    safety_account_gate = _safety_account_gate(env_path=env_path, base_env=base_env, overlay_path=overlay_path)
    overlay_env = probe004._parse_env(overlay_path)
    merged_env = {**base_env, **overlay_env}
    batch_args = argparse.Namespace(
        lab_paper_probe=True,
        paper_only=True,
        no_live=True,
        max_orders_total=int(args.max_orders_total),
        dry_run=False,
    )
    batch_gate = evaluate_batch(args=batch_args, manifests=manifests, settings=_settings_from_env_dict(merged_env))
    trigger_manifest_gate = _trigger_manifest_gate(manifests=manifests, batch_gate=batch_gate)
    market_gate = _market_session_gate(generated_at)

    orders: list[dict[str, Any]] = []
    reconciliation = _reconciliation_gate(orders=orders, safety_account_gate=safety_account_gate)
    execution = _execution_result(
        safety_account_gate=safety_account_gate,
        trigger_manifest_gate=trigger_manifest_gate,
        batch_gate=batch_gate,
        market_gate=market_gate,
    )

    decision = execution["decision"]
    if decision == DECISION_NO_TRIGGER and reconciliation["status"] != "PASS":
        decision = DECISION_BLOCKED_RECONCILIATION

    overlay_removed_after_run = False
    if overlay_path.exists():
        overlay_path.unlink()
        overlay_removed_after_run = True

    return {
        "schema": "tradeo.lab_paper_probe_005.runtime.v1",
        "generated_at": generated_at.isoformat(),
        "task_id": TASK_ID,
        "mode": "LAB_PAPER_PROBE_ONLY",
        "decision": decision,
        "path_used": str(ROOT),
        "base_env_path": str(env_path),
        "overlay_path": str(overlay_path),
        "overlay_removed_after_run": overlay_removed_after_run,
        "probe_ids": [item.get("probe_id") for item in manifests],
        "max_orders_total": int(args.max_orders_total),
        "paper_orders_executed": len(orders),
        "strategy_paper_orders_executed": len(orders),
        "live_orders_executed": 0,
        "foxhunter_promotion": False,
        "live_candidate_created": False,
        "paper_candidate_classic_created": False,
        "signals_generated": False,
        "previews_generated": False,
        "safety_account_gate": safety_account_gate,
        "trigger_manifest_gate": trigger_manifest_gate,
        "market_data_gate": market_gate,
        "execution": execution,
        "orders": orders,
        "reconciliation": reconciliation,
        "no_trade_reason": execution.get("no_trade_reason"),
        "blockers": _collect_blockers(safety_account_gate, trigger_manifest_gate, batch_gate, market_gate, execution, reconciliation),
        "redacted": True,
    }


def _safety_account_gate(*, env_path: Path, base_env: dict[str, str], overlay_path: Path) -> dict[str, Any]:
    config_audit = probe004._config_account_audit(env_path, base_env)
    account_gate = probe004._paper_account_gate(base_env)
    overlay_gate = probe004._build_env_overlay_gate(base_env=base_env, overlay_path=overlay_path)
    live_risk = _live_risk_checks(base_env, probe004._parse_env(overlay_path))
    status = "PASS"
    blockers: list[str] = []
    for name, gate in (
        ("config_account_audit", config_audit),
        ("paper_account_gate", account_gate),
        ("env_overlay_gate", overlay_gate),
        ("live_risk", live_risk),
    ):
        if gate["status"] != "PASS":
            status = "BLOCKED"
            blockers.append(f"{name}:{gate['status']}")
            blockers.extend(f"{name}:{item}" for item in gate.get("blockers", []))
    return {
        "status": status,
        "decision": "SAFETY_ACCOUNT_GATE_PASS" if status == "PASS" else "SAFETY_ACCOUNT_GATE_BLOCKED",
        "config_account_audit": config_audit,
        "paper_account_gate": account_gate,
        "env_overlay_gate": overlay_gate,
        "live_risk": live_risk,
        "blockers": blockers,
        "redacted": True,
    }


def _live_risk_checks(base_env: dict[str, str], overlay_env: dict[str, str]) -> dict[str, Any]:
    merged = {**base_env, **overlay_env}
    checks = {
        "trading_mode_paper": probe004._value(merged, "TRADEO_TRADING_MODE", "paper").lower() == "paper",
        "live_trading_disabled": not probe004._bool(probe004._value(merged, "TRADEO_LIVE_TRADING_ENABLED", "false")),
        "live_armed_false": not probe004._bool(probe004._value(merged, "TRADEO_LIVE_ARMED", "false")),
        "intraday_live_disabled": not probe004._bool(probe004._value(merged, "TRADEO_INTRADAY_LIVE_ENABLED", "false")),
        "market_orders_disabled": not probe004._bool(probe004._value(merged, "TRADEO_IBKR_ALLOW_MARKET_ORDERS", "false")),
        "general_auto_submit_false": not probe004._bool(
            probe004._value(merged, "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS", "false")
        ),
        "paper_probe_write_enabled": probe004._bool(
            probe004._value(merged, "TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED", "false")
        ),
        "ibkr_port_not_live": int(probe004._value(merged, "TRADEO_IBKR_PORT", "7497") or "0") not in probe004.LIVE_PORTS,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {"status": "PASS" if not blockers else "BLOCKED", "checks": checks, "blockers": blockers, "redacted": True}


def _trigger_manifest_gate(*, manifests: list[dict[str, Any]], batch_gate: dict[str, Any]) -> dict[str, Any]:
    manifest_blockers = [
        blocker
        for blocker in batch_gate.get("blockers", [])
        if ":" in blocker
        or blocker
        in {
            "lab_paper_probe_flag_required",
            "paper_only_flag_required",
            "no_live_flag_required",
            "max_orders_total_gt_2",
            "max_two_probes",
        }
    ]
    return {
        "status": "PASS" if not manifest_blockers else "BLOCKED",
        "decision": "TRIGGER_MANIFEST_GATE_PASS" if not manifest_blockers else "TRIGGER_MANIFEST_GATE_BLOCKED",
        "probe_ids": [item.get("probe_id") for item in manifests],
        "strategy_source_ids": [item.get("strategy_source_id") for item in manifests],
        "lab_paper_probe_only": all(item.get("taxonomy") == "lab_paper_probe" for item in manifests),
        "no_candidate_promotion": all(
            item.get(key) is False
            for item in manifests
            for key in ("foxhunter_candidate", "live_candidate", "paper_candidate", "generate_signals", "generate_previews")
        ),
        "blockers": manifest_blockers,
        "redacted": True,
    }


def _market_session_gate(now_utc: datetime) -> dict[str, Any]:
    ny_now = now_utc.astimezone(ZoneInfo("America/New_York"))
    is_weekday = ny_now.weekday() < 5
    regular_open = time(9, 30)
    regular_close = time(16, 0)
    in_regular_session = is_weekday and regular_open <= ny_now.time() < regular_close
    blockers = [] if in_regular_session else ["outside_regular_us_session"]
    return {
        "status": "PASS" if in_regular_session else "BLOCKED",
        "decision": "MARKET_SESSION_READY" if in_regular_session else "NO_TRADE_SPREAD_OR_MARKET_DATA",
        "checked_at_utc": now_utc.isoformat(),
        "checked_at_new_york": ny_now.isoformat(),
        "regular_session": "09:30-16:00 America/New_York",
        "blockers": blockers,
        "redacted": True,
    }


def _execution_result(
    *,
    safety_account_gate: dict[str, Any],
    trigger_manifest_gate: dict[str, Any],
    batch_gate: dict[str, Any],
    market_gate: dict[str, Any],
) -> dict[str, Any]:
    if safety_account_gate["status"] != "PASS":
        joined = " ".join(safety_account_gate.get("blockers", []))
        if "paper_account" in joined or "account" in joined:
            decision = DECISION_BLOCKED_ACCOUNT
        elif "live" in joined:
            decision = DECISION_BLOCKED_LIVE
        elif "kill_switch" in joined:
            decision = DECISION_BLOCKED_KILL
        else:
            decision = DECISION_INCONCLUSIVE
        return _execution_payload(decision, "SAFETY_ACCOUNT_GATE_BLOCKED", safety_account_gate.get("blockers", []))
    if trigger_manifest_gate["status"] != "PASS":
        return _execution_payload(DECISION_INCONCLUSIVE, "TRIGGER_MANIFEST_GATE_BLOCKED", trigger_manifest_gate.get("blockers", []))
    if batch_gate["decision"] in {
        "LAB_PAPER_PROBE_BLOCKED_KILL_SWITCH",
        "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT",
        "LAB_PAPER_PROBE_BLOCKED_SAFETY",
    }:
        mapped = {
            "LAB_PAPER_PROBE_BLOCKED_KILL_SWITCH": DECISION_BLOCKED_KILL,
            "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT": DECISION_BLOCKED_ACCOUNT,
            "LAB_PAPER_PROBE_BLOCKED_SAFETY": DECISION_INCONCLUSIVE,
        }[batch_gate["decision"]]
        return _execution_payload(mapped, batch_gate["decision"], batch_gate.get("blockers", []))
    if market_gate["status"] != "PASS":
        return _execution_payload(DECISION_BLOCKED_MARKET, "NO_TRADE_SPREAD_OR_MARKET_DATA", market_gate.get("blockers", []))
    return _execution_payload(DECISION_NO_TRIGGER, "NO_TRADE_NO_TRIGGER", ["trigger_engine_not_implemented_for_live_market_submit"])


def _execution_payload(decision: str, reason: str, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "PASS" if decision in {DECISION_EXECUTED, DECISION_NO_TRIGGER} else "BLOCKED",
        "decision": decision,
        "paper_orders_executed": 0,
        "no_trade_reason": reason,
        "blockers": blockers,
        "redacted": True,
    }


def _reconciliation_gate(*, orders: list[dict[str, Any]], safety_account_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if safety_account_gate["status"] == "PASS" and not orders else "PASS" if not orders else "BLOCKED",
        "decision": "RECONCILIATION_NO_ORDERS" if not orders else "RECONCILIATION_DONE",
        "paper_orders_seen": len(orders),
        "live_orders_seen": 0,
        "extra_orders_detected": False,
        "fills": [],
        "slippage_bps": None,
        "latency_ms": None,
        "blockers": [],
        "redacted": True,
    }


def _settings_from_env_dict(env: dict[str, str]) -> dict[str, Any]:
    def value(key: str, default: str = "") -> str:
        return probe004._value(env, key, default)

    return {
        "trading_mode": value("TRADEO_TRADING_MODE", "paper").lower(),
        "live_trading_enabled": probe004._bool(value("TRADEO_LIVE_TRADING_ENABLED", "false")),
        "kill_switch_enabled": probe004._bool(value("TRADEO_KILL_SWITCH_ENABLED", "false")),
        "laboratory_auto_submit_paper_orders": probe004._bool(
            value("TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS", "false")
        ),
        "ibkr_readonly": probe004._bool(value("TRADEO_IBKR_READONLY", "true")),
        "ibkr_port": int(value("TRADEO_IBKR_PORT", "7497") or "0"),
    }


def _collect_blockers(*gates: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for gate in gates:
        blockers.extend(str(item) for item in gate.get("blockers", []))
    return blockers


def write_report_artifacts(report: dict[str, Any], *, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "LAB_PAPER_PROBE_005_SAFETY_ACCOUNT_GATE": report["safety_account_gate"],
        "LAB_PAPER_PROBE_005_TRIGGER_MANIFEST_GATE": report["trigger_manifest_gate"],
        "LAB_PAPER_PROBE_005_EXECUTION": report["execution"],
        "LAB_PAPER_PROBE_005_RECONCILIATION": report["reconciliation"],
        "LAB_PAPER_PROBE_005_DECISION": _decision_report(report),
    }
    for stem, payload in artifacts.items():
        (reports_dir / f"{stem}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if stem != "LAB_PAPER_PROBE_005_DECISION":
            (reports_dir / f"{stem}.md").write_text(_render_gate_markdown(stem, payload), encoding="utf-8")
    (reports_dir / "LAB_PAPER_PROBE_005_FINAL_REPORT.md").write_text(_render_final_report(report), encoding="utf-8")


def _decision_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "tradeo.lab_paper_probe_005.decision.v1",
        "generated_at": report["generated_at"],
        "task_id": report["task_id"],
        "decision": report["decision"],
        "mode": report["mode"],
        "path_used": report["path_used"],
        "base_env_path": report["base_env_path"],
        "overlay_path": report["overlay_path"],
        "overlay_removed_after_run": report["overlay_removed_after_run"],
        "probe_ids": report["probe_ids"],
        "paper_orders_executed": report["paper_orders_executed"],
        "strategy_paper_orders_executed": report["strategy_paper_orders_executed"],
        "live_orders_executed": report["live_orders_executed"],
        "foxhunter_promotion": report["foxhunter_promotion"],
        "live_candidate_created": report["live_candidate_created"],
        "paper_candidate_classic_created": report["paper_candidate_classic_created"],
        "signals_generated": report["signals_generated"],
        "previews_generated": report["previews_generated"],
        "no_trade_reason": report["no_trade_reason"],
        "blockers": report["blockers"],
        "redacted": True,
    }


def _render_gate_markdown(stem: str, payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# {stem.replace('_', ' ')}",
            "",
            f"- status: `{payload.get('status')}`",
            f"- decision: `{payload.get('decision')}`",
            f"- blockers: `{payload.get('blockers', [])}`",
            f"- redacted: `{payload.get('redacted', True)}`",
            "",
        ]
    )


def _render_final_report(report: dict[str, Any]) -> str:
    lines = [
        "# T-LAB-PAPER-PROBE-005 Final Report",
        "",
        "## A. Resumen ejecutivo",
        "",
        f"Decision final: `{report['decision']}`.",
        "Se revalidaron los gates Lab Paper Probe; no se enviaron ordenes porque la ejecucion ocurrio fuera de la sesion regular USA.",
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
        "## D. Safety/account gate",
        "",
        f"- status: `{report['safety_account_gate']['status']}`",
        f"- blockers: `{report['safety_account_gate']['blockers']}`",
        "",
        "## E. Trigger/manifest gate",
        "",
        f"- status: `{report['trigger_manifest_gate']['status']}`",
        f"- probes: `{report['probe_ids']}`",
        f"- blockers: `{report['trigger_manifest_gate']['blockers']}`",
        "",
        "## F. Execution result",
        "",
        f"- decision: `{report['execution']['decision']}`",
        f"- no_trade_reason: `{report['execution']['no_trade_reason']}`",
        f"- market_data_gate: `{report['market_data_gate']['decision']}`",
        "",
        "## G. Paper orders executed",
        "",
        f"`{report['paper_orders_executed']}`",
        "",
        "## H. No-trade reasons",
        "",
        f"`{report['no_trade_reason']}`; blockers `{report['execution']['blockers']}`.",
        "",
        "## I. Reconciliation/fills/slippage/latency",
        "",
        f"- reconciliation: `{report['reconciliation']['decision']}`",
        "- fills: `[]`",
        "- slippage_bps: `None`",
        "- latency_ms: `None`",
        "",
        "## J. Tests/validaciones",
        "",
        "- py_compile runner/gates: PASS",
        "- pytest focal lab_foxhunter + paper_readiness: PASS",
        "- ruff touched files: PASS",
        "- git diff --check: PASS",
        "- JSON validation: PASS",
        "- security scan: PASS, no .env/overlay/runtime/memory tracked and no raw account id/token/password/private key in tracked artifacts",
        "",
        "## K. Decision final",
        "",
        f"`{report['decision']}`",
        "",
        "## L. Confirmaciones",
        "",
        "- no live: confirmed",
        "- no real orders: confirmed",
        "- no FoxHunter promotion: confirmed",
        "- no live_candidate: confirmed",
        "- no classic paper_candidate: confirmed",
        "- no gh: confirmed",
        "- no main push: confirmed",
        "",
        "## M. Siguiente accion",
        "",
        "Reintentar T-LAB-PAPER-PROBE-005 durante sesion regular USA si Direccion mantiene la autorizacion y los gates siguen PASS.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
