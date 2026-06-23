from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.global_experiment_registry import GlobalExperimentRegistry
from tradeo.research.types import ClusterCandidate, ForwardOutcome, WindowSample
from tradeo.research.validation_gate import ValidationGate
from tradeo.research.window_sampler import WindowSampler
from tradeo.schemas import DiscoveryRunRequest
from tradeo.tests.fixtures import fixture_ohlcv


def _research_sample(
    index: int,
    *,
    vector_value: float,
    highs: list[float],
    lows: list[float],
    closes: list[float],
) -> WindowSample:
    entry = 100.0
    risk = 10.0
    end = date(2024, 1, 1) + timedelta(days=index)
    return WindowSample(
        symbol="LABT",
        timeframe="1d",
        window_size=20,
        start=(end - timedelta(days=20)).isoformat(),
        end=end.isoformat(),
        year=end.year,
        vector=np.asarray([vector_value, vector_value * 0.5], dtype=np.float32),
        chart={},
        features={},
        outcome=ForwardOutcome(
            forward_returns={5: closes[-1] / entry - 1.0},
            entry_price=entry,
            risk_proxy=risk,
            forward_end=(end + timedelta(days=len(closes))).isoformat(),
            long_mfe_r=max((max(highs) - entry) / risk, 0.0),
            long_mae_r=max((entry - min(lows)) / risk, 0.0),
            long_outcome_r=(closes[-1] - entry) / risk,
            long_hit_4r=False,
            short_mfe_r=max((entry - min(lows)) / risk, 0.0),
            short_mae_r=max((max(highs) - entry) / risk, 0.0),
            short_outcome_r=(entry - closes[-1]) / risk,
            short_hit_4r=False,
            forward_highs=highs,
            forward_lows=lows,
            forward_closes=closes,
        ),
    )


def _research_vector_sample(
    index: int,
    *,
    vector: np.ndarray,
    chart: dict | None = None,
    symbol: str | None = None,
) -> WindowSample:
    sample = _research_sample(
        index,
        vector_value=0.0,
        highs=[104.0],
        lows=[99.0],
        closes=[103.0],
    )
    sample.vector = np.asarray(vector, dtype=np.float32)
    sample.chart = chart or {}
    sample.symbol = symbol or f"LAB{index % 8}"
    return sample


def test_window_sampler_generates_forward_labeled_samples() -> None:
    df = fixture_ohlcv("LABX", bars=320)
    samples = WindowSampler().sample(
        symbol="LABX",
        df=df,
        timeframe="1d",
        window_sizes=[20, 50],
        forward_bars=[5, 10, 20],
        stride=20,
        max_windows_per_symbol=30,
    )
    assert samples
    first = samples[0]
    assert first.vector.shape[0] > 50
    assert first.outcome.risk_proxy > 0
    assert first.outcome.execution_cost_r > 0
    assert first.outcome.long_label in {"target", "stop", "timeout"}
    assert first.outcome.short_label in {"target", "stop", "timeout"}
    assert first.outcome.long_speed_label in {"fast_target", "normal_target", "slow_target", "stopped", "timeout"}
    assert first.outcome.execution["fill_probability"] > 0
    assert 20 in first.outcome.forward_returns
    assert "close_norm" in first.chart
    assert "swing_state" in first.chart
    assert "long_entry_trigger_score" in first.features
    assert "liquidity_score" in first.features
    assert "shapelet_flag_continuation_score" in first.features
    assert "swing_trend_score" in first.features
    assert "execution_fill_probability" in first.features
    assert "weekly_return" in first.features
    assert "relative_strength_spy" in first.features


def test_forward_outcome_uses_array_path_and_keeps_conservative_intrabar_order(
    monkeypatch,
) -> None:
    sampler = WindowSampler()
    future = pd.DataFrame(
        [
            {"open": 100.0, "high": 145.0, "low": 89.0, "close": 130.0, "volume": 1_000_000},
            {"open": 130.0, "high": 150.0, "low": 120.0, "close": 140.0, "volume": 1_000_000},
        ],
        index=pd.date_range("2024-01-02", periods=2, freq="D"),
    )

    def fail_dataframe_path(*_args, **_kwargs) -> None:
        raise AssertionError("_forward_outcome should use the vectorized array path")

    monkeypatch.setattr(WindowSampler, "_path_outcome", fail_dataframe_path)

    outcome = sampler._forward_outcome(
        entry=100.0,
        risk_proxy=10.0,
        future=future,
        forward_bars=[1, 2],
    )

    assert outcome.long_label == "stop"
    assert outcome.long_outcome_r == -1.0
    assert outcome.long_time_to_stop == 1
    assert outcome.long_time_to_target is None
    assert outcome.short_label == "stop"
    assert outcome.short_outcome_r == -1.0
    assert np.isclose(outcome.forward_returns[1], 0.3)


