from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog


@dataclass
class DirectorAuditAutomation:
    """Backend integration for the repository-level Director audit bridge."""

    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def run_daily(self, db: Session | None = None, *, reason: str = "scheduled") -> dict[str, Any]:
        return self._run(cadence="daily", db=db, reason=reason)

    def run_weekly(self, db: Session | None = None, *, reason: str = "scheduled") -> dict[str, Any]:
        return self._run(cadence="weekly", db=db, reason=reason)

    def _run(self, *, cadence: str, db: Session | None, reason: str) -> dict[str, Any]:
        root = find_repo_root()
        runner = root / "research" / "audit_bridge" / "run_director_audit.py"
        command = [
            sys.executable,
            str(runner),
            "--cadence",
            cadence,
            "--api-url",
            self._api_url(),
            "--pattern-limit",
            str(self.settings.director_audit_pattern_limit),
            "--match-limit",
            str(self.settings.director_audit_match_limit),
        ]
        if self.settings.director_audit_fail_on_blocked:
            command.append("--fail-on-blocked")
        run = run_command(command, root=root, timeout=self.settings.director_audit_command_timeout_seconds)
        payload = latest_audit_run(root) or {
            "audit_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "director_gate_status": "unknown",
        }
        payload.update({"reason": reason, "cadence": cadence, "command": run})
        self._audit_log(db, "director_audit_completed" if run["exit_code"] == 0 else "director_audit_failed", payload)
        return payload

    def run_gate(self, package: str | Path, db: Session | None = None, *, reason: str = "manual") -> dict[str, Any]:
        root = find_repo_root()
        package_path = Path(package)
        if not package_path.is_absolute():
            package_path = root / package_path
        gate_json = package_path / "director_gate_result.json"
        gate_md = package_path / "director_gate_result.md"
        command = [
            sys.executable,
            str(root / "research" / "audit_bridge" / "director_gate.py"),
            str(package_path),
            "--json-output",
            str(gate_json),
            "--markdown-output",
            str(gate_md),
            "--allow-blocked-exit-zero",
        ]
        run = run_command(command, root=root, timeout=self.settings.director_audit_command_timeout_seconds)
        payload = {"reason": reason, "package": str(package_path), "command": run, "director_gate": read_json(gate_json)}
        self._audit_log(db, "director_gate_completed", payload)
        return payload

    def _api_url(self) -> str:
        configured = getattr(self.settings, "director_audit_api_url", None)
        if configured:
            return configured.rstrip("/")
        if Path("/.dockerenv").exists() or Path("/app").exists():
            return "http://backend:8000/api"
        return "http://localhost:8000/api"

    def _audit_log(self, db: Session | None, action: str, payload: dict[str, Any]) -> None:
        if db is None:
            return
        db.add(
            AuditLog(
                actor="director_audit_automation",
                action=action,
                entity_type="audit_package",
                entity_id=str(payload.get("audit_id") or payload.get("package") or "unknown"),
                details_json=payload,
            )
        )
        db.commit()


def find_repo_root() -> Path:
    for candidate in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (candidate / "research" / "audit_bridge").exists():
            return candidate
    raise FileNotFoundError("could not locate repository root containing research/audit_bridge")


def run_command(command: list[str], *, root: Path, timeout: int) -> dict[str, Any]:
    logger.info("running Director audit command: {}", " ".join(command))
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout_tail": completed.stdout[-8000:],
        "stderr_tail": completed.stderr[-8000:],
    }


def latest_audit_run(root: Path) -> dict[str, Any] | None:
    requests = root / "research" / "audit_bridge" / "requests"
    files = sorted(requests.glob("*/director_audit_run.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    return read_json(files[0]) if files else None


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
