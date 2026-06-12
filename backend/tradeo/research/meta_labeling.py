"""Meta-labeling calibration contracts for pattern entry selectivity.

This module intentionally starts with the audit-facing evaluation layer, not a
production predictor. A future model can generate probabilities, but it must
first pass these checks before Lab/Fox may use them as an entry gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

METHOD = "meta_label_calibration_v1"


@dataclass(frozen=True, slots=True)
class MetaLabelCalibrationConfig:
    min_samples: int = 50
    min_top_decile_count: int = 5
    brier_max: float = 0.20
    ece_max: float = 0.06
    min_top_decile_uplift: float = 0.08
    top_fraction: float = 0.10
    rr: float = 4.0
    cost_r: float = 0.0
    n_bins: int = 10


def meta_label_calibration_report(
    y_true: np.ndarray | list[float] | list[int],
    probabilities: np.ndarray | list[float],
    *,
    sample_weight: np.ndarray | list[float] | None = None,
    config: MetaLabelCalibrationConfig | None = None,
) -> dict[str, Any]:
    """Evaluate calibrated target-before-stop probabilities.

    ``y_true`` is binary: 1 means the canonical target barrier fired before the
    stop; 0 means stop/timeout/failure. ``probabilities`` must be available at
    decision time and already out-of-sample. The report is fail-closed: blocked
    or failed reports must not become an operational gate.
    """
    cfg = config or MetaLabelCalibrationConfig()
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    if y.ndim != 1 or p.ndim != 1 or y.shape[0] != p.shape[0]:
        return _blocked("inputs_must_be_1d_same_length")
    n = int(y.shape[0])
    if n < int(cfg.min_samples):
        return _blocked("insufficient_samples", sample_count=n, min_samples=int(cfg.min_samples))
    if not np.isin(y, [0.0, 1.0]).all():
        return _blocked("labels_must_be_binary", sample_count=n)
    if not np.isfinite(p).all() or np.any((p < 0.0) | (p > 1.0)):
        return _blocked("probabilities_must_be_finite_unit_interval", sample_count=n)

    weight = _weights(sample_weight, n)
    if weight is None:
        return _blocked("sample_weight_invalid", sample_count=n)

    brier = _weighted_mean((p - y) ** 2, weight)
    ece, bins = expected_calibration_error(y, p, sample_weight=weight, n_bins=cfg.n_bins)
    base_win_rate = _weighted_mean(y, weight)
    top_count = max(1, int(np.ceil(n * float(cfg.top_fraction))))
    order = np.argsort(p)[::-1]
    top_idx = order[:top_count]
    top_win_rate = _weighted_mean(y[top_idx], weight[top_idx])
    uplift = top_win_rate - base_win_rate
    breakeven_probability = (1.0 + float(cfg.cost_r)) / (1.0 + float(cfg.rr))
    selected = p >= breakeven_probability
    selected_count = int(np.sum(selected))
    selected_win_rate = _weighted_mean(y[selected], weight[selected]) if selected_count else 0.0
    selected_expectancy_r = (
        selected_win_rate * float(cfg.rr)
        - (1.0 - selected_win_rate)
        - float(cfg.cost_r)
        if selected_count
        else 0.0
    )

    passed = (
        brier <= float(cfg.brier_max)
        and ece <= float(cfg.ece_max)
        and top_count >= int(cfg.min_top_decile_count)
        and uplift >= float(cfg.min_top_decile_uplift)
    )
    return {
        "method": METHOD,
        "passed": bool(passed),
        "blocked": False,
        "sample_count": n,
        "brier": round(float(brier), 6),
        "brier_max": float(cfg.brier_max),
        "ece": round(float(ece), 6),
        "ece_max": float(cfg.ece_max),
        "calibration_bins": bins,
        "base_win_rate": round(float(base_win_rate), 6),
        "top_fraction": float(cfg.top_fraction),
        "top_count": top_count,
        "top_win_rate": round(float(top_win_rate), 6),
        "top_decile_uplift": round(float(uplift), 6),
        "min_top_decile_uplift": float(cfg.min_top_decile_uplift),
        "rr": float(cfg.rr),
        "cost_r": float(cfg.cost_r),
        "breakeven_probability": round(float(breakeven_probability), 6),
        "selected_count_at_breakeven": selected_count,
        "selected_win_rate_at_breakeven": round(float(selected_win_rate), 6),
        "selected_expectancy_r_at_breakeven": round(float(selected_expectancy_r), 6),
    }


def expected_calibration_error(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    sample_weight: np.ndarray | None = None,
    n_bins: int = 10,
) -> tuple[float, list[dict[str, Any]]]:
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    weight = np.ones_like(p, dtype=float) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    edges = np.linspace(0.0, 1.0, max(2, int(n_bins)) + 1)
    total_weight = max(float(np.sum(weight)), 1e-12)
    ece = 0.0
    bins: list[dict[str, Any]] = []
    for idx in range(len(edges) - 1):
        left = edges[idx]
        right = edges[idx + 1]
        mask = (p >= left) & (p <= right if idx == len(edges) - 2 else p < right)
        if not np.any(mask):
            continue
        bin_weight = float(np.sum(weight[mask]))
        confidence = _weighted_mean(p[mask], weight[mask])
        observed = _weighted_mean(y[mask], weight[mask])
        gap = abs(confidence - observed)
        ece += (bin_weight / total_weight) * gap
        bins.append(
            {
                "bin_left": round(float(left), 4),
                "bin_right": round(float(right), 4),
                "count": int(np.sum(mask)),
                "weight": round(bin_weight, 6),
                "mean_probability": round(float(confidence), 6),
                "observed_win_rate": round(float(observed), 6),
                "abs_gap": round(float(gap), 6),
            }
        )
    return float(ece), bins


def feature_leakage_guard(
    decision_time_features: dict[str, float],
    recomputed_truncated_features: dict[str, float],
    *,
    atol: float = 1e-12,
) -> dict[str, Any]:
    """Compare stored meta features with features recomputed at signal time."""
    keys = sorted(set(decision_time_features) | set(recomputed_truncated_features))
    differences: list[dict[str, Any]] = []
    for key in keys:
        left = decision_time_features.get(key)
        right = recomputed_truncated_features.get(key)
        if left is None or right is None:
            differences.append({"feature": key, "reason": "missing_on_one_side"})
            continue
        if not np.isclose(float(left), float(right), atol=atol, rtol=0.0):
            differences.append(
                {
                    "feature": key,
                    "decision_time": float(left),
                    "recomputed_truncated": float(right),
                }
            )
    return {
        "method": "meta_features_available_at_decision_time",
        "passed": not differences,
        "difference_count": len(differences),
        "differences": differences[:20],
    }


def _blocked(reason: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"method": METHOD, "passed": False, "blocked": True, "reason": reason}
    out.update(extra)
    return out


def _weights(sample_weight: np.ndarray | list[float] | None, n: int) -> np.ndarray | None:
    if sample_weight is None:
        return np.ones(n, dtype=float)
    weight = np.asarray(sample_weight, dtype=float)
    if weight.ndim != 1 or weight.shape[0] != n or not np.isfinite(weight).all():
        return None
    if np.any(weight < 0.0) or float(np.sum(weight)) <= 0.0:
        return None
    return weight


def _weighted_mean(values: np.ndarray, weight: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.average(values, weights=weight))
