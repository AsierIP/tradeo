from __future__ import annotations

from dataclasses import dataclass

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

        channels = [
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
        downsampled = np.concatenate([self._resample(channel, self.points_per_channel) for channel in channels])
        scalar_features = np.array(
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
        vector = np.concatenate([downsampled, scalar_features])
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
            "range_pct_mean": float(np.mean(range_pct) * 0.35),
            "volume_rel_last": float(volume_rel[-1] * 5.0),
        }
        chart = {
            "close_norm": self._resample(price_norm, 48).round(5).tolist(),
            "volume_rel": self._resample(volume_rel, 48).round(5).tolist(),
            "range_pct": self._resample(range_pct, 48).round(5).tolist(),
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
    def _market_context_features(window: pd.DataFrame, benchmark_frames: dict[str, pd.DataFrame]) -> dict[str, float]:
        close = window["close"].astype(float)
        local_return = float(close.iloc[-1] / max(close.iloc[0], 1e-9) - 1.0)
        weekly_close = close.resample("W").last() if isinstance(window.index, pd.DatetimeIndex) else close
        weekly_return = float(weekly_close.iloc[-1] / max(weekly_close.iloc[0], 1e-9) - 1.0) if len(weekly_close) >= 2 else local_return
        weekly_trend = PatternEmbeddingEngine._slope(
            (weekly_close / max(float(weekly_close.iloc[0]), 1e-9) - 1.0).to_numpy()
        ) if len(weekly_close) >= 2 else 0.0
        spy_return = PatternEmbeddingEngine._benchmark_return(window, benchmark_frames.get("SPY"))
        qqq_return = PatternEmbeddingEngine._benchmark_return(window, benchmark_frames.get("QQQ"))
        benchmark_return = spy_return if spy_return != 0.0 else qqq_return
        alignment = 1.0 if local_return == 0.0 or benchmark_return == 0.0 or np.sign(local_return) == np.sign(benchmark_return) else -1.0
        return {
            "weekly_return": weekly_return,
            "weekly_trend": float(weekly_trend),
            "relative_strength_spy": float(local_return - spy_return),
            "relative_strength_qqq": float(local_return - qqq_return),
            "benchmark_alignment": float(alignment),
        }

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
    def _winsorize(values: np.ndarray, low_q: float, high_q: float) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        lo = np.nanquantile(values, low_q)
        hi = np.nanquantile(values, high_q)
        return np.clip(values, lo, hi)
