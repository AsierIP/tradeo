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


def bounded_dtw_distances_to_prototype(
    matrices: np.ndarray,
    prototype: np.ndarray,
    *,
    band: int | None = None,
) -> np.ndarray:
    matrices, prototype = _validated_batch(matrices, prototype)
    batch_size = matrices.shape[0]
    n = matrices.shape[2]
    m = prototype.shape[1]
    width = _band_width(n, m, band)
    channel_scale = max(1.0, math.sqrt(float(matrices.shape[1])))
    previous = np.full((batch_size, m + 1), np.inf, dtype=float)
    previous[:, 0] = 0.0
    for i in range(1, n + 1):
        current = np.full((batch_size, m + 1), np.inf, dtype=float)
        j_start = max(1, i - width)
        j_end = min(m, i + width)
        prototype_slice = prototype[:, j_start - 1 : j_end]
        deltas = matrices[:, :, i - 1, None] - prototype_slice[None, :, :]
        point_cost_row = np.sqrt(np.sum(deltas * deltas, axis=1)) / channel_scale
        for offset, j in enumerate(range(j_start, j_end + 1)):
            current[:, j] = point_cost_row[:, offset] + np.minimum(
                np.minimum(previous[:, j], current[:, j - 1]),
                previous[:, j - 1],
            )
        previous = current
    values = previous[:, m] / max(1, max(n, m))
    values[~np.isfinite(values)] = math.inf
    return values


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
    point_costs = _point_cost_matrix(left, right)
    previous = np.full(m + 1, np.inf, dtype=float)
    previous[0] = 0.0
    for i in range(1, n + 1):
        current = np.full(m + 1, np.inf, dtype=float)
        j_start = max(1, i - width)
        j_end = min(m, i + width)
        point_cost_row = point_costs[i - 1]
        for j in range(j_start, j_end + 1):
            cost = point_cost_row[j - 1]
            current[j] = cost + min(previous[j], current[j - 1], previous[j - 1])
        previous = current
    value = float(previous[m])
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
    point_costs = _point_cost_matrix(left, right)
    previous = np.full(m + 1, np.inf, dtype=float)
    previous[0] = 0.0
    for i in range(1, n + 1):
        current = np.full(m + 1, np.inf, dtype=float)
        j_start = max(1, i - width)
        j_end = min(m, i + width)
        point_cost_row = point_costs[i - 1]
        for j in range(j_start, j_end + 1):
            up = previous[j]
            left_cost = current[j - 1]
            diagonal = previous[j - 1]
            if not (math.isfinite(up) or math.isfinite(left_cost) or math.isfinite(diagonal)):
                continue
            cost = point_cost_row[j - 1]
            current[j] = cost + _softmin3(up, left_cost, diagonal, gamma)
        previous = current
    value = float(previous[m])
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


def _validated_batch(matrices: np.ndarray, prototype: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    matrices = np.asarray(matrices, dtype=float)
    prototype = np.asarray(prototype, dtype=float)
    if prototype.ndim == 1:
        prototype = prototype.reshape(1, -1)
    if matrices.ndim == 2:
        matrices = matrices.reshape(1, *matrices.shape)
    if matrices.ndim != 3 or prototype.ndim != 2:
        raise ValueError("shape batch must be 3-D and prototype must be 1-D or 2-D")
    if matrices.shape[0] == 0:
        raise ValueError("shape batch must contain at least one matrix")
    if matrices.shape[1] != prototype.shape[0]:
        raise ValueError("shape matrices must have the same channel count")
    if matrices.shape[2] == 0 or prototype.shape[1] == 0:
        raise ValueError("shape matrices must have at least one point")
    if not np.isfinite(matrices).all() or not np.isfinite(prototype).all():
        raise ValueError("shape matrices must be finite")
    return matrices, prototype


def _band_width(n: int, m: int, band: int | None) -> int:
    if band is None:
        return max(n, m)
    return max(abs(n - m), int(band), 0)


def _point_cost(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(1.0, math.sqrt(float(left.shape[0]))))


def _point_cost_matrix(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    channel_scale = max(1.0, math.sqrt(float(left.shape[0])))
    deltas = left[:, :, None] - right[:, None, :]
    return np.sqrt(np.sum(deltas * deltas, axis=0)) / channel_scale


def _softmin(values: np.ndarray, gamma: float) -> float:
    offset = float(np.min(values))
    return offset - gamma * float(np.log(np.sum(np.exp(-(values - offset) / gamma))))


def _softmin3(first: float, second: float, third: float, gamma: float) -> float:
    offset = min(first, second, third)
    total = 0.0
    if math.isfinite(first):
        total += math.exp(-(first - offset) / gamma)
    if math.isfinite(second):
        total += math.exp(-(second - offset) / gamma)
    if math.isfinite(third):
        total += math.exp(-(third - offset) / gamma)
    return offset - gamma * math.log(total)


def _resample(values: np.ndarray, length: int) -> np.ndarray:
    length = max(1, int(length))
    if len(values) == length:
        return values.astype(float)
    if len(values) == 1:
        return np.repeat(float(values[0]), length)
    old_x = np.linspace(0.0, 1.0, len(values))
    new_x = np.linspace(0.0, 1.0, length)
    return np.interp(new_x, old_x, values)
