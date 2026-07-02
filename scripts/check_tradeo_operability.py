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


SCHEMA_VERSION = "tradeo.operability_preflight.v1"

SAFETY_FLAGS = (
    "TRADEO_TRADING_MODE",
    "TRADEO_LIVE_TRADING_ENABLED",
    "TRADEO_INTRADAY_PAPER_ENABLED",
    "TRADEO_INTRADAY_LIVE_ENABLED",
    "TRADEO_IBKR_READONLY",
    "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA",
    "TRADEO_KILL_SWITCH_ENABLED",
)

CRITICAL_FILES = (
    "docker-compose.yml",
    ".env.example",
    "backend/Dockerfile",
    "frontend/Dockerfile",
    "scripts/run_intraday_research_wave.py",
    "scripts/check_intraday_research_readiness.py",
    "scripts/plan_intraday_research_next.py",
    "scripts/analyze_intraday_research_forensics.py",
)

ARTIFACT_GROUPS = {
    "latest_universe_metadata": ("artifacts/runtime/*universe*.metadata.json",),
    "latest_readiness_manifest": ("artifacts/runtime/intraday_research_readiness_*.json",),
    "latest_wave_manifest": ("artifacts/runtime/intraday_research_wave_*.json",),
    "latest_forensics": ("artifacts/runtime/research_forensics/*.json",),
    "latest_planner": ("artifacts/runtime/research_plans/*.json",),
}

SENSITIVE_NAME_RE = re.compile(r"(KEY|SECRET|PASSWORD|TOKEN|ACCOUNT)", re.IGNORECASE)
LONG_CREDENTIAL_RE = re.compile(r"^[A-Za-z0-9_./+=:-]{32,}$")


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
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
        return CommandResult(command, None, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command,
            None,
            exc.stdout or "",
            f"timed out after {timeout}s",
        )
    return CommandResult(command, completed.returncode, completed.stdout, completed.stderr)


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
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            values[key] = value
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
    env = parse_env_file(path) if path else {}
    env.update({key: value for key, value in os.environ.items() if key.startswith("TRADEO_")})
    return source, env


def is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on", "enabled"}


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


