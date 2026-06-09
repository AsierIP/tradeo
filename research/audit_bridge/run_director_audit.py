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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the automated Tradeo Director audit loop.")
    parser.add_argument("--audit-id", default=None)
    parser.add_argument("--cadence", choices=["daily", "weekly", "manual"], default="daily")
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--pattern-limit", type=int, default=500)
    parser.add_argument("--match-limit", type=int, default=500)
    parser.add_argument("--skip-export", action="store_true")
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    audit_id = args.audit_id or build_audit_id(args.cadence)
    package = REQUESTS / audit_id
    package.mkdir(parents=True, exist_ok=True)
    api_url = args.api_url or os.environ.get("TRADEO_API_URL") or default_api_url()

    runs: list[CommandRun] = []
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
    write_json(package / "internal_auditor_agent_review.json", agent_review)
    write_agent_md(package / "internal_auditor_agent_review.md", agent_review)

    result = {
        "audit_id": audit_id,
        "cadence": args.cadence,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "package": str(package.relative_to(ROOT)),
        "api_url": api_url,
        "director_gate_status": gate_result.get("status", "unknown") if isinstance(gate_result, dict) else "unknown",
        "commands": [asdict(run) for run in runs],
        "agent_review": agent_review,
    }
    write_json(package / "director_audit_run.json", result)
    write_md(package / "director_audit_run.md", result)

    export_failed = any(run.name == "export" and run.exit_code != 0 for run in runs)
    validation_failed = any(run.name == "validate" and run.exit_code != 0 for run in runs)
    blocked = result["director_gate_status"] == "blocked"
    if export_failed or validation_failed:
        return 1
    if blocked and args.fail_on_blocked:
        return 2
    return 0


def build_audit_id(cadence: str) -> str:
    now = datetime.now(timezone.utc)
    return f"TRADEO-AUDIT-{now:%Y%m%d-%H%M%S}_{cadence}_internal"


def default_api_url() -> str:
    if Path("/.dockerenv").exists() or Path("/app").exists():
        return "http://backend:8000/api"
    return "http://localhost:8000/api"


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


def run_subprocess(name: str, command: list[str]) -> CommandRun:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)  # noqa: S603
    return CommandRun(name, command, completed.returncode, completed.stdout, completed.stderr)


def deterministic_review(
    audit_id: str,
    cadence: str,
    gate_result: dict[str, Any],
    command_runs: list[CommandRun],
) -> dict[str, Any]:
    blockers = gate_result.get("blockers", []) if isinstance(gate_result, dict) else []
    failed_commands = [run.name for run in command_runs if run.exit_code != 0]
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
        "",
        "## Commands",
        "",
        "| name | exit_code |",
        "|---|---:|",
    ]
    lines.extend(f"| {run['name']} | {run['exit_code']} |" for run in commands)
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
