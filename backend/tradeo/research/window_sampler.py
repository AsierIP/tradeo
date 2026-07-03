from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Iterable

import numpy as np
import pandas as pd

from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.research.intraday_vwap_conditions import (
    build_vwap_condition_frame,
    normalize_vwap_condition_spec,
    vwap_condition_passes,
    vwap_features_at,
)
from tradeo.research.types import ForwardOutcome, WindowSample
from tradeo.services.technical_indicators import atr, normalize_ohlcv

_LINEAGE_COLUMNS = ("adjusted", "what_to_show", "bar_complete")


@dataclass(slots=True)
class WindowSampler:
    """Extract fixed-length pattern windows and label each with future path stats."""

    embedding_engine: PatternEmbeddingEngine | None = None
    target_r: float = 4.0
    stop_r: float = 1.0
    min_risk_pct: float = 0.015
    atr_multiplier: float = 1.5
    last_diagnostics: dict[str, int | str] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.embedding_engine = self.embedding_engine or PatternEmbeddingEngine()

    def sample(
        self,
        symbol: str,
        df: pd.DataFrame,
        timeframe: str,
        window_sizes: Iterable[int],
        forward_bars: Iterable[int],
        stride: int = 3,
        max_windows_per_symbol: int = 450,
        benchmark_frames: dict[str, pd.DataFrame] | None = None,
        vwap_condition: str | None = None,
        vwap_side_bias: str | None = None,
        vwap_max_distance_bps: float | None = None,
        vwap_min_slope_bps: float | None = None,
    ) -> list[WindowSample]:
        vwap_spec = normalize_vwap_condition_spec(
            condition=vwap_condition,
            side_bias=vwap_side_bias,
            max_distance_bps=vwap_max_distance_bps,
            min_slope_bps=vwap_min_slope_bps,
        )
        self.last_diagnostics = {
            "vwap_condition": vwap_spec.condition,
            "vwap_side_bias": vwap_spec.side_bias,
            "vwap_expected_side": vwap_spec.expected_side,
            "vwap_condition_applied": int(vwap_spec.enabled),
            "windows_vwap_rejected": 0,
            "windows_vwap_selected": 0,
        }
        window_sizes = sorted({int(size) for size in window_sizes if int(size) >= 10})
        if not window_sizes:
            return []
        forward_bars = sorted({int(x) for x in forward_bars if int(x) > 0})
        if not forward_bars:
            raise ValueError("at least one forward horizon is required")
        max_windows_per_symbol = max(0, int(max_windows_per_symbol))
        if max_windows_per_symbol == 0:
            return []
        stride = max(1, int(stride))
        df = self._normalize_with_lineage(df).dropna(subset=["open", "high", "low", "close", "volume"])
        vwap_frame = build_vwap_condition_frame(df) if vwap_spec.enabled else None
        max_forward = max(forward_bars)
        if len(df) < max(window_sizes) + max_forward + 5:
            return []

        atr_raw_series = atr(df, 14)
        atr_series = atr_raw_series.bfill().fillna(df["close"] * self.min_risk_pct)
        open_values = df["open"].to_numpy(dtype=float, copy=False)
        high_values = df["high"].to_numpy(dtype=float, copy=False)
        low_values = df["low"].to_numpy(dtype=float, copy=False)
        close_values = df["close"].to_numpy(dtype=float, copy=False)
        volume_values = df["volume"].to_numpy(dtype=float, copy=False)
        atr_raw_values = atr_raw_series.to_numpy(dtype=float, copy=False)
        atr_values = atr_series.to_numpy(dtype=float, copy=False)
        index_values = df.index
        dollar_volume = close_values * volume_values
        bar_ranges = high_values - low_values
        true_ranges = self._true_range_values(high_values, low_values, close_values)
        rolling_dollar_volume: dict[int, np.ndarray] = {}
        rolling_volume: dict[int, np.ndarray] = {}
        rolling_range: dict[int, np.ndarray] = {}
        samples: list[WindowSample] = []
        window_quotas = self._window_size_quotas(window_sizes, max_windows_per_symbol)
        embedding_benchmark_frames = self._benchmark_frames_for_embedding(benchmark_frames)
        embedding_benchmark_close_values = self._benchmark_close_arrays_for_embedding(
            index_values,
            embedding_benchmark_frames,
        )
        embedding_week_codes = self._week_codes_for_embedding(index_values)
        use_embedding_placeholder_index = (
            embedding_week_codes is not None or not isinstance(index_values, pd.DatetimeIndex)
        )
        embedding_placeholder_indices: dict[int, pd.RangeIndex] = {}
        for window_size in window_sizes:
            if len(df) < window_size + max_forward + 2:
                continue
            window_quota = window_quotas.get(window_size, max_windows_per_symbol)
            if window_quota <= 0:
                continue
            window_count = 0
            # Sample from old to new. A stride keeps the system cheap enough to
            # run continuously, while still covering overlapping market states.
            # The per-window quota prevents short windows from consuming the
            # whole symbol budget before W100/W200 get any research coverage.
            end_positions = self._sample_end_positions(
                start=window_size - 1,
                stop=len(df) - max_forward - 1,
                stride=stride,
                quota=window_quota,
            )
            execution_tail = min(20, window_size)
            range_tail = min(14, window_size)
            if execution_tail not in rolling_dollar_volume:
                rolling_dollar_volume[execution_tail] = self._rolling_mean(
                    dollar_volume,
                    execution_tail,
                )
                rolling_volume[execution_tail] = self._rolling_mean(
                    volume_values,
                    execution_tail,
                )
            if range_tail not in rolling_range:
                rolling_range[range_tail] = self._rolling_mean(bar_ranges, range_tail)
            avg_dollar_volume_values = rolling_dollar_volume[execution_tail]
            avg_volume_values = rolling_volume[execution_tail]
            avg_range_values = rolling_range[range_tail]
            embedding_index = (
                embedding_placeholder_indices.setdefault(window_size, pd.RangeIndex(window_size))
                if use_embedding_placeholder_index
                else None
            )
            for end_pos in end_positions:
                if vwap_frame is not None and not vwap_condition_passes(vwap_frame, end_pos, vwap_spec):
                    self.last_diagnostics["windows_vwap_rejected"] = (
                        int(self.last_diagnostics["windows_vwap_rejected"]) + 1
                    )
                    continue
                start_pos = end_pos - window_size + 1
                future_start = end_pos + 1
                future_stop = min(len(df), future_start + max_forward)
                if future_start >= future_stop:
                    continue
                entry = float(close_values[end_pos])
                if entry <= 0:
                    continue
                risk_proxy = max(
                    float(atr_values[end_pos]) * self.atr_multiplier,
                    entry * self.min_risk_pct,
                    0.01,
                )
                execution_metrics = self._execution_cost_metrics_from_values(
                    entry=entry,
                    risk_proxy=risk_proxy,
                    latest_open=float(open_values[end_pos]),
                    latest_high=float(high_values[end_pos]),
                    latest_low=float(low_values[end_pos]),
                    previous_close=float(close_values[end_pos - 1]) if end_pos >= 1 else entry,
                    avg_dollar_volume=float(avg_dollar_volume_values[end_pos]),
                    adv_shares=float(avg_volume_values[end_pos]),
                    avg_range=float(avg_range_values[end_pos]),
                )
                execution_cost_r = float(execution_metrics["execution_cost_r"])
                outcome = self._forward_outcome_from_arrays(
                    entry,
                    risk_proxy,
                    future_end=index_values[future_stop - 1],
                    highs=high_values[future_start:future_stop],
                    lows=low_values[future_start:future_stop],
                    closes=close_values[future_start:future_stop],
                    opens=open_values[future_start:future_stop],
                    forward_bars=forward_bars,
                    execution_cost_r=execution_cost_r,
                    execution_metrics=execution_metrics,
                )
                vector, features, chart = self.embedding_engine.embed_arrays(
                    open_values=open_values[start_pos : end_pos + 1],
                    high_values=high_values[start_pos : end_pos + 1],
                    low_values=low_values[start_pos : end_pos + 1],
                    close_values=close_values[start_pos : end_pos + 1],
                    volume_values=volume_values[start_pos : end_pos + 1],
                    index=(
                        embedding_index
                        if embedding_index is not None
                        else index_values[start_pos : end_pos + 1]
                    ),
                    benchmark_frames=embedding_benchmark_frames,
                    benchmark_close_values=embedding_benchmark_close_values,
                    benchmark_close_slice=(start_pos, end_pos),
                    week_codes=(
                        embedding_week_codes[start_pos : end_pos + 1]
                        if embedding_week_codes is not None
                        else None
                    ),
                    atr_raw=self._embedding_atr_raw_for_window(
                        full_atr_raw=atr_raw_values,
                        true_ranges=true_ranges,
                        bar_ranges=bar_ranges,
                        start=start_pos,
                        end=end_pos,
                    ),
                )
                features.update(self._data_lineage_features_at(df, end_pos))
                if vwap_frame is not None:
                    features.update(vwap_features_at(vwap_frame, end_pos, vwap_spec))
                features.update({f"execution_{k}": float(v) for k, v in execution_metrics.items()})
                features["sample_window_size_quota"] = int(window_quota)
                start_idx = index_values[start_pos]
                end_idx = index_values[end_pos]
                year = self._year(end_idx)
                samples.append(
                    WindowSample(
                        symbol=symbol.upper(),
                        timeframe=timeframe,
                        window_size=window_size,
                        start=self._date_str(start_idx),
                        end=self._date_str(end_idx),
                        year=year,
                        vector=vector,
                        outcome=outcome,
                        chart=chart,
                        features=features,
                    )
                )
                if vwap_frame is not None:
                    self.last_diagnostics["windows_vwap_selected"] = (
                        int(self.last_diagnostics["windows_vwap_selected"]) + 1
                    )
                window_count += 1
                if len(samples) >= max_windows_per_symbol or window_count >= window_quota:
                    break
        return samples[:max_windows_per_symbol]

    @staticmethod
    def _sample_end_positions(*, start: int, stop: int, stride: int, quota: int) -> list[int]:
        stride = max(1, int(stride))
        position_count = len(range(start, stop, stride))
        if position_count <= 0:
            return []
        if quota <= 0 or position_count <= quota:
            return list(range(start, stop, stride))
        selected = np.linspace(0, position_count - 1, num=quota, dtype=int)
        return [start + int(index) * stride for index in selected]

    @staticmethod
    def _window_size_quotas(window_sizes: list[int], max_windows_per_symbol: int) -> dict[int, int]:
        if not window_sizes:
            return {}
        base = int(math.floor(max_windows_per_symbol / len(window_sizes)))
        remainder = max(0, max_windows_per_symbol - base * len(window_sizes))
        quotas: dict[int, int] = {}
        for index, window_size in enumerate(window_sizes):
            quotas[int(window_size)] = base + (1 if index < remainder else 0)
        return quotas

    @staticmethod
    def _normalize_with_lineage(df: pd.DataFrame) -> pd.DataFrame:
        raw = df.copy()
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = [str(column[0]).lower() for column in raw.columns]
        else:
            raw.columns = [str(column).lower().replace(" ", "_") for column in raw.columns]
        out = normalize_ohlcv(df)
        lineage_columns = [column for column in _LINEAGE_COLUMNS if column in raw.columns]
        if lineage_columns:
            out = out.join(raw[lineage_columns].reindex(out.index), how="left")
        return out

    @staticmethod
    def _benchmark_frames_for_embedding(
        benchmark_frames: dict[str, pd.DataFrame] | None,
    ) -> dict[str, pd.DataFrame] | None:
        if not benchmark_frames:
            return benchmark_frames
        normalized: dict[str, pd.DataFrame] = {}
        changed = False
        for key, frame in benchmark_frames.items():
            if isinstance(frame.index, pd.DatetimeIndex) and not frame.index.is_monotonic_increasing:
                normalized[key] = frame.sort_index()
                changed = True
            else:
                normalized[key] = frame
        return normalized if changed else benchmark_frames

    @staticmethod
    def _benchmark_close_arrays_for_embedding(
        index: pd.Index,
        benchmark_frames: dict[str, pd.DataFrame] | None,
    ) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray | None, np.ndarray | None] | None:
        if not benchmark_frames or not isinstance(index, pd.DatetimeIndex):
            return None
        aligned: list[np.ndarray | None] = []
        for keys in PatternEmbeddingEngine.BENCHMARK_KEY_GROUPS:
            frame = PatternEmbeddingEngine._first_benchmark(benchmark_frames, keys)
            if frame is None or frame.empty or not isinstance(frame.index, pd.DatetimeIndex):
                aligned.append(None)
                continue
            aligned.append(PatternEmbeddingEngine._aligned_benchmark_close_array(index, frame))
        return (aligned[0], aligned[1], aligned[2], aligned[3])

    @staticmethod
    def _week_codes_for_embedding(index: pd.Index) -> np.ndarray | None:
        if not isinstance(index, pd.DatetimeIndex):
            return None
        if index.hasnans or not index.is_monotonic_increasing:
            return None
        local_index = index.tz_localize(None) if index.tz is not None else index
        return local_index.to_period("W-SUN").asi8

    @staticmethod
    def _true_range_values(
        high_values: np.ndarray,
        low_values: np.ndarray,
        close_values: np.ndarray,
    ) -> np.ndarray:
        previous_close = np.empty(len(close_values), dtype=float)
        previous_close[0] = np.nan
        previous_close[1:] = close_values[:-1]
        return np.nanmax(
            np.vstack(
                [
                    np.abs(high_values - low_values),
                    np.abs(high_values - previous_close),
                    np.abs(low_values - previous_close),
                ]
            ),
            axis=0,
        )

    @staticmethod
    def _embedding_atr_raw_for_window(
        *,
        full_atr_raw: np.ndarray,
        true_ranges: np.ndarray,
        bar_ranges: np.ndarray,
        start: int,
        end: int,
    ) -> np.ndarray:
        window_length = end - start + 1
        if window_length < 15:
            return np.zeros(window_length, dtype=float)
        atr_raw = np.empty(window_length, dtype=float)
        atr_raw[:13] = np.nan
        atr_raw[13] = (bar_ranges[start] + np.sum(true_ranges[start + 1 : start + 14])) / 14.0
        if window_length > 14:
            atr_raw[14:] = full_atr_raw[start + 14 : end + 1]
        return atr_raw

    def _forward_outcome(
        self,
        entry: float,
        risk_proxy: float,
        future: pd.DataFrame,
        forward_bars: list[int],
        execution_cost_r: float = 0.0,
        execution_metrics: dict[str, float] | None = None,
    ) -> ForwardOutcome:
        closes = future["close"].astype(float).to_numpy()
        highs = future["high"].astype(float).to_numpy()
        lows = future["low"].astype(float).to_numpy()
        opens = future["open"].astype(float).to_numpy() if "open" in future else closes
        return self._forward_outcome_from_arrays(
            entry,
            risk_proxy,
            future_end=future.index[-1],
            highs=highs,
            lows=lows,
            closes=closes,
            opens=opens,
            forward_bars=forward_bars,
            execution_cost_r=execution_cost_r,
            execution_metrics=execution_metrics,
        )

    def _forward_outcome_from_arrays(
        self,
        entry: float,
        risk_proxy: float,
        *,
        future_end: object,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        opens: np.ndarray,
        forward_bars: list[int],
        execution_cost_r: float = 0.0,
        execution_metrics: dict[str, float] | None = None,
    ) -> ForwardOutcome:
        highs = np.asarray(highs, dtype=float)
        lows = np.asarray(lows, dtype=float)
        closes = np.asarray(closes, dtype=float)
        opens = np.asarray(opens, dtype=float)
        forward_returns = {}
        for horizon in forward_bars:
            idx = min(horizon, len(closes)) - 1
            forward_returns[horizon] = float(closes[idx] / entry - 1.0)

        long_mfe_r = float(np.max(highs - entry) / risk_proxy)
        long_mae_r = float(max(0.0, np.max(entry - lows) / risk_proxy))
        short_mfe_r = float(np.max(entry - lows) / risk_proxy)
        short_mae_r = float(max(0.0, np.max(highs - entry) / risk_proxy))
        long_path = self._path_outcome_from_arrays(entry, risk_proxy, highs, lows, closes, side="long")
        short_path = self._path_outcome_from_arrays(entry, risk_proxy, highs, lows, closes, side="short")
        long_outcome_r, long_hit_4r, long_target_bar, long_stop_bar, long_label = long_path
        short_outcome_r, short_hit_4r, short_target_bar, short_stop_bar, short_label = short_path
        first_open = float(opens[0]) if len(opens) else float(entry)
        long_gap_adverse_r = max(0.0, (entry - first_open) / max(risk_proxy, 1e-9))
        short_gap_adverse_r = max(0.0, (first_open - entry) / max(risk_proxy, 1e-9))
        long_mfe_bar = int(np.argmax(highs - entry) + 1) if len(highs) else 0
        long_mae_bar = int(np.argmax(entry - lows) + 1) if len(lows) else 0
        short_mfe_bar = int(np.argmax(entry - lows) + 1) if len(lows) else 0
        short_mae_bar = int(np.argmax(highs - entry) + 1) if len(highs) else 0
        strong_close_threshold = self.target_r * 0.75
        long_final_r = float((closes[-1] - entry) / risk_proxy) if len(closes) else 0.0
        short_final_r = float((entry - closes[-1]) / risk_proxy) if len(closes) else 0.0
        return ForwardOutcome(
            forward_returns=forward_returns,
            entry_price=float(entry),
            risk_proxy=float(risk_proxy),
            forward_end=self._date_str(future_end),
            long_mfe_r=round(long_mfe_r, 4),
            long_mae_r=round(long_mae_r, 4),
            long_outcome_r=round(long_outcome_r, 4),
            long_hit_4r=long_hit_4r,
            short_mfe_r=round(short_mfe_r, 4),
            short_mae_r=round(short_mae_r, 4),
            short_outcome_r=round(short_outcome_r, 4),
            short_hit_4r=short_hit_4r,
            forward_highs=np.round(highs.astype(float), 6).tolist(),
            forward_lows=np.round(lows.astype(float), 6).tolist(),
            forward_closes=np.round(closes.astype(float), 6).tolist(),
            forward_opens=np.round(opens.astype(float), 6).tolist(),
            execution_cost_r=round(float(execution_cost_r), 5),
            long_label=long_label,
            short_label=short_label,
            long_time_to_target=long_target_bar,
            long_time_to_stop=long_stop_bar,
            short_time_to_target=short_target_bar,
            short_time_to_stop=short_stop_bar,
            long_mfe_before_mae=long_mfe_bar > 0 and (long_mae_bar == 0 or long_mfe_bar <= long_mae_bar),
            short_mfe_before_mae=short_mfe_bar > 0 and (short_mae_bar == 0 or short_mfe_bar <= short_mae_bar),
            long_gap_adverse_r=round(float(long_gap_adverse_r), 5),
            short_gap_adverse_r=round(float(short_gap_adverse_r), 5),
            long_strong_close_without_target=long_target_bar is None and long_final_r >= strong_close_threshold,
            short_strong_close_without_target=short_target_bar is None and short_final_r >= strong_close_threshold,
            long_speed_label=self._speed_label(long_target_bar, long_stop_bar, len(closes)),
            short_speed_label=self._speed_label(short_target_bar, short_stop_bar, len(closes)),
            execution={k: round(float(v), 6) for k, v in (execution_metrics or {}).items()},
        )

    @staticmethod
    def _execution_cost_r(window: pd.DataFrame, *, entry: float, risk_proxy: float) -> float:
        metrics = WindowSampler._execution_cost_metrics(window, entry=entry, risk_proxy=risk_proxy)
        return float(metrics["execution_cost_r"])

    @staticmethod
    def _execution_cost_metrics(window: pd.DataFrame, *, entry: float, risk_proxy: float) -> dict[str, float]:
        latest = window.iloc[-1]
        previous_close = float(window["close"].iloc[-2]) if len(window) >= 2 else float(latest["close"])
        avg_dollar_volume = float((window["close"] * window["volume"]).tail(20).mean())
        adv_shares = float(window["volume"].tail(20).mean())
        avg_range = float((window["high"] - window["low"]).tail(14).mean())
        return WindowSampler._execution_cost_metrics_from_values(
            entry=entry,
            risk_proxy=risk_proxy,
            latest_open=float(latest["open"]),
            latest_high=float(latest["high"]),
            latest_low=float(latest["low"]),
            previous_close=previous_close,
            avg_dollar_volume=avg_dollar_volume,
            adv_shares=adv_shares,
            avg_range=avg_range,
        )

    @staticmethod
    def _execution_cost_metrics_from_values(
        *,
        entry: float,
        risk_proxy: float,
        latest_open: float,
        latest_high: float,
        latest_low: float,
        previous_close: float,
        avg_dollar_volume: float,
        adv_shares: float,
        avg_range: float,
    ) -> dict[str, float]:
        range_pct = float((latest_high - latest_low) / max(entry, 1e-9))
        atr_pct_proxy = max(range_pct, float(avg_range / max(entry, 1e-9)))
        liquidity_penalty_pct = 0.0015 if avg_dollar_volume < 5_000_000 else 0.0008
        price_penalty_pct = 0.0012 if entry < 5 else 0.0004 if entry < 15 else 0.00015
        liquidity_factor = 1.0 - min(avg_dollar_volume / 50_000_000, 1.0)
        spread_proxy_pct = min(0.025, max(0.0004, range_pct * (0.05 + 0.15 * liquidity_factor)))
        participation_rate = min(0.05, max(0.001, 250_000.0 / max(avg_dollar_volume, 1.0)))
        slippage_pct = min(0.03, atr_pct_proxy * (0.03 + np.sqrt(participation_rate) * 0.25))
        entry_gap_pct = abs(float(latest_open) / max(previous_close, 1e-9) - 1.0)
        entry_gap_penalty_pct = min(0.02, entry_gap_pct * 0.35)
        short_borrow_proxy_pct = min(
            0.015,
            0.00025 + max(0.0, 5_000_000.0 - avg_dollar_volume) / 5_000_000.0 * 0.004,
        )
        adverse_fill_pressure = min(
            1.0,
            spread_proxy_pct / 0.02 + slippage_pct / 0.03 + entry_gap_penalty_pct / 0.02,
        )
        fill_probability = max(0.10, min(0.99, 0.98 - adverse_fill_pressure * 0.22))
        max_size_usd = max(0.0, min(avg_dollar_volume * 0.005, adv_shares * entry * 0.02))
        roundtrip_cost_pct = (
            liquidity_penalty_pct
            + price_penalty_pct
            + spread_proxy_pct
            + slippage_pct
            + entry_gap_penalty_pct
        )
        execution_cost_r = max(0.0, float(entry * roundtrip_cost_pct / max(risk_proxy, 1e-9)))
        return {
            "execution_cost_r": execution_cost_r,
            "spread_proxy_pct": float(spread_proxy_pct),
            "slippage_proxy_pct": float(slippage_pct),
            "entry_gap_penalty_pct": float(entry_gap_penalty_pct),
            "liquidity_penalty_pct": float(liquidity_penalty_pct),
            "price_penalty_pct": float(price_penalty_pct),
            "short_borrow_proxy_pct": float(short_borrow_proxy_pct),
            "fill_probability": float(fill_probability),
            "max_size_usd": float(max_size_usd),
            "avg_dollar_volume": float(avg_dollar_volume),
            "participation_rate": float(participation_rate),
        }

    @staticmethod
    def _rolling_mean(values: np.ndarray, window: int) -> np.ndarray:
        return (
            pd.Series(values)
            .rolling(max(1, int(window)), min_periods=1)
            .mean()
            .to_numpy(dtype=float, copy=False)
        )

    def _path_outcome(
        self,
        entry: float,
        risk: float,
        future: pd.DataFrame,
        side: str,
    ) -> tuple[float, bool, int | None, int | None, str]:
        closes = future["close"].astype(float).to_numpy()
        highs = future["high"].astype(float).to_numpy()
        lows = future["low"].astype(float).to_numpy()
        return self._path_outcome_from_arrays(entry, risk, highs, lows, closes, side=side)

    def _path_outcome_from_arrays(
        self,
        entry: float,
        risk: float,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        side: str,
    ) -> tuple[float, bool, int | None, int | None, str]:
        if side == "long":
            target = entry + self.target_r * risk
            stop = entry - self.stop_r * risk
            for bar, (high, low) in enumerate(zip(highs, lows), start=1):
                # Conservative path assumption: if both are touched intrabar,
                # stop is considered first. That prevents discovery from being
                # overly optimistic on daily bars.
                if float(low) <= stop:
                    return -self.stop_r, False, None, bar, "stop"
                if float(high) >= target:
                    return self.target_r, True, bar, None, "target"
            return float((closes[-1] - entry) / risk), False, None, None, "timeout"
        target = entry - self.target_r * risk
        stop = entry + self.stop_r * risk
        for bar, (high, low) in enumerate(zip(highs, lows), start=1):
            if float(high) >= stop:
                return -self.stop_r, False, None, bar, "stop"
            if float(low) <= target:
                return self.target_r, True, bar, None, "target"
        return float((entry - closes[-1]) / risk), False, None, None, "timeout"

    @staticmethod
    def _speed_label(target_bar: int | None, stop_bar: int | None, horizon: int) -> str:
        if target_bar is None:
            return "stopped" if stop_bar is not None else "timeout"
        fast_cutoff = max(2, int(np.ceil(max(horizon, 1) * 0.25)))
        slow_cutoff = max(fast_cutoff + 1, int(np.ceil(max(horizon, 1) * 0.70)))
        if target_bar <= fast_cutoff:
            return "fast_target"
        if target_bar >= slow_cutoff:
            return "slow_target"
        return "normal_target"

    @staticmethod
    def _data_lineage_features(window: pd.DataFrame) -> dict[str, object]:
        return WindowSampler._data_lineage_features_at(window, -1)

    @staticmethod
    def _data_lineage_features_at(frame: pd.DataFrame, position: int) -> dict[str, object]:
        lineage: dict[str, object] = {}
        latest: pd.Series | None = None
        if "adjusted" in frame.columns:
            latest = frame.iloc[position] if latest is None else latest
            lineage["data_adjusted"] = bool(latest["adjusted"])
        if "what_to_show" in frame.columns:
            latest = frame.iloc[position] if latest is None else latest
            lineage["data_what_to_show"] = str(latest["what_to_show"])
        if "bar_complete" in frame.columns:
            latest = frame.iloc[position] if latest is None else latest
            lineage["data_bar_complete"] = bool(latest["bar_complete"])
        return lineage

    @staticmethod
    def _date_str(value: object) -> str:
        ts = pd.Timestamp(value)
        return ts.isoformat()

    @staticmethod
    def _year(value: object) -> int:
        return int(pd.Timestamp(value).year)
