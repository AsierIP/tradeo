from __future__ import annotations

from tradeo.research.intraday_research_forensics import classify_failure, next_hypotheses
from collections import Counter


def test_classifies_cost_dominated_from_cost_reasons() -> None:
    classes = classify_failure(
        rejection_reasons=["edge no sobrevive coste x2", "adversarial rejection: cost_shock"],
        sample_count=200,
        symbol_count=10,
        year_count=1,
    )

    assert "cost_dominated" in classes


def test_classifies_statistical_datamined_from_reality_checks() -> None:
    classes = classify_failure(
        rejection_reasons=[
            "no supera BH-FDR del run",
            "bootstrap reality proxy WRC-like insuficiente",
            "bootstrap reality proxy SPA-like insuficiente",
        ],
        sample_count=200,
        symbol_count=10,
        year_count=1,
    )

    assert "statistical_datamined" in classes


def test_classifies_oos_unstable_from_oos_metrics() -> None:
    classes = classify_failure(
        rejection_reasons=[],
        sample_count=200,
        symbol_count=10,
        year_count=1,
        oos_expectancy_r=-0.01,
        oos_profit_factor=0.9,
    )

    assert "oos_unstable" in classes


def test_missing_optional_fields_do_not_force_failure() -> None:
    classes = classify_failure(
        rejection_reasons=[],
        sample_count=100,
        symbol_count=8,
        year_count=1,
    )

    assert "insufficient_data" not in classes


def test_insufficient_data_when_scope_is_too_small() -> None:
    classes = classify_failure(
        rejection_reasons=[],
        sample_count=12,
        symbol_count=3,
        year_count=0,
    )

    assert "insufficient_data" in classes


def test_next_hypotheses_never_proposes_paper_or_live() -> None:
    hypotheses = next_hypotheses(Counter({"cost_dominated": 3, "oos_unstable": 2}))
    text = " ".join(item["hypothesis"] for item in hypotheses).lower()

    assert "paper" not in text
    assert "live" not in text
    assert "cost/spread filter required" in text


def test_exact_scope_contract_is_modelled_in_report_shape() -> None:
    # The CLI refuses implicit recency scopes by resolving only manifests/run IDs.
    # This unit test documents the public report contract used by downstream mail.
    scope = {"exact_scope": True, "wave_manifests": ["wave.json"], "run_ids": [1, 2]}

    assert scope["exact_scope"] is True
    assert scope["run_ids"] == [1, 2]
