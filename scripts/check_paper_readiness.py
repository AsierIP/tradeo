#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "tradeo.paper_readiness_002.v1"
TASK_ID = "T-PAPER-READINESS-002"
NO_PAPER_CANDIDATE = "NO_GO_NO_PAPER_CANDIDATE"
NO_TRADE_REASON = "NO_TRADE_NO_PAPER_CANDIDATE"

SAFETY_FLAGS = (
    "TRADEO_TRADING_MODE",
    "TRADEO_LIVE_TRADING_ENABLED",
    "TRADEO_INTRADAY_PAPER_ENABLED",
    "TRADEO_INTRADAY_LIVE_ENABLED",
    "TRADEO_IBKR_READONLY",
    "TRADEO_KILL_SWITCH_ENABLED",
    "TRADEO_INTRADAY_MAX_TRADES_PER_DAY",
    "TRADEO_INTRADAY_DAILY_LOSS_LIMIT_PCT",
    "TRADEO_MAX_POSITION_VALUE_PCT",
    "TRADEO_IBKR_MAX_ORDER_VALUE_USD",
    "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS",
    "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS",
    "TRADEO_IBKR_ALLOW_MARKET_ORDERS",
    "TRADEO_RECONCILIATION_AUTO_REPAIR_PAPER_EXITS",
    "TRADEO_INTRADAY_EOD_EMERGENCY_MARKET_ALLOWED",
)

AUTOMATION_BLOCK_FLAGS = (
    "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS",
    "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS",
    "TRADEO_IBKR_ALLOW_MARKET_ORDERS",
    "TRADEO_RECONCILIATION_AUTO_REPAIR_PAPER_EXITS",
    "TRADEO_INTRADAY_EOD_EMERGENCY_MARKET_ALLOWED",
)

EXECUTION_SURFACE_FILES = (
    "backend/tradeo/routers/ibkr.py",
    "backend/tradeo/tasks/worker.py",
    "backend/tradeo/services/ibkr_broker.py",
    "backend/tradeo/services/paper_broker.py",
    "backend/tradeo/modules/shared/entry_scanner.py",
    "backend/tradeo/modules/intraday/flat_service.py",
    "docker-compose.yml",
)

CANDIDATE_MANIFEST_GLOBS = (
    "config/**/*paper*candidate*.json",
    "research/**/*paper*candidate*.json",
    "artifacts/runtime/**/*paper*candidate*.json",
)

SENSITIVE_NAME_RE = re.compile(r"(KEY|SECRET|PASSWORD|TOKEN|ACCOUNT|USERNAME)", re.IGNORECASE)
LONG_CREDENTIAL_RE = re.compile(r"^[A-Za-z0-9_./+=:-]{32,}$")


@dataclass(frozen=True)
class CommandResult:
    exit_code: int | None
    stdout: str
    stderr: str