def git_repo_summary(repo_root: Path) -> dict[str, Any]:
    status = run_command(["git", "status", "--porcelain"], repo_root)
    tracked: list[str] = []
    untracked: list[str] = []
    if status.exit_code == 0:
        for line in status.stdout.splitlines():
            if not line:
                continue
            path = line[3:] if len(line) > 3 else line
            if line.startswith("??"):
                untracked.append(path)
            else:
                tracked.append(path)
    return {
        "root": str(repo_root),
        "branch": git_value(repo_root, ["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "commit_sha": git_value(repo_root, ["git", "rev-parse", "HEAD"]),
        "dirty": bool(tracked or untracked) if status.exit_code == 0 else True,
        "tracked_changes": tracked[:50],
        "untracked_changes": untracked[:50],
        "git_status_exit_code": status.exit_code,
    }


def check_critical_files(repo_root: Path) -> list[dict[str, Any]]:
    return [{"path": item, "exists": (repo_root / item).exists()} for item in CRITICAL_FILES]


def docker_compose_check(repo_root: Path) -> dict[str, Any]:
    result = run_command(["docker", "compose", "config", "--quiet"], repo_root, timeout=60)
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return {
        "config_ok": result.exit_code == 0,
        "exit_code": result.exit_code,
        "error": output[:1000],
    }


def env_summary(source: str | None, env: dict[str, str]) -> dict[str, Any]:
    sensitive_keys = sorted(key for key, value in env.items() if looks_sensitive(key, value))
    return {
        "source": source,
        "redaction_ok": True,
        "safety_flags": {key: redact_value(key, env.get(key)) for key in SAFETY_FLAGS},
        "sensitive_keys_redacted": sensitive_keys,
    }


def safety_summary(env: dict[str, str], allow_paper_enabled: bool = False) -> tuple[dict[str, Any], list[str]]:
    reasons: list[str] = []
    trading_mode = str(env.get("TRADEO_TRADING_MODE", "")).strip().lower()
    ibkr_readonly = str(env.get("TRADEO_IBKR_READONLY", "")).strip().lower() == "true"
    synthetic_allowed = is_truthy(env.get("TRADEO_ALLOW_SYNTHETIC_MARKET_DATA"))
    paper_enabled = is_truthy(env.get("TRADEO_INTRADAY_PAPER_ENABLED"))

    if trading_mode == "live":
        reasons.append("TRADEO_TRADING_MODE=live")
    if is_truthy(env.get("TRADEO_LIVE_TRADING_ENABLED")):
        reasons.append("TRADEO_LIVE_TRADING_ENABLED=true")
    if is_truthy(env.get("TRADEO_INTRADAY_LIVE_ENABLED")):
        reasons.append("TRADEO_INTRADAY_LIVE_ENABLED=true")
    if not ibkr_readonly:
        reasons.append("TRADEO_IBKR_READONLY is not true")
    if synthetic_allowed:
        reasons.append("TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=true")
    if paper_enabled and not allow_paper_enabled:
        reasons.append("TRADEO_INTRADAY_PAPER_ENABLED=true without --allow-paper-enabled")

    return (
        {
            "live_allowed": False,
            "paper_allowed": bool(paper_enabled and allow_paper_enabled),
            "orders_allowed": False,
            "order_code_changed": False,
            "gates_relaxed": False,
            "ibkr_readonly": ibkr_readonly,
            "synthetic_market_data_allowed": synthetic_allowed,
            "paper_trades": "not_checked",
            "ib_fills": "not_checked",
            "kill_switch_enabled": is_truthy(env.get("TRADEO_KILL_SWITCH_ENABLED")),
        },
        reasons,
    )


def safe_json_excerpt(path: Path) -> dict[str, Any] | None:
    if path.stat().st_size > 2_000_000:
        return {"skipped": "file_too_large"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    keys = (
        "status",
        "product_policy",
        "selected_count",
        "coverage",
        "readiness_coverage",
        "run_ids",
        "accepted",
        "rejected",
        "persisted_candidates",
        "universe_file",
    )
    return {key: data[key] for key in keys if key in data}


def latest_artifact(repo_root: Path, patterns: tuple[str, ...]) -> dict[str, Any] | None:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(path for path in repo_root.glob(pattern) if path.is_file())
    if not files:
        return None
    latest = max(files, key=lambda path: path.stat().st_mtime)
    stat = latest.stat()
    return {
        "path": str(latest.relative_to(repo_root)),
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "size_bytes": stat.st_size,
        "fields": safe_json_excerpt(latest),
    }


def latest_artifacts(repo_root: Path) -> dict[str, Any]:
    return {key: latest_artifact(repo_root, patterns) for key, patterns in ARTIFACT_GROUPS.items()}


def decide_status(
    repo: dict[str, Any],
    env_source: str | None,
    critical_files: list[dict[str, Any]],
    docker_compose: dict[str, Any],
    blocked_reasons: list[str],
) -> tuple[str, list[str]]:
    if blocked_reasons:
        return "BLOCKED", blocked_reasons
    reasons: list[str] = []
    if repo["git_status_exit_code"] != 0 or repo["commit_sha"] == "unknown":
        reasons.append("repo is not a valid git checkout")
    missing = [item["path"] for item in critical_files if not item["exists"]]
    if missing:
        reasons.append("missing critical files: " + ", ".join(missing))
    if not docker_compose["config_ok"]:
        reasons.append("docker compose config --quiet failed")
    if env_source is None:
        reasons.append(".env and .env.example are absent")
    if reasons:
        return "NOT_READY", reasons
    return "OPERABLE_READ_ONLY", ["all read-only operability checks passed"]


def build_report(
    repo_root: Path,
    env_file: Path | None = None,
    allow_paper_enabled: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    env_source, env = collect_env(repo_root, env_file)
    repo = git_repo_summary(repo_root)
    critical_files = check_critical_files(repo_root)
    compose = docker_compose_check(repo_root)
    safety, blocked_reasons = safety_summary(env, allow_paper_enabled=allow_paper_enabled)
    status, decision_reasons = decide_status(repo, env_source, critical_files, compose, blocked_reasons)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "decision_reasons": decision_reasons,
        "repo": repo,
        "critical_files": critical_files,
        "docker_compose": compose,
        "env": env_summary(env_source, env),
        "safety": safety,
        "artifacts": latest_artifacts(repo_root),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Tradeo Operability Preflight",
        "",
        f"Status: {report['status']}",
        f"Generated: {report['generated_at']}",
        f"Repo: {report['repo']['root']}",
        f"Branch: {report['repo']['branch']}",
        f"Commit: {report['repo']['commit_sha']}",
        "",
        "## Decision reasons",
        "",
    ]
    lines.extend(f"- {reason}" for reason in report["decision_reasons"])
    lines.extend(["", "## Safety flags", ""])
    for key, value in report["env"]["safety_flags"].items():
        lines.append(f"- {key}: {value if value not in (None, '') else 'unset'}")
    lines.extend(
        [
            f"- live_allowed: {report['safety']['live_allowed']}",
            f"- paper_allowed: {report['safety']['paper_allowed']}",
            f"- orders_allowed: {report['safety']['orders_allowed']}",
            f"- order_code_changed: {report['safety']['order_code_changed']}",
            f"- gates_relaxed: {report['safety']['gates_relaxed']}",
            f"- ibkr_readonly: {report['safety']['ibkr_readonly']}",
            f"- synthetic_market_data_allowed: {report['safety']['synthetic_market_data_allowed']}",
            f"- kill_switch_enabled: {report['safety']['kill_switch_enabled']}",
        ]
    )
    lines.extend(["", "## Docker Compose", ""])
    lines.append(f"- config_ok: {report['docker_compose']['config_ok']}")
    lines.append(f"- exit_code: {report['docker_compose']['exit_code']}")
    if report["docker_compose"]["error"]:
        lines.append(f"- error: {report['docker_compose']['error']}")
    lines.extend(["", "## Critical files", ""])
    for item in report["critical_files"]:
        lines.append(f"- {item['path']}: {'present' if item['exists'] else 'missing'}")
    lines.extend(["", "## Latest artifacts", ""])
    for key, item in report["artifacts"].items():
        if item is None:
            lines.append(f"- {key}: missing")
        else:
            lines.append(f"- {key}: {item['path']} ({item['size_bytes']} bytes)")
    lines.extend(["", "## Director decision", ""])
    if report["status"] == "OPERABLE_READ_ONLY":
        lines.append("- Continue read-only research/control work; do not enable paper/live or orders.")
    elif report["status"] == "BLOCKED":
        lines.append("- Block execution until Director/Asier resolves safety flags.")
    else:
        lines.append("- Resolve readiness/configuration gaps before continuing.")
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tradeo read-only operability preflight.")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--allow-paper-enabled", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--json-out", default="artifacts/runtime/operability/latest_operability.json")
    parser.add_argument("--md-out", default="artifacts/runtime/operability/latest_operability.md")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    env_file = Path(args.env_file).resolve() if args.env_file else None
    report = build_report(repo_root, env_file=env_file, allow_paper_enabled=args.allow_paper_enabled)

    if not args.json_only:
        write_outputs(report, repo_root / args.json_out, repo_root / args.md_out)
    print(json.dumps(report, indent=2, sort_keys=True))

    if report["status"] == "BLOCKED":
        return 2
    if report["status"] == "NOT_READY":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
