from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from tradeo.research.quant_validation import (
    profit_factor,
    select_nonoverlapping_events,
    tiered_round_trip_cost_r,
    triple_barrier_outcome,
)

LANE_CONTRACT_VERSION = "intraday-research-v1"
DEFAULT_COST_MULTIPLIERS = (1.0, 2.0, 3.0)


@dataclass(frozen=True, slots=True)
class IntradayResearchConfig:
    cost_multipliers: tuple[float, ...] = DEFAULT_COST_MULTIPLIERS
    min_events: int = 1
    min_net_expectancy_r: float = 0.0
    require_stratified_null: bool = True
    require_all_cost_stress_positive: bool = True
    participation_rate: float = 0.005
    commission_bps: float = 0.5

    def __post_init__(self) -> None:
        if not self.cost_multipliers:
            raise ValueError("cost_multipliers must not be empty")
        clean = tuple(float(value) for value in self.cost_multipliers)
        if any(value <= 0 or not isfinite(value) for value in clean):
            raise ValueError("cost_multipliers must be finite positive values")
        object.__setattr__(self, "cost_multipliers", clean)
        if self.min_events < 1:
            raise ValueError("min_events must be >= 1")


@dataclass(frozen=True, slots=True)
class IntradayResearchEvent:
    symbol: str
    session_id: str
    signal_index: int
    side: int | str
    stop_price: float
    target_price: float
    max_bars: int
    timeframe: str = "5m"
    event_id: str | None = None
    bucket: str | None = None
    session_bucket: str | None = None
    liquidity_bucket: str | None = None
    rvol_bucket: str | None = None
    gap_bucket: str | None = None
    regime_bucket: str | None = None
    avg_dollar_volume: float = 0.0
    entry_price: float | None = None
    base_cost_r: float | None = None
    available_data_cutoff_index: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "IntradayResearchEvent":
        intraday = _as_mapping(raw.get("intraday"))
        metadata = _as_mapping(raw.get("metadata"))
        intraday_meta = _as_mapping(metadata.get("intraday"))
        source = {**intraday_meta, **intraday, **raw}
        return cls(
            symbol=str(_first_present(source.get("symbol"), "")).upper().strip(),
            session_id=str(_first_present(source.get("session_id"), source.get("session"), "")).strip(),
            signal_index=int(_first_present(source.get("signal_index"), source.get("window_end_index"), source.get("closed_bar_index"), 0)),
            side=_first_present(source.get("side"), "long"),
            stop_price=float(_first_present(source.get("stop_price"), source.get("stop"), 0.0)),
            target_price=float(_first_present(source.get("target_price"), source.get("target"), 0.0)),
            max_bars=int(_first_present(source.get("max_bars"), source.get("forward_bars"), 1)),
            timeframe=str(_first_present(source.get("timeframe"), "5m")),
            event_id=_optional_str(_first_present(source.get("event_id"), source.get("id"), None)),
            bucket=_optional_str(source.get("bucket")),
            session_bucket=_optional_str(source.get("session_bucket")),
            liquidity_bucket=_optional_str(source.get("liquidity_bucket")),
            rvol_bucket=_optional_str(source.get("rvol_bucket")),
            gap_bucket=_optional_str(source.get("gap_bucket")),
            regime_bucket=_optional_str(source.get("regime_bucket")),
            avg_dollar_volume=float(_first_present(source.get("avg_dollar_volume"), source.get("dollar_volume"), 0.0)),
            entry_price=_optional_float(source.get("entry_price")),
            base_cost_r=_optional_float(_first_present(source.get("base_cost_r"), source.get("cost_r"), None)),
            available_data_cutoff_index=_optional_int(
                _first_present(
                    source.get("available_data_cutoff_index"),
                    source.get("data_cutoff_index"),
                    source.get("cutoff_index"),
                    None,
                )
            ),
            metadata=dict(metadata),
        )

    @property
    def side_int(self) -> int:
        if isinstance(self.side, str):
            value = self.side.strip().lower()
            if value in {"long", "buy", "+1", "1"}:
                return 1
            if value in {"short", "sell", "-1"}:
                return -1
        side = int(self.side)
        if side not in (1, -1):
            raise ValueError("side must be long/+1 or short/-1")
        return side

    @property
    def bucket_key(self) -> str:
        if self.bucket:
            return str(self.bucket)
        parts = (
            self.session_bucket or "unknown_session",
            self.liquidity_bucket or "unknown_liquidity",
            self.rvol_bucket or "unknown_rvol",
            self.gap_bucket or "unknown_gap",
            self.regime_bucket or "unknown_regime",
        )
        return "|".join(parts)

    @property
    def resolved_event_id(self) -> str:
        if self.event_id:
            return self.event_id
        return f"{self.symbol}:{self.session_id}:{self.timeframe}:{self.signal_index}"


