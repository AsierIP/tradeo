from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.research.types import ForwardOutcome, WindowSample
from tradeo.services.technical_indicators import atr, normalize_ohlcv


@dataclass(slots=True)
class WindowSampler:
    """Extract fixed-length pattern windows and label each with future path stats."""

    embedding_engine: PatternEmbeddingEngine | None = None
    target_r: float = 4.0
    stop_r: float = 1.0
    min_risk_pct: float = 0.015
    atr_multiplier: float = 1.5

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
    ) -> list[WindowSample]:
        df = normalize_ohlcv(df).dropna()
        forward_bars = sorted({int(x) for x in forward_bars if int(x) > 0})
        if not forward_bars:
            raise ValueError("at least one forward horizon is required")
        max_forward = max(forward_bars)
        if len(df) < max(window_sizes) + max_forward + 5:
            return []

        atr_series = atr(df, 14).bfill().fillna(df["close"] * self.min_risk_pct)
        samples: list[WindowSample] = []
        for window_size in sorted({int(x) for x in window_sizes if int(x) >= 10}):
            if len(df) < window_size + max_forward + 2:
                continue
            # Sample from old to new. A stride keeps the system cheap enough to
            # run continuously, while still covering overlapping market states.
            for end_pos in range(window_size - 1, len(df) - max_forward - 1, max(1, stride)):
                window = df.iloc[end_pos - window_size + 1 : end_pos + 1]
                future = df.iloc[end_pos + 1 : end_pos + 1 + max_forward]
                if future.empty:
                    continue
                entry = float(window["close"].iloc[-1])
                if entry <= 0:
                    continue
                risk_proxy = max(
                    float(atr_series.iloc[end_pos]) * self.atr_multiplier,
                    entry * self.min_risk_pct,
                    0.01,
                )
                execution_cost_r = self._execution_cost_r(window, entry=entry, risk_proxy=risk_proxy)
                outcome = self._forward_outcome(entry, risk_proxy, future, forward_bars, execution_cost_r)
                vector, features, chart = self.embedding_engine.embed(window)
                start_idx = window.index[0]
                end_idx = window.index[-1]
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
                if len(samples) >= max_windows_per_symbol:
                    return samples
        return samples

    def _forward_outcome(
        self,
        entry: float,
        risk_proxy: float,
        future: pd.DataFrame,
        forward_bars: list[int],
        execution_cost_r: float = 0.0,
    ) -> ForwardOutcome:
        closes = future["close"].astype(float).to_numpy()
        highs = future["high"].astype(float).to_numpy()
        lows = future["low"].astype(float).to_numpy()
        forward_returns = {}
        for horizon in forward_bars:
            idx = min(horizon, len(closes)) - 1
            forward_returns[horizon] = float(closes[idx] / entry - 1.0)

        long_mfe_r = float(np.max(highs - entry) / risk_proxy)
        long_mae_r = float(max(0.0, np.max(entry - lows) / risk_proxy))
        short_mfe_r = float(np.max(entry - lows) / risk_proxy)
        short_mae_r = float(max(0.0, np.max(highs - entry) / risk_proxy))
        long_outcome_r, long_hit_4r = self._path_outcome(entry, risk_proxy, future, side="long")
        short_outcome_r, short_hit_4r = self._path_outcome(entry, risk_proxy, future, side="short")
        return ForwardOutcome(
            forward_returns=forward_returns,
            entry_price=float(entry),
            risk_proxy=float(risk_proxy),
            forward_end=self._date_str(future.index[-1]),
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
            execution_cost_r=round(float(execution_cost_r), 5),
        )

    @staticmethod
    def _execution_cost_r(window: pd.DataFrame, *, entry: float, risk_proxy: float) -> float:
        latest = window.iloc[-1]
        range_pct = float((latest["high"] - latest["low"]) / max(entry, 1e-9))
        avg_dollar_volume = float((window["close"] * window["volume"]).tail(20).mean())
        liquidity_penalty_pct = 0.0015 if avg_dollar_volume < 5_000_000 else 0.0008
        spread_proxy_pct = min(0.02, max(0.0005, range_pct * 0.08))
        roundtrip_cost = entry * (liquidity_penalty_pct + spread_proxy_pct)
        return max(0.0, float(roundtrip_cost / max(risk_proxy, 1e-9)))

    def _path_outcome(self, entry: float, risk: float, future: pd.DataFrame, side: str) -> tuple[float, bool]:
        if side == "long":
            target = entry + self.target_r * risk
            stop = entry - self.stop_r * risk
            for _, row in future.iterrows():
                # Conservative path assumption: if both are touched intrabar,
                # stop is considered first. That prevents discovery from being
                # overly optimistic on daily bars.
                if float(row["low"]) <= stop:
                    return -self.stop_r, False
                if float(row["high"]) >= target:
                    return self.target_r, True
            return float((future["close"].iloc[-1] - entry) / risk), False
        target = entry - self.target_r * risk
        stop = entry + self.stop_r * risk
        for _, row in future.iterrows():
            if float(row["high"]) >= stop:
                return -self.stop_r, False
            if float(row["low"]) <= target:
                return self.target_r, True
        return float((entry - future["close"].iloc[-1]) / risk), False

    @staticmethod
    def _date_str(value: object) -> str:
        ts = pd.Timestamp(value)
        return ts.isoformat()

    @staticmethod
    def _year(value: object) -> int:
        return int(pd.Timestamp(value).year)
