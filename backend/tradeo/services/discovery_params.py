from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Callable

from tradeo.core.config import Settings
from tradeo.research.intraday_context_filters import normalize_context_filter_spec
from tradeo.research.intraday_vwap_conditions import expected_side_from_vwap_condition
from tradeo.schemas import DiscoveryRunRequest
from tradeo.services.data_provider import resolve_universe_for_interval


def file_sha256(path: str | os.PathLike[str]) -> str:
    try:
        with open(path, "rb") as handle:
            digest = hashlib.sha256()
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
            return digest.hexdigest()
    except OSError:
        return ""


def discovery_universe_key(
    *,
    scope: str,
    universe_file: str,
    universe_hash: str | None = None,
) -> str:
    sha256 = file_sha256(universe_file) if universe_hash is None else universe_hash
    payload = {
        "scope": scope,
        "file": str(universe_file),
        "sha256": sha256,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return f"{scope}:{digest}"


def resolve_discovery_run_params(
    settings: Settings,
    request: DiscoveryRunRequest,
    *,
    file_hasher: Callable[[str | os.PathLike[str]], str] = file_sha256,
) -> dict[str, Any]:
    max_total_windows = min(request.max_total_windows or settings.discovery_max_total_windows, 80_000)
    universe_selection = resolve_universe_for_interval(
        settings,
        request.interval or settings.discovery_interval,
        daily_cap_segment=request.daily_cap_segment,
    )
    universe_scope = universe_selection.scope
    universe_file = universe_selection.universe_file
    universe_hash = file_hasher(universe_file)
    is_intraday = universe_selection.daily_cap_segment is None
    context_spec = normalize_context_filter_spec(
        session_filter=request.session_filter,
        cost_filter=request.cost_filter,
        max_execution_cost_r=request.max_execution_cost_r,
    )
    return {
        "limit": request.limit or settings.discovery_limit_default,
        "period": request.period or settings.discovery_period,
        "interval": request.interval or settings.discovery_interval,
        "cadence": "intraday" if is_intraday else "daily",
        "universe_scope": universe_scope,
        "universe_file": universe_file,
        "daily_cap_segment": universe_selection.daily_cap_segment,
        "universe_hash": universe_hash,
        "universe_key": discovery_universe_key(
            scope=universe_scope,
            universe_file=universe_file,
            universe_hash=universe_hash,
        ),
        "symbols": [symbol.upper().strip() for symbol in request.symbols if symbol.strip()]
        if request.symbols
        else None,
        "window_sizes": request.window_sizes or settings.discovery_window_size_list,
        "forward_bars": request.forward_bars or settings.discovery_forward_bar_list,
        "stride": max(1, request.stride or settings.discovery_stride),
        "max_total_windows": max(100, max_total_windows),
        "max_windows_per_symbol": max(
            50, request.max_windows_per_symbol or settings.discovery_max_windows_per_symbol
        ),
        "min_cluster_size": max(20, request.min_cluster_size or settings.discovery_min_cluster_size),
        "max_clusters_per_window": max(
            2,
            min(
                request.max_clusters_per_window or settings.discovery_max_clusters_per_window,
                40,
            ),
        ),
        "store_rejected": settings.discovery_store_rejected
        if request.store_rejected is None
        else request.store_rejected,
        "daily_event_min_gain_pct": 0.0
        if is_intraday
        else (
            max(0.0, float(request.daily_event_min_gain_pct))
            if request.daily_event_min_gain_pct is not None
            else max(0.0, float(settings.discovery_daily_event_min_gain_pct))
        ),
        "vwap_condition": (request.vwap_condition or "none").strip().lower() or "none",
        "vwap_side_bias": (request.vwap_side_bias or "").strip().lower() or None,
        "vwap_expected_side": expected_side_from_vwap_condition(
            request.vwap_condition,
            request.vwap_side_bias,
        ),
        "vwap_max_distance_bps": request.vwap_max_distance_bps,
        "vwap_min_slope_bps": request.vwap_min_slope_bps,
        "session_filter": context_spec.session_filter,
        "cost_filter": context_spec.cost_filter,
        "max_execution_cost_r": context_spec.max_execution_cost_r,
        "rr_levels": settings.discovery_rr_level_list,
        "min_reward_risk": settings.discovery_min_reward_risk,
        "candidate_reward_risk": settings.discovery_candidate_reward_risk,
        "premium_reward_risk": settings.discovery_premium_reward_risk,
        "max_drawdown_r": settings.discovery_max_drawdown_r,
        "walk_forward_folds": settings.discovery_walk_forward_folds,
        "walk_forward_embargo_samples": settings.discovery_walk_forward_embargo_samples,
        "cost_stress_multipliers": settings.discovery_cost_stress_multiplier_list,
        "required_cost_stress_multiplier": settings.discovery_required_cost_stress_multiplier,
        "min_samples": settings.intraday_research_min_samples
        if is_intraday
        else settings.discovery_min_samples,
        "min_effective_samples": (
            settings.intraday_research_min_effective_samples
            if is_intraday
            else settings.discovery_min_effective_samples
        ),
        "min_symbols": settings.intraday_research_min_symbols
        if is_intraday
        else settings.discovery_min_symbols,
        "min_years": settings.intraday_research_min_years
        if is_intraday
        else settings.discovery_min_years,
    }
