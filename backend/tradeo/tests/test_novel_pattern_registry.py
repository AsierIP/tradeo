from __future__ import annotations

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import DiscoveredPattern, DiscoveredPatternStatus
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
