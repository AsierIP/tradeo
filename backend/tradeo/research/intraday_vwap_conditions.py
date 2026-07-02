from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from tradeo.research.intraday_vwap_features import build_intraday_vwap_features

VWAP_CONDITION_NONE = "none"
VWAP_CONDITION_CHOICES = {
    VWAP_CONDITION_NONE,
    "vwap_reclaim_long",
    "vwap_reject_short",
    "vwap_pullback_long",
    "vwap_pullback_short",
    "vwap_above_rising",
    "vwap_below_falling",
    "vwap_mean_reversion_long",
    "vwap_mean_reversion_short",
}
_LONG_CONDITIONS = {
    "vwap_reclaim_long",
    "vwap_pullback_long",
    "vwap_above_rising",
    "vwap_mean_reversion_long",
}
_SHORT_CONDITIONS = {
    "vwap_reject_short",
    "vwap_pullback_short",
    "vwap_below_falling",
    "vwap_mean_reversion_short",
}
_DEFAULT_NEAR_VWAP_BPS = 150.0
_DEFAULT_EXTENSION_BPS = 150.0


@dataclass(frozen=True, slots=True)
class VWAPConditionSpec:
    condition: str = VWAP_CONDITION_NONE
    side_bias: str | None = None
    max_distance_bps: float | None = None
    min_slope_bps: float | None = None

    @property
    def enabled(self) -> bool:
        return self.condition != VWAP_CONDITION_NONE

    def to_params(self) -> dict[str, Any]:
        return {
            "vwap_condition": self.condition,
            "vwap_side_bias": self.side_bias,
            "vwap_max_distance_bps": self.max_distance_bps,
            "vwap_min_slope_bps": self.min_slope_bps,
        }


def normalize_vwap_condition_spec(
    *,
    condition: str | None = None,
    side_bias: str | None = None,
    max_distance_bps: float | None = None,
    min_slope_bps: float | None = None,
) -> VWAPConditionSpec:
    normalized_condition = str(condition or VWAP_CONDITION_NONE).strip().lower() or VWAP_CONDITION_NONE
    if normalized_condition not in VWAP_CONDITION_CHOICES:
        raise ValueError(f"unsupported vwap_condition: {condition!r}")
    normalized_side = str(side_bias or "").strip().lower() or None
    if normalized_side not in {None, "long", "short"}:
        raise ValueError("vwap_side_bias must be long, short or empty")
    if normalized_condition in _LONG_CONDITIONS and normalized_side is None:
        normalized_side = "long"
    if normalized_condition in _SHORT_CONDITIONS and normalized_side is None:
        normalized_side = "short"
    return VWAPConditionSpec(
        condition=normalized_condition,
        side_bias=normalized_side,
        max_distance_bps=_optional_float(max_distance_bps),
        min_slope_bps=_optional_float(min_slope_bps),
    )


def build_vwap_condition_frame(df: pd.DataFrame) -> pd.DataFrame:
    features = build_intraday_vwap_features(
        df,
        price_mode="close",
        slope_lookback=1,
        extension_bps=_DEFAULT_EXTENSION_BPS,
    ).frame
    return features.reset_index(drop=True)


def vwap_features_at(frame: pd.DataFrame, end_pos: int, spec: VWAPConditionSpec) -> dict[str, Any]:
    row = frame.iloc[int(end_pos)]
    out = {
        "vwap_condition": spec.condition,
        "vwap_side_bias": spec.side_bias,
        "vwap_condition_passed": bool(vwap_condition_passes(frame, int(end_pos), spec)),
        "vwap": _optional_float(row.get("vwap")),
        "vwap_distance_bps": _optional_float(row.get("vwap_distance_bps")),
        "vwap_slope_bps": _optional_float(row.get("vwap_slope_bps")),
        "vwap_slope_direction": str(row.get("vwap_slope_direction") or "unknown"),
        "above_vwap": bool(row.get("above_vwap")),
        "below_vwap": bool(row.get("below_vwap")),
        "crossed_above_vwap": bool(row.get("crossed_above_vwap")),
        "crossed_below_vwap": bool(row.get("crossed_below_vwap")),
        "vwap_reclaim_long": bool(row.get("vwap_reclaim_long")),
        "vwap_reject_short": bool(row.get("vwap_reject_short")),
        "vwap_mean_reversion_candidate": bool(row.get("vwap_mean_reversion_candidate")),
    }
    bars_since_cross = row.get("bars_since_vwap_cross")
    out["bars_since_vwap_cross"] = int(bars_since_cross) if pd.notna(bars_since_cross) else None
    return out


