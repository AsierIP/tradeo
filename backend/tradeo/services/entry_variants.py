from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import blake2b
import math
from typing import Any

import pandas as pd

from tradeo.core.config import Settings
from tradeo.services.technical_indicators import atr

PENDING_FORWARD_LABEL = "pending_forward_label"


def build_entry_audit_context(df: pd.DataFrame, timeframe: str) -> dict[str, Any]:
    """Record the data cutoff proving an entry decision uses only known bars."""
    now = datetime.now(timezone.utc)
    window_end = _ts(df.index[-1]) if len(df.index) else now
    eligible = max(now, window_end + _timeframe_delta(timeframe))
    return {
        "available_data_cutoff_ts": window_end.isoformat(),
        "decision_ts": now.isoformat(),
        "entry_eligible_ts": eligible.isoformat(),
        "label_generated_ts": PENDING_FORWARD_LABEL,
        "source_bar_hash": _source_bar_hash(df),
        "split_id": "live_forward_scan",
        "lookahead_policy": "entry eligible only after available_data_cutoff_ts",
    }


def classify_regime(features: dict[str, Any], entry_gate: dict[str, Any]) -> dict[str, Any]:
    market = _float(features.get("market_regime_score"), 0.0)
    breadth = _float(features.get("market_breadth_proxy"), 0.5)
    trend = _float(features.get("trend_regime"), 0.0)
    volatility = _float(features.get("volatility_regime"), 1.0)
    liquidity = _float(features.get("liquidity_score"), 0.0)
    sector = _float(features.get("sector_strength"), 0.0)
    relative_spy = _float(features.get("relative_strength_spy"), 0.0)
    volume_ratio = _float(entry_gate.get("volume_ratio"), _float(features.get("volume_rel_last"), 1.0))
    regimes = {
        "market_regime": _bucket(market, low=-0.25, high=0.25, labels=("market_down", "market_mixed", "market_up")),
        "breadth_regime": "broad" if breadth >= 0.67 else "narrow" if breadth <= 0.33 else "neutral_breadth",
        "trend_regime": _bucket(trend, low=-0.25, high=0.25, labels=("downtrend", "mixed_trend", "uptrend")),
        "volatility_regime": "low_vol" if volatility < 0.8 else "high_vol" if volatility > 1.25 else "normal_vol",
        "liquidity_regime": "liquid" if liquidity >= 0.55 else "thin",
        "sector_regime": _bucket(sector, low=-0.03, high=0.03, labels=("sector_weak", "sector_neutral", "sector_strong")),
        "relative_strength_regime": "rs_leader" if relative_spy > 0.03 else "rs_laggard" if relative_spy < -0.03 else "rs_neutral",
        "volume_regime": "volume_confirmed" if volume_ratio >= 1.2 else "normal_volume" if volume_ratio >= 0.8 else "weak_volume",
    }
    regimes["regime_key"] = "|".join(
        str(regimes[key])
        for key in (
            "market_regime",
            "trend_regime",
            "volatility_regime",
            "liquidity_regime",
            "relative_strength_regime",
        )
    )
    return regimes


