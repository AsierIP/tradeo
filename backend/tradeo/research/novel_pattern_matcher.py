from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Literal

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import DiscoveredPattern, DiscoveredPatternMatch, DiscoveredPatternStatus
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.services.data_provider import MarketDataProvider, pick_symbols
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.technical_indicators import atr, normalize_ohlcv


@dataclass(slots=True)
class NovelPatternMatcher:
    """Find current charts that look like validated discovered patterns.

    This is still not an execution layer. Laboratory/Fox Hunter scanners decide
    whether a match becomes a signal or an IB order.
    """

    provider: MarketDataProvider | None = None
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.provider = self.provider or get_market_data_provider()

    def match_current(
        self,
        db: Session,
        symbols: list[str] | None = None,
        limit: int | None = None,
        max_patterns: int | None = None,
        similarity_threshold: float | None = None,
        module: Literal["laboratory", "fox_hunter"] = "laboratory",
        store: bool = True,
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        statuses = self._statuses_for_module(module)
        patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(DiscoveredPattern.status.in_(statuses))
            .order_by(DiscoveredPattern.score.desc())
            .limit(max_patterns or settings.discovery_match_max_patterns)
            .all()
        )
        if symbols is None:
            symbols = pick_symbols(limit=limit or settings.discovery_match_symbol_limit)
        else:
            symbols = [s.upper().strip() for s in symbols if s.strip()]
        threshold = similarity_threshold or settings.discovery_match_similarity_threshold
        matches: list[dict[str, Any]] = []
        engine = PatternEmbeddingEngine()
        required_bars_by_timeframe = self._required_bars_by_timeframe(patterns)
        data_cache: dict[tuple[str, str], pd.DataFrame | None] = {}
        for pattern in patterns:
            scaler_mean, scaler_scale = self._scaler(pattern)
            centroid = np.asarray(pattern.centroid_json, dtype=float)
            if scaler_mean is None or scaler_scale is None or len(centroid) == 0:
                continue
            for symbol in symbols:
                try:
                    df = self._current_data(
                        symbol,
                        pattern.timeframe,
                        required_bars=required_bars_by_timeframe[pattern.timeframe],
                        cache=data_cache,
                    )
                    if df is None:
                        continue
                    if len(df) < pattern.window_size + 20:
                        continue
                    window = df.iloc[-pattern.window_size :]
                    vector, features, chart = engine.embed(window)
                    if len(vector) != len(centroid):
                        continue
                    scaled = (vector - scaler_mean) / np.where(scaler_scale == 0, 1.0, scaler_scale)
                    normalized_distance = float(
                        np.linalg.norm(scaled - centroid) / max(1.0, np.sqrt(len(centroid)))
                    )
                    similarity = float(1.0 / (1.0 + normalized_distance))
                    if similarity < threshold:
                        continue
                    features = dict(features)
                    features["avg_dollar_volume"] = float(
                        (df["close"] * df["volume"]).tail(20).mean()
                    )
                    reward_risk = float(
                        pattern.best_rr or settings.unvalidated_pattern_min_reward_risk
                    )
                    prices = self._prices(pattern, df, reward_risk=reward_risk)
                    score = round(
                        similarity * 0.55 + pattern.score * 0.30 + pattern.stability_score * 0.15,
                        6,
                    )
                    entry_gate = self._entry_gate(pattern.side, df, score=score, settings=settings)
                    match_status = (
                        "production_entry_candidate"
                        if module == "fox_hunter"
                        else "lab_entry_candidate"
                    )
                    match = {
                        "module": module,
                        "pattern_id": pattern.id,
                        "pattern_name": pattern.name,
                        "pattern_key": pattern.pattern_key,
                        "pattern_status": pattern.status.value,
                        "pattern_promotion_status": pattern.promotion_status,
                        "symbol": symbol,
                        "timeframe": pattern.timeframe,
                        "side": pattern.side,
                        "similarity": round(similarity, 6),
                        "score": score,
                        "entry_score": entry_gate["entry_score"],
                        "entry_gate_passed": entry_gate["passed"],
                        "entry_trigger": entry_gate["trigger"],
                        "entry_price": prices["entry_price"],
                        "stop_price": prices["stop_price"],
                        "target_price": prices["target_price"],
                        "reward_risk": reward_risk,
                        "window_end": str(df.index[-1]),
                        "status": match_status,
                        "notes": self._notes_for_module(module),
                        "chart": chart,
                        "metrics": {
                            "entry_module": module,
                            "pattern_status": pattern.status.value,
                            "pattern_promotion_status": pattern.promotion_status,
                            "pattern_score": pattern.score,
                            "pattern_expectancy_r": pattern.expectancy_r,
                            "pattern_profit_factor": pattern.profit_factor,
                            "pattern_stability_score": pattern.stability_score,
                            "features": features,
                            "entry_gate": entry_gate,
                        },
                    }
                    matches.append(match)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "novel pattern match failed for {} / {}: {}",
                        pattern.name,
                        symbol,
                        exc,
                    )
                    continue
        matches = sorted(matches, key=lambda m: m["score"], reverse=True)[
            : settings.discovery_match_max_results
        ]
        if store:
            self._store_matches(db, matches)
        return {
            "patterns_checked": len(patterns),
            "symbols_checked": len(symbols),
            "matches": matches,
            "stored_matches": len(matches) if store else 0,
            "module": module,
            "similarity_threshold": threshold,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _statuses_for_module(module: str) -> list[DiscoveredPatternStatus]:
        if module == "fox_hunter":
            return [DiscoveredPatternStatus.PRODUCTION]
        return [
            DiscoveredPatternStatus.LAB,
            DiscoveredPatternStatus.LAB_WATCHLIST,
            DiscoveredPatternStatus.LAB_CANDIDATE,
            DiscoveredPatternStatus.DIRECTOR_REVIEW,
            DiscoveredPatternStatus.PREMIUM_CANDIDATE,
            DiscoveredPatternStatus.PAPER_CANDIDATE,
        ]

    @staticmethod
    def _notes_for_module(module: str) -> str:
        if module == "fox_hunter":
            return (
                "Match de patrón de Producción; requiere live_armed "
                "y auditoría continua de Director."
            )
        return (
            "Match de patrón de Laboratorio; requiere paper validation "
            "y auditoría de Director."
        )

    @staticmethod
    def _entry_gate(side: str, df: pd.DataFrame, *, score: float, settings: Settings) -> dict[str, Any]:
        latest = df.iloc[-1]
        previous = df.iloc[-21:-1] if len(df) >= 21 else df.iloc[:-1]
        if previous.empty:
            return {
                "passed": False,
                "trigger": "insufficient_history",
                "entry_score": 0.0,
                "reason": "not enough bars for entry trigger",
            }
        close = float(latest["close"])
        open_ = float(latest["open"])
        high = float(latest["high"])
        low = float(latest["low"])
        prev_close = float(previous["close"].iloc[-1])
        prev_high = float(previous["high"].max())
        prev_low = float(previous["low"].min())
        avg_volume = float(previous["volume"].tail(20).mean())
        volume_ratio = float(latest["volume"] / max(avg_volume, 1.0))
        sma20 = float(df["close"].tail(20).mean())
        atr_value = float(atr(df, 14).iloc[-1]) if len(df) >= 15 else max(close * 0.02, 0.01)
        extension_atr = abs(close - sma20) / max(atr_value, 0.01)
        extension_score = max(0.0, min(1.0, 1.0 - extension_atr / settings.entry_max_extension_atr))
        volume_score = max(0.0, min(1.0, (volume_ratio - 0.8) / 1.2))

        if side.lower() == "short":
            breakout = close <= prev_low * 1.005
            reclaim = high >= prev_low and close < prev_low * 1.01 and close < open_
            momentum = close < prev_close and close < sma20
        else:
            breakout = close >= prev_high * 0.995
            reclaim = low <= prev_high and close > prev_high * 0.99 and close > open_
            momentum = close > prev_close and close > sma20

        if breakout:
            trigger = "breakout"
            trigger_score = 1.0
        elif reclaim:
            trigger = "pullback_reclaim"
            trigger_score = 0.78
        elif momentum:
            trigger = "momentum_close"
            trigger_score = 0.58
        else:
            trigger = "no_operational_trigger"
            trigger_score = 0.0

        entry_score = round(
            score * 0.45 + trigger_score * 0.25 + volume_score * 0.15 + extension_score * 0.15,
            6,
        )
        volume_confirmed = volume_ratio >= settings.entry_min_volume_ratio
        not_extended = extension_atr <= settings.entry_max_extension_atr
        passed = (
            trigger_score > 0
            and entry_score >= settings.entry_min_score
            and volume_confirmed
            and not_extended
        )
        return {
            "passed": passed,
            "trigger": trigger,
            "entry_score": entry_score,
            "trigger_score": round(trigger_score, 4),
            "volume_ratio": round(volume_ratio, 4),
            "volume_confirmed": volume_confirmed,
            "extension_atr": round(extension_atr, 4),
            "not_extended": not_extended,
            "prev_high_20": round(prev_high, 4),
            "prev_low_20": round(prev_low, 4),
            "sma20": round(sma20, 4),
            "close": round(close, 4),
            "reason": "entry gate passed" if passed else "entry gate failed",
        }

    @staticmethod
    def _scaler(pattern: DiscoveredPattern) -> tuple[np.ndarray | None, np.ndarray | None]:
        metrics = pattern.metrics_json or {}
        mean = metrics.get("scaler_mean")
        scale = metrics.get("scaler_scale")
        if not isinstance(mean, list) or not isinstance(scale, list):
            return None, None
        return np.asarray(mean, dtype=float), np.asarray(scale, dtype=float)

    def _prices(self, pattern: DiscoveredPattern, df, *, reward_risk: float) -> dict[str, float]:
        entry = float(df["close"].iloc[-1])
        atr_value = float(atr(df, 14).iloc[-1]) if len(df) >= 15 else entry * 0.02
        risk = max(atr_value * 1.5, entry * 0.015, 0.01)
        if pattern.side == "short":
            stop = entry + risk
            target = entry - reward_risk * risk
        else:
            stop = entry - risk
            target = entry + reward_risk * risk
        return {
            "entry_price": round(entry, 4),
            "stop_price": round(stop, 4),
            "target_price": round(target, 4),
        }

    @staticmethod
    def _required_bars_by_timeframe(patterns: list[DiscoveredPattern]) -> dict[str, int]:
        required: dict[str, int] = {}
        for pattern in patterns:
            current = required.get(pattern.timeframe, 0)
            required[pattern.timeframe] = max(current, int(pattern.window_size) + 30)
        return required

    def _current_data(
        self,
        symbol: str,
        timeframe: str,
        *,
        required_bars: int,
        cache: dict[tuple[str, str], pd.DataFrame | None],
    ) -> pd.DataFrame | None:
        key = (symbol.upper(), timeframe)
        if key in cache:
            return cache[key].copy() if cache[key] is not None else None
        assert self.provider is not None
        period = self._current_match_period(timeframe, required_bars=required_bars)
        try:
            df = normalize_ohlcv(
                self.provider.fetch_ohlcv(
                    symbol,
                    period=period,
                    interval=timeframe,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("current data fetch failed for {} / {}: {}", symbol, timeframe, exc)
            cache[key] = None
            return None
        cache[key] = df
        return df.copy()

    @staticmethod
    def _current_match_period(timeframe: str, *, required_bars: int) -> str:
        interval = timeframe.lower().strip()
        if interval in {"1d", "1 day"}:
            calendar_days = math.ceil(required_bars * 7 / 5) + 10
            months = max(3, math.ceil(calendar_days / 30))
            return f"{months}mo"
        if interval in {"1wk", "1 week"}:
            months = max(12, math.ceil(required_bars * 7 / 30))
            return f"{months}mo"
        if interval in {"1h", "30m", "30 mins", "15m", "15 mins"}:
            days = max(10, math.ceil(required_bars / 6) + 5)
            return f"{days}d"
        if interval in {"5m", "5 mins", "1m", "1 min"}:
            days = max(3, math.ceil(required_bars / 60) + 2)
            return f"{days}d"
        return "6mo"

    @staticmethod
    def _store_matches(db: Session, matches: list[dict[str, Any]]) -> None:
        for match in matches:
            db.add(
                DiscoveredPatternMatch(
                    pattern_id=int(match["pattern_id"]),
                    symbol=str(match["symbol"]),
                    timeframe=str(match["timeframe"]),
                    side=str(match["side"]),
                    similarity=float(match["similarity"]),
                    score=float(match["score"]),
                    entry_price=float(match["entry_price"]),
                    stop_price=float(match["stop_price"]),
                    target_price=float(match["target_price"]),
                    reward_risk=float(match["reward_risk"]),
                    window_end=str(match["window_end"]),
                    status=str(match["status"]),
                    notes=str(match["notes"]),
                    chart_json=match.get("chart", {}),
                    metrics_json=match.get("metrics", {}),
                )
            )
        db.commit()
