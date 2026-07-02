from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tradeo.research.intraday_research_planner import normalize_wave_signature
from tradeo.research.intraday_vwap_features import build_intraday_vwap_features

SCHEMA_VERSION = "tradeo.intraday_vwap_research.v1"


def analyze_intraday_vwap_research(
    *,
    ohlcv_cache_dir: str | Path,
    universe_file: str | Path,
    limit: int,
    period: str,
    timeframe: str,
    forensics_json: str | Path | None = None,
) -> dict[str, Any]:
    symbols = _load_universe_symbols(universe_file, limit=limit)
    prohibited_repeats = _load_prohibited_repeats(forensics_json)
    symbol_stats: list[dict[str, Any]] = []
    frames: list[pd.DataFrame] = []
    missing_symbols: list[str] = []

    for symbol in symbols:
        cache_path = Path(ohlcv_cache_dir) / f"{symbol}_{timeframe}_{period}.csv"
        if not cache_path.exists():
            missing_symbols.append(symbol)
            continue
        try:
            bars = pd.read_csv(cache_path)
            features = build_intraday_vwap_features(bars, timestamp_column="timestamp").frame
        except (OSError, ValueError, pd.errors.ParserError, KeyError):
            missing_symbols.append(symbol)
            continue
        regular = features[features["in_regular_session"] & features["vwap"].notna()].copy()
        if regular.empty:
            missing_symbols.append(symbol)
            continue
        regular["symbol"] = symbol
        frames.append(regular)
        symbol_stats.append(_symbol_stats(symbol, regular))

    candidates = candidate_search_spaces(
        recommended_limit=len(symbols),
        limit_source="universe_requested_limit",
    )
    recommended, blocked = _filter_prohibited_candidates(candidates, prohibited_repeats)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    status = "OK" if symbol_stats else "NOT_AVAILABLE"
    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "universe": {
            "path": str(universe_file),
            "limit": int(limit),
            "symbols_requested": len(symbols),
            "symbols_analyzed": len(symbol_stats),
            "missing_symbols": missing_symbols,
        },
        "vwap_summary": _vwap_summary(combined, symbol_stats),
        "session_bucket_stats": _session_bucket_stats(combined),
        "symbol_stats": sorted(
            symbol_stats,
            key=lambda item: (-(item["above_vwap_pct"] or 0.0), item["symbol"]),
        ),
        "candidate_search_spaces": candidates,
        "recommended_next_waves": recommended,
        "blocked_waves": blocked,
        "prohibited_repeats": list(prohibited_repeats),
        "safety": {
            "live_allowed": False,
            "paper_allowed": False,
            "orders_allowed": False,
            "ibkr_used": False,
            "wave_executed": False,
        },
    }
    if status == "NOT_AVAILABLE":
        summary["not_available_reason"] = "No readable OHLCV cache files matched the requested universe/timeframe/period."
    return summary


def candidate_search_spaces(*, recommended_limit: int, limit_source: str) -> list[dict[str, Any]]:
    rows = [
        (
            "30m_W100_vwap_reclaim_slow",
            "30m",
            100,
            (8, 13, 21),
            "price_reclaims_vwap_with_flat_or_rising_vwap",
            "crossed_above_vwap and vwap_slope_direction in up/flat",
            "vwap_loss_long_exit or slow forward-bar evaluation",
            "Tests slow long reclaims where VWAP acceptance may survive costs.",
            "Can overfit clean reclaim events; must stay read-only until confirmed.",
        ),
        (
            "30m_W100_vwap_reject_slow",
            "30m",
            100,
            (8, 13, 21),
            "price_rejects_vwap_from_below",
            "below_vwap with intrabar touch/rejection near VWAP",
            "vwap_reclaim_short_exit or slow forward-bar evaluation",
            "Tests whether below-VWAP rejection captures weak intraday regimes.",
            "Short-side context is noisy and needs strict borrow/order review later.",
        ),
        (
            "15m_W50_vwap_pullback_fast",
            "15m",
            50,
            (4, 8, 13),
            "above_vwap_pullback_hold",
            "above_vwap and low touches VWAP without losing it",
            "vwap_loss_long_exit or fast forward-bar evaluation",
            "Probes faster VWAP pullbacks only after cache confirms structure.",
            "Faster bars are cost-sensitive; no paper/live without separate approval.",
        ),
        (
            "1h_W100_vwap_regime_filter",
            "1h",
            100,
            (2, 4, 6),
            "vwap_regime_above_rising_or_below_falling",
            "filter candidates by persistent VWAP side and slope regime",
            "regime loss or slow forward-bar evaluation",
            "Uses VWAP as a regime filter before another broad pattern wave.",
            "May reduce sample size too far; confirm with exact-scope diagnostics.",
        ),
    ]
    return [
        {
            "name": name,
            "timeframe": timeframe,
            "window_size": window_size,
            "forward_bars": list(forward_bars),
            "vwap_condition": condition,
            "entry_context": entry,
            "exit_context": exit_context,
            "recommended_limit": int(recommended_limit),
            "limit_source": limit_source,
            "reason": reason,
            "risk": risk,
            "signature": f"{timeframe} W{window_size} {','.join(str(item) for item in forward_bars)}",
        }
        for name, timeframe, window_size, forward_bars, condition, entry, exit_context, reason, risk in rows
    ]