def test_window_sampler_stratifies_budget_by_window_size() -> None:
    df = fixture_ohlcv("LABW", bars=360)

    samples = WindowSampler().sample(
        symbol="LABW",
        df=df,
        timeframe="1d",
        window_sizes=[20, 50, 100, 200],
        forward_bars=[20],
        stride=5,
        max_windows_per_symbol=40,
    )

    counts = Counter(sample.window_size for sample in samples)

    assert len(samples) <= 40
    assert set(counts) == {20, 50, 100, 200}
    assert all(count <= 10 for count in counts.values())
    assert all(sample.features["sample_window_size_quota"] == 10 for sample in samples)


def test_window_sampler_accepts_generator_window_sizes_and_preserves_lineage() -> None:
    df = fixture_ohlcv("LABG", bars=180)
    df["Adjusted"] = True
    df["What To Show"] = "TRADES"
    df["Bar Complete"] = False

    samples = WindowSampler().sample(
        symbol="LABG",
        df=df,
        timeframe="1d",
        window_sizes=(size for size in [20]),
        forward_bars=(bars for bars in [5]),
        stride=20,
        max_windows_per_symbol=3,
    )

    assert samples
    assert len(samples) <= 3
    assert samples[0].features["data_adjusted"] is True
    assert samples[0].features["data_what_to_show"] == "TRADES"
    assert samples[0].features["data_bar_complete"] is False


def test_cluster_feature_summary_ignores_non_numeric_lineage() -> None:
    samples = [
        _research_vector_sample(
            index,
            vector=np.asarray([float(index), 1.0], dtype=np.float32),
        )
        for index in range(3)
    ]
    for sample in samples:
        sample.features.update(
            {
                "atr_pct": 0.05,
                "data_adjusted": True,
                "data_what_to_show": "ADJUSTED_LAST",
                "data_bar_complete": True,
            }
        )

    summary = ClusterResearchEngine._feature_summary(samples)

    assert summary["atr_pct"]["mean"] == 0.05
    assert "data_what_to_show" not in summary


def test_window_sampler_adds_benchmark_relative_strength() -> None:
    df = fixture_ohlcv("LABR", bars=180)
    spy = fixture_ohlcv("SPY", bars=180)
    sector = fixture_ohlcv("SECTOR", bars=180)
    industry = fixture_ohlcv("INDUSTRY", bars=180)
    spy["close"] = spy["close"].iloc[0]
    sector["close"] = sector["close"].iloc[0] * 0.98
    industry["close"] = industry["close"].iloc[0] * 1.02
    samples = WindowSampler().sample(
        symbol="LABR",
        df=df,
        timeframe="1d",
        window_sizes=[20],
        forward_bars=[5],
        stride=20,
        max_windows_per_symbol=5,
        benchmark_frames={"SPY": spy, "SECTOR": sector, "INDUSTRY": industry},
    )
    assert samples
    assert samples[0].features["relative_strength_spy"] != 0.0
    assert "relative_strength_sector" in samples[0].features
    assert "relative_strength_industry" in samples[0].features
    assert "market_breadth_proxy" in samples[0].features


def test_cluster_engine_returns_candidates_or_empty_without_crashing() -> None:
    df = fixture_ohlcv("LABY", bars=500)
    samples = WindowSampler().sample(
        symbol="LABY",
        df=df,
        timeframe="1d",
        window_sizes=[20],
        forward_bars=[5, 10, 20],
        stride=2,
        max_windows_per_symbol=180,
    )
    engine = ClusterResearchEngine(min_cluster_size=20, max_clusters_per_window=4)
    candidates = engine.discover(samples)
    assert isinstance(candidates, list)
    if candidates:
        candidate = candidates[0]
        assert candidate.sample_count > 0
        assert candidate.metrics["sample_count"] == candidate.sample_count
        assert candidate.side in {"long", "short"}
        assert "operational_trigger" in candidate.metrics
        assert "event_ledger_count" in candidate.metrics
        assert "cost_stress" in candidate.metrics
        assert "human_rule" in candidate.metrics
        assert "regime_profile" in candidate.metrics
        assert "novelty_score" in candidate.metrics
        assert "expected_information_gain" in candidate.metrics
        assert candidate.metrics["feature_parity_contract"]["research_lab_shared_path"] is True
        assert candidate.metrics["feature_parity_contract"]["contract_id"].startswith("tradeo.pattern_embedding")
        assert "medoid" in candidate.metrics["cluster_signature"]
        assert "similarity_distribution" in candidate.metrics["cluster_signature"]
        assert "concentration_checks" in candidate.metrics


