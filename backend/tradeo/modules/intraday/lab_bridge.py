from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite, log1p
from typing import Any, Literal, Mapping

import numpy as np
import pandas as pd

from tradeo.modules.intraday.research_validation_stack import (
    IntradayValidationResult,
    IntradayValidationThresholds,
)

LabEntryAction = Literal["ENTER_PAPER", "SHADOW_ONLY", "WAIT", "REJECT"]
PaperExitAction = Literal["HOLD", "EXIT_NOW", "TIGHTEN_STOP"]


@dataclass(frozen=True, slots=True)
class IntradayLabBridgeThresholds:
    min_validation_net_ev_r: float = 0.05
    min_validation_effective_events: float = 25.0
    min_validation_unique_symbols: int = 5
    min_validation_unique_sessions: int = 5
    min_validation_unique_buckets: int = 2
    min_candidate_score: float = 0.55
    min_opportunity_score: float = 0.60
    min_timing_score: float = 0.55
    min_liquidity_score: float = 0.60
    max_spread_bps: float = 50.0
    max_spread_cost_r: float = 0.08
    min_dollar_volume: float = 1_000_000.0
    min_reward_risk: float = 4.0
    max_entry_extension_r: float = 0.80
    min_minutes_to_flat: float = 5.0
    max_candidate_age_seconds: int = 180
    min_liquidity_phase_score: float = -0.25
    min_rvol: float = 1.05
    min_rvol_acceleration: float = -0.35
    min_vwap_slope: float = -0.003
    allow_shadow_on_research_reject: bool = True


@dataclass(frozen=True, slots=True)
class IntradayLabEntryPlan:
    action: LabEntryAction
    reason_codes: tuple[str, ...]
    symbol: str
    pattern: str
    side: str
    entry: float | None
    stop: float | None
    target: float | None
    reward_risk: float | None
    opportunity_score: float
    research_score: float
    timing_score: float
    liquidity_score: float
    expires_at: datetime | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def paper_allowed(self) -> bool:
        return self.action == "ENTER_PAPER"


@dataclass(frozen=True, slots=True)
class IntradayPaperExitPolicy:
    profit_protect_start_r: float = 0.80
    profit_giveback_r: float = 0.35
    min_locked_profit_r: float = 0.20
    soft_loss_r: float = -0.55
    hard_loss_r: float = -1.00
    time_decay_fraction: float = 0.65
    min_progress_after_decay_r: float = 0.10
    force_exit_minutes_to_flat: float = 5.0
    vwap_fail_exit: bool = True
    vwap_fail_buffer_r: float = 0.05


@dataclass(frozen=True, slots=True)
class IntradayPaperExitDecision:
    action: PaperExitAction
    reason_codes: tuple[str, ...]
    current_r: float
    mfe_r: float
    mae_r: float
    bars_held: int
    exit_price: float | None
    suggested_stop: float | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def should_exit(self) -> bool:
        return self.action == "EXIT_NOW"