def render_markdown(summary: dict[str, Any]) -> str:
    universe = summary.get("universe") or {}
    vwap = summary.get("vwap_summary") or {}
    lines = [
        "# Intraday VWAP Research Summary",
        "",
        f"Status: `{summary.get('status')}`",
        "",
        "## Universe",
        f"- path: `{universe.get('path')}`",
        f"- limit: `{universe.get('limit')}`",
        f"- symbols_requested: `{universe.get('symbols_requested')}`",
        f"- symbols_analyzed: `{universe.get('symbols_analyzed')}`",
        "",
        "## VWAP structure",
        f"- bars_analyzed: `{vwap.get('bars_analyzed')}`",
        f"- above_vwap_pct: `{vwap.get('above_vwap_pct')}`",
        f"- below_vwap_pct: `{vwap.get('below_vwap_pct')}`",
        f"- median_distance_bps: `{vwap.get('median_distance_bps')}`",
        f"- p90_abs_distance_bps: `{vwap.get('p90_abs_distance_bps')}`",
        f"- vwap_chop_rate: `{vwap.get('vwap_chop_rate')}`",
        "",
        "## Session buckets",
    ]
    buckets = summary.get("session_bucket_stats") or {}
    if buckets:
        for bucket, row in buckets.items():
            lines.append(f"- {bucket}: bars `{row.get('bars')}`, above_vwap_pct `{row.get('above_vwap_pct')}`")
    else:
        lines.append("- No session bucket stats available.")
    lines.extend(["", "## Top symbols"])
    for row in (summary.get("symbol_stats") or [])[:10]:
        lines.append(
            f"- {row['symbol']}: above `{row['above_vwap_pct']}`, "
            f"chop `{row['chop_rate']}`, bias `{row['trend_bias']}`"
        )
    if not summary.get("symbol_stats"):
        lines.append("- No symbol stats available.")
    lines.extend(["", "## Chop / trend bias"])
    bias_counts: dict[str, int] = {}
    for row in summary.get("symbol_stats") or []:
        bias_counts[str(row.get("trend_bias"))] = bias_counts.get(str(row.get("trend_bias")), 0) + 1
    lines.extend(f"- {key}: `{value}`" for key, value in sorted(bias_counts.items()))
    if not bias_counts:
        lines.append("- Not available.")
    lines.extend(["", "## Recommended VWAP-aware waves"])
    for wave in summary.get("recommended_next_waves") or []:
        lines.append(f"- {wave['name']}: `{wave['signature']}` - {wave['reason']}")
    if not summary.get("recommended_next_waves"):
        lines.append("- No permitted VWAP-aware waves.")
    lines.extend(["", "## Blocked waves"])
    for wave in summary.get("blocked_waves") or []:
        lines.append(f"- {wave['name']}: `{wave['reason']}` `{wave['signature']}`")
    if not summary.get("blocked_waves"):
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Safety",
            "- No paper.",
            "- No live.",
            "- No orders.",
            "- No wave executed.",
            "- IBKR used: `False`.",
            "",
            "## Director note",
            "VWAP analysis is read-only and proposes search-space candidates only.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _load_universe_symbols(path: str | Path, *, limit: int) -> list[str]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    symbols: list[str] = []
    for row in rows:
        selected = str(row.get("selected", "true")).strip().lower()
        status = str(row.get("status", "")).strip().lower()
        if selected not in {"true", "1", "yes", "y"} and status not in {"selected", ""}:
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        if symbol:
            symbols.append(symbol)
        if len(symbols) >= limit:
            break
    return symbols


def _load_prohibited_repeats(path: str | Path | None) -> tuple[str, ...]:
    if not path:
        return ()
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ()
    return tuple(str(item) for item in payload.get("prohibited_repeats") or ())