@dataclass(frozen=True, slots=True)
class IntradayResearchOutcome:
    event: IntradayResearchEvent
    status: str
    reason: str
    gross_r: float | None
    base_cost_r: float | None
    net_r_by_cost: dict[float, float]
    entry_index: int | None
    exit_index: int | None
    bars_held: int
    mfe_r: float | None
    mae_r: float | None
    reject_reason_codes: tuple[str, ...] = ()

    @property
    def eligible_evidence(self) -> bool:
        return self.status == "ok" and not self.reject_reason_codes and self.gross_r is not None

    @property
    def span_start(self) -> int:
        return int(self.entry_index if self.entry_index is not None else self.event.signal_index)

    @property
    def span_end(self) -> int:
        return int(self.exit_index if self.exit_index is not None else self.span_start)

    @property
    def bucket_key(self) -> str:
        return self.event.bucket_key


@dataclass(frozen=True, slots=True)
class IntradayCostStressResult:
    multiplier: float
    n: int
    expectancy_r: float
    profit_factor: float
    win_rate: float
    null_expectancy_r: float | None
    edge_vs_null_r: float | None


@dataclass(frozen=True, slots=True)
class IntradayResearchReport:
    contract_version: str
    accepted: bool
    reason_codes: tuple[str, ...]
    outcomes: tuple[IntradayResearchOutcome, ...]
    evidence_outcomes: tuple[IntradayResearchOutcome, ...]
    gross_expectancy_r: float | None
    cost_stress: dict[float, IntradayCostStressResult]
    null_baseline: dict[float, dict[str, Any]]
    bucket_counts: dict[str, int]
    label_counts: dict[str, int]
    deoverlap: dict[str, int]

    @property
    def net_expectancy_r(self) -> float | None:
        result = self.cost_stress.get(1.0)
        return result.expectancy_r if result is not None else None

    def to_intraday_metadata(self) -> dict[str, Any]:
        return {
            "intraday": {
                "research_contract_version": self.contract_version,
                "accepted": self.accepted,
                "reason_codes": list(self.reason_codes),
                "gross_expectancy_r": self.gross_expectancy_r,
                "net_expectancy_r": self.net_expectancy_r,
                "bucket_counts": self.bucket_counts,
                "label_counts": self.label_counts,
                "deoverlap": self.deoverlap,
                "cost_stress": {
                    str(multiplier): {
                        "n": result.n,
                        "expectancy_r": result.expectancy_r,
                        "profit_factor": result.profit_factor,
                        "win_rate": result.win_rate,
                        "null_expectancy_r": result.null_expectancy_r,
                        "edge_vs_null_r": result.edge_vs_null_r,
                    }
                    for multiplier, result in self.cost_stress.items()
                },
            }
        }


