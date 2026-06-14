from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import AuditLog, DiscoveredPattern, DiscoveredPatternStatus
from tradeo.db.session import Base
from tradeo.ops.false_match_metrics import (
    collect_false_match_drift_metrics,
    persist_false_match_drift_report,
)


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def add_pattern(db, key: str, *, fpr: float | None, drift_status: str = "stable") -> None:
    metrics = {}
    if fpr is not None:
        metrics["false_match_harness"] = {"fpr_at_recall": fpr}
        metrics["fpr_at_recall90"] = fpr
    db.add(
        DiscoveredPattern(
            pattern_key=key,
            name=key,
            status=DiscoveredPatternStatus.LAB_CANDIDATE,
            side="long",
            timeframe="1d",
            window_size=20,
            cluster_id=1,
            drift_status=drift_status,
            drift_score=0.42 if drift_status != "stable" else 0.0,
            sample_count=100,
            symbol_count=10,
            year_count=3,
            score=0.7,
            validation_passed=True,
            validation_reasons_json=[],
            metrics_json=metrics,
            feature_summary_json={},
        )
    )
    db.commit()


def test_collect_false_match_drift_metrics_counts_high_fpr_and_missing() -> None:
    db = session_factory()
    add_pattern(db, "clean", fpr=0.0)
    add_pattern(db, "dirty", fpr=0.4)
    add_pattern(db, "legacy", fpr=None, drift_status="decaying")

    report = collect_false_match_drift_metrics(db, high_fpr_threshold=0.25)

    assert report["pattern_count"] == 3
    assert report["patterns_with_false_match_harness"] == 2
    assert report["patterns_missing_false_match_harness"] == 1
    assert report["patterns_high_fpr"] == 1
    assert report["patterns_drifted"] == 1
    assert report["worst_patterns"][0]["pattern_key"] == "dirty"


def test_persist_false_match_drift_report_alerts_on_thresholds() -> None:
    db = session_factory()
    add_pattern(db, "dirty", fpr=0.4)
    report = collect_false_match_drift_metrics(db, high_fpr_threshold=0.25)

    persist_false_match_drift_report(db, report)

    actions = [row.action for row in db.query(AuditLog).order_by(AuditLog.id).all()]
    assert actions == ["false_match_drift_metrics_report", "internal_ops_alert"]
