from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any, Iterable, Literal, Mapping

CandidateStatus = Literal["shadow", "paper_eligible", "blocked", "expired"]

ACCEPTED_STATUSES: set[str] = {"shadow", "paper_eligible"}
DEFAULT_TIMEFRAME = "5m"


@dataclass(frozen=True, slots=True)
class IntradayCandidateRules:
    """Hard gates for already-computed intraday matches.

    The builder is deliberately pure: callers hand in current matches,
    session/symbol state and known exposure keys; no DB, broker or scanner is
    touched here.
    """

    min_dollar_volume: float = 1_000_000.0
    max_spread_bps: float = 50.0
    max_stale_seconds: int = 900
    max_candidates_per_symbol: int = 1
    default_expiry_bars: int = 2
    min_expiry_bars: int = 1
    max_expiry_bars: int = 3
    paper_enabled: bool = False
    require_flat_plan: bool = True

    @classmethod
    def from_settings(cls, settings: Any, **overrides: Any) -> "IntradayCandidateRules":
        values = {
            "min_dollar_volume": float(getattr(settings, "intraday_min_dollar_volume", cls.min_dollar_volume)),
            "max_spread_bps": float(getattr(settings, "intraday_max_spread_bps", cls.max_spread_bps)),
            "paper_enabled": bool(getattr(settings, "intraday_paper_enabled", False)),
            "max_candidates_per_symbol": int(
                getattr(settings, "intraday_max_trades_per_symbol", 0) or cls.max_candidates_per_symbol
            ),
        }
        values.update(overrides)
        return cls(**values)


@dataclass(slots=True)
class IntradayCandidate:
    symbol: str
    pattern: str
    side: str
    timeframe: str
    entry: float | None
    stop: float | None
    target: float | None
    score: float
    status: CandidateStatus
    reason_codes: tuple[str, ...]
    session_id: str | None
    closed_bar_at: datetime | None
    expires_at: datetime | None
    expiry_bars: int
    flat_by: datetime | None
    bucket: str | None
    exposure_key: str
    spread_bps: float | None
    dollar_volume: float | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return self.status in ACCEPTED_STATUSES

    @property
    def reason_code(self) -> str:
        return self.reason_codes[0] if self.reason_codes else "accepted"

    def to_intraday_metadata(self) -> dict[str, Any]:
        return {
            "intraday": {
                "session_id": self.session_id,
                "status": self.status,
                "reason_codes": list(self.reason_codes),
                "closed_bar_at": _iso(self.closed_bar_at),
                "expires_at": _iso(self.expires_at),
                "expiry_bars": self.expiry_bars,
                "flat_by": _iso(self.flat_by),
                "bucket": self.bucket,
                "exposure_key": self.exposure_key,
                "spread_bps": self.spread_bps,
                "dollar_volume": self.dollar_volume,
            }
        }


@dataclass(frozen=True, slots=True)
class IntradayCandidateBatch:
    candidates: tuple[IntradayCandidate, ...]
    reason_counts: dict[str, int]

    @property
    def accepted(self) -> tuple[IntradayCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.accepted)

    @property
    def blocked(self) -> tuple[IntradayCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.status == "blocked")

    @property
    def expired(self) -> tuple[IntradayCandidate, ...]:
        return tuple(candidate for candidate in self.candidates if candidate.status == "expired")


@dataclass(slots=True)
class _NormalizedCandidate:
    raw: dict[str, Any]
    symbol: str
    pattern: str
    side: str
    timeframe: str
    entry: float | None
    stop: float | None
    target: float | None
    score: float
    session_id: str | None
    closed_bar: bool
    closed_bar_at: datetime | None
    bucket: str | None
    allowed_buckets: tuple[str, ...]
    spread_bps: float | None
    dollar_volume: float | None
    cooldown_until: datetime | None
    exposure_key: str
    expiry_bars: int
    expires_at: datetime | None
    flat_by: datetime | None
    paper_allowed: bool
    metadata: dict[str, Any]