class IntradayResearchLabBridge:
    """Strict paper-lab bridge between Research validation and intraday Lab execution.

    The bridge is intentionally pure. It does not touch a broker, DB session, or
    live execution flags. It receives an already-ranked candidate plus Research
    validation evidence and returns an auditable paper/shadow/wait/reject plan.
    """

    def __init__(self, thresholds: IntradayLabBridgeThresholds | None = None) -> None:
        self.thresholds = thresholds or IntradayLabBridgeThresholds()

    def plan_entry(
        self,
        candidate: Mapping[str, Any],
        validation: IntradayValidationResult | Mapping[str, Any],
        *,
        now: datetime,
        flat_by: datetime | None,
    ) -> IntradayLabEntryPlan:
        thresholds = self.thresholds
        current = _as_utc(now)
        flat_at = _as_utc(flat_by) if flat_by is not None else None
        symbol = str(_first(candidate, "symbol", default="")).upper()
        pattern = str(_first(candidate, "pattern", "pattern_key", "pattern_name", default="intraday_pattern"))
        side = str(_first(candidate, "side", default="long")).lower()
        entry = _float(_first(candidate, "entry", "entry_price"))
        stop = _float(_first(candidate, "stop", "stop_price"))
        target = _float(_first(candidate, "target", "target_price"))
        score = _float(_first(candidate, "score", "composite_score")) or 0.0
        features = _feature_map(candidate)
        metrics = _validation_metrics(validation)
        accepted = _validation_accepted(validation)
        reasons: list[str] = []

        reward_risk, extension_r = _reward_risk_and_extension(
            side=side,
            entry=entry,
            stop=stop,
            target=target,
            current_price=_float(_first(candidate, "current_price", "last_price"))
            or _float(features.get("close")),
        )
        if reward_risk is None:
            reasons.append("invalid_entry_stop_target")
        elif reward_risk < thresholds.min_reward_risk:
            reasons.append("reward_risk_below_lab_min")
        if extension_r is not None and extension_r > thresholds.max_entry_extension_r:
            reasons.append("entry_extension_too_large")

        if not accepted:
            reasons.append("research_validation_not_accepted")
        if float(metrics.get("effective_events", 0.0) or 0.0) < thresholds.min_validation_effective_events:
            reasons.append("research_effective_events_below_lab_min")
        if int(metrics.get("unique_symbols", 0) or 0) < thresholds.min_validation_unique_symbols:
            reasons.append("research_symbols_below_lab_min")
        if int(metrics.get("unique_sessions", 0) or 0) < thresholds.min_validation_unique_sessions:
            reasons.append("research_sessions_below_lab_min")
        if int(metrics.get("unique_buckets", 0) or 0) < thresholds.min_validation_unique_buckets:
            reasons.append("research_buckets_below_lab_min")
        if float(metrics.get("net_expectancy_r", 0.0) or 0.0) < thresholds.min_validation_net_ev_r:
            reasons.append("research_net_ev_below_lab_min")

        spread_bps = _float(_first(candidate, "spread_bps")) or _float(features.get("spread_proxy_bps"))
        spread_cost_r = _float(_first(candidate, "spread_cost_r", "estimated_spread_cost_r"))
        dollar_volume = _float(_first(candidate, "dollar_volume", "avg_dollar_volume")) or _float(
            features.get("dollar_volume")
        )
        rvol = _float(_first(candidate, "rvol")) or _float(features.get("rvol"))
        rvol_acceleration = _float(features.get("rvol_acceleration"))
        vwap_slope = _float(features.get("vwap_slope"))
        liquidity_phase_score = _float(features.get("liquidity_phase_score"))

        if spread_bps is None:
            reasons.append("missing_spread")
        elif spread_bps > thresholds.max_spread_bps:
            reasons.append("spread_too_wide")
        if spread_cost_r is not None and spread_cost_r > thresholds.max_spread_cost_r:
            reasons.append("spread_cost_r_too_high")
        if dollar_volume is None:
            reasons.append("missing_dollar_volume")
        elif dollar_volume < thresholds.min_dollar_volume:
            reasons.append("low_dollar_volume")
        if rvol is not None and rvol < thresholds.min_rvol:
            reasons.append("weak_rvol")
        if rvol_acceleration is not None and rvol_acceleration < thresholds.min_rvol_acceleration:
            reasons.append("weak_rvol_acceleration")
        if vwap_slope is not None:
            if side == "short" and -vwap_slope < thresholds.min_vwap_slope:
                reasons.append("adverse_vwap_slope")
            elif side != "short" and vwap_slope < thresholds.min_vwap_slope:
                reasons.append("adverse_vwap_slope")
        if liquidity_phase_score is not None and liquidity_phase_score < thresholds.min_liquidity_phase_score:
            reasons.append("weak_liquidity_phase")

        if score < thresholds.min_candidate_score:
            reasons.append("candidate_score_below_lab_min")
        window_end = _timestamp(_first(candidate, "window_end", "closed_bar_at", "bar_closed_at"))
        if window_end is not None and (current - window_end).total_seconds() > thresholds.max_candidate_age_seconds:
            reasons.append("candidate_stale")
        if flat_at is not None and (flat_at - current).total_seconds() / 60.0 < thresholds.min_minutes_to_flat:
            reasons.append("flat_window_too_short")

        research_score = _research_score(metrics, thresholds)
        timing_score = _timing_score(
            side=side,
            candidate_score=score,
            rvol=rvol,
            rvol_acceleration=rvol_acceleration,
            vwap_slope=vwap_slope,
            opening_range_position=_float(features.get("opening_range_position")),
            extension_r=extension_r,
            max_extension_r=thresholds.max_entry_extension_r,
        )
        liquidity_score = _liquidity_score(
            spread_bps=spread_bps,
            spread_cost_r=spread_cost_r,
            dollar_volume=dollar_volume,
            liquidity_phase_score=liquidity_phase_score,
            thresholds=thresholds,
        )
        opportunity_score = round(0.40 * research_score + 0.30 * timing_score + 0.30 * liquidity_score, 6)
        if timing_score < thresholds.min_timing_score:
            reasons.append("timing_score_below_lab_min")
        if liquidity_score < thresholds.min_liquidity_score:
            reasons.append("liquidity_score_below_lab_min")
        if opportunity_score < thresholds.min_opportunity_score:
            reasons.append("opportunity_score_below_lab_min")

        reasons = list(dict.fromkeys(reasons))
        hard = _hard_reasons(reasons)
        if "research_validation_not_accepted" in reasons and thresholds.allow_shadow_on_research_reject:
            action: LabEntryAction = "SHADOW_ONLY"
        elif hard:
            action = "REJECT"
        elif reasons:
            action = "WAIT"
        else:
            action = "ENTER_PAPER"
        expires_at = window_end + pd.Timedelta(minutes=10) if window_end is not None else None
        return IntradayLabEntryPlan(
            action=action,
            reason_codes=tuple(reasons),
            symbol=symbol,
            pattern=pattern,
            side=side,
            entry=entry,
            stop=stop,
            target=target,
            reward_risk=reward_risk,
            opportunity_score=opportunity_score,
            research_score=research_score,
            timing_score=timing_score,
            liquidity_score=liquidity_score,
            expires_at=expires_at,
            metadata={
                "paper_only": True,
                "research_metrics": metrics,
                "features_used": features,
                "extension_r": extension_r,
                "spread_bps": spread_bps,
                "spread_cost_r": spread_cost_r,
                "dollar_volume": dollar_volume,
            },
        )


