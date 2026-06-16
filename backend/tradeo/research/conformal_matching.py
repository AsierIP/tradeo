from __future__ import annotations

import math
from typing import Any

import numpy as np

METHOD = "split_conformal_similarity_threshold_v1"


def split_conformal_similarity_threshold(
    calibration_similarities: np.ndarray | list[float],
    *,
    alpha: float = 0.10,
    min_calibration_count: int = 20,
) -> dict[str, Any]:
    """Finite-sample threshold for accepting true pattern members.

    Similarities are higher-is-better. We convert to nonconformity
    ``1 - similarity`` and use the standard split-conformal quantile
    ``ceil((n + 1) * (1 - alpha)) / n``. A new match passes if its similarity is
    at least the returned threshold.
    """
    try:
        sims = np.asarray(calibration_similarities, dtype=float)
    except (TypeError, ValueError):
        return _blocked("calibration_similarities_must_be_numeric")
    if sims.ndim != 1:
        return _blocked("calibration_similarities_must_be_1d")
    if not np.isfinite(sims).all():
        return _blocked(
            "similarities_must_be_finite",
            calibration_count=int(np.isfinite(sims).sum()),
            invalid_count=int(np.size(sims) - np.isfinite(sims).sum()),
        )
    n = int(sims.size)
    if n < int(min_calibration_count):
        return _blocked(
            "insufficient_calibration_members",
            calibration_count=n,
            min_calibration_count=int(min_calibration_count),
        )
    if np.any((sims < 0.0) | (sims > 1.0)):
        return _blocked("similarities_must_be_unit_interval", calibration_count=n)
    alpha = float(alpha)
    if not 0.0 < alpha < 1.0:
        return _blocked("alpha_must_be_between_0_and_1", calibration_count=n, alpha=alpha)

    nonconformity = np.sort(1.0 - sims)
    rank = min(n, int(math.ceil((n + 1) * (1.0 - alpha))))
    q_hat = float(nonconformity[rank - 1])
    threshold = 1.0 - q_hat
    recall_on_calibration = float(np.mean(sims >= threshold))
    return {
        "method": METHOD,
        "blocked": False,
        "passed": True,
        "alpha": alpha,
        "target_recall": round(float(1.0 - alpha), 6),
        "calibration_count": n,
        "conformal_rank": rank,
        "nonconformity_quantile": round(q_hat, 6),
        "similarity_threshold": round(float(threshold), 6),
        "recall_on_calibration": round(recall_on_calibration, 6),
    }


def false_positive_rate_at_threshold(
    negative_similarities: np.ndarray | list[float],
    *,
    threshold: float,
) -> dict[str, Any]:
    try:
        sims = np.asarray(negative_similarities, dtype=float)
    except (TypeError, ValueError):
        return _blocked(
            "negative_similarities_must_be_numeric",
            method="fpr_at_similarity_threshold_v1",
        )
    if sims.ndim != 1:
        return _blocked("negative_similarities_must_be_1d", method="fpr_at_similarity_threshold_v1")
    if not np.isfinite(sims).all():
        return _blocked(
            "negative_similarities_must_be_finite",
            method="fpr_at_similarity_threshold_v1",
            negative_count=int(np.isfinite(sims).sum()),
            invalid_count=int(np.size(sims) - np.isfinite(sims).sum()),
        )
    n = int(sims.size)
    if n == 0:
        return _blocked("no_negative_similarities", method="fpr_at_similarity_threshold_v1")
    threshold = float(threshold)
    if not 0.0 <= threshold <= 1.0:
        return _blocked(
            "threshold_must_be_unit_interval",
            method="fpr_at_similarity_threshold_v1",
            negative_count=n,
        )
    hits = int(np.sum(sims >= threshold))
    return {
        "method": "fpr_at_similarity_threshold_v1",
        "blocked": False,
        "passed": True,
        "negative_count": n,
        "threshold": round(threshold, 6),
        "false_positive_count": hits,
        "fpr": round(hits / n, 6),
        "max_negative_similarity": round(float(np.max(sims)), 6),
    }


def _blocked(reason: str, *, method: str = METHOD, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"method": method, "blocked": True, "passed": False, "reason": reason}
    out.update(extra)
    return out
