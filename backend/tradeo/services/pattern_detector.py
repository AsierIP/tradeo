from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from tradeo.core.config import get_settings
from tradeo.schemas import PatternCandidate
from tradeo.services.ml_scorer import FeatureScorer
from tradeo.services.technical_indicators import atr, sma
from tradeo.services.vision_scorer import VisionGeometryScorer


@dataclass
class CupDetectorParams:
    min_bars: int = 45
    max_bars: int = 210
    min_depth: float = 0.10
    max_depth: float = 0.42
    rim_tolerance: float = 0.12
    max_handle_depth: float = 0.18
    breakout_buffer: float = 0.002
    min_breakout_volume_ratio: float = 1.12
    min_confidence: float = 0.68
    min_composite_score: float = 0.70
    max_holding_bars: int = 30
    target_r_multiple: float = 4.0


class CupPatternDetector:
    """Detects technical cup/base breakout candidates in mid/small-cap symbols.

    The detector is deliberately conservative and returns candidates only when the
    current bar is close to or above a breakout pivot and the pattern has an explicit
    stop and 4R+ target.
    """

    def __init__(self, params: CupDetectorParams | None = None) -> None:
        self.params = params or CupDetectorParams()
        self.ml = FeatureScorer()
        self.vision = VisionGeometryScorer()
        self.settings = get_settings()

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> "CupPatternDetector":
        p = CupDetectorParams(
            min_bars=int(cfg.get("min_bars", 45)),
            max_bars=int(cfg.get("max_bars", 210)),
            min_depth=float(cfg.get("min_depth", 0.10)),
            max_depth=float(cfg.get("max_depth", 0.42)),
            rim_tolerance=float(cfg.get("rim_tolerance", 0.12)),
            max_handle_depth=float(cfg.get("max_handle_depth", 0.18)),
            breakout_buffer=float(cfg.get("breakout_buffer", 0.002)),
            min_breakout_volume_ratio=float(cfg.get("min_breakout_volume_ratio", 1.12)),
            min_confidence=float(cfg.get("min_confidence", 0.68)),
            min_composite_score=float(cfg.get("min_composite_score", 0.70)),
            max_holding_bars=int(cfg.get("max_holding_bars", 30)),
            target_r_multiple=float(cfg.get("target_r_multiple", 4.0)),
        )
        return cls(p)

    def detect(self, symbol: str, df: pd.DataFrame, timeframe: str = "1d") -> PatternCandidate | None:
        if df.empty or len(df) < self.params.min_bars + 20:
            return None
        data = df.copy().dropna()
        data["atr"] = atr(data)
        data["sma50"] = sma(data["close"], 50)
        data["sma200"] = sma(data["close"], 200)
        last = data.iloc[-1]
        if last["close"] < self.settings.min_price:
            return None
        if last["atr"] and last["close"] and last["atr"] / last["close"] > self.settings.max_atr_pct:
            return None

        best: PatternCandidate | None = None
        for length in self._candidate_lengths(len(data)):
            candidate = self._detect_length(symbol, data.tail(length), timeframe)
            if candidate and (best is None or candidate.composite_score > best.composite_score):
                best = candidate
        return best

    def _candidate_lengths(self, n: int) -> list[int]:
        lengths = [55, 80, 110, 145, 180, self.params.max_bars]
        return sorted({x for x in lengths if self.params.min_bars <= x <= min(n, self.params.max_bars)})

    def _detect_length(self, symbol: str, w: pd.DataFrame, timeframe: str) -> PatternCandidate | None:
        p = self.params
        if len(w) < p.min_bars:
            return None
        highs = w["high"].to_numpy(dtype=float)
        lows = w["low"].to_numpy(dtype=float)
        closes = w["close"].to_numpy(dtype=float)
        vols = w["volume"].to_numpy(dtype=float)
        n = len(w)
        left_end = max(5, int(n * 0.30))
        mid_start = int(n * 0.20)
        mid_end = int(n * 0.82)
        right_start = int(n * 0.62)
        handle_bars = max(6, min(22, int(n * 0.16)))

        left_idx = int(np.argmax(highs[:left_end]))
        bottom_idx = int(mid_start + np.argmin(lows[mid_start:mid_end]))
        right_idx = int(right_start + np.argmax(highs[right_start:]))
        if not (left_idx < bottom_idx < right_idx < n):
            return None

        left_rim = highs[left_idx]
        right_rim = highs[right_idx]
        rim = (left_rim + right_rim) / 2
        bottom = lows[bottom_idx]
        if rim <= 0 or bottom <= 0:
            return None
        cup_depth = (rim - bottom) / rim
        if not (p.min_depth <= cup_depth <= p.max_depth):
            return None
        rim_diff = abs(left_rim - right_rim) / rim
        if rim_diff > p.rim_tolerance:
            return None

        handle_start = max(right_idx, n - handle_bars)
        handle_low = float(np.min(lows[handle_start:]))
        handle_high = float(np.max(highs[handle_start:]))
        pivot = max(right_rim, handle_high)
        latest_close = float(closes[-1])
        latest_high = float(highs[-1])
        latest_vol = float(vols[-1])
        handle_depth = (pivot - handle_low) / max(pivot, 1e-9)
        if handle_depth > p.max_handle_depth:
            return None

        avg_vol_20 = float(np.mean(vols[-21:-1])) if len(vols) > 21 else float(np.mean(vols[:-1]))
        avg_vol_base = float(np.mean(vols[max(0, bottom_idx - 10) : max(bottom_idx + 10, bottom_idx + 1)]))
        avg_vol_pre = float(np.mean(vols[max(0, left_idx - 10) : max(left_idx + 10, left_idx + 1)]))
        breakout_volume_ratio = latest_vol / max(avg_vol_20, 1.0)
        volume_dryup = 1 - min(1.0, avg_vol_base / max(avg_vol_pre, 1.0))

        is_breaking_out = latest_close >= pivot * (1 + p.breakout_buffer) or latest_high >= pivot * (
            1 + p.breakout_buffer
        )
        is_near_pivot = latest_close >= pivot * 0.975
        if not (is_breaking_out or is_near_pivot):
            return None
        if is_breaking_out and breakout_volume_ratio < p.min_breakout_volume_ratio:
            return None

        atr_value = float(w["atr"].iloc[-1]) if "atr" in w and not np.isnan(w["atr"].iloc[-1]) else 0.0
        entry = round(max(pivot * (1 + p.breakout_buffer), latest_close), 2)
        stop_candidate = min(handle_low, entry - 1.2 * atr_value) if atr_value > 0 else handle_low
        stop = round(max(0.01, stop_candidate), 2)
        risk_per_share = entry - stop
        if risk_per_share <= 0:
            return None
        target = round(entry + p.target_r_multiple * risk_per_share, 2)
        reward_risk = (target - entry) / risk_per_share
        if reward_risk < self.settings.min_reward_risk:
            return None

        rim_symmetry = float(max(0.0, min(1.0, 1 - rim_diff / p.rim_tolerance)))
        bottom = closes[max(0, bottom_idx - 8) : min(n, bottom_idx + 9)]
        if len(bottom) > 4:
            changes = np.diff(bottom / max(np.mean(bottom), 1e-9))
            bottom_smoothness = float(max(0.0, min(1.0, 1 - np.std(changes) * 25)))
        else:
            bottom_smoothness = 0.0
        trend_score = self._trend_score(w)
        avg_dollar_volume = float(np.mean(closes[-20:] * vols[-20:])) if n >= 20 else 0.0
        if avg_dollar_volume < self.settings.min_avg_dollar_volume:
            # With a $3k account we can trade smaller names, but very illiquid stocks
            # should stay in watchlist/rejected because stops slip aggressively.
            return None

        rule_score = self._rule_score(
            cup_depth=cup_depth,
            rim_symmetry=rim_symmetry,
            bottom_smoothness=bottom_smoothness,
            handle_depth=handle_depth,
            breakout_volume_ratio=breakout_volume_ratio,
            trend_score=trend_score,
            is_breaking_out=is_breaking_out,
        )
        features: dict[str, Any] = {
            "cup_depth": float(cup_depth),
            "cup_length": int(n),
            "rim_symmetry": rim_symmetry,
            "bottom_smoothness": bottom_smoothness,
            "handle_depth": float(handle_depth),
            "volume_dryup": float(volume_dryup),
            "breakout_volume_ratio": float(breakout_volume_ratio),
            "atr_pct": float(atr_value / latest_close) if latest_close else 0.0,
            "trend_score": trend_score,
            "avg_dollar_volume": avg_dollar_volume,
            "pivot": float(pivot),
            "left_rim_index": int(left_idx),
            "bottom_index": int(bottom_idx),
            "right_rim_index": int(right_idx),
            "is_breaking_out": bool(is_breaking_out),
        }
        ml_score = self.ml.score(features)
        vision_score, vision_details = self.vision.score(w["close"], handle_bars=handle_bars)
        features["vision_details"] = vision_details
        composite = 0.38 * rule_score + 0.34 * ml_score + 0.28 * vision_score
        confidence = min(0.98, max(0.0, composite))
        if composite < p.min_composite_score or confidence < p.min_confidence:
            return None

        notes = []
        if is_breaking_out:
            notes.append("breakout activo o muy reciente")
        else:
            notes.append("cerca de pivot; vigilar confirmación")
        if volume_dryup > 0.25:
            notes.append("contracción de volumen en base")
        if breakout_volume_ratio > 1.4:
            notes.append("volumen de ruptura superior a la media")

        return PatternCandidate(
            symbol=symbol,
            pattern="mid_small_cap_cup_breakout",
            side="long",
            timeframe=timeframe,
            entry=entry,
            stop=stop,
            target=target,
            reward_risk=round(float(reward_risk), 2),
            confidence=round(float(confidence), 4),
            rule_score=round(float(rule_score), 4),
            ml_score=round(float(ml_score), 4),
            vision_score=round(float(vision_score), 4),
            composite_score=round(float(composite), 4),
            features=features,
            notes=notes,
        )

    def _trend_score(self, w: pd.DataFrame) -> float:
        close = w["close"].iloc[-1]
        sma50 = w["sma50"].iloc[-1] if "sma50" in w else np.nan
        sma200 = w["sma200"].iloc[-1] if "sma200" in w else np.nan
        score = 0.0
        if not np.isnan(sma50) and close > sma50:
            score += 0.45
        if not np.isnan(sma200) and close > sma200:
            score += 0.35
        if len(w) >= 20 and w["close"].iloc[-1] > w["close"].iloc[-20]:
            score += 0.20
        return float(max(0.0, min(1.0, score)))

    def _rule_score(self, **kwargs: Any) -> float:
        cup_depth = float(kwargs["cup_depth"])
        rim_symmetry = float(kwargs["rim_symmetry"])
        bottom_smoothness = float(kwargs["bottom_smoothness"])
        handle_depth = float(kwargs["handle_depth"])
        volume_ratio = float(kwargs["breakout_volume_ratio"])
        trend_score = float(kwargs["trend_score"])
        is_breaking_out = bool(kwargs["is_breaking_out"])

        depth_score = max(0.0, min(1.0, 1 - abs(cup_depth - 0.24) / 0.22))
        handle_score = max(0.0, min(1.0, 1 - handle_depth / 0.18))
        volume_score = max(0.0, min(1.0, (volume_ratio - 0.85) / 1.1))
        breakout_score = 1.0 if is_breaking_out else 0.65
        return float(
            0.17 * depth_score
            + 0.17 * rim_symmetry
            + 0.13 * bottom_smoothness
            + 0.14 * handle_score
            + 0.15 * volume_score
            + 0.14 * trend_score
            + 0.10 * breakout_score
        )
