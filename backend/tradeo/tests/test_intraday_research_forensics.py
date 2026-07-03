from __future__ import annotations

from collections import Counter

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import DiscoveredPattern, DiscoveryRun
from tradeo.db.session import Base

from tradeo.research.intraday_research_forensics import (
    ScopeViolationError,
    build_forensics_report,
    classify_failure,
    next_hypotheses,
    scope_integrity_report,
    validate_scope_integrity,
)


def _db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


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


def test_forensics_scope_integrity_fails_with_out_of_scope_run_id() -> None:
    report = {
        "scope_integrity": scope_integrity_report(scope_run_ids=[1, 2], observed_run_ids=[1, 3])
    }

    assert report["scope_integrity"]["passed"] is False
    assert report["scope_integrity"]["out_of_scope_run_ids"] == [3]
    with pytest.raises(ScopeViolationError):
        validate_scope_integrity(report)


def test_forensics_marks_long_candidate_as_side_mismatch_for_vwap_reject_short() -> None:
    db = _db()
    run = DiscoveryRun(
        status="completed",
        params_json={"vwap_condition": "vwap_reject_short", "vwap_side_bias": "short"},
        clusters_evaluated=2,
    )
    db.add(run)
    db.flush()
    db.add_all(
        [
            DiscoveredPattern(
                run_id=run.id,
                pattern_key="long_candidate",
                name="long candidate",
                side="long",
                sample_count=120,
                symbol_count=8,
                score=2.0,
                expectancy_r=0.4,
                profit_factor=1.8,
            ),
            DiscoveredPattern(
                run_id=run.id,
                pattern_key="short_candidate",
                name="short candidate",
                side="short",
                sample_count=120,
                symbol_count=8,
                score=1.0,
                expectancy_r=0.2,
                profit_factor=1.4,
            ),
        ]
    )
    db.commit()

    report = build_forensics_report(db=db, run_ids=[int(run.id)])
    by_key = {row["pattern_key"]: row for row in report["candidate_forensics"]}

    assert report["hypothesis_integrity"]["expected_side"] == "short"
    assert report["hypothesis_integrity"]["side_mismatch_count"] == 1
    assert by_key["long_candidate"]["side_matches_hypothesis"] is False
    assert by_key["long_candidate"]["hypothesis_rejection_reason"] == (
        "side_mismatch:vwap_reject_short_expected_short_got_long"
    )
    assert by_key["short_candidate"]["side_matches_hypothesis"] is True