class IntradayCandidateBuilder:
    """Build auditable intraday candidates from already-ranked matches."""

    def __init__(self, rules: IntradayCandidateRules | None = None) -> None:
        self.rules = rules or IntradayCandidateRules()

    def build(
        self,
        matches: Iterable[Any],
        *,
        now: datetime | None = None,
        session_id: str | int | None = None,
        current_bucket: str | None = None,
        flat_by: datetime | str | None = None,
        existing_exposure_keys: Iterable[str] | None = None,
        symbol_states: Mapping[str, Any] | None = None,
    ) -> IntradayCandidateBatch:
        now_utc = _as_utc(now or datetime.now(timezone.utc))
        flat_by_utc = _as_utc(flat_by) if flat_by is not None else None
        reserved_exposures = {str(key) for key in (existing_exposure_keys or []) if str(key)}
        accepted_per_symbol: Counter[str] = Counter()
        reason_counts: Counter[str] = Counter()
        candidates: list[IntradayCandidate] = []

        for item in matches:
            raw = _mapping_from_any(item)
            normalized = self._normalize(
                raw,
                session_id=str(session_id) if session_id not in (None, "") else None,
                current_bucket=current_bucket,
                flat_by=flat_by_utc,
                symbol_state=_state_for_symbol(symbol_states, raw),
            )
            reason_codes = self._reason_codes(
                normalized,
                now=now_utc,
                accepted_per_symbol=accepted_per_symbol,
                reserved_exposures=reserved_exposures,
            )
            status = self._status(normalized, reason_codes)
            candidate = IntradayCandidate(
                symbol=normalized.symbol,
                pattern=normalized.pattern,
                side=normalized.side,
                timeframe=normalized.timeframe,
                entry=normalized.entry,
                stop=normalized.stop,
                target=normalized.target,
                score=normalized.score,
                status=status,
                reason_codes=tuple(reason_codes),
                session_id=normalized.session_id,
                closed_bar_at=normalized.closed_bar_at,
                expires_at=normalized.expires_at,
                expiry_bars=normalized.expiry_bars,
                flat_by=normalized.flat_by,
                bucket=normalized.bucket,
                exposure_key=normalized.exposure_key,
                spread_bps=normalized.spread_bps,
                dollar_volume=normalized.dollar_volume,
                metadata=self._metadata(normalized, status, reason_codes),
            )
            candidates.append(candidate)
            if candidate.accepted:
                accepted_per_symbol[candidate.symbol] += 1
                reserved_exposures.add(candidate.exposure_key)
            for reason in reason_codes or ("accepted",):
                reason_counts[reason] += 1

        return IntradayCandidateBatch(
            candidates=tuple(candidates),
            reason_counts=dict(sorted(reason_counts.items())),
        )

    def _normalize(
        self,
        raw: dict[str, Any],
        *,
        session_id: str | None,
        current_bucket: str | None,
        flat_by: datetime | None,
        symbol_state: Mapping[str, Any],
    ) -> _NormalizedCandidate:
        intraday = _as_mapping(_first_present(raw.get("intraday"), _nested(raw, "metadata", "intraday")))
        metrics = _as_mapping(raw.get("metrics"))
        features = _as_mapping(_first_present(raw.get("features"), metrics.get("features")))
        entry_variant = _as_mapping(_first_present(raw.get("entry_variant"), metrics.get("entry_variant")))

        symbol = str(_first_present(raw.get("symbol"), metrics.get("symbol"), features.get("symbol"), "")).upper()
        pattern = str(
            _first_present(
                raw.get("pattern"),
                raw.get("pattern_name"),
                raw.get("pattern_key"),
                metrics.get("pattern"),
                metrics.get("pattern_key"),
                "intraday_pattern",
            )
        )
        side = str(_first_present(raw.get("side"), metrics.get("side"), "long")).lower()
        timeframe = str(
            _first_present(raw.get("timeframe"), intraday.get("timeframe"), metrics.get("timeframe"), DEFAULT_TIMEFRAME)
        )
        closed_bar_at = _as_utc(
            _first_present(
                raw.get("closed_bar_at"),
                raw.get("bar_closed_at"),
                raw.get("window_end"),
                intraday.get("closed_bar_at"),
                intraday.get("window_end"),
                metrics.get("closed_bar_at"),
                metrics.get("window_end"),
            )
        )
        closed_bar = _as_bool(
            _first_present(raw.get("closed_bar"), intraday.get("closed_bar"), metrics.get("closed_bar")),
            default=closed_bar_at is not None,
        )
        resolved_session_id = str(
            _first_present(session_id, raw.get("session_id"), intraday.get("session_id"), metrics.get("session_id"), "")
        ) or None
        resolved_flat_by = _as_utc(
            _first_present(
                flat_by,
                raw.get("flat_by"),
                raw.get("must_flat_by"),
                intraday.get("flat_by"),
                intraday.get("must_flat_by"),
                metrics.get("flat_by"),
            )
        )
        expiry_bars = self._expiry_bars(_first_present(raw.get("expiry_bars"), intraday.get("expiry_bars")))
        expires_at = (
            closed_bar_at + _timeframe_delta(timeframe) * expiry_bars
            if closed_bar_at is not None
            else None
        )
        bucket = str(
            _first_present(
                current_bucket,
                raw.get("bucket"),
                raw.get("session_bucket"),
                intraday.get("bucket"),
                metrics.get("session_bucket"),
                "",
            )
        ) or None
        allowed_buckets = _string_tuple(
            _first_present(
                raw.get("allowed_buckets"),
                raw.get("allowed_session_buckets"),
                intraday.get("allowed_session_buckets"),
                metrics.get("allowed_session_buckets"),
                entry_variant.get("allowed_session_buckets"),
            )
        )
        spread_bps = _spread_bps(raw, intraday, metrics, features)
        dollar_volume = _safe_float(
            _first_present(
                raw.get("dollar_volume"),
                raw.get("avg_dollar_volume"),
                intraday.get("dollar_volume"),
                metrics.get("dollar_volume"),
                metrics.get("avg_dollar_volume"),
                features.get("dollar_volume"),
                features.get("avg_dollar_volume"),
            )
        )
        cooldown_until = _as_utc(
            _first_present(raw.get("cooldown_until"), intraday.get("cooldown_until"), symbol_state.get("cooldown_until"))
        )
        variant = str(
            _first_present(
                raw.get("entry_variant_id"),
                intraday.get("entry_variant_id"),
                metrics.get("entry_variant_id"),
                entry_variant.get("id"),
                raw.get("entry_variant"),
                "",
            )
        )
        exposure_key = str(
            _first_present(
                raw.get("exposure_key"),
                intraday.get("exposure_key"),
                _default_exposure_key(symbol, pattern, timeframe, side, variant),
            )
        )
        metadata = dict(_as_mapping(raw.get("metadata")))
        return _NormalizedCandidate(
            raw=raw,
            symbol=symbol,
            pattern=pattern,
            side=side,
            timeframe=timeframe,
            entry=_safe_float(raw.get("entry")),
            stop=_safe_float(raw.get("stop")),
            target=_safe_float(raw.get("target")),
            score=_safe_float(_first_present(raw.get("score"), raw.get("composite_score"), metrics.get("score"))) or 0.0,
            session_id=resolved_session_id,
            closed_bar=closed_bar,
            closed_bar_at=closed_bar_at,
            bucket=bucket,
            allowed_buckets=allowed_buckets,
            spread_bps=spread_bps,
            dollar_volume=dollar_volume,
            cooldown_until=cooldown_until,
            exposure_key=exposure_key,
            expiry_bars=expiry_bars,
            expires_at=expires_at,
            flat_by=resolved_flat_by,
            paper_allowed=_as_bool(_first_present(raw.get("paper_allowed"), intraday.get("paper_allowed")), default=True),
            metadata=metadata,
        )

    def _reason_codes(
        self,
        candidate: _NormalizedCandidate,
        *,
        now: datetime,
        accepted_per_symbol: Counter[str],
        reserved_exposures: set[str],
    ) -> list[str]:
        reasons: list[str] = []
        if not candidate.session_id:
            reasons.append("missing_session")
        if not candidate.closed_bar_at:
            reasons.append("missing_closed_bar_timestamp")
        elif not candidate.closed_bar:
            reasons.append("bar_not_closed")
        if self.rules.require_flat_plan:
            if not candidate.flat_by:
                reasons.append("missing_flat_plan")
            elif candidate.closed_bar_at and candidate.flat_by <= candidate.closed_bar_at:
                reasons.append("flat_plan_elapsed")
        if candidate.expires_at is not None and now >= candidate.expires_at:
            reasons.append("expired")
        elif (
            candidate.closed_bar_at is not None
            and self.rules.max_stale_seconds > 0
            and now - candidate.closed_bar_at > timedelta(seconds=self.rules.max_stale_seconds)
        ):
            reasons.append("stale_bar")
        if candidate.spread_bps is None:
            reasons.append("missing_spread")
        elif candidate.spread_bps > self.rules.max_spread_bps:
            reasons.append("spread_too_wide")
        if candidate.dollar_volume is None:
            reasons.append("missing_dollar_volume")
        elif candidate.dollar_volume < self.rules.min_dollar_volume:
            reasons.append("low_dollar_volume")
        if candidate.cooldown_until is not None and now < candidate.cooldown_until:
            reasons.append("cooldown_active")
        if candidate.allowed_buckets and candidate.bucket not in candidate.allowed_buckets:
            reasons.append("bucket_not_allowed")
        if candidate.exposure_key in reserved_exposures:
            reasons.append("duplicate_exposure")
        if (
            self.rules.max_candidates_per_symbol >= 0
            and accepted_per_symbol[candidate.symbol] >= self.rules.max_candidates_per_symbol
        ):
            reasons.append("max_per_symbol")
        return _dedupe(reasons)

    def _status(self, candidate: _NormalizedCandidate, reason_codes: list[str]) -> CandidateStatus:
        if "expired" in reason_codes or "flat_plan_elapsed" in reason_codes:
            return "expired"
        if reason_codes:
            return "blocked"
        if self.rules.paper_enabled and candidate.paper_allowed:
            return "paper_eligible"
        return "shadow"

    def _expiry_bars(self, value: Any) -> int:
        requested = _safe_int(value)
        if requested is None:
            requested = self.rules.default_expiry_bars
        return max(self.rules.min_expiry_bars, min(self.rules.max_expiry_bars, requested))

    @staticmethod
    def _metadata(
        candidate: _NormalizedCandidate,
        status: CandidateStatus,
        reason_codes: list[str],
    ) -> dict[str, Any]:
        metadata = dict(candidate.metadata)
        intraday = dict(_as_mapping(metadata.get("intraday")))
        intraday.update(
            {
                "session_id": candidate.session_id,
                "status": status,
                "reason_codes": list(reason_codes),
                "closed_bar_at": _iso(candidate.closed_bar_at),
                "expires_at": _iso(candidate.expires_at),
                "expiry_bars": candidate.expiry_bars,
                "flat_by": _iso(candidate.flat_by),
                "bucket": candidate.bucket,
                "exposure_key": candidate.exposure_key,
                "spread_bps": candidate.spread_bps,
                "dollar_volume": candidate.dollar_volume,
            }
        )
        metadata["intraday"] = intraday
        return metadata


