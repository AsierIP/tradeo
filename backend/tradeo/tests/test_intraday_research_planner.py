from __future__ import annotations

import csv
import json
from pathlib import Path

from tradeo.research.intraday_research_planner import (
    IntradayResearchPlanner,
    PlannerInput,
    filter_prohibited_waves,
    planner_input_from_payload,
    render_markdown,
)


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


def test_universe_metadata_overrides_zero_diagnostic_selected_count(tmp_path: Path) -> None:
    metadata = tmp_path / "universe.metadata.json"
    metadata.write_text(json.dumps({"selected_count": 117}), encoding="utf-8")
    payload = {
        "selected_count": 0,
        "readiness_ready": True,
        "top_blockers": {"oos_unstable": 3},
    }

    planner_input = planner_input_from_payload(payload, universe_metadata=metadata)

    assert planner_input.selected_count == 117
    assert planner_input.selected_count_source == "universe_metadata"
    assert planner_input.selected_count_diagnostic_value == 0


def test_universe_file_can_supply_selected_count(tmp_path: Path) -> None:
    universe = tmp_path / "universe.csv"
    with universe.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "selected", "status"])
        writer.writeheader()
        writer.writerow({"symbol": "AAPL", "selected": "True", "status": "selected"})
        writer.writerow({"symbol": "MSFT", "selected": "False", "status": "rejected"})
        writer.writerow({"symbol": "NVDA", "selected": "1", "status": "selected"})

    planner_input = planner_input_from_payload({"selected_count": 0}, universe_file=universe)

    assert planner_input.selected_count == 2
    assert planner_input.selected_count_source == "universe_file"


def test_large_universe_with_oos_cost_fdr_blockers_changes_search_space() -> None:
    result = IntradayResearchPlanner().plan(
        PlannerInput(
            selected_count=117,
            readiness_ready=True,
            rejected=240,
            blockers={"oos_unstable": 235, "cost_dominated": 229, "statistical_datamined": 218},
        )
    )

    assert result.decision == "change_search_space"


def test_prohibited_repeats_filter_30m_w20_and_1h_w50() -> None:
    result = IntradayResearchPlanner().plan(
        PlannerInput(
            selected_count=117,
            rejected=240,
            blockers={"cost_dominated": 229, "oos_unstable": 235},
            prohibited_repeats=("30m W20 4,8,13", "1h W50 2,4,6"),
        )
    )

    blocked = {(item.name, item.reason, item.signature) for item in result.blocked_waves}
    assert ("1h_W50_cost_aware", "prohibited_repeat", "1h W50 2,4,6") in blocked
    assert all("1h W50 2,4,6" not in wave.signatures for wave in result.allowed_waves)
    assert all("30m W20 4,8,13" not in wave.signatures for wave in result.allowed_waves)


def test_filter_prohibited_waves_records_block_reason() -> None:
    result = IntradayResearchPlanner().plan(
        PlannerInput(
            selected_count=117,
            blockers={"cost_dominated": 1},
            prohibited_repeats=("30m W100 8,13,21",),
        )
    )

    assert any(item.reason == "prohibited_repeat" for item in result.blocked_waves)
    assert all("30m W100 8,13,21" not in wave.signatures for wave in result.allowed_waves)
    assert result.waves == result.allowed_waves


def test_recommended_limit_matches_selected_count_effective() -> None:
    result = IntradayResearchPlanner().plan(PlannerInput(selected_count=117, blockers={"oos_unstable": 1}))

    assert result.recommended_limit == 117
    assert result.limit_source == "selected_count_effective"
    assert result.input_summary["selected_count_effective"] == 117


def test_markdown_warns_about_explicit_limit() -> None:
    result = IntradayResearchPlanner().plan(PlannerInput(selected_count=117, blockers={"oos_unstable": 1}))
    markdown = render_markdown(result)

    assert "explicit `--limit 117`" in markdown


def test_allowed_waves_exclude_all_prohibited_signatures() -> None:
    result = IntradayResearchPlanner().plan(
        PlannerInput(
            selected_count=117,
            blockers={"cost_dominated": 2, "drawdown_excessive": 1},
            prohibited_repeats=("1h W50 2,4,6", "30m W100 8,13,21"),
        )
    )
    prohibited = {"1h w50 2,4,6", "30m w100 8,13,21"}

    for wave in result.allowed_waves:
        assert not prohibited.intersection(signature.lower() for signature in wave.signatures)


def test_filter_helper_blocks_exact_signature() -> None:
    result = IntradayResearchPlanner().plan(PlannerInput(selected_count=117, blockers={"cost_dominated": 1}))
    allowed, blocked = filter_prohibited_waves(result.allowed_waves, ("30m W100 8,13,21",))

    assert len(blocked) == 1
    assert blocked[0].signature == "30m W100 8,13,21"
    assert all("30m W100 8,13,21" not in wave.signatures for wave in allowed)


def test_planner_uses_vwap_summary_json_when_changing_search_space() -> None:
    result = IntradayResearchPlanner().plan(
        PlannerInput(
            selected_count=117,
            blockers={"oos_unstable": 1},
            vwap_summary=_vwap_summary(),
        )
    )

    names = [wave.name for wave in result.allowed_waves]
    assert result.decision == "change_search_space"
    assert names[0] == "30m_W100_vwap_reclaim_slow"
    assert "30m_W100_vwap_reject_slow" in names
    assert "30m_W100_vwap_reclaim_slow" in result.vwap_context["recommended_waves"]
    assert result.vwap_context["available"] is True
    assert result.vwap_context["symbols_analyzed"] == 117


def test_planner_keeps_previous_behavior_without_vwap_summary_json() -> None:
    result = IntradayResearchPlanner().plan(PlannerInput(selected_count=117, blockers={"oos_unstable": 1}))

    names = [wave.name for wave in result.allowed_waves]
    assert "30m_W100_standard_regime_probe" in names
    assert "30m_W100_vwap_reclaim_slow" not in names
    assert result.vwap_context["available"] is False


def _vwap_summary() -> dict[str, object]:
    return {
        "schema_version": "tradeo.intraday_vwap_research.v1",
        "status": "OK",
        "universe": {"symbols_analyzed": 117},
        "vwap_summary": {"bars_analyzed": 9000},
        "recommended_next_waves": [
            {
                "name": "30m_W100_vwap_reclaim_slow",
                "timeframe": "30m",
                "window_size": 100,
                "forward_bars": [8, 13, 21],
                "reason": "synthetic VWAP structure supports reclaim search",
                "signature": "30m W100 8,13,21",
            },
            {
                "name": "30m_W100_vwap_reject_slow",
                "timeframe": "30m",
                "window_size": 100,
                "forward_bars": [8, 13, 21],
                "reason": "synthetic VWAP structure supports reject search",
                "signature": "30m W100 8,13,21",
            }
        ],
    }