class IntradayResearchLane:
    """Pure intraday research evaluator.

    The lane takes in-memory bars/events only. It never reads DB state, broker
    state, settings, or daily Research artifacts.
    """

    def __init__(self, config: IntradayResearchConfig | None = None) -> None:
        self.config = config or IntradayResearchConfig()

    def evaluate(
        self,
        events: Iterable[IntradayResearchEvent | Mapping[str, Any]],
        bars_by_symbol_session: Mapping[Any, Any],
        *,
        null_events: Iterable[IntradayResearchEvent | Mapping[str, Any]] | None = None,
    ) -> IntradayResearchReport:
        event_list = tuple(_coerce_event(event) for event in events)
        null_event_list = tuple(_coerce_event(event) for event in null_events or ())

        outcomes = tuple(self._label_events(event_list, bars_by_symbol_session))
        evidence, overlap_dropped = _deoverlap_symbol_session(outcomes)
        null_outcomes = tuple(self._label_events(null_event_list, bars_by_symbol_session))
        null_evidence, _ = _deoverlap_symbol_session(null_outcomes)

        cost_stress, null_baseline, missing_buckets = _cost_stress(
            evidence,
            null_evidence,
            cost_multipliers=self.config.cost_multipliers,
        )
        reasons = _gate_reasons(
            outcomes=outcomes,
            evidence=evidence,
            null_evidence=null_evidence,
            cost_stress=cost_stress,
            missing_buckets=missing_buckets,
            config=self.config,
        )
        gross_values = [float(outcome.gross_r) for outcome in evidence if outcome.gross_r is not None]
        bucket_counts = Counter(outcome.bucket_key for outcome in evidence)
        label_counts = Counter(_label_reason(outcome.reason) for outcome in evidence)

        return IntradayResearchReport(
            contract_version=LANE_CONTRACT_VERSION,
            accepted=not reasons,
            reason_codes=tuple(reasons),
            outcomes=outcomes,
            evidence_outcomes=evidence,
            gross_expectancy_r=_mean_or_none(gross_values),
            cost_stress=cost_stress,
            null_baseline=null_baseline,
            bucket_counts=dict(sorted(bucket_counts.items())),
            label_counts=dict(sorted(label_counts.items())),
            deoverlap={
                "input_events": len(event_list),
                "labeled_events": len(outcomes),
                "eligible_before_deoverlap": sum(outcome.eligible_evidence for outcome in outcomes),
                "kept": len(evidence),
                "dropped_symbol_session_overlap": overlap_dropped,
            },
        )

    def _label_events(
        self,
        events: Sequence[IntradayResearchEvent],
        bars_by_symbol_session: Mapping[Any, Any],
    ) -> list[IntradayResearchOutcome]:
        outcomes: list[IntradayResearchOutcome] = []
        for event in events:
            early_rejects = _event_rejects(event)
            bars = _bars_for_event(bars_by_symbol_session, event)
            if bars is None:
                outcomes.append(_rejected_outcome(event, "no_bars", early_rejects + ("missing_bars",)))
                continue
            arrays = _ohlc_arrays(bars)
            if early_rejects:
                outcomes.append(_rejected_outcome(event, "rejected", early_rejects))
                continue
            try:
                out = triple_barrier_outcome(
                    arrays["open"],
                    arrays["high"],
                    arrays["low"],
                    arrays["close"],
                    signal_index=event.signal_index,
                    side=event.side_int,
                    stop_price=event.stop_price,
                    target_price=event.target_price,
                    max_bars=event.max_bars,
                    entry_price=event.entry_price,
                    round_trip_cost_R=0.0,
                )
            except (IndexError, ValueError, TypeError) as exc:
                outcomes.append(_rejected_outcome(event, f"invalid_event:{exc}", ("invalid_event",)))
                continue
            base_cost = _base_cost_r(event, out)
            reject_codes: tuple[str, ...] = ()
            if out["status"] != "ok":
                reject_codes = (str(out["status"]), str(out["reason"]))
            gross_r = _finite_or_none(out.get("R"))
            net = {
                multiplier: float(gross_r - base_cost * multiplier)
                for multiplier in self.config.cost_multipliers
                if gross_r is not None
            }
            outcomes.append(
                IntradayResearchOutcome(
                    event=event,
                    status=str(out["status"]),
                    reason=str(out["reason"]),
                    gross_r=gross_r,
                    base_cost_r=base_cost,
                    net_r_by_cost=net,
                    entry_index=_optional_int(out.get("entry_index")),
                    exit_index=_optional_int(out.get("exit_index")),
                    bars_held=int(out.get("bars_held") or 0),
                    mfe_r=_finite_or_none(out.get("mfe_R")),
                    mae_r=_finite_or_none(out.get("mae_R")),
                    reject_reason_codes=reject_codes,
                )
            )
        return outcomes


def evaluate_intraday_research(
    events: Iterable[IntradayResearchEvent | Mapping[str, Any]],
    bars_by_symbol_session: Mapping[Any, Any],
    *,
    null_events: Iterable[IntradayResearchEvent | Mapping[str, Any]] | None = None,
    config: IntradayResearchConfig | None = None,
) -> IntradayResearchReport:
    return IntradayResearchLane(config).evaluate(
        events,
        bars_by_symbol_session,
        null_events=null_events,
    )


def _coerce_event(raw: IntradayResearchEvent | Mapping[str, Any]) -> IntradayResearchEvent:
    if isinstance(raw, IntradayResearchEvent):
        return raw
    if isinstance(raw, Mapping):
        return IntradayResearchEvent.from_mapping(raw)
    raise TypeError("events must be IntradayResearchEvent or mapping rows")


def _event_rejects(event: IntradayResearchEvent) -> tuple[str, ...]:
    reasons: list[str] = []
    if not event.symbol:
        reasons.append("missing_symbol")
    if not event.session_id:
        reasons.append("missing_session_id")
    if event.signal_index < 0:
        reasons.append("negative_signal_index")
    if event.max_bars <= 0:
        reasons.append("max_bars_le_0")
    if event.available_data_cutoff_index is not None and event.available_data_cutoff_index > event.signal_index:
        reasons.append("lookahead_detected")
    if not (isfinite(event.stop_price) and isfinite(event.target_price)):
        reasons.append("non_finite_barrier")
    if event.stop_price == event.target_price:
        reasons.append("flat_barriers")
    try:
        event.side_int
    except (TypeError, ValueError):
        reasons.append("invalid_side")
    return tuple(reasons)


