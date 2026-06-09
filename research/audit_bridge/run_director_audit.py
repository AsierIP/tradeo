#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "research" / "audit_bridge"
REQUESTS = BRIDGE / "requests"


@dataclass
class CommandRun:
    name: str
    command: list[str]
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    blocking: bool = True


def main() -> int:
    args = parse_args()
    audit_id = args.audit_id or build_audit_id(args.cadence)
    package = REQUESTS / audit_id
    package.mkdir(parents=True, exist_ok=True)
    api_url = args.api_url or os.environ.get("TRADEO_API_URL") or default_api_url()
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    runs: list[CommandRun] = []
    gate_result: dict[str, Any] = {}
    agent_review: dict[str, Any] = {}
    runtime_status: dict[str, Any] = {"available": False, "reason": "not_collected"}
    runner_error: dict[str, str] | None = None
    exit_code = 1

    try:
        runtime_run, runtime_status = collect_compose_status()
        runs.append(runtime_run)

        if not args.skip_export:
            runs.append(run_exporter(audit_id, api_url, args.pattern_limit, args.match_limit))

        gate_json = package / "director_gate_result.json"
        gate_md = package / "director_gate_result.md"
        runs.append(
            run_subprocess(
                "director_gate",
                [
                    sys.executable,
                    str(BRIDGE / "director_gate.py"),
                    str(package),
                    "--json-output",
                    str(gate_json),
                    "--markdown-output",
                    str(gate_md),
                    "--allow-blocked-exit-zero",
                ],
            )
        )
        runs.append(run_subprocess("validate", [sys.executable, str(BRIDGE / "validate_audit_package.py"), str(package)]))

        gate_result = read_json(gate_json)
        agent_review = deterministic_review(audit_id, args.cadence, gate_result, runs)

        export_failed = any(run.name == "export" and run.exit_code != 0 for run in runs)
        validation_failed = any(run.name == "validate" and run.exit_code != 0 for run in runs)
        blocked = gate_result.get("status") == "blocked" if isinstance(gate_result, dict) else False
        if export_failed or validation_failed:
            exit_code = 1
        elif blocked and args.fail_on_blocked:
            exit_code = 2
        else:
            exit_code = 0
    except Exception as exc:  # noqa: BLE001
        runner_error = {"type": type(exc).__name__, "message": str(exc)}
        runs.append(CommandRun("runner_error", [], 1, stderr=f"{type(exc).__name__}: {exc}"))
        gate_result = {"status": "runner_error", "blockers": [f"runner_error: {type(exc).__name__}: {exc}"]}
        agent_review = deterministic_review(audit_id, args.cadence, gate_result, runs)
        exit_code = 1

    result = {
        "audit_id": audit_id,
        "cadence": args.cadence,
        "created_at": created_at,
        "package": display_path(package),
        "api_url": api_url,
        "director_gate_status": gate_result.get("status", "unknown") if isinstance(gate_result, dict) else "unknown",
        "runtime_status": runtime_status,
        "commands": [asdict(run) for run in runs],
        "agent_review": agent_review,
        "artifact_paths": {
            "run_json": display_path(package / "director_audit_run.json"),
            "run_markdown": display_path(package / "director_audit_run.md"),
            "agent_review_json": display_path(package / "internal_auditor_agent_review.json"),
            "agent_review_markdown": display_path(package / "internal_auditor_agent_review.md"),
        },
    }
    if runner_error is not None:
        result["runner_error"] = runner_error

    try:
        write_json(package / "internal_auditor_agent_review.json", agent_review)
        write_agent_md(package / "internal_auditor_agent_review.md", agent_review)
        write_json(package / "director_audit_run.json", result)
        write_md(package / "director_audit_run.md", result)
    except Exception as exc:  # noqa: BLE001
        print(f"failed to write audit artifacts in {package}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    return exit_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the automated Tradeo Director audit loop.")
    parser.add_argument("--audit-id", default=None)
    parser.add_argument("--cadence", choices=["daily", "weekly", "manual"], default="daily")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--pattern-limit", type=int, default=500)
    parser.add_argument("--match-limit", type=int, default=500)
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true")
    return parser.parse_args()