def test_cluster_engine_hdbscan_persists_noise_and_consensus_metadata() -> None:
    rng = np.random.default_rng(123)
    samples: list[WindowSample] = []
    for i in range(56):
        if i % 14 == 0:
            vector = np.asarray([18.0 + i, -12.0], dtype=float)
        elif i % 2 == 0:
            vector = np.asarray([0.0, 0.0], dtype=float) + rng.normal(0.0, 0.03, 2)
        else:
            vector = np.asarray([5.0, 5.0], dtype=float) + rng.normal(0.0, 0.03, 2)
        samples.append(_research_vector_sample(i, vector=vector, symbol=f"DNS{i % 6}"))

    candidates = ClusterResearchEngine(
        min_cluster_size=6,
        max_clusters_per_window=4,
        out_of_sample_pct=0.1,
        rr_levels=[2.0],
        min_samples=1,
        clusterer_method="hdbscan",
        clusterer_min_samples=3,
        consensus_repeats=3,
        quant_bootstrap_draws=50,
        event_ledger_limit=0,
    ).discover(samples)

    assert candidates
    metrics = candidates[0].metrics
    assert metrics["clusterer_method"] == "hdbscan"
    assert metrics["clusterer"]["noise_count_train"] > 0
    assert metrics["density_noise"]["train_noise_count"] == metrics["clusterer"]["noise_count_train"]
    consensus = metrics["cluster_stability"]["coassignment_consensus"]
    assert consensus["method"] == "subsample_coassignment_consensus_v1"
    assert consensus["pair_observations"] > 0
    assert consensus["coassignment_rate"] is not None


def test_cluster_engine_fits_scaler_on_train_only() -> None:
    samples = [
        _research_sample(i, vector_value=0.01 * (i % 2), highs=[101.0], lows=[99.0], closes=[100.0])
        for i in range(24)
    ]
    samples.extend(
        _research_sample(24 + i, vector_value=50.0, highs=[101.0], lows=[99.0], closes=[100.0])
        for i in range(6)
    )
    candidates = ClusterResearchEngine(
        min_cluster_size=5,
        max_clusters_per_window=2,
        out_of_sample_pct=0.2,
        rr_levels=[2.0],
        min_samples=1,
    ).discover(samples)
    assert candidates
    assert candidates[0].metrics["validation_method"] == "train_fit_forward_holdout_walk_forward_embargo"
    assert candidates[0].metrics["model_fit_sample_count"] == 24
    assert candidates[0].metrics["model_holdout_sample_count"] == 6
    assert "walk_forward_folds" in candidates[0].metrics
    assert candidates[0].metrics["multiple_testing_trials"] >= 4
    assert "adjusted_p_value" in candidates[0].metrics
    assert "wrc_p_value" in candidates[0].metrics
    assert "spa_p_value" in candidates[0].metrics
    assert candidates[0].metrics["null_method"] == "stratified_regime_bootstrap"
    assert candidates[0].metrics["reality_check_method"] == "bootstrap_reality_proxy"
    assert candidates[0].metrics["reality_check_formal_test"] is False
    assert candidates[0].metrics["bootstrap_reality_proxy"]["formal_test"] is False
    assert "expectancy_ci_low" in candidates[0].metrics
    assert "deflated_sharpe_probability" in candidates[0].metrics
    assert "purged_cv_fold_count" in candidates[0].metrics
    assert "edge_decay_parameter_score" in candidates[0].metrics
    assert "overfit_score" in candidates[0].metrics
    assert "selection_split" in candidates[0].metrics
    assert candidates[0].metrics["fit_scope"]["descriptive_all_feeds_scores"] is False
    assert candidates[0].metrics["feature_parity_contract"]["research_path"].startswith("WindowSampler")
    assert candidates[0].metrics["cluster_stability"]["concentration_passed"] in {True, False}
    assert "train_metrics" in candidates[0].metrics
    assert "out_of_sample_metrics" in candidates[0].metrics
    assert "walk_forward_metrics" in candidates[0].metrics
    assert "descriptive_all_expectancy_r" in candidates[0].metrics
    assert candidates[0].metrics["descriptive_metric_policy"]["feeds_lab_priority_score"] is False
    assert candidates[0].metrics["score_input_scope"]["descriptive_all_fields_used"] is False
    mutated = dict(candidates[0].metrics)
    mutated["descriptive_all_expectancy_r"] = 999.0
    mutated["descriptive_all_profit_factor"] = 999.0
    assert ClusterResearchEngine._candidate_score(mutated) == ClusterResearchEngine._candidate_score(candidates[0].metrics)
    assert abs(float(candidates[0].metrics["scaler_mean"][0])) < 0.01