class IntradayPaperExitManager:
    """Paper-only optimal-stopping proxy for minute-sensitive intraday exits."""

    def __init__(self, policy: IntradayPaperExitPolicy | None = None) -> None:
        self.policy = policy or IntradayPaperExitPolicy()

    def decide(
        self,
        bars: pd.DataFrame,
        *,
        symbol: str,
        side: str,
        entry: float,
        stop: float,
        target: float,
        opened_at: datetime,
        now: datetime,
        must_close_by: datetime,
        max_holding_bars: int,
        estimated_cost_r: float = 0.0,
        feature_frame: pd.DataFrame | None = None,
    ) -> IntradayPaperExitDecision:
        frame = _slice_bars(bars, opened_at=opened_at, now=now, must_close_by=must_close_by)
        if frame.empty:
            return IntradayPaperExitDecision("HOLD", ("no_bars",), 0.0, 0.0, 0.0, 0, None, None)
        risk = abs(entry - stop)
        if risk <= 0 or not isfinite(risk):
            raise ValueError("entry/stop risk must be positive")
        direction = -1.0 if side.lower() == "short" else 1.0
        high_r = (frame["high"].to_numpy(dtype=float) - entry) * direction / risk
        low_r = (frame["low"].to_numpy(dtype=float) - entry) * direction / risk
        close_r = (frame["close"].to_numpy(dtype=float) - entry) * direction / risk
        best_r = np.maximum(high_r, low_r)
        worst_r = np.minimum(high_r, low_r)
        current_r = float(close_r[-1] - estimated_cost_r)
        mfe_r = float(best_r.max() - estimated_cost_r)
        mae_r = float(worst_r.min() - estimated_cost_r)
        target_r = abs(target - entry) / risk
        bars_held = min(len(frame), int(max_holding_bars))
        minutes_to_flat = (_as_utc(must_close_by) - _as_utc(now)).total_seconds() / 60.0
        reasons: list[str] = []
        exit_price: float | None = None
        suggested_stop: float | None = None

        target_idx = _first_true(best_r >= target_r)
        stop_idx = _first_true(worst_r <= self.policy.hard_loss_r)
        if stop_idx is not None and (target_idx is None or stop_idx <= target_idx):
            reasons.append("stop_hit")
            exit_price = float(stop)
        elif target_idx is not None:
            reasons.append("target_hit")
            exit_price = float(target)
        elif minutes_to_flat <= self.policy.force_exit_minutes_to_flat:
            reasons.append("force_flat_window")
            exit_price = float(frame["close"].iloc[-1])
        elif bars_held >= max_holding_bars:
            reasons.append("max_holding_bars")
            exit_price = float(frame["close"].iloc[-1])
        elif current_r <= self.policy.hard_loss_r:
            reasons.append("hard_loss_r")
            exit_price = float(frame["close"].iloc[-1])
        elif mfe_r >= self.policy.profit_protect_start_r and current_r <= max(
            self.policy.min_locked_profit_r,
            mfe_r - self.policy.profit_giveback_r,
        ):
            reasons.append("profit_giveback")
            exit_price = float(frame["close"].iloc[-1])
        elif current_r <= self.policy.soft_loss_r and self._momentum_or_vwap_failed(
            frame,
            feature_frame=feature_frame,
            direction=direction,
            risk=risk,
        ):
            reasons.append("loss_reduction_signal")
            exit_price = float(frame["close"].iloc[-1])
        elif bars_held / max(1, max_holding_bars) >= self.policy.time_decay_fraction and current_r < self.policy.min_progress_after_decay_r:
            reasons.append("time_decay_no_progress")
            exit_price = float(frame["close"].iloc[-1])

        if exit_price is not None:
            return IntradayPaperExitDecision(
                "EXIT_NOW",
                tuple(reasons),
                round(current_r, 6),
                round(mfe_r, 6),
                round(mae_r, 6),
                bars_held,
                exit_price,
                None,
                {"minutes_to_flat": minutes_to_flat, "paper_only": True},
            )

        if mfe_r >= self.policy.profit_protect_start_r:
            locked_r = max(self.policy.min_locked_profit_r, mfe_r - self.policy.profit_giveback_r)
            suggested_stop = entry + direction * locked_r * risk
            return IntradayPaperExitDecision(
                "TIGHTEN_STOP",
                ("protect_open_profit",),
                round(current_r, 6),
                round(mfe_r, 6),
                round(mae_r, 6),
                bars_held,
                None,
                round(float(suggested_stop), 6),
                {"minutes_to_flat": minutes_to_flat, "paper_only": True, "locked_r": locked_r},
            )
        return IntradayPaperExitDecision(
            "HOLD",
            (),
            round(current_r, 6),
            round(mfe_r, 6),
            round(mae_r, 6),
            bars_held,
            None,
            None,
            {"minutes_to_flat": minutes_to_flat, "paper_only": True},
        )

    def _momentum_or_vwap_failed(
        self,
        frame: pd.DataFrame,
        *,
        feature_frame: pd.DataFrame | None,
        direction: float,
        risk: float,
    ) -> bool:
        if len(frame) >= 2:
            close = frame["close"].to_numpy(dtype=float)
            if direction * (close[-1] - close[-2]) < 0:
                return True
        if not self.policy.vwap_fail_exit or feature_frame is None or feature_frame.empty:
            return False
        latest = feature_frame.sort_index().iloc[-1]
        distance = _float(latest.get("distance_to_vwap"))
        if distance is None:
            return False
        return direction * distance < -self.policy.vwap_fail_buffer_r / max(risk, 1e-12)


