from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import DiscoveredPattern, DiscoveredPatternExample, DiscoveryRun
from tradeo.db.session import Base
from tradeo.research.intraday_research_evidence import (
    ALLOWED_TERMINAL_RECOMMENDATIONS,
    build_evidence_report,
    derive_time_features,
    resolve_run_ids,
    safe_candidate_key,
    session_bucket,
)


def _db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def _seed_run(db, *, with_examples: bool = True) -> int:
    run = DiscoveryRun(
        status="completed",
        symbols_scanned=4,
        windows_sampled=300,
        clusters_evaluated=12,
        accepted_patterns=1,
        rejected_patterns=2,
        summary_json={},
    )
    db.add(run)
    db.flush()
    pattern = DiscoveredPattern(
        run_id=run.id,
        pattern_key="30m W20 4,8,13 / ABC",
        name="ABC candidate",
        status="lab_candidate",
        side="long",
        timeframe="30m",
        window_size=20,
        cluster_id=7,
        sample_count=120,
        symbol_count=2,
        score=1.4,
        expectancy_r=0.25,
        profit_factor=1.8,
        validation_passed=True,
        rejection_reasons_json=["cost review still required"],
        metrics_json={"forward_bars": 6, "cost_base_r": 0.02, "cost_x2_r": 0.04},
    )
    db.add(pattern)
    db.flush()
    if with_examples:
        db.add_all(
            [
                DiscoveredPatternExample(
                    pattern_id=pattern.id,
                    symbol="AAPL",
                    timeframe="30m",
                    window_start="2026-06-01T09:30:00-04:00",
                    window_end="2026-06-01T10:00:00-04:00",
                    forward_end="2026-06-01T13:00:00-04:00",
                    entry_price=10.0,
                    outcome_r=1.25,
                    features_json={"split": "oos", "exit_price": 10.5, "source": "fixture"},
                ),
                DiscoveredPatternExample(
                    pattern_id=pattern.id,
                    symbol="MSFT",
                    timeframe="30m",
                    window_start="2026-06-02T14:00:00-04:00",
                    window_end="2026-06-02T15:05:00-04:00",
                    forward_end="2026-06-02T15:45:00-04:00",
                    entry_price=20.0,
                    outcome_r=-0.5,
                    features_json={"split": "is", "exit_price": 19.5},
                ),
            ]
        )
    db.commit()
    return int(run.id)


def test_resolve_run_ids_from_manifest_and_csv(tmp_path: Path) -> None:
    manifest = tmp_path / "wave.json"
    manifest.write_text(
        json.dumps({"research_result": {"details": {"runs": [{"run_id": 3}, {"run_id": 4}]}}}),
        encoding="utf-8",
    )

    assert resolve_run_ids(wave_manifests=[str(manifest)], run_ids=["1,2", "2"]) == [1, 2, 3, 4]


def test_safe_candidate_filename_is_stable() -> None:
    assert safe_candidate_key("30m W20 4,8,13 / ABC") == "30m_w20_4_8_13_abc"
    assert safe_candidate_key("***") == "candidate"


def test_hour_month_and_session_bucket_derivation() -> None:
    open_features = derive_time_features("2026-06-01T13:45:00+00:00")
    close_features = derive_time_features("2026-06-01T15:05:00")

    assert open_features["hour_of_day"] == 9
    assert open_features["session_bucket"] == "open"
    assert open_features["month"] == "2026-06"
    assert close_features["session_bucket"] == "close"
    assert close_features["timestamp_timezone_assumption"] == "naive_timestamp_assumed_america_new_york"
    assert session_bucket(__import__("datetime").time(11, 0)) == "mid"


def test_build_report_writes_jsonl_and_summary(tmp_path: Path) -> None:
    db = _db()
    run_id = _seed_run(db)

    report = build_evidence_report(
        db=db,
        run_ids=[run_id],
        top_candidates=25,
        artifact_root=tmp_path,
    )

    assert report["schema_version"] == "tradeo.intraday_research_evidence.v1"
    assert report["candidate_count"] == 1
    assert report["sample_count"] == 2
    assert report["safety"]["live_allowed"] is False
    assert report["safety"]["paper_allowed"] is False
    assert report["safety"]["orders_allowed"] is False
    assert report["summary"]["by_symbol"]["AAPL"]["outcome_mean_r"] == 1.25
    assert report["summary"]["by_session"]["open"]["n"] == 1
    assert report["summary"]["by_session"]["close"]["n"] == 1
    assert report["summary"]["by_month"]["2026-06"]["n"] == 2
    assert report["summary"]["by_split"]["oos"]["n"] == 1
    assert report["summary"]["terminal_research_recommendation"] in ALLOWED_TERMINAL_RECOMMENDATIONS
    assert report["summary"]["terminal_research_recommendation"] == "candidate_for_shadow_review"

    jsonl = tmp_path / f"run_{run_id}" / "candidate_30m_w20_4_8_13_abc.jsonl"
    assert jsonl.exists()
    lines = jsonl.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(json.loads(line)["candidate_key"] == "30m_w20_4_8_13_abc" for line in lines)
    assert (tmp_path / "_summary.json").exists()
    assert (tmp_path / "_summary.md").exists()


def test_missing_fields_are_null_or_not_available_and_counted() -> None:
    db = _db()
    run = DiscoveryRun(status="completed", clusters_evaluated=1)
    db.add(run)
    db.flush()
    pattern = DiscoveredPattern(
        run_id=run.id,
        pattern_key="missing",
        name="missing",
        timeframe="5m",
        sample_count=5,
        symbol_count=1,
    )
    db.add(pattern)
    db.flush()
    db.add(DiscoveredPatternExample(pattern_id=pattern.id, symbol="", window_end="", entry_price=0.0))
    db.commit()

    report = build_evidence_report(db=db, run_ids=[int(run.id)])
    sample = report["samples_by_candidate"]["missing"][0]

    assert sample["symbol"] is None
    assert sample["session_bucket"] == "unknown"
    assert sample["split"] == "not_available"
    assert report["missing_fields_summary"]["symbol"] == 1
    assert report["missing_fields_summary"]["month"] == 1


def test_limits_truncate_candidates_and_samples(tmp_path: Path) -> None:
    db = _db()
    run_id = _seed_run(db)

    report = build_evidence_report(
        db=db,
        run_ids=[run_id],
        max_candidates=1,
        max_samples_per_candidate=1,
        max_total_samples=1,
        artifact_root=tmp_path,
    )

    assert report["candidate_count"] == 1
    assert report["sample_count"] == 1
    assert report["truncated"] is True


def test_terminal_recommendation_never_mentions_paper_or_live() -> None:
    db = _db()
    run_id = _seed_run(db, with_examples=False)

    report = build_evidence_report(db=db, run_ids=[run_id])
    recommendation = report["summary"]["terminal_research_recommendation"]

    assert recommendation in ALLOWED_TERMINAL_RECOMMENDATIONS
    assert "paper" not in recommendation
    assert "live" not in recommendation


def test_safety_flags_are_false_for_execution_surfaces() -> None:
    db = _db()
    run_id = _seed_run(db)

    safety = build_evidence_report(db=db, run_ids=[run_id])["safety"]

    assert safety["live_allowed"] is False
    assert safety["paper_allowed"] is False
    assert safety["orders_allowed"] is False
    assert safety["broker_allowed"] is False
    assert safety["read_only"] is True