def test_cluster_signature_records_medoid_and_concentration() -> None:
    samples = [
        _research_sample(i, vector_value=0.01 * i, highs=[104.0], lows=[99.0], closes=[103.0])
        for i in range(6)
    ]
    samples[2].features.update(
        {
            "numeric_feature": 1.2345678,
            "what_to_show": "ADJUSTED_LAST",
            "nan_feature": float("nan"),
        }
    )
    vectors = np.asarray([[0.0, 0.0], [0.1, 0.0], [0.2, 0.0], [0.3, 0.0], [0.4, 0.0], [0.5, 0.0]])
    signature = ClusterResearchEngine._cluster_signature(
        samples,
        vectors,
        np.asarray([0.2, 0.0]),
        "long",
    )

    assert signature["medoid"]["window_end"] == samples[2].end
    assert signature["medoid"]["features"]["numeric_feature"] == 1.234568
    assert signature["medoid"]["features"]["what_to_show"] == "ADJUSTED_LAST"
    assert signature["medoid"]["features"]["nan_feature"] is None
    assert signature["similarity_distribution"]["p50"] > 0
    checks = signature["concentration_checks"]
    assert checks["passed"] is False
    assert checks["max_symbol_share"] == 1.0
    assert "symbol_concentration_gt_40pct" in checks["reasons"]


def test_cluster_research_persists_shape_verifier_contract() -> None:
    base_close = np.linspace(0.0, 1.0, 48)
    base_volume = np.linspace(0.2, 1.0, 48)
    samples = [
        _research_vector_sample(
            i,
            vector=np.asarray([0.0, 0.0]),
            chart={
                "close_norm": (base_close + i * 0.001).round(6).tolist(),
                "volume_rel": (base_volume + i * 0.001).round(6).tolist(),
            },
        )
        for i in range(8)
    ]

    contract = ClusterResearchEngine()._shape_match_contract(samples)

    verifier = contract["shape_verifier"]
    assert verifier["status"] == "ok"
    assert verifier["method"] == "bounded_dtw_shape_verifier_v1"
    assert verifier["distance_threshold"] > 0
    assert verifier["fit_scope"] == "train_cluster_members_only"
    assert len(verifier["prototype"]["close_norm"]) == 48
    assert len(verifier["prototype"]["volume_rel"]) == 48


def test_cluster_research_persists_matcher_prototype_contract() -> None:
    vectors = np.asarray(
        [[0.0, 0.0], [0.1, 0.0], [0.2, 0.0], [0.3, 0.0], [0.4, 0.0], [0.5, 0.0]],
        dtype=float,
    )

    contract = ClusterResearchEngine._prototype_match_contract(
        vectors,
        np.asarray([0.2, 0.0]),
        medoid_count=3,
        knn_k=2,
    )

    assert len(contract["matcher_medoids_scaled"]) == 3
    assert len(contract["matcher_diag_variance_scaled"]) == 2
    assert contract["match_knn_similarity_threshold"] > 0
    assert contract["matcher_prototype_contract"]["knn_k"] == 2


def test_cluster_research_persists_conformal_match_threshold() -> None:
    vectors = np.asarray([[float(i) / 100.0, 0.0] for i in range(25)], dtype=float)

    report = ClusterResearchEngine._match_conformal_threshold(
        vectors,
        np.asarray([0.12, 0.0]),
    )

    assert report["blocked"] is False
    assert report["similarity_threshold"] > 0
    assert report["target_recall"] == 0.9


