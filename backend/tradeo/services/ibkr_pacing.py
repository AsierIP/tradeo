from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Iterable, Protocol

HISTORICAL_DATA = "historical"
REALTIME_BARS = "realtime_bar"
MARKET_DATA_LINE = "market_data_line"


@dataclass(frozen=True)
class PacingRule:
    capacity: int
    window_seconds: int
    daily_reserved: int = 0

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("pacing capacity must be positive")
        if self.window_seconds <= 0:
            raise ValueError("pacing window must be positive")
        if self.daily_reserved < 0 or self.daily_reserved >= self.capacity:
            raise ValueError("daily_reserved must be non-negative and below capacity")


@dataclass(frozen=True)
class PacingRequest:
    symbol: str
    timeframe: str
    request_type: str = HISTORICAL_DATA
    role: str = ""
    priority: int = 0
    portfolio_open: bool = False
    last_updated_at: datetime | None = None
    scope: str = "intraday"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_key(self) -> tuple[str, str, str, str]:
        return (
            self.request_type.strip().lower(),
            self.symbol.strip().upper(),
            self.timeframe.strip().lower(),
            self.role.strip().lower(),
        )


@dataclass(frozen=True)
class PacingDecision:
    allowed: bool
    request_type: str
    symbol: str
    timeframe: str
    scope: str
    reason: str
    requested_at: datetime
    next_available_at: datetime | None
    budget_remaining: int
    remaining_by_window: dict[int, int]
    degraded_to_shadow_safe: bool


@dataclass(frozen=True)
class PacingPlan:
    allowed: list[PacingRequest]
    skipped: list[tuple[PacingRequest, PacingDecision]]
    decisions: list[PacingDecision]
    degraded_to_shadow_safe: bool


@dataclass(frozen=True)
class _PacingEvent:
    timestamp: datetime
    request_type: str
    symbol: str
    timeframe: str
    scope: str


class PacingLedger(Protocol):
    def record(self, entry: dict[str, Any]) -> None: ...


class InMemoryPacingLedger:
    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def record(self, entry: dict[str, Any]) -> None:
        self.entries.append(dict(entry))


class SqlAlchemyPacingLedgerAdapter:
    """Optional DB adapter; no-ops until WP-02 adds IntradayPacingLedger."""

    def __init__(self, db: Any) -> None:
        self.db = db

    def record(self, entry: dict[str, Any]) -> None:
        from tradeo.db import models

        model = getattr(models, "IntradayPacingLedger", None)
        if model is None:
            return
        row = model(
            timestamp=entry["timestamp"],
            request_type=entry["request_type"],
            symbol=entry["symbol"],
            timeframe=entry["timeframe"],
            allowed=entry["allowed"],
            budget_remaining=entry["budget_remaining"],
            blocked_reason=entry.get("blocked_reason", ""),
            ibkr_error_code=entry.get("ibkr_error_code"),
        )
        self.db.add(row)


