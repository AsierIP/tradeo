"""Audit §3.1.1-4: kNN/Mahalanobis conformal matcher gate + ambiguity teeth.

Covers the report's priority test `test_conformal_threshold_coverage`, the
prototype-bank persistence contract (§2.3.4), the matcher gate behavior with
and without a bank, and the entry-scanner ambiguity escalation (§3.1.4).
"""

from __future__ import annotations

import numpy as np

from tradeo.core.config import Settings
from tradeo.db.models import DiscoveredPattern, DiscoveredPatternStatus
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.prototype_bank import (
    build_prototype_bank,
    conformal_tau,
    knn_distance,
    mahalanobis_diag_distance,
    parse_prototype_bank,
)
from tradeo.tests.test_discovery_determinism import _engine, _make_samples


def test_conformal_threshold_coverage() -> None:
    """tau = conformal quantile must cover >= 1 - alpha of exchangeable members."""
    rng = np.random.default_rng(11)
    alpha = 0.10
    coverages: list[float] = []
    for _ in range(200):
        cal = rng.lognormal(mean=0.0, sigma=0.6, size=40)
        new_members = rng.lognormal(mean=0.0, sigma=0.6, size=400)
        tau = conformal_tau(cal, alpha=alpha)
        coverages.append(float(np.mean(new_members <= tau)))
    # Finite-sample guarantee holds in expectation over splits.
    assert float(np.mean(coverages)) >= 1.0 - alpha - 0.02


def test_conformal_tau_small_sample_is_conservative() -> None:
    cal = np.asarray([0.2, 0.5, 0.3])
    # k = ceil(4 * 0.9) = 4 > n -> clamps to the max calibration distance.
    assert conformal_tau(cal, alpha=0.10) == 0.5


def test_prototype_bank_build_is_deterministic_and_disjoint() -> None:
    rng = np.random.default_rng(3)
    members = rng.normal(0.0, 1.0, size=(60, 8))
    bank_a = build_prototype_bank(members, seed=99)
    bank_b = build_prototype_bank(members, seed=99)
    assert bank_a == bank_b
    assert bank_a is not None
    assert bank_a["medoid_count"] <= 16
    assert bank_a["calibration_count"] + bank_a["prototype_count"] == len(members)
    assert bank_a["tau_knn_distance"] > 0.0
    assert bank_a["tau_maha_distance"] > 0.0
    parsed = parse_prototype_bank({"prototype_bank": bank_a})
    assert parsed is not None
    assert parsed.dimension == 8


def test_prototype_bank_too_small_returns_none() -> None:
    rng = np.random.default_rng(4)
    assert build_prototype_bank(rng.normal(size=(5, 4)), seed=1) is None


def test_prototype_bank_members_pass_their_own_gate_at_conformal_rate() -> None:
    """>= ~90% of held-out true members must pass the persisted gate (alpha=0.10)."""
    rng = np.random.default_rng(7)
    cluster = rng.normal(0.0, 1.0, size=(160, 6))
    bank_dict = build_prototype_bank(cluster[:120], alpha=0.10, seed=21)
    assert bank_dict is not None
    bank = parse_prototype_bank({"prototype_bank": bank_dict})
    assert bank is not None
    fresh = cluster[120:]
    passed = sum(
        1
        for vector in fresh
        if knn_distance(vector, bank.medoids, bank.knn_k) <= bank.tau_knn_distance
        and mahalanobis_diag_distance(vector, bank.maha_center, bank.maha_var)
        <= bank.tau_maha_distance
    )
    # Two simultaneous conformal axes; each guarantees 90%, the AND is looser.
    assert passed / len(fresh) >= 0.75


def test_engine_persists_prototype_bank() -> None:
    candidates = _engine().discover(_make_samples())
    assert candidates
    banked = [c for c in candidates if "prototype_bank" in c.metrics]
    assert banked, "expected at least one cluster large enough for a prototype bank"
    bank = banked[0].metrics["prototype_bank"]
    assert bank["method"] == "knn_medoids_mahalanobis_diag_split_conformal"
    assert bank["medoid_count"] >= 1
    assert bank["calibration_count"] >= 2
    assert parse_prototype_bank({"prototype_bank": bank}) is not None
    # The bank dimension must match the persisted centroid prefix.
    assert len(bank["maha_center"]) == len(banked[0].centroid)


def _pattern(metrics: dict, dim: int = 6) -> DiscoveredPattern:
    return DiscoveredPattern(
        pattern_key="conformal_key",
        name="conformal_pattern",
        status=DiscoveredPatternStatus.LAB_CANDIDATE,
        side="long",
        timeframe="1d",
        window_size=20,
        sample_count=100,
        symbol_count=10,
        year_count=3,
        score=0.9,
        stability_score=0.8,
        best_rr=4.0,
        validation_passed=True,
        promotion_status="lab_candidate",
        centroid_json=[0.0] * dim,
        metrics_json={
            "scaler_mean": [0.0] * dim,
            "scaler_scale": [1.0] * dim,
            **metrics,
        },
    )


