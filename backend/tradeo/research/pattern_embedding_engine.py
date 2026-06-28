from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import ClassVar

import numpy as np
import pandas as pd

from tradeo.services.technical_indicators import atr

_MISSING_BENCHMARK = object()


def _zscore_constant(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    std = float(np.std(arr))
    if std == 0.0:
        return np.zeros_like(arr, dtype=float)
    return (arr - float(np.mean(arr))) / std


_SHAPELET_X = np.linspace(-1, 1, 16)
_SHAPELET_V_TEMPLATE_Z = _zscore_constant(-np.abs(_SHAPELET_X) + np.max(np.abs(_SHAPELET_X)))
_SHAPELET_INVERTED_V_TEMPLATE_Z = _zscore_constant(-(-np.abs(_SHAPELET_X) + np.max(np.abs(_SHAPELET_X))))
_SHAPELET_FLAG_TEMPLATE_Z = _zscore_constant(
    np.r_[
        np.linspace(0.0, 1.0, 6),
        np.linspace(0.65, 0.45, 5),
        np.linspace(0.45, 1.15, 5),
    ]
)
_SHAPELET_IMPULSE_TEMPLATE_Z = _zscore_constant(np.r_[np.zeros(10), np.linspace(0.2, 1.0, 6)])

_BenchmarkCloseValues = (
    Mapping[str, np.ndarray | None]
    | tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None, np.ndarray | None]
)


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
    BENCHMARK_KEY_GROUPS: ClassVar[tuple[tuple[str, ...], ...]] = (
        ("SPY",),
        ("QQQ",),
        ("SECTOR", "sector", "sector_etf", "SECTOR_ETF"),
        ("INDUSTRY", "industry", "industry_etf", "INDUSTRY_ETF"),
    )
    _resample_grid_cache: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

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
        atr_raw = (
            atr(window, 14).to_numpy(dtype=float, copy=False)
            if len(window) >= 15
            else np.zeros(len(window), dtype=float)
        )
        return self.embed_arrays(
            open_values=window["open"].to_numpy(dtype=float, copy=False),
            high_values=window["high"].to_numpy(dtype=float, copy=False),
            low_values=window["low"].to_numpy(dtype=float, copy=False),
            close_values=window["close"].to_numpy(dtype=float, copy=False),
            volume_values=window["volume"].to_numpy(dtype=float, copy=False),
            index=window.index,
            benchmark_frames=benchmark_frames,
            atr_raw=atr_raw,
        )

    def embed_arrays(
        self,
        *,
        open_values: np.ndarray,
        high_values: np.ndarray,
        low_values: np.ndarray,
        close_values: np.ndarray,
        volume_values: np.ndarray,
        index: pd.Index,
        benchmark_frames: dict[str, pd.DataFrame] | None = None,
        benchmark_close_values: _BenchmarkCloseValues | None = None,
        benchmark_close_slice: tuple[int, int] | None = None,
        week_codes: np.ndarray | None = None,
        atr_raw: np.ndarray | None = None,
    ) -> tuple[np.ndarray, dict[str, float], dict[str, list[float]]]:
        close = np.asarray(close_values, dtype=float)
        if len(close) < 5:
            raise ValueError("window must contain at least 5 bars")
        high = np.asarray(high_values, dtype=float)
        low = np.asarray(low_values, dtype=float)
        open_ = np.asarray(open_values, dtype=float)
        volume = np.asarray(volume_values, dtype=float)
        if not (len(high) == len(low) == len(open_) == len(volume) == len(close)):
            raise ValueError("OHLCV arrays must have the same length")
        if len(index) != len(close):
            raise ValueError("index length must match OHLCV arrays")
        atr_values = (
            np.asarray(atr_raw, dtype=float)
            if atr_raw is not None
            else self._atr_from_arrays(high=high, low=low, close=close)
        )
        if len(atr_values) != len(close):
            raise ValueError("atr_raw length must match OHLCV arrays")

        safe_close = np.maximum(close, 1e-9)
        bar_range = high - low
        safe_bar_range = np.maximum(bar_range, 1e-9)
        log_close = np.log(safe_close)
        returns = np.diff(log_close, prepend=log_close[0])
        returns = self._winsorize(returns, 0.01, 0.99)
        cumulative_return = close[-1] / close[0] - 1 if close[0] else 0.0

        price_norm = close / max(close[0], 1e-9) - 1.0
        volume_rel = volume / max(float(np.nanmedian(volume)), 1.0)
        volume_rel = np.clip(volume_rel, 0, 5) / 5.0
        range_pct = np.clip(bar_range / safe_close, 0, 0.35) / 0.35
        close_position = np.clip((close - low) / safe_bar_range, 0, 1)
        body_pct = np.clip(np.abs(close - open_) / safe_bar_range, 0, 1)
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
        atr_pct = float(atr_values[-1] / close[-1]) if len(close) >= 15 and close[-1] else 0.0
        sma20 = float(np.mean(close[-min(20, len(close)) :]))
        sma50 = float(np.mean(close[-min(50, len(close)) :]))
        trend_regime = self._trend_regime(close[-1], sma20, sma50)
        atr_series = self._bfill_nan(atr_values)
        atr_tail_length = min(50, len(close))
        median_atr_pct = float(
            np.median(
                atr_series[-atr_tail_length:]
                / np.maximum(close[-atr_tail_length:], 1e-9)
            )
        )
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
        distance_sma20_atr = float(
            (close[-1] - sma20) / max(float(atr_series[-1]), close[-1] * 0.01, 1e-9)
        )
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
        market_context = self._market_context_features_from_values(
            close,
            index,
            benchmark_frames or {},
            benchmark_close_values=benchmark_close_values,
            benchmark_close_slice=benchmark_close_slice,
            week_codes=week_codes,
        )
        phase_features = self._phase_features(volume_rel, range_pct, returns)
        shapelet_features = self._shapelet_features_cached(price_norm, volume_rel)
        swing_features, swing_state_channel = self._swing_features_and_state_channel(high, low, close)
        gap_reclaim_features = self._gap_reclaim_features(
            close=close,
            open_=open_,
            high=high,
            low=low,
            previous_close=previous_close,
            previous_high=previous_high,
            previous_low=previous_low,
        )
        range_velocity = self._first_zero_diff(range_pct)
        volume_price_pressure = np.clip(np.sign(returns) * volume_rel, -1.0, 1.0)

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
            [self._resample_cached(channel, self.points_per_channel) for channel in legacy_channels]
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
            [self._resample_cached(channel, self.points_per_channel) for channel in enhanced_channels]
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
            "close_norm": self._resample_cached(price_norm, 48).round(5).tolist(),
            "volume_rel": self._resample_cached(volume_rel, 48).round(5).tolist(),
            "range_pct": self._resample_cached(range_pct, 48).round(5).tolist(),
            "swing_state": self._resample_cached(swing_state_channel, 48).round(5).tolist(),
            "volume_price_pressure": self._resample_cached(
                volume_price_pressure,
                48,
            ).round(5).tolist(),
        }
        return vector, features, chart

    def _resample_cached(self, values: np.ndarray, length: int) -> np.ndarray:
        values = np.asarray(values, dtype=float)
        if len(values) == length:
            return values
        if len(values) == 1:
            return np.repeat(values[0], length)
        key = (len(values), int(length))
        grids = self._resample_grid_cache.get(key)
        if grids is None:
            grids = (np.linspace(0, 1, len(values)), np.linspace(0, 1, length))
            self._resample_grid_cache[key] = grids
        old_x, new_x = grids
        return np.interp(new_x, old_x, values)

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
    def _atr_from_arrays(*, high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        if len(close) < 15:
            return np.zeros(len(close), dtype=float)
        previous_close = np.empty(len(close), dtype=float)
        previous_close[0] = np.nan
        previous_close[1:] = close[:-1]
        true_range = np.nanmax(
            np.vstack(
                [
                    np.abs(high - low),
                    np.abs(high - previous_close),
                    np.abs(low - previous_close),
                ]
            ),
            axis=0,
        )
        rolling = pd.Series(true_range).rolling(window=14, min_periods=14).mean()
        return rolling.to_numpy(dtype=float, copy=False)

    @staticmethod
    def _bfill_nan(values: np.ndarray) -> np.ndarray:
        out = np.asarray(values, dtype=float).copy()
        if out.size == 0:
            return out
        mask = np.isnan(out)
        if not mask.any():
            return out
        valid = np.flatnonzero(~mask)
        if valid.size == 0:
            out.fill(0.0)
            return out
        positions = np.arange(out.size)
        next_valid_positions = np.searchsorted(valid, positions, side="left")
        fillable = mask & (next_valid_positions < valid.size)
        out[fillable] = out[valid[next_valid_positions[fillable]]]
        out[np.isnan(out)] = 0.0
        return out

    @staticmethod
    def _first_zero_diff(values: np.ndarray) -> np.ndarray:
        out = np.empty_like(values, dtype=float)
        out[0] = 0.0
        out[1:] = np.diff(values)
        return out

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
        split_a = (n + 2) // 3
        split_b = (2 * n + 2) // 3
        volume_means = (
            float(np.mean(volume_rel[:split_a])) if split_a else 0.0,
            float(np.mean(volume_rel[split_a:split_b])) if split_b > split_a else 0.0,
            float(np.mean(volume_rel[split_b:])) if n > split_b else 0.0,
        )
        range_means = (
            float(np.mean(range_pct[:split_a])) if split_a else 0.0,
            float(np.mean(range_pct[split_a:split_b])) if split_b > split_a else 0.0,
            float(np.mean(range_pct[split_b:])) if n > split_b else 0.0,
        )
        return_means = (
            float(np.mean(returns[:split_a])) if split_a else 0.0,
            float(np.mean(returns[split_a:split_b])) if split_b > split_a else 0.0,
            float(np.mean(returns[split_b:])) if n > split_b else 0.0,
        )
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

    def _shapelet_features_cached(
        self,
        price_norm: np.ndarray,
        volume_rel: np.ndarray,
    ) -> dict[str, float]:
        price = self._zscore(self._resample_cached(price_norm, 16))
        volume = self._zscore(self._resample_cached(volume_rel, 16))
        price_corr = self._zscore(price)
        volume_corr = self._zscore(volume)
        price_diff = np.diff(price, prepend=price[0])
        with np.errstate(divide="ignore", invalid="ignore"):
            corr_matrix = np.corrcoef(
                np.vstack(
                    [
                        price_corr,
                        _SHAPELET_V_TEMPLATE_Z,
                        _SHAPELET_INVERTED_V_TEMPLATE_Z,
                        _SHAPELET_FLAG_TEMPLATE_Z,
                        volume_corr,
                        _SHAPELET_IMPULSE_TEMPLATE_Z,
                        price_diff,
                        volume,
                    ]
                )
            )
        price_volume_impulse_corr = float(corr_matrix[6, 7])
        if np.isnan(price_volume_impulse_corr) and (
            float(np.std(price_diff)) == 0.0 or float(np.std(volume)) == 0.0
        ):
            price_volume_impulse_corr = 0.0
        return {
            "shapelet_v_reversal_score": max(0.0, float(corr_matrix[0, 1])),
            "shapelet_inverted_v_score": max(
                0.0,
                float(corr_matrix[0, 2]),
            ),
            "shapelet_flag_continuation_score": max(
                0.0,
                float(corr_matrix[0, 3]),
            ),
            "shapelet_volume_impulse_score": max(
                0.0,
                float(corr_matrix[4, 5]),
            ),
            "price_volume_impulse_corr": price_volume_impulse_corr,
        }

    @staticmethod
    def _swing_features(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> dict[str, float]:
        features, _ = PatternEmbeddingEngine._swing_features_and_state_channel(high, low, close)
        return features

    @staticmethod
    def _swing_state_channel(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
        _, state = PatternEmbeddingEngine._swing_features_and_state_channel(high, low, close)
        return state

    @staticmethod
    def _swing_features_and_state_channel(
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> tuple[dict[str, float], np.ndarray]:
        pivot_highs: list[float] = []
        pivot_lows: list[float] = []
        state = np.zeros(len(close), dtype=float)
        last_high: float | None = None
        last_low: float | None = None
        hh = hl = lh = ll = 0
        for idx in range(1, max(1, len(close) - 1)):
            if high[idx] >= high[idx - 1] and high[idx] >= high[idx + 1]:
                if pivot_highs:
                    if high[idx] > pivot_highs[-1]:
                        hh += 1
                    else:
                        lh += 1
                if last_high is not None:
                    state[idx] += 1.0 if high[idx] > last_high else -1.0
                last_high = float(high[idx])
                pivot_highs.append(last_high)
            if low[idx] <= low[idx - 1] and low[idx] <= low[idx + 1]:
                if pivot_lows:
                    if low[idx] > pivot_lows[-1]:
                        hl += 1
                    else:
                        ll += 1
                if last_low is not None:
                    state[idx] += 1.0 if low[idx] > last_low else -1.0
                last_low = float(low[idx])
                pivot_lows.append(last_low)
        total = max(1, hh + hl + lh + ll)
        if len(state) > 1:
            last_state = 0.0
            for idx, value in enumerate(state):
                if value == 0.0:
                    state[idx] = last_state
                else:
                    last_state = value
        return {
            "swing_hh_rate": hh / total,
            "swing_hl_rate": hl / total,
            "swing_lh_rate": lh / total,
            "swing_ll_rate": ll / total,
            "swing_trend_score": (hh + hl - lh - ll) / total,
            "swing_pivot_count": float(len(pivot_highs) + len(pivot_lows)),
        }, np.clip(state, -1.0, 1.0)

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
        return PatternEmbeddingEngine._market_context_features_from_values(
            window["close"].to_numpy(dtype=float, copy=False),
            window.index,
            benchmark_frames,
        )

    @staticmethod
    def _market_context_features_from_values(
        close: np.ndarray,
        index: pd.Index,
        benchmark_frames: dict[str, pd.DataFrame],
        *,
        benchmark_close_values: _BenchmarkCloseValues | None = None,
        benchmark_close_slice: tuple[int, int] | None = None,
        week_codes: np.ndarray | None = None,
    ) -> dict[str, float]:
        local_return = float(close[-1] / max(close[0], 1e-9) - 1.0)
        weekly_close = (
            PatternEmbeddingEngine._weekly_close_values_from_week_codes(close, week_codes)
            if week_codes is not None
            else PatternEmbeddingEngine._weekly_close_values(close, index)
        )
        weekly_return = (
            float(weekly_close[-1] / max(float(weekly_close[0]), 1e-9) - 1.0)
            if len(weekly_close) >= 2
            else local_return
        )
        weekly_trend = (
            PatternEmbeddingEngine._slope(
                weekly_close / max(float(weekly_close[0]), 1e-9) - 1.0
            )
            if len(weekly_close) >= 2
            else 0.0
        )
        spy_close = PatternEmbeddingEngine._benchmark_close_values_from_context(
            index,
            benchmark_frames,
            benchmark_close_values,
            PatternEmbeddingEngine.BENCHMARK_KEY_GROUPS[0],
            benchmark_group_index=0,
            benchmark_close_slice=benchmark_close_slice,
        )
        qqq_close = PatternEmbeddingEngine._benchmark_close_values_from_context(
            index,
            benchmark_frames,
            benchmark_close_values,
            PatternEmbeddingEngine.BENCHMARK_KEY_GROUPS[1],
            benchmark_group_index=1,
            benchmark_close_slice=benchmark_close_slice,
        )
        sector_close = PatternEmbeddingEngine._benchmark_close_values_from_context(
            index,
            benchmark_frames,
            benchmark_close_values,
            PatternEmbeddingEngine.BENCHMARK_KEY_GROUPS[2],
            benchmark_group_index=2,
            benchmark_close_slice=benchmark_close_slice,
        )
        industry_close = PatternEmbeddingEngine._benchmark_close_values_from_context(
            index,
            benchmark_frames,
            benchmark_close_values,
            PatternEmbeddingEngine.BENCHMARK_KEY_GROUPS[3],
            benchmark_group_index=3,
            benchmark_close_slice=benchmark_close_slice,
        )
        spy_return = PatternEmbeddingEngine._benchmark_return_from_close_values(spy_close)
        qqq_return = PatternEmbeddingEngine._benchmark_return_from_close_values(qqq_close)
        sector_return = PatternEmbeddingEngine._benchmark_return_from_close_values(sector_close)
        industry_return = PatternEmbeddingEngine._benchmark_return_from_close_values(industry_close)
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
            PatternEmbeddingEngine._benchmark_breadth_proxy_from_close_values(spy_close),
            PatternEmbeddingEngine._benchmark_breadth_proxy_from_close_values(qqq_close),
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
    def _weekly_close_values(close: np.ndarray, index: pd.Index) -> np.ndarray:
        close_values = np.asarray(close, dtype=float)
        if not isinstance(index, pd.DatetimeIndex):
            return close_values
        if close_values.size == 0:
            return close_values
        if index.hasnans or not index.is_monotonic_increasing:
            return pd.Series(close_values, index=index).resample("W").last().to_numpy(
                dtype=float,
                copy=False,
            )
        local_index = index.tz_localize(None) if index.tz is not None else index
        week_codes = local_index.to_period("W-SUN").asi8
        first_week = int(week_codes[0])
        last_week = int(week_codes[-1])
        if last_week < first_week:
            return pd.Series(close_values, index=index).resample("W").last().to_numpy(
                dtype=float,
                copy=False,
            )
        weekly_close = np.full(last_week - first_week + 1, np.nan, dtype=float)
        valid_closes = ~np.isnan(close_values)
        if bool(np.any(valid_closes)):
            weekly_close[week_codes[valid_closes] - first_week] = close_values[valid_closes]
        return weekly_close

    @staticmethod
    def _weekly_close_values_from_week_codes(close: np.ndarray, week_codes: np.ndarray) -> np.ndarray:
        close_values = np.asarray(close, dtype=float)
        if close_values.size == 0:
            return close_values
        codes = np.asarray(week_codes, dtype=np.int64)
        if codes.size != close_values.size:
            raise ValueError("week_codes length must match close values")
        first_week = int(codes[0])
        last_week = int(codes[-1])
        if last_week < first_week:
            raise ValueError("week_codes must be sorted ascending")
        weekly_close = np.full(last_week - first_week + 1, np.nan, dtype=float)
        valid_closes = ~np.isnan(close_values)
        if bool(np.any(valid_closes)):
            weekly_close[codes[valid_closes] - first_week] = close_values[valid_closes]
        return weekly_close

    @staticmethod
    def _benchmark_close_values_from_context(
        index: pd.Index,
        benchmark_frames: dict[str, pd.DataFrame],
        benchmark_close_values: _BenchmarkCloseValues | None,
        keys: tuple[str, ...],
        *,
        benchmark_group_index: int | None = None,
        benchmark_close_slice: tuple[int, int] | None = None,
    ) -> np.ndarray | None:
        if isinstance(benchmark_close_values, tuple):
            if benchmark_group_index is None or benchmark_group_index >= len(benchmark_close_values):
                return None
            return PatternEmbeddingEngine._benchmark_window_close_values(
                benchmark_close_values[benchmark_group_index],
                benchmark_close_slice,
            )
        provided = PatternEmbeddingEngine._first_benchmark_close_values(
            benchmark_close_values,
            keys,
            benchmark_close_slice=benchmark_close_slice,
        )
        if provided is not _MISSING_BENCHMARK:
            return provided
        return PatternEmbeddingEngine._benchmark_close_values_for_index(
            index,
            PatternEmbeddingEngine._first_benchmark(benchmark_frames, keys),
        )

    @staticmethod
    def _first_benchmark_close_values(
        benchmark_close_values: Mapping[str, np.ndarray | None] | None,
        keys: tuple[str, ...],
        *,
        benchmark_close_slice: tuple[int, int] | None = None,
    ) -> np.ndarray | None | object:
        if not benchmark_close_values:
            return _MISSING_BENCHMARK
        for key in keys:
            if key in benchmark_close_values:
                return PatternEmbeddingEngine._benchmark_window_close_values(
                    benchmark_close_values[key],
                    benchmark_close_slice,
                )
        lower_map = {key.lower(): value for key, value in benchmark_close_values.items()}
        for key in keys:
            value = lower_map.get(key.lower(), _MISSING_BENCHMARK)
            if value is not _MISSING_BENCHMARK:
                return PatternEmbeddingEngine._benchmark_window_close_values(
                    value,
                    benchmark_close_slice,
                )
        return _MISSING_BENCHMARK

    @staticmethod
    def _benchmark_window_close_values(
        close_values: np.ndarray | None,
        benchmark_close_slice: tuple[int, int] | None,
    ) -> np.ndarray | None:
        if close_values is None:
            return None
        values = np.asarray(close_values, dtype=float)
        if benchmark_close_slice is not None:
            start, end = benchmark_close_slice
            values = values[start : end + 1]
        nan_mask = np.isnan(values)
        return values[~nan_mask] if bool(np.any(nan_mask)) else values

    @staticmethod
    def _first_benchmark(benchmark_frames: dict[str, pd.DataFrame], keys: tuple[str, ...]) -> pd.DataFrame | None:
        for key in keys:
            frame = benchmark_frames.get(key)
            if frame is not None:
                return frame
        lower_map = {key.lower(): value for key, value in benchmark_frames.items()}
        for key in keys:
            frame = lower_map.get(key.lower())
            if frame is not None:
                return frame
        return None

    @staticmethod
    def _benchmark_return(window: pd.DataFrame, benchmark: pd.DataFrame | None) -> float:
        close_values = PatternEmbeddingEngine._benchmark_close_values(window, benchmark)
        return PatternEmbeddingEngine._benchmark_return_from_close_values(close_values)

    @staticmethod
    def _benchmark_breadth_proxy(window: pd.DataFrame, benchmark: pd.DataFrame | None) -> float | None:
        close_values = PatternEmbeddingEngine._benchmark_close_values(window, benchmark)
        return PatternEmbeddingEngine._benchmark_breadth_proxy_from_close_values(close_values)

    @staticmethod
    def _benchmark_close_values(window: pd.DataFrame, benchmark: pd.DataFrame | None) -> np.ndarray | None:
        return PatternEmbeddingEngine._benchmark_close_values_for_index(window.index, benchmark)

    @staticmethod
    def _benchmark_close_values_for_index(
        window_index: pd.Index,
        benchmark: pd.DataFrame | None,
    ) -> np.ndarray | None:
        if benchmark is None or benchmark.empty:
            return None
        if not isinstance(window_index, pd.DatetimeIndex):
            return None
        if not isinstance(benchmark.index, pd.DatetimeIndex):
            return None
        return PatternEmbeddingEngine._aligned_benchmark_close_values(window_index, benchmark)

    @staticmethod
    def _benchmark_return_from_close_values(close_values: np.ndarray | None) -> float:
        if close_values is None or close_values.size < 2:
            return 0.0
        return float(close_values[-1] / max(float(close_values[0]), 1e-9) - 1.0)

    @staticmethod
    def _benchmark_breadth_proxy_from_close_values(close_values: np.ndarray | None) -> float | None:
        if close_values is None or close_values.size < 5:
            return None
        lookback = min(20, int(close_values.size))
        sma = float(np.mean(close_values[-lookback:]))
        above_ma = float(close_values[-1] >= sma)
        positive_return = float(close_values[-1] >= close_values[0])
        return (above_ma + positive_return) / 2.0

    @staticmethod
    def _aligned_benchmark_close_values(
        window_index: pd.DatetimeIndex,
        benchmark: pd.DataFrame,
    ) -> np.ndarray | None:
        aligned = PatternEmbeddingEngine._aligned_benchmark_close_array(window_index, benchmark)
        if aligned is None:
            return None
        return aligned[~np.isnan(aligned)]

    @staticmethod
    def _aligned_benchmark_close_array(
        window_index: pd.DatetimeIndex,
        benchmark: pd.DataFrame,
    ) -> np.ndarray | None:
        if "close" not in benchmark.columns or len(window_index) == 0:
            return None
        bench = benchmark if benchmark.index.is_monotonic_increasing else benchmark.sort_index()
        positions = bench.index.searchsorted(window_index, side="right") - 1
        positions = np.asarray(positions, dtype=int)
        valid = positions >= 0
        if not bool(np.any(valid)):
            return None
        aligned = np.full(len(window_index), np.nan, dtype=float)
        closes = bench["close"].to_numpy(dtype=float, copy=False)
        aligned[valid] = closes[positions[valid]]
        return aligned

    @staticmethod
    def _corr(left: np.ndarray, right: np.ndarray) -> float:
        left = np.asarray(left, dtype=float)
        right = np.asarray(right, dtype=float)
        if len(left) != len(right) or len(left) < 2:
            return 0.0
        with np.errstate(divide="ignore", invalid="ignore"):
            corr = float(np.corrcoef(left, right)[0, 1])
        if not np.isnan(corr):
            return corr
        left_std = float(np.std(left))
        right_std = float(np.std(right))
        if left_std == 0.0 or right_std == 0.0:
            return 0.0
        return corr

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
        lo, hi = np.nanquantile(values, (low_q, high_q))
        return np.clip(values, lo, hi)