def _feature_map(candidate: Mapping[str, Any]) -> dict[str, Any]:
    features = dict(_mapping(candidate.get("features")))
    metrics = _mapping(candidate.get("metrics"))
    features.update(_mapping(metrics.get("features")))
    intraday = _mapping(_mapping(candidate.get("metadata")).get("intraday"))
    features.update(_mapping(intraday.get("features")))
    return features


def _validation_accepted(validation: IntradayValidationResult | Mapping[str, Any]) -> bool:
    if isinstance(validation, IntradayValidationResult):
        return validation.accepted
    return bool(validation.get("accepted"))


def _validation_metrics(validation: IntradayValidationResult | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(validation, IntradayValidationResult):
        return dict(validation.metrics)
    metrics = validation.get("metrics")
    return dict(metrics) if isinstance(metrics, Mapping) else dict(validation)


def _reward_risk_and_extension(
    *,
    side: str,
    entry: float | None,
    stop: float | None,
    target: float | None,
    current_price: float | None,
) -> tuple[float | None, float | None]:
    if entry is None or stop is None or target is None:
        return None, None
    risk = abs(entry - stop)
    if risk <= 0 or not all(isfinite(x) for x in (entry, stop, target)):
        return None, None
    reward_risk = abs(target - entry) / risk
    if current_price is None or not isfinite(current_price):
        return reward_risk, None
    direction = -1.0 if side == "short" else 1.0
    extension = max(0.0, direction * (current_price - entry) / risk)
    return float(reward_risk), float(extension)


def _research_score(metrics: Mapping[str, Any], thresholds: IntradayLabBridgeThresholds) -> float:
    net = _float(metrics.get("net_expectancy_r")) or 0.0
    eff = _float(metrics.get("effective_events")) or 0.0
    symbols = float(metrics.get("unique_symbols", 0) or 0)
    sessions = float(metrics.get("unique_sessions", 0) or 0)
    buckets = float(metrics.get("unique_buckets", 0) or 0)
    return round(
        0.35 * _clip(net / max(thresholds.min_validation_net_ev_r * 4.0, 1e-9))
        + 0.25 * _clip(eff / max(thresholds.min_validation_effective_events * 2.0, 1e-9))
        + 0.15 * _clip(symbols / max(thresholds.min_validation_unique_symbols * 1.5, 1.0))
        + 0.15 * _clip(sessions / max(thresholds.min_validation_unique_sessions * 1.5, 1.0))
        + 0.10 * _clip(buckets / max(thresholds.min_validation_unique_buckets * 1.5, 1.0)),
        6,
    )


def _timing_score(
    *,
    side: str,
    candidate_score: float,
    rvol: float | None,
    rvol_acceleration: float | None,
    vwap_slope: float | None,
    opening_range_position: float | None,
    extension_r: float | None,
    max_extension_r: float,
) -> float:
    slope = -(vwap_slope or 0.0) if side == "short" else (vwap_slope or 0.0)
    position = opening_range_position if opening_range_position is not None else 0.5
    position_score = 1.0 - min(1.0, abs(position - 0.95) / 1.25)
    extension_score = 1.0 if extension_r is None else 1.0 - _clip(extension_r / max(max_extension_r, 1e-9))
    return round(
        0.25 * _clip(candidate_score)
        + 0.20 * _clip(((rvol or 1.0) - 1.0) / 1.5)
        + 0.20 * _clip(((rvol_acceleration or 0.0) + 0.35) / 1.0)
        + 0.15 * _clip((slope + 0.003) / 0.012)
        + 0.10 * _clip(position_score)
        + 0.10 * _clip(extension_score),
        6,
    )


def _liquidity_score(
    *,
    spread_bps: float | None,
    spread_cost_r: float | None,
    dollar_volume: float | None,
    liquidity_phase_score: float | None,
    thresholds: IntradayLabBridgeThresholds,
) -> float:
    spread_component = 0.5 if spread_bps is None else 1.0 - _clip(spread_bps / max(thresholds.max_spread_bps, 1e-9))
    cost_component = 0.7 if spread_cost_r is None else 1.0 - _clip(spread_cost_r / max(thresholds.max_spread_cost_r, 1e-9))
    dollar_component = 0.0 if dollar_volume is None else _clip(log1p(dollar_volume / thresholds.min_dollar_volume) / log1p(4.0))
    phase_component = 0.5 if liquidity_phase_score is None else _clip((liquidity_phase_score + 0.25) / 2.25)
    return round(0.30 * spread_component + 0.20 * cost_component + 0.30 * dollar_component + 0.20 * phase_component, 6)


def _hard_reasons(reasons: list[str]) -> set[str]:
    hard_prefixes = (
        "invalid_",
        "reward_risk_",
        "spread_",
        "low_dollar_volume",
        "missing_",
        "flat_window_",
        "candidate_stale",
        "entry_extension_",
    )
    return {reason for reason in reasons if reason.startswith(hard_prefixes)}


def _slice_bars(
    bars: pd.DataFrame,
    *,
    opened_at: datetime,
    now: datetime,
    must_close_by: datetime,
) -> pd.DataFrame:
    frame = bars.copy().sort_index()
    frame.columns = [str(c).lower().replace(" ", "_") for c in frame.columns]
    end = min(_as_utc(now), _as_utc(must_close_by))
    return frame[(frame.index >= pd.Timestamp(_as_utc(opened_at))) & (frame.index <= pd.Timestamp(end))]


def _first_true(values: np.ndarray) -> int | None:
    hits = np.flatnonzero(values)
    return int(hits[0]) if hits.size else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first(mapping: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return default


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        ts = pd.Timestamp(value)
    except (TypeError, ValueError):
        return None
    if ts.tzinfo is None:
        ts = ts.tz_localize(timezone.utc)
    return ts.to_pydatetime().astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
