from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

IntradayPatternState = Literal[
    "INTRADAY_LAB",
    "INTRADAY_PAPER_CANDIDATE",
    "INTRADAY_PRODUCTION",
    "INTRADAY_REJECTED",
]


@dataclass(frozen=True, slots=True)
class IntradayDirectorThresholds:
    min_shadow_observations: int = 50
    min_paper_fills: int = 10
    min_unique_days: int = 5
    min_buckets: int = 2
    min_net_ev_r: float = 0.05
    max_slippage_bps: float = 80.0
    max_age_days: int = 30


@dataclass(frozen=True, slots=True)
class IntradayEvidence:
    shadow_observations: int
    paper_fills: int
    unique_days: int
    buckets: int
    net_ev_r: float
    slippage_bps: float
    last_evidence_at: datetime
    flat_success_rate: float = 1.0


@dataclass(frozen=True, slots=True)
class IntradayDirectorDecision:
    state: IntradayPatternState
    promotion_allowed: bool
    reason_codes: tuple[str, ...]


class IntradayDirectorGate:
    def __init__(self, thresholds: IntradayDirectorThresholds | None = None) -> None:
        self.thresholds = thresholds or IntradayDirectorThresholds()

    def evaluate(self, evidence: IntradayEvidence, *, now: datetime | None = None) -> IntradayDirectorDecision:
        current = _as_utc(now)
        t = self.thresholds
        reasons: list[str] = []
        if evidence.shadow_observations < t.min_shadow_observations:
            reasons.append("insufficient_shadow_observations")
        if evidence.unique_days < t.min_unique_days:
            reasons.append("insufficient_unique_days")
        if evidence.buckets < t.min_buckets:
            reasons.append("insufficient_buckets")
        if evidence.net_ev_r < t.min_net_ev_r:
            reasons.append("net_ev_below_threshold")
        if evidence.slippage_bps > t.max_slippage_bps:
            reasons.append("slippage_too_high")
        if current - _as_utc(evidence.last_evidence_at) > timedelta(days=t.max_age_days):
            reasons.append("evidence_stale")
        if evidence.flat_success_rate < 1.0:
            reasons.append("flat_not_perfect")
        if evidence.paper_fills < t.min_paper_fills:
            if reasons:
                return IntradayDirectorDecision("INTRADAY_LAB", False, tuple(reasons + ["paper_required"]))
            return IntradayDirectorDecision("INTRADAY_PAPER_CANDIDATE", False, ("paper_required",))
        if reasons:
            return IntradayDirectorDecision("INTRADAY_REJECTED", False, tuple(reasons))
        return IntradayDirectorDecision("INTRADAY_PRODUCTION", True, ())


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
