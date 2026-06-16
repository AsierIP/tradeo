from __future__ import annotations

import math
from typing import Any

from tradeo.core.config import Settings


def rank_entry_matches(
    matches: list[dict[str, Any]],
    *,
    settings: Settings,
    execution_history: dict[tuple[str, ...], dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    history = execution_history or {}
    ranked: list[dict[str, Any]] = []
    for match in matches:
        enriched = dict(match)
        score, components, reason = _opportunity_score(
            enriched,
            settings=settings,
            execution_history=history,
        )
        enriched["opportunity_rank_score"] = score
        enriched["opportunity_rank_components"] = components
        enriched["opportunity_rank_reason"] = reason
        ranked.append(enriched)
    ranked.sort(
        key=lambda item: (
            float(item.get("opportunity_rank_score") or 0.0),
            float(item.get("entry_score") or 0.0),
            float(item.get("score") or 0.0),
        ),
        reverse=True,
    )
    for index, match in enumerate(ranked, start=1):
        match["opportunity_rank"] = index
    return ranked


def _opportunity_score(
    match: dict[str, Any],
    *,
    settings: Settings,
    execution_history: dict[tuple[str, ...], dict[str, float]],
) -> tuple[float, dict[str, float], str]:
    metrics = match.get("metrics") or {}
    features = metrics.get("features") or {}
    entry_gate = metrics.get("entry_gate") or {}
    similarity = _bounded(match.get("similarity"), default=0.0)
    match_score = _bounded(match.get("score"), default=0.0)
    entry_score = _bounded(entry_gate.get("entry_score", match.get("entry_score")), default=match_score)
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
        _safe_float(match.get("reward_risk"), 0.0) / max(settings.min_reward_risk, 1.0),
        default=0.0,
    )
    regime_fit = _bounded(((match.get("regime_fit") or {}).get("score")), default=0.5)
    avg_dollar_volume = _safe_float(features.get("avg_dollar_volume"), 0.0)
    liquidity = _bounded(
        avg_dollar_volume / max(settings.min_avg_dollar_volume * 5.0, 1.0),
        default=0.5 if settings.min_avg_dollar_volume <= 0 else 0.0,
    )
    history_score, history_count, history_item = _history_score(match, execution_history)
    exploration_bonus = max(0.0, 1.0 - min(history_count, 10.0) / 10.0) * max(
        0.0,
        min(0.30, float(settings.entry_exploration_rate)),
    )
    research_edge = expectancy * 0.55 + profit_factor * 0.30 + stability * 0.15
    components = {
        "entry": round(entry_score, 4),
        "match": round(match_score, 4),
        "similarity": round(similarity, 4),
        "research_edge": round(research_edge, 4),
        "reward_risk": round(reward_risk, 4),
        "liquidity": round(liquidity, 4),
        "regime_fit": round(regime_fit, 4),
        "execution_history": round(history_score, 4),
        "history_count": round(history_count, 4),
        "history_expectancy_r": round(_safe_float(history_item.get("expectancy_r"), 0.0), 4),
        "history_win_rate": round(_safe_float(history_item.get("win_rate"), 0.0), 4),
        "history_profit_factor": round(_safe_float(history_item.get("profit_factor"), 0.0), 4),
        "history_max_drawdown_r": round(_safe_float(history_item.get("max_drawdown_r"), 0.0), 4),
        "history_decay": round(_safe_float(history_item.get("decay_score"), 0.5), 4),
        "exploration": round(exploration_bonus, 4),
    }
    if history_count > 0:
        score = round(
            components["execution_history"] * 0.34
            + components["entry"] * 0.18
            + components["match"] * 0.10
            + components["research_edge"] * 0.10
            + components["reward_risk"] * 0.08
            + components["liquidity"] * 0.06
            + components["regime_fit"] * 0.08
            + components["similarity"] * 0.03
            + components["exploration"] * 0.03,
            6,
        )
        reason = "paper_history_weighted"
    else:
        score = round(
            components["entry"] * 0.22
            + components["match"] * 0.14
            + components["research_edge"] * 0.18
            + components["reward_risk"] * 0.10
            + components["liquidity"] * 0.08
            + components["regime_fit"] * 0.10
            + components["execution_history"] * 0.12
            + components["similarity"] * 0.04
            + components["exploration"] * 0.02,
            6,
        )
        reason = "research_score_fallback_no_paper_history"
    return score, components, reason


def _history_score(
    match: dict[str, Any],
    execution_history: dict[tuple[str, ...], dict[str, float]],
) -> tuple[float, float, dict[str, float]]:
    pattern = str(match.get("pattern_name") or "")
    symbol = str(match.get("symbol") or "")
    variant = str(match.get("entry_variant_id") or "")
    regime_key = str((match.get("regime") or {}).get("regime_key") or "")
    keys: tuple[tuple[str, ...], ...]
    if variant:
        keys = (
            (pattern, symbol, variant, regime_key),
            (pattern, "*", variant, regime_key),
            (pattern, symbol, variant, "*"),
            (pattern, "*", variant, "*"),
        )
    else:
        keys = (
            (pattern, symbol, "*", "*"),
            (pattern, "*", "*", "*"),
        )
    for key in keys:
        item = execution_history.get(key)
        if item:
            return float(item.get("score", 0.5)), float(item.get("count", 0.0)), item
    return 0.5, 0.0, {}


def _bounded(value: Any, *, default: float) -> float:
    number = _safe_float(value, default)
    return max(0.0, min(1.0, number))


def _safe_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default
