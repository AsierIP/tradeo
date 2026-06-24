from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

import numpy as np
import pandas as pd

from tradeo.modules.intraday.features import IntradayFeatureBuilder, IntradayFeatureConfig
from tradeo.modules.intraday.research_contracts import (
    INTRADAY_RESEARCH_CORE_VERSION,
    IntradayResearchDataContract,
    IntradayResearchDataContractBuilder,
    as_utc,
    hash_text,
    json_float,
    normalize_intraday_bars,
)


@dataclass(frozen=True, slots=True)
class IntradayFeatureCube:
    symbol: str
    session_id: str
    contract: IntradayResearchDataContract
    frames: dict[str, pd.DataFrame]
    feature_columns_by_timeframe: dict[str, tuple[str, ...]]
    metadata: dict[str, Any] = field(default_factory=dict)
    contract_version: str = INTRADAY_RESEARCH_CORE_VERSION

    def frame(self, timeframe: str) -> pd.DataFrame:
        return self.frames[timeframe]

    def latest_snapshot(self, timeframe: str) -> dict[str, Any]:
        frame = self.frame(timeframe)
        row = frame.iloc[-1]
        return {
            "symbol": self.symbol,
            "timeframe": timeframe,
            "bar_at": frame.index[-1].isoformat(),
        } | {col: json_float(row[col]) for col in self.feature_columns_by_timeframe[timeframe]}


class IntradayFeatureCubeBuilder:
    """Adds intraday-native, vectorized channels on top of IntradayFeatureBuilder."""

    def __init__(self, config: IntradayFeatureConfig | None = None) -> None:
        self.config = config or IntradayFeatureConfig()
        self.contract_builder = IntradayResearchDataContractBuilder()

    def build(
        self,
        bars_by_timeframe: Mapping[str, pd.DataFrame],
        *,
        symbol: str,
        session_id: str,
        previous_close: float | Mapping[str, float],
        minute_volume_baselines: Mapping[str, Mapping[int | str, float] | pd.Series | pd.DataFrame],
        session_open: pd.Timestamp | str | None = None,
        session_close: pd.Timestamp | str | None = None,
    ) -> IntradayFeatureCube:
        contract = self.contract_builder.build(bars_by_timeframe, symbol=symbol, session_id=session_id)
        prev = previous_close if isinstance(previous_close, Mapping) else {"*": previous_close}
        frames: dict[str, pd.DataFrame] = {}
        columns: dict[str, tuple[str, ...]] = {}
        for timeframe, raw in bars_by_timeframe.items():
            bars = normalize_intraday_bars(raw)
            base = IntradayFeatureBuilder(self.config).build(
                bars,
                symbol=symbol,
                previous_close=float(prev.get(timeframe, prev.get("*"))),
                minute_volume_baseline=minute_volume_baselines[timeframe],
                timeframe=timeframe,
                session_open=session_open,
                session_close=session_close,
            ).frame
            enriched = _enrich_intraday_features(bars, base, self.config)
            frames[timeframe] = enriched
            columns[timeframe] = tuple(
                c for c in enriched.columns if pd.api.types.is_numeric_dtype(enriched[c])
            )
        return IntradayFeatureCube(
            symbol=symbol.upper().strip(),
            session_id=str(session_id),
            contract=contract,
            frames=frames,
            feature_columns_by_timeframe=columns,
            metadata={
                "math_backend": "numpy_pandas_vectorized",
                "complexity_policy": "best_real_solution",
            },
        )


@dataclass(frozen=True, slots=True)
class MultiScaleIntradaySample:
    symbol: str
    session_id: str
    trigger_timeframe: str
    trigger_end_index: int
    trigger_end_ts: datetime
    windows: dict[str, pd.DataFrame]
    data_cutoff_ts: datetime
    source_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MultiScaleSamplerConfig:
    context_bars_by_timeframe: Mapping[str, int] = field(
        default_factory=lambda: {"15m": 20, "5m": 50, "1m": 20}
    )
    stride: int = 1
    max_samples: int = 2_000


