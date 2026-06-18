from __future__ import annotations

import numpy as np

from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.reward_risk_analyzer import RewardRiskAnalyzer
from tradeo.research.types import ForwardOutcome, WindowSample


def _sample(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    cost_r: float = 0.0,
    opens: list[float] | None = None,
) -> WindowSample:
    return WindowSample(
        symbol="TST",
        timeframe="1d",
        window_size=20,
        start="2024-01-01",
        end="2024-01-20",
        year=2024,
        vector=np.zeros(64),
        chart={},
        features={},
        outcome=ForwardOutcome(
            forward_returns={5: 0.0},
            entry_price=100.0,
            risk_proxy=10.0,
            forward_end="2024-01-25",
            long_mfe_r=max(highs) / 100.0,
            long_mae_r=1.0,
            long_outcome_r=0.0,
            long_hit_4r=False,
            short_mfe_r=0.0,
            short_mae_r=0.0,
            short_outcome_r=0.0,
            short_hit_4r=False,
            forward_highs=highs,
            forward_lows=lows,
            forward_closes=closes,
            forward_opens=opens or [100.0 for _ in closes],
            execution_cost_r=cost_r,
            long_gap_adverse_r=0.2,
            long_mfe_before_mae=True,
            execution={"fill_probability": 0.8, "max_size_usd": 12_500.0, "spread_proxy_pct": 0.001},
        ),
    )


def test_target_and_stop_same_bar_counts_stop_first() -> None:
    sample = _sample([130.0], [90.0], [120.0])
    result, target_bar, stop_bar = RewardRiskAnalyzer._simulate_sample(sample, "long", 3.0)
    assert result == -1.0
    assert target_bar is None
    assert stop_bar == 1


def test_expectancy_profit_factor_and_drawdown() -> None:
    samples = [
        _sample([130.0], [99.0], [130.0]),
        _sample([130.0], [99.0], [130.0]),
        _sample([104.0], [90.0], [90.0]),
    ]
    metrics = RewardRiskAnalyzer([3.0], min_samples=1).metrics_for_rr(samples, "long", 3.0)
    assert metrics["expectancy_r"] == 1.66667
    assert metrics["profit_factor"] == 6.0
    assert metrics["max_drawdown_r"] == 1.0


def test_best_rr_ignores_sub_4r_and_unprofitable_4r_candidates() -> None:
    samples = [
        _sample([125.0], [99.0], [100.0]),
        _sample([125.0], [99.0], [100.0]),
        _sample([125.0], [99.0], [100.0]),
        _sample([151.0], [90.0], [151.0]),
    ]
    result = RewardRiskAnalyzer([2.0, 5.0], min_samples=1).analyze(samples, "long")
    assert result["best_rr"] == 0.0


def test_best_rr_selects_profitable_4r_or_higher_candidate() -> None:
    samples = [
        _sample([151.0], [99.0], [151.0]),
        _sample([151.0], [99.0], [151.0]),
        _sample([104.0], [90.0], [90.0]),
    ]
    result = RewardRiskAnalyzer([2.0, 5.0], min_samples=1).analyze(samples, "long")
    assert result["best_rr"] == 5.0


def test_best_rr_has_no_selectable_candidate_below_4r() -> None:
    samples = [
        _sample([125.0], [99.0], [125.0]),
        _sample([104.0], [90.0], [90.0]),
    ]
    result = RewardRiskAnalyzer([2.0, 3.0], min_samples=1).analyze(samples, "long")
    assert result["best_rr"] == 0.0
    assert result["best_expectancy_r"] == 0.0


def test_simulation_subtracts_execution_cost_r() -> None:
    sample = _sample([130.0], [99.0], [130.0], cost_r=0.15)
    result, target_bar, stop_bar = RewardRiskAnalyzer._simulate_sample(sample, "long", 3.0)
    assert result == 2.85
    assert target_bar == 1
    assert stop_bar is None
    metrics = RewardRiskAnalyzer([3.0], min_samples=1).metrics_for_rr([sample], "long", 3.0)
    assert metrics["avg_execution_cost_r"] == 0.15
    assert metrics["triple_barrier_labels"] == {"target": 1, "stop": 0, "timeout": 0, "skipped": 0}
    assert metrics["avg_gap_adverse_r"] == 0.2
    assert metrics["mfe_before_mae_rate"] == 1.0
    assert metrics["avg_fill_probability"] == 0.8
    assert metrics["p25_max_size_usd"] == 12500.0


