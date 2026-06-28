from __future__ import annotations

import math

import numpy as np
import pytest

from tradeo.research.shape_verifier import (
    bounded_dtw_distance,
    bounded_dtw_distances_to_prototype,
    shape_distance,
)


def _point_cost(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(left - right) / max(1.0, math.sqrt(float(left.shape[0]))))


def _band_width(n: int, m: int, band: int | None) -> int:
    if band is None:
        return max(n, m)
    return max(abs(n - m), int(band), 0)


def _softmin(values: np.ndarray, gamma: float) -> float:
    offset = float(np.min(values))
    return offset - gamma * float(np.log(np.sum(np.exp(-(values - offset) / gamma))))


def _reference_bounded_dtw_distance(
    left: np.ndarray,
    right: np.ndarray,
    *,
    band: int | None,
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
            cost = _point_cost(left[:, i - 1], right[:, j - 1])
            dp[i, j] = cost + min(dp[i - 1, j], dp[i, j - 1], dp[i - 1, j - 1])
    value = float(dp[n, m])
    if not math.isfinite(value):
        return math.inf
    return value / max(1, max(n, m))


def _reference_soft_dtw_raw(
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


def _reference_soft_dtw_divergence(
    left: np.ndarray,
    right: np.ndarray,
    *,
    band: int | None,
    gamma: float,
) -> float:
    raw = _reference_soft_dtw_raw(left, right, band=band, gamma=gamma)
    self_left = _reference_soft_dtw_raw(left, left, band=band, gamma=gamma)
    self_right = _reference_soft_dtw_raw(right, right, band=band, gamma=gamma)
    return max(0.0, float(raw - 0.5 * self_left - 0.5 * self_right))


@pytest.mark.parametrize("band", [None, 0, 2, 5])
def test_shape_dtw_distances_match_table_reference(band: int | None) -> None:
    rng = np.random.default_rng(123)
    left = rng.normal(size=(3, 13))
    right = rng.normal(size=(3, 11))

    assert bounded_dtw_distance(left, right, band=band) == pytest.approx(
        _reference_bounded_dtw_distance(left, right, band=band)
    )
    assert shape_distance(left, right, method="soft_dtw", band=band, gamma=0.07) == pytest.approx(
        _reference_soft_dtw_divergence(left, right, band=band, gamma=0.07)
    )


@pytest.mark.parametrize("band", [None, 0, 2, 5])
def test_batched_shape_dtw_distances_match_scalar_path(band: int | None) -> None:
    rng = np.random.default_rng(456)
    matrices = rng.normal(size=(7, 3, 13))
    prototype = rng.normal(size=(3, 11))

    batched = bounded_dtw_distances_to_prototype(matrices, prototype, band=band)
    scalar = np.asarray(
        [bounded_dtw_distance(matrix, prototype, band=band) for matrix in matrices],
        dtype=float,
    )

    np.testing.assert_allclose(batched, scalar)
