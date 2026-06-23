from __future__ import annotations

import json
import inspect
from copy import deepcopy

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings
from tradeo.research.pattern_committee import COMMITTEE_ROLES, PatternResearchCommittee
from tradeo.research.types import ClusterCandidate


def _strong_candidate(*, timeframe: str = "1d") -> ClusterCandidate:
    return ClusterCandidate(
        pattern_key=f"committee_{timeframe}_strong",
        name="COMMITTEE_STRONG",
        side="long",
        timeframe=timeframe,
        window_size=20,
        cluster_id=7,
        centroid=[0.1, 0.2, 0.3],
        sample_count=180,
        symbol_count=12,
        year_count=4,
        score=0.91,
        validation_passed=True,
        validation_reasons=[],
        metrics={
            "validation_passed": True,
            "promotion_status": "lab_candidate",
            "promotion_reason": "ValidationGate accepted LAB candidate",
            "required_runtime_rr": 4.0,
            "best_rr": 4.0,
            "best_expectancy_r": 0.55,
            "expectancy_r": 0.55,
            "best_profit_factor": 2.4,
            "profit_factor": 2.4,
            "best_max_drawdown_r": 4.0,
            "out_of_sample_expectancy_r": 0.31,
            "out_of_sample_profit_factor": 1.9,
            "stability_score": 0.78,
            "fdr_passed": True,
            "cost_stress_passed": True,
            "overfit_score": 0.10,
            "effective_sample_count": 125.0,
            "avg_fill_probability": 0.72,
            "rr_metrics": {"4": {"expectancy_r": 0.55, "profit_factor": 2.4}},
            "research_hypothesis": {
                "thesis": "trend compression resolves with positive continuation",
                "edge_claim": "NO_DEMOSTRADO",
            },
            "pattern_lifecycle": {"state": "discovered"},
            "research_director": {"paper_live_auto_promotion": False},
        },
        feature_summary={},
        examples=[],
    )


def _committee(tmp_path) -> PatternResearchCommittee:
    return PatternResearchCommittee(
        settings=Settings(reports_dir=str(tmp_path / "reports"), artifacts_dir=str(tmp_path / "artifacts"))
    )


def test_daily_strong_pattern_passes_to_lab_daily(tmp_path) -> None:
    candidate = _strong_candidate(timeframe="1d")

    summary = _committee(tmp_path).review_candidates([candidate], run_id=101, params={"interval": "1d"})

    assert summary["approved_count"] == 1
    assert candidate.validation_passed is True
    assert candidate.metrics["research_committee_approved"] is True
    assert candidate.metrics["research_committee_verdict"] == "approved_for_lab"
    assert candidate.metrics["lab_destination"] == "lab_daily"
    assert candidate.metrics["next_research_layer"] == "lab_daily"
    assert candidate.metrics["promotion_status"] == "lab_candidate"
    assert "consensus" in candidate.metrics["promotion_reason"]
    payload = candidate.metrics["research_committee"]
    assert candidate.metrics["research_committee_compact"]["approved"] is True
    assert candidate.metrics["pattern_lifecycle"]["committee_gate"] == payload
    assert candidate.metrics["research_director"]["pattern_committee"] == payload


def test_intraday_strong_pattern_passes_to_lab_intraday(tmp_path) -> None:
    candidate = _strong_candidate(timeframe="5m")

    _committee(tmp_path).review_candidates([candidate], run_id=102, params={"interval": "5m"})

    assert candidate.validation_passed is True
    assert candidate.metrics["lab_destination"] == "lab_intraday"
    assert candidate.metrics["next_research_layer"] == "lab_intraday"
    assert candidate.metrics["research_committee"]["lab_destination"] == "lab_intraday"


def test_pattern_with_failed_fdr_does_not_pass(tmp_path) -> None:
    candidate = _strong_candidate()
    candidate.metrics["fdr_passed"] = False

    _committee(tmp_path).review_candidates([candidate])

    assert candidate.validation_passed is False
    assert candidate.metrics["research_committee_approved"] is False
    assert candidate.metrics["research_committee_verdict"] == "rejected_false_positive"
    assert candidate.metrics["lab_destination"] is None
    assert candidate.metrics["next_research_layer"] is None
    assert candidate.metrics["promotion_status"] == "rejected"
    assert "fdr_failed" in candidate.metrics["research_committee"]["hard_failures"]
    assert "research_committee:rejected_false_positive" in candidate.validation_reasons


def test_pattern_with_negative_oos_expectancy_does_not_pass(tmp_path) -> None:
    candidate = _strong_candidate()
    candidate.metrics["out_of_sample_expectancy_r"] = -0.01

    _committee(tmp_path).review_candidates([candidate])

    assert candidate.validation_passed is False
    assert candidate.metrics["research_committee_approved"] is False
    assert candidate.metrics["research_committee_verdict"] == "rejected_false_positive"
    assert candidate.metrics["promotion_status"] == "rejected"
    assert "negative_oos_expectancy" in candidate.metrics["research_committee"]["hard_failures"]
    assert "research_committee:rejected_false_positive" in candidate.validation_reasons


def test_agents_after_first_include_prior_agents_and_critiques(tmp_path) -> None:
    candidate = _strong_candidate()

    _committee(tmp_path).review_candidates([candidate])

    agents = candidate.metrics["research_committee"]["agents"]
    assert [agent["role"] for agent in agents] == list(COMMITTEE_ROLES)
    required_fields = {
        "agent_id",
        "role",
        "focus",
        "seen_prior_agents",
        "critique_of_previous",
        "supporting_evidence",
        "objections",
        "entry_exit_recommendations",
        "vote",
        "confidence",
        "veto",
        "veto_reason",
    }
    for index, agent in enumerate(agents):
        assert required_fields <= set(agent)
        if index == 0:
            assert agent["seen_prior_agents"] == []
        else:
            assert len(agent["seen_prior_agents"]) == index
            assert agent["critique_of_previous"]
            assert "prior agents" in agent["critique_of_previous"]


def test_committee_payload_is_json_serializable(tmp_path) -> None:
    candidate = _strong_candidate()

    _committee(tmp_path).review_candidates([candidate])

    json.dumps(candidate.metrics["research_committee"], sort_keys=True)
    json.dumps(candidate.metrics["research_committee_compact"], sort_keys=True)
    json.dumps(candidate.metrics["pattern_lifecycle"]["committee_gate"], sort_keys=True)
    json.dumps(candidate.metrics["research_director"]["pattern_committee"], sort_keys=True)


def test_committee_cannot_leave_promotion_status_as_production(tmp_path) -> None:
    candidate = _strong_candidate()
    candidate.metrics = deepcopy(candidate.metrics)
    candidate.metrics["promotion_status"] = "production"

    _committee(tmp_path).review_candidates([candidate])

    assert candidate.validation_passed is True
    assert candidate.metrics["research_committee_approved"] is True
    assert candidate.metrics["promotion_status"] == "lab_candidate"
    assert candidate.metrics["research_committee"]["production_or_live_allowed"] is False


def test_lab_agent_wires_committee_between_validation_gate_and_registry() -> None:
    source = inspect.getsource(PatternDiscoveryLabAgent.run)

    validation_index = source.index("ValidationGate(settings).evaluate_many")
    committee_index = source.index("PatternResearchCommittee(settings=settings).review_candidates")
    registry_index = source.index("NovelPatternRegistry().store_candidates")

    assert validation_index < committee_index < registry_index