def _rejected_outcome(
    event: IntradayResearchEvent,
    reason: str,
    reject_reason_codes: tuple[str, ...],
) -> IntradayResearchOutcome:
    return IntradayResearchOutcome(
        event=event,
        status="rejected",
        reason=reason,
        gross_r=None,
        base_cost_r=None,
        net_r_by_cost={},
        entry_index=None,
        exit_index=None,
        bars_held=0,
        mfe_r=None,
        mae_r=None,
        reject_reason_codes=reject_reason_codes,
    )


def _bars_for_event(
    bars_by_symbol_session: Mapping[Any, Any],
    event: IntradayResearchEvent,
) -> Any | None:
    keys = (
        (event.symbol, event.session_id),
        (event.symbol.upper(), event.session_id),
        f"{event.symbol}:{event.session_id}",
        f"{event.symbol.upper()}:{event.session_id}",
        event.symbol,
        event.symbol.upper(),
    )
    for key in keys:
        if key in bars_by_symbol_session:
            value = bars_by_symbol_session[key]
            if isinstance(value, Mapping) and event.session_id in value:
                return value[event.session_id]
            return value
    by_symbol = bars_by_symbol_session.get(event.symbol) or bars_by_symbol_session.get(event.symbol.upper())
    if isinstance(by_symbol, Mapping):
        return by_symbol.get(event.session_id)
    return None


def _ohlc_arrays(bars: Any) -> dict[str, np.ndarray]:
    if isinstance(bars, pd.DataFrame):
        frame = bars.copy()
        frame.columns = [str(column).lower().replace(" ", "_") for column in frame.columns]
        required = ("open", "high", "low", "close")
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"missing OHLC columns: {missing}")
        return {
            column: pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
            for column in required
        }
    if isinstance(bars, Mapping):
        return {
            "open": np.asarray(_first_present(bars.get("open"), bars.get("open_")), dtype=float),
            "high": np.asarray(bars["high"], dtype=float),
            "low": np.asarray(bars["low"], dtype=float),
            "close": np.asarray(bars["close"], dtype=float),
        }
    raise TypeError("bars must be a pandas DataFrame or OHLC mapping")


def _base_cost_r(event: IntradayResearchEvent, outcome: Mapping[str, Any]) -> float:
    if event.base_cost_r is not None:
        return max(0.0, float(event.base_cost_r))
    entry = _finite_or_none(outcome.get("entry_price"))
    stop = float(event.stop_price)
    if entry is None:
        return 0.0
    risk = abs(entry - stop)
    if risk <= 0 or not isfinite(risk):
        return 0.0
    return tiered_round_trip_cost_r(
        entry_price=entry,
        risk_per_share=risk,
        avg_dollar_volume=event.avg_dollar_volume,
        participation_rate=0.005,
        multiplier=1.0,
        commission_bps=0.5,
    )


def _deoverlap_symbol_session(
    outcomes: Sequence[IntradayResearchOutcome],
) -> tuple[tuple[IntradayResearchOutcome, ...], int]:
    eligible = [outcome for outcome in outcomes if outcome.eligible_evidence]
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    for idx, outcome in enumerate(eligible):
        groups[(outcome.event.symbol, outcome.event.session_id)].append(idx)

    kept_positions: set[int] = set()
    for positions in groups.values():
        starts = [eligible[pos].span_start for pos in positions]
        ends = [eligible[pos].span_end for pos in positions]
        keep_local = select_nonoverlapping_events(starts, ends)
        kept_positions.update(positions[int(local)] for local in keep_local)

    kept = tuple(eligible[idx] for idx in sorted(kept_positions))
    return kept, len(eligible) - len(kept)