def test_cluster_engine_does_not_select_holdout_or_unprofitable_rr() -> None:
    train = [
        _research_sample(i, vector_value=0.0, highs=[121.0], lows=[99.0], closes=[100.0])
        for i in range(20)
    ]
    holdout = [
        _research_sample(20 + i, vector_value=0.0, highs=[151.0], lows=[99.0], closes=[151.0])
        for i in range(20)
    ]
    candidates = ClusterResearchEngine(
        min_cluster_size=5,
        max_clusters_per_window=2,
        out_of_sample_pct=0.5,
        rr_levels=[2.0, 5.0],
        min_samples=1,
    ).discover(train + holdout)
    assert candidates
    candidate = max(candidates, key=lambda c: c.sample_count)
    assert candidate.metrics["best_rr"] == 0.0
    assert candidate.metrics["train_sample_count"] == 20
    assert candidate.metrics["holdout_sample_count"] == 20


def test_validation_gate_rejects_underpowered_candidate() -> None:
    df = fixture_ohlcv("LABZ", bars=320)
    samples = WindowSampler().sample(
        symbol="LABZ",
        df=df,
        timeframe="1d",
        window_sizes=[20],
        forward_bars=[5, 10, 20],
        stride=3,
        max_windows_per_symbol=90,
    )
    candidates = ClusterResearchEngine(min_cluster_size=15, max_clusters_per_window=3).discover(samples)
    if candidates:
        candidate = ValidationGate().evaluate(candidates[0])
        assert candidate.validation_reasons


def test_validation_gate_rejects_edge_below_4r() -> None:
    candidate = ClusterCandidate(
        pattern_key="x",
        name="x",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=120,
        symbol_count=10,
        year_count=3,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "best_rr": 2.5,
            "best_expectancy_r": 0.12,
            "best_profit_factor": 1.3,
            "best_max_drawdown_r": 4.0,
            "expectancy_r": 0.12,
            "profit_factor": 1.3,
            "stability_score": 0.5,
            "out_of_sample_expectancy_r": 0.05,
            "out_of_sample_profit_factor": 1.3,
            "walk_forward_fold_count": 2,
            "walk_forward_positive_fold_rate": 1.0,
            "expectancy_ci_low": 0.01,
            "overfit_score": 0.1,
            "rr_metrics": {"2.5": {"expectancy_r": 0.12, "profit_factor": 1.3, "sample_count": 120}},
        },
        feature_summary={},
        examples=[],
    )
    evaluated = ValidationGate().evaluate(candidate)
    assert not evaluated.validation_passed
    assert evaluated.metrics["promotion_status"] == "rejected"
    assert any("4" in reason for reason in evaluated.validation_reasons)


def test_validation_gate_rejects_nonfinite_core_metrics_fail_closed() -> None:
    candidate = ClusterCandidate(
        pattern_key="x",
        name="x",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=140,
        symbol_count=12,
        year_count=3,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "train_sample_count": 120,
            "best_rr": 3.0,
            "best_expectancy_r": float("nan"),
            "best_profit_factor": 2.4,
            "best_max_drawdown_r": 5.0,
            "expectancy_r": float("nan"),
            "profit_factor": 2.4,
            "stability_score": 0.62,
            "out_of_sample_expectancy_r": 0.22,
            "out_of_sample_profit_factor": 1.8,
            "expectancy_lift_r": 0.18,
            "adjusted_p_value": 0.08,
            "statistical_edge_passed": True,
            "walk_forward_fold_count": 4,
            "walk_forward_positive_fold_rate": 1.0,
            "expectancy_ci_low": 0.05,
            "overfit_score": 0.1,
            "rr_metrics": {"3": {"expectancy_r": float("nan"), "profit_factor": 2.4, "sample_count": 120}},
        },
        feature_summary={},
        examples=[],
    )

    evaluated = ValidationGate().evaluate(candidate)

    assert not evaluated.validation_passed
    assert any("metrica no finita" in reason for reason in evaluated.validation_reasons)
    assert evaluated.metrics["best_expectancy_r"] == 0.0


def test_validation_gate_rejects_high_adjusted_null_p_value() -> None:
    candidate = ClusterCandidate(
        pattern_key="x",
        name="x",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=140,
        symbol_count=12,
        year_count=3,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "train_sample_count": 110,
            "best_rr": 3.0,
            "best_expectancy_r": 0.35,
            "best_profit_factor": 2.1,
            "best_max_drawdown_r": 4.0,
            "expectancy_r": 0.35,
            "profit_factor": 2.1,
            "stability_score": 0.6,
            "out_of_sample_expectancy_r": 0.12,
            "out_of_sample_profit_factor": 1.5,
            "expectancy_lift_r": 0.04,
            "adjusted_p_value": 0.7,
            "statistical_edge_passed": False,
            "walk_forward_fold_count": 2,
            "walk_forward_positive_fold_rate": 1.0,
            "expectancy_ci_low": 0.05,
            "overfit_score": 0.1,
            "rr_metrics": {"3": {"expectancy_r": 0.35, "profit_factor": 2.1, "sample_count": 110}},
        },
        feature_summary={},
        examples=[],
    )
    evaluated = ValidationGate().evaluate(candidate)
    assert not evaluated.validation_passed
    assert any("significancia insuficiente" in reason for reason in evaluated.validation_reasons)


