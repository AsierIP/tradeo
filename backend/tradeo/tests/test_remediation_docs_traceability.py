"""Traceability checks for the 12-phase remediation documentation.

Every remediation report under ``docs/remediation`` lists the files it
changed. These tests assert that those references still resolve to real
files in the repository, so the audit package cannot silently drift away
from the code it claims to describe.

The docs tree is not copied into the Docker image (only ``backend/tradeo``
and ``research`` are), so the tests skip when ``docs/remediation`` is not
present next to the backend tree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REMEDIATION_DIR = _REPO_ROOT / "docs" / "remediation"

_FILES_CHANGED_HEADING = re.compile(r"^##\s+Files Changed\s*$", re.MULTILINE)
_BULLET_PATH = re.compile(r"^-\s+`([^`]+)`\s*$")


def _files_changed_entries(doc: Path) -> list[str]:
    text = doc.read_text(encoding="utf-8")
    match = _FILES_CHANGED_HEADING.search(text)
    if match is None:
        return []
    section = text[match.end() :]
    next_heading = re.search(r"^##\s+", section, re.MULTILINE)
    if next_heading is not None:
        section = section[: next_heading.start()]
    entries: list[str] = []
    for line in section.splitlines():
        bullet = _BULLET_PATH.match(line.strip())
        if bullet is not None:
            entries.append(bullet.group(1))
    return entries


def _remediation_docs() -> list[Path]:
    if not _REMEDIATION_DIR.is_dir():
        return []
    return sorted(_REMEDIATION_DIR.glob("*.md"))


def test_remediation_docs_directory_present_or_skipped() -> None:
    if not _REMEDIATION_DIR.is_dir():
        pytest.skip("docs/remediation not available in this environment")
    assert _remediation_docs(), "docs/remediation exists but holds no reports"


def test_files_changed_references_resolve_to_real_files() -> None:
    docs = _remediation_docs()
    if not docs:
        pytest.skip("docs/remediation not available in this environment")
    checked = 0
    missing: list[str] = []
    for doc in docs:
        for entry in _files_changed_entries(doc):
            checked += 1
            if not (_REPO_ROOT / entry).is_file():
                missing.append(f"{doc.name}: {entry}")
    assert checked > 0, "no Files Changed entries found in any remediation doc"
    assert not missing, f"remediation docs reference missing files: {missing}"


def test_compliance_matrix_covers_all_agents() -> None:
    matrix = _REMEDIATION_DIR / "tradeo_12_phase_compliance_matrix_2026_06_10.md"
    if not matrix.is_file():
        pytest.skip("docs/remediation not available in this environment")
    text = matrix.read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith("|")]
    agents_with_rows = {
        cells[2]
        for line in rows
        if len(cells := [cell.strip() for cell in line.split("|")]) > 3
    }
    for agent in ("A", "B", "C", "D"):
        assert agent in agents_with_rows, f"matrix lost agent {agent} rows"


def test_audit_export_exposes_independent_sample_fields() -> None:
    """The audit export contract keeps the honest-count fields added by D."""
    export_script = _REPO_ROOT / "research" / "audit_bridge" / "export_audit_package.py"
    if not export_script.is_file():
        pytest.skip("research/audit_bridge not available in this environment")
    text = export_script.read_text(encoding="utf-8")
    for field in ("is_independent_sample", "independent_sample_count", "event_count"):
        assert field in text, f"audit export lost honest-count field {field!r}"
