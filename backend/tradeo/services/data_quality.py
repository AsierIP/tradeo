"""Per-symbol OHLCV quality assessment for research-grade scanning.

`normalize_ohlcv`/`validate_ohlcv` reject structurally broken bars (NaN, negative
prices, high < low). This module covers the next layer: data that is well-formed
but statistically poisonous for pattern research — halted/illiquid symbols,
frozen feeds, unadjusted splits and large calendar holes. Symbols failing these
checks should be skipped and audited, never silently sampled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from tradeo.core.config import Settings

ISSUE_INSUFFICIENT_BARS = "insufficient_bars"
ISSUE_ZERO_VOLUME = "excess_zero_volume_bars"
ISSUE_STALE_CLOSES = "stale_close_run"
ISSUE_CALENDAR_GAP = "calendar_gap"
ISSUE_SUSPECT_BAR_RETURN = "suspect_split_or_bad_tick"


@dataclass(frozen=True)
class DataQualityReport:
    symbol: str
    bars: int
    zero_volume_pct: float
    longest_stale_close_run: int
    max_single_gap_business_days: int
    max_bar_return_ratio: float
    issues: list[str] = field(default_factory=list)

    @property
    def research_grade(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "bars": self.bars,
            "zero_volume_pct": round(self.zero_volume_pct, 4),
            "longest_stale_close_run": self.longest_stale_close_run,
            "max_single_gap_business_days": self.max_single_gap_business_days,
            "max_bar_return_ratio": round(self.max_bar_return_ratio, 4),
            "issues": list(self.issues),
            "research_grade": self.research_grade,
        }


def _longest_constant_run(values: pd.Series) -> int:
    if values.empty:
        return 0
    changed = values.ne(values.shift())
    run_ids = changed.cumsum()
    return int(run_ids.value_counts().max())


def _max_business_day_gap(index: pd.Index) -> int:
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return 0
    idx = index.tz_localize(None) if index.tz is not None else index
    starts = idx[:-1].to_numpy(dtype="datetime64[D]")
    ends = idx[1:].to_numpy(dtype="datetime64[D]")
    # Missing business days strictly between consecutive bars.
    gaps = np.busday_count(starts, ends) - 1
    return int(gaps.max()) if len(gaps) else 0


def assess_ohlcv_quality(
    df: pd.DataFrame,
    symbol: str = "",
    *,
    interval: str = "1d",
    min_bars: int = 60,
    max_zero_volume_pct: float = 0.15,
    max_stale_close_run: int = 8,
    max_single_gap_business_days: int = 5,
    max_bar_return_ratio: float = 4.0,
) -> DataQualityReport:
    """Assess whether a normalized OHLCV frame is fit for pattern research.

    Expects a frame already passed through ``normalize_ohlcv`` (lowercase
    columns, sorted index). Calendar-gap detection only applies to daily bars.
    """
    issues: list[str] = []
    bars = int(len(df))
    if bars == 0:
        return DataQualityReport(
            symbol=symbol,
            bars=0,
            zero_volume_pct=1.0,
            longest_stale_close_run=0,
            max_single_gap_business_days=0,
            max_bar_return_ratio=1.0,
            issues=[ISSUE_INSUFFICIENT_BARS],
        )

    zero_volume_pct = float((df["volume"] <= 0).mean())
    stale_run = _longest_constant_run(df["close"])
    gap_days = _max_business_day_gap(df.index) if interval == "1d" else 0
    ratios = (df["close"] / df["close"].shift(1)).dropna()
    if ratios.empty:
        return_ratio = 1.0
    else:
        return_ratio = float(np.maximum(ratios, 1.0 / ratios).max())

    if bars < min_bars:
        issues.append(ISSUE_INSUFFICIENT_BARS)
    if zero_volume_pct > max_zero_volume_pct:
        issues.append(ISSUE_ZERO_VOLUME)
    if stale_run > max_stale_close_run:
        issues.append(ISSUE_STALE_CLOSES)
    if gap_days > max_single_gap_business_days:
        issues.append(ISSUE_CALENDAR_GAP)
    if return_ratio > max_bar_return_ratio:
        issues.append(ISSUE_SUSPECT_BAR_RETURN)

    return DataQualityReport(
        symbol=symbol,
        bars=bars,
        zero_volume_pct=zero_volume_pct,
        longest_stale_close_run=stale_run,
        max_single_gap_business_days=gap_days,
        max_bar_return_ratio=return_ratio,
        issues=issues,
    )


def assess_ohlcv_quality_from_settings(
    df: pd.DataFrame,
    symbol: str,
    interval: str,
    settings: "Settings",
) -> DataQualityReport:
    return assess_ohlcv_quality(
        df,
        symbol,
        interval=interval,
        min_bars=settings.data_quality_min_bars,
        max_zero_volume_pct=settings.data_quality_max_zero_volume_pct,
        max_stale_close_run=settings.data_quality_max_stale_close_run,
        max_single_gap_business_days=settings.data_quality_max_single_gap_business_days,
        max_bar_return_ratio=settings.data_quality_max_bar_return_ratio,
    )