class MultiScaleIntradaySampler:
    """Aligns context/setup/trigger windows by timestamp, never future bars."""

    def __init__(self, config: MultiScaleSamplerConfig | None = None) -> None:
        self.config = config or MultiScaleSamplerConfig()

    def sample(
        self,
        cube: IntradayFeatureCube,
        *,
        trigger_timeframe: str = "5m",
    ) -> tuple[MultiScaleIntradaySample, ...]:
        trigger = cube.frame(trigger_timeframe)
        need_trigger = max(1, int(self.config.context_bars_by_timeframe.get(trigger_timeframe, 1)))
        indices = np.arange(need_trigger - 1, len(trigger), max(1, self.config.stride), dtype=int)
        if self.config.max_samples > 0:
            indices = indices[-self.config.max_samples :]
        samples: list[MultiScaleIntradaySample] = []
        for idx in indices:
            ts = trigger.index[int(idx)]
            windows: dict[str, pd.DataFrame] = {}
            for timeframe, frame in cube.frames.items():
                count = max(1, int(self.config.context_bars_by_timeframe.get(timeframe, 1)))
                right = int(frame.index.searchsorted(ts, side="right"))
                if right < count:
                    windows = {}
                    break
                windows[timeframe] = frame.iloc[right - count : right]
            if not windows:
                continue
            source_hash = hash_text(
                cube.contract.manifest_hash + trigger_timeframe + str(idx) + ts.isoformat()
            )
            samples.append(
                MultiScaleIntradaySample(
                    cube.symbol,
                    cube.session_id,
                    trigger_timeframe,
                    int(idx),
                    as_utc(ts.to_pydatetime()),
                    windows,
                    as_utc(ts.to_pydatetime()),
                    source_hash,
                    {"no_lookahead": True, "math_backend": "searchsorted"},
                )
            )
        return tuple(samples)


def _enrich_intraday_features(
    bars: pd.DataFrame,
    base: pd.DataFrame,
    config: IntradayFeatureConfig,
) -> pd.DataFrame:
    out = base.copy()
    close, open_, high, low = (bars[c].astype(float) for c in ("close", "open", "high", "low"))
    safe_close = close.replace(0.0, np.nan)
    out["close"] = close
    out["volume"] = bars["volume"].astype(float)
    out["return_1"] = close.pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    out["return_3"] = close.pct_change(3).replace([np.inf, -np.inf], 0.0).fillna(0.0)
    out["hl_range_pct"] = ((high - low).abs() / safe_close).fillna(0.0)
    out["candle_body_pct"] = ((close - open_).abs() / safe_close).fillna(0.0)
    out["vwap_slope"] = out["vwap"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    out["rvol_acceleration"] = out["rvol"].pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
    spread = out["spread_proxy_bps"].astype(float).clip(lower=1e-9)
    out["spread_compression"] = (
        spread.rolling(5, min_periods=1).mean() / spread - 1.0
    ).clip(-5.0, 5.0)
    range_pct = out["hl_range_pct"].astype(float).clip(lower=1e-9)
    out["range_compression_score"] = (
        range_pct.rolling(8, min_periods=1).mean() / range_pct - 1.0
    ).clip(-5.0, 5.0)
    opening_den = (out["opening_range_high"] - out["opening_range_low"]).replace(0.0, np.nan)
    out["opening_range_position"] = (
        (close - out["opening_range_low"]) / opening_den
    ).clip(-2.0, 3.0).fillna(0.5)
    dollar_score = (
        out["dollar_volume"].astype(float) / max(config.high_liquidity_dollar_volume, 1.0)
    ).clip(0.0, 3.0)
    out["liquidity_phase_score"] = (
        np.log1p(out["rvol"].clip(lower=0.0))
        + dollar_score
        + out["spread_compression"]
        - np.log1p(spread / max(config.tight_spread_bps, 1.0))
    )
    out["bar_index"] = np.arange(len(out), dtype=float)
    numeric = [c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])]
    if not np.isfinite(out[numeric].to_numpy(dtype=float)).all():
        raise ValueError("non_finite_feature_cube")
    return out