class IbkrPacingBudget:
    """Central rolling budget for IBKR data requests used by intraday jobs."""

    def __init__(
        self,
        *,
        rules: dict[str, PacingRule | list[PacingRule]] | None = None,
        ledger: PacingLedger | None = None,
        clock: Any | None = None,
        minimum_refresh_interval_seconds: int = 0,
    ) -> None:
        self.rules = self._normalize_rules(rules or self._default_rules())
        self.ledger = ledger or InMemoryPacingLedger()
        self.clock = clock
        self.minimum_refresh_interval_seconds = max(0, int(minimum_refresh_interval_seconds))
        self._events: dict[str, deque[_PacingEvent]] = defaultdict(deque)
        self._omitted_symbols_by_pacing: set[str] = set()
        self._last_update_by_timeframe: dict[str, datetime] = {}
        self._last_degraded_at: datetime | None = None

    def try_acquire(
        self,
        request_type: str,
        symbol: str,
        timeframe: str,
        *,
        scope: str = "intraday",
        now: datetime | None = None,
        ibkr_error_code: int | None = None,
    ) -> PacingDecision:
        requested_at = self._now(now)
        key = self._request_type_key(request_type)
        rules = self.rules[key]
        self._prune(key, requested_at)
        block_reason = ""
        next_available_at: datetime | None = None
        for rule in rules:
            used_total = self._used(key, requested_at, rule.window_seconds)
            used_intraday = self._used(
                key,
                requested_at,
                rule.window_seconds,
                scope_filter="intraday",
            )
            if scope == "intraday":
                intraday_capacity = rule.capacity - rule.daily_reserved
                if rule.daily_reserved > 0 and used_intraday >= intraday_capacity:
                    block_reason = "daily_budget_reserved"
                    next_available_at = self._next_slot(
                        key,
                        requested_at,
                        rule.window_seconds,
                        scope_filter="intraday",
                    )
                    break
            if used_total >= rule.capacity:
                block_reason = "pacing_exhausted"
                next_available_at = self._next_slot(key, requested_at, rule.window_seconds)
                break

        allowed = not block_reason
        normalized_symbol = symbol.strip().upper()
        normalized_timeframe = timeframe.strip().lower()
        if allowed:
            self._events[key].append(
                _PacingEvent(
                    timestamp=requested_at,
                    request_type=key,
                    symbol=normalized_symbol,
                    timeframe=normalized_timeframe,
                    scope=scope,
                )
            )
            self._last_update_by_timeframe[normalized_timeframe] = requested_at
            reason = "allowed"
        else:
            self._omitted_symbols_by_pacing.add(normalized_symbol)
            self._last_degraded_at = requested_at
            reason = block_reason

        remaining_by_window = self._remaining_by_window(
            key,
            requested_at,
            scope=scope,
        )
        budget_remaining = min(remaining_by_window.values()) if remaining_by_window else 0
        decision = PacingDecision(
            allowed=allowed,
            request_type=key,
            symbol=normalized_symbol,
            timeframe=normalized_timeframe,
            scope=scope,
            reason=reason,
            requested_at=requested_at,
            next_available_at=next_available_at,
            budget_remaining=budget_remaining,
            remaining_by_window=remaining_by_window,
            degraded_to_shadow_safe=not allowed,
        )
        self._record(decision, ibkr_error_code=ibkr_error_code)
        return decision

    def plan_requests(
        self,
        requests: Iterable[PacingRequest],
        *,
        now: datetime | None = None,
    ) -> PacingPlan:
        requested_at = self._now(now)
        deduped = self._dedupe_requests(requests)
        allowed: list[PacingRequest] = []
        skipped: list[tuple[PacingRequest, PacingDecision]] = []
        decisions: list[PacingDecision] = []
        for request in self._sort_requests(deduped):
            if self._cache_is_fresh(request, requested_at):
                decision = self._cache_fresh_decision(request, requested_at)
                skipped.append((request, decision))
                decisions.append(decision)
                continue
            decision = self.try_acquire(
                request.request_type,
                request.symbol,
                request.timeframe,
                scope=request.scope,
                now=requested_at,
            )
            decisions.append(decision)
            if decision.allowed:
                allowed.append(request)
            else:
                skipped.append((request, decision))
        return PacingPlan(
            allowed=allowed,
            skipped=skipped,
            decisions=decisions,
            degraded_to_shadow_safe=any(d.degraded_to_shadow_safe for d in decisions),
        )

    def metrics(self, *, now: datetime | None = None) -> dict[str, Any]:
        current = self._now(now)
        payload: dict[str, Any] = {
            "generated_at": current.isoformat(),
            "request_types": {},
            "omitted_symbols_by_pacing": sorted(self._omitted_symbols_by_pacing),
            "last_update_by_timeframe": {
                timeframe: value.isoformat()
                for timeframe, value in sorted(self._last_update_by_timeframe.items())
            },
            "degraded_to_shadow_safe": self._last_degraded_at is not None,
            "last_degraded_at": self._last_degraded_at.isoformat()
            if self._last_degraded_at
            else None,
            "new_entries_allowed": self._last_degraded_at is None,
        }
        for request_type, rules in self.rules.items():
            self._prune(request_type, current)
            windows = []
            for rule in rules:
                used = self._used(request_type, current, rule.window_seconds)
                windows.append(
                    {
                        "window_seconds": rule.window_seconds,
                        "capacity": rule.capacity,
                        "daily_reserved": rule.daily_reserved,
                        "used": used,
                        "remaining": max(0, rule.capacity - used),
                        "next_available_at": _iso_or_none(
                            self._next_slot(request_type, current, rule.window_seconds)
                        ),
                    }
                )
            payload["request_types"][request_type] = {"windows": windows}
        return payload

    def _record(self, decision: PacingDecision, *, ibkr_error_code: int | None = None) -> None:
        self.ledger.record(
            {
                "timestamp": decision.requested_at,
                "request_type": decision.request_type,
                "symbol": decision.symbol,
                "timeframe": decision.timeframe,
                "scope": decision.scope,
                "allowed": decision.allowed,
                "budget_remaining": decision.budget_remaining,
                "blocked_reason": "" if decision.allowed else decision.reason,
                "ibkr_error_code": ibkr_error_code,
                "next_available_at": decision.next_available_at,
            }
        )

    def _remaining_by_window(
        self,
        request_type: str,
        now: datetime,
        *,
        scope: str,
    ) -> dict[int, int]:
        out: dict[int, int] = {}
        for rule in self.rules[request_type]:
            used_total = self._used(request_type, now, rule.window_seconds)
            remaining = rule.capacity - used_total
            if scope == "intraday":
                used_intraday = self._used(
                    request_type,
                    now,
                    rule.window_seconds,
                    scope_filter="intraday",
                )
                remaining = min(remaining, rule.capacity - rule.daily_reserved - used_intraday)
            out[rule.window_seconds] = max(0, remaining)
        return out

    def _used(
        self,
        request_type: str,
        now: datetime,
        window_seconds: int,
        *,
        scope_filter: str | None = None,
    ) -> int:
        cutoff = now - timedelta(seconds=window_seconds)
        return sum(
            1
            for event in self._events[request_type]
            if event.timestamp > cutoff
            and (scope_filter is None or event.scope == scope_filter)
        )

    def _next_slot(
        self,
        request_type: str,
        now: datetime,
        window_seconds: int,
        *,
        scope_filter: str | None = None,
    ) -> datetime | None:
        cutoff = now - timedelta(seconds=window_seconds)
        candidates = [
            event.timestamp
            for event in self._events[request_type]
            if event.timestamp > cutoff
            and (scope_filter is None or event.scope == scope_filter)
        ]
        if not candidates:
            return now
        return min(candidates) + timedelta(seconds=window_seconds)

    def _prune(self, request_type: str, now: datetime) -> None:
        max_window = max(rule.window_seconds for rule in self.rules[request_type])
        cutoff = now - timedelta(seconds=max_window)
        events = self._events[request_type]
        while events and events[0].timestamp <= cutoff:
            events.popleft()

    def _cache_is_fresh(self, request: PacingRequest, now: datetime) -> bool:
        if not request.last_updated_at or self.minimum_refresh_interval_seconds <= 0:
            return False
        last = self._as_utc(request.last_updated_at)
        return now - last < timedelta(seconds=self.minimum_refresh_interval_seconds)

    def _cache_fresh_decision(self, request: PacingRequest, now: datetime) -> PacingDecision:
        return PacingDecision(
            allowed=False,
            request_type=self._request_type_key(request.request_type),
            symbol=request.symbol.strip().upper(),
            timeframe=request.timeframe.strip().lower(),
            scope=request.scope,
            reason="cache_fresh",
            requested_at=now,
            next_available_at=None,
            budget_remaining=min(
                self._remaining_by_window(
                    self._request_type_key(request.request_type),
                    now,
                    scope=request.scope,
                ).values()
            ),
            remaining_by_window=self._remaining_by_window(
                self._request_type_key(request.request_type),
                now,
                scope=request.scope,
            ),
            degraded_to_shadow_safe=False,
        )

    @staticmethod
    def _dedupe_requests(requests: Iterable[PacingRequest]) -> list[PacingRequest]:
        selected: dict[tuple[str, str, str, str], PacingRequest] = {}
        for request in requests:
            current = selected.get(request.normalized_key)
            if current is None or _request_sort_key(request) > _request_sort_key(current):
                selected[request.normalized_key] = request
        return list(selected.values())

    @staticmethod
    def _sort_requests(requests: list[PacingRequest]) -> list[PacingRequest]:
        return sorted(requests, key=_request_sort_key, reverse=True)

    @staticmethod
    def _request_type_key(request_type: str) -> str:
        return request_type.strip().lower()

    @staticmethod
    def _normalize_rules(
        rules: dict[str, PacingRule | list[PacingRule]],
    ) -> dict[str, list[PacingRule]]:
        normalized: dict[str, list[PacingRule]] = {}
        for request_type, value in rules.items():
            values = value if isinstance(value, list) else [value]
            normalized[request_type.strip().lower()] = sorted(
                values,
                key=lambda rule: rule.window_seconds,
            )
        return normalized

    @staticmethod
    def _default_rules() -> dict[str, list[PacingRule]]:
        return {
            HISTORICAL_DATA: [PacingRule(capacity=60, window_seconds=600, daily_reserved=10)],
            REALTIME_BARS: [PacingRule(capacity=60, window_seconds=600, daily_reserved=10)],
            MARKET_DATA_LINE: [PacingRule(capacity=100, window_seconds=1, daily_reserved=20)],
        }

    def _now(self, value: datetime | None = None) -> datetime:
        if value is not None:
            return self._as_utc(value)
        if self.clock is not None:
            return self._as_utc(self.clock())
        return datetime.now(UTC)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _request_sort_key(request: PacingRequest) -> tuple[int, int, float]:
    last = request.last_updated_at
    last_ts = 0.0 if last is None else IbkrPacingBudget._as_utc(last).timestamp()
    return (1 if request.portfolio_open else 0, int(request.priority), -last_ts)


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
