"""Prototype bank: medoids + diagonal covariance + split-conformal thresholds.

Audit §2.3.4 / §3.1.1-3: a single centroid is a poor summary of a non-spherical
cluster. Research persists m medoids and a regularized diagonal covariance per
pattern; the matcher gates on k-NN distance to medoids AND diagonal Mahalanobis
distance, with thresholds calibrated by split conformal on a held-out 25% of
cluster members (never used for medoids/covariance), giving the finite-sample
guarantee P(d <= tau) >= 1 - alpha for exchangeable true members.

Research and Lab import THESE functions, so the distance definitions cannot
drift between the two sides.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from sklearn.cluster import MiniBatchKMeans

PROTOTYPE_BANK_METHOD = "knn_medoids_mahalanobis_diag_split_conformal"
MIN_BANK_MEMBERS = 8


def conformal_tau(member_dists_cal: np.ndarray, alpha: float = 0.10) -> float:
    """Split-conformal quantile (audit §10.2).

    Guarantee under exchangeability: P(d_new_member <= tau) >= 1 - alpha.
    """
    dists = np.asarray(member_dists_cal, dtype=float)
    n = len(dists)
    if n == 0:
        return float("nan")
    k = int(math.ceil((n + 1) * (1.0 - alpha)))
    return float(np.sort(dists)[min(k, n) - 1])


def knn_distance(vector: np.ndarray, medoids: np.ndarray, k: int = 3) -> float:
    """Mean of the k smallest scaled L2 distances to the medoids (§3.1.1).

    Distances are normalized by sqrt(dim) to stay on the same scale as the
    matcher's legacy centroid distance.
    """
    diffs = np.asarray(medoids, dtype=float) - np.asarray(vector, dtype=float)
    dists = np.linalg.norm(diffs, axis=1) / max(1.0, math.sqrt(diffs.shape[1]))
    k = max(1, min(int(k), len(dists)))
    return float(np.mean(np.sort(dists)[:k]))


def mahalanobis_diag_distance(
    vector: np.ndarray,
    center: np.ndarray,
    var_regularized: np.ndarray,
) -> float:
    """Diagonal Mahalanobis distance, mean-normalized per dimension (§3.1.2).

    Catches vectors "close in mean but outside the cloud in the dimensions the
    cluster holds tight". var_regularized must already include the epsilon.
    """
    diff = np.asarray(vector, dtype=float) - np.asarray(center, dtype=float)
    var = np.asarray(var_regularized, dtype=float)
    return float(math.sqrt(float(np.mean((diff * diff) / np.where(var <= 0, 1.0, var)))))


def build_prototype_bank(
    member_vectors_scaled: np.ndarray,
    *,
    medoid_count: int = 16,
    knn_k: int = 3,
    alpha: float = 0.10,
    calibration_fraction: float = 0.25,
    seed: int = 42,
) -> dict[str, Any] | None:
    """Build the persistable bank from a cluster's scaled train-member vectors.

    The calibration split is disjoint from the prototype subset: medoids,
    Mahalanobis center and covariance are fit on the prototype subset only, so
    the calibration distances are valid conformal scores.
    """
    vectors = np.asarray(member_vectors_scaled, dtype=float)
    if vectors.ndim != 2 or len(vectors) < MIN_BANK_MEMBERS:
        return None
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(len(vectors))
    n_cal = max(2, int(round(len(vectors) * calibration_fraction)))
    n_cal = min(n_cal, len(vectors) - 4)
    cal_vectors = vectors[permutation[:n_cal]]
    proto_vectors = vectors[permutation[n_cal:]]

    medoids = _select_medoids(proto_vectors, medoid_count=medoid_count, seed=seed)
    maha_center = proto_vectors.mean(axis=0)
    variance = proto_vectors.var(axis=0)
    eps = max(1e-9, 0.05 * float(np.mean(variance)))
    var_regularized = variance + eps

    cal_knn = np.asarray([knn_distance(v, medoids, knn_k) for v in cal_vectors])
    cal_maha = np.asarray(
        [mahalanobis_diag_distance(v, maha_center, var_regularized) for v in cal_vectors]
    )
    tau_knn = conformal_tau(cal_knn, alpha)
    tau_maha = conformal_tau(cal_maha, alpha)
    if not (math.isfinite(tau_knn) and math.isfinite(tau_maha)):
        return None
    return {
        "method": PROTOTYPE_BANK_METHOD,
        "knn_k": int(knn_k),
        "alpha": round(float(alpha), 6),
        "calibration_fraction": round(float(calibration_fraction), 6),
        "calibration_count": int(n_cal),
        "prototype_count": int(len(proto_vectors)),
        "medoid_count": int(len(medoids)),
        "split_seed": int(seed),
        "medoids": np.round(medoids, 6).tolist(),
        "maha_center": np.round(maha_center, 6).tolist(),
        "maha_var": np.round(var_regularized, 9).tolist(),
        "maha_eps": round(float(eps), 9),
        "tau_knn_distance": round(float(tau_knn), 6),
        "tau_maha_distance": round(float(tau_maha), 6),
        "guarantee": (
            "split_conformal: P(d <= tau) >= 1 - alpha for exchangeable true "
            "members, per distance axis"
        ),
    }


def _select_medoids(proto_vectors: np.ndarray, *, medoid_count: int, seed: int) -> np.ndarray:
    """Pick up to medoid_count actual member vectors covering the cluster."""
    if len(proto_vectors) <= medoid_count:
        return proto_vectors.copy()
    model = MiniBatchKMeans(
        n_clusters=medoid_count,
        random_state=int(seed) % (2**31 - 1),
        n_init=10,
        batch_size=min(2048, max(128, len(proto_vectors))),
    )
    model.fit(proto_vectors)
    chosen: list[int] = []
    for center in model.cluster_centers_:
        idx = int(np.argmin(np.linalg.norm(proto_vectors - center, axis=1)))
        if idx not in chosen:
            chosen.append(idx)
    return proto_vectors[np.asarray(chosen, dtype=int)]


@dataclass(slots=True)
class ParsedPrototypeBank:
    medoids: np.ndarray
    maha_center: np.ndarray
    maha_var: np.ndarray
    tau_knn_distance: float
    tau_maha_distance: float
    knn_k: int
    alpha: float

    @property
    def dimension(self) -> int:
        return int(self.medoids.shape[1])


def parse_prototype_bank(metrics: dict[str, Any] | None) -> ParsedPrototypeBank | None:
    """Validate and parse a persisted bank; None keeps the legacy gate."""
    bank = (metrics or {}).get("prototype_bank")
    if not isinstance(bank, dict):
        return None
    try:
        medoids = np.asarray(bank["medoids"], dtype=float)
        maha_center = np.asarray(bank["maha_center"], dtype=float)
        maha_var = np.asarray(bank["maha_var"], dtype=float)
        tau_knn = float(bank["tau_knn_distance"])
        tau_maha = float(bank["tau_maha_distance"])
        knn_k = int(bank.get("knn_k") or 3)
        alpha = float(bank.get("alpha") or 0.10)
    except (KeyError, TypeError, ValueError):
        return None
    if medoids.ndim != 2 or len(medoids) == 0:
        return None
    dimension = medoids.shape[1]
    if maha_center.shape != (dimension,) or maha_var.shape != (dimension,):
        return None
    if not (math.isfinite(tau_knn) and math.isfinite(tau_maha)):
        return None
    if tau_knn <= 0.0 or tau_maha <= 0.0 or np.any(maha_var <= 0.0):
        return None
    return ParsedPrototypeBank(
        medoids=medoids,
        maha_center=maha_center,
        maha_var=maha_var,
        tau_knn_distance=tau_knn,
        tau_maha_distance=tau_maha,
        knn_k=knn_k,
        alpha=alpha,
    )
