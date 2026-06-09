from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np

from tradeo.core.config import Settings
from tradeo.research.adversarial_research import AdversarialResearchEngine
from tradeo.research.causal_invariance import CausalInvariantTester
from tradeo.research.foundation_teacher import FoundationChartTeacher
from tradeo.research.market_replay import MarketReplayConfig, MarketReplayEngine
from tradeo.research.research_director import ResearchDirector
from tradeo.research.types import ClusterCandidate, ForwardOutcome, WindowSample
from tradeo.research.validation_gate import ValidationGate


def _sample(
    index: int,
    *,
    symbol: str = "AAA",
    year: int = 2024,
    win: bool = True,
    fill_probability: float = 0.90,
    max_size_usd: float = 25000.0,
) -> WindowSample:
    entry = 100.0
    risk = 10.0
    if win:
        highs = [111.0, 132.0, 135.0]
        lows = [99.0, 101.0, 108.0]
        closes = [102.0, 126.0, 133.0]
    else:
        highs = [101.0, 102.0, 103.0]
        lows = [96.0, 91.0, 88.0]
        closes = [98.0, 93.0, 90.0]
    end = date(year, 1, 1) + timedelta(days=index)
    result = 3.0 if win else -1.0
    return WindowSample(
        symbol=symbol,
        timeframe="1d",
        window_size=20,
        start=(end - timedelta(days=20)).isoformat(),
        end=end.isoformat(),
        year=year,
        vector=np.asarray([index / 10.0, 1.0 if win else -1.0, year - 2020], dtype=np.float32),
        chart={
            "close_norm": [0.0, 0.01, 0.02, 0.03, 0.06, 0.10],
            "volume_rel": [0.2, 0.3, 0.5, 0.7, 0.8, 1.0],
            "range_pct": [0.1, 0.1, 0.2, 0.2, 0.3, 0.3],
        },
        features={
            "market_regime_score": 0.4,
            "volatility_regime": 1.0,
            "trend_regime": 1.0,
            "sector_strength": 0.05,
            "liquidity_score": 0.8,
            "volume_phase_acceleration": 0.2,
            "slope": 0.04,
            "long_entry_trigger_score": 0.8,
        },
        outcome=ForwardOutcome(
            forward_returns={3: closes[-1] / entry - 1.0},
            entry_price=entry,
            risk_proxy=risk,
            forward_end=(end + timedelta(days=3)).isoformat(),
            long_mfe_r=max((max(highs) - entry) / risk, 0.0),
            long_mae_r=max((entry - min(lows)) / risk, 0.0),
            long_outcome_r=result,
            long_hit_4r=False,
            short_mfe_r=max((entry - min(lows)) / risk, 0.0),
            short_mae_r=max((max(highs) - entry) / risk, 0.0),
            short_outcome_r=-result,
            short_hit_4r=False,
            forward_highs=highs,
            forward_lows=lows,
            forward_closes=closes,
            execution_cost_r=0.05,
            long_gap_adverse_r=0.0,
            long_mfe_before_mae=True,
            execution={
                "fill_probability": fill_probability,
                "max_size_usd": max_size_usd,
                "spread_proxy_pct": 0.001,
                "slippage_proxy_pct": 0.002,
                "entry_gap_penalty_pct": 0.001,
                "short_borrow_proxy_pct": 0.001,
            },
        ),
    )


def _candidate(samples: list[WindowSample], metrics: dict[str, object]) -> ClusterCandidate:
    centroid = np.mean(np.vstack([sample.vector for sample in samples]), axis=0).round(6).tolist()
    return ClusterCandidate(
        pattern_key="autonomous_lab_candidate",
        name="AUTONOMOUS_LAB_CANDIDATE",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=centroid,
        sample_count=len(samples),
        symbol_count=len({sample.symbol for sample in samples}),
        year_count=len({sample.year for sample in samples}),
        score=0.75,
        validation_passed=True,
        validation_reasons=[],
        metrics=metrics,
        feature_summary={},
        examples=[],
    )