def test_cost_multiplier_stresses_result_r() -> None:
    sample = _sample([130.0], [99.0], [130.0], cost_r=0.15)
    result, _, _ = RewardRiskAnalyzer._simulate_sample(sample, "long", 3.0, cost_multiplier=2.0)
    assert result == 2.7


def test_canonical_outcome_skips_entry_gap_past_target() -> None:
    sample = _sample([151.0], [149.0], [150.0], opens=[140.0])
    detail = RewardRiskAnalyzer._simulate_sample_detail(sample, "long", 3.0)
    result, target_bar, stop_bar = RewardRiskAnalyzer._simulate_sample(sample, "long", 3.0)
    assert detail["status"] == "skipped"
    assert detail["reason"] == "gapped_past_target"
    assert (result, target_bar, stop_bar) == (0.0, None, None)


def test_skipped_signals_do_not_dilute_traded_aggregates() -> None:
    winner = _sample([130.0], [99.0], [130.0])
    loser = _sample([104.0], [90.0], [90.0])
    skipped = _sample([151.0], [149.0], [150.0], opens=[140.0])
    metrics = RewardRiskAnalyzer([3.0], min_samples=1).metrics_for_rr([winner, loser, skipped], "long", 3.0)
    # Traded aggregates over {+3R, -1R} only; the skipped signal adds no 0R.
    assert metrics["sample_count"] == 2
    assert metrics["signal_count"] == 3
    assert metrics["skipped_count"] == 1
    assert metrics["skip_rate"] == 0.33333
    assert metrics["skip_reason_counts"] == {"gapped_past_target": 1}
    assert metrics["expectancy_r"] == 1.0
    assert metrics["win_rate"] == 0.5
    assert metrics["loss_rate"] == 0.5
    assert metrics["target_hit_rate"] == 0.5
    assert metrics["stop_hit_rate"] == 0.5
    assert metrics["triple_barrier_labels"] == {"target": 1, "stop": 1, "timeout": 0, "skipped": 1}
    # Speed labels only cover traded samples (no phantom timeout for the skip).
    assert sum(metrics["speed_label_counts"].values()) == 2


def test_all_skipped_signals_yield_zero_sample_count() -> None:
    skipped = _sample([151.0], [149.0], [150.0], opens=[140.0])
    metrics = RewardRiskAnalyzer([3.0], min_samples=1).metrics_for_rr([skipped, skipped], "long", 3.0)
    assert metrics["sample_count"] == 0
    assert metrics["signal_count"] == 2
    assert metrics["skipped_count"] == 2
    assert metrics["skip_rate"] == 1.0
    assert metrics["expectancy_r"] == 0.0
    assert metrics["win_rate"] == 0.0
    assert metrics["profit_factor"] == 0.0


def test_cluster_split_metrics_do_not_count_skips_as_zero_r() -> None:
    winner = _sample([130.0], [99.0], [130.0])
    loser = _sample([104.0], [90.0], [90.0])
    skipped = _sample([151.0], [149.0], [150.0], opens=[140.0])

    metrics = ClusterResearchEngine._split_metrics([winner, loser, skipped], "long", 3.0)

    assert metrics["sample_count"] == 2
    assert metrics["signal_count"] == 3
    assert metrics["skipped_count"] == 1
    assert metrics["skip_rate"] == 0.33333
    assert metrics["skip_reason_counts"] == {"gapped_past_target": 1}
    assert metrics["expectancy_r"] == 1.0
    assert metrics["win_rate"] == 0.5


def test_quant_validation_metrics_do_not_count_skips_as_unique_events() -> None:
    winner = _sample([130.0], [99.0], [130.0])
    loser = _sample([104.0], [90.0], [90.0])
    skipped = _sample([151.0], [149.0], [150.0], opens=[140.0])
    for index, sample in enumerate((winner, loser, skipped), start=1):
        sample.symbol = f"TST{index}"
        sample.end = f"2024-01-{20 + index:02d}"
        sample.outcome.forward_end = f"2024-01-{25 + index:02d}"

    metrics = ClusterResearchEngine(quant_bootstrap_draws=100)._quant_validation_metrics(
        [winner, loser, skipped],
        side="long",
        rr=3.0,
    )

    assert metrics["n_raw"] == 3
    assert metrics["signal_count"] == 3
    assert metrics["skipped_count"] == 1
    assert metrics["skip_rate"] == 0.33333
    assert metrics["skip_reason_counts"] == {"gapped_past_target": 1}
    assert metrics["n_unique"] == 2
    assert metrics["expectancy_r_weighted"] == 1.0
