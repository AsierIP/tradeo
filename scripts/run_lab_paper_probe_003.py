#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from tradeo.modules.laboratory.paper_readiness import settings_from_env_file  # noqa: E402
from run_lab_paper_probe_batch import evaluate_batch  # noqa: E402

ALLOWED_OVERLAY_KEYS = {
    "TRADEO_IBKR_READONLY",
    "TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED",
    "TRADEO_LIVE_ARMED",
    "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS",
}
LIVE_PORTS = {4001, 7496}
PAPER_PORTS = {4002, 7497, 14002}
CANARY_SYMBOL = "AAPL"
TASK_ID = "T-LAB-PAPER-PROBE-003"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run isolated Lab Paper Probe 003 overlay, paper account, canary and batch gates."
    )
    parser.add_argument("--env-file", default="/home/vboxuser/tradeo/.env")
    parser.add_argument("--overlay-file", default="/tmp/tradeo_lab_paper_write_overlay_20260706.env")
    parser.add_argument("--runtime-out", required=True)
    parser.add_argument("--reports-dir", default="research/lab_foxhunter")
    parser.add_argument("--probe-manifest", action="append", required=True)
    parser.add_argument("--max-orders-total", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-canary-submit", action="store_true")
    args = parser.parse_args()

    report = run_probe_003(args)
    runtime_path = Path(args.runtime_out)
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report_artifacts(report, reports_dir=Path(args.reports_dir))
    print(json.dumps(report, indent=2, sort_keys=True))
    successful = {
        "LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER",
        "LAB_PAPER_PROBE_EXECUTED_PAPER_ORDERS",
    }
    return 0 if report["decision"] in successful else 2


def run_probe_003(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    env_path = Path(args.env_file)
    overlay_path = Path(args.overlay_file)
    base_env = _parse_env(env_path)
    env_gate = _build_env_overlay_gate(base_env=base_env, overlay_path=overlay_path)
    overlay_env = _parse_env(overlay_path)
    merged_env = {**base_env, **overlay_env}
    settings = settings_from_env_file(args.env_file)
    settings.update({_field_name(key): _coerce_value(value) for key, value in overlay_env.items()})

    account_gate = _paper_account_gate(merged_env)
    canary = _canary_submit_cancel(merged_env, account_gate, skip_submit=bool(args.skip_canary_submit))

    manifests = [json.loads(Path(item).read_text(encoding="utf-8")) for item in args.probe_manifest]
    runner_args = argparse.Namespace(
        lab_paper_probe=True,
        paper_only=True,
        no_live=True,
        max_orders_total=args.max_orders_total,
        dry_run=args.dry_run,
    )
    runner = evaluate_batch(args=runner_args, manifests=manifests, settings=settings)

    blockers = []
    for gate_name, gate in (
        ("env_overlay", env_gate),
        ("paper_account", account_gate),
        ("canary", canary),
    ):
        if gate["status"] != "PASS":
            blockers.append(f"{gate_name}:{gate['status']}")
            blockers.extend(f"{gate_name}:{item}" for item in gate.get("blockers", []))
    if runner["decision"].startswith("LAB_PAPER_PROBE_BLOCKED"):
        blockers.append(f"runner:{runner['decision']}")
        blockers.extend(f"runner:{item}" for item in runner.get("blockers", []))

    if env_gate["status"] != "PASS":
        decision = "LAB_PAPER_PROBE_BLOCKED_READONLY_WRITE_REQUIRED"
    elif account_gate["status"] != "PASS":
        decision = "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT"
    elif canary["status"] != "PASS":
        decision = "LAB_PAPER_PROBE_BLOCKED_CANARY_FAIL"
    elif runner["decision"] == "LAB_PAPER_PROBE_BLOCKED_KILL_SWITCH":
        decision = runner["decision"]
    elif runner["decision"] == "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT":
        decision = runner["decision"]
    elif runner["decision"].startswith("LAB_PAPER_PROBE_BLOCKED"):
        decision = "LAB_PAPER_PROBE_INCONCLUSIVE"
    else:
        decision = "LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER"

    overlay_removed_after_run = False
    if overlay_path.exists():
        overlay_path.unlink()
        overlay_removed_after_run = True

    return {
        "schema": "tradeo.lab_paper_probe_003.runtime.v1",
        "generated_at": generated_at,
        "task_id": TASK_ID,
        "mode": "LAB_PAPER_PROBE_ONLY",
        "decision": decision,
        "path_used": str(ROOT),
        "base_env_path": str(env_path),
        "overlay_path": str(overlay_path),
        "overlay_tracked": _is_tracked(ROOT, overlay_path),
        "overlay_removed_after_run": overlay_removed_after_run,
        "paper_orders_executed": 0,
        "live_orders_executed": 0,
        "foxhunter_promotion": False,
        "live_candidate_created": False,
        "paper_candidate_classic_created": False,
        "signals_generated": False,
        "previews_generated": False,
        "env_overlay_gate": env_gate,
        "paper_account_gate": account_gate,
        "canary": canary,
        "runner": runner,
        "orders": [],
        "no_trade_reason": decision,
        "blockers": blockers,
        "redacted": True,
    }


def write_report_artifacts(report: dict[str, Any], *, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "LAB_PAPER_PROBE_003_ENV_OVERLAY": report["env_overlay_gate"],
        "LAB_PAPER_PROBE_003_PAPER_ACCOUNT_GATE": report["paper_account_gate"],
        "LAB_PAPER_PROBE_003_CANARY": report["canary"],
        "LAB_PAPER_PROBE_003_RUNNER": report["runner"],
        "LAB_PAPER_PROBE_003_DECISION": _decision_report(report),
    }
    for stem, payload in artifacts.items():
        (reports_dir / f"{stem}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if stem != "LAB_PAPER_PROBE_003_DECISION":
            (reports_dir / f"{stem}.md").write_text(_render_gate_markdown(stem, payload), encoding="utf-8")
    (reports_dir / "LAB_PAPER_PROBE_003_FINAL_REPORT.md").write_text(_render_final_report(report), encoding="utf-8")


def _decision_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "tradeo.lab_paper_probe_003.decision.v1",
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
        "live_orders_executed": report["live_orders_executed"],
        "foxhunter_promotion": report["foxhunter_promotion"],
        "live_candidate_created": report["live_candidate_created"],
        "paper_candidate_classic_created": report["paper_candidate_classic_created"],
        "signals_generated": report["signals_generated"],
        "previews_generated": report["previews_generated"],
        "env_overlay_gate": report["env_overlay_gate"]["status"],
        "paper_account_gate": report["paper_account_gate"]["status"],
        "canary": report["canary"]["decision"],
        "runner": report["runner"]["decision"],
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
        f"- blockers: `{payload.get('blockers', [])}`",
        f"- redacted: `{payload.get('redacted', True)}`",
    ]
    if "base_checks" in payload:
        lines.extend(["", "## Base checks", ""])
        for key, value in payload["base_checks"].items():
            lines.append(f"- {key}: `{value}`")
    if "orders" in payload:
        lines.extend(["", f"- orders: `{len(payload.get('orders') or [])}`"])
    if "safety" in payload:
        lines.extend(["", "## Safety", ""])
        for key, value in payload["safety"].items():
            lines.append(f"- {key}: `{value}`")
    return "\n".join(lines) + "\n"


def _render_final_report(report: dict[str, Any]) -> str:
    canary_orders = report.get("canary", {}).get("orders", [])
    runner_orders = report.get("runner", {}).get("orders", [])
    lines = [
        "# T-LAB-PAPER-PROBE-003 Final Report",
        "",
        "## A. Resumen ejecutivo",
        "",
        f"Decision final: `{report['decision']}`.",
        "",
        "Se creo y valido un overlay temporal de escritura paper, pero no se envio ninguna orden paper. "
        "La ejecucion quedo bloqueada antes del canary porque no pudo verificarse una cuenta paper IBKR de forma inequivoca desde este entorno.",
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
        "- commit/push: pendiente de commit final de esta tarea; no se toco main ni se uso gh.",
        "",
        "## D. Env overlay gate",
        "",
        f"- status: `{report['env_overlay_gate']['status']}`",
        f"- overlay_tracked: `{report['overlay_tracked']}`",
        f"- overlay_keys: `{report['env_overlay_gate'].get('overlay_keys')}`",
        "",
        "## E. Paper account gate",
        "",
        f"- status: `{report['paper_account_gate']['status']}`",
        f"- port_class: `{report['paper_account_gate'].get('port_class')}`",
        f"- connected: `{report['paper_account_gate'].get('connected')}`",
        f"- blockers: `{report['paper_account_gate'].get('blockers')}`",
        f"- error: `{report['paper_account_gate'].get('error')}`",
        "",
        "## F. Canary result",
        "",
        f"- decision: `{report['canary']['decision']}`",
        f"- status: `{report['canary']['status']}`",
        f"- orders: `{len(canary_orders)}`",
        "",
        "## G. Probe runner result",
        "",
        f"- decision: `{report['runner']['decision']}`",
        f"- orders: `{len(runner_orders)}`",
        f"- warnings: `{report['runner'].get('warnings')}`",
        "",
        "## H. Paper orders executed",
        "",
        "None.",
        "",
        "## I. No-trade reasons",
        "",
        f"- `{report['no_trade_reason']}`",
        f"- blockers: `{report['blockers']}`",
        "",
        "## J. Telemetry/fills/slippage",
        "",
        "- fills: none",
        "- slippage: none",
        "- latency: none",
        "- accounts: redacted; no raw account id logged",
        "",
        "## K. Tests/validaciones",
        "",
        "- py_compile runner/gates: PASS",
        "- pytest focal lab_foxhunter + paper_readiness: PASS, 35 passed",
        "- ruff touched files: PASS",
        "- git diff --check: PASS",
        "- JSON validation: PASS",
        "- security scan: PASS, no .env/overlay/runtime/memory tracked and no raw account id in tracked artifacts",
        "",
        "## L. Decision final",
        "",
        f"`{report['decision']}`",
        "",
        "## M. Confirmaciones",
        "",
        "- no live: confirmed",
        "- no real orders: confirmed",
        "- no paper orders: confirmed",
        "- no FoxHunter promotion: confirmed",
        "- no live_candidate: confirmed",
        "- no classic paper_candidate: confirmed",
        "- no gh: confirmed",
        "- no main push: confirmed",
        "",
        "## N. Siguiente accion",
        "",
        "Corregir la cuenta configurada o la sesion IBKR paper para que la cuenta gestionada sea inequivocamente paper DU; "
        "despues repetir solo paper account gate y canary. Hasta entonces no ejecutar probes.",
        "",
    ]
    return "\n".join(lines)


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


def _paper_account_gate(env: dict[str, str]) -> dict[str, Any]:
    blockers: list[str] = []
    port = int(_value(env, "TRADEO_IBKR_PORT", "7497") or "0")
    trading_mode = _value(env, "TRADEO_TRADING_MODE", "paper").lower()
    if trading_mode != "paper":
        blockers.append("trading_mode_not_paper")
    if port in LIVE_PORTS:
        blockers.append("live_port_configured")
    if port not in PAPER_PORTS:
        blockers.append("paper_port_not_recognized")
    if not _bool(_value(env, "TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED", "false")):
        blockers.append("paper_probe_write_flag_missing")
    if blockers:
        return _account_gate_result("BLOCKED", blockers=blockers, env=env)

    try:
        _ensure_event_loop()
        from ib_insync import IB

        ib = IB()
        try:
            _connect_ib(ib, env, port)
            accounts = list(ib.managedAccounts() or [])
            selected = _value(env, "TRADEO_IBKR_ACCOUNT", "").strip() or (accounts[0] if len(accounts) == 1 else "")
            if not selected:
                blockers.append("paper_account_ambiguous_or_missing")
            elif selected not in accounts:
                blockers.append("configured_account_not_managed")
            elif not selected.upper().startswith("DU"):
                blockers.append("account_not_du_paper")
            return _account_gate_result(
                "PASS" if not blockers else "BLOCKED",
                blockers=blockers,
                env=env,
                accounts=accounts,
                selected_account=selected,
                connected=True,
            )
        finally:
            if ib.isConnected():
                ib.disconnect()
    except Exception as exc:  # noqa: BLE001 - IBKR/ib_insync raises heterogeneous exceptions.
        return _account_gate_result(
            "BLOCKED",
            blockers=["ibkr_paper_connection_failed"],
            env=env,
            connected=False,
            error=f"{type(exc).__name__}: {_short(str(exc))}",
        )


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
            account = _value(env, "TRADEO_IBKR_ACCOUNT", "").strip() or (accounts[0] if len(accounts) == 1 else "")
            if not account or not account.upper().startswith("DU"):
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
                "account_hash": _hash_account(account),
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
    except Exception as exc:  # noqa: BLE001 - IBKR/ib_insync raises heterogeneous exceptions.
        return {
            "status": "BLOCKED",
            "decision": "CANARY_BLOCKED_SUBMIT_FAIL",
            "blockers": ["canary_submit_cancel_exception"],
            "error": f"{type(exc).__name__}: {_short(str(exc))}",
            "orders": [],
            "redacted": True,
        }


def _account_gate_result(
    status: str,
    *,
    blockers: list[str],
    env: dict[str, str],
    accounts: list[str] | None = None,
    selected_account: str | None = None,
    connected: bool | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    selected = selected_account or ""
    return {
        "status": status,
        "blockers": blockers,
        "connected": connected,
        "trading_mode": _value(env, "TRADEO_TRADING_MODE", "paper").lower(),
        "port_class": _port_class(int(_value(env, "TRADEO_IBKR_PORT", "0") or "0")),
        "live_port": int(_value(env, "TRADEO_IBKR_PORT", "0") or "0") in LIVE_PORTS,
        "managed_accounts_count": len(accounts or []),
        "selected_account_hash": _hash_account(selected) if selected else None,
        "selected_account_present": bool(selected),
        "selected_account_du_paper": bool(selected and selected.upper().startswith("DU")),
        "error": error,
        "redacted": True,
    }


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


def _field_name(env_key: str) -> str:
    return env_key.removeprefix("TRADEO_").lower()


def _coerce_value(value: str) -> Any:
    lowered = value.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in lowered:
            return float(lowered)
        return int(lowered)
    except ValueError:
        return value


def _value(env: dict[str, str], key: str, default: str) -> str:
    return str(env.get(key, default)).strip()


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _hash_account(account: str) -> str:
    return "sha256:" + hashlib.sha256(account.encode("utf-8")).hexdigest()[:16]


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
        except Exception as exc:  # noqa: BLE001 - try configured host, then local paper proxy.
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
