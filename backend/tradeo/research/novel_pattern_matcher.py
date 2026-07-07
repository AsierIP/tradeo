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
from tradeo.research.prototype_bank import (
    knn_distance,
    mahalanobis_diag_distance,
    parse_prototype_bank,
)
from tradeo.research.shape_verifier import (
    DEFAULT_SHAPE_CHANNELS,
    SHAPE_VERIFIER_METHOD,
    shape_distance,
    shape_matrix_from_chart,
)
from tradeo.services.data_provider import MarketDataProvider, pick_symbols, universe_scope_for_interval
from tradeo.services.data_quality import assess_ohlcv_quality_from_settings
from tradeo.services.entry_variants import (
    build_entry_audit_context,
    build_entry_variants,
    classify_regime,
)
from tradeo.services.market_regime import INSUFFICIENT_HISTORY, MarketRegimeService
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.modules.fox_hunter.production_manifest import (
    production_manifest_for_pattern,
    production_manifest_is_active,
)
from tradeo.services.market_session import REGULAR_CLOSE, US_EQUITY_TZ
from tradeo.services.state_policy import DAILY_RUNTIME_STATES, LAB_RUNTIME_STATES, PRODUCTION_RUNTIME_STATES
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
        max_results: int | None = None,
        similarity_threshold: float | None = None,
        module: Literal["laboratory", "fox_hunter", "daily"] = "laboratory",
        store: bool = True,
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        statuses = self._statuses_for_module(module)
        pattern_limit = _optional_limit(max_patterns, settings.discovery_match_max_patterns)
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
            ]
            if pattern_limit is not None:
                patterns = patterns[:pattern_limit]
        else:
            patterns = pattern_query.limit(pattern_limit).all() if pattern_limit is not None else pattern_query.all()
        explicit_symbols = symbols is not None
        symbol_limit = _optional_limit(limit, settings.discovery_match_symbol_limit)
        requested_symbols = [s.upper().strip() for s in symbols or [] if s.strip()]
        threshold = self._resolved_similarity_threshold(
            similarity_threshold,
            settings.discovery_match_similarity_threshold,
        )
        matches: list[dict[str, Any]] = []
        regime_gate_blocked = 0
        reward_risk_gate_blocked = 0
        engine = PatternEmbeddingEngine()
        contract_gamma = (
            float(settings.discovery_match_temporal_gamma)
            if settings.discovery_match_temporal_weighting_enabled
            else None
        )
        feature_parity_contract = {
            **engine.contract(temporal_gamma=contract_gamma),
            "research_path": "WindowSampler -> PatternEmbeddingEngine.embed",
            "lab_path": "NovelPatternMatcher -> PatternEmbeddingEngine.embed",
        }
        required_bars_by_timeframe = self._required_bars_by_timeframe(patterns)
        assert self.provider is not None
        benchmark_regime = MarketRegimeService(
            provider=self.provider, settings=settings
        ).current_regime()
        ambiguity_gate_blocked = 0
        data_cache: dict[tuple[str, str], pd.DataFrame | None] = {}
        benchmark_cache: dict[str, dict[str, pd.DataFrame]] = {}
        embedding_cache: dict[
            tuple[str, str, int],
            tuple[pd.DataFrame, np.ndarray, dict[str, float], dict[str, list[float]]] | None,
        ] = {}
        patterns_by_timeframe: dict[str, list[DiscoveredPattern]] = defaultdict(list)
        for pattern in patterns:
            patterns_by_timeframe[pattern.timeframe].append(pattern)

        symbols_by_timeframe: dict[str, list[str]] = {}
        for timeframe, timeframe_patterns in patterns_by_timeframe.items():
            timeframe_symbols = (
                requested_symbols
                if explicit_symbols
                else _pick_symbols(settings, symbol_limit, timeframe=timeframe)
            )
            symbols_by_timeframe[timeframe] = timeframe_symbols
            required_bars = required_bars_by_timeframe[timeframe]
            benchmark_cache[timeframe] = self._benchmark_frames(
                timeframe,
                required_bars=required_bars,
                cache=data_cache,
            )
            for symbol in timeframe_symbols:
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

                similarity_diagnostics: dict[int, dict[str, Any]] = {}
                competitors_by_window: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
                for pattern in timeframe_patterns:
                    cached = embedding_cache.get((symbol.upper(), timeframe, int(pattern.window_size)))
                    diagnostic = self._similarity_diagnostic(
                        pattern,
                        cached,
                        threshold,
                    )
                    if diagnostic is None:
                        continue
                    similarity_diagnostics[int(pattern.id)] = diagnostic
                    competitors_by_window[(pattern.timeframe, int(pattern.window_size))].append(
                        {
                            "pattern_id": int(pattern.id),
                            "pattern_name": pattern.name,
                            "pattern_key": pattern.pattern_key,
                            "similarity": diagnostic["similarity"],
                        }
                    )
                ambiguity_by_pattern: dict[int, dict[str, Any]] = {}
                for competitors in competitors_by_window.values():
                    ranked = sorted(competitors, key=lambda item: float(item["similarity"]), reverse=True)
                    for item in ranked:
                        peers = [peer for peer in ranked if int(peer["pattern_id"]) != int(item["pattern_id"])]
                        second = peers[0] if peers else None
                        ambiguity_by_pattern[int(item["pattern_id"])] = self._ambiguity_ratio(
                            similarity=float(item["similarity"]),
                            second=second,
                        )

                for pattern in timeframe_patterns:
                    try:
                        cached = embedding_cache.get((symbol.upper(), timeframe, int(pattern.window_size)))
                        if cached is None:
                            continue
                        df_for_match, vector, features, chart = cached
                        diagnostic = similarity_diagnostics.get(int(pattern.id))
                        if not diagnostic or not diagnostic["passed_threshold"]:
                            continue
                        similarity = float(diagnostic["similarity"])
                        effective_threshold = float(diagnostic["similarity_threshold_used"])
                        ambiguity = ambiguity_by_pattern.get(int(pattern.id)) or self._ambiguity_ratio(
                            similarity=similarity,
                            second=None,
                        )
                        features = dict(features)
                        features["avg_dollar_volume"] = float(
                            (df_for_match["close"] * df_for_match["volume"]).tail(20).mean()
                        )
                        reward_risk_floor = self._runtime_reward_risk_floor(settings)
                        reward_risk = float(pattern.best_rr or settings.unvalidated_pattern_min_reward_risk)
                        if not math.isfinite(reward_risk) or reward_risk < reward_risk_floor:
                            reward_risk_gate_blocked += 1
                            logger.info(
                                "reward:risk hard gate blocked {} on {}: {:.2f} < {:.2f}",
                                pattern.name,
                                symbol,
                                reward_risk,
                                reward_risk_floor,
                            )
                            continue
                        base_score = round(
                            similarity * 0.55 + pattern.score * 0.30 + pattern.stability_score * 0.15,
                            6,
                        )
                        base_gate = self._entry_gate(pattern.side, df_for_match, score=base_score, settings=settings)
                        ambiguity_gate = self._ambiguity_gate(ambiguity, base_gate, settings)
                        if not ambiguity_gate["passed"]:
                            ambiguity_gate_blocked += 1
                            logger.info(
                                "ambiguity hard gate blocked {} on {}: {}",
                                pattern.name,
                                symbol,
                                ambiguity_gate,
                            )
                            continue
                        regime = classify_regime(features, base_gate)
                        regime["benchmark_regime"] = dict(benchmark_regime)
                        regime_fit = self._pattern_regime_fit(pattern, regime, settings)
                        if settings.market_regime_hard_gate_enabled and regime_fit.get("hard_gate_blocked"):
                            regime_gate_blocked += 1
                            logger.info(
                                "regime hard gate blocked {} on {} ({}): {}",
                                pattern.name,
                                symbol,
                                regime_fit.get("label"),
                                regime_fit.get("calibration"),
                            )
                            continue
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
                            else "daily_entry_candidate"
                            if module == "daily"
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
                                "shape_verifier": diagnostic.get("shape_verifier"),
                                "conformal_gate": diagnostic.get("conformal_gate"),
                                "match_ambiguity": ambiguity,
                                "ambiguity_ratio": ambiguity["ambiguity_ratio"],
                                "ambiguity_gate": ambiguity_gate,
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
                                    "feature_parity_contract": {
                                        **feature_parity_contract,
                                        "vector_length": int(len(vector)),
                                    },
                                    "shape_verifier": diagnostic.get("shape_verifier"),
                                    "match_ambiguity": ambiguity,
                                    "ambiguity_gate": ambiguity_gate,
                                    "conformal_gate": diagnostic.get("conformal_gate"),
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
        result_limit = self._result_limit(module, max_results)
        matches = sorted(matches, key=self._match_rank_key)
        if result_limit is not None:
            matches = matches[:result_limit]
        if store:
            self._store_matches(db, matches)
        return {
            "patterns_checked": len(patterns),
            "symbols_checked": sum(len(symbols) for symbols in symbols_by_timeframe.values()),
            "symbols_by_timeframe": symbols_by_timeframe,
            "universe_scope_by_timeframe": {
                timeframe: universe_scope_for_interval(timeframe)
                for timeframe in symbols_by_timeframe
            },
            "matches": matches,
            "stored_matches": len(matches) if store else 0,
            "max_results": result_limit,
            "module": module,
            "similarity_threshold": threshold,
            "feature_parity_contract": feature_parity_contract,
            "benchmark_regime": benchmark_regime,
            "regime_hard_gate_enabled": bool(settings.market_regime_hard_gate_enabled),
            "regime_gate_blocked": regime_gate_blocked,
            "reward_risk_floor": self._runtime_reward_risk_floor(settings),
            "reward_risk_gate_blocked": reward_risk_gate_blocked,
            "ambiguity_hard_gate_enabled": bool(settings.discovery_match_ambiguity_hard_gate_enabled),
            "ambiguity_gate_blocked": ambiguity_gate_blocked,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _runtime_reward_risk_floor(settings: Settings) -> float:
        return max(
            4.0,
            float(settings.discovery_min_reward_risk),
            float(settings.discovery_premium_reward_risk),
            float(settings.unvalidated_pattern_min_reward_risk),
        )

    def _result_limit(
        self,
        module: Literal["laboratory", "fox_hunter", "daily"],
        max_results: int | None,
    ) -> int | None:
        settings = self.settings
        assert settings is not None
        configured = (
            settings.laboratory_match_max_results
            if module == "laboratory"
            else settings.discovery_match_max_results
        )
        raw_limit = configured if max_results is None else max_results
        if int(raw_limit) <= 0:
            return None
        return int(raw_limit)

    @staticmethod
    def _resolved_similarity_threshold(
        override: float | None,
        default: float,
    ) -> float:
        raw = default if override is None else override
        try:
            threshold = float(raw)
        except (TypeError, ValueError):
            return float(default)
        return threshold if math.isfinite(threshold) else float(default)

    @staticmethod
    def _match_rank_key(match: dict[str, Any]) -> tuple[Any, ...]:
        """Deterministic matcher order; lower keys rank first."""
        return (
            -NovelPatternMatcher._safe_float(match.get("score"), 0.0),
            -NovelPatternMatcher._safe_float(match.get("entry_score"), 0.0),
            -NovelPatternMatcher._safe_float(match.get("similarity"), 0.0),
            NovelPatternMatcher._rank_ambiguity_ratio(match),
            str(match.get("symbol") or "").upper(),
            str(match.get("pattern_key") or match.get("pattern_name") or "").upper(),
            str(match.get("entry_variant_id") or "").upper(),
            str(match.get("window_end") or ""),
            NovelPatternMatcher._safe_int(match.get("pattern_id")),
        )

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return number if math.isfinite(number) else default

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _rank_ambiguity_ratio(match: dict[str, Any]) -> float:
        ambiguity = match.get("match_ambiguity")
        if not isinstance(ambiguity, dict):
            return 0.0
        return NovelPatternMatcher._safe_float(ambiguity.get("ambiguity_ratio"), 0.0)

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
        if module == "daily":
            return list(DAILY_RUNTIME_STATES)
        return list(LAB_RUNTIME_STATES)

    @staticmethod
    def _notes_for_module(module: str) -> str:
        if module == "fox_hunter":
            return (
                "Match de patrón de Producción; requiere live_armed "
                "y auditoría continua de Director."
            )
        if module == "daily":
            return (
                "Match de patrón Daily aprobado por Research; requiere "
                "paper execution gates, riesgo y broker paper."
            )
        return (
            "Match de patrón de Laboratorio; requiere paper validation "
            "y auditoría de Director."
        )

    @staticmethod
    def _pattern_regime_fit(
        pattern: DiscoveredPattern,
        regime: dict[str, Any],
        settings: Settings | None = None,
    ) -> dict[str, Any]:
        profile = (pattern.metrics_json or {}).get("regime_profile", {})
        if not isinstance(profile, dict) or not profile:
            return {"score": 0.5, "label": "unknown_pattern_regime", "matched": False}
        calibrated = NovelPatternMatcher._calibrated_regime_fit(profile, regime, settings)
        if calibrated is not None:
            return calibrated
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
    def _calibrated_regime_fit(
        profile: dict[str, Any],
        regime: dict[str, Any],
        settings: Settings | None,
    ) -> dict[str, Any] | None:
        """Per-bucket calibrated fit from research-labeled benchmark outcomes (3.8).

        Only fires when Research persisted enough simulated outcomes for the
        CURRENT benchmark regime bucket; otherwise the caller falls back to the
        presence heuristics. A calibrated-negative bucket marks the match as
        hard-gate eligible, enforced in match_current behind
        market_regime_hard_gate_enabled (default off).
        """
        if settings is None:
            return None
        outcomes = profile.get("benchmark_regime_outcomes")
        if not isinstance(outcomes, dict) or not outcomes.get("available"):
            return None
        benchmark = regime.get("benchmark_regime") if isinstance(regime, dict) else None
        regime_key = str((benchmark or {}).get("regime_key") or "")
        if not regime_key or INSUFFICIENT_HISTORY in regime_key:
            return None
        buckets = outcomes.get("buckets")
        bucket = buckets.get(regime_key) if isinstance(buckets, dict) else None
        if not isinstance(bucket, dict):
            return None
        sample_count = int(bucket.get("sample_count") or 0)
        min_samples = int(settings.market_regime_outcome_min_samples)
        if sample_count < min_samples:
            return None
        expectancy_r = float(bucket.get("expectancy_r") or 0.0)
        calibration = {
            "regime_key": regime_key,
            "sample_count": sample_count,
            "min_samples": min_samples,
            "expectancy_r": expectancy_r,
            "win_rate": float(bucket.get("win_rate") or 0.0),
            "profit_factor": float(bucket.get("profit_factor") or 0.0),
            "rr": outcomes.get("rr"),
            "side": outcomes.get("side"),
            "benchmark_symbol": outcomes.get("benchmark_symbol"),
            "method": outcomes.get("method"),
        }
        if expectancy_r > 0.0:
            return {
                "score": round(min(1.0, 0.75 + 0.25 * min(1.0, expectancy_r)), 4),
                "label": "calibrated_regime_positive",
                "matched": True,
                "hard_gate_blocked": False,
                "calibration": calibration,
            }
        return {
            "score": 0.2,
            "label": "calibrated_regime_negative",
            "matched": False,
            "hard_gate_blocked": True,
            "calibration": calibration,
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
        if not all(
            math.isfinite(value)
            for value in (
                close,
                open_,
                high,
                low,
                prev_close,
                prev_high,
                prev_low,
                avg_volume,
                volume_ratio,
                sma20,
                sma50,
                sma20_prev,
                atr_value,
            )
        ):
            return {
                "passed": False,
                "trigger": "invalid_market_data",
                "entry_score": 0.0,
                "reason": "non_finite_market_data",
                "rejection_reasons": ["non_finite_market_data"],
            }
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
        try:
            mean_array = np.asarray(mean, dtype=float)
            scale_array = np.asarray(scale, dtype=float)
        except (TypeError, ValueError):
            return None, None
        if not np.isfinite(mean_array).all() or not np.isfinite(scale_array).all():
            return None, None
        return mean_array, scale_array

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
        if (
            not np.isfinite(vector_prefix).all()
            or not np.isfinite(centroid).all()
            or not np.isfinite(mean_prefix).all()
            or not np.isfinite(scale_prefix).all()
        ):
            return None
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

    def _effective_threshold(
        self,
        pattern: DiscoveredPattern,
        floor: float,
        *,
        tau_key: str = "match_tau_similarity",
    ) -> float:
        """Per-pattern similarity threshold; the global config value is a floor.

        A single global threshold misfits every cluster at once: compact clusters
        accept spurious matches and loose clusters never fire (P0-4). Research
        persists match_tau_similarity (the intra-cluster similarity percentile),
        and the matcher requires the stricter of the two. With temporal
        weighting active, similarities live on the weighted scale, so the tau
        must come from the matching weighted distribution (tau_key).
        """
        settings = self.settings
        if settings is None or not settings.discovery_match_per_pattern_threshold:
            return floor
        metrics = pattern.metrics_json or {}
        conformal_tau = metrics.get("match_conformal_similarity_threshold")
        try:
            conformal_tau = float(conformal_tau)
        except (TypeError, ValueError):
            conformal_tau = None
        tau = metrics.get(tau_key)
        try:
            tau = float(tau)
        except (TypeError, ValueError):
            tau = None
        candidates = [float(floor)]
        if conformal_tau is not None and math.isfinite(conformal_tau) and conformal_tau > 0.0:
            candidates.append(conformal_tau)
        if tau is not None and math.isfinite(tau) and tau > 0.0:
            candidates.append(tau)
        return max(candidates)

    def _temporal_weighting_for_pattern(
        self, pattern: DiscoveredPattern
    ) -> tuple[float, float] | None:
        """Gamma + weighted tau when temporal weighting (audit §2.2.a) applies.

        Requires the config flag AND research-persisted weighted tau with its
        gamma: weighting only one side of the research<->lab pair would compare
        weighted similarities against an unweighted threshold.
        """
        settings = self.settings
        if settings is None or not settings.discovery_match_temporal_weighting_enabled:
            return None
        metrics = pattern.metrics_json or {}
        gamma = (metrics.get("temporal_weighting") or {}).get("gamma")
        tau = metrics.get("match_tau_similarity_temporal")
        try:
            gamma = float(gamma)
            tau = float(tau)
        except (TypeError, ValueError):
            return None
        if not (0.0 < gamma <= 1.0) or not math.isfinite(tau) or tau <= 0.0:
            return None
        return gamma, tau

    def _similarity_diagnostic(
        self,
        pattern: DiscoveredPattern,
        cached: tuple[pd.DataFrame, np.ndarray, dict[str, float], dict[str, list[float]]] | None,
        floor: float,
    ) -> dict[str, Any] | None:
        if cached is None:
            return None
        _, vector, _, chart = cached
        scaler_mean, scaler_scale = self._scaler(pattern)
        try:
            centroid = np.asarray(pattern.centroid_json, dtype=float)
        except (TypeError, ValueError):
            return None
        if scaler_mean is None or scaler_scale is None or len(centroid) == 0:
            return None
        if not np.isfinite(centroid).all():
            return None
        scaled = self._scaled_vector_for_pattern(vector, centroid, scaler_mean, scaler_scale)
        if scaled is None:
            return None
        temporal = self._temporal_weighting_for_pattern(pattern)
        if temporal is not None:
            gamma, _ = temporal
            engine = PatternEmbeddingEngine()
            weights = engine.temporal_weights(len(centroid), gamma=gamma)
            normalized_distance = float(
                np.linalg.norm((scaled - centroid) * weights)
                / max(1.0, math.sqrt(float(np.sum(weights * weights))))
            )
            effective_threshold = self._effective_threshold(
                pattern, floor, tau_key="match_tau_similarity_temporal"
            )
        else:
            normalized_distance = float(
                np.linalg.norm(scaled - centroid) / max(1.0, np.sqrt(len(centroid)))
            )
            effective_threshold = self._effective_threshold(pattern, floor)
        similarity = float(1.0 / (1.0 + normalized_distance))
        prototype = self._prototype_diagnostic(
            pattern,
            scaled,
            centroid,
            floor=effective_threshold,
        )
        conformal = self._conformal_gate(pattern, scaled)
        passed_threshold = similarity >= effective_threshold
        if prototype is not None:
            passed_threshold = passed_threshold and bool(prototype["passed"])
        if conformal is not None:
            passed_threshold = bool(similarity >= floor and conformal["passed"])
        shape_verifier = None
        if passed_threshold:
            shape_verifier = self._shape_verifier_diagnostic(pattern, chart)
            if shape_verifier is not None and shape_verifier.get("hard_gate_applied"):
                passed_threshold = passed_threshold and bool(shape_verifier.get("passed"))
        diagnostic = {
            "similarity": round(similarity, 6),
            "normalized_distance": round(normalized_distance, 6),
            "similarity_threshold_used": round(float(floor if conformal is not None else effective_threshold), 6),
            "passed_threshold": passed_threshold,
            "temporal_weighting": {
                "enabled": temporal is not None,
                "gamma": temporal[0] if temporal is not None else None,
            },
        }
        if conformal is not None:
            diagnostic["centroid_similarity_role"] = "diagnostic_only"
            diagnostic["conformal_gate"] = conformal
        if prototype is not None:
            diagnostic["prototype_match"] = prototype
        if shape_verifier is not None:
            diagnostic["shape_verifier"] = shape_verifier
        return diagnostic

    def _shape_verifier_diagnostic(
        self,
        pattern: DiscoveredPattern,
        chart: dict[str, list[float]],
    ) -> dict[str, Any] | None:
        settings = self.settings
        if settings is None or not settings.discovery_match_shape_dtw_enabled:
            return None
        metrics = pattern.metrics_json or {}
        contract = metrics.get("shape_verifier")
        hard_gate_enabled = bool(settings.discovery_match_shape_dtw_hard_gate_enabled)
        base = {
            "method": SHAPE_VERIFIER_METHOD,
            "enabled": True,
            "hard_gate_enabled": hard_gate_enabled,
            "hard_gate_applied": False,
        }
        if not isinstance(contract, dict) or contract.get("status") != "ok":
            return {
                **base,
                "status": "missing_research_contract",
                "enforceable": False,
                "passed": None,
            }
        channels = contract.get("channels")
        if not isinstance(channels, list) or not channels:
            channels = list(DEFAULT_SHAPE_CHANNELS)
        channels = [str(channel) for channel in channels]
        points = int(contract.get("points_per_channel") or 48)
        current = shape_matrix_from_chart(chart, channels=channels, length=points)
        prototype = shape_matrix_from_chart(
            contract.get("prototype") if isinstance(contract.get("prototype"), dict) else None,
            channels=channels,
            length=points,
        )
        threshold = contract.get("distance_threshold")
        try:
            threshold = float(threshold)
        except (TypeError, ValueError):
            threshold = math.nan
        if current is None or prototype is None or not math.isfinite(threshold):
            return {
                **base,
                "status": "invalid_shape_inputs",
                "enforceable": False,
                "passed": None,
            }
        band = int(contract.get("band") or max(1, math.ceil(points * settings.discovery_match_shape_dtw_band_pct)))
        method = str(contract.get("distance") or settings.discovery_match_shape_dtw_method)
        distance = shape_distance(
            current,
            prototype,
            method=method,
            band=band,
            gamma=float(contract.get("soft_dtw_gamma") or settings.discovery_match_shape_soft_dtw_gamma),
        )
        passed = bool(math.isfinite(distance) and distance <= threshold)
        return {
            **base,
            "status": "ok",
            "enforceable": True,
            "hard_gate_applied": hard_gate_enabled,
            "passed": passed,
            "distance": round(float(distance), 6) if math.isfinite(distance) else None,
            "distance_threshold": round(float(threshold), 6),
            "channels": channels,
            "points_per_channel": int(points),
            "band": int(band),
            "distance_method": method,
        }

    def _prototype_diagnostic(
        self,
        pattern: DiscoveredPattern,
        scaled: np.ndarray,
        centroid: np.ndarray,
        *,
        floor: float,
    ) -> dict[str, Any] | None:
        settings = self.settings
        if settings is None or not settings.discovery_match_knn_enabled:
            return None
        metrics = pattern.metrics_json or {}
        medoids = metrics.get("matcher_medoids_scaled") or metrics.get("medoid_vectors_scaled")
        if not isinstance(medoids, list) or not medoids:
            return None
        try:
            medoid_matrix = np.asarray(medoids, dtype=float)
        except (TypeError, ValueError):
            return None
        if (
            medoid_matrix.ndim != 2
            or medoid_matrix.shape[1] != len(centroid)
            or not np.isfinite(medoid_matrix).all()
        ):
            return None
        k = max(1, min(int(settings.discovery_match_knn_k), medoid_matrix.shape[0]))
        distances = np.linalg.norm(medoid_matrix - scaled, axis=1) / max(
            1.0, math.sqrt(medoid_matrix.shape[1])
        )
        knn_distance = float(np.mean(np.sort(distances)[:k]))
        knn_similarity = float(1.0 / (1.0 + knn_distance))
        threshold = metrics.get("match_knn_similarity_threshold")
        try:
            threshold = float(threshold)
        except (TypeError, ValueError):
            threshold = float(floor)
        if not math.isfinite(threshold) or threshold <= 0.0:
            threshold = float(floor)
        threshold = max(float(floor), threshold)
        diag = {
            "method": "knn_medoids_mahalanobis_optional_v1",
            "enabled": True,
            "k": k,
            "medoid_count": int(medoid_matrix.shape[0]),
            "knn_distance": round(knn_distance, 6),
            "knn_similarity": round(knn_similarity, 6),
            "knn_similarity_threshold": round(threshold, 6),
            "knn_passed": knn_similarity >= threshold,
            "mahalanobis": None,
        }
        passed = bool(diag["knn_passed"])
        variance = metrics.get("matcher_diag_variance_scaled") or metrics.get("diag_variance_scaled")
        if isinstance(variance, list) and len(variance) >= len(centroid):
            var = np.asarray(variance[: len(centroid)], dtype=float)
            if np.isfinite(var).all():
                var = np.maximum(var, 1e-9)
                maha_distance = float(np.sqrt(np.mean(((scaled - centroid) ** 2) / var)))
                max_distance = metrics.get("match_mahalanobis_max_distance")
                try:
                    max_distance = float(max_distance)
                except (TypeError, ValueError):
                    max_distance = math.inf
                maha_passed = maha_distance <= max_distance
                diag["mahalanobis"] = {
                    "distance": round(maha_distance, 6),
                    "max_distance": (
                        round(max_distance, 6) if math.isfinite(max_distance) else None
                    ),
                    "passed": bool(maha_passed),
                }
                passed = passed and bool(maha_passed)
        diag["passed"] = passed
        return diag

    def _conformal_gate(
        self,
        pattern: DiscoveredPattern,
        scaled: np.ndarray,
    ) -> dict[str, Any] | None:
        """kNN/Mahalanobis conformal gate when Research persisted a bank.

        Returns None (legacy gate applies) when the flag is off, no valid bank
        exists, or the bank dimension does not match the compared prefix.
        """
        settings = self.settings
        if settings is None or not settings.discovery_match_conformal_gate_enabled:
            return None
        bank = parse_prototype_bank(pattern.metrics_json or {})
        if bank is None or bank.dimension != len(scaled):
            return None
        d_knn = knn_distance(scaled, bank.medoids, bank.knn_k)
        d_maha = mahalanobis_diag_distance(scaled, bank.maha_center, bank.maha_var)
        knn_passed = d_knn <= bank.tau_knn_distance
        maha_passed = d_maha <= bank.tau_maha_distance
        return {
            "method": "knn_medoids_mahalanobis_diag_split_conformal",
            "knn_distance": round(d_knn, 6),
            "tau_knn_distance": round(bank.tau_knn_distance, 6),
            "knn_passed": bool(knn_passed),
            "knn_similarity": round(1.0 / (1.0 + d_knn), 6),
            "maha_distance": round(d_maha, 6),
            "tau_maha_distance": round(bank.tau_maha_distance, 6),
            "maha_passed": bool(maha_passed),
            "alpha": round(bank.alpha, 6),
            "knn_k": int(bank.knn_k),
            "medoid_count": int(len(bank.medoids)),
            "passed": bool(knn_passed and maha_passed),
        }

    @staticmethod
    def _ambiguity_ratio(
        *,
        similarity: float,
        second: dict[str, Any] | None,
    ) -> dict[str, Any]:
        best = max(0.0, float(similarity))
        second_similarity = max(0.0, float(second.get("similarity", 0.0))) if second else 0.0
        margin = max(0.0, best - second_similarity)
        ratio = second_similarity / best if best > 1e-12 else 0.0
        return {
            "method": "second_best_similarity_over_best_same_symbol_timeframe_window",
            "ambiguity_ratio": round(float(ratio), 6),
            "similarity_margin": round(float(margin), 6),
            "best_similarity": round(float(best), 6),
            "second_best_similarity": round(float(second_similarity), 6),
            "second_best_pattern_id": int(second["pattern_id"]) if second else None,
            "second_best_pattern_name": str(second["pattern_name"]) if second else None,
            "second_best_pattern_key": str(second["pattern_key"]) if second else None,
            "ambiguous": bool(second and ratio >= 0.95),
        }

    @staticmethod
    def _ambiguity_gate(
        ambiguity: dict[str, Any],
        entry_gate: dict[str, Any],
        settings: Settings,
    ) -> dict[str, Any]:
        ratio = float(ambiguity.get("ambiguity_ratio") or 0.0)
        threshold = float(settings.discovery_match_ambiguity_ratio_threshold)
        ambiguous = bool(ambiguity.get("ambiguous")) or ratio >= threshold
        required_entry_score = min(
            1.0,
            float(settings.entry_min_score)
            + float(settings.discovery_match_ambiguity_entry_score_margin),
        )
        entry_score = float(entry_gate.get("entry_score") or 0.0)
        enabled = bool(settings.discovery_match_ambiguity_hard_gate_enabled)
        passed = (not enabled) or (not ambiguous) or entry_score >= required_entry_score
        return {
            "method": "ambiguity_requires_extra_entry_quality",
            "enabled": enabled,
            "passed": passed,
            "ambiguous": ambiguous,
            "ambiguity_ratio": round(ratio, 6),
            "ambiguity_ratio_threshold": round(threshold, 6),
            "entry_score": round(entry_score, 6),
            "required_entry_score": round(required_entry_score, 6),
            "reason": (
                "passed"
                if passed
                else "ambiguous_match_below_extra_entry_quality"
            ),
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
        if self.settings and self.settings.discovery_match_complete_bars_only:
            df = self._drop_incomplete_daily_bar(df, timeframe)
        if self.settings and self.settings.data_quality_filter_enabled:
            quality = assess_ohlcv_quality_from_settings(df, symbol, timeframe, self.settings)
            if not quality.research_grade:
                logger.warning(
                    "current data quality reject for {} / {}: {}",
                    symbol,
                    timeframe,
                    ",".join(quality.issues),
                )
                cache[key] = None
                return None
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


def _optional_limit(value: int | None, fallback: int) -> int | None:
    raw = fallback if value is None else value
    if int(raw) <= 0:
        return None
    return int(raw)


def _pick_symbols(settings: Settings, limit: int | None, *, timeframe: str) -> list[str]:
    return pick_symbols(
        limit=0 if limit is None else limit,
        interval=timeframe,
        universe_file=(
            settings.daily_universe_file
            if universe_scope_for_interval(timeframe) == "daily_midcap"
            else settings.intraday_universe_file
        ),
    )