def test_validation_gate_rejects_failed_reality_check_and_edge_decay() -> None:
    candidate = ClusterCandidate(
        pattern_key="x",
        name="x",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=140,
        symbol_count=12,
        year_count=3,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "train_sample_count": 120,
            "best_rr": 3.0,
            "best_expectancy_r": 0.45,
            "best_profit_factor": 2.4,
            "best_max_drawdown_r": 5.0,
            "expectancy_r": 0.45,
            "profit_factor": 2.4,
            "stability_score": 0.62,
            "out_of_sample_expectancy_r": 0.22,
            "out_of_sample_profit_factor": 1.8,
            "expectancy_lift_r": 0.18,
            "adjusted_p_value": 0.08,
            "wrc_p_value": 0.7,
            "spa_p_value": 0.08,
            "statistical_edge_passed": True,
            "walk_forward_fold_count": 4,
            "walk_forward_positive_fold_rate": 1.0,
            "expectancy_ci_low": 0.05,
            "overfit_score": 0.1,
            "edge_decay_passed": False,
            "rr_metrics": {"3": {"expectancy_r": 0.45, "profit_factor": 2.4, "sample_count": 120}},
        },
        feature_summary={},
        examples=[],
    )
    evaluated = ValidationGate().evaluate(candidate)
    assert not evaluated.validation_passed
    assert any("bootstrap reality proxy WRC-like" in reason for reason in evaluated.validation_reasons)
    assert any("edge decae" in reason for reason in evaluated.validation_reasons)


def test_validation_gate_marks_strong_underpowered_edge_for_confirmation() -> None:
    candidate = ClusterCandidate(
        pattern_key="x",
        name="x",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=72,
        symbol_count=12,
        year_count=3,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "train_sample_count": 58,
            "best_rr": 3.0,
            "best_expectancy_r": 0.45,
            "best_profit_factor": 2.4,
            "best_max_drawdown_r": 5.0,
            "expectancy_r": 0.45,
            "profit_factor": 2.4,
            "stability_score": 0.62,
            "out_of_sample_expectancy_r": 0.22,
            "out_of_sample_profit_factor": 1.8,
            "expectancy_lift_r": 0.18,
            "adjusted_p_value": 0.08,
            "statistical_edge_passed": True,
            "walk_forward_fold_count": 2,
            "walk_forward_positive_fold_rate": 1.0,
            "expectancy_ci_low": 0.05,
            "overfit_score": 0.1,
            "rr_metrics": {"3": {"expectancy_r": 0.45, "profit_factor": 2.4, "sample_count": 58}},
        },
        feature_summary={},
        examples=[],
    )
    evaluated = ValidationGate().evaluate(candidate)
    assert not evaluated.validation_passed
    assert evaluated.metrics["confirmation_recommended"] is True
    assert evaluated.metrics["confirmation_priority_score"] > 0
    assert any("confirmación ampliada" in reason for reason in evaluated.validation_reasons)


def test_validation_gate_rejects_unstable_walk_forward_candidate() -> None:
    candidate = ClusterCandidate(
        pattern_key="x",
        name="x",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=140,
        symbol_count=12,
        year_count=3,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "train_sample_count": 120,
            "best_rr": 3.0,
            "best_expectancy_r": 0.45,
            "best_profit_factor": 2.4,
            "best_max_drawdown_r": 5.0,
            "expectancy_r": 0.45,
            "profit_factor": 2.4,
            "stability_score": 0.62,
            "out_of_sample_expectancy_r": 0.22,
            "out_of_sample_profit_factor": 1.8,
            "expectancy_lift_r": 0.18,
            "adjusted_p_value": 0.08,
            "statistical_edge_passed": True,
            "walk_forward_fold_count": 4,
            "walk_forward_positive_fold_rate": 0.25,
            "expectancy_ci_low": 0.05,
            "overfit_score": 0.1,
            "rr_metrics": {"3": {"expectancy_r": 0.45, "profit_factor": 2.4, "sample_count": 120}},
        },
        feature_summary={},
        examples=[],
    )
    evaluated = ValidationGate().evaluate(candidate)
    assert not evaluated.validation_passed
    assert any("walk-forward inestable" in reason for reason in evaluated.validation_reasons)


