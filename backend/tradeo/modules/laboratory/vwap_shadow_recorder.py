from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo
import json
import math
import time as monotonic_time

SCHEMA_VERSION = "tradeo.lab_vwap_shadow.v1"
ShadowDecision = Literal["shadow_recorded", "market_closed", "quote_unavailable", "blocked_safety"]
Side = Literal["long", "short"]


@dataclass(frozen=True, slots=True)
class ShadowQuote:
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    source: str = "mock_or_external_quote"


def build_vwap_shadow_record(
    *,
    symbol: str,
    side: Side,
    vwap_condition: str,
    timeframe: str,
    quote: ShadowQuote | None = None,
    bars: Any = None,
    future_bars: Any = None,
    settings: Any | None = None,
    now: datetime | None = None,
    market_open: bool | None = None,
    latency_ms: float | None = None,
    runtime_kill_switch_active: bool = False,
) -> dict[str, Any]:
    """Build one read-only VWAP Lab shadow record.

    This function never imports broker adapters and never sends orders. It
    produces an artifact-shaped record that can later feed Paper-readiness work.
    """

    settings = settings or _default_settings()
    generated_at = now or datetime.now(timezone.utc)
    started = monotonic_time.monotonic()
    quote = quote or ShadowQuote()
    market_is_open = _is_market_open(generated_at) if market_open is None else bool(market_open)
    latency = latency_ms if latency_ms is not None else (monotonic_time.monotonic() - started) * 1000.0
    entry_context = _entry_context(bars, vwap_condition=vwap_condition)
    side_multiplier = 1.0 if side == "long" else -1.0
    quote_status = _quote_status(quote)
    entry = _theoretical_entry(quote)
    risk = max(entry * 0.015, 0.01) if entry is not None else None
    stop = entry - side_multiplier * risk if entry is not None and risk is not None else None
    target = entry + side_multiplier * risk * 4.0 if entry is not None and risk is not None else None
    spread_bps = _spread_bps(quote)
    spread_cost_r = _spread_cost_r(quote, risk)
    mfe_r, mae_r, gross_r = _path_metrics(future_bars, entry=entry, risk=risk, side=side)
    cost_x2 = _round(spread_cost_r * 2.0) if spread_cost_r is not None else None
    net_r = _round(gross_r - spread_cost_r) if gross_r is not None and spread_cost_r is not None else None
    exit_context = _exit_context(entry_context, side=side)
    blocked = _safety_blocked(settings, runtime_kill_switch_active=runtime_kill_switch_active)
    if blocked:
        decision: ShadowDecision = "blocked_safety"
    elif not market_is_open:
        decision = "market_closed"
    elif quote_status != "available":
        decision = "quote_unavailable"
    else:
        decision = "shadow_recorded"
    decision_reason = blocked or (decision if decision != "shadow_recorded" else "shadow_recorded")
    record = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "symbol": symbol.upper(),
        "side": side,
        "timeframe": timeframe,
        "vwap_condition": vwap_condition,
        "candidate_signal": bool(entry_context.get("condition_passed")),
        "entry_context": entry_context,
        "exit_context": exit_context,
        "theoretical_entry": _round(entry),
        "theoretical_stop": _round(stop),
        "theoretical_target": _round(target),
        "bid": _round(quote.bid),
        "ask": _round(quote.ask),
        "last": _round(quote.last),
        "quote_status": quote_status,
        "quote_source": _safe_text(quote.source),
        "spread_bps": spread_bps,
        "latency_ms": _round(latency),
        "mfe_r": mfe_r,
        "mae_r": mae_r,
        "gross_r": gross_r,
        "net_r_estimate": net_r,
        "spread_cost_r": spread_cost_r,
        "cost_x2_estimate": cost_x2,
        "entry_reason": vwap_condition if entry_context.get("condition_passed") else "condition_not_confirmed",
        "exit_reason_vwap": exit_context.get("vwap_exit_reason"),
        "no_order_reason": "shadow_lab_no_orders",
        "ibkr_status": "not_used",
        "decision": decision,
        "decision_reason": decision_reason,
        "orders_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
        "submit_order_called": False,
        "paper_order_submitted": False,
        "live_order_submitted": False,
        "wave_executed": False,
    }
    return redact_shadow_record(record)