def _mapping_from_any(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    fields = (
        "symbol",
        "pattern",
        "pattern_name",
        "pattern_key",
        "side",
        "timeframe",
        "entry",
        "stop",
        "target",
        "score",
        "composite_score",
        "session_id",
        "closed_bar",
        "closed_bar_at",
        "window_end",
        "flat_by",
        "must_flat_by",
        "bucket",
        "session_bucket",
        "allowed_session_buckets",
        "spread_bps",
        "spread_pct",
        "dollar_volume",
        "avg_dollar_volume",
        "cooldown_until",
        "exposure_key",
        "expiry_bars",
        "paper_allowed",
        "entry_variant_id",
        "entry_variant",
        "metrics",
        "features",
        "metadata",
        "intraday",
    )
    return {name: getattr(value, name) for name in fields if hasattr(value, name)}


def _state_for_symbol(symbol_states: Mapping[str, Any] | None, raw: Mapping[str, Any]) -> Mapping[str, Any]:
    if not symbol_states:
        return {}
    symbol = str(raw.get("symbol") or "").upper()
    state = symbol_states.get(symbol) or symbol_states.get(symbol.lower()) or {}
    return _mapping_from_any(state) if not isinstance(state, Mapping) else state


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _nested(mapping: Mapping[str, Any], *keys: str) -> Any:
    value: Any = mapping
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _as_utc(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off"}
    return bool(value)


def _string_tuple(value: Any) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    if isinstance(value, str):
        parts = re.split(r"[,|]", value)
    elif isinstance(value, Iterable):
        parts = [str(part) for part in value]
    else:
        parts = [str(value)]
    return tuple(part.strip() for part in parts if part and part.strip())


def _spread_bps(*mappings: Mapping[str, Any]) -> float | None:
    spread_bps = _safe_float(_first_present(*(mapping.get("spread_bps") for mapping in mappings)))
    if spread_bps is not None:
        return spread_bps
    spread_pct = _safe_float(_first_present(*(mapping.get("spread_pct") for mapping in mappings)))
    if spread_pct is not None:
        return spread_pct * 10_000.0
    bid = _safe_float(_first_present(*(mapping.get("bid") for mapping in mappings)))
    ask = _safe_float(_first_present(*(mapping.get("ask") for mapping in mappings)))
    if bid is None or ask is None or bid <= 0 or ask <= 0:
        return None
    mid = (bid + ask) / 2.0
    return (ask - bid) / mid * 10_000.0 if mid > 0 else None


def _timeframe_delta(timeframe: str) -> timedelta:
    value = timeframe.strip().lower()
    match = re.fullmatch(r"(\d+)\s*(m|min|minute|minutes|h|hour|hours)", value)
    if not match:
        return timedelta(minutes=5)
    amount = int(match.group(1))
    unit = match.group(2)
    if unit.startswith("h"):
        return timedelta(hours=amount)
    return timedelta(minutes=amount)


def _default_exposure_key(symbol: str, pattern: str, timeframe: str, side: str, variant: str) -> str:
    parts = [symbol.upper(), pattern, timeframe, side.lower(), variant or "default"]
    return "|".join(str(part) for part in parts)


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