def test_validation_gate_rejects_high_overfit_score() -> None:
    candidate = ClusterCandidate(
        pattern_key="x",
        name="x",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=140,
        symbol_count=12,
        year_count=3,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "train_sample_count": 120,
            "best_rr": 3.0,
            "best_expectancy_r": 0.45,
            "best_profit_factor": 2.4,
            "best_max_drawdown_r": 5.0,
            "expectancy_r": 0.45,
            "profit_factor": 2.4,
            "stability_score": 0.62,
            "out_of_sample_expectancy_r": 0.22,
            "out_of_sample_profit_factor": 1.8,
            "expectancy_lift_r": 0.18,
            "adjusted_p_value": 0.08,
            "statistical_edge_passed": True,
            "walk_forward_fold_count": 4,
            "walk_forward_positive_fold_rate": 1.0,
            "expectancy_ci_low": 0.05,
            "overfit_score": 0.9,
            "rr_metrics": {"3": {"expectancy_r": 0.45, "profit_factor": 2.4, "sample_count": 120}},
        },
        feature_summary={},
        examples=[],
    )
    evaluated = ValidationGate().evaluate(candidate)
    assert not evaluated.validation_passed
    assert any("overfit alto" in reason for reason in evaluated.validation_reasons)


def test_validation_gate_rejects_failed_cost_stress() -> None:
    candidate = ClusterCandidate(
        pattern_key="x",
        name="x",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=140,
        symbol_count=12,
        year_count=3,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "train_sample_count": 120,
            "best_rr": 3.0,
            "best_expectancy_r": 0.45,
            "best_profit_factor": 2.4,
            "best_max_drawdown_r": 5.0,
            "expectancy_r": 0.45,
            "profit_factor": 2.4,
            "stability_score": 0.62,
            "out_of_sample_expectancy_r": 0.22,
            "out_of_sample_profit_factor": 1.8,
            "expectancy_lift_r": 0.18,
            "adjusted_p_value": 0.08,
            "statistical_edge_passed": True,
            "walk_forward_fold_count": 4,
            "walk_forward_positive_fold_rate": 1.0,
            "expectancy_ci_low": 0.05,
            "overfit_score": 0.1,
            "cost_stress_passed": False,
            "rr_metrics": {"3": {"expectancy_r": 0.45, "profit_factor": 2.4, "sample_count": 120}},
        },
        feature_summary={},
        examples=[],
    )
    evaluated = ValidationGate().evaluate(candidate)
    assert not evaluated.validation_passed
    assert any("coste x2" in reason for reason in evaluated.validation_reasons)


def test_lab_agent_persists_compressed_event_ledger(tmp_path: Path) -> None:
    candidate = ClusterCandidate(
        pattern_key="family/unsafe pattern",
        name="auditable",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=2,
        symbol_count=1,
        year_count=1,
        score=0.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "event_ledger": [
                {"symbol": "AAA", "window_end": "2024-01-01", "result_r": 1.2},
                {"symbol": "BBB", "window_end": "2024-01-02", "result_r": -1.0},
            ],
        },
        feature_summary={},
        examples=[],
    )
    agent = PatternDiscoveryLabAgent(provider=object(), settings=Settings(reports_dir=str(tmp_path)))

    assert agent._write_event_ledgers(42, [candidate]) == 1

    path = Path(str(candidate.metrics["event_ledger_path"]))
    raw = gzip.decompress(path.read_bytes())
    payload = json.loads(raw)
    assert path.name == "family_unsafe_pattern.json.gz"
    assert payload["event_count"] == 2
    assert payload["events"][0]["symbol"] == "AAA"
    assert candidate.metrics["event_ledger_sha256"] == hashlib.sha256(raw).hexdigest()
    assert candidate.metrics["event_ledger_persisted"] is True
    assert "event_ledger" not in candidate.metrics
    assert len(candidate.metrics["event_ledger_preview"]) == 2


