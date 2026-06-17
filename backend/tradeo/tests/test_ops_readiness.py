from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_compose_binds_public_ports_to_localhost_by_default() -> None:
    compose = (_REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "${TRADEO_BACKEND_BIND:-127.0.0.1}:8000:8000" in compose
    assert "${TRADEO_FRONTEND_BIND:-127.0.0.1}:3000:3000" in compose
    assert '"8000:8000"' not in compose
    assert '"3000:3000"' not in compose


def test_director_audit_workflow_uses_current_or_requested_package() -> None:
    workflow = (
        _REPO_ROOT / ".github" / "workflows" / "director-audit.yml"
    ).read_text(encoding="utf-8")

    assert "2026-06-07_ib_paper_patterns" not in workflow
    assert "github.event.inputs.audit_package" in workflow
    assert "ops/scripts/director_audit_ci.py" in workflow
    assert "TRADEO_AUDIT_PACKAGE" in workflow


def test_director_audit_ci_requires_tracked_hashed_package() -> None:
    script = (_REPO_ROOT / "ops" / "scripts" / "director_audit_ci.py").read_text(
        encoding="utf-8"
    )

    assert "Untracked audit evidence" in script
    assert "file_hashes.sha256 is required" in script
    assert "manifest.audit_id must match package directory" in script
    assert "Director gate is BLOCKED" in script