def _symbol_stats(symbol: str, frame: pd.DataFrame) -> dict[str, Any]:
    crosses = frame["crossed_above_vwap"].astype(bool) | frame["crossed_below_vwap"].astype(bool)
    slope = frame["vwap_slope_direction"].astype(str)
    above_pct = _pct(frame["above_vwap"])
    below_pct = _pct(frame["below_vwap"])
    chop_rate = _round(float(crosses.sum()) / float(len(frame))) if len(frame) else None
    return {
        "symbol": symbol,
        "bars": int(len(frame)),
        "above_vwap_pct": above_pct,
        "below_vwap_pct": below_pct,
        "crosses_count": int(crosses.sum()),
        "chop_rate": chop_rate,
        "median_distance_bps": _round(frame["vwap_distance_bps"].median()),
        "p90_abs_distance_bps": _round(frame["vwap_distance_bps"].abs().quantile(0.90)),
        "session_open_above_vwap_pct": _bucket_above_pct(frame, "open"),
        "session_close_above_vwap_pct": _bucket_above_pct(frame, "close"),
        "trend_bias": _trend_bias(above_pct, below_pct, chop_rate, slope),
        "data_status": "OK",
    }


def _vwap_summary(frame: pd.DataFrame, symbol_stats: list[dict[str, Any]]) -> dict[str, Any]:
    if frame.empty:
        return {
            "bars_analyzed": 0,
            "above_vwap_pct": None,
            "below_vwap_pct": None,
            "median_distance_bps": None,
            "p90_abs_distance_bps": None,
            "vwap_crosses_per_symbol_median": None,
            "vwap_chop_rate": None,
        }
    crosses_per_symbol = [row["crosses_count"] for row in symbol_stats]
    crosses = frame["crossed_above_vwap"].astype(bool) | frame["crossed_below_vwap"].astype(bool)
    return {
        "bars_analyzed": int(len(frame)),
        "above_vwap_pct": _pct(frame["above_vwap"]),
        "below_vwap_pct": _pct(frame["below_vwap"]),
        "median_distance_bps": _round(frame["vwap_distance_bps"].median()),
        "p90_abs_distance_bps": _round(frame["vwap_distance_bps"].abs().quantile(0.90)),
        "vwap_crosses_per_symbol_median": _round(float(np.median(crosses_per_symbol))) if crosses_per_symbol else None,
        "vwap_chop_rate": _round(float(crosses.sum()) / float(len(frame))),
    }


def _session_bucket_stats(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if frame.empty:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for bucket, bucket_frame in frame.groupby("session_bucket"):
        out[str(bucket)] = {
            "bars": int(len(bucket_frame)),
            "above_vwap_pct": _pct(bucket_frame["above_vwap"]),
            "below_vwap_pct": _pct(bucket_frame["below_vwap"]),
            "median_distance_bps": _round(bucket_frame["vwap_distance_bps"].median()),
        }
    return out


def _filter_prohibited_candidates(
    candidates: list[dict[str, Any]], prohibited_repeats: tuple[str, ...]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    prohibited = {normalize_wave_signature(item) for item in prohibited_repeats}
    recommended: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for candidate in candidates:
        if normalize_wave_signature(str(candidate["signature"])) in prohibited:
            blocked.append(candidate | {"reason": "prohibited_repeat"})
        else:
            recommended.append(candidate)
    return recommended, blocked


def _pct(values: pd.Series) -> float | None:
    if values.empty:
        return None
    return _round(float(values.astype(bool).mean() * 100.0))


def _bucket_above_pct(frame: pd.DataFrame, bucket: str) -> float | None:
    bucket_frame = frame[frame["session_bucket"] == bucket]
    return _pct(bucket_frame["above_vwap"]) if not bucket_frame.empty else None


def _trend_bias(above_pct: float | None, below_pct: float | None, chop_rate: float | None, slope: pd.Series) -> str:
    if above_pct is None or below_pct is None or chop_rate is None:
        return "unknown"
    if chop_rate >= 0.18:
        return "chop"
    up_or_flat = float(slope.isin(["up", "flat"]).mean() * 100.0)
    down_or_flat = float(slope.isin(["down", "flat"]).mean() * 100.0)
    if above_pct >= 55.0 and up_or_flat >= 50.0:
        return "above_rising"
    if below_pct >= 55.0 and down_or_flat >= 50.0:
        return "below_falling"
    return "mixed"


def _round(value: Any) -> float | None:
    if pd.isna(value):
        return None
    return round(float(value), 6)