def build_audit_id(cadence: str) -> str:
    now = datetime.now(timezone.utc)
    return f"TRADEO-AUDIT-{now:%Y%m%d-%H%M%S}_{cadence}_internal"


def default_api_url() -> str:
    if Path("/.dockerenv").exists() or Path("/app").exists():
        return "http://backend:8000/api"
    return "http://localhost:8000/api"


def collect_compose_status() -> tuple[CommandRun, dict[str, Any]]:
    command = compose_ps_command(json_format=True)
    run = run_subprocess("docker_compose_ps", command, blocking=False)
    if run.exit_code == 0:
        services = parse_compose_ps_json(run.stdout)
        if not services and run.stdout.strip():
            fallback = run_subprocess("docker_compose_ps", compose_ps_command(json_format=False), blocking=False)
            return fallback, {
                "available": fallback.exit_code == 0,
                "source": "docker compose ps",
                "service_count": None,
                "services": [],
                "reason": "json_output_unparseable",
                "json_stdout": run.stdout,
                "json_stderr": run.stderr,
            }
        return run, {
            "available": True,
            "source": "docker compose ps --format json",
            "service_count": len(services),
            "services": services,
        }

    fallback = run_subprocess("docker_compose_ps", compose_ps_command(json_format=False), blocking=False)
    return fallback, {
        "available": fallback.exit_code == 0,
        "source": "docker compose ps",
        "service_count": None,
        "services": [],
        "reason": "json_format_failed" if fallback.exit_code == 0 else "docker_compose_ps_unavailable",
        "json_stderr": run.stderr,
    }


def compose_ps_command(*, json_format: bool) -> list[str]:
    command = ["docker", "compose"]
    files = [value for value in os.environ.get("TRADEO_AUDIT_COMPOSE_FILES", "").split(os.pathsep) if value]
    for file_name in files:
        command.extend(["-f", file_name])
    command.append("ps")
    if json_format:
        command.extend(["--format", "json"])
    return command


def parse_compose_ps_json(stdout: str) -> list[dict[str, Any]]:
    text = stdout.strip()
    if not text:
        return []
    try:
        raw = json.loads(text)
        rows = raw if isinstance(raw, list) else [raw]
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                return []

    services: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("Name") or row.get("name") or ""
        service = row.get("Service") or row.get("service") or name
        state = row.get("State") or row.get("state") or ""
        health = row.get("Health") or row.get("health") or health_from_status(row.get("Status") or row.get("status"))
        services.append(
            {
                "service": service,
                "name": name,
                "state": state,
                "health": health,
                "exit_code": row.get("ExitCode") or row.get("exit_code"),
            }
        )
    return services


def health_from_status(status: object) -> str:
    text = str(status or "").lower()
    if "unhealthy" in text:
        return "unhealthy"
    if "(healthy)" in text or "healthy" in text:
        return "healthy"
    return ""


def run_exporter(audit_id: str, api_url: str, pattern_limit: int, match_limit: int) -> CommandRun:
    exporter_path = BRIDGE / "export_audit_package.py"
    command = [
        sys.executable,
        str(exporter_path),
        "--audit-id",
        audit_id,
        "--api-url",
        api_url,
        "--pattern-limit",
        str(pattern_limit),
        "--match-limit",
        str(match_limit),
    ]
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = 1
    old_argv = sys.argv[:]
    try:
        spec = importlib.util.spec_from_file_location("tradeo_export_audit_package", exporter_path)
        if not spec or not spec.loader:
            raise RuntimeError(f"cannot import exporter from {exporter_path}")
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        original_read_env = exporter.read_env

        def read_env_with_process_env(path: Path) -> dict[str, str]:
            env = original_read_env(path)
            for key, value in os.environ.items():
                if key.startswith("TRADEO_"):
                    env[key] = value
            env["TRADEO_API_URL"] = api_url
            return env

        exporter.read_env = read_env_with_process_env
        sys.argv = command[1:]
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                exit_code = int(exporter.main())
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
    except Exception as exc:  # noqa: BLE001
        stderr.write(f"{type(exc).__name__}: {exc}\n")
        exit_code = 1
    finally:
        sys.argv = old_argv
    return CommandRun("export", command, exit_code, stdout.getvalue(), stderr.getvalue())