def build_entry_variants(
    *,
    side: str,
    df: pd.DataFrame,
    base_entry_gate: dict[str, Any],
    score: float,
    reward_risk: float,
    settings: Settings,
) -> list[dict[str, Any]]:
    if df.empty:
        return []
    side = side.lower().strip()
    latest = df.iloc[-1]
    previous = df.iloc[-21:-1] if len(df) >= 21 else df.iloc[:-1]
    if previous.empty:
        previous = df.iloc[-2:-1] if len(df) >= 2 else df.iloc[-1:]
    close = _required_float(latest["close"])
    high = _required_float(latest["high"])
    low = _required_float(latest["low"])
    open_ = _required_float(latest["open"])
    prev_close = _required_float(previous["close"].iloc[-1])
    prev_high = _required_float(previous["high"].max())
    prev_low = _required_float(previous["low"].min())
    if None in {close, high, low, open_, prev_close, prev_high, prev_low}:
        return []
    atr_value = _float(atr(df, 14).iloc[-1], max(close * 0.02, 0.01)) if len(df) >= 15 else max(close * 0.02, 0.01)
    risk = max(atr_value * 1.5, close * 0.015, 0.01)
    volume_ratio = _float(base_entry_gate.get("volume_ratio"), 1.0)
    base_trigger = str(base_entry_gate.get("trigger") or "pattern_close")
    base_passed = bool(base_entry_gate.get("passed", False)) or not settings.entry_gate_enabled
    variants: list[dict[str, Any]] = []

    if base_passed and base_trigger != "no_operational_trigger":
        variants.append(
            _variant(
                side=side,
                variant_id=f"{base_trigger}_next_bar_limit",
                family=base_trigger,
                entry=close,
                risk=risk,
                reward_risk=reward_risk,
                score=_variant_score(base_entry_gate, bump=0.00),
                order_style="next_bar_limit",
                rule=f"Last closed bar confirmed {base_trigger}; enter no earlier than next eligible bar.",
                base_gate=base_entry_gate,
            )
        )

    if side == "long":
        stop_entry = high + max(atr_value * 0.05, close * 0.001)
        retest_entry = max(prev_high, close - atr_value * 0.35)
        gap_confirmed = open_ > prev_close * 1.005 and close > open_
    else:
        stop_entry = low - max(atr_value * 0.05, close * 0.001)
        retest_entry = min(prev_low, close + atr_value * 0.35)
        gap_confirmed = open_ < prev_close * 0.995 and close < open_

    if base_trigger in {"breakout", "momentum_close", "pullback_reclaim"} or not settings.entry_gate_enabled:
        variants.append(
            _variant(
                side=side,
                variant_id="next_bar_stop_confirmation",
                family="stop_confirmation",
                entry=stop_entry,
                risk=risk,
                reward_risk=reward_risk,
                score=_variant_score(base_entry_gate, bump=-0.03),
                order_style="next_bar_stop",
                rule="Require next bar continuation through the signal bar extreme.",
                base_gate=base_entry_gate,
            )
        )
        variants.append(
            _variant(
                side=side,
                variant_id="next_bar_limit_retest",
                family="limit_retest",
                entry=retest_entry,
                risk=risk,
                reward_risk=reward_risk,
                score=_variant_score(base_entry_gate, bump=-0.06),
                order_style="next_bar_limit",
                rule="Enter on next-bar retest near prior 20-bar breakout/reclaim level.",
                base_gate=base_entry_gate,
            )
        )

    if volume_ratio >= max(1.2, settings.entry_min_volume_ratio):
        variants.append(
            _variant(
                side=side,
                variant_id="volume_confirmed_close",
                family="volume_confirmation",
                entry=close,
                risk=risk,
                reward_risk=reward_risk,
                score=_variant_score(base_entry_gate, bump=0.04),
                order_style="next_bar_limit",
                rule="Volume-confirmed close; enter no earlier than next eligible bar.",
                base_gate=base_entry_gate,
            )
        )

    if gap_confirmed:
        variants.append(
            _variant(
                side=side,
                variant_id="gap_open_follow_through",
                family="gap_follow_through",
                entry=close,
                risk=risk,
                reward_risk=reward_risk,
                score=_variant_score(base_entry_gate, bump=0.02),
                order_style="next_bar_limit",
                rule="Gap-open follow-through held into the signal close; enter next eligible bar only.",
                base_gate=base_entry_gate,
            )
        )

    if not variants and not settings.entry_gate_enabled:
        variants.append(
            _variant(
                side=side,
                variant_id="pattern_close_probe",
                family="close_probe",
                entry=close,
                risk=risk,
                reward_risk=reward_risk,
                score=max(score, _variant_score(base_entry_gate, bump=0.0)),
                order_style="next_bar_limit",
                rule="Gate disabled; probe the pattern close on the next eligible bar.",
                base_gate={**base_entry_gate, "passed": True, "trigger": "pattern_close_probe"},
            )
        )

    deduped: dict[str, dict[str, Any]] = {}
    for item in variants:
        if _valid_bracket(side, item["entry_price"], item["stop_price"], item["target_price"]):
            deduped[item["entry_variant_id"]] = item
    ordered = sorted(deduped.values(), key=lambda item: item["entry_gate"]["entry_score"], reverse=True)
    return ordered[: max(1, int(settings.entry_variant_max_per_pattern_symbol))]


