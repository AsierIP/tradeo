from __future__ import annotations

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import DiscoveredPattern
from tradeo.db.session import Base
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.novel_pattern_registry import NovelPatternRegistry
from tradeo.research.types import ClusterCandidate


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


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

    stored_first = registry.store_candidates(db, [first])[0]
    stored_second = registry.store_candidates(db, [second])[0]

    assert stored_first.id == stored_second.id
    assert stored_second.pattern_key == "novel_long_w20_a"
    assert second.metrics["registry_deduped"] is True
    assert second.metrics["registry_canonical_pattern_key"] == "novel_long_w20_a"
    assert db.query(DiscoveredPattern).count() == 1


def test_matcher_scales_legacy_centroid_prefix() -> None:
    vector = np.asarray([1.0, 2.0, 99.0], dtype=np.float32)
    centroid = np.asarray([1.0, 2.0], dtype=float)
    mean = np.asarray([0.0, 1.0], dtype=float)
    scale = np.asarray([1.0, 2.0], dtype=float)

    scaled = NovelPatternMatcher._scaled_vector_for_pattern(vector, centroid, mean, scale)

    assert scaled is not None
    assert scaled.tolist() == [1.0, 0.5]
