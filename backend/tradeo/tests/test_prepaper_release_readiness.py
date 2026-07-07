from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUDIT_ID = "TRADEO-AUDIT-20260616-213627_daily_internal"


def _research_root() -> Path:
    for candidate in (_REPO_ROOT / "research", Path("/research")):
        if (candidate / "audit_bridge").is_dir():
            return candidate
    pytest.skip("research/audit_bridge not available in this environment")


def _audit_package() -> Path:
    package = _research_root() / "audit_bridge" / "requests" / _AUDIT_ID
    if not package.is_dir():
        pytest.skip(f"prePaper audit package not available in this checkout: {package}")
    return package


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv_row_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def test_prepaper_audit_package_is_reproducible_and_still_blocked() -> None:
    package = _audit_package()
    manifest = _load_json(package / "manifest.json")
    gate = _load_json(package / "director_gate_result.json")

    assert manifest["audit_id"] == _AUDIT_ID
    assert manifest["contains_sensitive_data"] is False
    assert manifest["account_ids_redacted"] is True
    assert manifest["patterns_detected"] == 500
    assert manifest["total_pattern_events"] == 5619
    assert manifest["total_paper_trades"] == 0
    assert manifest["total_ib_fills"] == 0
    assert manifest["total_experiment_variants"] == 2995

    assert _csv_row_count(package / "pattern_catalog.csv") == 500
    assert _csv_row_count(package / "pattern_events.csv") == 5619
    assert _csv_row_count(package / "paper_trades.csv") == 0
    assert _csv_row_count(package / "ib_fills.csv") == 0
    assert _csv_row_count(package / "experiment_registry.csv") == 2995

    assert gate["director_gate_status"] == "blocked"
    assert gate["promotion_allowed"] is False
    blockers = "\n".join(gate["blockers"])
    for expected in (
        "paper_trades.csv has zero rows",
        "ib_fills.csv has zero rows",
        "PATTERN_000282",
        "PATTERN_000364",
        "PATTERN_000366",
        "271 event rows have blank anti-lookahead",
        "125/5619 rows",
        "nested_discovery_replay not implemented/passed",
    ):
        assert expected in blockers


def test_prepaper_audit_package_hash_manifest_matches_files() -> None:
    package = _audit_package()
    hash_manifest = package / "file_hashes.sha256"

    for line in hash_manifest.read_text(encoding="utf-8").splitlines():
        expected_hash, relative_path = line.split(maxsplit=1)
        target = package / relative_path
        assert target.is_file(), f"hash manifest references missing file {relative_path}"
        actual_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"hash mismatch for {relative_path}"


def test_prepaper_docs_and_makefile_keep_live_blocked_message() -> None:
    paths = {
        "runbook": (
            _REPO_ROOT
            / "docs"
            / "remediation"
            / "prepaper_operational_runbook_2026_06_17.md"
        ),
        "prelive": _REPO_ROOT / "reports" / "Auditoria_Tradeo_V_0_9_preLive.md",
        "readme": _REPO_ROOT / "README.md",
        "makefile": _REPO_ROOT / "Makefile",
    }
    required = ("runbook", "readme", "makefile")
    missing = [name for name in required if not paths[name].is_file()]
    if missing:
        pytest.skip(f"release docs not available in this environment: {missing}")

    runbook = paths["runbook"].read_text(encoding="utf-8")
    readme = paths["readme"].read_text(encoding="utf-8")
    makefile = paths["makefile"].read_text(encoding="utf-8")

    assert "Live remains blocked" in runbook
    assert "Lab/IBKR Paper only" in runbook
    assert "DIRECTOR GATE BLOCKED" in runbook
    assert "Live bloqueado; Lab/IBKR Paper ampliado y medido" in readme
    assert "prepaper-verify:" in makefile
    assert "validate_audit_package.py" in makefile
    assert "director_gate.py" in makefile
    assert "sha256sum -c file_hashes.sha256" in makefile

    if paths["prelive"].is_file():
        prelive = paths["prelive"].read_text(encoding="utf-8")
        assert "Live bloqueado; Paper ampliado y medido" in prelive
