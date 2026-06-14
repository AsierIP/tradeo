from __future__ import annotations

import math
from typing import Iterable

import numpy as np

DEFAULT_SHAPE_CHANNELS: tuple[str, ...] = ("close_norm", "volume_rel")
SHAPE_VERIFIER_METHOD = "bounded_dtw_shape_verifier_v1"


def shape_matrix_from_chart(
    chart: dict[str, object] | None,
    *,
    channels: Iterable[str] = DEFAULT_SHAPE_CHANNELS,
    length: int = 48,
) -> np.ndarray | None:
    if not isinstance(chart, dict):
        return None
    rows: list[np.ndarray] = []
    for channel in channels:
        raw = chart.get(str(channel))
        if not isinstance(raw, list | tuple) or not raw:
            return None
        try:
            values = np.asarray(raw, dtype=float)
        except (TypeError, ValueError):
            return None
        if values.ndim != 1 or not np.isfinite(values).all():
            return None
        rows.append(_resample(values, int(length)))
    if not rows:
        return None
    return np.vstack(rows)


def shape_distance(
    left: np.ndarray,
    right: np.ndarray,
    *,
    method: str = "dtw",
    band: int | None = None,
    gamma: float = 0.05,
) -> float:
    method_key = str(method).lower().replace("-", "_")
    if method_key in {"soft_dtw", "softdtw"}:
        return soft_dtw_divergence(left, right, band=band, gamma=gamma)
    return bounded_dtw_distance(left, right, band=band)


def bounded_dtw_distance(
    left: np.ndarray,
    right: np.ndarray,
    *,
    band: int | None = None,
) -> float:
    left, right = _validated_pair(left, right)
    n = left.shape[1]
    m = right.shape[1]
    width = _band_width(n, m, band)
    dp = np.full((n + 1, m + 1), np.inf, dtype=float)
    dp[0, 0] = 0.0
    for i in range(1, n + 1):
        j_start = max(1, i - width)
        j_end = min(m, i + width)
        for j in range(j_start, j_end + 1):
            cost = _point_cost(left[:, i - 1], right[:, j - 1])
            dp[i, j] = cost + min(dp[i - 1, j], dp[i, j - 1], dp[i - 1, j - 1])
    value = float(dp[n, m])
    if not math.isfinite(value):
        return math.inf
    return value / max(1, max(n, m))


def soft_dtw_divergence(
    left: np.ndarray,
    right: np.ndarray,
    *,
    band: int | None = None,
    gamma: float = 0.05,
) -> float:
    left, right = _validated_pair(left, right)
    gamma = max(float(gamma), 1e-6)
    raw = _soft_dtw_raw(left, right, band=band, gamma=gamma)
    self_left = _soft_dtw_raw(left, left, band=band, gamma=gamma)
    self_right = _soft_dtw_raw(right, right, band=band, gamma=gamma)
    value = raw - 0.5 * self_left - 0.5 * self_right
    return max(0.0, float(value))


def _soft_dtw_raw(
    left: np.ndarray,
    right: np.ndarray,
    *,
    band: int | None,
    gamma: float,
) -> float:
    n = left.shape[1]
    m = right.shape[1]
    width = _band_width(n, m, band)
    dp = np.full((n + 1, m + 1), np.inf, dtype=float)
    dp[0, 0] = 0.0
    for i in range(1, n + 1):
        j_start = max(1, i - width)
        j_end = min(m, i + width)
        for j in range(j_start, j_end + 1):
            prev = np.asarray([dp[i - 1, j], dp[i, j - 1], dp[i - 1, j - 1]], dtype=float)
            finite = prev[np.isfinite(prev)]
            if finite.size == 0:
                continue
            cost = _point_cost(left[:, i - 1], right[:, j - 1])
            dp[i, j] = cost + _softmin(finite, gamma)
    value = float(dp[n, m])
    if not math.isfinite(value):
        return math.inf
    return value / max(1, max(n, m))


def _validated_pair(left: np.ndarray, right: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    if left.ndim == 1:
        left = left.reshape(1, -1)
    if right.ndim == 1:
        right = right.reshape(1, -1)
    if left.ndim != 2 or right.ndim != 2:
        raise ValueError("shape matrices must be 1-D or 2-D")
    if left.shape[0] != right.shape[0]:
        raise ValueError("shape matrices must have the same channel count")
    if left.shape[1] == 0 or right.shape[1] == 0:
        raise ValueError("shape matrices must have at least one point")
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("shape matrices must be finite")
    return left, right


def _band_width(n: int, m: int, band: int | None) -> int:
    if band is None:
        return max(n, m)
    return max(abs(n - m), int(band), 0)


def _point_cost(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(1.0, math.sqrt(float(left.shape[0]))))


def _softmin(values: np.ndarray, gamma: float) -> float:
    offset = float(np.min(values))
    return offset - gamma * float(np.log(np.sum(np.exp(-(values - offset) / gamma))))


def _resample(values: np.ndarray, length: int) -> np.ndarray:
    length = max(1, int(length))
    if len(values) == length:
        return values.astype(float)
    if len(values) == 1:
        return np.repeat(float(values[0]), length)
    old_x = np.linspace(0.0, 1.0, len(values))
    new_x = np.linspace(0.0, 1.0, length)
    return np.interp(new_x, old_x, values)
