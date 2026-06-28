from __future__ import annotations

import numpy as np
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import (
    AuditLog,
    DiscoveredPattern,
    DiscoveredPatternExample,
    DiscoveredPatternMetric,
    DiscoveredPatternStatus,
)
from tradeo.db.session import Base
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher, _optional_limit
from tradeo.research.novel_pattern_registry import NovelPatternRegistry
from tradeo.research.types import ClusterCandidate


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def test_zero_match_limit_means_unbounded() -> None:
    assert _optional_limit(0, 25) is None
    assert _optional_limit(None, 0) is None
    assert _optional_limit(None, 25) == 25
    assert _optional_limit(10, 25) == 10


def _candidate(pattern_key: str, centroid: list[float], score: float = 0.8) -> ClusterCandidate:
    return ClusterCandidate(
        pattern_key=pattern_key,
        name=pattern_key.upper(),
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=centroid,
        sample_count=140,
        symbol_count=12,
        year_count=3,
        score=score,
        validation_passed=True,
        validation_reasons=[],
        metrics={
            "promotion_status": "lab_candidate",
            "reward_risk_estimate": 3.0,
            "expectancy_r": 0.4,
            "profit_factor": 2.1,
            "best_expectancy_r": 0.4,
            "best_profit_factor": 2.1,
            "win_rate": 0.48,
            "stability_score": 0.62,
            "out_of_sample_expectancy_r": 0.2,
            "out_of_sample_profit_factor": 1.6,
        },
        feature_summary={},
        examples=[],
    )


def _example(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "timeframe": "1d",
        "window_start": "2026-01-01",
        "window_end": "2026-01-20",
        "forward_end": "2026-01-27",
        "entry_price": 10.0,
        "risk_proxy": 0.25,
        "outcome_r": 0.5,
        "mfe_r": 1.0,
        "mae_r": -0.2,
        "similarity": 0.91,
        "kind": "typical",
        "chart": {"close": [10.0, 10.4, 10.2]},
        "features": {"trend": 1.0},
    }


def test_registry_dedupes_similar_centroids() -> None:
    db = session_factory()
    registry = NovelPatternRegistry(similarity_threshold=0.99)
    first = _candidate("novel_long_w20_a", [0.0, 0.0, 0.0])
    second = _candidate("novel_long_w20_b", [0.001, 0.0, 0.0], score=0.9)
    second.metrics["best_expectancy_r"] = 0.2

    stored_first = registry.store_candidates(db, [first])[0]
    stored_second = registry.store_candidates(db, [second])[0]

    assert stored_first.id == stored_second.id
    assert stored_second.pattern_key == "novel_long_w20_a"
    assert stored_second.pattern_family_key.startswith("family_long_1d_w20_")
    assert stored_second.canonical_pattern_key == "novel_long_w20_a"
    assert stored_second.variant_key == "novel_long_w20_b"
    assert stored_second.variant_count == 2
    assert stored_second.drift_status == "degrading"
    assert second.metrics["registry_deduped"] is True
    assert second.metrics["registry_canonical_pattern_key"] == "novel_long_w20_a"
    assert second.metrics["registry_novelty_score"] < 0.01
    assert second.metrics["registry_family_penalty"] > 0
    assert "registry_adjusted_score" in second.metrics
    assert db.query(DiscoveredPattern).count() == 1


def test_registry_batches_candidates_without_per_candidate_flushes() -> None:
    db = session_factory()
    flush_count = 0

    @event.listens_for(db, "before_flush")
    def count_flushes(*_args: object) -> None:
        nonlocal flush_count
        flush_count += 1

    first = _candidate("batch_new_a", [0.0, 0.0, 0.0], score=0.8)
    variant = _candidate("batch_new_b", [0.001, 0.0, 0.0], score=0.9)
    distinct = _candidate("batch_new_c", [10.0, 0.0, 0.0], score=0.7)
    first.examples = [_example("AAA")]
    variant.examples = [_example("BBB")]
    distinct.examples = [_example("CCC")]

    stored = NovelPatternRegistry(similarity_threshold=0.99).store_candidates(
        db,
        [first, variant, distinct],
    )

    assert len(stored) == 3
    assert stored[0].id == stored[1].id
    assert db.query(DiscoveredPattern).count() == 2
    assert db.query(DiscoveredPatternExample).count() == 2
    assert db.query(DiscoveredPatternMetric).count() == 3
    assert db.query(AuditLog).filter(AuditLog.action == "new_pattern_discovered").count() == 2
    assert variant.metrics["registry_deduped"] is True
    assert flush_count <= 2