def run_subprocess(name: str, command: list[str], *, blocking: bool = True) -> CommandRun:
    try:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)  # noqa: S603
    except FileNotFoundError as exc:
        return CommandRun(name, command, 127, stderr=f"{type(exc).__name__}: {exc}", blocking=blocking)
    return CommandRun(name, command, completed.returncode, completed.stdout, completed.stderr, blocking)


def deterministic_review(
    audit_id: str,
    cadence: str,
    gate_result: dict[str, Any],
    command_runs: list[CommandRun],
) -> dict[str, Any]:
    blockers = gate_result.get("blockers", []) if isinstance(gate_result, dict) else []
    failed_commands = [run.name for run in command_runs if run.blocking and run.exit_code != 0]
    status = gate_result.get("status", "unknown") if isinstance(gate_result, dict) else "unknown"
    priority = "P0" if failed_commands or blockers else "P2"
    return {
        "audit_id": audit_id,
        "cadence": cadence,
        "agent": "tradeo-internal-daily-auditor",
        "model_profile": "gpt-5.5-xhigh-specified-in-skill; deterministic fallback used by runner",
        "status": status,
        "priority": priority,
        "failed_commands": failed_commands,
        "blocker_count": len(blockers),
        "top_blockers": blockers[:10],
        "director_handoff": "ChatGPT Director must review weekly packs or any P0 blocker before promotion.",
        "promotion_decision": "stay_in_research" if blockers else "eligible_for_director_review",
        "required_next_actions": required_actions(blockers, failed_commands),
    }


def required_actions(blockers: list[str], failed_commands: list[str]) -> list[str]:
    actions: list[str] = []
    if failed_commands:
        actions.append("Fix failed audit commands before trusting the package.")
    if any("paper_trades.csv has zero rows" in blocker for blocker in blockers):
        actions.append("Keep all patterns in research/watchlist until paper trades are exported.")
    if any("ib_fills.csv has zero rows" in blocker for blocker in blockers):
        actions.append("Ingest IB Paper fills with commissions, spread and slippage before promotion.")
    if any("out_of_sample" in blocker for blocker in blockers):
        actions.append("Add explicit OOS/walk-forward boundaries and metrics.")
    if any("market_regime" in blocker or "sector" in blocker for blocker in blockers):
        actions.append("Persist market regime and sector, then regenerate metrics_by_regime.csv.")
    if not actions:
        actions.append("Prepare the package for ChatGPT Director review; do not auto-promote.")
    return actions


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_md(path: Path, result: dict[str, Any]) -> None:
    commands = result.get("commands", [])
    lines = [
        "# Director Audit Run",
        "",
        f"- Audit ID: `{result['audit_id']}`",
        f"- Cadence: `{result['cadence']}`",
        f"- Created at: `{result['created_at']}`",
        f"- Package: `{result['package']}`",
        f"- Director gate status: `{result['director_gate_status']}`",
        f"- Runtime status: `{result.get('runtime_status', {}).get('source', 'unknown')}`",
        "",
        "## Commands",
        "",
        "| name | exit_code | blocking |",
        "|---|---:|---|",
    ]
    lines.extend(f"| {run['name']} | {run['exit_code']} | {run.get('blocking', True)} |" for run in commands)
    lines.extend(["", "## Agent review", "", "```json", json.dumps(result.get("agent_review", {}), indent=2, ensure_ascii=False), "```", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_agent_md(path: Path, review: dict[str, Any]) -> None:
    lines = [
        "# Internal Auditor Agent Review",
        "",
        f"- Audit ID: `{review.get('audit_id')}`",
        f"- Status: `{review.get('status')}`",
        f"- Priority: `{review.get('priority')}`",
        f"- Promotion decision: `{review.get('promotion_decision')}`",
        "",
        "## Top blockers",
        "",
    ]
    blockers = review.get("top_blockers") or []
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None")
    lines.extend(["", "## Required next actions", ""])
    actions = review.get("required_next_actions") or []
    if actions:
        lines.extend(f"- {action}" for action in actions)
    else:
        lines.append("- None")
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
