from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping

from tradeo.services.market_session import market_session_status

RESOURCE_POLICY_EVALUATE = "resource_policy.evaluate"
RESOURCE_MARKET_SESSION_STATUS = "market_session.status"
RESOURCE_LOCAL_CACHE_READ = "local_cache.read"
RESOURCE_LOCAL_CACHE_WRITE = "local_cache.write"
RESOURCE_ARTIFACT_WRITE = "artifact.write"
RESOURCE_REPORT_WRITE = "report.write"
RESOURCE_LAB_BACKTEST = "lab.backtest"
RESOURCE_MARKET_DATA_REFRESH = "market_data.refresh"
RESOURCE_IBKR_HISTORICAL_DATA = "ibkr.historical_data"
RESOURCE_REALTIME_MARKET_DATA = "market_data.realtime"
RESOURCE_ORDER_PREVIEW = "order.preview"
RESOURCE_PAPER_ORDER = "order.paper"
RESOURCE_LIVE_ORDER = "order.live"
RESOURCE_SIGNAL_OUTPUT = "signal.output"

PROHIBITED_RESOURCES = frozenset(
    {
        RESOURCE_ORDER_PREVIEW,
        RESOURCE_PAPER_ORDER,
        RESOURCE_LIVE_ORDER,
        RESOURCE_SIGNAL_OUTPUT,
    }
)
SESSION_SENSITIVE_RESOURCES = frozenset(
    {
        RESOURCE_MARKET_DATA_REFRESH,
        RESOURCE_IBKR_HISTORICAL_DATA,
        RESOURCE_REALTIME_MARKET_DATA,
    }
)
DEFAULT_OPEN_SESSION_ALLOWLIST = frozenset(
    {
        RESOURCE_POLICY_EVALUATE,
        RESOURCE_MARKET_SESSION_STATUS,
        RESOURCE_LOCAL_CACHE_READ,
    }
)
DEFAULT_CLOSED_SESSION_ALLOWLIST = frozenset(
    {
        *DEFAULT_OPEN_SESSION_ALLOWLIST,
        RESOURCE_LOCAL_CACHE_WRITE,
        RESOURCE_ARTIFACT_WRITE,
        RESOURCE_REPORT_WRITE,
        RESOURCE_LAB_BACKTEST,
        RESOURCE_MARKET_DATA_REFRESH,
        RESOURCE_IBKR_HISTORICAL_DATA,
    }
)
KNOWN_RESOURCES = (
    DEFAULT_OPEN_SESSION_ALLOWLIST
    | DEFAULT_CLOSED_SESSION_ALLOWLIST
    | PROHIBITED_RESOURCES
    | SESSION_SENSITIVE_RESOURCES
)

OPEN_STATE = "regular_open"
CLOSED_STATES = frozenset({"market_closed", "market_holiday"})
SUPPORTED_MARKET = "us_equities"

SessionProvider = Callable[[datetime | None], Mapping[str, object]]


@dataclass(frozen=True, slots=True)
class ResourcePolicyDecision:
    decision: str
    allowed_resources: tuple[str, ...]
    blocked_resources: tuple[str, ...]
    reason_codes: tuple[str, ...]
    block_reasons: dict[str, tuple[str, ...]]
    market_session: dict[str, object]
    fail_closed: bool

    @property
    def allowed(self) -> bool:
        return not self.fail_closed and not self.blocked_resources

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision,
            "allowed": self.allowed,
            "allowed_resources": list(self.allowed_resources),
            "blocked_resources": list(self.blocked_resources),
            "reason_codes": list(self.reason_codes),
            "block_reasons": {key: list(value) for key, value in self.block_reasons.items()},
            "market_session": dict(self.market_session),
            "fail_closed": self.fail_closed,
        }