def test_registry_respects_store_rejected_false() -> None:
    db = session_factory()
    rejected = _candidate("batch_rejected_skip", [0.0, 0.0, 0.0])
    rejected.validation_passed = False
    rejected.metrics["promotion_status"] = "rejected"

    stored = NovelPatternRegistry(similarity_threshold=0.99).store_candidates(
        db,
        [rejected],
        store_rejected=False,
    )

    assert stored == []
    assert db.query(DiscoveredPattern).count() == 0


def test_matcher_scales_legacy_centroid_prefix() -> None:
    vector = np.asarray([1.0, 2.0, 99.0], dtype=np.float32)
    centroid = np.asarray([1.0, 2.0], dtype=float)
    mean = np.asarray([0.0, 1.0], dtype=float)
    scale = np.asarray([1.0, 2.0], dtype=float)

    scaled = NovelPatternMatcher._scaled_vector_for_pattern(vector, centroid, mean, scale)

    assert scaled is not None
    assert scaled.tolist() == [1.0, 0.5]


def test_registry_persists_confirmation_lifecycle() -> None:
    db = session_factory()
    candidate = _candidate("novel_confirm", [0.0, 0.0, 0.0])
    candidate.validation_passed = False
    candidate.metrics.update(
        {
            "promotion_status": "rejected",
            "confirmation_recommended": True,
            "confirmation_status": "needs_confirmation",
            "confirmation_priority_score": 0.72,
            "confirmation_reason": "edge strong but underpowered",
            "confirmation_next_action": "rerun expanded universe",
        }
    )

    stored = NovelPatternRegistry(similarity_threshold=0.99).store_candidates(db, [candidate])[0]

    assert stored.status == DiscoveredPatternStatus.NEEDS_CONFIRMATION
    assert stored.promotion_status == "needs_confirmation"
    assert stored.confirmation_status == "needs_confirmation"
    assert stored.confirmation_priority_score == 0.72
    assert stored.confirmation_reason == "edge strong but underpowered"


def test_registry_blocks_legacy_promotion_states() -> None:
    db = session_factory()
    candidate = _candidate("novel_legacy_paper", [0.0, 0.0, 0.0])
    candidate.metrics["promotion_status"] = "paper_candidate"

    stored = NovelPatternRegistry(similarity_threshold=0.99).store_candidates(db, [candidate])[0]

    assert stored.status == DiscoveredPatternStatus.LAB_CANDIDATE
    assert stored.promotion_status == "lab_candidate"
    assert stored.metrics_json["legacy_promotion_status_blocked"] == "paper_candidate"
    assert stored.metrics_json["runtime_promotion_blocked"] is True


def test_registry_blocks_production_promotion_state_from_discovery() -> None:
    db = session_factory()
    candidate = _candidate("novel_illegal_production", [0.0, 0.0, 0.0])
    candidate.metrics["promotion_status"] = "production"

    stored = NovelPatternRegistry(similarity_threshold=0.99).store_candidates(db, [candidate])[0]

    assert stored.status == DiscoveredPatternStatus.LAB_CANDIDATE
    assert stored.promotion_status == "lab_candidate"
    assert stored.metrics_json["legacy_promotion_status_blocked"] == "production"
    assert stored.metrics_json["runtime_promotion_blocked"] is True


def test_registry_emits_new_pattern_audit_event_with_lane_and_quality() -> None:
    db = session_factory()
    candidate = _candidate("novel_intraday_alert", [0.0, 0.0, 0.0])
    candidate.timeframe = "15m"
    candidate.metrics.update(
        {
            "reward_risk_estimate": 4.2,
            "expectancy_r": 0.51,
            "profit_factor": 2.2,
            "stability_score": 0.7,
            "out_of_sample_expectancy_r": 0.31,
        }
    )

    stored = NovelPatternRegistry(similarity_threshold=0.99).store_candidates(db, [candidate])[0]

    event = db.query(AuditLog).filter(AuditLog.action == "new_pattern_discovered").one()
    assert event.entity_type == "discovered_pattern"
    assert event.entity_id == str(stored.id)
    assert event.details_json["pattern_id"] == stored.id
    assert event.details_json["lane"] == "intraday"
    assert event.details_json["timeframe"] == "15m"
    assert event.details_json["quality"]["label"] == "alta"


def test_registry_does_not_emit_new_pattern_event_for_rejected_candidates() -> None:
    db = session_factory()
    candidate = _candidate("novel_rejected_alert", [0.0, 0.0, 0.0])
    candidate.validation_passed = False
    candidate.metrics["promotion_status"] = "rejected"

    stored = NovelPatternRegistry(similarity_threshold=0.99).store_candidates(db, [candidate])[0]

    assert stored.status == DiscoveredPatternStatus.REJECTED
    assert db.query(AuditLog).filter(AuditLog.action == "new_pattern_discovered").count() == 0