def vwap_condition_passes(frame: pd.DataFrame, end_pos: int, spec: VWAPConditionSpec) -> bool:
    if not spec.enabled:
        return True
    row = frame.iloc[int(end_pos)]
    if not bool(row.get("in_regular_session")) or pd.isna(row.get("vwap")):
        return False
    distance = _optional_float(row.get("vwap_distance_bps"))
    slope = _optional_float(row.get("vwap_slope_bps"))
    if distance is None:
        return False
    if spec.condition == "vwap_reclaim_long":
        return _reclaim_long(row, distance, slope, spec)
    if spec.condition == "vwap_reject_short":
        return _reject_short(row, distance, slope, spec)
    if spec.condition == "vwap_pullback_long":
        return _pullback_long(row, distance, spec)
    if spec.condition == "vwap_pullback_short":
        return _pullback_short(row, distance, spec)
    if spec.condition == "vwap_above_rising":
        return _above_rising(row, distance, slope, spec)
    if spec.condition == "vwap_below_falling":
        return _below_falling(row, distance, slope, spec)
    if spec.condition == "vwap_mean_reversion_long":
        return _mean_reversion_long(row, distance, spec)
    if spec.condition == "vwap_mean_reversion_short":
        return _mean_reversion_short(row, distance, spec)
    return False


def _reclaim_long(row: pd.Series, distance: float, slope: float | None, spec: VWAPConditionSpec) -> bool:
    if not bool(row.get("above_vwap")):
        return False
    if not _slope_at_least(slope, spec.min_slope_bps):
        return False
    max_distance = spec.max_distance_bps
    if max_distance is not None and distance > max_distance:
        return False
    bars_since = row.get("bars_since_vwap_cross")
    recent_cross = pd.notna(bars_since) and int(bars_since) <= 1
    return bool(row.get("vwap_reclaim_long")) or recent_cross


def _reject_short(row: pd.Series, distance: float, slope: float | None, spec: VWAPConditionSpec) -> bool:
    if not bool(row.get("below_vwap")):
        return False
    max_distance = spec.max_distance_bps
    if max_distance is not None and abs(distance) > max_distance:
        return False
    if spec.min_slope_bps is not None and slope is not None and slope > -abs(spec.min_slope_bps):
        return False
    return bool(row.get("vwap_reject_short")) or bool(row.get("crossed_below_vwap"))


def _pullback_long(row: pd.Series, distance: float, spec: VWAPConditionSpec) -> bool:
    near = spec.max_distance_bps if spec.max_distance_bps is not None else _DEFAULT_NEAR_VWAP_BPS
    return bool(row.get("above_vwap")) and 0.0 <= distance <= near and bool(row.get("vwap_hold_long"))


def _pullback_short(row: pd.Series, distance: float, spec: VWAPConditionSpec) -> bool:
    near = spec.max_distance_bps if spec.max_distance_bps is not None else _DEFAULT_NEAR_VWAP_BPS
    return bool(row.get("below_vwap")) and -near <= distance <= 0.0 and bool(row.get("vwap_reject_short"))


def _above_rising(row: pd.Series, distance: float, slope: float | None, spec: VWAPConditionSpec) -> bool:
    if not bool(row.get("above_vwap")) or not _slope_at_least(slope, spec.min_slope_bps):
        return False
    return spec.max_distance_bps is None or distance <= spec.max_distance_bps


def _below_falling(row: pd.Series, distance: float, slope: float | None, spec: VWAPConditionSpec) -> bool:
    if not bool(row.get("below_vwap")):
        return False
    min_slope = abs(spec.min_slope_bps) if spec.min_slope_bps is not None else 0.0
    if slope is not None and slope > -min_slope:
        return False
    return spec.max_distance_bps is None or abs(distance) <= spec.max_distance_bps


def _mean_reversion_long(row: pd.Series, distance: float, spec: VWAPConditionSpec) -> bool:
    extension = spec.max_distance_bps if spec.max_distance_bps is not None else _DEFAULT_EXTENSION_BPS
    return bool(row.get("below_vwap")) and distance <= -abs(extension)


def _mean_reversion_short(row: pd.Series, distance: float, spec: VWAPConditionSpec) -> bool:
    extension = spec.max_distance_bps if spec.max_distance_bps is not None else _DEFAULT_EXTENSION_BPS
    return bool(row.get("above_vwap")) and distance >= abs(extension)


def _slope_at_least(value: float | None, minimum: float | None) -> bool:
    if minimum is None:
        return value is None or value >= 0.0
    return value is not None and value >= minimum


def _optional_float(value: Any) -> float | None:
    if value in (None, "") or pd.isna(value):
        return None
    return float(value)
