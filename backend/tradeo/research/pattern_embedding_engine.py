from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import numpy as np
import pandas as pd

from tradeo.services.technical_indicators import atr


@dataclass(slots=True)
class PatternEmbeddingEngine:
    """Convert arbitrary OHLCV windows into fixed-length numeric fingerprints.

    The embedding is intentionally local, deterministic and cheap. Tradeo can run
    it all day without spending API tokens because every calculation is NumPy /
    pandas based. LLM/API review only receives the final compact digest.
    """

    points_per_channel: int = 24
    CONTRACT_ID: ClassVar[str] = "tradeo.pattern_embedding.v2.legacy_prefix_stable"
    # Vector layout owned by embed(): downsampled channel blocks carry a bar
    # position, scalar blocks do not. temporal_weights() depends on these counts
    # staying in sync with the channel lists in embed().
    LEGACY_CHANNEL_COUNT: ClassVar[int] = 9
    LEGACY_SCALAR_COUNT: ClassVar[int] = 23
    ENHANCED_CHANNEL_COUNT: ClassVar[int] = 3
    ENHANCED_SCALAR_COUNT: ClassVar[int] = 23
    MATCHER_SCALING_BASE: ClassVar[str] = "train_fit_standard_scaler_prefix"

    def contract(
        self,
        *,
        vector_length: int | None = None,
        temporal_gamma: float | None = None,
    ) -> dict[str, object]:
        matcher_scaling = self.MATCHER_SCALING_BASE
        if temporal_gamma is not None:
            matcher_scaling = f"{matcher_scaling}+temporal_gamma_{float(temporal_gamma):g}"
        return {
            "contract_id": self.CONTRACT_ID,
            "engine": "PatternEmbeddingEngine",
            "points_per_channel": int(self.points_per_channel),
            "legacy_prefix_stable": True,
            "research_lab_shared_path": True,
            "vector_length": int(vector_length) if vector_length is not None else None,
            "normalization": {
                "price": "close/first_close_minus_1",
                "returns": "winsorized_log_returns",
                "volume": "volume/median_volume_clipped",
                "range": "high_low_pct_clipped",
            },
            "matcher_scaling": matcher_scaling,
        }

    def temporal_weights(self, length: int, *, gamma: float = 0.97) -> np.ndarray:
        """Exponential time ramp per downsampled channel block (audit §2.2.a).

        Weight gamma^(bars_from_end) over each points_per_channel block, so the
        trigger end of the window dominates the distance and two shapes that
        differ only in handle phase stop colliding. Scalar features carry no bar
        position and keep weight 1.0. `length` may be a stored centroid prefix
        shorter than the full vector; weights are truncated to match.
        """
        ppc = int(self.points_per_channel)
        gamma = float(gamma)
        if not 0.0 < gamma <= 1.0:
            raise ValueError(f"gamma must be in (0, 1], got {gamma}")
        weights = np.ones(max(0, int(length)), dtype=float)
        ramp = gamma ** np.arange(ppc - 1, -1, -1, dtype=float)
        legacy_end = self.LEGACY_CHANNEL_COUNT * ppc
        enhanced_start = legacy_end + self.LEGACY_SCALAR_COUNT
        block_starts = [ch * ppc for ch in range(self.LEGACY_CHANNEL_COUNT)]
        block_starts += [enhanced_start + ch * ppc for ch in range(self.ENHANCED_CHANNEL_COUNT)]
        for start in block_starts:
            if start >= len(weights):
                break
            end = min(start + ppc, len(weights))
            weights[start:end] = ramp[: end - start]
        return weights

    def embed(
        self,
        window: pd.DataFrame,
        benchmark_frames: dict[str, pd.DataFrame] | None = None,
    ) -> tuple[np.ndarray, dict[str, float], dict[str, list[float]]]:
        if len(window) < 5:
            raise ValueError("window must contain at least 5 bars")
        df = window.copy()
        close = df["close"].astype(float).to_numpy()
        high = df["high"].astype(float).to_numpy()
        low = df["low"].astype(float).to_numpy()
        open_ = df["open"].astype(float).to_numpy()
        volume = df["volume"].astype(float).to_numpy()

        safe_close = np.where(close == 0, 1e-9, close)
        log_close = np.log(np.maximum(safe_close, 1e-9))
        returns = np.diff(log_close, prepend=log_close[0])
        returns = self._winsorize(returns, 0.01, 0.99)
        cumulative_return = close[-1] / close[0] - 1 if close[0] else 0.0

        price_norm = close / max(close[0], 1e-9) - 1.0
        volume_rel = volume / max(float(np.nanmedian(volume)), 1.0)
        volume_rel = np.clip(volume_rel, 0, 5) / 5.0
        range_pct = np.clip((high - low) / np.maximum(safe_close, 1e-9), 0, 0.35) / 0.35
        close_position = np.clip((close - low) / np.maximum(high - low, 1e-9), 0, 1)
        body_pct = np.clip(np.abs(close - open_) / np.maximum(high - low, 1e-9), 0, 1)
        rolling_vol = pd.Series(returns).rolling(5, min_periods=2).std().fillna(0).to_numpy()
        rolling_vol = np.clip(rolling_vol, 0, np.nanpercentile(rolling_vol, 95) + 1e-9)
        if rolling_vol.max() > 0:
            rolling_vol = rolling_vol / rolling_vol.max()

        running_max = np.maximum.accumulate(close)
        running_min = np.minimum.accumulate(close)
        drawdown = (close - running_max) / np.maximum(running_max, 1e-9)
        distance_from_low = close / np.maximum(running_min, 1e-9) - 1.0

        slope = self._slope(price_norm)
        downside_vol = float(np.std(np.minimum(returns, 0)))
        upside_vol = float(np.std(np.maximum(returns, 0)))
        local_drawdown = float(abs(np.min(drawdown)))
        local_runup = float(np.max(distance_from_low))
        last_quarter_return = float(close[-1] / close[max(0, len(close) * 3 // 4)] - 1)
        volume_trend = self._slope(volume_rel)
        atr_pct = float(atr(df, 14).iloc[-1] / close[-1]) if len(df) >= 15 and close[-1] else 0.0
        sma20 = float(np.mean(close[-min(20, len(close)) :]))
        sma50 = float(np.mean(close[-min(50, len(close)) :]))
        trend_regime = self._trend_regime(close[-1], sma20, sma50)
        atr_series = atr(df, 14).bfill().fillna(0.0) if len(df) >= 15 else pd.Series([0.0] * len(df), index=df.index)
        median_atr_pct = float(np.median(atr_series.tail(50) / np.maximum(df["close"].tail(50).astype(float), 1e-9)))
        volatility_regime = float(atr_pct / max(median_atr_pct, 1e-9)) if median_atr_pct > 0 else 1.0
        previous_close = float(close[-2]) if len(close) >= 2 else float(close[-1])
        gap_pct = float(open_[-1] / max(previous_close, 1e-9) - 1.0)
        lookback = min(20, max(2, len(close) - 1))
        previous_high = float(np.max(high[-lookback - 1 : -1])) if len(high) > 1 else float(high[-1])
        previous_low = float(np.min(low[-lookback - 1 : -1])) if len(low) > 1 else float(low[-1])
        breakout_strength = float(close[-1] / max(previous_high, 1e-9) - 1.0)
        breakdown_strength = float(previous_low / max(close[-1], 1e-9) - 1.0)
        avg_dollar_volume = float(np.mean(close[-lookback:] * volume[-lookback:]))
        liquidity_score = float(min(1.0, np.log1p(max(avg_dollar_volume, 0.0)) / np.log1p(50_000_000.0)))
        distance_sma20_atr = float((close[-1] - sma20) / max(float(atr_series.iloc[-1]), close[-1] * 0.01, 1e-9))
        long_trigger_score = self._entry_trigger_score(
            side="long",
            close=float(close[-1]),
            open_=float(open_[-1]),
            high=float(high[-1]),
            low=float(low[-1]),
            previous_close=previous_close,
            previous_high=previous_high,
            previous_low=previous_low,
            sma20=sma20,
        )
        short_trigger_score = self._entry_trigger_score(
            side="short",
            close=float(close[-1]),
            open_=float(open_[-1]),
            high=float(high[-1]),
            low=float(low[-1]),
            previous_close=previous_close,
            previous_high=previous_high,
            previous_low=previous_low,
            sma20=sma20,
        )
        market_context = self._market_context_features(df, benchmark_frames or {})
        phase_features = self._phase_features(volume_rel, range_pct, returns)
        shapelet_features = self._shapelet_features(price_norm, volume_rel)
        swing_features = self._swing_features(high, low, close)
        gap_reclaim_features = self._gap_reclaim_features(
            close=close,
            open_=open_,
            high=high,
            low=low,
            previous_close=previous_close,
            previous_high=previous_high,
            previous_low=previous_low,
        )
        range_velocity = pd.Series(range_pct).diff().fillna(0.0).to_numpy()
        volume_price_pressure = np.clip(np.sign(returns) * volume_rel, -1.0, 1.0)
        swing_state_channel = self._swing_state_channel(high, low, close)

        # Keep this legacy prefix stable. Stored pattern centroids may be shorter
        # and NovelPatternMatcher intentionally compares only the saved prefix.
        legacy_channels = [
            price_norm,
            returns,
            volume_rel,
            range_pct,
            close_position,
            body_pct,
            rolling_vol,
            drawdown,
            distance_from_low,
        ]
        legacy_downsampled = np.concatenate(
            [self._resample(channel, self.points_per_channel) for channel in legacy_channels]
        )
        legacy_scalar_features = np.array(
            [
                cumulative_return,
                slope,
                downside_vol,
                upside_vol,
                local_drawdown,
                local_runup,
                last_quarter_return,
                volume_trend,
                atr_pct,
                trend_regime,
                min(volatility_regime, 5.0),
                gap_pct,
                breakout_strength,
                breakdown_strength,
                liquidity_score,
                distance_sma20_atr,
                long_trigger_score,
                short_trigger_score,
                market_context["weekly_return"],
                market_context["weekly_trend"],
                market_context["relative_strength_spy"],
                market_context["relative_strength_qqq"],
                market_context["benchmark_alignment"],
            ],
            dtype=float,
        )
        enhanced_channels = [
            range_velocity,
            volume_price_pressure,
            swing_state_channel,
        ]
        enhanced_downsampled = np.concatenate(
            [self._resample(channel, self.points_per_channel) for channel in enhanced_channels]
        )
        enhanced_scalar_features = np.array(
            [
                phase_features["volume_phase_early"],
                phase_features["volume_phase_mid"],
                phase_features["volume_phase_late"],
                phase_features["volume_phase_acceleration"],
                phase_features["range_phase_expansion"],
                shapelet_features["shapelet_v_reversal_score"],
                shapelet_features["shapelet_inverted_v_score"],
                shapelet_features["shapelet_flag_continuation_score"],
                shapelet_features["price_volume_impulse_corr"],
                swing_features["swing_hh_rate"],
                swing_features["swing_hl_rate"],
                swing_features["swing_lh_rate"],
                swing_features["swing_ll_rate"],
                swing_features["swing_trend_score"],
                gap_reclaim_features["gap_up_reclaim_continuation_score"],
                gap_reclaim_features["gap_down_reclaim_continuation_score"],
                market_context["market_return"],
                market_context["market_breadth_proxy"],
                market_context["sector_strength"],
                market_context["industry_strength"],
                market_context["relative_strength_sector"],
                market_context["relative_strength_industry"],
                market_context["market_regime_score"],
            ],
            dtype=float,
        )
        vector = np.concatenate(
            [legacy_downsampled, legacy_scalar_features, enhanced_downsampled, enhanced_scalar_features]
        )
        vector = np.nan_to_num(vector, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        features = {
            "cumulative_return": float(cumulative_return),
            "slope": float(slope),
            "downside_vol": downside_vol,
            "upside_vol": upside_vol,
            "local_drawdown": local_drawdown,
            "local_runup": local_runup,
            "last_quarter_return": last_quarter_return,
            "volume_trend": float(volume_trend),
            "atr_pct": atr_pct,
            "trend_regime": trend_regime,
            "volatility_regime": volatility_regime,
            "gap_pct": gap_pct,
            "breakout_strength": breakout_strength,
            "breakdown_strength": breakdown_strength,
            "avg_dollar_volume": avg_dollar_volume,
            "liquidity_score": liquidity_score,
            "distance_sma20_atr": distance_sma20_atr,
            "long_entry_trigger_score": long_trigger_score,
            "short_entry_trigger_score": short_trigger_score,
            **market_context,
            **phase_features,
            **shapelet_features,
            **swing_features,
            **gap_reclaim_features,
            "range_pct_mean": float(np.mean(range_pct) * 0.35),
            "volume_rel_last": float(volume_rel[-1] * 5.0),
            "range_velocity_last": float(range_velocity[-1] * 0.35),
            "volume_price_pressure_last": float(volume_price_pressure[-1]),
        }
        chart = {
            "close_norm": self._resample(price_norm, 48).round(5).tolist(),
            "volume_rel": self._resample(volume_rel, 48).round(5).tolist(),
            "range_pct": self._resample(range_pct, 48).round(5).tolist(),
            "swing_state": self._resample(swing_state_channel, 48).round(5).tolist(),
            "volume_price_pressure": self._resample(volume_price_pressure, 48).round(5).tolist(),
        }
        return vector, features, chart

    @staticmethod
    def _resample(values: np.ndarray, length: int) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        if len(values) == length:
            return values
        if len(values) == 1:
            return np.repeat(values[0], length)
        old_x = np.linspace(0, 1, len(values))
        new_x = np.linspace(0, 1, length)
        return np.interp(new_x, old_x, values)

    @staticmethod
    def _slope(values: np.ndarray) -> float:
        values = np.asarray(values, dtype=float)
        if len(values) < 2:
            return 0.0
        x = np.linspace(-1, 1, len(values))
        try:
            return float(np.polyfit(x, values, 1)[0])
        except Exception:  # noqa: BLE001
            return 0.0

    @staticmethod
    def _trend_regime(close: float, sma20: float, sma50: float) -> float:
        if close >= sma20 >= sma50:
            return 1.0
        if close <= sma20 <= sma50:
            return -1.0
        return 0.0

    @staticmethod
    def _entry_trigger_score(
        *,
        side: str,
        close: float,
        open_: float,
        high: float,
        low: float,
        previous_close: float,
        previous_high: float,
        previous_low: float,
        sma20: float,
    ) -> float:
        if side == "short":
            breakout = close <= previous_low * 1.005
            reclaim = high >= previous_low and close < previous_low * 1.01 and close < open_
            momentum = close < previous_close and close < sma20
        else:
            breakout = close >= previous_high * 0.995
            reclaim = low <= previous_high and close > previous_high * 0.99 and close > open_
            momentum = close > previous_close and close > sma20
        if breakout:
            return 1.0
        if reclaim:
            return 0.78
        if momentum:
            return 0.58
        return 0.0

    @staticmethod
    def _phase_features(volume_rel: np.ndarray, range_pct: np.ndarray, returns: np.ndarray) -> dict[str, float]:
        n = len(volume_rel)
        if n == 0:
            return {
                "volume_phase_early": 0.0,
                "volume_phase_mid": 0.0,
                "volume_phase_late": 0.0,
                "volume_phase_acceleration": 0.0,
                "range_phase_expansion": 0.0,
                "return_phase_acceleration": 0.0,
            }
        thirds = np.array_split(np.arange(n), 3)
        volume_means = [float(np.mean(volume_rel[idxs])) if len(idxs) else 0.0 for idxs in thirds]
        range_means = [float(np.mean(range_pct[idxs])) if len(idxs) else 0.0 for idxs in thirds]
        return_means = [float(np.mean(returns[idxs])) if len(idxs) else 0.0 for idxs in thirds]
        return {
            "volume_phase_early": volume_means[0] * 5.0,
            "volume_phase_mid": volume_means[1] * 5.0,
            "volume_phase_late": volume_means[2] * 5.0,
            "volume_phase_acceleration": volume_means[2] - volume_means[0],
            "range_phase_expansion": range_means[2] - range_means[0],
            "return_phase_acceleration": return_means[2] - return_means[0],
        }

    @classmethod
    def _shapelet_features(cls, price_norm: np.ndarray, volume_rel: np.ndarray) -> dict[str, float]:
        price = cls._zscore(cls._resample(price_norm, 16))
        volume = cls._zscore(cls._resample(volume_rel, 16))
        x = np.linspace(-1, 1, 16)
        v_template = -np.abs(x) + np.max(np.abs(x))
        inverted_v_template = -v_template
        flag_template = np.r_[np.linspace(0.0, 1.0, 6), np.linspace(0.65, 0.45, 5), np.linspace(0.45, 1.15, 5)]
        impulse = np.r_[np.zeros(10), np.linspace(0.2, 1.0, 6)]
        return {
            "shapelet_v_reversal_score": cls._positive_corr(price, v_template),
            "shapelet_inverted_v_score": cls._positive_corr(price, inverted_v_template),
            "shapelet_flag_continuation_score": cls._positive_corr(price, flag_template),
            "shapelet_volume_impulse_score": cls._positive_corr(volume, impulse),
            "price_volume_impulse_corr": cls._corr(np.diff(price, prepend=price[0]), volume),
        }

    @staticmethod
    def _swing_features(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> dict[str, float]:
        pivot_highs: list[float] = []
        pivot_lows: list[float] = []
        hh = hl = lh = ll = 0
        for idx in range(1, max(1, len(close) - 1)):
            if high[idx] >= high[idx - 1] and high[idx] >= high[idx + 1]:
                if pivot_highs:
                    if high[idx] > pivot_highs[-1]:
                        hh += 1
                    else:
                        lh += 1
                pivot_highs.append(float(high[idx]))
            if low[idx] <= low[idx - 1] and low[idx] <= low[idx + 1]:
                if pivot_lows:
                    if low[idx] > pivot_lows[-1]:
                        hl += 1
                    else:
                        ll += 1
                pivot_lows.append(float(low[idx]))
        total = max(1, hh + hl + lh + ll)
        return {
            "swing_hh_rate": hh / total,
            "swing_hl_rate": hl / total,
            "swing_lh_rate": lh / total,
            "swing_ll_rate": ll / total,
            "swing_trend_score": (hh + hl - lh - ll) / total,
            "swing_pivot_count": float(len(pivot_highs) + len(pivot_lows)),
        }

    @staticmethod
    def _swing_state_channel(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        state = np.zeros(len(close), dtype=float)
        last_high: float | None = None
        last_low: float | None = None
        for idx in range(1, max(1, len(close) - 1)):
            if high[idx] >= high[idx - 1] and high[idx] >= high[idx + 1]:
                if last_high is not None:
                    state[idx] += 1.0 if high[idx] > last_high else -1.0
                last_high = float(high[idx])
            if low[idx] <= low[idx - 1] and low[idx] <= low[idx + 1]:
                if last_low is not None:
                    state[idx] += 1.0 if low[idx] > last_low else -1.0
                last_low = float(low[idx])
        if len(state) > 1:
            state = pd.Series(state).replace(0.0, np.nan).ffill().fillna(0.0).to_numpy()
        return np.clip(state, -1.0, 1.0)

    @staticmethod
    def _gap_reclaim_features(
        *,
        close: np.ndarray,
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        previous_close: float,
        previous_high: float,
        previous_low: float,
    ) -> dict[str, float]:
        last_open = float(open_[-1])
        last_close = float(close[-1])
        last_high = float(high[-1])
        last_low = float(low[-1])
        gap_pct = last_open / max(previous_close, 1e-9) - 1.0
        gap_up = gap_pct > 0.005
        gap_down = gap_pct < -0.005
        reclaim_up = (
            gap_up
            and last_low <= previous_high
            and last_close > max(last_open, previous_high * 0.995)
        )
        reclaim_down = (
            gap_down
            and last_high >= previous_low
            and last_close < min(last_open, previous_low * 1.005)
        )
        continuation_up = (
            gap_up
            and last_close > last_open
            and last_close >= (last_low + (last_high - last_low) * 0.65)
        )
        continuation_down = (
            gap_down
            and last_close < last_open
            and last_close <= (last_low + (last_high - last_low) * 0.35)
        )
        return {
            "gap_up_reclaim_score": 1.0 if reclaim_up else 0.0,
            "gap_down_reclaim_score": 1.0 if reclaim_down else 0.0,
            "gap_up_continuation_score": 1.0 if continuation_up else 0.0,
            "gap_down_continuation_score": 1.0 if continuation_down else 0.0,
            "gap_up_reclaim_continuation_score": 1.0 if reclaim_up and continuation_up else 0.0,
            "gap_down_reclaim_continuation_score": 1.0 if reclaim_down and continuation_down else 0.0,
        }

    @staticmethod
    def _market_context_features(
        window: pd.DataFrame,
        benchmark_frames: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        close = window["close"].astype(float)
        local_return = float(close.iloc[-1] / max(close.iloc[0], 1e-9) - 1.0)
        weekly_close = close.resample("W").last() if isinstance(window.index, pd.DatetimeIndex) else close
        weekly_return = (
            float(weekly_close.iloc[-1] / max(weekly_close.iloc[0], 1e-9) - 1.0)
            if len(weekly_close) >= 2
            else local_return
        )
        weekly_trend = (
            PatternEmbeddingEngine._slope(
                (weekly_close / max(float(weekly_close.iloc[0]), 1e-9) - 1.0).to_numpy()
            )
            if len(weekly_close) >= 2
            else 0.0
        )
        spy_return = PatternEmbeddingEngine._benchmark_return(window, benchmark_frames.get("SPY"))
        qqq_return = PatternEmbeddingEngine._benchmark_return(window, benchmark_frames.get("QQQ"))
        sector_return = PatternEmbeddingEngine._benchmark_return(
            window,
            PatternEmbeddingEngine._first_benchmark(
                benchmark_frames,
                ("SECTOR", "sector", "sector_etf", "SECTOR_ETF"),
            ),
        )
        industry_return = PatternEmbeddingEngine._benchmark_return(
            window,
            PatternEmbeddingEngine._first_benchmark(
                benchmark_frames,
                ("INDUSTRY", "industry", "industry_etf", "INDUSTRY_ETF"),
            ),
        )
        benchmark_return = spy_return if spy_return != 0.0 else qqq_return
        alignment = (
            1.0
            if local_return == 0.0
            or benchmark_return == 0.0
            or np.sign(local_return) == np.sign(benchmark_return)
            else -1.0
        )
        market_returns = [value for value in (spy_return, qqq_return) if value != 0.0]
        market_return = float(np.mean(market_returns)) if market_returns else 0.0
        breadth_inputs = [
            PatternEmbeddingEngine._benchmark_breadth_proxy(window, benchmark_frames.get("SPY")),
            PatternEmbeddingEngine._benchmark_breadth_proxy(window, benchmark_frames.get("QQQ")),
        ]
        breadth_values = [value for value in breadth_inputs if value is not None]
        breadth_proxy = float(np.mean(breadth_values)) if breadth_values else 0.5
        sector_strength = sector_return if sector_return != 0.0 else market_return
        industry_strength = industry_return if industry_return != 0.0 else sector_strength
        market_regime_score = float(np.clip(market_return * 10.0 + (breadth_proxy - 0.5) * 1.5, -1.0, 1.0))
        return {
            "weekly_return": weekly_return,
            "weekly_trend": float(weekly_trend),
            "relative_strength_spy": float(local_return - spy_return),
            "relative_strength_qqq": float(local_return - qqq_return),
            "benchmark_alignment": float(alignment),
            "market_return": market_return,
            "market_breadth_proxy": breadth_proxy,
            "market_regime_score": market_regime_score,
            "sector_strength": float(sector_strength),
            "industry_strength": float(industry_strength),
            "relative_strength_sector": float(local_return - sector_return) if sector_return != 0.0 else 0.0,
            "relative_strength_industry": float(local_return - industry_return) if industry_return != 0.0 else 0.0,
        }

    @staticmethod
    def _first_benchmark(benchmark_frames: dict[str, pd.DataFrame], keys: tuple[str, ...]) -> pd.DataFrame | None:
        lower_map = {key.lower(): value for key, value in benchmark_frames.items()}
        for key in keys:
            frame = benchmark_frames.get(key)
            if frame is not None:
                return frame
            frame = lower_map.get(key.lower())
            if frame is not None:
                return frame
        return None

    @staticmethod
    def _benchmark_return(window: pd.DataFrame, benchmark: pd.DataFrame | None) -> float:
        if benchmark is None or benchmark.empty:
            return 0.0
        if not isinstance(window.index, pd.DatetimeIndex):
            return 0.0
        bench = benchmark.copy()
        if not isinstance(bench.index, pd.DatetimeIndex):
            return 0.0
        bench = bench.sort_index()
        aligned = bench.reindex(window.index, method="ffill")
        aligned = aligned.dropna(subset=["close"])
        if len(aligned) < 2:
            return 0.0
        return float(aligned["close"].iloc[-1] / max(float(aligned["close"].iloc[0]), 1e-9) - 1.0)

    @staticmethod
    def _benchmark_breadth_proxy(window: pd.DataFrame, benchmark: pd.DataFrame | None) -> float | None:
        if benchmark is None or benchmark.empty or not isinstance(window.index, pd.DatetimeIndex):
            return None
        if not isinstance(benchmark.index, pd.DatetimeIndex):
            return None
        aligned = benchmark.sort_index().reindex(window.index, method="ffill").dropna(subset=["close"])
        if len(aligned) < 5:
            return None
        close = aligned["close"].astype(float)
        sma = close.rolling(min(20, len(close)), min_periods=3).mean()
        above_ma = float(close.iloc[-1] >= sma.iloc[-1])
        positive_return = float(close.iloc[-1] >= close.iloc[0])
        return (above_ma + positive_return) / 2.0

    @staticmethod
    def _corr(left: np.ndarray, right: np.ndarray) -> float:
        left = np.asarray(left, dtype=float)
        right = np.asarray(right, dtype=float)
        if len(left) != len(right) or len(left) < 2:
            return 0.0
        left_std = float(np.std(left))
        right_std = float(np.std(right))
        if left_std == 0.0 or right_std == 0.0:
            return 0.0
        return float(np.corrcoef(left, right)[0, 1])

    @classmethod
    def _positive_corr(cls, left: np.ndarray, right: np.ndarray) -> float:
        return max(0.0, cls._corr(cls._zscore(left), cls._zscore(right)))

    @staticmethod
    def _zscore(values: np.ndarray) -> np.ndarray:
        arr = np.asarray(values, dtype=float)
        std = float(np.std(arr))
        if std == 0.0:
            return np.zeros_like(arr, dtype=float)
        return (arr - float(np.mean(arr))) / std

    @staticmethod
    def _winsorize(values: np.ndarray, low_q: float, high_q: float) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        lo = np.nanquantile(values, low_q)
        hi = np.nanquantile(values, high_q)
        return np.clip(values, lo, hi)
