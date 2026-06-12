"""False-match harness: the missing metric for matcher accuracy (audit §3.1.5).

For each discovered pattern, score a bank of known-negative windows with the
exact distance -> similarity mapping NovelPatternMatcher uses at match time and
publish FPR@recall90: the false-positive rate at the similarity threshold that
still accepts ``recall_target`` of the cluster's real members. Without this
number "the matcher improved" is opinion; with it, every matcher change
(temporal weighting, embedding v3, DTW) has an acceptance gate.

Negative sources, kept disjoint by the caller:
  - ``same_symbol_outside_cluster``: random windows of the cluster's own
    symbols that did not fall in the cluster (hardest negatives).
  - ``other_cluster_members``: members of other clusters with the same
    window_size (cross-pattern confusion).
  - ``shadow_occurrences``: lab near-misses, when available (optional; empty
    at research time).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class FalseMatchHarness:
    recall_target: float = 0.90
    max_negatives_per_source: int = 500
    min_positive_count: int = 10
    random_state: int = 42

    def evaluate(
        self,
        *,
        positives: np.ndarray,
        centroid: np.ndarray,
        negative_banks: dict[str, np.ndarray],
        tau_similarity: float | None = None,
        weights: np.ndarray | None = None,
    ) -> dict[str, object]:
        """Score positives and per-source negatives against one centroid.

        ``positives``/bank arrays are already in the pattern's scaled space
        (rows = windows). ``weights`` optionally applies the temporal ramp of
        ``PatternEmbeddingEngine.temporal_weights`` to the distance.
        """
        centroid = np.asarray(centroid, dtype=float)
        positives = np.asarray(positives, dtype=float)
        result: dict[str, object] = {
            "method": "fpr_at_recall_vs_negative_banks",
            "recall_target": round(float(self.recall_target), 4),
            "temporal_weighting_applied": weights is not None,
            "positive_count": int(positives.shape[0]) if positives.ndim == 2 else 0,
        }
        if positives.ndim != 2 or positives.shape[0] < self.min_positive_count:
            result["status"] = "insufficient_positives"
            result["fpr_at_recall"] = None
            return result

        positive_sims = self._similarities(positives, centroid, weights)
        # Highest similarity that still keeps recall_target of true members.
        threshold = float(np.quantile(positive_sims, 1.0 - self.recall_target))
        result["threshold_at_recall"] = round(threshold, 6)

        rng = np.random.default_rng(self.random_state)
        sources: dict[str, dict[str, object]] = {}
        pooled_hits = 0
        pooled_total = 0
        for name in sorted(negative_banks):
            bank = np.asarray(negative_banks[name], dtype=float)
            if bank.ndim != 2 or bank.shape[0] == 0:
                sources[name] = {"count": 0, "fpr_at_recall": None}
                continue
            if bank.shape[0] > self.max_negatives_per_source:
                idx = rng.choice(bank.shape[0], size=self.max_negatives_per_source, replace=False)
                bank = bank[np.sort(idx)]
            sims = self._similarities(bank, centroid, weights)
            hits = int(np.sum(sims >= threshold))
            entry: dict[str, object] = {
                "count": int(bank.shape[0]),
                "fpr_at_recall": round(hits / bank.shape[0], 6),
                "max_similarity": round(float(np.max(sims)), 6),
            }
            if tau_similarity is not None and math.isfinite(float(tau_similarity)):
                entry["fpr_at_tau"] = round(float(np.mean(sims >= float(tau_similarity))), 6)
            sources[name] = entry
            pooled_hits += hits
            pooled_total += int(bank.shape[0])

        result["sources"] = sources
        result["negative_count"] = pooled_total
        if pooled_total == 0:
            result["status"] = "no_negatives"
            result["fpr_at_recall"] = None
            return result
        result["status"] = "ok"
        result["fpr_at_recall"] = round(pooled_hits / pooled_total, 6)
        if tau_similarity is not None and math.isfinite(float(tau_similarity)):
            tau = float(tau_similarity)
            result["tau_similarity"] = round(tau, 6)
            result["recall_at_tau"] = round(float(np.mean(positive_sims >= tau)), 6)
        return result

    @staticmethod
    def _similarities(
        vectors: np.ndarray,
        centroid: np.ndarray,
        weights: np.ndarray | None = None,
    ) -> np.ndarray:
        """Same normalized-distance -> similarity mapping as NovelPatternMatcher.

        With unit weights the weighted form reduces exactly to the matcher's
        ``norm(diff) / sqrt(d)`` so unweighted harness numbers are directly
        comparable with live match similarities.
        """
        diff = vectors - centroid
        if weights is not None:
            w = np.asarray(weights, dtype=float)[: diff.shape[1]]
            diff = diff * w
            denom = max(1.0, math.sqrt(float(np.sum(w * w))))
        else:
            denom = max(1.0, math.sqrt(diff.shape[1]))
        distances = np.linalg.norm(diff, axis=1) / denom
        return 1.0 / (1.0 + distances)
