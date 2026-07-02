from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_audit_module():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "audit_intraday_wave_traceability.py"
    spec = importlib.util.spec_from_file_location("audit_intraday_wave_traceability", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _report(audit, *, forensics_run_id: int, evidence_run_id: int):
    return audit.build_traceability_report(
        manifest_run_ids=[10, 11],
        compare_run_ids=[10, 11, 12],
        db_runs=[
            {"run_id": 10, "windows_sampled": 100, "clusters_evaluated": 1, "rejected_patterns": 1},
            {"run_id": 11, "windows_sampled": 100, "clusters_evaluated": 1, "rejected_patterns": 1},
        ],
        patterns_by_run_id={"10": 1, "11": 1},
        examples_by_run_id={},
        metrics_by_run_id={},
        forensics={
            "scope": {"run_ids": [10, 11]},
            "candidate_forensics": [{"run_id": forensics_run_id}],
            "near_misses": [],
        },
        evidence={
            "scope": {"run_ids": [10, 11]},
            "candidate_manifests": [{"run_id": evidence_run_id}],
            "samples_by_candidate": {},
            "summary": {},
        },
        artifact_hashes={"wave_manifest": "a", "forensics_json": "b", "evidence_json": "c"},
    )


def test_audit_detects_forensics_candidate_run_id_outside_manifest() -> None:
    audit = _load_audit_module()

    report = _report(audit, forensics_run_id=12, evidence_run_id=10)

    assert report["status"] == "VIOLATION"
    assert report["decision"] == "invalid_scope_mixed"
    assert report["forensics_out_of_scope_run_ids"] == [12]


def test_audit_passes_when_all_observed_run_ids_are_in_manifest() -> None:
    audit = _load_audit_module()

    report = _report(audit, forensics_run_id=11, evidence_run_id=10)

    assert report["status"] == "OK"
    assert report["decision"] == "valid_exact_scope"
    assert report["forensics_out_of_scope_run_ids"] == []
    assert report["evidence_out_of_scope_run_ids"] == []
