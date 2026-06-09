from __future__ import annotations

from datetime import date, timedelta

import numpy as np

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
    assert 20 in first.outcome.forward_returns
    assert "close_norm" in first.chart


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
    assert candidates[0].metrics["validation_method"] == "train_fit_forward_holdout"
    assert candidates[0].metrics["model_fit_sample_count"] == 24
    assert candidates[0].metrics["model_holdout_sample_count"] == 6
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
            "rr_metrics": {"2.5": {"expectancy_r": 0.12, "profit_factor": 1.3, "sample_count": 120}},
        },
        feature_summary={},
        examples=[],
    )
    evaluated = ValidationGate().evaluate(candidate)
    assert evaluated.validation_passed
    assert evaluated.metrics["promotion_status"] == "lab_watchlist"