def _variant(
    *,
    side: str,
    variant_id: str,
    family: str,
    entry: float,
    risk: float,
    reward_risk: float,
    score: float,
    order_style: str,
    rule: str,
    base_gate: dict[str, Any],
) -> dict[str, Any]:
    if side == "short":
        stop = entry + risk
        target = entry - reward_risk * risk
    else:
        stop = entry - risk
        target = entry + reward_risk * risk
    gate = {**base_gate}
    gate["passed"] = bool(base_gate.get("passed", False)) or str(base_gate.get("trigger")) == "pattern_close_probe"
    gate["trigger"] = variant_id
    gate["entry_score"] = round(max(0.0, min(1.0, score)), 6)
    gate["entry_variant_family"] = family
    gate["entry_order_style"] = order_style
    return {
        "entry_variant_id": variant_id,
        "entry_variant": {
            "id": variant_id,
            "family": family,
            "order_style": order_style,
            "entry_timing": "next_eligible_bar",
            "entry_rule": rule,
            "stop_rule": "1.5 ATR or 1.5% minimum risk from variant entry.",
            "target_rule": f"{reward_risk:g}R target from variant entry.",
        },
        "entry_gate": gate,
        "entry_price": round(float(entry), 4),
        "stop_price": round(float(stop), 4),
        "target_price": round(float(target), 4),
    }


def _variant_score(base_gate: dict[str, Any], *, bump: float) -> float:
    return _float(base_gate.get("entry_score"), 0.0) + bump


def _valid_bracket(side: str, entry: float, stop: float, target: float) -> bool:
    if min(entry, stop, target) <= 0:
        return False
    if side == "short":
        return target < entry < stop
    return stop < entry < target


def _source_bar_hash(df: pd.DataFrame) -> str:
    cols = [col for col in ("open", "high", "low", "close", "volume") if col in df.columns]
    payload = df.tail(3)[cols].round(8).to_csv(index=True)
    return blake2b(payload.encode("utf-8"), digest_size=12).hexdigest()


def _timeframe_delta(timeframe: str) -> timedelta:
    compact = " ".join(str(timeframe).lower().strip().split()).replace(" ", "")
    units: tuple[tuple[str, Any], ...] = (
        ("minutes", lambda amount: timedelta(minutes=amount)),
        ("minute", lambda amount: timedelta(minutes=amount)),
        ("mins", lambda amount: timedelta(minutes=amount)),
        ("min", lambda amount: timedelta(minutes=amount)),
        ("hours", lambda amount: timedelta(hours=amount)),
        ("hour", lambda amount: timedelta(hours=amount)),
        ("hrs", lambda amount: timedelta(hours=amount)),
        ("hr", lambda amount: timedelta(hours=amount)),
        ("weeks", lambda amount: timedelta(weeks=amount)),
        ("week", lambda amount: timedelta(weeks=amount)),
        ("wks", lambda amount: timedelta(weeks=amount)),
        ("wk", lambda amount: timedelta(weeks=amount)),
        ("days", lambda amount: timedelta(days=amount)),
        ("day", lambda amount: timedelta(days=amount)),
        ("m", lambda amount: timedelta(minutes=amount)),
        ("h", lambda amount: timedelta(hours=amount)),
        ("w", lambda amount: timedelta(weeks=amount)),
        ("d", lambda amount: timedelta(days=amount)),
    )
    for suffix, build_delta in units:
        if compact.endswith(suffix):
            amount = compact[: -len(suffix)]
            if amount.isdigit() or amount == "":
                return build_delta(max(1, int(amount or "1")))
    return timedelta(days=1)


def _ts(value: Any) -> datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        ts = ts.tz_localize(timezone.utc)
    else:
        ts = ts.tz_convert(timezone.utc)
    return ts.to_pydatetime()


def _bucket(value: float, *, low: float, high: float, labels: tuple[str, str, str]) -> str:
    if value < low:
        return labels[0]
    if value > high:
        return labels[2]
    return labels[1]


def _float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _required_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
