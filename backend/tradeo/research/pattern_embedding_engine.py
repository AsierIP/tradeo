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

    def embed(self, window: pd.DataFrame) -> tuple[np.ndarray, dict[str, float], dict[str, list[float]]]:
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
    def _winsorize(values: np.ndarray, low_q: float, high_q: float) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        lo = np.nanquantile(values, low_q)
        hi = np.nanquantile(values, high_q)
        return np.clip(values, lo, hi)