def _cost_stress(
    evidence: Sequence[IntradayResearchOutcome],
    null_evidence: Sequence[IntradayResearchOutcome],
    *,
    cost_multipliers: Sequence[float],
) -> tuple[dict[float, IntradayCostStressResult], dict[float, dict[str, Any]], tuple[str, ...]]:
    result: dict[float, IntradayCostStressResult] = {}
    baseline: dict[float, dict[str, Any]] = {}
    missing_all: set[str] = set()
    real_bucket_counts = Counter(outcome.bucket_key for outcome in evidence)
    null_by_bucket: dict[str, list[IntradayResearchOutcome]] = defaultdict(list)
    for outcome in null_evidence:
        null_by_bucket[outcome.bucket_key].append(outcome)

    for multiplier in cost_multipliers:
        values = np.asarray([outcome.net_r_by_cost[multiplier] for outcome in evidence], dtype=float)
        null_bucket_means: dict[str, float] = {}
        missing = []
        for bucket, count in real_bucket_counts.items():
            null_values = [
                outcome.net_r_by_cost[multiplier]
                for outcome in null_by_bucket.get(bucket, [])
                if multiplier in outcome.net_r_by_cost
            ]
            if not null_values:
                missing.append(bucket)
                continue
            null_bucket_means[bucket] = float(np.mean(null_values))
        missing_all.update(missing)
        null_expectancy = None
        edge = None
        if real_bucket_counts and not missing:
            weighted_sum = sum(
                null_bucket_means[bucket] * count
                for bucket, count in real_bucket_counts.items()
            )
            null_expectancy = float(weighted_sum / sum(real_bucket_counts.values()))
            edge = float(values.mean() - null_expectancy) if values.size else None
        baseline[multiplier] = {
            "method": "stratified_by_intraday_bucket_v1",
            "bucket_counts": dict(sorted(real_bucket_counts.items())),
            "null_bucket_means": dict(sorted(null_bucket_means.items())),
            "missing_buckets": tuple(sorted(missing)),
            "expectancy_r": null_expectancy,
        }
        result[multiplier] = IntradayCostStressResult(
            multiplier=float(multiplier),
            n=int(values.size),
            expectancy_r=float(values.mean()) if values.size else float("nan"),
            profit_factor=profit_factor(values) if values.size else float("nan"),
            win_rate=float(np.mean(values > 0.0)) if values.size else float("nan"),
            null_expectancy_r=null_expectancy,
            edge_vs_null_r=edge,
        )
    return result, baseline, tuple(sorted(missing_all))


def _gate_reasons(
    *,
    outcomes: Sequence[IntradayResearchOutcome],
    evidence: Sequence[IntradayResearchOutcome],
    null_evidence: Sequence[IntradayResearchOutcome],
    cost_stress: Mapping[float, IntradayCostStressResult],
    missing_buckets: Sequence[str],
    config: IntradayResearchConfig,
) -> list[str]:
    reasons: list[str] = []
    all_rejects = [code for outcome in outcomes for code in outcome.reject_reason_codes]
    if "lookahead_detected" in all_rejects:
        reasons.append("lookahead_detected")
    if len(evidence) < config.min_events:
        reasons.append("insufficient_intraday_events")
    if config.require_stratified_null:
        if not null_evidence:
            reasons.append("missing_stratified_null_baseline")
        if missing_buckets:
            reasons.append("missing_null_bucket")

    gross = _mean_or_none([float(outcome.gross_r) for outcome in evidence if outcome.gross_r is not None])
    one_x = cost_stress.get(1.0)
    if one_x is not None:
        if one_x.expectancy_r <= config.min_net_expectancy_r:
            reasons.append("net_ev_below_threshold_1x")
        if gross is not None and gross > 0.0 and one_x.expectancy_r <= 0.0:
            reasons.append("gross_ev_only")

    if config.require_all_cost_stress_positive:
        for multiplier, stress in sorted(cost_stress.items()):
            if stress.expectancy_r <= config.min_net_expectancy_r:
                suffix = _multiplier_suffix(multiplier)
                code = f"cost_stress_{suffix}_nonpositive"
                if code not in reasons:
                    reasons.append(code)

    for multiplier, stress in sorted(cost_stress.items()):
        if stress.edge_vs_null_r is not None and stress.edge_vs_null_r <= 0.0:
            reasons.append(f"fails_stratified_null_baseline_{_multiplier_suffix(multiplier)}")

    return list(dict.fromkeys(reasons))


def _label_reason(reason: str) -> str:
    return "time_stop" if reason == "time" else reason


def _multiplier_suffix(multiplier: float) -> str:
    return f"{int(multiplier)}x" if float(multiplier).is_integer() else f"{multiplier:g}x"


def _mean_or_none(values: Sequence[float]) -> float | None:
    finite = [float(value) for value in values if isfinite(float(value))]
    if not finite:
        return None
    return float(np.mean(finite))


def _finite_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


__all__ = [
    "LANE_CONTRACT_VERSION",
    "IntradayCostStressResult",
    "IntradayResearchConfig",
    "IntradayResearchEvent",
    "IntradayResearchLane",
    "IntradayResearchOutcome",
    "IntradayResearchReport",
    "evaluate_intraday_research",
]
