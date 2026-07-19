from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


@pytest.fixture()
def guard_module():
    root = _repo_root()
    path = root / "ops" / "scripts" / "director_audit_chain_guard.py"
    spec = importlib.util.spec_from_file_location("director_audit_chain_guard", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalize_review_preserves_blocked_gate_as_research_only(guard_module) -> None:
    review = guard_module.normalize_review(
        {"cadence": "daily", "top_blockers": ["zero fills"]},
        audit_id="AUDIT-1",
        schema_status="passed",
        gate_status="blocked",
        errors=[],
    )

    assert review["schema_validation_status"] == "passed"
    assert review["promotion_gate_status"] == "blocked"
    assert review["promotion_decision"] == "stay_in_research"
    assert review["priority"] == "P0"


def test_normalize_review_never_eligibilizes_unknown_gate(guard_module) -> None:
    review = guard_module.normalize_review(
        {},
        audit_id="AUDIT-2",
        schema_status="passed",
        gate_status="not_run",
        errors=[],
    )

    assert review["status"] == "invalid"
    assert review["promotion_decision"] == "stay_in_research"


def test_guard_rejects_stale_package(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    package = _write_package(
        repo,
        created_at=datetime.now(timezone.utc) - timedelta(hours=48),
        repo_commit="placeholder",
        discovery_status="completed",
    )
    head = _git(repo, "rev-parse", "HEAD")
    _rewrite_manifest(package, repo_commit=head)

    result = _run_guard(repo, package, "--max-age-hours", "36")

    assert result.returncode == 1
    assert "audit package is stale" in result.stdout


def test_guard_rejects_head_mismatch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    package = _write_package(
        repo,
        created_at=datetime.now(timezone.utc),
        repo_commit="deadbeef",
        discovery_status="completed",
    )

    result = _run_guard(repo, package, "--require-head-commit")

    assert result.returncode == 1
    assert "does not match HEAD" in result.stdout


def test_guard_rejects_gate_before_validation(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    package = _write_package(
        repo,
        created_at=datetime.now(timezone.utc),
        repo_commit="placeholder",
        discovery_status="completed",
    )
    head = _git(repo, "rev-parse", "HEAD")
    _rewrite_manifest(package, repo_commit=head)
    run_path = package / "director_audit_run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["commands"] = [
        {"name": "director_gate", "exit_code": 0},
        {"name": "validate", "exit_code": 0},
    ]
    run_path.write_text(json.dumps(run), encoding="utf-8")

    result = _run_guard(repo, package)

    assert result.returncode == 1
    assert "validate must run before director_gate" in result.stdout


def test_guard_rejects_partial_discovery(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    package = _write_package(
        repo,
        created_at=datetime.now(timezone.utc),
        repo_commit="placeholder",
        discovery_status="partial_failed",
    )
    head = _git(repo, "rev-parse", "HEAD")
    _rewrite_manifest(package, repo_commit=head)

    result = _run_guard(repo, package, "--require-discovery-status")

    assert result.returncode == 1
    assert "source discovery status is not completed" in result.stdout


def test_guard_accepts_complete_blocked_chain_and_normalizes_review(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    package = _write_package(
        repo,
        created_at=datetime.now(timezone.utc),
        repo_commit="placeholder",
        discovery_status="completed",
        gate_status="blocked",
    )
    head = _git(repo, "rev-parse", "HEAD")
    _rewrite_manifest(package, repo_commit=head)

    result = _run_guard(
        repo,
        package,
        "--require-head-commit",
        "--require-discovery-status",
        "--normalize-review",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    review = json.loads((package / "internal_auditor_agent_review.json").read_text(encoding="utf-8"))
    assert review["schema_validation_status"] == "passed"
    assert review["promotion_gate_status"] == "blocked"
    assert review["promotion_decision"] == "stay_in_research"


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "ops" / "scripts" / "director_audit_chain_guard.py").exists():
            return parent
    raise AssertionError("could not locate repo root")


def _init_repo(path: Path) -> Path:
    repo = path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "audit-test@example.invalid")
    _git(repo, "config", "user.name", "Audit Test")
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-qm", "init")
    return repo


def _write_package(
    repo: Path,
    *,
    created_at: datetime,
    repo_commit: str,
    discovery_status: str,
    gate_status: str = "blocked",
) -> Path:
    package = repo / "research" / "audit_bridge" / "requests" / "AUDIT-TEST"
    package.mkdir(parents=True)
    manifest = {
        "audit_id": package.name,
        "created_at": created_at.isoformat(),
        "repo_commit": repo_commit,
        "source_discovery_status": discovery_status,
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (package / "director_gate_result.json").write_text(
        json.dumps({"status": gate_status}), encoding="utf-8"
    )
    (package / "director_gate_result.md").write_text("# Gate\n", encoding="utf-8")
    review = {
        "audit_id": package.name,
        "cadence": "daily",
        "agent": "tradeo-internal-daily-auditor",
        "status": gate_status,
        "priority": "P0",
        "blocker_count": 1,
        "top_blockers": ["test blocker"],
        "promotion_decision": "stay_in_research",
        "required_next_actions": [],
        "director_handoff": "review",
    }
    (package / "internal_auditor_agent_review.json").write_text(
        json.dumps(review), encoding="utf-8"
    )
    (package / "internal_auditor_agent_review.md").write_text("# Review\n", encoding="utf-8")
    run = {
        "audit_id": package.name,
        "director_gate_status": gate_status,
        "commands": [
            {"name": "validate", "exit_code": 0},
            {"name": "director_gate", "exit_code": 0},
        ],
        "agent_review": review,
    }
    (package / "director_audit_run.json").write_text(json.dumps(run), encoding="utf-8")
    (package / "director_audit_run.md").write_text("# Run\n", encoding="utf-8")
    return package


def _rewrite_manifest(package: Path, *, repo_commit: str) -> None:
    path = package / "manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["repo_commit"] = repo_commit
    path.write_text(json.dumps(payload), encoding="utf-8")


def _run_guard(repo: Path, package: Path, *args: str) -> subprocess.CompletedProcess[str]:
    script = _repo_root() / "ops" / "scripts" / "director_audit_chain_guard.py"
    return subprocess.run(
        [sys.executable, str(script), "--package", str(package), *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True
    )
    return result.stdout.strip()
