from __future__ import annotations

from typing import Any

from tradeo.core.config import Settings


def rank_entry_matches(
    matches: list[dict[str, Any]],
    *,
    settings: Settings,
    execution_history: dict[tuple[str, str], float] | None = None,
) -> list[dict[str, Any]]:
    history = execution_history or {}
    ranked: list[dict[str, Any]] = []
    for match in matches:
        enriched = dict(match)
        score, components = _opportunity_score(enriched, settings=settings, execution_history=history)
        enriched["opportunity_rank_score"] = score
        enriched["opportunity_rank_components"] = components
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
    execution_history: dict[tuple[str, str], float],
) -> tuple[float, dict[str, float]]:
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
    avg_dollar_volume = _safe_float(features.get("avg_dollar_volume"), 0.0)
    liquidity = _bounded(
        avg_dollar_volume / max(settings.min_avg_dollar_volume * 5.0, 1.0),
        default=0.5 if settings.min_avg_dollar_volume <= 0 else 0.0,
    )
    history_score = _history_score(match, execution_history)
    research_edge = expectancy * 0.55 + profit_factor * 0.30 + stability * 0.15
    components = {
        "entry": round(entry_score, 4),
        "match": round(match_score, 4),
        "similarity": round(similarity, 4),
        "research_edge": round(research_edge, 4),
        "reward_risk": round(reward_risk, 4),
        "liquidity": round(liquidity, 4),
        "execution_history": round(history_score, 4),
    }
    score = round(
        components["entry"] * 0.24
        + components["match"] * 0.16
        + components["research_edge"] * 0.20
        + components["reward_risk"] * 0.12
        + components["liquidity"] * 0.10
        + components["execution_history"] * 0.12
        + components["similarity"] * 0.06,
        6,
    )
    return score, components


def _history_score(
    match: dict[str, Any],
    execution_history: dict[tuple[str, str], float],
) -> float:
    pattern = str(match.get("pattern_name") or "")
    symbol = str(match.get("symbol") or "")
    return execution_history.get((pattern, symbol), execution_history.get((pattern, "*"), 0.5))


def _bounded(value: Any, *, default: float) -> float:
    number = _safe_float(value, default)
    return max(0.0, min(1.0, number))


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
