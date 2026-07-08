from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import DiscoveredPattern, DiscoveredPatternExample, DiscoveryRun
from tradeo.db.session import Base
from tradeo.research.intraday_vwap_confirmation import (
    DEFAULT_PATTERN_KEY,
    DEFAULT_RUN_ID,
    CandidateScope,
    CandidateScopeError,
    build_candidate_confirmation_dataset,
    load_candidate_artifacts,
    load_db_candidate_events,
    validate_requested_scope,
)


def _db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _artifact_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    root = tmp_path / "project"
    wave = _write_json(
        root / "wave.json",
        {
            "research_result": {
                "details": {"runs": [{"run_id": DEFAULT_RUN_ID}, {"run_id": 6455}]}
            },
            "readiness": {
                "spec": {
                    "period": "60d",
                    "timeframes": ["30m"],
                    "window_sizes": [100],
                    "forward_bars": [8, 13, 21],
                }
            },
        },
    )
    forensics = _write_json(
        root / "forensics.json",
        {
            "scope": {"run_ids": [DEFAULT_RUN_ID, 6455]},
            "candidate_forensics": [
                {
                    "run_id": DEFAULT_RUN_ID,
                    "pattern_key": DEFAULT_PATTERN_KEY,
                    "timeframe": "30m",
                    "window_size": 100,
                }
            ],
        },
    )
    evidence_jsonl = (
        root
        / "evidence_payloads"
        / "run_6454"
        / f"candidate_{DEFAULT_PATTERN_KEY}.jsonl"
    )
    evidence_jsonl.parent.mkdir(parents=True, exist_ok=True)
    evidence_jsonl.write_text(
        json.dumps(
            {
                "run_id": DEFAULT_RUN_ID,
                "pattern_key": DEFAULT_PATTERN_KEY,
                "candidate_key": DEFAULT_PATTERN_KEY,
                "symbol": "LCID",
                "timeframe": "30m",
                "window_size": 100,
                "window_start_ts": "2026-04-20T13:00:00-04:00",
                "window_end_ts": "2026-04-30T10:30:00-04:00",
                "entry_ts": "2026-04-30T10:30:00-04:00",
                "entry_price": 5.965,
                "outcome_r": 1.25,
                "exit_ts": "2026-05-01T14:30:00-04:00",
                "session_bucket": "mid",
                "month": "2026-04",
                "source": "discovered_pattern_examples",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    evidence = _write_json(
        root / "evidence.json",
        {
            "scope": {"run_ids": [DEFAULT_RUN_ID, 6455]},
            "candidate_manifests": [
                {
                    "run_id": DEFAULT_RUN_ID,
                    "pattern_key": DEFAULT_PATTERN_KEY,
                    "candidate_key": DEFAULT_PATTERN_KEY,
                    "timeframe": "30m",
                    "window_size": 100,
                }
            ],
            "artifacts": {
                "runs": {
                    str(DEFAULT_RUN_ID): [
                        {
                            "jsonl": str(evidence_jsonl.relative_to(root)),
                            "sample_count": 1,
                        }
                    ]
                }
            },
        },
    )
    cache_dir = root / "ohlcv_cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "LCID_30m_60d.csv").write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume,adjusted,what_to_show,bar_complete",
                "2026-04-30T09:30:00-0400,5.8,6.0,5.7,5.9,1000,True,ADJUSTED_LAST,True",
                "2026-04-30T10:00:00-0400,5.9,6.1,5.8,6.0,2000,True,ADJUSTED_LAST,True",
                "2026-04-30T10:30:00-0400,6.0,6.1,5.9,5.965,3000,True,ADJUSTED_LAST,True",
            ]
        ),
        encoding="utf-8",
    )
    return wave, forensics, evidence, cache_dir


def test_build_candidate_confirmation_dataset_filters_target_and_enriches_vwap(
    tmp_path: Path,
) -> None:
    wave, forensics, evidence, cache_dir = _artifact_fixture(tmp_path)

    report = build_candidate_confirmation_dataset(
        wave_manifest_path=wave,
        forensics_json_path=forensics,
        evidence_json_path=evidence,
        ohlcv_cache_dir=cache_dir,
        project_root=wave.parent,
    )

    assert report["schema_version"] == "tradeo.intraday_vwap_confirmation.v1"
    assert report["scope"]["requested_run_id"] == DEFAULT_RUN_ID
    assert report["scope"]["out_of_scope_artifact_run_ids"] == [6455]
    assert report["event_count"] == 1
    event = report["events"][0]
    assert event["run_id"] == DEFAULT_RUN_ID
    assert event["pattern_key"] == DEFAULT_PATTERN_KEY
    assert event["candidate_id"] == DEFAULT_PATTERN_KEY
    assert event["forward_end"] == "2026-05-01T14:30:00-04:00"
    assert event["risk_proxy"] is None
    assert event["vwap_at_entry"] is not None
    assert event["price_vs_vwap_bps"] is not None
    assert event["data_quality"]["filled_from"]["vwap_at_entry"] == "ohlcv_cache"
    assert report["safety"]["orders_allowed"] is False
    assert report["safety"]["read_only"] is True


def test_strict_artifact_scope_rejects_extra_run_ids(tmp_path: Path) -> None:
    wave, forensics, evidence, _ = _artifact_fixture(tmp_path)
    artifacts = load_candidate_artifacts(
        wave_manifest_path=wave,
        forensics_json_path=forensics,
        evidence_json_path=evidence,
    )

    with pytest.raises(CandidateScopeError, match="additional run IDs"):
        validate_requested_scope(
            artifacts,
            scope=CandidateScope(),
            strict_artifact_scope=True,
        )


def test_out_of_scope_event_row_is_rejected(tmp_path: Path) -> None:
    wave, forensics, evidence, _ = _artifact_fixture(tmp_path)
    payload_path = (
        wave.parent
        / "evidence_payloads"
        / "run_6454"
        / f"candidate_{DEFAULT_PATTERN_KEY}.jsonl"
    )
    row = json.loads(payload_path.read_text(encoding="utf-8"))
    row["run_id"] = 9999
    payload_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(CandidateScopeError, match="out-of-scope run_id"):
        build_candidate_confirmation_dataset(
            wave_manifest_path=wave,
            forensics_json_path=forensics,
            evidence_json_path=evidence,
            project_root=wave.parent,
        )


def test_db_read_only_examples_fill_research_event_fields() -> None:
    db = _db()
    run = DiscoveryRun(id=DEFAULT_RUN_ID, status="completed")
    db.add(run)
    pattern = DiscoveredPattern(
        run_id=DEFAULT_RUN_ID,
        pattern_key=DEFAULT_PATTERN_KEY,
        name="target",
        timeframe="30m",
        window_size=100,
        sample_count=1,
        symbol_count=1,
    )
    db.add(pattern)
    db.flush()
    db.add(
        DiscoveredPatternExample(
            pattern_id=pattern.id,
            symbol="LCID",
            timeframe="30m",
            window_start="2026-04-20T13:00:00-04:00",
            window_end="2026-04-30T10:30:00-04:00",
            forward_end="2026-05-01T14:30:00-04:00",
            entry_price=5.965,
            risk_proxy=0.42,
            outcome_r=1.25,
            mfe_r=2.0,
            mae_r=0.5,
        )
    )
    db.commit()

    records = load_db_candidate_events(db, scope=CandidateScope())

    assert len(records) == 1
    event = records[0].to_dict()
    assert event["pattern_id"] == pattern.id
    assert event["risk_proxy"] == 0.42
    assert event["mfe_r"] == 2.0
    assert event["mae_r"] == 0.5
