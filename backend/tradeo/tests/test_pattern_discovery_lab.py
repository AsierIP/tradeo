from __future__ import annotations

import gzip
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.types import ClusterCandidate, ForwardOutcome, WindowSample
from tradeo.research.validation_gate import ValidationGate
from tradeo.research.window_sampler import WindowSampler
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
    assert "expectancy_ci_low" in candidates[0].metrics
    assert "deflated_sharpe_probability" in candidates[0].metrics
    assert "purged_cv_fold_count" in candidates[0].metrics
    assert "edge_decay_parameter_score" in candidates[0].metrics
    assert "overfit_score" in candidates[0].metrics
    assert abs(float(candidates[0].metrics["scaler_mean"][0])) < 0.01


def test_cluster_engine_selects_best_rr_from_train_only() -> None:
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
    assert candidate.metrics["best_rr"] == 2.0
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


def test_validation_gate_allows_edge_below_4r_as_watchlist() -> None:
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
    assert evaluated.validation_passed
    assert evaluated.metrics["promotion_status"] == "lab_watchlist"


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
    assert any("White Reality Check" in reason for reason in evaluated.validation_reasons)
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