def _tight_bank(dim: int = 6) -> dict:
    # Cluster hugs zero; dimension 0 is very tight (var 1e-4), rest are loose.
    var = [1e-4] + [1.0] * (dim - 1)
    return {
        "method": "knn_medoids_mahalanobis_diag_split_conformal",
        "knn_k": 3,
        "alpha": 0.10,
        "calibration_fraction": 0.25,
        "calibration_count": 10,
        "prototype_count": 30,
        "medoid_count": 4,
        "split_seed": 1,
        "medoids": [[0.0] * dim, [0.01] * dim, [-0.01] * dim, [0.005] * dim],
        "maha_center": [0.0] * dim,
        "maha_var": var,
        "maha_eps": 1e-4,
        "tau_knn_distance": 0.25,
        "tau_maha_distance": 2.0,
    }


def _matcher(**overrides) -> NovelPatternMatcher:
    settings = Settings(**overrides)

    class NoProvider:
        def fetch_ohlcv(self, *args, **kwargs):
            raise AssertionError("no data needed")

    return NovelPatternMatcher(provider=NoProvider(), settings=settings)


def test_matcher_conformal_gate_blocks_out_of_cloud_vector() -> None:
    """Mahalanobis catches a vector the legacy centroid similarity accepts."""
    matcher = _matcher()
    pattern = _pattern({"prototype_bank": _tight_bank(), "match_tau_similarity": 0.5})
    dim = 6
    in_cloud = np.zeros(dim)
    # Far only along the tight dimension: tiny L2 distance, huge Mahalanobis.
    out_of_cloud = np.zeros(dim)
    out_of_cloud[0] = 0.5

    def diagnostic(vector: np.ndarray) -> dict:
        cached = (None, vector, {}, {})
        result = matcher._similarity_diagnostic(pattern, cached, 0.45)
        assert result is not None
        return result

    accepted = diagnostic(in_cloud)
    assert accepted["passed_threshold"] is True
    assert accepted["conformal_gate"]["passed"] is True
    assert accepted["centroid_similarity_role"] == "diagnostic_only"

    rejected = diagnostic(out_of_cloud)
    # Legacy similarity barely moves (0.5 / sqrt(6) ~ 0.2 distance)...
    assert rejected["similarity"] > 0.8
    # ...but the diagonal Mahalanobis axis blocks it.
    assert rejected["conformal_gate"]["maha_passed"] is False
    assert rejected["passed_threshold"] is False


def test_matcher_conformal_gate_keeps_global_floor() -> None:
    matcher = _matcher(discovery_match_similarity_threshold=0.99)
    pattern = _pattern({"prototype_bank": _tight_bank()})
    diagnostic = matcher._similarity_diagnostic(pattern, (None, np.full(6, 0.9), {}, {}), 0.99)
    assert diagnostic is not None
    assert diagnostic["similarity"] < 0.99
    assert diagnostic["passed_threshold"] is False


def test_matcher_without_bank_uses_legacy_threshold() -> None:
    matcher = _matcher()
    pattern = _pattern({"match_tau_similarity": 0.9})
    diagnostic = matcher._similarity_diagnostic(pattern, (None, np.full(6, 0.5), {}, {}), 0.45)
    assert diagnostic is not None
    assert "conformal_gate" not in diagnostic
    assert diagnostic["similarity_threshold_used"] == 0.9


def test_matcher_conformal_gate_flag_off_restores_legacy() -> None:
    matcher = _matcher(discovery_match_conformal_gate_enabled=False)
    pattern = _pattern({"prototype_bank": _tight_bank(), "match_tau_similarity": 0.5})
    vector = np.zeros(6)
    vector[0] = 0.5
    diagnostic = matcher._similarity_diagnostic(pattern, (None, vector, {}, {}), 0.45)
    assert diagnostic is not None
    assert "conformal_gate" not in diagnostic
    assert diagnostic["passed_threshold"] is True


def test_matcher_ignores_bank_with_wrong_dimension() -> None:
    matcher = _matcher()
    bank = _tight_bank(dim=4)
    pattern = _pattern({"prototype_bank": bank, "match_tau_similarity": 0.5})
    diagnostic = matcher._similarity_diagnostic(pattern, (None, np.zeros(6), {}, {}), 0.45)
    assert diagnostic is not None
    assert "conformal_gate" not in diagnostic