class MarketSessionResourcePolicy:
    """Resource gate for lab and research workloads keyed by US equity session state.

    The policy is pure and does not touch brokers, DB sessions, or orders. Missing,
    invalid, or contradictory session inputs return a fail-closed decision.
    """

    def __init__(
        self,
        *,
        session_provider: SessionProvider | None = market_session_status,
        open_session_allowlist: Iterable[str] = DEFAULT_OPEN_SESSION_ALLOWLIST,
        closed_session_allowlist: Iterable[str] = DEFAULT_CLOSED_SESSION_ALLOWLIST,
        prohibited_resources: Iterable[str] = PROHIBITED_RESOURCES,
    ) -> None:
        self.session_provider = session_provider
        self.open_session_allowlist = _normalize_static_resources(open_session_allowlist)
        self.closed_session_allowlist = _normalize_static_resources(closed_session_allowlist)
        self.prohibited_resources = _normalize_static_resources(prohibited_resources)
        self.known_resources = (
            KNOWN_RESOURCES
            | self.open_session_allowlist
            | self.closed_session_allowlist
            | self.prohibited_resources
        )

    def evaluate(
        self,
        requested_resources: Iterable[str],
        *,
        market_session: Mapping[str, object] | None = None,
        now: datetime | None = None,
    ) -> ResourcePolicyDecision:
        resources, resource_errors = _normalize_requested_resources(requested_resources)
        session, session_errors = self._resolve_session(market_session, now)
        if resource_errors or session_errors:
            reasons = tuple([*resource_errors, *session_errors, "fail_closed"])
            return _decision(
                decision="RESOURCE_POLICY_FAIL_CLOSED",
                allowed_resources=(),
                blocked_resources=resources,
                reason_codes=reasons,
                block_reasons={resource: reasons for resource in resources},
                market_session=session,
                fail_closed=True,
            )

        session_open = session["regular_session_open"] is True
        allowlist = self.open_session_allowlist if session_open else self.closed_session_allowlist
        allowed: list[str] = []
        blocked: list[str] = []
        block_reasons: dict[str, tuple[str, ...]] = {}

        for resource in resources:
            reasons = self._block_reasons(resource, allowlist, session_open)
            if reasons:
                blocked.append(resource)
                block_reasons[resource] = reasons
            else:
                allowed.append(resource)

        reason_codes = _dedupe_reason_codes(block_reasons)
        if blocked and allowed:
            decision = "RESOURCE_POLICY_PARTIAL_ALLOW"
        elif blocked:
            decision = "RESOURCE_POLICY_BLOCKED"
        else:
            decision = "RESOURCE_POLICY_ALLOW"
            reason_codes = ("allowed",)

        return _decision(
            decision=decision,
            allowed_resources=tuple(allowed),
            blocked_resources=tuple(blocked),
            reason_codes=reason_codes,
            block_reasons=block_reasons,
            market_session=session,
            fail_closed=False,
        )

    def _resolve_session(
        self,
        market_session: Mapping[str, object] | None,
        now: datetime | None,
    ) -> tuple[dict[str, object], tuple[str, ...]]:
        if market_session is None:
            if self.session_provider is None:
                return {}, ("market_session_missing",)
            try:
                market_session = self.session_provider(now)
            except Exception as exc:  # noqa: BLE001 - provider failure must fail closed.
                return {}, (f"market_session_provider_error:{type(exc).__name__}",)

        session = dict(market_session)
        errors = _validate_session(session)
        return session, errors

    def _block_reasons(
        self,
        resource: str,
        allowlist: frozenset[str],
        session_open: bool,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if resource not in self.known_resources:
            reasons.append(f"unknown_resource:{resource}")
        if resource in self.prohibited_resources:
            reasons.append(f"prohibited_resource:{resource}")
        if session_open and resource in SESSION_SENSITIVE_RESOURCES:
            reasons.append("regular_session_resource_protected")
        if resource not in allowlist:
            reasons.append(f"not_in_session_allowlist:{resource}")
        return tuple(reasons)


def _decision(
    *,
    decision: str,
    allowed_resources: tuple[str, ...],
    blocked_resources: tuple[str, ...],
    reason_codes: tuple[str, ...],
    block_reasons: dict[str, tuple[str, ...]],
    market_session: Mapping[str, object],
    fail_closed: bool,
) -> ResourcePolicyDecision:
    return ResourcePolicyDecision(
        decision=decision,
        allowed_resources=tuple(sorted(allowed_resources)),
        blocked_resources=tuple(sorted(blocked_resources)),
        reason_codes=tuple(reason_codes),
        block_reasons={key: tuple(value) for key, value in sorted(block_reasons.items())},
        market_session=dict(market_session),
        fail_closed=fail_closed,
    )


def _validate_session(session: Mapping[str, object]) -> tuple[str, ...]:
    errors: list[str] = []
    market = session.get("market")
    state = session.get("state")
    is_open = session.get("regular_session_open")

    if market != SUPPORTED_MARKET:
        errors.append("market_session_unsupported_or_missing")
    if not isinstance(is_open, bool):
        errors.append("regular_session_open_missing_or_invalid")
    if not isinstance(state, str) or not state:
        errors.append("market_session_state_missing_or_invalid")
    elif is_open is True and state != OPEN_STATE:
        errors.append("market_session_open_state_mismatch")
    elif is_open is False and state not in CLOSED_STATES:
        errors.append("market_session_closed_state_unrecognized")
    return tuple(errors)


def _normalize_requested_resources(resources: Iterable[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    raw_resources: Iterable[Any]
    if isinstance(resources, str):
        raw_resources = (resources,)
    else:
        raw_resources = resources

    normalized: list[str] = []
    errors: list[str] = []
    try:
        iterator = iter(raw_resources)
    except TypeError:
        return (), ("requested_resources_not_iterable",)

    for raw in iterator:
        if not isinstance(raw, str):
            errors.append("requested_resource_not_string")
            continue
        value = raw.strip().lower()
        if not value:
            errors.append("requested_resource_empty")
            continue
        if value not in normalized:
            normalized.append(value)
    return tuple(normalized), tuple(errors)


def _normalize_static_resources(resources: Iterable[str]) -> frozenset[str]:
    normalized, errors = _normalize_requested_resources(resources)
    if errors:
        raise ValueError(";".join(errors))
    return frozenset(normalized)


def _dedupe_reason_codes(block_reasons: Mapping[str, tuple[str, ...]]) -> tuple[str, ...]:
    seen: set[str] = set()
    reason_codes: list[str] = []
    for reasons in block_reasons.values():
        for reason in reasons:
            if reason not in seen:
                seen.add(reason)
                reason_codes.append(reason)
    return tuple(reason_codes)