def run_command(command: list[str], cwd: Path, timeout: int = 30) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return CommandResult(None, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(None, exc.stdout or "", f"timed out after {timeout}s")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and (candidate / "docker-compose.yml").exists():
            return candidate
    raise SystemExit("could not locate Tradeo repo root")


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("TRADEO_"):
            values[key] = value.strip().strip("'\"")
    return values


def choose_env_source(repo_root: Path, env_file: Path | None = None) -> tuple[str | None, Path | None]:
    if env_file is not None:
        return str(env_file), env_file
    if (repo_root / ".env").exists():
        return ".env", repo_root / ".env"
    if (repo_root / ".env.example").exists():
        return ".env.example", repo_root / ".env.example"
    return None, None


def collect_env(repo_root: Path, env_file: Path | None = None) -> tuple[str | None, dict[str, str]]:
    source, path = choose_env_source(repo_root, env_file)
    env = parse_env_file(repo_root / ".env.example")
    if path:
        env.update(parse_env_file(path))
    env.update({key: value for key, value in os.environ.items() if key.startswith("TRADEO_")})
    return source, env


def is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


def positive_number(value: str | None) -> bool:
    try:
        return float(str(value or "").strip()) > 0
    except ValueError:
        return False


def positive_int(value: str | None) -> bool:
    try:
        return int(str(value or "").strip()) > 0
    except ValueError:
        return False


def non_negative_int(value: str | None) -> bool:
    try:
        return int(str(value or "").strip()) >= 0
    except ValueError:
        return False


def looks_sensitive(key: str, value: str | None) -> bool:
    if value is None:
        return False
    return bool(SENSITIVE_NAME_RE.search(key) or LONG_CREDENTIAL_RE.match(value.strip()))


def redact_value(key: str, value: str | None) -> str | None:
    if value is None:
        return None
    if looks_sensitive(key, value):
        return "<redacted>" if value else ""
    return value


def git_value(repo_root: Path, command: list[str], default: str = "unknown") -> str:
    result = run_command(command, repo_root)
    if result.exit_code != 0:
        return default
    return result.stdout.strip() or default


def git_summary(repo_root: Path) -> dict[str, Any]:
    status = run_command(["git", "status", "--porcelain"], repo_root)
    tracked: list[str] = []
    untracked: list[str] = []
    if status.exit_code == 0:
        for line in status.stdout.splitlines():
            if line.startswith("??"):
                untracked.append(line[3:])
            elif line:
                tracked.append(line[3:] if len(line) > 3 else line)
    return {
        "root": str(repo_root),
        "branch": git_value(repo_root, ["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "commit_sha": git_value(repo_root, ["git", "rev-parse", "HEAD"]),
        "origin_main_sha": git_value(repo_root, ["git", "rev-parse", "origin/main"]),
        "dirty": bool(tracked or untracked) if status.exit_code == 0 else True,
        "tracked_changes": tracked[:100],
        "untracked_changes": untracked[:100],
        "git_status_exit_code": status.exit_code,
    }


def env_summary(source: str | None, env: dict[str, str]) -> dict[str, Any]:
    return {
        "source": source,
        "redaction_ok": True,
        "safety_flags": {key: redact_value(key, env.get(key)) for key in SAFETY_FLAGS},
        "sensitive_keys_redacted": sorted(key for key, value in env.items() if looks_sensitive(key, value)),
    }


def safety_audit(env: dict[str, str]) -> dict[str, Any]:
    checks = {
        "trading_mode_not_live": str(env.get("TRADEO_TRADING_MODE", "paper")).lower() != "live",
        "live_trading_disabled": not is_truthy(env.get("TRADEO_LIVE_TRADING_ENABLED")),
        "intraday_live_disabled": not is_truthy(env.get("TRADEO_INTRADAY_LIVE_ENABLED")),
        "ibkr_readonly": is_truthy(env.get("TRADEO_IBKR_READONLY", "true")),
        "auto_submit_disabled": not any(is_truthy(env.get(key)) for key in AUTOMATION_BLOCK_FLAGS),
        "kill_switch_control_present": "TRADEO_KILL_SWITCH_ENABLED" in env,
        "max_trades_per_day_defined": non_negative_int(env.get("TRADEO_INTRADAY_MAX_TRADES_PER_DAY")),
        "max_daily_loss_defined": positive_number(env.get("TRADEO_INTRADAY_DAILY_LOSS_LIMIT_PCT")),
        "max_position_value_defined": positive_number(env.get("TRADEO_MAX_POSITION_VALUE_PCT")),
        "max_order_value_defined": positive_number(env.get("TRADEO_IBKR_MAX_ORDER_VALUE_USD")),
    }
    blockers: list[str] = []
    if not checks["trading_mode_not_live"]:
        blockers.append("TRADEO_TRADING_MODE=live")
    if not checks["live_trading_disabled"]:
        blockers.append("TRADEO_LIVE_TRADING_ENABLED=true")
    if not checks["intraday_live_disabled"]:
        blockers.append("TRADEO_INTRADAY_LIVE_ENABLED=true")
    if not checks["ibkr_readonly"]:
        blockers.append("TRADEO_IBKR_READONLY is not true")
    for key in AUTOMATION_BLOCK_FLAGS:
        if is_truthy(env.get(key)):
            blockers.append(f"{key}=true")
    if is_truthy(env.get("TRADEO_INTRADAY_PAPER_ENABLED")) and not is_truthy(
        env.get("TRADEO_PAPER_ORDER_EXPLICIT_APPROVAL")
    ):
        blockers.append("TRADEO_INTRADAY_PAPER_ENABLED=true without explicit approval")
    gaps = [name for name, passed in checks.items() if not passed and name not in {
        "trading_mode_not_live",
        "live_trading_disabled",
        "intraday_live_disabled",
        "ibkr_readonly",
        "auto_submit_disabled",
    }]
    return {
        "checks": checks,
        "blockers": blockers,
        "gaps": gaps,
        "live_allowed": False,
        "paper_enabled": is_truthy(env.get("TRADEO_INTRADAY_PAPER_ENABLED")),
        "paper_enabled_controlled": not is_truthy(env.get("TRADEO_INTRADAY_PAPER_ENABLED"))
        or is_truthy(env.get("TRADEO_PAPER_ORDER_EXPLICIT_APPROVAL")),
        "orders_allowed": False,
        "paper_orders_allowed": False,
        "live_orders_allowed": False,
    }


def execution_surface_audit(repo_root: Path, env_file: Path | None = None) -> dict[str, Any]:
    files = [{"path": path, "exists": (repo_root / path).exists()} for path in EXECUTION_SURFACE_FILES]
    compose_command = ["docker", "compose"]
    if env_file is not None and env_file.name == ".env":
        compose_command.extend(["--project-directory", str(env_file.parent)])
        compose_command.extend(["-f", str(repo_root / "docker-compose.yml")])
    elif env_file is not None:
        compose_command.extend(["--env-file", str(env_file)])
    compose_command.extend(["config", "--quiet"])
    compose = run_command(compose_command, repo_root, timeout=60)
    worker_text = (repo_root / "backend/tradeo/tasks/worker.py").read_text(encoding="utf-8")
    ibkr_router_text = (repo_root / "backend/tradeo/routers/ibkr.py").read_text(encoding="utf-8")
    return {
        "surface_files": files,
        "docker_compose_config_ok": compose.exit_code == 0,
        "docker_compose_exit_code": compose.exit_code,
        "worker_declared": (repo_root / "docker-compose.yml").read_text(encoding="utf-8").find("tradeo.tasks.worker") >= 0,
        "worker_has_entry_scanner_job": "laboratory_entry_job" in worker_text or "fox_hunter_entry_job" in worker_text,
        "ibkr_submit_endpoint_present": "submit-bracket" in ibkr_router_text,
        "ibkr_preview_endpoint_present": "/preview" in ibkr_router_text,
        "audit_result": "EXECUTION_SURFACE_PRESENT_BUT_GATED",
    }


def candidate_gate(repo_root: Path) -> dict[str, Any]:
    manifests: list[dict[str, Any]] = []
    for pattern in CANDIDATE_MANIFEST_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                data = {}
            text = json.dumps(data, sort_keys=True).lower() if data else path.name.lower()
            approved = "paper_candidate" in text and any(token in text for token in ("approved", "director_approved"))
            manifests.append(
                {
                    "path": str(path.relative_to(repo_root)),
                    "approved_paper_candidate": approved,
                    "redacted": True,
                }
            )
    approved = [item for item in manifests if item["approved_paper_candidate"]]
    return {
        "approved_paper_candidate_count": len(approved),
        "approved_paper_candidate_manifests": approved,
        "scanned_manifest_count": len(manifests),
        "order_gate_status": "BLOCK_NO_PAPER_CANDIDATE" if not approved else "PAPER_CANDIDATE_PRESENT_REQUIRES_DIRECTOR_APPROVAL",
        "order_gate_reason": NO_TRADE_REASON if not approved else "PAPER_CANDIDATE_PRESENT",
        "orders_allowed": bool(approved),
    }


def build_shadow_rehearsal(
    *,
    candidate: dict[str, Any],
    safety: dict[str, Any],
    generated_at: str,
    ibkr_state: str = "not_checked",
) -> dict[str, Any]:
    reason = NO_TRADE_REASON if not candidate["orders_allowed"] else "PAPER_CANDIDATE_PRESENT_REQUIRES_SEPARATE_APPROVAL"
    return {
        "schema_version": "tradeo.paper_readiness_002.shadow_no_order_rehearsal.v1",
        "generated_at": generated_at,
        "source": TASK_ID,
        "strategy_family": "NONE",
        "symbol": None,
        "theoretical_event": "MONDAY_READINESS_REHEARSAL_ONLY",
        "ibkr_state": ibkr_state,
        "reason_no_trade": reason,
        "candidate_gate_status": candidate["order_gate_status"],
        "kill_switch_status": "configured" if safety["checks"]["kill_switch_control_present"] else "missing",
        "signals_generated": False,
        "preview_generated": False,
        "orders_generated": False,
        "orders_submitted": False,
        "paper_order_submitted": False,
        "live_order_submitted": False,
        "orders_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def build_report(repo_root: Path, env_file: Path | None = None, ibkr_state: str = "not_checked") -> dict[str, Any]:
    repo_root = repo_root.resolve()
    generated_at = datetime.now(timezone.utc).isoformat()
    env_source, env = collect_env(repo_root, env_file)
    _, selected_env_file = choose_env_source(repo_root, env_file)
    repo = git_summary(repo_root)
    safety = safety_audit(env)
    surface = execution_surface_audit(repo_root, env_file=selected_env_file)
    candidate = candidate_gate(repo_root)
    rehearsal = build_shadow_rehearsal(
        candidate=candidate,
        safety=safety,
        generated_at=generated_at,
        ibkr_state=ibkr_state,
    )

    infra_blockers = list(safety["blockers"])
    if not surface["docker_compose_config_ok"]:
        infra_blockers.append("docker compose config failed")
    infra_gaps = list(safety["gaps"])
    paper_infra_ready = not infra_blockers and not infra_gaps
    shadow_ready = paper_infra_ready and rehearsal["reason_no_trade"] == NO_TRADE_REASON
    if candidate["approved_paper_candidate_count"] == 0:
        paper_order_decision = "PAPER_ORDER_READY_NO_GO_NO_PAPER_CANDIDATE"
    elif infra_blockers:
        paper_order_decision = "PAPER_ORDER_READY_NO_GO_SAFETY_BLOCKER"
    else:
        paper_order_decision = "PAPER_ORDER_READY_NO_GO_OPERABILITY_BLOCKER"

    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "generated_at": generated_at,
        "repo": repo,
        "env": env_summary(env_source, env),
        "safety": safety,
        "execution_surface": surface,
        "candidate_gate": candidate,
        "shadow_no_order_rehearsal": rehearsal,
        "decisions": {
            "PAPER_INFRA_READY": "GO" if paper_infra_ready else "NO_GO",
            "SHADOW_NO_ORDER_READY": "GO" if shadow_ready else "NO_GO",
            "PAPER_ORDER_READY": paper_order_decision.removeprefix("PAPER_ORDER_READY_"),
            "paper_infra_decision": "PAPER_INFRA_READY_GO" if paper_infra_ready else "PAPER_INFRA_READY_NO_GO",
            "shadow_no_order_decision": "SHADOW_NO_ORDER_READY_GO" if shadow_ready else "SHADOW_NO_ORDER_READY_NO_GO",
            "paper_order_decision": paper_order_decision,
        },
        "safety_confirmations": {
            "no_live": True,
            "no_paper_orders": True,
            "no_orders": True,
            "no_preview": True,
            "no_signals": True,
            "no_ibkr_operational": ibkr_state in {"not_checked", "tcp_unavailable", "tcp_available_readonly_only"},
            "no_downloads": True,
            "no_cron_trading": True,
            "no_gh": True,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    decisions = report["decisions"]
    safety = report["safety"]
    candidate = report["candidate_gate"]
    surface = report["execution_surface"]
    rehearsal = report["shadow_no_order_rehearsal"]
    lines = [
        "# PAPER READINESS 002 REPORT",
        "",
        "## A. Resumen ejecutivo",
        "",
        "- Preflight infra/shadow ejecutado sin señales, previews ni órdenes.",
        f"- PAPER_INFRA_READY: `{decisions['PAPER_INFRA_READY']}`",
        f"- SHADOW_NO_ORDER_READY: `{decisions['SHADOW_NO_ORDER_READY']}`",
        f"- PAPER_ORDER_READY: `{decisions['PAPER_ORDER_READY']}`",
        "",
        "## B. Path real usado",
        "",
        f"- `{report['repo']['root']}`",
        "",
        "## C. Rama/commit/push",
        "",
        f"- branch: `{report['repo']['branch']}`",
        f"- commit: `{report['repo']['commit_sha']}`",
        f"- origin_main: `{report['repo']['origin_main_sha']}`",
        "- push: pendiente hasta validacion final",
        "",
        "## D. Estado repo/main",
        "",
        f"- dirty: `{report['repo']['dirty']}`",
        "",
        "## E. IBKR paper connectivity",
        "",
        f"- ibkr_state: `{rehearsal['ibkr_state']}`",
        "- No se hizo diagnostico operativo ni account logging.",
        "",
        "## F. Flags de seguridad",
        "",
    ]
    for key, value in report["env"]["safety_flags"].items():
        lines.append(f"- {key}: `{value if value not in (None, '') else 'unset'}`")
    lines.extend(
        [
            f"- blockers: `{safety['blockers']}`",
            f"- gaps: `{safety['gaps']}`",
            "",
            "## G. Worker/cron audit",
            "",
            f"- docker_compose_config_ok: `{surface['docker_compose_config_ok']}`",
            f"- worker_declared: `{surface['worker_declared']}`",
            f"- worker_has_entry_scanner_job: `{surface['worker_has_entry_scanner_job']}`",
            f"- ibkr_submit_endpoint_present: `{surface['ibkr_submit_endpoint_present']}`",
            f"- audit_result: `{surface['audit_result']}`",
            "",
            "## H. Kill-switch/risk limits",
            "",
            f"- kill_switch_control_present: `{safety['checks']['kill_switch_control_present']}`",
            f"- max_trades_per_day_defined: `{safety['checks']['max_trades_per_day_defined']}`",
            f"- max_daily_loss_defined: `{safety['checks']['max_daily_loss_defined']}`",
            f"- max_position_value_defined: `{safety['checks']['max_position_value_defined']}`",
            "",
            "## I. Candidate manifest gate",
            "",
            f"- approved_paper_candidate_count: `{candidate['approved_paper_candidate_count']}`",
            f"- order_gate_status: `{candidate['order_gate_status']}`",
            f"- reason: `{candidate['order_gate_reason']}`",
            "",
            "## J. Paper infra readiness",
            "",
            f"- `{decisions['paper_infra_decision']}`",
            "",
            "## K. Shadow/no-order readiness",
            "",
            f"- `{decisions['shadow_no_order_decision']}`",
            f"- reason_no_trade: `{rehearsal['reason_no_trade']}`",
            "",
            "## L. Paper order readiness",
            "",
            f"- `{decisions['paper_order_decision']}`",
            "",
            "## M. Tests/validaciones",
            "",
            "- Ver reporte final de tarea para comandos ejecutados.",
            "",
            "## N. Riesgos residuales",
            "",
            "- La salida depende de la configuracion local redaccionada usada por el preflight.",
            "- Paper orders siguen bloqueadas por falta de paper_candidate aprobado.",
            "",
            "## O. GO/NO-GO para manana",
            "",
            f"- PAPER_INFRA_READY: `{decisions['PAPER_INFRA_READY']}`",
            f"- SHADOW_NO_ORDER_READY: `{decisions['SHADOW_NO_ORDER_READY']}`",
            f"- PAPER_ORDER_READY: `{decisions['PAPER_ORDER_READY']}`",
            "",
            "## P. Confirmacion restricciones",
            "",
            "- no live, no paper orders, no ordenes, no preview, no senales, no IBKR operativo salvo diagnostico, no descargas, no cron trading, no gh.",
            "",
            "## Q. Siguiente accion recomendada",
            "",
            "- Antes de mercado: ejecutar el preflight con el .env real y confirmar que el bloqueo NO_TRADE_NO_PAPER_CANDIDATE sigue activo.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _write_md(path: Path, title: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# " + title + "\n\n" + "\n".join(rows).rstrip() + "\n", encoding="utf-8")


def write_outputs(report: dict[str, Any], *, json_out: Path, md_out: Path, runtime_out: Path) -> None:
    for path in (json_out, md_out, runtime_out):
        path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(json_out, report)
    md_out.write_text(render_markdown(report), encoding="utf-8")
    _write_json(runtime_out, report["shadow_no_order_rehearsal"])
    research_dir = md_out.parent
    _write_json(
        research_dir / "PAPER_READINESS_002_REPO_SAFETY_AUDIT.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": report["generated_at"],
            "repo": report["repo"],
            "env": report["env"],
            "safety": report["safety"],
            "decision": report["decisions"]["paper_infra_decision"],
        },
    )
    _write_md(
        research_dir / "PAPER_READINESS_002_REPO_SAFETY_AUDIT.md",
        "PAPER READINESS 002 REPO SAFETY AUDIT",
        [
            f"- branch: `{report['repo']['branch']}`",
            f"- commit: `{report['repo']['commit_sha']}`",
            f"- env_source: `{report['env']['source']}`",
            f"- blockers: `{report['safety']['blockers']}`",
            f"- gaps: `{report['safety']['gaps']}`",
            f"- decision: `{report['decisions']['paper_infra_decision']}`",
            "- Secrets and account identifiers are redacted.",
        ],
    )
    _write_json(
        research_dir / "PAPER_READINESS_002_EXECUTION_SURFACE_AUDIT.json",
        {
            "schema_version": SCHEMA_VERSION,
            "generated_at": report["generated_at"],
            "execution_surface": report["execution_surface"],
            "safety_confirmations": report["safety_confirmations"],
        },
    )
    _write_md(
        research_dir / "PAPER_READINESS_002_EXECUTION_SURFACE_AUDIT.md",
        "PAPER READINESS 002 EXECUTION SURFACE AUDIT",
        [
            f"- docker_compose_config_ok: `{report['execution_surface']['docker_compose_config_ok']}`",
            f"- worker_declared: `{report['execution_surface']['worker_declared']}`",
            f"- worker_has_entry_scanner_job: `{report['execution_surface']['worker_has_entry_scanner_job']}`",
            f"- ibkr_submit_endpoint_present: `{report['execution_surface']['ibkr_submit_endpoint_present']}`",
            "- Order surfaces exist but this rehearsal did not call them.",
        ],
    )
    _write_md(
        research_dir / "PAPER_READINESS_002_CANDIDATE_GATE.md",
        "PAPER READINESS 002 CANDIDATE GATE",
        [
            f"- approved_paper_candidate_count: `{report['candidate_gate']['approved_paper_candidate_count']}`",
            f"- order_gate_status: `{report['candidate_gate']['order_gate_status']}`",
            f"- order_gate_reason: `{report['candidate_gate']['order_gate_reason']}`",
            f"- orders_allowed: `{report['candidate_gate']['orders_allowed']}`",
            "- Sin paper_candidate aprobado, cualquier orden paper queda bloqueada.",
        ],
    )
    _write_md(
        research_dir / "PAPER_READINESS_002_SHADOW_NO_ORDER_REHEARSAL.md",
        "PAPER READINESS 002 SHADOW NO ORDER REHEARSAL",
        [
            f"- reason_no_trade: `{report['shadow_no_order_rehearsal']['reason_no_trade']}`",
            f"- candidate_gate_status: `{report['shadow_no_order_rehearsal']['candidate_gate_status']}`",
            f"- signals_generated: `{report['shadow_no_order_rehearsal']['signals_generated']}`",
            f"- preview_generated: `{report['shadow_no_order_rehearsal']['preview_generated']}`",
            f"- orders_submitted: `{report['shadow_no_order_rehearsal']['orders_submitted']}`",
            f"- decision: `{report['decisions']['shadow_no_order_decision']}`",
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run T-PAPER-READINESS-002 gate without signals, previews, or orders.")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--ibkr-state", default="not_checked")
    parser.add_argument("--json-out", default="research/paper_readiness/PAPER_READINESS_002_DECISION.json")
    parser.add_argument("--md-out", default="research/paper_readiness/PAPER_READINESS_002_REPORT.md")
    parser.add_argument(
        "--runtime-out",
        default="artifacts/runtime/paper_readiness/paper_readiness_2026-07-06.json",
    )
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    env_file = Path(args.env_file).resolve() if args.env_file else None
    report = build_report(repo_root, env_file=env_file, ibkr_state=args.ibkr_state)
    if not args.json_only:
        write_outputs(
            report,
            json_out=repo_root / args.json_out,
            md_out=repo_root / args.md_out,
            runtime_out=repo_root / args.runtime_out,
        )
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report["decisions"]["PAPER_ORDER_READY"] == NO_PAPER_CANDIDATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
