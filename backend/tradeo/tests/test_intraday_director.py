from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tradeo.modules.intraday.director import (
    IntradayDirectorGate,
    IntradayDirectorThresholds,
    IntradayEvidence,
)


NOW = datetime(2026, 6, 22, tzinfo=timezone.utc)


def test_intraday_director_shadow_only_never_promotes_to_production() -> None:
    gate = IntradayDirectorGate(IntradayDirectorThresholds(min_shadow_observations=10, min_paper_fills=3))
    decision = gate.evaluate(
        IntradayEvidence(
            shadow_observations=20,
            paper_fills=0,
            unique_days=5,
            buckets=2,
            net_ev_r=0.2,
            slippage_bps=20,
            last_evidence_at=NOW,
        ),
        now=NOW,
    )

    assert decision.state == "INTRADAY_PAPER_CANDIDATE"
    assert decision.promotion_allowed is False
    assert decision.reason_codes == ("paper_required",)


def test_intraday_director_promotes_only_clean_paper_evidence() -> None:
    gate = IntradayDirectorGate(IntradayDirectorThresholds(min_shadow_observations=10, min_paper_fills=3))
    decision = gate.evaluate(
        IntradayEvidence(
            shadow_observations=20,
            paper_fills=3,
            unique_days=5,
            buckets=2,
            net_ev_r=0.2,
            slippage_bps=20,
            last_evidence_at=NOW,
        ),
        now=NOW,
    )

    assert decision.state == "INTRADAY_PRODUCTION"
    assert decision.promotion_allowed is True


def test_intraday_director_rejects_stale_or_degraded_evidence() -> None:
    gate = IntradayDirectorGate(IntradayDirectorThresholds(min_shadow_observations=10, min_paper_fills=3))
    decision = gate.evaluate(
        IntradayEvidence(
            shadow_observations=20,
            paper_fills=3,
            unique_days=5,
            buckets=2,
            net_ev_r=-0.1,
            slippage_bps=120,
            last_evidence_at=NOW - timedelta(days=60),
            flat_success_rate=0.99,
        ),
        now=NOW,
    )

    assert decision.state == "INTRADAY_REJECTED"
    assert decision.promotion_allowed is False
    assert decision.reason_codes == (
        "net_ev_below_threshold",
        "slippage_too_high",
        "evidence_stale",
        "flat_not_perfect",
    )
