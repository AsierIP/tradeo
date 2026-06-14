"""False-match harness (§3.1.5) + temporal weighting (§2.2.a) coverage."""

from __future__ import annotations

import numpy as np
import pytest

from tradeo.core.config import Settings
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.false_match_harness import FalseMatchHarness
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.research.shape_verifier import bounded_dtw_distance, shape_distance
from tradeo.research.types import ForwardOutcome, WindowSample

DIM = 24


def _cloud(center: np.ndarray, n: int, spread: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return center + rng.normal(0.0, spread, size=(n, len(center)))


def test_false_match_harness_regression() -> None:
    """Separated negatives -> FPR 0; overlapping negatives -> FPR rises.

    This is the regression contract: a matcher change that degrades separation
    must show up as a worse fpr_at_recall on the same banks.
    """
    centroid = np.zeros(DIM)
    positives = _cloud(centroid, 200, 0.3, seed=1)
    far_negatives = _cloud(centroid + 5.0, 300, 0.3, seed=2)
    harness = FalseMatchHarness()
    clean = harness.evaluate(
        positives=positives,
        centroid=centroid,
        negative_banks={"other_cluster_members": far_negatives},
        tau_similarity=0.5,
    )
    assert clean["status"] == "ok"
    assert clean["fpr_at_recall"] == 0.0
    assert clean["recall_at_tau"] >= 0.85
    assert clean["sources"]["other_cluster_members"]["count"] == 300

    overlapping = _cloud(centroid + 0.05, 300, 0.3, seed=3)
    dirty = harness.evaluate(
        positives=positives,
        centroid=centroid,
        negative_banks={"other_cluster_members": overlapping},
    )
    assert dirty["fpr_at_recall"] > clean["fpr_at_recall"]
    assert dirty["fpr_at_recall"] > 0.5


def test_false_match_harness_edge_cases() -> None:
    harness = FalseMatchHarness()
    centroid = np.zeros(DIM)
    too_few = harness.evaluate(
        positives=np.zeros((3, DIM)),
        centroid=centroid,
        negative_banks={"other_cluster_members": np.ones((10, DIM))},
    )
    assert too_few["status"] == "insufficient_positives"
    assert too_few["fpr_at_recall"] is None

    no_negatives = harness.evaluate(
        positives=_cloud(centroid, 50, 0.3, seed=4),
        centroid=centroid,
        negative_banks={"shadow_occurrences": np.empty((0, DIM))},
    )
    assert no_negatives["status"] == "no_negatives"
    assert no_negatives["fpr_at_recall"] is None


def test_harness_similarity_matches_matcher_formula() -> None:
    """Unweighted harness similarities must be bit-compatible with the matcher."""
    rng = np.random.default_rng(7)
    centroid = rng.normal(size=DIM)
    vectors = rng.normal(size=(5, DIM))
    sims = FalseMatchHarness._similarities(vectors, centroid)
    for row, sim in zip(vectors, sims):
        distance = float(np.linalg.norm(row - centroid) / max(1.0, np.sqrt(DIM)))
        assert sim == pytest.approx(1.0 / (1.0 + distance))


def test_temporal_weights_layout() -> None:
    engine = PatternEmbeddingEngine()
    ppc = engine.points_per_channel
    legacy_prefix = engine.LEGACY_CHANNEL_COUNT * ppc + engine.LEGACY_SCALAR_COUNT
    weights = engine.temporal_weights(legacy_prefix, gamma=0.97)
    assert len(weights) == legacy_prefix
    # Each channel block ramps from gamma^(ppc-1) up to 1.0 at the last bar.
    first_block = weights[:ppc]
    assert first_block[-1] == pytest.approx(1.0)
    assert first_block[0] == pytest.approx(0.97 ** (ppc - 1))
    assert np.all(np.diff(first_block) > 0)
    # Scalar features carry no bar position: weight 1.0.
    scalars = weights[engine.LEGACY_CHANNEL_COUNT * ppc :]
    assert np.all(scalars == 1.0)
    # Truncation to a stored centroid prefix keeps the same leading weights.
    short = engine.temporal_weights(ppc + 5, gamma=0.97)
    assert np.allclose(short, weights[: ppc + 5])
    with pytest.raises(ValueError):
        engine.temporal_weights(10, gamma=1.5)


def test_temporal_weighting_downweights_early_window_differences() -> None:
    """Same-size difference hurts less at the start of the window than at the end."""
    engine = PatternEmbeddingEngine()
    ppc = engine.points_per_channel
    centroid = np.zeros(ppc)
    early_diff = np.zeros((1, ppc))
    early_diff[0, 0] = 1.0
    late_diff = np.zeros((1, ppc))
    late_diff[0, -1] = 1.0
    weights = engine.temporal_weights(ppc, gamma=0.97)
    sim_early = FalseMatchHarness._similarities(early_diff, centroid, weights)[0]
    sim_late = FalseMatchHarness._similarities(late_diff, centroid, weights)[0]
    assert sim_early > sim_late
    # Unweighted, both differences are indistinguishable.
    sim_early_uw = FalseMatchHarness._similarities(early_diff, centroid)[0]
    sim_late_uw = FalseMatchHarness._similarities(late_diff, centroid)[0]
    assert sim_early_uw == pytest.approx(sim_late_uw)


def test_bounded_dtw_shape_distance_handles_small_phase_shift() -> None:
    base = np.vstack(
        [
            np.r_[np.linspace(0.0, 1.0, 12), np.linspace(1.0, 0.4, 12)],
            np.r_[np.zeros(8), np.linspace(0.0, 1.0, 16)],
        ]
    )
    shifted = np.roll(base, 2, axis=1)
    euclidean = float(np.linalg.norm(base - shifted) / np.sqrt(base.size))
    dtw = bounded_dtw_distance(base, shifted, band=4)
    soft = shape_distance(base, shifted, method="soft_dtw", band=4, gamma=0.05)

    assert dtw < euclidean
    assert soft >= 0.0


def _sample(symbol: str, vector: np.ndarray, end: str = "2024-01-31") -> WindowSample:
    outcome = ForwardOutcome(
        forward_returns={5: 0.0},
        entry_price=100.0,
        risk_proxy=1.0,
        forward_end="2024-02-10",
        long_mfe_r=0.0,
        long_mae_r=0.0,
        long_outcome_r=0.0,
        long_hit_4r=False,
        short_mfe_r=0.0,
        short_mae_r=0.0,
        short_outcome_r=0.0,
        short_hit_4r=False,
    )
    return WindowSample(
        symbol=symbol,
        timeframe="1d",
        window_size=20,
        start="2024-01-01",
        end=end,
        year=2024,
        vector=vector,
        outcome=outcome,
        chart={},
        features={},
    )


def test_cluster_engine_false_match_metrics_banks_are_disjoint() -> None:
    """Banks split by symbol membership and the temporal variant is published."""
    centroid = np.zeros(DIM)
    cluster_vectors = _cloud(centroid, 30, 0.2, seed=10)
    same_symbol_neg = _cloud(centroid + 4.0, 20, 0.2, seed=11)
    other_neg = _cloud(centroid - 4.0, 25, 0.2, seed=12)
    matrix = np.vstack([cluster_vectors, same_symbol_neg, other_neg])
    labels = np.array([0] * 30 + [1] * 20 + [2] * 25)
    samples = (
        [_sample("AAA", row) for row in cluster_vectors]
        + [_sample("AAA", row) for row in same_symbol_neg]
        + [_sample("BBB", row) for row in other_neg]
    )
    engine = ClusterResearchEngine()
    result = engine._false_match_metrics(
        cluster_id=0,
        all_labels=labels,
        ordered_samples=samples,
        matrix_all_scaled=matrix,
        cluster_samples=samples[:30],
        cluster_vectors=cluster_vectors,
        centroid_scaled=centroid,
        tau_similarity=0.5,
    )
    unweighted = result["unweighted"]
    assert unweighted["status"] == "ok"
    assert unweighted["sources"]["same_symbol_outside_cluster"]["count"] == 20
    assert unweighted["sources"]["other_cluster_members"]["count"] == 25
    assert unweighted["sources"]["shadow_occurrences"]["count"] == 0
    assert unweighted["fpr_at_recall"] == 0.0
    temporal = result["temporal"]
    assert temporal["temporal_weighting_applied"] is True
    assert temporal["status"] == "ok"
    assert 0.0 < result["tau_similarity_temporal"] <= 1.0
    meta = result["temporal_weighting"]
    assert meta["gamma"] == pytest.approx(0.97)
    assert meta["matcher_scaling"].endswith("temporal_gamma_0.97")
    assert meta["adopted_in_matcher"] is False


class _PatternStub:
    side = "long"

    def __init__(self, metrics: dict, centroid: list[float]) -> None:
        self.metrics_json = metrics
        self.centroid_json = centroid


def _matcher(tmp_path, **overrides) -> NovelPatternMatcher:
    settings = Settings(
        reports_dir=str(tmp_path / "reports"),
        artifacts_dir=str(tmp_path / "artifacts"),
        **overrides,
    )
    return NovelPatternMatcher(provider=object(), settings=settings)


def test_matcher_temporal_weighting_gated_by_flag_and_pattern_metrics(tmp_path) -> None:
    engine = PatternEmbeddingEngine()
    ppc = engine.points_per_channel
    centroid = [0.0] * ppc
    metrics_with_temporal = {
        "scaler_mean": [0.0] * ppc,
        "scaler_scale": [1.0] * ppc,
        "match_tau_similarity": 0.6,
        "match_tau_similarity_temporal": 0.7,
        "temporal_weighting": {"gamma": 0.97},
    }
    vector = np.zeros(ppc, dtype=float)
    vector[0] = 2.0  # early-window difference: down-weighted by the ramp
    cached = (None, vector, {}, {})

    # Flag off -> unweighted path, unweighted tau.
    off = _matcher(tmp_path, discovery_match_temporal_weighting_enabled=False)
    diag_off = off._similarity_diagnostic(
        _PatternStub(dict(metrics_with_temporal), centroid), cached, 0.45
    )
    assert diag_off["temporal_weighting"]["enabled"] is False
    assert diag_off["similarity_threshold_used"] == pytest.approx(0.6)

    # Flag on + pattern persisted weighted tau -> weighted distance and tau.
    on = _matcher(tmp_path, discovery_match_temporal_weighting_enabled=True)
    diag_on = on._similarity_diagnostic(
        _PatternStub(dict(metrics_with_temporal), centroid), cached, 0.45
    )
    assert diag_on["temporal_weighting"]["enabled"] is True
    assert diag_on["temporal_weighting"]["gamma"] == pytest.approx(0.97)
    assert diag_on["similarity_threshold_used"] == pytest.approx(0.7)
    assert diag_on["similarity"] > diag_off["similarity"]

    # Flag on but pattern lacks the weighted tau -> falls back to unweighted.
    no_temporal_metrics = {
        "scaler_mean": [0.0] * ppc,
        "scaler_scale": [1.0] * ppc,
        "match_tau_similarity": 0.6,
    }
    diag_fallback = on._similarity_diagnostic(
        _PatternStub(no_temporal_metrics, centroid), cached, 0.45
    )
    assert diag_fallback["temporal_weighting"]["enabled"] is False
    assert diag_fallback["similarity"] == pytest.approx(diag_off["similarity"])


def test_matcher_shape_dtw_is_diagnostic_until_hard_gate_enabled(tmp_path) -> None:
    centroid = [0.0, 0.0]
    prototype = {
        "close_norm": [0.0] * 48,
        "volume_rel": [0.0] * 48,
    }
    metrics = {
        "scaler_mean": [0.0, 0.0],
        "scaler_scale": [1.0, 1.0],
        "match_tau_similarity": 0.45,
        "shape_verifier": {
            "status": "ok",
            "method": "bounded_dtw_shape_verifier_v1",
            "channels": ["close_norm", "volume_rel"],
            "points_per_channel": 48,
            "distance": "dtw",
            "band": 8,
            "distance_threshold": 0.01,
            "prototype": prototype,
        },
    }
    bad_chart = {
        "close_norm": [1.0] * 48,
        "volume_rel": [0.0] * 48,
    }
    cached = (None, np.zeros(2, dtype=float), {}, bad_chart)

    diagnostic_only = _matcher(
        tmp_path,
        discovery_match_shape_dtw_enabled=True,
        discovery_match_shape_dtw_hard_gate_enabled=False,
    )._similarity_diagnostic(_PatternStub(dict(metrics), centroid), cached, 0.45)
    assert diagnostic_only["shape_verifier"]["passed"] is False
    assert diagnostic_only["shape_verifier"]["hard_gate_applied"] is False
    assert diagnostic_only["passed_threshold"] is True

    hard_gate = _matcher(
        tmp_path,
        discovery_match_shape_dtw_enabled=True,
        discovery_match_shape_dtw_hard_gate_enabled=True,
    )._similarity_diagnostic(_PatternStub(dict(metrics), centroid), cached, 0.45)
    assert hard_gate["shape_verifier"]["hard_gate_applied"] is True
    assert hard_gate["passed_threshold"] is False


def test_matcher_shape_dtw_hard_gate_requires_research_contract(tmp_path) -> None:
    metrics = {
        "scaler_mean": [0.0, 0.0],
        "scaler_scale": [1.0, 1.0],
        "match_tau_similarity": 0.45,
    }
    cached = (
        None,
        np.zeros(2, dtype=float),
        {},
        {"close_norm": [1.0] * 48, "volume_rel": [0.0] * 48},
    )

    diag = _matcher(
        tmp_path,
        discovery_match_shape_dtw_enabled=True,
        discovery_match_shape_dtw_hard_gate_enabled=True,
    )._similarity_diagnostic(_PatternStub(metrics, [0.0, 0.0]), cached, 0.45)

    assert diag["shape_verifier"]["status"] == "missing_research_contract"
    assert diag["shape_verifier"]["hard_gate_applied"] is False
    assert diag["passed_threshold"] is True


def test_contract_matcher_scaling_bumps_with_gamma() -> None:
    engine = PatternEmbeddingEngine()
    base = engine.contract()
    assert base["matcher_scaling"] == "train_fit_standard_scaler_prefix"
    bumped = engine.contract(temporal_gamma=0.97)
    assert bumped["matcher_scaling"] == "train_fit_standard_scaler_prefix+temporal_gamma_0.97"
    assert bumped["contract_id"] == base["contract_id"]
