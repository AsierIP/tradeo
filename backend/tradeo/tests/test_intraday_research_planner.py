from __future__ import annotations

from tradeo.research.intraday_research_planner import IntradayResearchPlanner, PlannerInput


def test_planner_expands_small_universe() -> None:
    result = IntradayResearchPlanner().plan(PlannerInput(selected_count=84))

    assert result.decision == "expand_universe"
    assert result.waves == ()


def test_planner_recommends_next_waves_after_rejected_run() -> None:
    result = IntradayResearchPlanner().plan(
        PlannerInput(
            selected_count=117,
            rejected=48,
            persisted_candidates=48,
            blockers={
                "cost_stress_failed": 94,
                "oos_expectancy_not_positive": 86,
                "fdr_failed": 88,
            },
        )
    )

    assert result.decision == "change_search_space"
    names = [wave.name for wave in result.waves]
    assert "1h_W50_cost_aware" in names
    assert result.safety["paper_allowed"] is False