def test_market_replay_penalizes_latency_and_partial_fills() -> None:
    samples = [
        _sample(1, fill_probability=0.50, max_size_usd=750.0),
        _sample(2, fill_probability=0.50, max_size_usd=750.0),
    ]

    replay = MarketReplayEngine(
        MarketReplayConfig(latency_bars=1, requested_size_usd=1500.0),
    ).analyze(samples, "long", 3.0)

    assert replay["sample_count"] == 2
    assert replay["avg_fill_ratio"] == 0.25
    assert replay["expected_expectancy_r"] < replay["full_fill_expectancy_r"]
    assert replay["partial_fill_rate"] == 1.0


def test_validation_gate_rejects_adversarial_hard_failure() -> None:
    candidate = _candidate(
        [_sample(i, symbol=f"S{i % 8}", year=2021 + i % 3) for i in range(140)],
        {
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
            "cost_stress_passed": True,
            "market_replay": {"expected_expectancy_r": 0.25, "avg_fill_ratio": 0.8, "passed": True},
            "causal_invariance": {
                "invariance_score": 0.7,
                "expected_fail_buckets": [],
                "symbol_dependency": {"no_three_symbol_dependency": True},
            },
            "adversarial_challenge": {
                "challenge_score": 0.2,
                "rejection_recommended": True,
                "rejection_reasons": ["leakage_probe"],
                "warnings": [],
            },
            "rr_metrics": {"3": {"expectancy_r": 0.45, "profit_factor": 2.4, "sample_count": 120}},
        },
    )

    evaluated = ValidationGate().evaluate(candidate)

    assert not evaluated.validation_passed
    assert any("adversarial rejection" in reason for reason in evaluated.validation_reasons)
    assert any("challenge score bajo" in reason for reason in evaluated.validation_reasons)


def test_research_director_writes_memory_graph_papers_and_agenda(tmp_path: Path) -> None:
    samples = [
        _sample(i, symbol=f"S{i % 6}", year=2021 + i % 3, win=i % 5 != 0)
        for i in range(36)
    ]
    replay = MarketReplayEngine().analyze(samples, "long", 3.0)
    causal = CausalInvariantTester(min_bucket_samples=1).analyze(samples, "long", 3.0)
    teacher = FoundationChartTeacher().analyze(samples, side="long", rr=3.0, baseline_samples=samples)
    metrics: dict[str, object] = {
        "best_rr": 3.0,
        "best_expectancy_r": 0.35,
        "best_profit_factor": 2.0,
        "expectancy_r": 0.35,
        "profit_factor": 2.0,
        "out_of_sample_expectancy_r": 0.20,
        "walk_forward_positive_fold_rate": 0.75,
        "purged_cv_positive_rate": 0.70,
        "expectancy_ci_low": 0.05,
        "edge_decay_parameter_score": 0.1,
        "cost_stress_passed": True,
        "expected_information_gain": 0.4,
        "novelty_score": 0.8,
        "human_rule": {
            "rule": "long setup when volume acceleration is positive",
            "conditions": [{"feature": "volume_phase_acceleration", "label": "volume acceleration"}],
        },
        "market_replay": replay,
        "causal_invariance": causal,
        "foundation_teacher": teacher,
    }
    metrics["adversarial_challenge"] = AdversarialResearchEngine().analyze(
        samples,
        baseline_samples=samples,
        side="long",
        rr=3.0,
        metrics=metrics,
        causal_invariance=causal,
        market_replay=replay,
    )
    candidate = _candidate(samples, metrics)
    settings = Settings(reports_dir=str(tmp_path), discovery_report_top_n=5)

    summary = ResearchDirector(settings=settings).run(
        run_id=77,
        candidates=[candidate],
        samples=samples,
        params={"window_sizes": [20]},
    )

    assert summary["candidate_count"] == 1
    assert Path(summary["memory_graph_path"]).exists()
    assert Path(summary["artifact_json_path"]).exists()
    assert Path(summary["artifact_markdown_path"]).exists()
    assert candidate.metrics["research_hypothesis"]["falsifiable"] is True
    assert candidate.metrics["research_memory"]["family_key"].startswith("family_long_1d_w20_")
    assert candidate.metrics["pattern_lifecycle"]["paper_live_auto_promotion"] is False
    assert candidate.metrics["research_paper_report_path"]
    assert Path(str(candidate.metrics["research_paper_report_path"])).exists()
    assert candidate.metrics["active_learning"]["experiments"]
