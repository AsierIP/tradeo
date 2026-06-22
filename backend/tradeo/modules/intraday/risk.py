from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

RiskIntent = Literal["ENTRY", "REDUCE_ONLY", "RECONCILE"]


@dataclass(frozen=True, slots=True)
class IntradayRiskLimits:
    max_trades_per_day: int = 0
    max_trades_per_symbol: int = 0
    max_open_positions: int = 0
    max_daily_loss_usd: float = 0.0
    max_notional_usd: float = 0.0
    max_hold_minutes: int = 0
    no_new_entries_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class IntradayRiskState:
    trades_today: int = 0
    open_positions: int = 0
    realized_pnl_usd: float = 0.0
    notional_open_usd: float = 0.0
    trades_by_symbol: dict[str, int] = field(default_factory=dict)
    cooldown_until_by_symbol: dict[str, datetime] = field(default_factory=dict)
    kill_switch_active: bool = False
    kill_switch_reason: str = ""
    stale_data: bool = False
    broker_desync: bool = False
    calendar_unknown: bool = False
    flatten_failed: bool = False


@dataclass(frozen=True, slots=True)
class IntradayRiskRequest:
    symbol: str
    intent: RiskIntent = "ENTRY"
    now: datetime | None = None
    notional_usd: float = 0.0
    expected_hold_minutes: int = 0


@dataclass(frozen=True, slots=True)
class IntradayRiskDecision:
    allowed: bool
    reduce_only: bool
    reason_codes: tuple[str, ...]
    remaining_capacity: dict[str, float]

    @property
    def reason_code(self) -> str:
        return self.reason_codes[0] if self.reason_codes else "allowed"


class IntradayRiskManager:
    """Session-scoped risk gate; daily RiskManager remains separate."""

    def __init__(self, limits: IntradayRiskLimits) -> None:
        self.limits = limits

    def evaluate(
        self,
        request: IntradayRiskRequest,
        state: IntradayRiskState,
    ) -> IntradayRiskDecision:
        now = _as_utc(request.now)
        symbol = request.symbol.upper().strip()
        reasons: list[str] = []

        if state.kill_switch_active:
            reasons.append(state.kill_switch_reason or "kill_switch_active")
        if state.stale_data:
            reasons.append("stale_data")
        if state.broker_desync:
            reasons.append("broker_desync")
        if state.calendar_unknown:
            reasons.append("calendar_unknown")
        if state.flatten_failed:
            reasons.append("flatten_failed")

        if request.intent == "REDUCE_ONLY":
            hard = tuple(reasons)
            return IntradayRiskDecision(
                allowed=not state.broker_desync and not state.calendar_unknown,
                reduce_only=True,
                reason_codes=hard,
                remaining_capacity=self._remaining(state),
            )

        if self.limits.no_new_entries_at and now >= self.limits.no_new_entries_at:
            reasons.append("no_new_entries_cutoff")
        if self.limits.max_trades_per_day and state.trades_today >= self.limits.max_trades_per_day:
            reasons.append("max_trades_per_day")
        symbol_trades = state.trades_by_symbol.get(symbol, 0)
        if self.limits.max_trades_per_symbol and symbol_trades >= self.limits.max_trades_per_symbol:
            reasons.append("max_trades_per_symbol")
        if self.limits.max_open_positions and state.open_positions >= self.limits.max_open_positions:
            reasons.append("max_open_positions")
        if self.limits.max_daily_loss_usd and abs(min(state.realized_pnl_usd, 0.0)) >= self.limits.max_daily_loss_usd:
            reasons.append("max_daily_loss")
        if self.limits.max_notional_usd and state.notional_open_usd + request.notional_usd > self.limits.max_notional_usd:
            reasons.append("max_notional")
        if self.limits.max_hold_minutes and request.expected_hold_minutes > self.limits.max_hold_minutes:
            reasons.append("max_hold_minutes")
        cooldown_until = state.cooldown_until_by_symbol.get(symbol)
        if cooldown_until and now < _as_utc(cooldown_until):
            reasons.append("cooldown_active")

        return IntradayRiskDecision(
            allowed=not reasons,
            reduce_only=False,
            reason_codes=tuple(_dedupe(reasons)),
            remaining_capacity=self._remaining(state),
        )

    def ledger_snapshot(self, events: Iterable[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(str(event.get("event_type", "unknown")) for event in events)
        return {"scope": "intraday", "event_counts": dict(sorted(counts.items()))}

    def _remaining(self, state: IntradayRiskState) -> dict[str, float]:
        return {
            "trades_today": max(0, self.limits.max_trades_per_day - state.trades_today)
            if self.limits.max_trades_per_day
            else float("inf"),
            "open_positions": max(0, self.limits.max_open_positions - state.open_positions)
            if self.limits.max_open_positions
            else float("inf"),
            "notional_usd": max(0.0, self.limits.max_notional_usd - state.notional_open_usd)
            if self.limits.max_notional_usd
            else float("inf"),
        }


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