def test_lab_agent_routes_research_universe_by_timeframe(tmp_path: Path) -> None:
    midcaps = tmp_path / "midcaps.csv"
    smallcaps = tmp_path / "smallcaps.csv"
    midcaps.write_text("symbol\nMID1\nMID2\n", encoding="utf-8")
    smallcaps.write_text("symbol\nSML1\nSML2\n", encoding="utf-8")
    settings = Settings(
        daily_universe_file=str(midcaps),
        intraday_universe_file=str(smallcaps),
        reports_dir=str(tmp_path / "reports"),
        universe_snapshot_monthly=False,
    )
    agent = PatternDiscoveryLabAgent(provider=object(), settings=settings)

    daily_request = DiscoveryRunRequest(limit=2, interval="1d")
    daily_params = agent._resolve_params(daily_request)
    assert daily_params["universe_scope"] == "daily_midcap"
    assert agent._resolve_symbols(daily_request, daily_params) == ["MID1", "MID2"]

    intraday_request = DiscoveryRunRequest(limit=2, interval="5m")
    intraday_params = agent._resolve_params(intraday_request)
    assert intraday_params["universe_scope"] == "intraday_smallcap"
    assert agent._resolve_symbols(intraday_request, intraday_params) == ["SML1", "SML2"]


def test_global_experiment_registry_does_not_recount_repeated_experiments(tmp_path: Path) -> None:
    candidate = ClusterCandidate(
        pattern_key="pattern-a",
        name="pattern-a",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=10,
        symbol_count=3,
        year_count=2,
        score=0.8,
        validation_passed=True,
        validation_reasons=[],
        metrics={"real_variant_count": 12, "fit_scope": {"scaler": "train_only"}},
        feature_summary={},
        examples=[],
    )
    registry = GlobalExperimentRegistry(tmp_path / "global_experiment_registry.json")

    first = registry.register([candidate], run_id=1, params={"interval": "1d"})
    duplicate = registry.register([candidate], run_id=1, params={"interval": "1d"})
    second = registry.register([candidate], run_id=2, params={"interval": "1d"})
    payload = registry.load()

    assert first["global_trial_count"] == 12
    assert duplicate["global_trial_count"] == 12
    assert duplicate["repeated_experiments"] == 1
    assert second["global_trial_count"] == 12
    assert second["repeated_experiments"] == 1
    assert len(payload["experiments"]) == 1
    assert payload["experiments"][0]["replication_count"] == 3
    assert candidate.metrics["global_experiment_registry"]["edge_claim"] == "NO_DEMOSTRADO"
    assert candidate.metrics["global_experiment_registry"]["global_trial_count_increased"] is False
    assert candidate.metrics["global_experiment_registry"]["is_repeated_experiment"] is True
    assert candidate.metrics["global_experiment_registry"]["replication_count"] == 3


def test_global_experiment_registry_hash_chain_atomic_write_and_backup(tmp_path: Path) -> None:
    first_candidate = ClusterCandidate(
        pattern_key="pattern-a",
        name="pattern-a",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[],
        sample_count=10,
        symbol_count=3,
        year_count=2,
        score=0.8,
        validation_passed=True,
        validation_reasons=[],
        metrics={"real_variant_count": 2, "fit_scope": {"scaler": "train_only"}},
        feature_summary={},
        examples=[],
    )
    second_candidate = ClusterCandidate(
        pattern_key="pattern-b",
        name="pattern-b",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=2,
        centroid=[],
        sample_count=12,
        symbol_count=4,
        year_count=2,
        score=0.9,
        validation_passed=True,
        validation_reasons=[],
        metrics={"real_variant_count": 3, "fit_scope": {"scaler": "train_only"}},
        feature_summary={},
        examples=[],
    )
    registry = GlobalExperimentRegistry(tmp_path / "global_experiment_registry.json")

    first = registry.register([first_candidate], run_id=1, params={"interval": "1d"})
    first_payload = registry.load()
    second = registry.register([second_candidate], run_id=2, params={"interval": "1d"})
    second_payload = registry.load()

    assert first_payload["registry_hash"] == first["registry_hash"]
    assert second_payload["latest_run_manifest"]["previous_registry_hash"] == first["registry_hash"]
    assert second_payload["latest_run_manifest"]["run_manifest_hash"] == second["run_manifest_hash"]
    assert second_payload["registry_hash"] == registry.registry_hash(second_payload)
    assert second_candidate.metrics["global_experiment_registry"]["registry_hash"] == second["registry_hash"]
    assert list((tmp_path / ".backups").glob("global_experiment_registry.json.*.bak"))
    assert list(tmp_path.glob(".global_experiment_registry.json.*.tmp")) == []
