from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import DiscoveredPattern, DiscoveredPatternMatch
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.services.data_provider import MarketDataProvider, pick_symbols
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.technical_indicators import atr, normalize_ohlcv


@dataclass(slots=True)
class NovelPatternMatcher:
    """Find current charts that look like validated LAB patterns.

    Matches remain in `lab_watchlist`. This is not a trading signal generator; it
    is the bridge between discovery and later paper-trading validation.
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
        store: bool = True,
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
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
        for pattern in patterns:
            scaler_mean, scaler_scale = self._scaler(pattern)
            centroid = np.asarray(pattern.centroid_json, dtype=float)
            if scaler_mean is None or scaler_scale is None or len(centroid) == 0:
                continue
            for symbol in symbols:
                try:
                    df = normalize_ohlcv(
                        self.provider.fetch_ohlcv(symbol, period=settings.discovery_period, interval=pattern.timeframe)
                    )
                    if len(df) < pattern.window_size + 20:
                        continue
                    window = df.iloc[-pattern.window_size :]
                    vector, features, chart = engine.embed(window)
                    if len(vector) != len(centroid):
                        continue
                    scaled = (vector - scaler_mean) / np.where(scaler_scale == 0, 1.0, scaler_scale)
                    normalized_distance = float(np.linalg.norm(scaled - centroid) / max(1.0, np.sqrt(len(centroid))))
                    similarity = float(1.0 / (1.0 + normalized_distance))
                    if similarity < threshold:
                        continue
                    prices = self._prices(pattern, df)
                    score = round(similarity * 0.55 + pattern.score * 0.30 + pattern.stability_score * 0.15, 6)
                    match = {
                        "pattern_id": pattern.id,
                        "pattern_name": pattern.name,
                        "pattern_key": pattern.pattern_key,
                        "symbol": symbol,
                        "timeframe": pattern.timeframe,
                        "side": pattern.side,
                        "similarity": round(similarity, 6),
                        "score": score,
                        "entry_price": prices["entry_price"],
                        "stop_price": prices["stop_price"],
                        "target_price": prices["target_price"],
                        "reward_risk": settings.unvalidated_pattern_min_reward_risk,
                        "window_end": str(df.index[-1]),
                        "status": "lab_watchlist",
                        "notes": "Match de patrón descubierto; requiere paper validation y aprobación antes de uso operativo.",
                        "chart": chart,
                        "metrics": {
                            "pattern_score": pattern.score,
                            "pattern_expectancy_r": pattern.expectancy_r,
                            "pattern_profit_factor": pattern.profit_factor,
                            "pattern_stability_score": pattern.stability_score,
                            "features": features,
                        },
                    }
                    matches.append(match)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("novel pattern match failed for {} / {}: {}", pattern.name, symbol, exc)
                    continue
        matches = sorted(matches, key=lambda m: m["score"], reverse=True)[: settings.discovery_match_max_results]
        if store:
            self._store_matches(db, matches)
        return {
            "patterns_checked": len(patterns),
            "symbols_checked": len(symbols),
            "matches": matches,
            "stored_matches": len(matches) if store else 0,
            "similarity_threshold": threshold,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _scaler(pattern: DiscoveredPattern) -> tuple[np.ndarray | None, np.ndarray | None]:
        metrics = pattern.metrics_json or {}
        mean = metrics.get("scaler_mean")
        scale = metrics.get("scaler_scale")
        if not isinstance(mean, list) or not isinstance(scale, list):
            return None, None
        return np.asarray(mean, dtype=float), np.asarray(scale, dtype=float)

    def _prices(self, pattern: DiscoveredPattern, df) -> dict[str, float]:
        settings = self.settings
        assert settings is not None
        entry = float(df["close"].iloc[-1])
        atr_value = float(atr(df, 14).iloc[-1]) if len(df) >= 15 else entry * 0.02
        risk = max(atr_value * 1.5, entry * 0.015, 0.01)
        if pattern.side == "short":
            stop = entry + risk
            target = entry - settings.unvalidated_pattern_min_reward_risk * risk
        else:
            stop = entry - risk
            target = entry + settings.unvalidated_pattern_min_reward_risk * risk
        return {
            "entry_price": round(entry, 4),
            "stop_price": round(stop, 4),
            "target_price": round(target, 4),
        }

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
