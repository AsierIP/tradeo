from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from tradeo.research.reward_risk_analyzer import RewardRiskAnalyzer
from tradeo.research.types import Side, WindowSample


@dataclass(slots=True)
class FoundationChartTeacher:
    """Cheap self-supervised diagnostics for chart embeddings.

    The goal is foundation-model-like discipline without a foundation model:
    masked-window reconstruction, contrastive family compactness and future
    proxy alignment are deterministic NumPy diagnostics stored with each pattern.
    """

    mask_fraction: float = 0.25
    min_vector_dims_for_corr: int = 8

    def analyze(
        self,
        samples: list[WindowSample],
        *,
        side: Side,
        rr: float,
        centroid: list[float] | np.ndarray | None = None,
        baseline_samples: list[WindowSample] | None = None,
    ) -> dict[str, Any]:
        if not samples:
            return self._empty()
        masked = self._masked_reconstruction(samples)
        contrastive = self._contrastive_diagnostics(samples, baseline_samples or [], centroid)
        future_proxy = self._future_proxy_objectives(samples, side, rr)
        quality = (
            float(masked["masked_window_reconstruction_score"]) * 0.35
            + float(contrastive["contrastive_score"]) * 0.35
            + float(future_proxy["future_proxy_alignment_score"]) * 0.30
        )
        digest = {
            "teacher_version": "deterministic_proxy_v1",
            "embedding_quality_score": round(float(max(0.0, min(1.0, quality))), 5),
            "objectives": [
                "masked_window_reconstruction",
                "contrastive_neighborhood_compactness",
                "future_proxy_alignment",
            ],
            "use_for_reporting": bool(quality >= 0.35),
            "notes": (
                "Embedding looks coherent enough for lab reporting"
                if quality >= 0.35
                else "Embedding diagnostics are weak; require more samples or features"
            ),
        }
        return {
            "method": "deterministic_self_supervised_proxy_teacher",
            **masked,
            "contrastive_diagnostics": contrastive,
            "future_proxy_objectives": future_proxy,
            "pretraining_digest": digest,
        }

    def _masked_reconstruction(self, samples: list[WindowSample]) -> dict[str, float | int]:
        errors: list[float] = []
        channel_count = 0
        for sample in samples:
            channels = self._chart_channels(sample)
            if not channels:
                channels = [np.asarray(sample.vector, dtype=float)]
            for channel in channels:
                if len(channel) < 6:
                    continue
                channel_count += 1
                errors.append(self._masked_channel_error(channel))
        if not errors:
            return {
                "masked_window_reconstruction_score": 0.0,
                "masked_window_error": 0.0,
                "masked_channel_count": 0,
            }
        error = float(np.mean(errors))
        return {
            "masked_window_reconstruction_score": round(float(1.0 / (1.0 + error)), 5),
            "masked_window_error": round(error, 5),
            "masked_channel_count": int(channel_count),
        }

    def _masked_channel_error(self, values: np.ndarray) -> float:
        arr = np.asarray(values, dtype=float)
        if len(arr) < 6:
            return 0.0
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
        mask_len = max(2, int(round(len(arr) * max(0.05, min(0.60, self.mask_fraction)))))
        start = max(1, (len(arr) - mask_len) // 2)
        end = min(len(arr) - 1, start + mask_len)
        if end <= start:
            return 0.0
        left = arr[start - 1]
        right = arr[end]
        predicted = np.linspace(left, right, end - start + 2)[1:-1]
        actual = arr[start:end]
        scale = float(np.nanstd(arr)) or max(abs(float(np.nanmean(arr))), 1.0)
        return float(np.mean(((actual - predicted) / max(scale, 1e-9)) ** 2))

    def _contrastive_diagnostics(
        self,
        samples: list[WindowSample],
        baseline_samples: list[WindowSample],
        centroid: list[float] | np.ndarray | None,
    ) -> dict[str, float | int | bool]:
        matrix = self._matrix(samples)
        if matrix.size == 0:
            return self._empty_contrastive()
        center = np.asarray(centroid, dtype=float) if centroid is not None else np.mean(matrix, axis=0)
        if len(center) != matrix.shape[1]:
            center = np.mean(matrix, axis=0)
        distances = np.linalg.norm(matrix - center, axis=1) / max(1.0, np.sqrt(matrix.shape[1]))
        cluster_distance = float(np.mean(distances))
        compactness = float(1.0 / (1.0 + cluster_distance))
        baseline_matrix = self._matrix([s for s in baseline_samples if len(s.vector) == matrix.shape[1]])
        baseline_distance = 0.0
        separation_margin = 0.0
        if baseline_matrix.size:
            baseline_distances = np.linalg.norm(baseline_matrix - center, axis=1) / max(
                1.0,
                np.sqrt(matrix.shape[1]),
            )
            baseline_distance = float(np.mean(baseline_distances))
            separation_margin = baseline_distance - cluster_distance
        separation_score = max(0.0, min(1.0, separation_margin / max(baseline_distance, 1e-9)))
        contrastive_score = compactness * 0.55 + separation_score * 0.45
        return {
            "sample_count": int(len(samples)),
            "embedding_dims": int(matrix.shape[1]),
            "centroid_distance_mean": round(cluster_distance, 5),
            "centroid_distance_p90": round(float(np.quantile(distances, 0.90)), 5),
            "baseline_distance_mean": round(baseline_distance, 5),
            "separation_margin": round(separation_margin, 5),
            "compactness_score": round(compactness, 5),
            "separation_score": round(separation_score, 5),
            "contrastive_score": round(float(max(0.0, min(1.0, contrastive_score))), 5),
            "family_embedding_coherent": bool(contrastive_score >= 0.45),
        }

    def _future_proxy_objectives(
        self,
        samples: list[WindowSample],
        side: Side,
        rr: float,
    ) -> dict[str, Any]:
        outcomes = np.asarray(
            [RewardRiskAnalyzer._simulate_sample(sample, side, rr)[0] for sample in samples],
            dtype=float,
        )
        if len(outcomes) < 3:
            return {
                "future_proxy_alignment_score": 0.0,
                "best_feature_alignment": [],
                "outcome_mean_r": round(float(np.mean(outcomes)), 5) if len(outcomes) else 0.0,
            }
        alignments: list[dict[str, float | str]] = []
        keys = sorted({key for sample in samples for key in sample.features})
        for key in keys:
            values = np.asarray([float(sample.features.get(key, 0.0)) for sample in samples], dtype=float)
            corr = self._corr(values, outcomes)
            if abs(corr) >= 0.08:
                alignments.append({"feature": key, "corr_to_future_r": round(float(corr), 5)})
        alignments = sorted(alignments, key=lambda row: abs(float(row["corr_to_future_r"])), reverse=True)[:8]
        vector_alignment = self._vector_future_alignment(samples, outcomes)
        feature_score = max((abs(float(row["corr_to_future_r"])) for row in alignments), default=0.0)
        score = max(feature_score, vector_alignment)
        return {
            "future_proxy_alignment_score": round(float(max(0.0, min(1.0, score))), 5),
            "best_feature_alignment": alignments,
            "vector_future_alignment_score": round(float(vector_alignment), 5),
            "outcome_mean_r": round(float(np.mean(outcomes)), 5),
            "objective_target": "future_r_proxy_not_used_for_fit",
        }

    def _vector_future_alignment(self, samples: list[WindowSample], outcomes: np.ndarray) -> float:
        matrix = self._matrix(samples)
        if matrix.size == 0 or len(outcomes) != matrix.shape[0]:
            return 0.0
        dims = min(matrix.shape[1], 64)
        if dims < self.min_vector_dims_for_corr:
            return 0.0
        correlations = [abs(self._corr(matrix[:, idx], outcomes)) for idx in range(dims)]
        return float(np.nanmax(correlations)) if correlations else 0.0

    @staticmethod
    def _chart_channels(sample: WindowSample) -> list[np.ndarray]:
        channels = []
        for key in ("close_norm", "volume_rel", "range_pct", "swing_state", "volume_price_pressure"):
            value = sample.chart.get(key) if isinstance(sample.chart, dict) else None
            if isinstance(value, list) and value:
                channels.append(np.asarray(value, dtype=float))
        return channels

    @staticmethod
    def _matrix(samples: list[WindowSample]) -> np.ndarray:
        if not samples:
            return np.empty((0, 0), dtype=float)
        lengths = [len(sample.vector) for sample in samples]
        if not lengths:
            return np.empty((0, 0), dtype=float)
        common = max(set(lengths), key=lengths.count)
        vectors = [np.asarray(sample.vector, dtype=float) for sample in samples if len(sample.vector) == common]
        if not vectors:
            return np.empty((0, 0), dtype=float)
        return np.nan_to_num(np.vstack(vectors), nan=0.0, posinf=0.0, neginf=0.0)

    @staticmethod
    def _corr(left: np.ndarray, right: np.ndarray) -> float:
        left = np.asarray(left, dtype=float)
        right = np.asarray(right, dtype=float)
        if len(left) != len(right) or len(left) < 3:
            return 0.0
        left_std = float(np.std(left))
        right_std = float(np.std(right))
        if left_std <= 1e-12 or right_std <= 1e-12:
            return 0.0
        return float(np.corrcoef(left, right)[0, 1])

    @staticmethod
    def _empty_contrastive() -> dict[str, float | int | bool]:
        return {
            "sample_count": 0,
            "embedding_dims": 0,
            "centroid_distance_mean": 0.0,
            "centroid_distance_p90": 0.0,
            "baseline_distance_mean": 0.0,
            "separation_margin": 0.0,
            "compactness_score": 0.0,
            "separation_score": 0.0,
            "contrastive_score": 0.0,
            "family_embedding_coherent": False,
        }

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "method": "deterministic_self_supervised_proxy_teacher",
            "masked_window_reconstruction_score": 0.0,
            "masked_window_error": 0.0,
            "masked_channel_count": 0,
            "contrastive_diagnostics": FoundationChartTeacher._empty_contrastive(),
            "future_proxy_objectives": {
                "future_proxy_alignment_score": 0.0,
                "best_feature_alignment": [],
                "outcome_mean_r": 0.0,
            },
            "pretraining_digest": {
                "teacher_version": "deterministic_proxy_v1",
                "embedding_quality_score": 0.0,
                "objectives": [],
                "use_for_reporting": False,
                "notes": "No samples available",
            },
        }