def write_shadow_artifacts(record: dict[str, Any], *, json_out: str | Path, md_out: str | Path) -> None:
    json_path = Path(json_out)
    md_path = Path(md_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    md_path.write_text(render_shadow_markdown(record), encoding="utf-8")


def render_shadow_markdown(record: dict[str, Any]) -> str:
    lines = [
        "# VWAP Lab Shadow",
        "",
        f"- symbol: `{record.get('symbol')}`",
        f"- side: `{record.get('side')}`",
        f"- timeframe: `{record.get('timeframe')}`",
        f"- vwap_condition: `{record.get('vwap_condition')}`",
        f"- decision: `{record.get('decision')}`",
        f"- quote_status: `{record.get('quote_status')}`",
        f"- spread_bps: `{record.get('spread_bps')}`",
        f"- latency_ms: `{record.get('latency_ms')}`",
        f"- orders_allowed: `{record.get('orders_allowed')}`",
        f"- paper_allowed: `{record.get('paper_allowed')}`",
        f"- live_allowed: `{record.get('live_allowed')}`",
        "",
        "No broker, order, Paper, Live, or wave action is performed by this smoke recorder.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def redact_shadow_record(record: dict[str, Any]) -> dict[str, Any]:
    sensitive_parts = ("secret", "token", "password", "api_key", "account", "username")
    redacted: dict[str, Any] = {}
    for key, value in record.items():
        if any(part in key.lower() for part in sensitive_parts):
            redacted[key] = "<redacted>"
        elif isinstance(value, dict):
            redacted[key] = redact_shadow_record(value)
        else:
            redacted[key] = value
    return redacted


def _entry_context(bars: Any, *, vwap_condition: str) -> dict[str, Any]:
    if bars is None or bars.empty:
        return {"data_available": False, "condition_passed": False}
    try:
        from tradeo.research.intraday_vwap_features import build_intraday_vwap_features

        frame = build_intraday_vwap_features(bars, timestamp_column="timestamp").frame
    except (ImportError, KeyError, ValueError):
        return {"data_available": False, "condition_passed": False, "error": "invalid_ohlcv"}
    if frame.empty:
        return {"data_available": False, "condition_passed": False}
    latest = frame.iloc[-1]
    condition_value = bool(latest.get(vwap_condition, False)) if vwap_condition in frame.columns else False
    return {
        "data_available": True,
        "condition_passed": condition_value,
        "timestamp": str(frame.index[-1]),
        "close": _round(latest.get("close")),
        "vwap": _round(latest.get("vwap")),
        "price_vs_vwap_bps": _round(latest.get("vwap_distance_bps")),
        "vwap_slope_bps": _round(latest.get("vwap_slope_bps")),
        "above_vwap": bool(latest.get("above_vwap")),
        "below_vwap": bool(latest.get("below_vwap")),
        "session_bucket": str(latest.get("session_bucket")),
    }


def _exit_context(entry_context: dict[str, Any], *, side: Side) -> dict[str, Any]:
    if not entry_context.get("data_available"):
        return {"vwap_exit_reason": "no_vwap_context"}
    if side == "long" and entry_context.get("below_vwap"):
        return {"vwap_exit_reason": "long_below_vwap"}
    if side == "short" and entry_context.get("above_vwap"):
        return {"vwap_exit_reason": "short_above_vwap"}
    return {"vwap_exit_reason": "no_vwap_exit"}


def _path_metrics(
    future_bars: Any,
    *,
    entry: float | None,
    risk: float | None,
    side: Side,
) -> tuple[float | None, float | None, float | None]:
    if future_bars is None or future_bars.empty or entry is None or risk in (None, 0.0):
        return None, None, None
    import pandas as pd

    high = pd.to_numeric(future_bars["high"], errors="coerce").max()
    low = pd.to_numeric(future_bars["low"], errors="coerce").min()
    close = pd.to_numeric(future_bars["close"], errors="coerce").iloc[-1]
    if side == "long":
        mfe = (float(high) - entry) / risk
        mae = (float(low) - entry) / risk
        gross = (float(close) - entry) / risk
    else:
        mfe = (entry - float(low)) / risk
        mae = (entry - float(high)) / risk
        gross = (entry - float(close)) / risk
    return _round(mfe), _round(mae), _round(gross)


def _quote_status(quote: ShadowQuote) -> str:
    if _usable_price(quote.bid) and _usable_price(quote.ask) and float(quote.ask or 0.0) >= float(quote.bid or 0.0):
        return "available"
    return "unavailable"


def _theoretical_entry(quote: ShadowQuote) -> float | None:
    if _usable_price(quote.last):
        return float(quote.last)
    if _quote_status(quote) == "available":
        return (float(quote.bid or 0.0) + float(quote.ask or 0.0)) / 2.0
    return None


def _spread_bps(quote: ShadowQuote) -> float | None:
    if _quote_status(quote) != "available":
        return None
    mid = (float(quote.bid or 0.0) + float(quote.ask or 0.0)) / 2.0
    return _round((float(quote.ask or 0.0) - float(quote.bid or 0.0)) / mid * 10_000.0) if mid > 0 else None


def _spread_cost_r(quote: ShadowQuote, risk: float | None) -> float | None:
    if _quote_status(quote) != "available" or risk in (None, 0.0):
        return None
    return _round((float(quote.ask or 0.0) - float(quote.bid or 0.0)) / risk)


def _default_settings() -> Any:
    try:
        from tradeo.core.config import get_settings
    except ImportError:
        return {"live_trading_enabled": False, "trading_mode": "paper"}
    return get_settings()


def _safety_blocked(settings: Any, *, runtime_kill_switch_active: bool = False) -> str | None:
    if bool(runtime_kill_switch_active):
        return "runtime_kill_switch_enabled"
    if bool(_setting(settings, "kill_switch_enabled", False)):
        return "kill_switch_enabled"
    if bool(_setting(settings, "live_trading_enabled", False)):
        return "live_trading_enabled"
    if str(_setting(settings, "trading_mode", "")).lower() == "live":
        return "trading_mode_live"
    if bool(_setting(settings, "live_armed", False)):
        return "live_armed"
    if bool(_setting(settings, "intraday_live_enabled", False)):
        return "intraday_live_enabled"
    if int(_setting(settings, "ibkr_port", 0) or 0) in {4001, 7496}:
        return "ibkr_live_port"
    return None


def _setting(settings: Any, name: str, default: Any) -> Any:
    if isinstance(settings, dict):
        return settings.get(name, default)
    return getattr(settings, name, default)


def _is_market_open(now: datetime) -> bool:
    ny = now.astimezone(ZoneInfo("America/New_York"))
    if ny.weekday() >= 5:
        return False
    return time(9, 30) <= ny.time() < time(16, 0)


def _usable_price(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0


def _safe_text(value: str) -> str:
    lowered = str(value).lower()
    if any(part in lowered for part in ("secret", "token", "password", "api_key")):
        return "<redacted>"
    return str(value)


def _round(value: Any) -> float | None:
    if value in (None, "", "not_available"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(number, 5) if math.isfinite(number) else None
