from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import DiscoveredPattern, DiscoveredPatternExample, DiscoveryRun
from tradeo.db.session import Base


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


def _session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)


def _seed_runs(session_factory) -> None:
    db = session_factory()
    try:
        for run_id in (100, 101, 102):
            run = DiscoveryRun(
                id=run_id,
                status="completed",
                windows_sampled=10,
                clusters_evaluated=1,
                accepted_patterns=0,
                rejected_patterns=1,
                params_json={
                    "interval": "30m",
                    "period": "60d",
                    "window_sizes": [100],
                    "forward_bars": [8, 13, 21],
                    "vwap_condition": "vwap_reclaim_long",
                    "vwap_side_bias": "long",
                },
            )
            db.add(run)
            db.flush()
            pattern = DiscoveredPattern(
                run_id=run_id,
                pattern_key=f"p{run_id}",
                name=f"p{run_id}",
                status="rejected",
                timeframe="30m",
                window_size=100,
                sample_count=1,
                symbol_count=1,
            )
            db.add(pattern)
            db.flush()
            db.add(DiscoveredPatternExample(pattern_id=pattern.id, symbol="AAPL"))
        db.commit()
    finally:
        db.close()


def _write_inputs(tmp_path: Path, *, artifact_run_id: int) -> tuple[Path, Path, Path]:
    manifest = tmp_path / "wave.json"
    manifest.write_text(
        json.dumps({"research_result": {"details": {"runs": [{"run_id": 100}, {"run_id": 101}]}}}),
        encoding="utf-8",
    )
    forensics = tmp_path / "forensics.json"
    forensics.write_text(
        json.dumps(
            {
                "scope": {"exact_scope": True, "run_ids": [100, 101]},
                "candidate_forensics": [{"run_id": artifact_run_id}],
                "near_misses": [],
            }
        ),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        json.dumps(
            {
                "scope": {"exact_scope": True, "run_ids": [100, 101]},
                "candidate_manifests": [{"run_id": artifact_run_id}],
                "samples_by_candidate": {"candidate": [{"run_id": artifact_run_id}]},
            }
        ),
        encoding="utf-8",
    )
    return manifest, forensics, evidence


def test_audit_detects_forensics_candidate_outside_manifest(monkeypatch, tmp_path: Path) -> None:
    audit = _load_audit_module()
    session_factory = _session_factory()
    _seed_runs(session_factory)
    monkeypatch.setattr(audit, "SessionLocal", session_factory)
    manifest, forensics, evidence = _write_inputs(tmp_path, artifact_run_id=102)

    report = audit.build_traceability_audit(
        wave_manifest=manifest,
        compare_run_ids=[100, 101, 102],
        forensics_json=forensics,
        evidence_json=evidence,
    )

    assert report["status"] == "VIOLATION"
    assert report["decision"] == "invalid_scope_mixed"
    assert report["forensics_out_of_scope_run_ids"] == [102]


def test_audit_passes_when_all_run_ids_are_in_manifest(monkeypatch, tmp_path: Path) -> None:
    audit = _load_audit_module()
    session_factory = _session_factory()
    _seed_runs(session_factory)
    monkeypatch.setattr(audit, "SessionLocal", session_factory)
    manifest, forensics, evidence = _write_inputs(tmp_path, artifact_run_id=101)

    report = audit.build_traceability_audit(
        wave_manifest=manifest,
        compare_run_ids=[100, 101, 102],
        forensics_json=forensics,
        evidence_json=evidence,
    )

    assert report["status"] == "OK"
    assert report["decision"] == "valid_exact_scope"
    assert report["evidence_out_of_scope_run_ids"] == []
