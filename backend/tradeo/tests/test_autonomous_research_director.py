from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import DiscoveredPattern, DiscoveredPatternStatus
from tradeo.db.session import Base
from tradeo.research.autonomous_research_director import ResearchDirector


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def _pattern(pattern_key: str, *, score: float = 0.8, run_id: int = 7) -> DiscoveredPattern:
    return DiscoveredPattern(
        run_id=run_id,
        pattern_key=pattern_key,
        name=pattern_key.upper(),
        status=DiscoveredPatternStatus.LAB_CANDIDATE,
        promotion_status="lab_candidate",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        pattern_family_key="family_long_1d_w20_alpha",
        canonical_pattern_key="novel_long_w20_a",
        variant_key=pattern_key,
        sample_count=160,
        symbol_count=14,
        year_count=4,
        score=score,
        reward_risk_estimate=3.2,
        expectancy_r=0.28,
        profit_factor=2.0,
        win_rate=0.46,
        avg_mfe_r=2.4,
        avg_mae_r=0.8,
        stability_score=0.62,
        out_of_sample_expectancy_r=0.16,
        out_of_sample_profit_factor=1.5,
        best_rr=3.0,
        best_tested_rr=3.0,
        best_expectancy_r=0.31,
        best_profit_factor=2.1,
        best_win_rate=0.47,
        best_max_drawdown_r=5.0,
        preferred_rr_passed=True,
        premium_rr_passed=False,
        promotion_reason="lab_candidate",
        validation_passed=True,
        validation_reasons_json=[],
        centroid_json=[0.1, 0.2, 0.3],
        rr_metrics_json={"3": {"expectancy_r": 0.31, "profit_factor": 2.1}},
        feature_summary_json={
            "relative_strength_sector": {"median": 0.04},
            "swing_trend_score": {"median": 0.35},
        },
        metrics_json={
            "best_rr": 3.0,
            "best_expectancy_r": 0.31,
            "best_profit_factor": 2.1,
            "human_rule": {
                "rule": "long setup when RS vs sector >= 0.02 and swing trend score >= 0.2",
                "conditions": [
                    {"label": "RS vs sector", "operator": ">=", "threshold": 0.02},
                    {"label": "swing trend score", "operator": ">=", "threshold": 0.2},
                ],
            },
            "regime_profile": {"dominant_regime": "normal_vol|up|market_up|broad|sector_strong|liquid"},
            "purged_cv_positive_rate": 0.75,
            "deflated_sharpe_probability": 0.68,
            "wrc_p_value": 0.08,
            "spa_p_value": 0.09,
            "cost_stress_passed": True,
            "edge_decay_passed": True,
            "avg_fill_probability": 0.82,
            "p25_max_size_usd": 18_000.0,
            "avg_execution_cost_r": 0.12,
            "avg_spread_proxy_pct": 0.001,
            "avg_slippage_proxy_pct": 0.002,
            "avg_entry_gap_penalty_pct": 0.001,
            "fast_target_rate": 0.18,
            "mfe_before_mae_rate": 0.61,
            "expectancy_lift_r": 0.14,
            "by_year_expectancy": {"2022": 0.2, "2023": 0.1, "2024": 0.3},
            "top_symbols_expectancy": {"AAA": 0.2, "BBB": 0.1, "CCC": 0.4},
            "expected_information_gain": 0.08,
        },
    )


def test_research_director_enriches_patterns_and_writes_artifacts(tmp_path: Path) -> None:
    db = session_factory()
    first = _pattern("novel_long_w20_a", score=0.9)
    second = _pattern("novel_long_w20_b", score=0.7)
    db.add_all([first, second])
    db.commit()

    result = ResearchDirector(Settings(reports_dir=str(tmp_path))).run(db, run_id=7)

    assert result["patterns_reviewed"] == 2
    assert result["hypotheses_created"] == 2
    assert result["memory_graph"]["node_count"] >= 2
    assert result["memory_graph"]["edge_count"] >= 1
    assert result["active_learning_agenda"]
    assert Path(result["artifacts"]["latest_json"]).exists()
    assert Path(result["artifacts"]["memory_graph"]).exists()

    enriched = db.query(DiscoveredPattern).filter_by(pattern_key="novel_long_w20_a").one()
    intelligence = enriched.metrics_json["research_intelligence"]
    assert intelligence["hypothesis"]["falsifiable"] is True
    assert intelligence["adversarial_challenge"]["verdict"] == "survives_adversarial_review"
    assert intelligence["lifecycle"]["paper_live_blocked"] is True
    assert intelligence["paper"]["death_conditions"]


def test_research_director_latest_artifact_is_reusable_json(tmp_path: Path) -> None:
    db = session_factory()
    db.add(_pattern("novel_long_w20_a"))
    db.commit()

    result = ResearchDirector(Settings(reports_dir=str(tmp_path))).run(db)

    latest = Path(result["artifacts"]["latest_json"]).read_text(encoding="utf-8")
    assert "Autonomous" not in latest
    assert "research_intelligence" not in latest
    assert "active_learning_agenda" in latest
