from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

from tradeo.core.config import Settings


def build_entry_quality(
    *,
    match: dict[str, Any],
    risk: Any,
    settings: Settings,
    execution_requested: bool,
    market_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = match.get("metrics") or {}
    features = metrics.get("features") or {}
    entry_gate = metrics.get("entry_gate") or {}

    similarity = _bounded(match.get("similarity"), default=0.0)
    match_score = _bounded(match.get("score"), default=0.0)
    entry_score = _bounded(
        entry_gate.get("entry_score", match.get("entry_score")),
        default=match_score,
    )
    stability = _bounded(metrics.get("pattern_stability_score"), default=0.0)
    expectancy = _bounded(
        _safe_float(metrics.get("pattern_expectancy_r"), 0.0)
        / max(settings.discovery_min_expectancy_r * 2.0, 0.01),
        default=0.0,
    )
    profit_factor = _bounded(
        _safe_float(metrics.get("pattern_profit_factor"), 0.0)
        / max(settings.discovery_min_profit_factor * 1.5, 0.01),
        default=0.0,
    )
    reward_risk = _bounded(
        _safe_float(match.get("reward_risk"), 0.0)
        / max(settings.unvalidated_pattern_min_reward_risk, 1.0),
        default=0.0,
    )
    volume_ratio = _safe_float(entry_gate.get("volume_ratio"), 0.0)
    volume_score = _bounded(volume_ratio / max(settings.entry_min_volume_ratio * 1.8, 0.01), default=0.0)
    avg_dollar_volume = _safe_float(features.get("avg_dollar_volume"), 0.0)
    liquidity_score = _bounded(
        avg_dollar_volume / max(settings.min_avg_dollar_volume * 3.0, 1.0),
        default=0.0,
    )
    extension_atr = _safe_float(entry_gate.get("extension_atr"), 0.0)
    extension_score = _bounded(
        1.0 - extension_atr / max(settings.entry_max_extension_atr, 0.01),
        default=1.0,
    )
    regime_fit = _bounded((match.get("regime_fit") or metrics.get("regime_fit") or {}).get("score"), default=0.5)

    components = {
        "match": round(match_score, 4),
        "similarity": round(similarity, 4),
        "entry": round(entry_score, 4),
        "research_edge": round((expectancy * 0.55) + (profit_factor * 0.30) + (stability * 0.15), 4),
        "reward_risk": round(reward_risk, 4),
        "liquidity": round(liquidity_score, 4),
        "volume": round(volume_score, 4),
        "extension": round(extension_score, 4),
        "regime_fit": round(regime_fit, 4),
    }
    score = round(
        components["entry"] * 0.25
        + components["match"] * 0.16
        + components["research_edge"] * 0.17
        + components["reward_risk"] * 0.11
        + components["liquidity"] * 0.09
        + components["volume"] * 0.08
        + components["extension"] * 0.06
        + components["regime_fit"] * 0.08,
        6,
    )
    flags = _quality_flags(
        match=match,
        risk=risk,
        settings=settings,
        avg_dollar_volume=avg_dollar_volume,
        volume_ratio=volume_ratio,
        extension_atr=extension_atr,
    )
    actionable = score >= 0.60 and not flags
    return {
        "score": score,
        "label": _quality_label(score, flags),
        "actionable": actionable,
        "components": components,
        "flags": flags,
        "execution_requested": execution_requested,
        "market_state": (market_session or {}).get("state"),
    }


def build_signal_snapshot(
    *,
    match: dict[str, Any],
    risk: Any,
    settings: Settings,
    entry_quality: dict[str, Any],
    execution_requested: bool,
    market_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = match.get("metrics") or {}
    features = metrics.get("features") or {}
    entry_gate = metrics.get("entry_gate") or {}
    entry = _safe_float(match.get("entry_price"), 0.0)
    stop = _safe_float(match.get("stop_price"), 0.0)
    target = _safe_float(match.get("target_price"), 0.0)
    risk_per_share = abs(entry - stop)
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "market_session": market_session or {},
        "execution_requested": execution_requested,
        "symbol": match.get("symbol"),
        "timeframe": match.get("timeframe"),
        "side": match.get("side"),
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_per_share": round(risk_per_share, 4),
        "notional_usd": round(entry * int(getattr(risk, "suggested_qty", 0) or 0), 2),
        "entry_variant": match.get("entry_variant") or {},
        "entry_variant_id": match.get("entry_variant_id"),
        "entry_audit": match.get("entry_audit") or metrics.get("entry_audit") or {},
        "regime": match.get("regime") or metrics.get("regime") or {},
        "regime_fit": match.get("regime_fit") or metrics.get("regime_fit") or {},
        "entry_quality": entry_quality,
        "entry_gate": entry_gate,
        "features": {
            "avg_dollar_volume": features.get("avg_dollar_volume"),
            "atr_pct": features.get("atr_pct", entry_gate.get("atr_pct")),
            "trend_score": features.get("trend_score"),
            "volume_ratio": entry_gate.get("volume_ratio"),
            "extension_atr": entry_gate.get("extension_atr"),
            "sma20": entry_gate.get("sma20"),
            "prev_high_20": entry_gate.get("prev_high_20"),
            "prev_low_20": entry_gate.get("prev_low_20"),
            "last_close": entry_gate.get("close"),
        },
        "pattern": {
            "id": match.get("pattern_id"),
            "key": match.get("pattern_key"),
            "status": match.get("pattern_status"),
            "promotion_status": match.get("pattern_promotion_status"),
            "score": metrics.get("pattern_score"),
            "expectancy_r": metrics.get("pattern_expectancy_r"),
            "profit_factor": metrics.get("pattern_profit_factor"),
            "stability_score": metrics.get("pattern_stability_score"),
        },
        "match": {
            "similarity": match.get("similarity"),
            "score": match.get("score"),
            "entry_score": match.get("entry_score"),
            "trigger": match.get("entry_trigger"),
            "window_end": match.get("window_end"),
        },
        "risk": {
            "approved": bool(getattr(risk, "approved", True)),
            "risk_usd": getattr(risk, "risk_usd", None),
            "suggested_qty": getattr(risk, "suggested_qty", None),
            "notional_usd": getattr(risk, "notional_usd", None),
            "reason": getattr(risk, "reason", ""),
            "warnings": list(getattr(risk, "warnings", []) or []),
        },
        "thresholds": {
            "min_avg_dollar_volume": settings.min_avg_dollar_volume,
            "max_atr_pct": settings.max_atr_pct,
            "entry_min_score": settings.entry_min_score,
            "entry_min_volume_ratio": settings.entry_min_volume_ratio,
            "entry_max_extension_atr": settings.entry_max_extension_atr,
        },
    }


def _quality_flags(
    *,
    match: dict[str, Any],
    risk: Any,
    settings: Settings,
    avg_dollar_volume: float,
    volume_ratio: float,
    extension_atr: float,
) -> list[str]:
    flags: list[str] = []
    if not bool(getattr(risk, "approved", True)):
        flags.append("risk_rejected")
    risk_warnings = set(getattr(risk, "warnings", []) or [])
    entry_gate = ((match.get("metrics") or {}).get("entry_gate") or {})
    if settings.entry_gate_enabled and not bool(entry_gate.get("passed", False)):
        flags.append("entry_gate_failed")
    if settings.entry_gate_enabled and entry_gate.get("regime_ok") is False:
        flags.append("regime_filter_failed")
    if (
        avg_dollar_volume < settings.min_avg_dollar_volume
        and "liquidity_filter_failed" not in risk_warnings
    ):
        flags.append("thin_liquidity")
    if settings.entry_gate_enabled and volume_ratio and volume_ratio < settings.entry_min_volume_ratio:
        flags.append("weak_volume_confirmation")
    if settings.entry_gate_enabled and extension_atr > settings.entry_max_extension_atr:
        flags.append("overextended")
    return flags


def _quality_label(score: float, flags: list[str]) -> str:
    if flags:
        return "blocked"
    if score >= 0.78:
        return "high"
    if score >= 0.60:
        return "actionable"
    if score >= 0.45:
        return "watch"
    return "weak"


def _bounded(value: Any, *, default: float) -> float:
    number = _safe_float(value, default)
    return max(0.0, min(1.0, number))


def _safe_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default
