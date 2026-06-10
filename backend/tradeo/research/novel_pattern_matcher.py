from __future__ import annotations

from collections import defaultdict
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
from tradeo.services.entry_variants import (
    build_entry_audit_context,
    build_entry_variants,
    classify_regime,
)
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.modules.fox_hunter.production_manifest import (
    production_manifest_for_pattern,
    production_manifest_is_active,
)
from tradeo.services.market_session import REGULAR_CLOSE, US_EQUITY_TZ
from tradeo.services.state_policy import LAB_RUNTIME_STATES, PRODUCTION_RUNTIME_STATES
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
        pattern_limit = max_patterns or settings.discovery_match_max_patterns
        pattern_query = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(DiscoveredPattern.status.in_(statuses))
            .order_by(DiscoveredPattern.score.desc())
        )
        if module == "fox_hunter":
            patterns = [
                pattern
                for pattern in pattern_query.all()
                if production_manifest_is_active(pattern)
            ][:pattern_limit]
        else:
            patterns = pattern_query.limit(pattern_limit).all()
        if symbols is None:
            symbols = pick_symbols(limit=limit or settings.discovery_match_symbol_limit)
        else:
            symbols = [s.upper().strip() for s in symbols if s.strip()]
        threshold = similarity_threshold or settings.discovery_match_similarity_threshold
        matches: list[dict[str, Any]] = []
        engine = PatternEmbeddingEngine()
        required_bars_by_timeframe = self._required_bars_by_timeframe(patterns)
        data_cache: dict[tuple[str, str], pd.DataFrame | None] = {}
        benchmark_cache: dict[str, dict[str, pd.DataFrame]] = {}
        embedding_cache: dict[
            tuple[str, str, int],
            tuple[pd.DataFrame, np.ndarray, dict[str, float], dict[str, list[float]]] | None,
        ] = {}
        patterns_by_timeframe: dict[str, list[DiscoveredPattern]] = defaultdict(list)
        for pattern in patterns:
            patterns_by_timeframe[pattern.timeframe].append(pattern)

        for timeframe, timeframe_patterns in patterns_by_timeframe.items():
            required_bars = required_bars_by_timeframe[timeframe]
            benchmark_cache[timeframe] = self._benchmark_frames(
                timeframe,
                required_bars=required_bars,
                cache=data_cache,
            )
            for symbol in symbols:
                df = self._current_data(
                    symbol,
                    timeframe,
                    required_bars=required_bars,
                    cache=data_cache,
                )
                if df is None:
                    continue
                for window_size in sorted({pattern.window_size for pattern in timeframe_patterns}):
                    cache_key = (symbol.upper(), timeframe, int(window_size))
                    if cache_key not in embedding_cache:
                        if len(df) < int(window_size) + 20:
                            embedding_cache[cache_key] = None
                        else:
                            try:
                                window = df.iloc[-int(window_size) :]
                                embedding_cache[cache_key] = (
                                    df,
                                    *engine.embed(window, benchmark_frames=benchmark_cache[timeframe]),
                                )
                            except Exception as exc:  # noqa: BLE001
                                logger.warning(
                                    "current embedding failed for {} / {} / w{}: {}",
                                    symbol,
                                    timeframe,
                                    window_size,
                                    exc,
                                )
                                embedding_cache[cache_key] = None

                for pattern in timeframe_patterns:
                    try:
                        scaler_mean, scaler_scale = self._scaler(pattern)
                        centroid = np.asarray(pattern.centroid_json, dtype=float)
                        if scaler_mean is None or scaler_scale is None or len(centroid) == 0:
                            continue
                        cached = embedding_cache.get((symbol.upper(), timeframe, int(pattern.window_size)))
                        if cached is None:
                            continue
                        df_for_match, vector, features, chart = cached
                        scaled = self._scaled_vector_for_pattern(vector, centroid, scaler_mean, scaler_scale)
                        if scaled is None:
                            continue
                        normalized_distance = float(
                            np.linalg.norm(scaled - centroid) / max(1.0, np.sqrt(len(centroid)))
                        )
                        similarity = float(1.0 / (1.0 + normalized_distance))
                        effective_threshold = self._effective_threshold(pattern, threshold)
                        if similarity < effective_threshold:
                            continue
                        features = dict(features)
                        features["avg_dollar_volume"] = float(
                            (df_for_match["close"] * df_for_match["volume"]).tail(20).mean()
                        )
                        reward_risk = float(
                            pattern.best_rr or settings.unvalidated_pattern_min_reward_risk
                        )
                        base_score = round(
                            similarity * 0.55 + pattern.score * 0.30 + pattern.stability_score * 0.15,
                            6,
                        )
                        base_gate = self._entry_gate(pattern.side, df_for_match, score=base_score, settings=settings)
                        regime = classify_regime(features, base_gate)
                        regime_fit = self._pattern_regime_fit(pattern, regime)
                        entry_audit = build_entry_audit_context(df_for_match, pattern.timeframe)
                        variants = build_entry_variants(
                            side=pattern.side,
                            df=df_for_match,
                            base_entry_gate=base_gate,
                            score=base_score,
                            reward_risk=reward_risk,
                            settings=settings,
                        )
                        if not variants:
                            continue
                        match_status = (
                            "production_entry_candidate"
                            if module == "fox_hunter"
                            else "lab_entry_candidate"
                        )
                        for variant in variants:
                            entry_gate = variant["entry_gate"]
                            score = round(
                                base_score * 0.78
                                + float(entry_gate.get("entry_score", 0.0)) * 0.14
                                + float(regime_fit["score"]) * 0.08,
                                6,
                            )
                            match = {
                                "module": module,
                                "pattern_id": pattern.id,
                                "pattern_name": pattern.name,
                                "pattern_key": pattern.pattern_key,
                                "pattern_family_key": pattern.pattern_family_key,
                                "canonical_pattern_key": pattern.canonical_pattern_key,
                                "pattern_status": pattern.status.value,
                                "pattern_promotion_status": pattern.promotion_status,
                                "production_manifest": (
                                    production_manifest_for_pattern(pattern)
                                    if module == "fox_hunter"
                                    else None
                                ),
                                "symbol": symbol,
                                "timeframe": pattern.timeframe,
                                "side": pattern.side,
                                "similarity": round(similarity, 6),
                                "similarity_threshold_used": round(effective_threshold, 6),
                                "score": score,
                                "entry_score": entry_gate["entry_score"],
                                "entry_gate_passed": entry_gate["passed"],
                                "entry_trigger": entry_gate["trigger"],
                                "entry_variant_id": variant["entry_variant_id"],
                                "entry_variant": variant["entry_variant"],
                                "entry_price": variant["entry_price"],
                                "stop_price": variant["stop_price"],
                                "target_price": variant["target_price"],
                                "reward_risk": reward_risk,
                                "window_end": str(df_for_match.index[-1]),
                                "status": match_status,
                                "notes": self._notes_for_module(module),
                                "chart": chart,
                                "entry_audit": entry_audit,
                                "regime": regime,
                                "regime_fit": regime_fit,
                                "metrics": {
                                    "entry_module": module,
                                    "entry_variant_id": variant["entry_variant_id"],
                                    "entry_variant": variant["entry_variant"],
                                    "pattern_status": pattern.status.value,
                                    "pattern_promotion_status": pattern.promotion_status,
                                    "pattern_score": pattern.score,
                                    "pattern_expectancy_r": pattern.expectancy_r,
                                    "pattern_profit_factor": pattern.profit_factor,
                                    "pattern_stability_score": pattern.stability_score,
                                    "pattern_regime_profile": (pattern.metrics_json or {}).get("regime_profile", {}),
                                    "features": features,
                                    "entry_gate": entry_gate,
                                    "base_entry_gate": base_gate,
                                    "entry_audit": entry_audit,
                                    "regime": regime,
                                    "regime_fit": regime_fit,
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

    def _benchmark_frames(
        self,
        timeframe: str,
        *,
        required_bars: int,
        cache: dict[tuple[str, str], pd.DataFrame | None],
    ) -> dict[str, pd.DataFrame]:
        frames: dict[str, pd.DataFrame] = {}
        for symbol in ("SPY", "QQQ"):
            df = self._current_data(symbol, timeframe, required_bars=required_bars, cache=cache)
            if df is not None:
                frames[symbol] = df
        return frames

    @staticmethod
    def _statuses_for_module(module: str) -> list[DiscoveredPatternStatus]:
        if module == "fox_hunter":
            return list(PRODUCTION_RUNTIME_STATES)
        return list(LAB_RUNTIME_STATES)

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
    def _pattern_regime_fit(pattern: DiscoveredPattern, regime: dict[str, Any]) -> dict[str, Any]:
        profile = (pattern.metrics_json or {}).get("regime_profile", {})
        if not isinstance(profile, dict) or not profile:
            return {"score": 0.5, "label": "unknown_pattern_regime", "matched": False}
        regime_key = str(regime.get("regime_key") or "")
        preferred = profile.get("preferred_regime_keys")
        if isinstance(preferred, list) and preferred:
            if regime_key in {str(item) for item in preferred}:
                return {"score": 1.0, "label": "preferred_regime", "matched": True}
            return {"score": 0.35, "label": "outside_preferred_regime", "matched": False}
        buckets = profile.get("bucket_counts") if isinstance(profile.get("bucket_counts"), dict) else {}
        if not buckets and isinstance(profile.get("buckets"), dict):
            buckets = profile["buckets"]
        if regime_key and regime_key in buckets:
            return {"score": 0.85, "label": "seen_regime", "matched": True}
        dominant = str(profile.get("dominant_regime") or "")
        if dominant and regime_key and dominant in regime_key:
            return {"score": 0.75, "label": "dominant_regime_overlap", "matched": True}
        market = str(regime.get("market_regime") or "")
        trend = str(regime.get("trend_regime") or "")
        top_market = profile.get("top_market_regime")
        top_trend = profile.get("top_trend_regime")
        overlap = 0.0
        if top_market and str(top_market) == market:
            overlap += 0.25
        if top_trend and str(top_trend) == trend:
            overlap += 0.25
        return {
            "score": round(0.45 + overlap, 4),
            "label": "partial_regime_overlap" if overlap else "unseen_regime",
            "matched": bool(overlap),
        }

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
        sma50 = float(df["close"].tail(50).mean()) if len(df) >= 50 else sma20
        sma20_prev = float(df["close"].iloc[-40:-20].mean()) if len(df) >= 40 else sma20
        atr_value = float(atr(df, 14).iloc[-1]) if len(df) >= 15 else max(close * 0.02, 0.01)
        atr_pct = atr_value / max(close, 0.01)
        extension_atr = abs(close - sma20) / max(atr_value, 0.01)
        extension_score = max(0.0, min(1.0, 1.0 - extension_atr / settings.entry_max_extension_atr))
        volume_score = max(0.0, min(1.0, (volume_ratio - 0.8) / 1.2))
        volatility_ok = atr_pct <= settings.max_atr_pct
        if side.lower() == "short":
            trend_aligned = close <= sma20 and sma20 <= sma50 and sma20 <= sma20_prev * 1.01
        else:
            trend_aligned = close >= sma20 and sma20 >= sma50 and sma20 >= sma20_prev * 0.99
        trend_score = 1.0 if trend_aligned else 0.35
        volatility_score = 1.0 if volatility_ok else max(0.0, 1.0 - (atr_pct / max(settings.max_atr_pct, 0.01) - 1.0))
        regime_score = round(
            trend_score * 0.45 + volatility_score * 0.30 + extension_score * 0.15 + volume_score * 0.10,
            6,
        )
        regime_ok = regime_score >= settings.entry_min_regime_score

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
        rejection_reasons: list[str] = []
        if trigger_score <= 0:
            rejection_reasons.append("weak_trigger")
        if entry_score < settings.entry_min_score:
            rejection_reasons.append("weak_entry_score")
        if not regime_ok:
            rejection_reasons.append("regime_not_aligned")
        if not volume_confirmed:
            rejection_reasons.append("insufficient_volume")
        if not not_extended:
            rejection_reasons.append("excessive_extension")
        if not volatility_ok:
            rejection_reasons.append("excessive_volatility")
        passed = (
            trigger_score > 0
            and entry_score >= settings.entry_min_score
            and regime_ok
            and volume_confirmed
            and not_extended
        )
        reason = "entry gate passed" if passed else ";".join(rejection_reasons) or "entry gate failed"
        return {
            "passed": passed,
            "trigger": trigger,
            "entry_score": entry_score,
            "trigger_score": round(trigger_score, 4),
            "volume_ratio": round(volume_ratio, 4),
            "volume_confirmed": volume_confirmed,
            "atr_pct": round(atr_pct, 6),
            "volatility_ok": volatility_ok,
            "extension_atr": round(extension_atr, 4),
            "not_extended": not_extended,
            "regime_score": regime_score,
            "regime_ok": regime_ok,
            "trend_aligned": trend_aligned,
            "prev_high_20": round(prev_high, 4),
            "prev_low_20": round(prev_low, 4),
            "sma20": round(sma20, 4),
            "sma50": round(sma50, 4),
            "close": round(close, 4),
            "reason": reason,
            "rejection_reasons": rejection_reasons,
        }

    @staticmethod
    def _scaler(pattern: DiscoveredPattern) -> tuple[np.ndarray | None, np.ndarray | None]:
        metrics = pattern.metrics_json or {}
        mean = metrics.get("scaler_mean")
        scale = metrics.get("scaler_scale")
        if not isinstance(mean, list) or not isinstance(scale, list):
            return None, None
        return np.asarray(mean, dtype=float), np.asarray(scale, dtype=float)

    @staticmethod
    def _scaled_vector_for_pattern(
        vector: np.ndarray,
        centroid: np.ndarray,
        scaler_mean: np.ndarray,
        scaler_scale: np.ndarray,
    ) -> np.ndarray | None:
        if len(centroid) == 0 or len(vector) < len(centroid):
            return None
        if len(scaler_mean) < len(centroid) or len(scaler_scale) < len(centroid):
            return None
        vector_prefix = vector[: len(centroid)]
        mean_prefix = scaler_mean[: len(centroid)]
        scale_prefix = scaler_scale[: len(centroid)]
        return (vector_prefix - mean_prefix) / np.where(scale_prefix == 0, 1.0, scale_prefix)

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

    def _effective_threshold(self, pattern: DiscoveredPattern, floor: float) -> float:
        """Per-pattern similarity threshold; the global config value is a floor.

        A single global threshold misfits every cluster at once: compact clusters
        accept spurious matches and loose clusters never fire (P0-4). Research
        persists match_tau_similarity (the intra-cluster similarity percentile),
        and the matcher requires the stricter of the two.
        """
        settings = self.settings
        if settings is None or not settings.discovery_match_per_pattern_threshold:
            return floor
        tau = (pattern.metrics_json or {}).get("match_tau_similarity")
        try:
            tau = float(tau)
        except (TypeError, ValueError):
            return floor
        if not math.isfinite(tau) or tau <= 0.0:
            return floor
        return max(floor, tau)

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
        if self.settings and self.settings.discovery_match_complete_bars_only:
            df = self._drop_incomplete_daily_bar(df, timeframe)
        cache[key] = df
        return df.copy()

    @staticmethod
    def _drop_incomplete_daily_bar(
        df: pd.DataFrame,
        timeframe: str,
        now: datetime | None = None,
    ) -> pd.DataFrame:
        """Drop today's daily bar while the US session has not closed (P0-3).

        Patterns were trained on completed bars; an in-session daily bar carries
        partial volume and provisional high/low/close, so matching against it
        breaks Research<->Lab feature parity. Before the 16:00 New York close
        the operative window must end on yesterday's bar.
        """
        if timeframe.lower().strip() not in {"1d", "1 day"} or df.empty:
            return df
        current = now or datetime.now(US_EQUITY_TZ)
        local = current.astimezone(US_EQUITY_TZ) if current.tzinfo else current.replace(tzinfo=US_EQUITY_TZ)
        if local.time() >= REGULAR_CLOSE:
            return df
        try:
            last_date = pd.Timestamp(df.index[-1]).date()
        except (TypeError, ValueError):
            return df
        if last_date >= local.date():
            return df.iloc[:-1]
        return df

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

    @classmethod
    def _store_matches(cls, db: Session, matches: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc)
        for match in matches:
            metrics = cls._stored_match_metrics(match, now=now)
            existing = cls._existing_match(db, match, metrics)
            if existing is None:
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
                        matched_at=now,
                        window_end=str(match["window_end"]),
                        status=str(match["status"]),
                        notes=str(match["notes"]),
                        chart_json=match.get("chart", {}),
                        metrics_json=metrics,
                    )
                )
                continue
            prior = existing.metrics_json or {}
            metrics["first_seen_at"] = prior.get("first_seen_at") or (
                existing.matched_at.isoformat() if existing.matched_at else now.isoformat()
            )
            metrics["seen_count"] = int(prior.get("seen_count") or 1) + 1
            existing.side = str(match["side"])
            existing.similarity = float(match["similarity"])
            existing.score = float(match["score"])
            existing.entry_price = float(match["entry_price"])
            existing.stop_price = float(match["stop_price"])
            existing.target_price = float(match["target_price"])
            existing.reward_risk = float(match["reward_risk"])
            existing.matched_at = now
            existing.status = str(match["status"])
            existing.notes = str(match["notes"])
            existing.chart_json = match.get("chart", {})
            existing.metrics_json = metrics
            db.add(existing)
        db.commit()

    @classmethod
    def _existing_match(
        cls,
        db: Session,
        match: dict[str, Any],
        metrics: dict[str, Any],
    ) -> DiscoveredPatternMatch | None:
        candidate_rows = (
            db.query(DiscoveredPatternMatch)
            .filter(DiscoveredPatternMatch.pattern_id == int(match["pattern_id"]))
            .filter(DiscoveredPatternMatch.symbol == str(match["symbol"]))
            .filter(DiscoveredPatternMatch.timeframe == str(match["timeframe"]))
            .filter(DiscoveredPatternMatch.window_end == str(match["window_end"]))
            .all()
        )
        wanted = cls.match_dedupe_key(match, metrics)
        for row in candidate_rows:
            if cls.match_dedupe_key_from_model(row) == wanted:
                return row
        return None

    @staticmethod
    def _stored_match_metrics(match: dict[str, Any], *, now: datetime) -> dict[str, Any]:
        metrics = dict(match.get("metrics") or {})
        metrics["entry_variant_id"] = str(match.get("entry_variant_id") or metrics.get("entry_variant_id") or "")
        metrics["entry_variant"] = match.get("entry_variant") or metrics.get("entry_variant") or {}
        metrics["match_dedupe_key"] = NovelPatternMatcher.match_dedupe_key(match, metrics)
        metrics.setdefault("first_seen_at", now.isoformat())
        metrics["last_seen_at"] = now.isoformat()
        metrics.setdefault("seen_count", 1)
        return metrics

    @staticmethod
    def match_dedupe_key(match: dict[str, Any], metrics: dict[str, Any] | None = None) -> tuple[str, ...]:
        data = metrics or match.get("metrics") or {}
        return (
            str(match.get("pattern_id") or ""),
            str(match.get("symbol") or "").upper(),
            str(match.get("timeframe") or ""),
            str(data.get("entry_variant_id") or match.get("entry_variant_id") or ""),
            str(match.get("window_end") or ""),
        )

    @staticmethod
    def match_dedupe_key_from_model(match: DiscoveredPatternMatch) -> tuple[str, ...]:
        metrics = match.metrics_json or {}
        return (
            str(match.pattern_id),
            str(match.symbol or "").upper(),
            str(match.timeframe or ""),
            str(metrics.get("entry_variant_id") or ""),
            str(match.window_end or ""),
        )
