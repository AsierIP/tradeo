from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from itertools import combinations
import math
from typing import Iterable

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

import pandas as pd

from tradeo.research.adversarial_research import AdversarialResearchEngine
from tradeo.research.causal_invariance import CausalInvariantTester
from tradeo.research.false_match_harness import FalseMatchHarness
from tradeo.research.conformal_matching import split_conformal_similarity_threshold
from tradeo.research.foundation_teacher import FoundationChartTeacher
from tradeo.research.market_replay import MarketReplayEngine
from tradeo.research.quant_validation import (
    average_uniqueness_weights,
    newey_west_tstat,
    profit_factor as weighted_profit_factor,
    sample_skew_kurt,
    select_nonoverlapping_events,
    stationary_bootstrap_ci,
)
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.research.prototype_bank import build_prototype_bank
from tradeo.research.reward_risk_analyzer import RewardRiskAnalyzer
from tradeo.research.shape_verifier import (
    DEFAULT_SHAPE_CHANNELS,
    SHAPE_VERIFIER_METHOD,
    shape_distance,
    shape_matrix_from_chart,
)
from tradeo.research.types import ClusterCandidate, Side, WindowSample
from tradeo.services.market_regime import (
    INSUFFICIENT_HISTORY,
    regime_keys_for_dates,
)

try:  # scikit-learn >=1.3
    from sklearn.cluster import HDBSCAN
except Exception:  # noqa: BLE001
    HDBSCAN = None  # type: ignore[assignment]


def _json_safe_features(features: dict[str, object]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in features.items():
        try:
            number = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            output[key] = value
            continue
        if math.isfinite(number):
            output[key] = round(number, 6)
        else:
            output[key] = None
    return output


def _numeric_feature_values(samples: list[WindowSample], key: str) -> np.ndarray:
    values: list[float] = []
    for sample in samples:
        raw = sample.features.get(key, 0.0)
        try:
            number = float(raw)
        except (TypeError, ValueError):
            return np.asarray([], dtype=float)
        if not math.isfinite(number):
            return np.asarray([], dtype=float)
        values.append(number)
    return np.asarray(values, dtype=float)


def _numeric_feature_keys(samples: list[WindowSample]) -> list[str]:
    keys = sorted({key for sample in samples for key in sample.features})
    return [key for key in keys if len(_numeric_feature_values(samples, key)) == len(samples)]


@dataclass(slots=True)
class ClusterFitResult:
    method: str
    requested_method: str
    train_labels: np.ndarray
    all_labels: np.ndarray
    centroids: dict[int, np.ndarray]
    metadata: dict[str, object]


@dataclass(slots=True)
class ClusterResearchEngine:
    """Cluster unlabeled chart windows, then measure what happened next."""

    min_cluster_size: int = 60
    max_clusters_per_window: int = 12
    random_state: int = 42
    target_r: float = 4.0
    out_of_sample_pct: float = 0.25
    rr_levels: list[float] | None = None
    min_samples: int = 100
    event_ledger_limit: int = 250
    walk_forward_folds: int = 4
    walk_forward_embargo_samples: int = 5
    cost_stress_multipliers: list[float] | None = None
    required_cost_stress_multiplier: float = 2.0
    match_tau_percentile: float = 92.5
    # Diagnostic gamma for the temporal-weighting variant of the false-match
    # harness (audit §2.2.a); live matcher adoption is gated separately.
    match_temporal_gamma: float = 0.97
    clusterer_method: str = "auto"
    clusterer_min_samples: int | None = None
    density_holdout_radius_multiplier: float = 1.25
    consensus_repeats: int = 8
    consensus_subsample_pct: float = 0.80
    consensus_max_members: int = 120
    shape_dtw_points: int = 48
    shape_dtw_band_pct: float = 0.15
    shape_dtw_threshold_quantile: float = 0.90
    shape_dtw_method: str = "dtw"
    shape_soft_dtw_gamma: float = 0.05
    quant_bootstrap_draws: int = 500
    benchmark_regime_table: pd.DataFrame | None = None
    conformal_alpha: float = 0.10
    prototype_medoid_count: int = 16
    prototype_knn_k: int = 3

    def discover(self, samples: list[WindowSample]) -> list[ClusterCandidate]:
        candidates: list[ClusterCandidate] = []
        for window_size in sorted({sample.window_size for sample in samples}):
            window_samples = [sample for sample in samples if sample.window_size == window_size]
            candidates.extend(self._cluster_window_size(window_size, window_samples))
        self._apply_novelty_diversity(candidates)
        return sorted(candidates, key=lambda c: c.score, reverse=True)

    def _cluster_window_size(self, window_size: int, samples: list[WindowSample]) -> list[ClusterCandidate]:
        if len(samples) < max(self.min_cluster_size * 2, 20):
            return []
        ordered_samples = sorted(samples, key=lambda s: s.end)
        train_samples, holdout_samples = self._train_holdout_samples(ordered_samples)
        if len(train_samples) < max(self.min_cluster_size * 2, 20):
            return []
        matrix_train = np.vstack([s.vector for s in train_samples])
        matrix_all = np.vstack([s.vector for s in ordered_samples])
        scaler = StandardScaler()
        matrix_train_scaled = scaler.fit_transform(matrix_train)
        matrix_all_scaled = scaler.transform(matrix_all)
        target_clusters = min(self.max_clusters_per_window, max(2, len(train_samples) // self.min_cluster_size))
        fit = self._fit_clusters(
            matrix_train_scaled,
            matrix_all_scaled,
            target_clusters=target_clusters,
        )
        train_labels = fit.train_labels
        all_labels = fit.all_labels
        cluster_ids = sorted(label for label in set(train_labels.tolist()) if int(label) >= 0)
        if not cluster_ids:
            return []
        consensus_ensemble = self._cluster_consensus_ensemble(
            matrix_train_scaled,
            target_clusters=target_clusters,
            method=fit.method,
        )
        candidates: list[ClusterCandidate] = []
        embedding_contract = PatternEmbeddingEngine().contract()
        holdout_ids = {id(sample) for sample in holdout_samples}
        for cluster_id in cluster_ids:
            train_idxs = np.flatnonzero(train_labels == cluster_id)
            if len(train_idxs) < max(10, self.min_cluster_size // 2):
                continue
            all_idxs = np.flatnonzero(all_labels == cluster_id)
            cluster_samples = [ordered_samples[int(i)] for i in all_idxs]
            cluster_train_samples = [train_samples[int(i)] for i in train_idxs]
            cluster_holdout_samples = [sample for sample in cluster_samples if id(sample) in holdout_ids]
            cluster_vectors = matrix_all_scaled[all_idxs]
            centroid_scaled = fit.centroids[int(cluster_id)]
            rr_trial_count = len(self.rr_levels or [1.5, 2.0, 2.5, 3.0, 4.0, 5.0])
            tested_trials = len(cluster_ids) * 2 * rr_trial_count
            long_metrics = self._metrics_for_side(
                cluster_train_samples,
                cluster_samples,
                cluster_holdout_samples,
                train_samples,
                "long",
                multiple_testing_trials=tested_trials,
            )
            short_metrics = self._metrics_for_side(
                cluster_train_samples,
                cluster_samples,
                cluster_holdout_samples,
                train_samples,
                "short",
                multiple_testing_trials=tested_trials,
            )
            side: Side = "long" if self._side_score(long_metrics) >= self._side_score(short_metrics) else "short"
            metrics = long_metrics if side == "long" else short_metrics
            metrics["opposite_side"] = short_metrics if side == "long" else long_metrics
            metrics["cluster_density"] = round(float(len(all_idxs) / len(ordered_samples)), 5)
            metrics["train_cluster_density"] = round(float(len(train_idxs) / len(train_samples)), 5)
            metrics["window_size"] = window_size
            metrics["side"] = side
            metrics["target_r"] = self.target_r
            metrics["clusterer_method"] = fit.method
            metrics["clusterer"] = {
                **fit.metadata,
                "cluster_id": int(cluster_id),
                "cluster_sample_count": int(len(all_idxs)),
                "train_cluster_sample_count": int(len(train_idxs)),
            }
            metrics["density_noise"] = {
                "method": fit.method,
                "train_noise_count": int(np.sum(train_labels == -1)),
                "train_noise_rate": round(float(np.mean(train_labels == -1)), 6)
                if len(train_labels)
                else 0.0,
                "all_noise_count": int(np.sum(all_labels == -1)),
                "all_noise_rate": round(float(np.mean(all_labels == -1)), 6)
                if len(all_labels)
                else 0.0,
            }
            metrics["embedding_length"] = int(matrix_all.shape[1])
            metrics["feature_parity_contract"] = {
                **embedding_contract,
                "vector_length": int(matrix_all.shape[1]),
                "research_path": "WindowSampler -> PatternEmbeddingEngine.embed",
                "lab_path": "NovelPatternMatcher -> PatternEmbeddingEngine.embed",
            }
            metrics["scaler_mean"] = np.nan_to_num(scaler.mean_, nan=0, posinf=0, neginf=0).round(6).tolist()
            metrics["scaler_scale"] = np.nan_to_num(scaler.scale_, nan=1, posinf=1, neginf=1).round(6).tolist()
            metrics["validation_method"] = "train_fit_forward_holdout_walk_forward_embargo"
            metrics["selection_split"] = {
                "method": metrics["validation_method"],
                "train_start": train_samples[0].end if train_samples else None,
                "train_end": train_samples[-1].end if train_samples else None,
                "holdout_start": holdout_samples[0].end if holdout_samples else None,
                "holdout_end": holdout_samples[-1].end if holdout_samples else None,
                "train_sample_count": len(train_samples),
                "holdout_sample_count": len(holdout_samples),
                "out_of_sample_pct": self.out_of_sample_pct,
            }
            metrics["fit_scope"] = {
                "scaler": "train_only",
                "cluster_model": "train_only",
                "rr_selection": "train_only",
                "side_selection": "train_metrics_only",
                "null_baseline": "train_population_stratified_bootstrap",
                "lab_priority_score": "train_oos_walk_forward_only",
                "promotion_score": "train_oos_walk_forward_only",
                "descriptive_all_feeds_scores": False,
            }
            metrics["train_cutoff"] = train_samples[-1].end if train_samples else None
            metrics["holdout_start"] = holdout_samples[0].end if holdout_samples else None
            metrics["holdout_end"] = holdout_samples[-1].end if holdout_samples else None
            metrics["model_fit_sample_count"] = len(train_samples)
            metrics["model_holdout_sample_count"] = len(holdout_samples)
            metrics["real_variant_count"] = tested_trials
            metrics["real_variant_dimensions"] = {
                "clusters": len(cluster_ids),
                "sides": 2,
                "rr_levels": rr_trial_count,
            }
            walk_forward = self._walk_forward_metrics(cluster_samples, side)
            metrics["walk_forward_folds"] = walk_forward["folds"]
            metrics["walk_forward_fold_count"] = walk_forward["fold_count"]
            metrics["walk_forward_positive_fold_rate"] = walk_forward["positive_fold_rate"]
            metrics["walk_forward_avg_expectancy_r"] = walk_forward["avg_expectancy_r"]
            metrics["walk_forward_min_expectancy_r"] = walk_forward["min_expectancy_r"]
            metrics["walk_forward_pooled"] = walk_forward["pooled"]
            metrics["walk_forward_embargo_samples"] = self.walk_forward_embargo_samples
            metrics["walk_forward_metrics"] = {
                "folds": walk_forward["folds"],
                "fold_count": walk_forward["fold_count"],
                "positive_fold_rate": walk_forward["positive_fold_rate"],
                "avg_expectancy_r": walk_forward["avg_expectancy_r"],
                "min_expectancy_r": walk_forward["min_expectancy_r"],
                "pooled": walk_forward["pooled"],
                "embargo_samples": self.walk_forward_embargo_samples,
            }
            purged_cv = self._purged_combinatorial_cv(cluster_samples, side)
            metrics["purged_combinatorial_cv"] = purged_cv["folds"]
            metrics["purged_cv_fold_count"] = purged_cv["fold_count"]
            metrics["purged_cv_positive_rate"] = purged_cv["positive_rate"]
            metrics["purged_cv_avg_expectancy_r"] = purged_cv["avg_expectancy_r"]
            metrics["purged_cv_min_expectancy_r"] = purged_cv["min_expectancy_r"]
            metrics["purged_cv_p10_expectancy_r"] = purged_cv["p10_expectancy_r"]
            metrics["purged_cv_embargo_samples"] = self.walk_forward_embargo_samples
            metrics["overfit_score"] = self._overfit_score(metrics)
            metrics["cost_stress"] = self._cost_stress_metrics(
                cluster_samples,
                side,
                rr=float(metrics.get("best_rr", self.target_r)),
            )
            metrics["cost_stress_passed"] = self._cost_stress_passed(
                metrics["cost_stress"],
                required_multiplier=self.required_cost_stress_multiplier,
            )
            best_rr = float(metrics.get("best_rr", self.target_r))
            quant = self._quant_validation_metrics(cluster_train_samples, side=side, rr=best_rr)
            metrics["quant_validation"] = quant
            metrics["effective_sample_count"] = quant.get("n_eff", 0.0)
            metrics["unique_event_count"] = quant.get("n_unique", 0)
            metrics["match_tau_percentile"] = round(float(self.match_tau_percentile), 3)
            metrics["match_tau_similarity"] = self._match_tau_similarity(
                cluster_vectors, centroid_scaled
            )
            conformal = self._match_conformal_threshold(cluster_vectors, centroid_scaled)
            metrics["match_conformal"] = conformal
            if not conformal.get("blocked"):
                metrics["match_conformal_similarity_threshold"] = conformal["similarity_threshold"]
            prototype = self._prototype_match_contract(cluster_vectors, centroid_scaled)
            metrics.update(prototype)
            prototype_bank = build_prototype_bank(
                matrix_train_scaled[train_idxs],
                medoid_count=self.prototype_medoid_count,
                knn_k=self.prototype_knn_k,
                alpha=self.conformal_alpha,
                seed=self._prototype_bank_seed(window_size, int(cluster_id)),
            )
            if prototype_bank is not None:
                metrics["prototype_bank"] = prototype_bank
            metrics.update(self._shape_match_contract(cluster_train_samples))
            false_match = self._false_match_metrics(
                cluster_id=int(cluster_id),
                all_labels=all_labels,
                ordered_samples=ordered_samples,
                matrix_all_scaled=matrix_all_scaled,
                cluster_samples=cluster_samples,
                cluster_vectors=cluster_vectors,
                centroid_scaled=centroid_scaled,
                tau_similarity=float(metrics["match_tau_similarity"]),
            )
            metrics["false_match_harness"] = false_match["unweighted"]
            metrics["false_match_harness_temporal"] = false_match["temporal"]
            metrics["fpr_at_recall90"] = false_match["unweighted"].get("fpr_at_recall")
            metrics["match_tau_similarity_temporal"] = false_match["tau_similarity_temporal"]
            metrics["temporal_weighting"] = false_match["temporal_weighting"]
            signature = self._cluster_signature(cluster_samples, cluster_vectors, centroid_scaled, side)
            metrics["cluster_signature"] = signature
            metrics["medoid"] = signature["medoid"]
            metrics["concentration_checks"] = signature["concentration_checks"]
            consensus = self._coassignment_stability(train_idxs, consensus_ensemble)
            metrics["coassignment_consensus"] = consensus
            metrics["cluster_stability"] = {
                "method": "outcome_diversity_concentration_proxy+coassignment_consensus",
                "stability_score": metrics["stability_score"],
                "stability_year": metrics["stability_year"],
                "stability_symbol": metrics["stability_symbol"],
                "concentration_passed": signature["concentration_checks"]["passed"],
                "coassignment_consensus": consensus,
                "clusterer_method": fit.method,
                "noise_rate_train": metrics["density_noise"]["train_noise_rate"],
            }
            metrics["foundation_teacher"] = FoundationChartTeacher().analyze(
                cluster_samples,
                side=side,
                rr=best_rr,
                centroid=centroid_scaled,
                baseline_samples=train_samples,
            )
            metrics["market_replay"] = MarketReplayEngine().analyze(
                cluster_samples,
                side,
                best_rr,
            )
            metrics["causal_invariance"] = CausalInvariantTester().analyze(
                cluster_samples,
                side,
                best_rr,
            )
            metrics["adversarial_challenge"] = AdversarialResearchEngine().analyze(
                cluster_samples,
                baseline_samples=train_samples,
                side=side,
                rr=best_rr,
                metrics=metrics,
                causal_invariance=metrics["causal_invariance"],
                market_replay=metrics["market_replay"],
            )
            metrics["operational_trigger"] = self._operational_trigger_metrics(cluster_samples, side)
            metrics["event_ledger"] = self._event_ledger(
                cluster_samples,
                train_samples=cluster_train_samples,
                holdout_samples=cluster_holdout_samples,
                side=side,
                rr=best_rr,
            )
            metrics["event_ledger_count"] = len(metrics["event_ledger"])
            feature_summary = self._feature_summary(cluster_samples)
            regime_profile = self._regime_profile(cluster_samples)
            regime_profile["benchmark_regime_outcomes"] = self._benchmark_regime_outcomes(
                cluster_samples,
                side=side,
                rr=best_rr,
            )
            metrics["regime_profile"] = regime_profile
            metrics["human_rule"] = self._human_rule(
                cluster_samples,
                baseline_samples=train_samples,
                side=side,
                metrics=metrics,
            )
            score = self._candidate_score(metrics)
            metrics["lab_priority_score"] = round(float(score), 5)
            metrics["promotion_score"] = self._promotion_score(metrics)
            metrics["score_input_scope"] = {
                "lab_priority_score": [
                    "train_metrics",
                    "out_of_sample_metrics",
                    "walk_forward_metrics",
                    "purged_combinatorial_cv",
                    "bootstrap_reality_proxy",
                    "market_replay",
                    "adversarial_challenge",
                    "causal_invariance",
                    "foundation_teacher",
                ],
                "descriptive_all_fields_used": False,
            }
            metrics["nested_discovery_replay"] = {
                "status": "required_for_finalists",
                "implemented": False,
                "blocking_reason": (
                    "Full nested replay must refit scaler, clustering, side selection "
                    "and R:R selection inside each fold before any edge claim upgrade."
                ),
                "applies_before": ["production_gate", "edge_claim_upgrade"],
            }
            centroid = np.nan_to_num(centroid_scaled, nan=0, posinf=0, neginf=0).round(6).tolist()
            key = self._pattern_key(window_size, cluster_id, side, centroid)
            name = f"DISCOVERED_{side.upper()}_W{window_size}_C{cluster_id:02d}_{key[-8:].upper()}"
            examples = self._examples(cluster_samples, cluster_vectors, centroid_scaled, side)
            candidates.append(
                ClusterCandidate(
                    pattern_key=key,
                    name=name,
                    side=side,
                    timeframe=cluster_samples[0].timeframe if cluster_samples else "1d",
                    window_size=window_size,
                    cluster_id=int(cluster_id),
                    centroid=centroid,
                    sample_count=len(cluster_samples),
                    symbol_count=len({s.symbol for s in cluster_samples}),
                    year_count=len({s.year for s in cluster_samples}),
                    score=round(score, 5),
                    validation_passed=False,
                    validation_reasons=[],
                    metrics=metrics,
                    feature_summary=feature_summary,
                    examples=examples,
                )
            )
        return candidates

    def _metrics_for_side(
        self,
        train_samples: list[WindowSample],
        all_samples: list[WindowSample],
        holdout_samples: list[WindowSample],
        baseline_samples: list[WindowSample],
        side: Side,
        multiple_testing_trials: int,
    ) -> dict[str, object]:
        rr_levels = self.rr_levels or [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        rr_analysis = RewardRiskAnalyzer(
            rr_levels=rr_levels,
            min_samples=self.min_samples,
        ).analyze(train_samples, side)
        best_rr = float(rr_analysis.get("best_rr", self.target_r))
        rr_metrics = rr_analysis.get("rr_metrics", {})
        best_rr_metrics = rr_metrics.get(f"{best_rr:g}", {}) if isinstance(rr_metrics, dict) else {}
        outcomes = np.asarray(
            [RewardRiskAnalyzer._simulate_sample(s, side, best_rr)[0] for s in all_samples],
            dtype=float,
        )
        mfe = np.asarray([s.outcome.mfe_for(side) for s in all_samples], dtype=float)
        mae = np.asarray([s.outcome.mae_for(side) for s in all_samples], dtype=float)
        hits = np.asarray(
            [RewardRiskAnalyzer._simulate_sample(s, side, 4.0)[0] >= 4.0 for s in all_samples],
            dtype=bool,
        )
        train_outcomes = np.asarray(
            [RewardRiskAnalyzer._simulate_sample(s, side, best_rr)[0] for s in train_samples],
            dtype=float,
        )
        train_mfe = np.asarray([s.outcome.mfe_for(side) for s in train_samples], dtype=float)
        train_mae = np.asarray([s.outcome.mae_for(side) for s in train_samples], dtype=float)
        train_hits = np.asarray(
            [RewardRiskAnalyzer._simulate_sample(s, side, 4.0)[0] >= 4.0 for s in train_samples],
            dtype=bool,
        )
        wins = outcomes[outcomes > 0]
        losses = outcomes[outcomes < 0]
        profit_factor = float(wins.sum() / abs(losses.sum())) if len(losses) else float(wins.sum() or 0.0)
        by_year = self._group_expectancy(all_samples, outcomes, key="year")
        by_symbol = self._group_expectancy(all_samples, outcomes, key="symbol")
        train_by_year = self._group_expectancy(train_samples, train_outcomes, key="year")
        train_by_symbol = self._group_expectancy(train_samples, train_outcomes, key="symbol")
        oos = self._split_metrics(holdout_samples, side, best_rr)
        in_sample_metrics = self._split_metrics(train_samples, side, best_rr)
        null_baseline = self._null_baseline(
            baseline_samples,
            cluster_samples=train_samples,
            cluster_size=len(train_samples),
            side=side,
            rr=best_rr,
            observed_expectancy=float(in_sample_metrics["expectancy_r"]),
            multiple_testing_trials=multiple_testing_trials,
        )
        bootstrap = self._bootstrap_confidence(train_samples, side, best_rr)
        sharpe = self._sharpe_diagnostics(train_outcomes, multiple_testing_trials=multiple_testing_trials)
        edge_decay = self._edge_decay_metrics(rr_metrics, best_rr)
        stability_year = self._positive_group_fraction(train_by_year)
        stability_symbol = self._positive_group_fraction(train_by_symbol)
        diversity_score = min(1.0, len(train_by_symbol) / 20.0) * 0.55 + min(1.0, len(train_by_year) / 4.0) * 0.45
        stability_score = 0.40 * stability_year + 0.35 * stability_symbol + 0.25 * diversity_score
        avg_mae = float(np.mean(mae)) if len(mae) else 0.0
        avg_mfe = float(np.mean(mfe)) if len(mfe) else 0.0
        train_avg_mae = float(np.mean(train_mae)) if len(train_mae) else 0.0
        train_avg_mfe = float(np.mean(train_mfe)) if len(train_mfe) else 0.0
        return {
            "sample_count": len(all_samples),
            "train_sample_count": len(train_samples),
            "holdout_sample_count": len(holdout_samples),
            "symbol_count": len({s.symbol for s in all_samples}),
            "year_count": len({s.year for s in all_samples}),
            "descriptive_all_sample_count": len(all_samples),
            "descriptive_all_expectancy_r": round(float(np.mean(outcomes)), 5) if len(outcomes) else 0.0,
            "descriptive_all_median_r": round(float(np.median(outcomes)), 5) if len(outcomes) else 0.0,
            "descriptive_all_win_rate": round(float(np.mean(outcomes > 0)), 5) if len(outcomes) else 0.0,
            "descriptive_all_hit_4r_rate": round(float(np.mean(hits)), 5) if len(hits) else 0.0,
            "descriptive_all_profit_factor": round(profit_factor, 5),
            "descriptive_all_avg_mfe_r": round(avg_mfe, 5),
            "descriptive_all_avg_mae_r": round(avg_mae, 5),
            "expectancy_r": in_sample_metrics["expectancy_r"],
            "median_r": round(float(np.median(train_outcomes)), 5) if len(train_outcomes) else 0.0,
            "win_rate": in_sample_metrics["win_rate"],
            "hit_4r_rate": round(float(np.mean(train_hits)), 5) if len(train_hits) else 0.0,
            "profit_factor": in_sample_metrics["profit_factor"],
            "avg_mfe_r": round(train_avg_mfe, 5),
            "avg_mae_r": round(train_avg_mae, 5),
            "avg_execution_cost_r": float(best_rr_metrics.get("avg_execution_cost_r", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "avg_bars_to_target": float(best_rr_metrics.get("avg_bars_to_target", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "avg_bars_to_stop": float(best_rr_metrics.get("avg_bars_to_stop", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "triple_barrier_labels": best_rr_metrics.get("triple_barrier_labels", {})
            if isinstance(best_rr_metrics, dict)
            else {},
            "avg_gap_adverse_r": float(best_rr_metrics.get("avg_gap_adverse_r", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "mfe_before_mae_rate": float(best_rr_metrics.get("mfe_before_mae_rate", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "strong_close_without_target_rate": float(best_rr_metrics.get("strong_close_without_target_rate", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "speed_label_counts": best_rr_metrics.get("speed_label_counts", {})
            if isinstance(best_rr_metrics, dict)
            else {},
            "fast_target_rate": float(best_rr_metrics.get("fast_target_rate", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "slow_target_rate": float(best_rr_metrics.get("slow_target_rate", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "timeout_rate": float(best_rr_metrics.get("timeout_rate", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "avg_fill_probability": float(best_rr_metrics.get("avg_fill_probability", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "p25_max_size_usd": float(best_rr_metrics.get("p25_max_size_usd", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "median_max_size_usd": float(best_rr_metrics.get("median_max_size_usd", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "avg_spread_proxy_pct": float(best_rr_metrics.get("avg_spread_proxy_pct", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "avg_slippage_proxy_pct": float(best_rr_metrics.get("avg_slippage_proxy_pct", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "avg_entry_gap_penalty_pct": float(best_rr_metrics.get("avg_entry_gap_penalty_pct", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "avg_short_borrow_proxy_pct": float(best_rr_metrics.get("avg_short_borrow_proxy_pct", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "descriptive_all_mfe_mae_ratio": round(float(avg_mfe / max(avg_mae, 1e-9)), 5),
            "descriptive_all_reward_risk_estimate": round(
                float(np.quantile(mfe, 0.60) / max(np.quantile(mae, 0.60), 1e-9)),
                5,
            )
            if len(mfe) and len(mae)
            else 0.0,
            "mfe_mae_ratio": round(float(train_avg_mfe / max(train_avg_mae, 1e-9)), 5),
            "reward_risk_estimate": round(
                float(np.quantile(train_mfe, 0.60) / max(np.quantile(train_mae, 0.60), 1e-9)),
                5,
            )
            if len(train_mfe) and len(train_mae)
            else 0.0,
            "rr_levels": rr_levels,
            "rr_metrics": rr_metrics,
            "train_rr_metrics": rr_metrics,
            "rr_metrics_json": rr_metrics,
            "best_rr": round(float(best_rr), 5),
            "best_tested_rr": round(float(rr_analysis.get("best_tested_rr", best_rr)), 5),
            "best_expectancy_r": round(float(rr_analysis.get("best_expectancy_r", 0.0)), 5),
            "best_profit_factor": round(float(rr_analysis.get("best_profit_factor", 0.0)), 5),
            "best_win_rate": round(float(rr_analysis.get("best_win_rate", 0.0)), 5),
            "best_max_drawdown_r": round(float(rr_analysis.get("best_max_drawdown_r", 0.0)), 5),
            "best_edge_score": round(float(rr_analysis.get("best_score", 0.0)), 5),
            "target_hit_rate": float(best_rr_metrics.get("target_hit_rate", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "stop_hit_rate": float(best_rr_metrics.get("stop_hit_rate", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "max_drawdown_r": float(best_rr_metrics.get("max_drawdown_r", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "in_sample_expectancy_r": in_sample_metrics["expectancy_r"],
            "in_sample_profit_factor": in_sample_metrics["profit_factor"],
            "train_metrics": {
                "sample_count": in_sample_metrics["sample_count"],
                "expectancy_r": in_sample_metrics["expectancy_r"],
                "profit_factor": in_sample_metrics["profit_factor"],
                "win_rate": in_sample_metrics["win_rate"],
                "max_drawdown_r": in_sample_metrics["max_drawdown_r"],
                "best_rr": round(float(best_rr), 5),
                "best_expectancy_r": round(float(rr_analysis.get("best_expectancy_r", 0.0)), 5),
                "best_profit_factor": round(float(rr_analysis.get("best_profit_factor", 0.0)), 5),
                "best_win_rate": round(float(rr_analysis.get("best_win_rate", 0.0)), 5),
                "target_hit_rate": float(best_rr_metrics.get("target_hit_rate", 0.0))
                if isinstance(best_rr_metrics, dict)
                else 0.0,
                "stability_year": round(stability_year, 5),
                "stability_symbol": round(stability_symbol, 5),
                "stability_score": round(float(stability_score), 5),
            },
            "null_expectancy_r": null_baseline["expectancy_r"],
            "null_profit_factor": null_baseline["profit_factor"],
            "null_win_rate": null_baseline["win_rate"],
            "expectancy_lift_r": null_baseline["expectancy_lift_r"],
            "null_p_value": null_baseline["p_value"],
            "adjusted_p_value": null_baseline["adjusted_p_value"],
            "wrc_p_value": null_baseline["wrc_p_value"],
            "spa_p_value": null_baseline["spa_p_value"],
            "wrc_passed": null_baseline["wrc_passed"],
            "spa_passed": null_baseline["spa_passed"],
            "multiple_testing_penalty": null_baseline["multiple_testing_penalty"],
            "reality_check_method": null_baseline["reality_check_method"],
            "reality_check_formal_test": null_baseline["reality_check_formal_test"],
            "bootstrap_reality_proxy": {
                "method": null_baseline["reality_check_method"],
                "formal_test": null_baseline["reality_check_formal_test"],
                "wrc_like_p_value": null_baseline["wrc_p_value"],
                "spa_like_p_value": null_baseline["spa_p_value"],
                "wrc_like_passed": null_baseline["wrc_passed"],
                "spa_like_passed": null_baseline["spa_passed"],
                "draws": bootstrap["draws"],
                "trial_count": null_baseline["multiple_testing_trials"],
            },
            "multiple_testing_trials": null_baseline["multiple_testing_trials"],
            "statistical_edge_passed": null_baseline["statistical_edge_passed"],
            "null_method": null_baseline["method"],
            "null_strata_count": null_baseline["strata_count"],
            "expectancy_ci_low": bootstrap["expectancy_ci_low"],
            "expectancy_ci_high": bootstrap["expectancy_ci_high"],
            "profit_factor_ci_low": bootstrap["profit_factor_ci_low"],
            "bootstrap_draws": bootstrap["draws"],
            **sharpe,
            **edge_decay,
            "out_of_sample_expectancy_r": oos["expectancy_r"],
            "out_of_sample_profit_factor": oos["profit_factor"],
            "out_of_sample_win_rate": oos["win_rate"],
            "out_of_sample_max_drawdown_r": oos["max_drawdown_r"],
            "out_of_sample_sample_count": oos["sample_count"],
            "out_of_sample_metrics": {
                "sample_count": oos["sample_count"],
                "expectancy_r": oos["expectancy_r"],
                "profit_factor": oos["profit_factor"],
                "win_rate": oos["win_rate"],
                "max_drawdown_r": oos["max_drawdown_r"],
                "fit_scope": "holdout_only_no_refit",
            },
            "stability_year": round(stability_year, 5),
            "stability_symbol": round(stability_symbol, 5),
            "stability_score": round(float(stability_score), 5),
            "by_year_expectancy": train_by_year,
            "top_symbols_expectancy": dict(list(train_by_symbol.items())[:25]),
            "descriptive_all_by_year_expectancy": by_year,
            "descriptive_all_top_symbols_expectancy": dict(list(by_symbol.items())[:25]),
            "descriptive_metric_policy": {
                "prefix": "descriptive_all_",
                "feeds_lab_priority_score": False,
                "feeds_promotion_score": False,
                "feeds_best_pattern_selection": False,
            },
        }

    def _train_holdout_samples(self, samples: list[WindowSample]) -> tuple[list[WindowSample], list[WindowSample]]:
        if len(samples) < 8:
            return samples, []
        split = int(len(samples) * (1.0 - self.out_of_sample_pct))
        split = min(max(1, split), len(samples) - 1)
        return samples[:split], samples[split:]

    def _fit_clusters(
        self,
        matrix_train_scaled: np.ndarray,
        matrix_all_scaled: np.ndarray,
        *,
        target_clusters: int,
    ) -> ClusterFitResult:
        requested = str(self.clusterer_method or "auto").lower().strip()
        if requested in {"auto", "hdbscan", "density"}:
            density = self._fit_hdbscan_clusters(
                matrix_train_scaled,
                matrix_all_scaled,
                target_clusters=target_clusters,
                requested_method=requested,
            )
            if density is not None and density.centroids:
                return density
            fallback_reason = "hdbscan_unavailable_or_no_dense_clusters"
        else:
            fallback_reason = ""
        return self._fit_kmeans_clusters(
            matrix_train_scaled,
            matrix_all_scaled,
            target_clusters=target_clusters,
            requested_method=requested,
            fallback_reason=fallback_reason,
        )

    def _fit_hdbscan_clusters(
        self,
        matrix_train_scaled: np.ndarray,
        matrix_all_scaled: np.ndarray,
        *,
        target_clusters: int,
        requested_method: str,
    ) -> ClusterFitResult | None:
        if HDBSCAN is None:
            return None
        n_train = int(matrix_train_scaled.shape[0])
        if n_train < 5:
            return None
        min_cluster_size = max(5, min(int(self.min_cluster_size), max(2, n_train // 2)))
        configured_min_samples = int(self.clusterer_min_samples or 0)
        if configured_min_samples > 0:
            min_samples = max(1, min(configured_min_samples, min_cluster_size))
        else:
            min_samples = max(2, min(min_cluster_size, int(math.sqrt(n_train))))
        try:
            model = HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric="euclidean",
                copy=False,
            )
            train_labels = np.asarray(model.fit_predict(matrix_train_scaled), dtype=int)
        except Exception:  # noqa: BLE001
            return None
        centroids = self._centroids_from_labels(matrix_train_scaled, train_labels)
        if not centroids:
            return None
        all_labels = np.full(matrix_all_scaled.shape[0], -1, dtype=int)
        all_labels[:n_train] = train_labels
        if matrix_all_scaled.shape[0] > n_train:
            all_labels[n_train:] = self._assign_density_holdout_labels(
                matrix_all_scaled[n_train:],
                matrix_train_scaled,
                train_labels,
                centroids,
            )
        metadata = self._clusterer_metadata(
            method="hdbscan",
            requested_method=requested_method,
            target_clusters=target_clusters,
            train_labels=train_labels,
            all_labels=all_labels,
            extra={
                "hdbscan_available": True,
                "hdbscan_min_cluster_size": int(min_cluster_size),
                "hdbscan_min_samples": int(min_samples),
                "holdout_assignment": "nearest_train_centroid_with_member_radius",
                "holdout_radius_multiplier": round(float(self.density_holdout_radius_multiplier), 6),
            },
        )
        return ClusterFitResult(
            method="hdbscan",
            requested_method=requested_method,
            train_labels=train_labels,
            all_labels=all_labels,
            centroids=centroids,
            metadata=metadata,
        )

    def _fit_kmeans_clusters(
        self,
        matrix_train_scaled: np.ndarray,
        matrix_all_scaled: np.ndarray,
        *,
        target_clusters: int,
        requested_method: str,
        fallback_reason: str = "",
    ) -> ClusterFitResult:
        n_clusters = max(1, min(int(target_clusters), matrix_train_scaled.shape[0]))
        model = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=self.random_state,
            n_init=10,
            batch_size=min(2048, max(128, len(matrix_train_scaled))),
        )
        train_labels = np.asarray(model.fit_predict(matrix_train_scaled), dtype=int)
        all_labels = np.asarray(model.predict(matrix_all_scaled), dtype=int)
        centroids = {int(i): np.asarray(center, dtype=float) for i, center in enumerate(model.cluster_centers_)}
        extra: dict[str, object] = {"hdbscan_available": HDBSCAN is not None}
        if fallback_reason:
            extra["fallback_reason"] = fallback_reason
        metadata = self._clusterer_metadata(
            method="kmeans",
            requested_method=requested_method,
            target_clusters=target_clusters,
            train_labels=train_labels,
            all_labels=all_labels,
            extra=extra,
        )
        return ClusterFitResult(
            method="kmeans",
            requested_method=requested_method,
            train_labels=train_labels,
            all_labels=all_labels,
            centroids=centroids,
            metadata=metadata,
        )

    @staticmethod
    def _centroids_from_labels(matrix: np.ndarray, labels: np.ndarray) -> dict[int, np.ndarray]:
        centroids: dict[int, np.ndarray] = {}
        for label in sorted({int(value) for value in labels.tolist() if int(value) >= 0}):
            idxs = np.flatnonzero(labels == label)
            if len(idxs):
                centroids[int(label)] = np.mean(matrix[idxs], axis=0)
        return centroids

    def _assign_density_holdout_labels(
        self,
        holdout_scaled: np.ndarray,
        matrix_train_scaled: np.ndarray,
        train_labels: np.ndarray,
        centroids: dict[int, np.ndarray],
    ) -> np.ndarray:
        if holdout_scaled.size == 0 or not centroids:
            return np.empty((0,), dtype=int)
        dim = max(1.0, math.sqrt(float(matrix_train_scaled.shape[1])))
        radii: dict[int, float] = {}
        for label, centroid in centroids.items():
            members = matrix_train_scaled[train_labels == label]
            if members.size == 0:
                continue
            distances = np.linalg.norm(members - centroid, axis=1) / dim
            radius = float(np.quantile(distances, 0.90)) if len(distances) else 0.0
            radii[int(label)] = max(radius * float(self.density_holdout_radius_multiplier), 1e-9)
        labels = np.full(holdout_scaled.shape[0], -1, dtype=int)
        ordered_labels = sorted(centroids)
        centroid_matrix = np.vstack([centroids[label] for label in ordered_labels])
        for row_idx, vector in enumerate(holdout_scaled):
            distances = np.linalg.norm(centroid_matrix - vector, axis=1) / dim
            nearest_pos = int(np.argmin(distances))
            nearest_label = int(ordered_labels[nearest_pos])
            if float(distances[nearest_pos]) <= radii.get(nearest_label, 0.0):
                labels[row_idx] = nearest_label
        return labels

    @staticmethod
    def _clusterer_metadata(
        *,
        method: str,
        requested_method: str,
        target_clusters: int,
        train_labels: np.ndarray,
        all_labels: np.ndarray,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        cluster_labels = sorted({int(label) for label in train_labels.tolist() if int(label) >= 0})
        train_noise_count = int(np.sum(train_labels == -1))
        all_noise_count = int(np.sum(all_labels == -1))
        metadata: dict[str, object] = {
            "method": method,
            "requested_method": requested_method,
            "target_clusters": int(target_clusters),
            "cluster_count": int(len(cluster_labels)),
            "cluster_labels": cluster_labels,
            "noise_label": -1,
            "noise_count_train": train_noise_count,
            "noise_rate_train": round(float(train_noise_count / max(1, len(train_labels))), 6),
            "noise_count_all": all_noise_count,
            "noise_rate_all": round(float(all_noise_count / max(1, len(all_labels))), 6),
            "fit_scope": "train_only",
        }
        if extra:
            metadata.update(extra)
        return metadata

    def _cluster_consensus_ensemble(
        self,
        matrix_train_scaled: np.ndarray,
        *,
        target_clusters: int,
        method: str,
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        repeats = max(0, int(self.consensus_repeats))
        n_train = int(matrix_train_scaled.shape[0])
        if repeats == 0 or n_train < 4:
            return []
        size = int(math.ceil(n_train * float(self.consensus_subsample_pct)))
        size = min(n_train, max(2, size))
        ensemble: list[tuple[np.ndarray, np.ndarray]] = []
        for repeat in range(repeats):
            rng = np.random.default_rng(self.random_state + 7919 * (repeat + 1))
            subset = np.sort(rng.choice(n_train, size=size, replace=False))
            subset_matrix = matrix_train_scaled[subset]
            labels = self._consensus_labels(
                subset_matrix,
                target_clusters=target_clusters,
                method=method,
                seed=self.random_state + 1543 * (repeat + 1),
            )
            if labels is not None and len(labels) == len(subset):
                ensemble.append((subset, labels))
        return ensemble

    def _consensus_labels(
        self,
        matrix: np.ndarray,
        *,
        target_clusters: int,
        method: str,
        seed: int,
    ) -> np.ndarray | None:
        if method == "hdbscan" and HDBSCAN is not None and matrix.shape[0] >= 5:
            min_cluster_size = max(5, min(int(self.min_cluster_size), max(2, matrix.shape[0] // 2)))
            configured_min_samples = int(self.clusterer_min_samples or 0)
            min_samples = (
                max(1, min(configured_min_samples, min_cluster_size))
                if configured_min_samples > 0
                else max(2, min(min_cluster_size, int(math.sqrt(matrix.shape[0]))))
            )
            try:
                return np.asarray(
                    HDBSCAN(
                        min_cluster_size=min_cluster_size,
                        min_samples=min_samples,
                        metric="euclidean",
                        copy=False,
                    ).fit_predict(matrix),
                    dtype=int,
                )
            except Exception:  # noqa: BLE001
                return None
        n_clusters = max(1, min(int(target_clusters), matrix.shape[0]))
        try:
            return np.asarray(
                MiniBatchKMeans(
                    n_clusters=n_clusters,
                    random_state=seed,
                    n_init=5,
                    batch_size=min(2048, max(128, len(matrix))),
                ).fit_predict(matrix),
                dtype=int,
            )
        except Exception:  # noqa: BLE001
            return None

    def _coassignment_stability(
        self,
        train_idxs: np.ndarray,
        ensemble: list[tuple[np.ndarray, np.ndarray]],
    ) -> dict[str, object]:
        members = np.asarray(train_idxs, dtype=int)
        if len(members) > int(self.consensus_max_members):
            positions = np.linspace(0, len(members) - 1, int(self.consensus_max_members), dtype=int)
            members = members[positions]
        if len(members) < 2 or not ensemble:
            return {
                "method": "subsample_coassignment_consensus_v1",
                "status": "insufficient_pairs",
                "repeats": int(self.consensus_repeats),
                "subsample_pct": round(float(self.consensus_subsample_pct), 6),
                "member_count": int(len(train_idxs)),
                "members_evaluated": int(len(members)),
                "pair_observations": 0,
                "coassignment_rate": None,
                "stability_score": None,
                "mean_noise_vote_rate": None,
            }
        member_set = {int(idx) for idx in members.tolist()}
        pairs = [(int(a), int(b)) for a, b in combinations(members.tolist(), 2)]
        pair_observations = 0
        coassigned = 0
        noise_rates: list[float] = []
        for subset, labels in ensemble:
            positions = {int(idx): pos for pos, idx in enumerate(subset.tolist()) if int(idx) in member_set}
            present = [idx for idx in members.tolist() if int(idx) in positions]
            if present:
                present_labels = np.asarray([labels[positions[int(idx)]] for idx in present], dtype=int)
                noise_rates.append(float(np.mean(present_labels == -1)))
            for left, right in pairs:
                left_pos = positions.get(left)
                right_pos = positions.get(right)
                if left_pos is None or right_pos is None:
                    continue
                pair_observations += 1
                left_label = int(labels[left_pos])
                right_label = int(labels[right_pos])
                if left_label >= 0 and left_label == right_label:
                    coassigned += 1
        if pair_observations == 0:
            status = "insufficient_pairs"
            rate = None
        else:
            status = "ok"
            rate = coassigned / pair_observations
        return {
            "method": "subsample_coassignment_consensus_v1",
            "status": status,
            "repeats": int(self.consensus_repeats),
            "subsample_pct": round(float(self.consensus_subsample_pct), 6),
            "member_count": int(len(train_idxs)),
            "members_evaluated": int(len(members)),
            "pair_observations": int(pair_observations),
            "coassigned_pairs": int(coassigned),
            "coassignment_rate": round(float(rate), 6) if rate is not None else None,
            "stability_score": round(float(rate), 6) if rate is not None else None,
            "mean_noise_vote_rate": round(float(np.mean(noise_rates)), 6) if noise_rates else None,
        }

    def _shape_match_contract(self, cluster_train_samples: list[WindowSample]) -> dict[str, object]:
        channels = list(DEFAULT_SHAPE_CHANNELS)
        length = max(4, int(self.shape_dtw_points))
        band = max(1, int(math.ceil(length * float(self.shape_dtw_band_pct))))
        matrices: list[np.ndarray] = []
        for sample in cluster_train_samples:
            matrix = shape_matrix_from_chart(sample.chart, channels=channels, length=length)
            if matrix is not None:
                matrices.append(matrix)
        base: dict[str, object] = {
            "method": SHAPE_VERIFIER_METHOD,
            "channels": channels,
            "points_per_channel": int(length),
            "distance": str(self.shape_dtw_method).lower().replace("-", "_"),
            "band": int(band),
            "band_pct": round(float(self.shape_dtw_band_pct), 6),
            "threshold_quantile": round(float(self.shape_dtw_threshold_quantile), 6),
            "fit_scope": "train_cluster_members_only",
            "enabled_in_matcher_default": False,
            "member_count": int(len(matrices)),
        }
        if len(matrices) < 3:
            return {
                "shape_verifier": {
                    **base,
                    "status": "insufficient_shape_snippets",
                    "distance_threshold": None,
                    "prototype": {},
                }
            }
        stacked = np.stack(matrices)
        prototype = np.median(stacked, axis=0)
        distances = np.asarray(
            [
                shape_distance(
                    matrix,
                    prototype,
                    method=str(self.shape_dtw_method),
                    band=band,
                    gamma=float(self.shape_soft_dtw_gamma),
                )
                for matrix in matrices
            ],
            dtype=float,
        )
        finite = distances[np.isfinite(distances)]
        if finite.size == 0:
            return {
                "shape_verifier": {
                    **base,
                    "status": "invalid_member_distances",
                    "distance_threshold": None,
                    "prototype": {},
                }
            }
        quantile = min(1.0, max(0.0, float(self.shape_dtw_threshold_quantile)))
        threshold = float(np.quantile(finite, quantile))
        return {
            "shape_verifier": {
                **base,
                "status": "ok",
                "distance_threshold": round(threshold, 6),
                "member_distance_p50": round(float(np.quantile(finite, 0.50)), 6),
                "member_distance_p90": round(float(np.quantile(finite, 0.90)), 6),
                "member_distance_max": round(float(np.max(finite)), 6),
                "soft_dtw_gamma": round(float(self.shape_soft_dtw_gamma), 6),
                "prototype": {
                    channel: np.round(prototype[idx], 6).tolist()
                    for idx, channel in enumerate(channels)
                },
            }
        }

    def _null_baseline(
        self,
        samples: list[WindowSample],
        *,
        cluster_samples: list[WindowSample],
        cluster_size: int,
        side: Side,
        rr: float,
        observed_expectancy: float,
        multiple_testing_trials: int,
    ) -> dict[str, object]:
        outcomes = np.asarray([RewardRiskAnalyzer._simulate_sample(s, side, rr)[0] for s in samples], dtype=float)
        if len(outcomes) == 0 or cluster_size <= 0:
            return {
                "expectancy_r": 0.0,
                "profit_factor": 0.0,
                "win_rate": 0.0,
                "expectancy_lift_r": observed_expectancy,
                "p_value": 1.0,
                "adjusted_p_value": 1.0,
                "wrc_p_value": 1.0,
                "spa_p_value": 1.0,
                "wrc_passed": False,
                "spa_passed": False,
                "multiple_testing_penalty": 1.0,
                "multiple_testing_trials": max(1, int(multiple_testing_trials)),
                "statistical_edge_passed": False,
                "method": "stratified_regime_bootstrap",
                "reality_check_method": "bootstrap_reality_proxy",
                "reality_check_formal_test": False,
                "strata_count": 0,
            }

        baseline = self._outcome_metrics(outcomes)
        draws = min(512, max(96, len(outcomes) * 2))
        seed = self._null_seed(side, rr, cluster_size, len(outcomes))
        rng = np.random.default_rng(seed)
        stratified_groups = self._baseline_groups(samples)
        cluster_strata = self._cluster_strata(cluster_samples)
        draw_size = min(cluster_size, len(outcomes))
        random_means = []
        for _ in range(draws):
            draw = self._stratified_draw(
                rng,
                outcomes=outcomes,
                groups=stratified_groups,
                cluster_strata=cluster_strata,
                fallback_size=draw_size,
            )
            random_means.append(float(np.mean(draw)))
        p_value = (1 + sum(1 for mean in random_means if mean >= observed_expectancy)) / (draws + 1)
        trial_count = max(1, int(multiple_testing_trials))
        adjusted_p = min(1.0, p_value * trial_count)
        wrc_p = min(1.0, 1.0 - (1.0 - p_value) ** trial_count)
        spa_p = min(1.0, p_value * math.sqrt(trial_count))
        multiple_testing_penalty = min(1.0, math.sqrt(math.log1p(trial_count)) / 4.0)
        null_expectancy = float(np.mean(random_means)) if random_means else float(baseline["expectancy_r"])
        expectancy_lift = observed_expectancy - null_expectancy
        return {
            "expectancy_r": round(null_expectancy, 5),
            "profit_factor": baseline["profit_factor"],
            "win_rate": baseline["win_rate"],
            "expectancy_lift_r": round(expectancy_lift, 5),
            "p_value": round(float(p_value), 5),
            "adjusted_p_value": round(float(adjusted_p), 5),
            "wrc_p_value": round(float(wrc_p), 5),
            "spa_p_value": round(float(spa_p), 5),
            "wrc_passed": wrc_p <= 0.25 and expectancy_lift > 0,
            "spa_passed": spa_p <= 0.25 and expectancy_lift > 0,
            "multiple_testing_penalty": round(float(multiple_testing_penalty), 5),
            "multiple_testing_trials": trial_count,
            "statistical_edge_passed": adjusted_p <= 0.25 and expectancy_lift > 0,
            "method": "stratified_regime_bootstrap",
            "reality_check_method": "bootstrap_reality_proxy",
            "reality_check_formal_test": False,
            "strata_count": len(cluster_strata),
        }

    def _baseline_groups(self, samples: list[WindowSample]) -> dict[tuple[object, ...], list[int]]:
        groups: dict[tuple[object, ...], list[int]] = {}
        for idx, sample in enumerate(samples):
            groups.setdefault(self._stratum(sample), []).append(idx)
        return groups

    def _cluster_strata(self, samples: list[WindowSample]) -> dict[tuple[object, ...], int]:
        strata: dict[tuple[object, ...], int] = {}
        for sample in samples:
            key = self._stratum(sample)
            strata[key] = strata.get(key, 0) + 1
        return strata

    def _stratified_draw(
        self,
        rng: np.random.Generator,
        *,
        outcomes: np.ndarray,
        groups: dict[tuple[object, ...], list[int]],
        cluster_strata: dict[tuple[object, ...], int],
        fallback_size: int,
    ) -> np.ndarray:
        selected: list[float] = []
        all_indices = np.arange(len(outcomes))
        for stratum, count in cluster_strata.items():
            group = groups.get(stratum)
            if not group:
                continue
            size = min(count, len(group))
            idxs = rng.choice(np.asarray(group), size=size, replace=False)
            selected.extend(float(outcomes[int(idx)]) for idx in idxs)
        missing = max(0, fallback_size - len(selected))
        if missing:
            idxs = rng.choice(all_indices, size=min(missing, len(outcomes)), replace=False)
            selected.extend(float(outcomes[int(idx)]) for idx in idxs)
        if not selected:
            idxs = rng.choice(all_indices, size=min(fallback_size, len(outcomes)), replace=False)
            selected.extend(float(outcomes[int(idx)]) for idx in idxs)
        return np.asarray(selected, dtype=float)

    @staticmethod
    def _stratum(sample: WindowSample) -> tuple[object, ...]:
        volatility = float(sample.features.get("volatility_regime", 1.0))
        trend = float(sample.features.get("trend_regime", 0.0))
        market = float(sample.features.get("market_regime_score", 0.0))
        breadth = float(sample.features.get("market_breadth_proxy", 0.5))
        sector = float(sample.features.get("sector_strength", 0.0))
        liquidity = float(sample.features.get("liquidity_score", 0.0))
        if volatility < 0.8:
            vol_bucket = "low_vol"
        elif volatility > 1.25:
            vol_bucket = "high_vol"
        else:
            vol_bucket = "normal_vol"
        if trend > 0.25:
            trend_bucket = "up"
        elif trend < -0.25:
            trend_bucket = "down"
        else:
            trend_bucket = "mixed"
        if market > 0.25:
            market_bucket = "market_up"
        elif market < -0.25:
            market_bucket = "market_down"
        else:
            market_bucket = "market_mixed"
        if breadth >= 0.67:
            breadth_bucket = "broad"
        elif breadth <= 0.33:
            breadth_bucket = "narrow"
        else:
            breadth_bucket = "neutral_breadth"
        if sector > 0.03:
            sector_bucket = "sector_strong"
        elif sector < -0.03:
            sector_bucket = "sector_weak"
        else:
            sector_bucket = "sector_neutral"
        liquidity_bucket = "liquid" if liquidity >= 0.55 else "thin"
        return (
            sample.year,
            vol_bucket,
            trend_bucket,
            market_bucket,
            breadth_bucket,
            sector_bucket,
            liquidity_bucket,
        )

    def _bootstrap_confidence(self, samples: list[WindowSample], side: Side, rr: float) -> dict[str, float | int]:
        outcomes = np.asarray(
            [RewardRiskAnalyzer._simulate_sample(sample, side, rr)[0] for sample in samples],
            dtype=float,
        )
        if len(outcomes) == 0:
            return {"expectancy_ci_low": 0.0, "expectancy_ci_high": 0.0, "profit_factor_ci_low": 0.0, "draws": 0}
        draws = min(512, max(128, len(outcomes) * 3))
        rng = np.random.default_rng(self._null_seed(side, rr, len(samples), len(outcomes)) ^ 0xA5A5A5A5)
        expectancies: list[float] = []
        profit_factors: list[float] = []
        for _ in range(draws):
            idxs = rng.choice(len(outcomes), size=len(outcomes), replace=True)
            metrics = self._outcome_metrics(outcomes[idxs])
            expectancies.append(float(metrics["expectancy_r"]))
            profit_factors.append(float(metrics["profit_factor"]))
        return {
            "expectancy_ci_low": round(float(np.quantile(expectancies, 0.05)), 5),
            "expectancy_ci_high": round(float(np.quantile(expectancies, 0.95)), 5),
            "profit_factor_ci_low": round(float(np.quantile(profit_factors, 0.05)), 5),
            "draws": draws,
        }

    @staticmethod
    def _sharpe_diagnostics(outcomes: np.ndarray, *, multiple_testing_trials: int) -> dict[str, float]:
        outcomes = np.asarray(outcomes, dtype=float)
        if len(outcomes) < 3:
            return {
                "trade_sharpe": 0.0,
                "probabilistic_sharpe": 0.0,
                "deflated_sharpe": 0.0,
                "deflated_sharpe_probability": 0.0,
            }
        mean = float(np.mean(outcomes))
        std = float(np.std(outcomes, ddof=1))
        if std <= 1e-12:
            sharpe = 0.0 if mean <= 0 else 10.0
        else:
            sharpe = mean / std
        centered = outcomes - mean
        skew = float(np.mean(centered**3) / max(float(np.std(outcomes) ** 3), 1e-12))
        kurt = float(np.mean(centered**4) / max(float(np.std(outcomes) ** 4), 1e-12))
        denominator = math.sqrt(max(1e-9, 1.0 - skew * sharpe + ((kurt - 1.0) / 4.0) * sharpe * sharpe))
        psr_z = sharpe * math.sqrt(max(len(outcomes) - 1, 1)) / denominator
        trial_haircut = math.sqrt(2.0 * math.log(max(2, int(multiple_testing_trials)))) / math.sqrt(len(outcomes))
        deflated = sharpe - trial_haircut
        deflated_z = deflated * math.sqrt(max(len(outcomes) - 1, 1)) / denominator
        return {
            "trade_sharpe": round(float(sharpe), 5),
            "probabilistic_sharpe": round(ClusterResearchEngine._normal_cdf(psr_z), 5),
            "deflated_sharpe": round(float(deflated), 5),
            "deflated_sharpe_probability": round(ClusterResearchEngine._normal_cdf(deflated_z), 5),
        }

    @staticmethod
    def _edge_decay_metrics(rr_metrics: object, best_rr: float) -> dict[str, float | bool | list[dict[str, float]]]:
        if not isinstance(rr_metrics, dict) or not rr_metrics:
            return {
                "edge_decay_parameter_score": 1.0,
                "edge_decay_passed": False,
                "edge_decay_neighbors": [],
            }
        levels: list[tuple[float, float]] = []
        for key, metrics in rr_metrics.items():
            if not isinstance(metrics, dict):
                continue
            try:
                level = float(key)
            except (TypeError, ValueError):
                continue
            levels.append((level, float(metrics.get("expectancy_r", 0.0))))
        levels = sorted(levels)
        if not levels:
            return {
                "edge_decay_parameter_score": 1.0,
                "edge_decay_passed": False,
                "edge_decay_neighbors": [],
            }
        best_expectancy = next(
            (expectancy for level, expectancy in levels if abs(level - best_rr) < 1e-9),
            levels[0][1],
        )
        neighbors = sorted(
            [(level, expectancy) for level, expectancy in levels if abs(level - best_rr) >= 1e-9],
            key=lambda item: abs(item[0] - best_rr),
        )[:2]
        decays = [
            max(0.0, best_expectancy - expectancy) / max(abs(best_expectancy), 0.25)
            for _, expectancy in neighbors
        ]
        score = float(np.mean(decays)) if decays else 0.0
        return {
            "edge_decay_parameter_score": round(float(min(score, 1.0)), 5),
            "edge_decay_passed": bool(score <= 0.55 or best_expectancy <= 0.0),
            "edge_decay_neighbors": [
                {
                    "rr": round(float(level), 5),
                    "expectancy_r": round(float(expectancy), 5),
                    "decay_from_best": round(
                        float(max(0.0, best_expectancy - expectancy) / max(abs(best_expectancy), 0.25)),
                        5,
                    ),
                }
                for level, expectancy in neighbors
            ],
        }

    @staticmethod
    def _normal_cdf(value: float) -> float:
        return float(0.5 * (1.0 + math.erf(value / math.sqrt(2.0))))

    @staticmethod
    def _overfit_score(metrics: dict[str, object]) -> float:
        fold_count = int(metrics.get("walk_forward_fold_count", 0))
        if fold_count == 0:
            base = 0.5
        else:
            train_expectancy = float(metrics.get("in_sample_expectancy_r", metrics.get("expectancy_r", 0.0)))
            walk_forward_expectancy = float(metrics.get("walk_forward_avg_expectancy_r", 0.0))
            positive_rate = float(metrics.get("walk_forward_positive_fold_rate", 0.0))
            generalization_gap = max(0.0, train_expectancy - walk_forward_expectancy) / max(abs(train_expectancy), 0.25)
            base = (1.0 - positive_rate) * 0.55 + min(generalization_gap, 1.0) * 0.45
        purged_count = int(metrics.get("purged_cv_fold_count", 0))
        purged_penalty = 0.0
        if purged_count:
            purged_penalty = max(0.0, 0.50 - float(metrics.get("purged_cv_positive_rate", 0.0)))
        sharpe_penalty = max(0.0, 0.55 - float(metrics.get("deflated_sharpe_probability", 0.55))) * 0.5
        decay_penalty = float(metrics.get("edge_decay_parameter_score", 0.0)) * 0.25
        score = base * 0.70 + purged_penalty * 0.15 + sharpe_penalty * 0.10 + decay_penalty * 0.05
        return round(float(min(max(score, 0.0), 1.0)), 5)

    def _null_seed(self, side: Side, rr: float, cluster_size: int, population_size: int) -> int:
        digest = blake2b(digest_size=4)
        digest.update(
            f"{self.random_state}|{side}|{rr:g}|cluster={cluster_size}|population={population_size}".encode()
        )
        return int.from_bytes(digest.digest(), "big", signed=False)

    @staticmethod
    def _outcome_metrics(outcomes: np.ndarray) -> dict[str, float]:
        if len(outcomes) == 0:
            return {"expectancy_r": 0.0, "profit_factor": 0.0, "win_rate": 0.0}
        wins = outcomes[outcomes > 0]
        losses = outcomes[outcomes < 0]
        profit_factor = float(wins.sum() / abs(losses.sum())) if len(losses) else float(wins.sum() or 0.0)
        return {
            "expectancy_r": round(float(np.mean(outcomes)), 5),
            "profit_factor": round(profit_factor, 5),
            "win_rate": round(float(np.mean(outcomes > 0)), 5),
        }

    def _walk_forward_metrics(self, samples: list[WindowSample], side: Side) -> dict[str, object]:
        ordered = sorted(samples, key=lambda s: s.end)
        if len(ordered) < 12 or self.walk_forward_folds <= 0:
            return self._empty_walk_forward()

        embargo = max(0, int(self.walk_forward_embargo_samples))
        min_train = max(6, min(len(ordered) // 2, self.min_samples))
        if min_train + embargo + 3 >= len(ordered):
            min_train = max(6, len(ordered) // 2)
        remaining = len(ordered) - min_train - embargo
        if remaining < 3:
            return self._empty_walk_forward()

        fold_count = min(max(1, self.walk_forward_folds), remaining)
        validation_size = max(3, remaining // fold_count)
        folds: list[dict[str, object]] = []
        validation_samples_all: list[WindowSample] = []
        for fold_idx in range(fold_count):
            train_end = min_train + fold_idx * validation_size
            validation_start = train_end + embargo
            validation_end = min(len(ordered), validation_start + validation_size)
            train = ordered[:train_end]
            validation = ordered[validation_start:validation_end]
            if len(train) < 6 or len(validation) < 3:
                continue
            rr_analysis = RewardRiskAnalyzer(
                rr_levels=self.rr_levels or [1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
                min_samples=self.min_samples,
            ).analyze(train, side)
            rr = float(rr_analysis.get("best_rr", self.target_r))
            train_metrics = self._split_metrics(train, side, rr)
            validation_metrics = self._split_metrics(validation, side, rr)
            validation_samples_all.extend(validation)
            folds.append(
                {
                    "fold": len(folds) + 1,
                    "train_start": train[0].end,
                    "train_end": train[-1].end,
                    "validation_start": validation[0].end,
                    "validation_end": validation[-1].end,
                    "embargo_samples": embargo,
                    "train_sample_count": len(train),
                    "validation_sample_count": len(validation),
                    "best_rr": round(rr, 5),
                    "train_expectancy_r": train_metrics["expectancy_r"],
                    "train_profit_factor": train_metrics["profit_factor"],
                    "validation_expectancy_r": validation_metrics["expectancy_r"],
                    "validation_profit_factor": validation_metrics["profit_factor"],
                    "validation_win_rate": validation_metrics["win_rate"],
                    "validation_max_drawdown_r": validation_metrics["max_drawdown_r"],
                }
            )

        if not folds:
            return self._empty_walk_forward()
        validation_expectancies = [float(fold["validation_expectancy_r"]) for fold in folds]
        pooled_rr = float(folds[-1]["best_rr"])
        pooled = self._split_metrics(validation_samples_all, side, pooled_rr)
        return {
            "folds": folds,
            "fold_count": len(folds),
            "positive_fold_rate": round(float(np.mean(np.asarray(validation_expectancies) > 0)), 5),
            "avg_expectancy_r": round(float(np.mean(validation_expectancies)), 5),
            "min_expectancy_r": round(float(np.min(validation_expectancies)), 5),
            "pooled": pooled,
        }

    def _purged_combinatorial_cv(self, samples: list[WindowSample], side: Side) -> dict[str, object]:
        ordered = sorted(samples, key=lambda s: s.end)
        fold_target = min(max(3, self.walk_forward_folds), 6)
        if len(ordered) < fold_target * 4:
            return self._empty_purged_cv()
        folds = [list(chunk) for chunk in np.array_split(np.arange(len(ordered)), fold_target) if len(chunk)]
        validation_combos: list[tuple[int, ...]] = [(idx,) for idx in range(len(folds))]
        if len(folds) <= 5:
            validation_combos.extend(combinations(range(len(folds)), 2))
        embargo = max(0, int(self.walk_forward_embargo_samples))
        rr_levels = self.rr_levels or [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
        cv_folds: list[dict[str, object]] = []
        for combo in validation_combos[:18]:
            validation_indices = sorted(int(i) for fold_idx in combo for i in folds[fold_idx])
            purged = set(validation_indices)
            for idx in validation_indices:
                for purge_idx in range(max(0, idx - embargo), min(len(ordered), idx + embargo + 1)):
                    purged.add(purge_idx)
            train = [sample for idx, sample in enumerate(ordered) if idx not in purged]
            validation = [ordered[idx] for idx in validation_indices]
            if len(train) < max(6, self.min_samples // 2) or len(validation) < 3:
                continue
            rr_analysis = RewardRiskAnalyzer(rr_levels=rr_levels, min_samples=self.min_samples).analyze(train, side)
            rr = float(rr_analysis.get("best_rr", self.target_r))
            train_metrics = self._split_metrics(train, side, rr)
            validation_metrics = self._split_metrics(validation, side, rr)
            cv_folds.append(
                {
                    "fold": len(cv_folds) + 1,
                    "validation_fold_ids": list(combo),
                    "train_sample_count": len(train),
                    "validation_sample_count": len(validation),
                    "purged_sample_count": len(purged) - len(validation_indices),
                    "embargo_samples": embargo,
                    "best_rr": round(rr, 5),
                    "train_expectancy_r": train_metrics["expectancy_r"],
                    "validation_expectancy_r": validation_metrics["expectancy_r"],
                    "validation_profit_factor": validation_metrics["profit_factor"],
                    "validation_win_rate": validation_metrics["win_rate"],
                }
            )
        if not cv_folds:
            return self._empty_purged_cv()
        expectancies = np.asarray([float(fold["validation_expectancy_r"]) for fold in cv_folds], dtype=float)
        return {
            "folds": cv_folds,
            "fold_count": len(cv_folds),
            "positive_rate": round(float(np.mean(expectancies > 0)), 5),
            "avg_expectancy_r": round(float(np.mean(expectancies)), 5),
            "min_expectancy_r": round(float(np.min(expectancies)), 5),
            "p10_expectancy_r": round(float(np.quantile(expectancies, 0.10)), 5),
        }

    @staticmethod
    def _empty_purged_cv() -> dict[str, object]:
        return {
            "folds": [],
            "fold_count": 0,
            "positive_rate": 0.0,
            "avg_expectancy_r": 0.0,
            "min_expectancy_r": 0.0,
            "p10_expectancy_r": 0.0,
        }

    @staticmethod
    def _empty_walk_forward() -> dict[str, object]:
        return {
            "folds": [],
            "fold_count": 0,
            "positive_fold_rate": 0.0,
            "avg_expectancy_r": 0.0,
            "min_expectancy_r": 0.0,
            "pooled": {
                "sample_count": 0,
                "expectancy_r": 0.0,
                "profit_factor": 0.0,
                "win_rate": 0.0,
                "max_drawdown_r": 0.0,
            },
        }

    def _operational_trigger_metrics(self, samples: list[WindowSample], side: Side) -> dict[str, float | int]:
        key = f"{side}_entry_trigger_score"
        scores = np.asarray([float(sample.features.get(key, 0.0)) for sample in samples], dtype=float)
        if len(scores) == 0:
            return {"sample_count": 0, "avg_score": 0.0, "trigger_rate": 0.0}
        return {
            "sample_count": int(len(scores)),
            "avg_score": round(float(np.mean(scores)), 5),
            "trigger_rate": round(float(np.mean(scores >= 0.58)), 5),
        }

    def _event_ledger(
        self,
        samples: list[WindowSample],
        *,
        train_samples: list[WindowSample],
        holdout_samples: list[WindowSample],
        side: Side,
        rr: float,
    ) -> list[dict[str, object]]:
        train_ids = {id(sample) for sample in train_samples}
        holdout_ids = {id(sample) for sample in holdout_samples}
        ledger: list[dict[str, object]] = []
        ordered_samples = sorted(samples, key=lambda s: s.end)
        if self.event_ledger_limit > 0:
            ordered_samples = ordered_samples[: self.event_ledger_limit]
        for sample in ordered_samples:
            result_r, target_bar, stop_bar = RewardRiskAnalyzer._simulate_sample(sample, side, rr)
            if id(sample) in train_ids:
                split = "train"
            elif id(sample) in holdout_ids:
                split = "holdout"
            else:
                split = "assigned"
            ledger.append(
                {
                    "symbol": sample.symbol,
                    "window_end": sample.end,
                    "forward_end": sample.outcome.forward_end,
                    "year": sample.year,
                    "split": split,
                    "side": side,
                    "rr": round(float(rr), 5),
                    "result_r": round(float(result_r), 5),
                    "triple_barrier_label": self._triple_barrier_label(target_bar, stop_bar),
                    "target_bar": target_bar,
                    "stop_bar": stop_bar,
                    "sample_label": sample.outcome.label_for(side),
                    "sample_speed_label": sample.outcome.speed_label_for(side),
                    "sample_time_to_target": sample.outcome.time_to_target_for(side),
                    "sample_time_to_stop": sample.outcome.time_to_stop_for(side),
                    "gap_adverse_r": round(
                        float(self._side_attr(sample, side, "gap_adverse_r")),
                        5,
                    ),
                    "mfe_before_mae": bool(
                        self._side_attr(sample, side, "mfe_before_mae")
                    ),
                    "execution_cost_r": round(float(sample.outcome.execution_cost_r), 5),
                    "fill_probability": round(float((sample.outcome.execution or {}).get("fill_probability", 0.0)), 5),
                    "max_size_usd": round(float((sample.outcome.execution or {}).get("max_size_usd", 0.0)), 2),
                    "entry_trigger_score": round(float(sample.features.get(f"{side}_entry_trigger_score", 0.0)), 5),
                    "data_lineage": {
                        "adjusted": sample.features.get("data_adjusted"),
                        "what_to_show": sample.features.get("data_what_to_show"),
                        "bar_complete": sample.features.get("data_bar_complete"),
                    },
                }
            )
        return ledger

    @staticmethod
    def _triple_barrier_label(target_bar: int | None, stop_bar: int | None) -> str:
        if target_bar is not None:
            return "target"
        if stop_bar is not None:
            return "stop"
        return "timeout"

    @staticmethod
    def _side_attr(sample: WindowSample, side: Side, suffix: str) -> object:
        return getattr(sample.outcome, f"{side}_{suffix}")

    def _cost_stress_metrics(self, samples: list[WindowSample], side: Side, rr: float) -> dict[str, object]:
        stress: dict[str, object] = {}
        for multiplier in self.cost_stress_multipliers or [1.0, 2.0, 3.0]:
            metrics = self._split_metrics(samples, side, rr, cost_multiplier=float(multiplier))
            stress[f"{float(multiplier):g}x"] = {
                "multiplier": float(multiplier),
                "expectancy_r": metrics["expectancy_r"],
                "profit_factor": metrics["profit_factor"],
                "win_rate": metrics["win_rate"],
                "max_drawdown_r": metrics["max_drawdown_r"],
                "sample_count": metrics["sample_count"],
            }
        return stress

    @staticmethod
    def _cost_stress_passed(stress: object, *, required_multiplier: float) -> bool:
        if not isinstance(stress, dict):
            return False
        key = f"{float(required_multiplier):g}x"
        metrics = stress.get(key)
        if not isinstance(metrics, dict):
            return False
        return float(metrics.get("expectancy_r", 0.0)) > 0 and float(metrics.get("profit_factor", 0.0)) >= 1.0

    @staticmethod
    def _split_metrics(
        samples: list[WindowSample],
        side: Side,
        rr: float,
        *,
        cost_multiplier: float = 1.0,
    ) -> dict[str, float | int]:
        outcomes_list: list[float] = []
        skipped_count = 0
        skip_reason_counts: dict[str, int] = {}
        for sample in samples:
            detail = RewardRiskAnalyzer._simulate_sample_detail(
                sample,
                side,
                rr,
                cost_multiplier=cost_multiplier,
            )
            if str(detail.get("status", "ok")) not in ("ok", "fallback"):
                skipped_count += 1
                reason = str(detail.get("reason") or "unknown")
                skip_reason_counts[reason] = skip_reason_counts.get(reason, 0) + 1
                continue
            outcomes_list.append(RewardRiskAnalyzer._tuple_from_detail(detail)[0])
        outcomes = np.asarray(outcomes_list, dtype=float)
        if len(outcomes) == 0:
            return {
                "sample_count": 0,
                "signal_count": len(samples),
                "skipped_count": skipped_count,
                "skip_rate": round(skipped_count / len(samples), 5) if samples else 0.0,
                "skip_reason_counts": skip_reason_counts,
                "expectancy_r": 0.0,
                "profit_factor": 0.0,
                "win_rate": 0.0,
                "max_drawdown_r": 0.0,
            }
        wins = outcomes[outcomes > 0]
        losses = outcomes[outcomes < 0]
        pf = float(wins.sum() / abs(losses.sum())) if len(losses) else float(wins.sum() or 0.0)
        return {
            "sample_count": int(len(outcomes)),
            "signal_count": int(len(samples)),
            "skipped_count": skipped_count,
            "skip_rate": round(skipped_count / len(samples), 5) if samples else 0.0,
            "skip_reason_counts": skip_reason_counts,
            "expectancy_r": round(float(np.mean(outcomes)), 5),
            "profit_factor": round(pf, 5),
            "win_rate": round(float(np.mean(outcomes > 0)), 5),
            "max_drawdown_r": round(RewardRiskAnalyzer._max_drawdown(outcomes), 5),
        }

    @staticmethod
    def _group_expectancy(samples: list[WindowSample], outcomes: np.ndarray, key: str) -> dict[str, float]:
        buckets: dict[str, list[float]] = {}
        for sample, outcome in zip(samples, outcomes, strict=True):
            value = str(getattr(sample, key))
            buckets.setdefault(value, []).append(float(outcome))
        items = sorted(
            ((k, round(float(np.mean(v)), 5)) for k, v in buckets.items()),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
        return dict(items)

    @staticmethod
    def _positive_group_fraction(group_metrics: dict[str, float]) -> float:
        if not group_metrics:
            return 0.0
        return float(sum(1 for v in group_metrics.values() if v > 0) / len(group_metrics))

    @staticmethod
    def _side_score(metrics: dict[str, object]) -> float:
        train = metrics.get("train_metrics", {})
        expectancy = (
            float(train.get("expectancy_r", 0.0)) if isinstance(train, dict) else float(metrics.get("in_sample_expectancy_r", 0.0))
        )
        pf = min(
            float(train.get("profit_factor", 0.0)) if isinstance(train, dict) else float(metrics.get("in_sample_profit_factor", 0.0)),
            8.0,
        )
        hit_rate = float(metrics.get("target_hit_rate", metrics.get("hit_4r_rate", 0.0)))
        stability = float(metrics.get("stability_score", 0.0))
        return expectancy * 2.0 + pf * 0.15 + hit_rate * 1.5 + stability * 0.7

    @staticmethod
    def _candidate_score(metrics: dict[str, object]) -> float:
        train = metrics.get("train_metrics", {})
        if isinstance(train, dict):
            train_expectancy = float(train.get("best_expectancy_r", train.get("expectancy_r", 0.0)) or 0.0)
            train_pf = float(train.get("best_profit_factor", train.get("profit_factor", 0.0)) or 0.0)
            stability = float(train.get("stability_score", metrics.get("stability_score", 0.0)) or 0.0)
        else:
            train_expectancy = float(metrics.get("best_expectancy_r", metrics.get("in_sample_expectancy_r", 0.0)) or 0.0)
            train_pf = float(metrics.get("best_profit_factor", metrics.get("in_sample_profit_factor", 0.0)) or 0.0)
            stability = float(metrics.get("stability_score", 0.0))
        expectancy = max(0.0, train_expectancy)
        pf = min(train_pf, 8.0) / 8.0
        hit = float(metrics.get("target_hit_rate", metrics.get("hit_4r_rate", 0.0)))
        oos = max(0.0, float(metrics.get("out_of_sample_expectancy_r", 0.0)))
        rr = min(float(metrics.get("best_rr", 0.0)), 8.0) / 8.0
        operational = metrics.get("operational_trigger", {})
        trigger_rate = float(operational.get("trigger_rate", 0.0)) if isinstance(operational, dict) else 0.0
        walk_forward_rate = float(metrics.get("walk_forward_positive_fold_rate", 0.0))
        lift = min(max(0.0, float(metrics.get("expectancy_lift_r", 0.0))), 2.0)
        adjusted_p = min(max(float(metrics.get("adjusted_p_value", 1.0)), 0.0), 1.0)
        overfit = min(max(float(metrics.get("overfit_score", 0.5)), 0.0), 1.0)
        ci_low_bonus = min(max(0.0, float(metrics.get("expectancy_ci_low", 0.0))), 1.0)
        purged_rate = float(metrics.get("purged_cv_positive_rate", 0.0))
        deflated_psr = float(metrics.get("deflated_sharpe_probability", 0.0))
        fast_target = float(metrics.get("fast_target_rate", 0.0))
        fill_probability = float(metrics.get("avg_fill_probability", 0.0))
        replay = metrics.get("market_replay", {})
        replay_expectancy = (
            max(0.0, float(replay.get("expected_expectancy_r", 0.0))) if isinstance(replay, dict) else 0.0
        )
        replay_quality = (
            float(replay.get("execution_quality_score", 0.0)) if isinstance(replay, dict) else 0.0
        )
        challenge = metrics.get("adversarial_challenge", {})
        challenge_score = float(challenge.get("challenge_score", 0.0)) if isinstance(challenge, dict) else 0.0
        causal = metrics.get("causal_invariance", {})
        invariance_score = float(causal.get("invariance_score", 0.0)) if isinstance(causal, dict) else 0.0
        teacher = metrics.get("foundation_teacher", {})
        teacher_digest = teacher.get("pretraining_digest", {}) if isinstance(teacher, dict) else {}
        teacher_score = (
            float(teacher_digest.get("embedding_quality_score", 0.0)) if isinstance(teacher_digest, dict) else 0.0
        )
        edge_decay = min(max(float(metrics.get("edge_decay_parameter_score", 0.0)), 0.0), 1.0)
        testing_penalty = min(max(float(metrics.get("multiple_testing_penalty", 0.0)), 0.0), 1.0)
        confidence = 1.0 - adjusted_p
        raw_score = (
            expectancy * 0.24
            + pf * 0.13
            + hit * 0.11
            + stability * 0.11
            + oos * 0.08
            + rr * 0.05
            + trigger_rate * 0.04
            + walk_forward_rate * 0.03
            + purged_rate * 0.03
            + ci_low_bonus * 0.02
            + deflated_psr * 0.02
            + fast_target * 0.01
            + fill_probability * 0.01
            + min(replay_expectancy, 1.0) * 0.05
            + replay_quality * 0.03
            + challenge_score * 0.03
            + invariance_score * 0.03
            + teacher_score * 0.02
        )
        challenge_penalty = 0.25 if isinstance(challenge, dict) and challenge.get("rejection_recommended") else 0.0
        replay_penalty = 0.18 if isinstance(replay, dict) and replay.get("passed") is False else 0.0
        invariance_penalty = 0.15 if isinstance(causal, dict) and causal.get("passed") is False else 0.0
        robustness = (
            (1.0 - 0.35 * overfit)
            * (1.0 - 0.12 * edge_decay)
            * (1.0 - 0.10 * testing_penalty)
            * (1.0 - challenge_penalty)
            * (1.0 - replay_penalty)
            * (1.0 - invariance_penalty)
        )
        return raw_score * (0.45 + 0.55 * confidence) * robustness + lift * 0.05

    @staticmethod
    def _promotion_score(metrics: dict[str, object]) -> float:
        train = metrics.get("train_metrics", {})
        oos = metrics.get("out_of_sample_metrics", {})
        wf = metrics.get("walk_forward_metrics", {})
        train_expectancy = (
            float(train.get("best_expectancy_r", train.get("expectancy_r", 0.0)) or 0.0)
            if isinstance(train, dict)
            else float(metrics.get("best_expectancy_r", 0.0) or 0.0)
        )
        oos_expectancy = (
            float(oos.get("expectancy_r", 0.0) or 0.0)
            if isinstance(oos, dict)
            else float(metrics.get("out_of_sample_expectancy_r", 0.0) or 0.0)
        )
        wf_rate = (
            float(wf.get("positive_fold_rate", 0.0) or 0.0)
            if isinstance(wf, dict)
            else float(metrics.get("walk_forward_positive_fold_rate", 0.0) or 0.0)
        )
        purged_rate = float(metrics.get("purged_cv_positive_rate", 0.0) or 0.0)
        adjusted_p = min(max(float(metrics.get("adjusted_p_value", 1.0) or 1.0), 0.0), 1.0)
        return round(
            max(0.0, train_expectancy) * 0.35
            + max(0.0, oos_expectancy) * 0.25
            + wf_rate * 0.20
            + purged_rate * 0.10
            + (1.0 - adjusted_p) * 0.10,
            5,
        )

    @staticmethod
    def _feature_summary(samples: list[WindowSample]) -> dict[str, object]:
        if not samples:
            return {}
        summary: dict[str, object] = {}
        for key in _numeric_feature_keys(samples):
            values = _numeric_feature_values(samples, key)
            summary[key] = {
                "mean": round(float(np.mean(values)), 6),
                "median": round(float(np.median(values)), 6),
                "p25": round(float(np.quantile(values, 0.25)), 6),
                "p75": round(float(np.quantile(values, 0.75)), 6),
            }
        return summary

    @classmethod
    def _human_rule(
        cls,
        samples: list[WindowSample],
        *,
        baseline_samples: list[WindowSample],
        side: Side,
        metrics: dict[str, object],
    ) -> dict[str, object]:
        if not samples:
            return {"method": "monotonic_feature_rules", "rule": "", "conditions": []}
        allowed = cls._interpretable_feature_names(samples, baseline_samples)
        conditions: list[dict[str, object]] = []
        for key in allowed:
            cluster_values = np.asarray([sample.features.get(key, 0.0) for sample in samples], dtype=float)
            baseline_values = np.asarray([sample.features.get(key, 0.0) for sample in baseline_samples], dtype=float)
            if len(cluster_values) == 0 or len(baseline_values) == 0:
                continue
            cluster_median = float(np.median(cluster_values))
            baseline_median = float(np.median(baseline_values))
            iqr = float(np.quantile(baseline_values, 0.75) - np.quantile(baseline_values, 0.25))
            denominator = max(iqr, abs(baseline_median) * 0.25, 0.01)
            distinctiveness = abs(cluster_median - baseline_median) / denominator
            if distinctiveness < 0.45:
                continue
            if cluster_median >= baseline_median:
                operator = ">="
                threshold = float(np.quantile(cluster_values, 0.25))
            else:
                operator = "<="
                threshold = float(np.quantile(cluster_values, 0.75))
            conditions.append(
                {
                    "feature": key,
                    "label": cls._feature_label(key),
                    "operator": operator,
                    "threshold": round(float(threshold), 6),
                    "cluster_median": round(cluster_median, 6),
                    "baseline_median": round(baseline_median, 6),
                    "distinctiveness": round(float(distinctiveness), 5),
                    "monotonic": True,
                }
            )
        conditions = sorted(conditions, key=lambda item: float(item["distinctiveness"]), reverse=True)[:4]
        fragments = [
            f"{item['label']} {item['operator']} {item['threshold']}"
            for item in conditions
        ]
        if fragments:
            rule = f"{side} setup when " + " and ".join(fragments)
        else:
            rule = f"{side} setup defined by centroid similarity; no single feature rule dominates"
        return {
            "method": "monotonic_feature_rules",
            "side": side,
            "rule": rule,
            "conditions": conditions,
            "support": int(len(samples)),
            "quality": {
                "best_rr": metrics.get("best_rr", 0.0),
                "expectancy_r": metrics.get("expectancy_r", 0.0),
                "profit_factor": metrics.get("profit_factor", 0.0),
                "purged_cv_positive_rate": metrics.get("purged_cv_positive_rate", 0.0),
            },
        }

    @staticmethod
    def _interpretable_feature_names(
        samples: list[WindowSample],
        baseline_samples: list[WindowSample],
    ) -> list[str]:
        preferred = [
            "cumulative_return",
            "slope",
            "last_quarter_return",
            "local_drawdown",
            "local_runup",
            "range_phase_expansion",
            "volume_phase_acceleration",
            "volume_rel_last",
            "shapelet_v_reversal_score",
            "shapelet_inverted_v_score",
            "shapelet_flag_continuation_score",
            "swing_hh_rate",
            "swing_hl_rate",
            "swing_lh_rate",
            "swing_ll_rate",
            "swing_trend_score",
            "gap_up_reclaim_continuation_score",
            "gap_down_reclaim_continuation_score",
            "relative_strength_spy",
            "relative_strength_qqq",
            "relative_strength_sector",
            "relative_strength_industry",
            "market_regime_score",
            "market_breadth_proxy",
            "liquidity_score",
            "avg_dollar_volume",
            "atr_pct",
        ]
        available = {key for sample in samples + baseline_samples for key in sample.features}
        numeric = set(_numeric_feature_keys(samples + baseline_samples))
        return [key for key in preferred if key in available and key in numeric]

    @staticmethod
    def _feature_label(key: str) -> str:
        labels = {
            "cumulative_return": "window return",
            "slope": "price slope",
            "last_quarter_return": "late-window return",
            "local_drawdown": "local drawdown",
            "local_runup": "runup from low",
            "range_phase_expansion": "range expansion",
            "volume_phase_acceleration": "volume acceleration",
            "volume_rel_last": "last relative volume",
            "shapelet_v_reversal_score": "V reversal shape",
            "shapelet_inverted_v_score": "inverted-V shape",
            "shapelet_flag_continuation_score": "flag continuation shape",
            "swing_hh_rate": "higher-high swing rate",
            "swing_hl_rate": "higher-low swing rate",
            "swing_lh_rate": "lower-high swing rate",
            "swing_ll_rate": "lower-low swing rate",
            "swing_trend_score": "swing trend score",
            "gap_up_reclaim_continuation_score": "gap-up reclaim continuation",
            "gap_down_reclaim_continuation_score": "gap-down reclaim continuation",
            "relative_strength_spy": "RS vs SPY",
            "relative_strength_qqq": "RS vs QQQ",
            "relative_strength_sector": "RS vs sector",
            "relative_strength_industry": "RS vs industry",
            "market_regime_score": "market regime score",
            "market_breadth_proxy": "breadth proxy",
            "liquidity_score": "liquidity score",
            "avg_dollar_volume": "avg dollar volume",
            "atr_pct": "ATR percent",
        }
        return labels.get(key, key.replace("_", " "))

    @classmethod
    def _regime_profile(cls, samples: list[WindowSample]) -> dict[str, object]:
        if not samples:
            return {"dominant_regime": "unknown", "buckets": {}}
        bucket_counts: dict[str, int] = {}
        for sample in samples:
            stratum = cls._stratum(sample)
            bucket = "|".join(str(part) for part in stratum[1:])
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        dominant = max(bucket_counts.items(), key=lambda item: item[1])[0] if bucket_counts else "unknown"
        feature_keys = [
            "volatility_regime",
            "trend_regime",
            "market_regime_score",
            "market_breadth_proxy",
            "sector_strength",
            "liquidity_score",
        ]
        means = {
            key: round(float(np.mean([sample.features.get(key, 0.0) for sample in samples])), 6)
            for key in feature_keys
        }
        sorted_buckets = dict(sorted(bucket_counts.items(), key=lambda item: item[1], reverse=True)[:12])
        dominant_parts = dominant.split("|")
        total = sum(bucket_counts.values()) or 1
        regime_count = len(bucket_counts)
        dominant_share = bucket_counts.get(dominant, 0) / total
        return {
            "dominant_regime": dominant,
            "preferred_regime_keys": [dominant],
            "bucket_counts": sorted_buckets,
            "buckets": sorted_buckets,
            "regime_count": regime_count,
            "dominant_share": round(float(dominant_share), 6),
            "regime_specific": regime_count < 2 or dominant_share >= 0.75,
            "research_gate": (
                "regime_specific"
                if regime_count < 2 or dominant_share >= 0.75
                else "multi_regime_observed"
            ),
            "top_trend_regime": dominant_parts[1] if len(dominant_parts) > 1 else "",
            "top_market_regime": dominant_parts[2] if len(dominant_parts) > 2 else "",
            "feature_means": means,
        }

    def _benchmark_regime_outcomes(
        self,
        samples: list[WindowSample],
        *,
        side: Side,
        rr: float,
    ) -> dict[str, object]:
        """Labeled outcome history per benchmark-regime bucket (section 3.8).

        Each cluster sample is labeled with the PIT benchmark regime at its
        window end and simulated with the canonical triple-barrier path at the
        pattern's side/RR, so the matcher can calibrate a regime gate against
        real per-bucket expectancies instead of presence heuristics.
        """
        table = self.benchmark_regime_table
        if table is None or table.empty:
            return {
                "available": False,
                "reason": "benchmark_regime_table_unavailable",
                "buckets": {},
            }
        keys = regime_keys_for_dates(table, [sample.end for sample in samples])
        grouped: dict[str, list[float]] = {}
        for sample, key in zip(samples, keys, strict=True):
            outcome_r = float(RewardRiskAnalyzer._simulate_sample(sample, side, rr)[0])
            grouped.setdefault(key, []).append(outcome_r)
        buckets: dict[str, dict[str, float | int]] = {}
        labeled = 0
        for key in sorted(grouped):
            arr = np.asarray(grouped[key], dtype=float)
            stats = self._outcome_metrics(arr)
            buckets[key] = {"sample_count": int(len(arr)), **stats}
            if INSUFFICIENT_HISTORY not in key:
                labeled += int(len(arr))
        return {
            "available": True,
            "method": "pit_benchmark_regime_at_sample_end+canonical_triple_barrier",
            "side": str(side),
            "rr": round(float(rr), 4),
            "benchmark_symbol": str(table.attrs.get("benchmark_symbol", "SPY")),
            "labeled_sample_count": int(labeled),
            "unlabeled_sample_count": int(len(samples) - labeled),
            "buckets": buckets,
        }

    def _apply_novelty_diversity(self, candidates: list[ClusterCandidate]) -> None:
        if not candidates:
            return
        ordered = sorted(candidates, key=lambda candidate: candidate.score, reverse=True)
        prior: list[ClusterCandidate] = []
        for candidate in ordered:
            comparable = [
                existing
                for existing in prior
                if existing.side == candidate.side
                and existing.timeframe == candidate.timeframe
                and existing.window_size == candidate.window_size
            ]
            max_similarity = max(
                (self._centroid_similarity(candidate.centroid, existing.centroid) for existing in comparable),
                default=0.0,
            )
            novelty = max(0.0, min(1.0, 1.0 - max_similarity))
            regime_profile = candidate.metrics.get("regime_profile", {})
            dominant_regime = (
                str(regime_profile.get("dominant_regime", "unknown"))
                if isinstance(regime_profile, dict)
                else "unknown"
            )
            bucket = f"{candidate.side}|{candidate.timeframe}|w{candidate.window_size}|{dominant_regime}"
            density = float(candidate.metrics.get("cluster_density", 0.0))
            rare_promising_bonus = 0.0
            if density > 0.0 and density <= 0.08 and float(candidate.metrics.get("expectancy_r", 0.0)) > 0:
                rare_promising_bonus = min(0.12, (0.08 - density) * 1.5)
            uncertainty = 1.0 / math.sqrt(max(candidate.sample_count, 1))
            quality = max(0.0, float(candidate.metrics.get("expectancy_lift_r", 0.0))) + max(
                0.0,
                float(candidate.metrics.get("out_of_sample_expectancy_r", 0.0)),
            )
            expected_information_gain = novelty * (quality + rare_promising_bonus) * min(1.0, uncertainty * 10.0)
            candidate.metrics["run_max_family_similarity"] = round(float(max_similarity), 6)
            candidate.metrics["novelty_score"] = round(float(novelty), 6)
            candidate.metrics["diversity_bucket"] = bucket
            candidate.metrics["rare_promising_bonus"] = round(float(rare_promising_bonus), 6)
            candidate.metrics["expected_information_gain"] = round(float(expected_information_gain), 6)
            candidate.metrics["base_score_before_novelty"] = candidate.score
            prior.append(candidate)

        buckets: dict[str, list[ClusterCandidate]] = {}
        for candidate in candidates:
            bucket = str(candidate.metrics.get("diversity_bucket", "unknown"))
            buckets.setdefault(bucket, []).append(candidate)
        for bucket_candidates in buckets.values():
            ranked = sorted(bucket_candidates, key=lambda candidate: candidate.score, reverse=True)
            for rank, candidate in enumerate(ranked, start=1):
                novelty = float(candidate.metrics.get("novelty_score", 1.0))
                eig = float(candidate.metrics.get("expected_information_gain", 0.0))
                rare_bonus = float(candidate.metrics.get("rare_promising_bonus", 0.0))
                quota_penalty = min(0.45, max(0, rank - 3) * 0.12)
                candidate.metrics["diversity_quota_rank"] = rank
                candidate.metrics["diversity_quota_penalty"] = round(float(quota_penalty), 6)
                adjusted = (
                    candidate.score
                    * (0.78 + 0.22 * novelty)
                    * (1.0 - quota_penalty)
                    + eig * 0.06
                    + rare_bonus * 0.03
                )
                candidate.score = round(float(max(0.0, adjusted)), 5)

    @staticmethod
    def _centroid_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        left_arr = np.asarray(left, dtype=float)
        right_arr = np.asarray(right, dtype=float)
        if not np.isfinite(left_arr).all() or not np.isfinite(right_arr).all():
            return 0.0
        distance = float(np.linalg.norm(left_arr - right_arr) / max(1.0, np.sqrt(len(left_arr))))
        return float(1.0 / (1.0 + distance))

    def _examples(
        self,
        samples: list[WindowSample],
        vectors_scaled: np.ndarray,
        centroid_scaled: np.ndarray,
        side: Side,
    ) -> list[dict[str, object]]:
        distances = np.linalg.norm(vectors_scaled - centroid_scaled, axis=1)
        outcomes = np.asarray([s.outcome.outcome_for(side) for s in samples], dtype=float)
        selected: list[tuple[int, str]] = []
        for idx in np.argsort(distances)[:4]:
            selected.append((int(idx), "typical"))
        for idx in np.argsort(outcomes)[-4:][::-1]:
            selected.append((int(idx), "winner"))
        for idx in np.argsort(outcomes)[:3]:
            selected.append((int(idx), "loser"))
        seen: set[int] = set()
        examples: list[dict[str, object]] = []
        for idx, kind in selected:
            if idx in seen:
                continue
            seen.add(idx)
            sample = samples[idx]
            similarity = float(1.0 / (1.0 + distances[idx]))
            examples.append(
                {
                    "symbol": sample.symbol,
                    "timeframe": sample.timeframe,
                    "window_start": sample.start,
                    "window_end": sample.end,
                    "forward_end": sample.outcome.forward_end,
                    "entry_price": round(sample.outcome.entry_price, 4),
                    "risk_proxy": round(sample.outcome.risk_proxy, 4),
                    "outcome_r": round(sample.outcome.outcome_for(side), 4),
                    "mfe_r": round(sample.outcome.mfe_for(side), 4),
                    "mae_r": round(sample.outcome.mae_for(side), 4),
                    "triple_barrier_label": sample.outcome.label_for(side),
                    "time_to_target": sample.outcome.time_to_target_for(side),
                    "time_to_stop": sample.outcome.time_to_stop_for(side),
                    "speed_label": sample.outcome.speed_label_for(side),
                    "gap_adverse_r": round(
                        float(self._side_attr(sample, side, "gap_adverse_r")),
                        5,
                    ),
                    "mfe_before_mae": bool(
                        self._side_attr(sample, side, "mfe_before_mae")
                    ),
                    "fill_probability": round(float((sample.outcome.execution or {}).get("fill_probability", 0.0)), 5),
                    "max_size_usd": round(float((sample.outcome.execution or {}).get("max_size_usd", 0.0)), 2),
                    "similarity": round(similarity, 6),
                    "kind": kind,
                    "chart": sample.chart,
                    "features": _json_safe_features(sample.features),
                }
            )
        return examples

    @staticmethod
    def _cluster_signature(
        samples: list[WindowSample],
        vectors_scaled: np.ndarray,
        centroid_scaled: np.ndarray,
        side: Side,
    ) -> dict[str, object]:
        if not samples or vectors_scaled.size == 0:
            return {
                "medoid": {},
                "similarity_distribution": {},
                "concentration_checks": {
                    "passed": False,
                    "reasons": ["empty_cluster"],
                    "max_symbol_share": 0.0,
                    "max_month_share": 0.0,
                    "symbol_herfindahl": 0.0,
                    "month_herfindahl": 0.0,
                },
            }
        distances = np.linalg.norm(vectors_scaled - centroid_scaled, axis=1) / max(
            1.0, math.sqrt(vectors_scaled.shape[1])
        )
        similarities = 1.0 / (1.0 + distances)
        medoid_idx = int(np.argmin(distances))
        medoid_sample = samples[medoid_idx]

        def share_counts(values: list[str]) -> tuple[dict[str, int], float, float]:
            counts: dict[str, int] = {}
            for value in values:
                counts[value] = counts.get(value, 0) + 1
            total = max(1, len(values))
            shares = [count / total for count in counts.values()]
            return counts, round(float(max(shares, default=0.0)), 6), round(float(sum(s * s for s in shares)), 6)

        month_keys: list[str] = []
        for sample in samples:
            try:
                month_keys.append(pd.Timestamp(sample.end).strftime("%Y-%m"))
            except (TypeError, ValueError):
                month_keys.append("unknown")
        symbol_counts, max_symbol_share, symbol_hhi = share_counts([sample.symbol for sample in samples])
        month_counts, max_month_share, month_hhi = share_counts(month_keys)
        reasons: list[str] = []
        if max_symbol_share > 0.40:
            reasons.append("symbol_concentration_gt_40pct")
        if max_month_share > 0.50:
            reasons.append("month_concentration_gt_50pct")
        top_symbols = sorted(symbol_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        top_months = sorted(month_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        return {
            "method": "centroid_distance_medoid_and_concentration",
            "medoid": {
                "symbol": medoid_sample.symbol,
                "timeframe": medoid_sample.timeframe,
                "window_start": medoid_sample.start,
                "window_end": medoid_sample.end,
                "outcome_r": round(float(medoid_sample.outcome.outcome_for(side)), 5),
                "similarity": round(float(similarities[medoid_idx]), 6),
                "distance": round(float(distances[medoid_idx]), 6),
                "chart": medoid_sample.chart,
                "features": _json_safe_features(medoid_sample.features),
            },
            "similarity_distribution": {
                "p05": round(float(np.quantile(similarities, 0.05)), 6),
                "p50": round(float(np.quantile(similarities, 0.50)), 6),
                "p90": round(float(np.quantile(similarities, 0.90)), 6),
                "p95": round(float(np.quantile(similarities, 0.95)), 6),
                "min": round(float(np.min(similarities)), 6),
                "max": round(float(np.max(similarities)), 6),
            },
            "concentration_checks": {
                "passed": not reasons,
                "reasons": reasons,
                "max_symbol_share": max_symbol_share,
                "max_month_share": max_month_share,
                "symbol_herfindahl": symbol_hhi,
                "month_herfindahl": month_hhi,
                "top_symbols": [{"symbol": symbol, "count": count} for symbol, count in top_symbols],
                "top_months": [{"month": month, "count": count} for month, count in top_months],
                "thresholds": {
                    "max_symbol_share": 0.40,
                    "max_month_share": 0.50,
                },
            },
        }

    def _quant_validation_metrics(
        self,
        samples: list[WindowSample],
        *,
        side: Side,
        rr: float,
    ) -> dict[str, object]:
        """Dedup + uniqueness-weighted inference over the cluster's train events.

        Overlapping windows from a stride sampler pseudo-replicate the same market
        episode. Here every occurrence's outcome span is placed on a shared
        calendar-day axis, occurrences of the same symbol that overlap in time are
        deduplicated, and the survivors get Lopez de Prado average-uniqueness
        weights so n_eff (= sum of weights) reflects the information actually
        available. Expectancy/PF are weight-corrected and uncertainty comes from a
        stationary block bootstrap plus a Newey-West t-stat, both of which respect
        the residual autocorrelation that an iid bootstrap ignores.
        """
        empty = {
            "n_raw": len(samples),
            "n_unique": 0,
            "n_eff": 0.0,
            "expectancy_r_weighted": 0.0,
            "profit_factor_weighted": 0.0,
            "expectancy_ci95_low": 0.0,
            "expectancy_ci95_high": 0.0,
            "newey_west_t": 0.0,
            "sharpe_per_trade": 0.0,
            "skew": 0.0,
            "kurtosis": 3.0,
            "horizon_bars": 0,
            "method": "dedup_uniqueness_stationary_bootstrap_newey_west",
        }
        if not samples:
            return empty
        spans: list[tuple[int, int]] = []
        horizons: list[int] = []
        tradable_samples: list[WindowSample] = []
        tradable_outcomes: list[float] = []
        skipped_count = 0
        skip_reason_counts: dict[str, int] = {}
        for sample in samples:
            detail = RewardRiskAnalyzer._simulate_sample_detail(sample, side, rr)
            if str(detail.get("status", "ok")) not in ("ok", "fallback"):
                skipped_count += 1
                reason = str(detail.get("reason") or "unknown")
                skip_reason_counts[reason] = skip_reason_counts.get(reason, 0) + 1
                continue
            tradable_samples.append(sample)
            tradable_outcomes.append(RewardRiskAnalyzer._tuple_from_detail(detail)[0])
            entry_day = pd.Timestamp(sample.end).toordinal() + 1
            exit_day = max(entry_day, pd.Timestamp(sample.outcome.forward_end).toordinal())
            spans.append((entry_day, exit_day))
            if sample.outcome.forward_returns:
                horizons.append(max(int(h) for h in sample.outcome.forward_returns))
        if not tradable_samples:
            return {
                **empty,
                "n_raw": len(samples),
                "signal_count": len(samples),
                "skipped_count": skipped_count,
                "skip_rate": 1.0,
                "skip_reason_counts": skip_reason_counts,
            }
        horizon_bars = max(horizons) if horizons else 10
        starts = np.asarray([s for s, _ in spans], dtype=int)
        ends = np.asarray([e for _, e in spans], dtype=int)

        kept: list[int] = []
        by_symbol: dict[str, list[int]] = {}
        for idx, sample in enumerate(tradable_samples):
            by_symbol.setdefault(sample.symbol, []).append(idx)
        for indices in by_symbol.values():
            idx_arr = np.asarray(indices, dtype=int)
            local_keep = select_nonoverlapping_events(starts[idx_arr], ends[idx_arr])
            kept.extend(int(idx_arr[i]) for i in local_keep)
        kept_arr = np.asarray(sorted(kept), dtype=int)
        if kept_arr.size == 0:
            return {
                **empty,
                "signal_count": len(samples),
                "skipped_count": skipped_count,
                "skip_rate": round(skipped_count / len(samples), 5) if samples else 0.0,
                "skip_reason_counts": skip_reason_counts,
            }

        weights, n_eff = average_uniqueness_weights(starts[kept_arr], ends[kept_arr])
        order = np.argsort(starts[kept_arr], kind="stable")
        kept_sorted = kept_arr[order]
        weights_sorted = weights[order]
        outcomes = np.asarray([tradable_outcomes[int(i)] for i in kept_sorted], dtype=float)
        weight_sum = float(weights_sorted.sum())
        mean_w = float(np.sum(weights_sorted * outcomes) / weight_sum) if weight_sum > 0 else 0.0
        pf_w = weighted_profit_factor(outcomes, weights_sorted)
        seed = self._null_seed(side, rr, kept_sorted.size, len(samples)) ^ 0x51A7B007
        ci_lo, ci_hi, _, _ = stationary_bootstrap_ci(
            outcomes,
            np.mean,
            n_boot=max(100, int(self.quant_bootstrap_draws)),
            mean_block=horizon_bars,
            rng=seed,
        )
        nw_t, _ = newey_west_tstat(outcomes, lags=horizon_bars)
        sd = float(np.std(outcomes, ddof=1)) if outcomes.size > 1 else 0.0
        sharpe = float(np.mean(outcomes) / sd) if sd > 1e-12 else 0.0
        skew, kurt = sample_skew_kurt(outcomes)
        return {
            "n_raw": len(samples),
            "signal_count": len(samples),
            "skipped_count": skipped_count,
            "skip_rate": round(skipped_count / len(samples), 5) if samples else 0.0,
            "skip_reason_counts": skip_reason_counts,
            "n_unique": int(kept_sorted.size),
            "n_eff": round(float(n_eff), 4),
            "expectancy_r_weighted": round(mean_w, 5),
            "profit_factor_weighted": round(float(pf_w), 5) if math.isfinite(pf_w) else pf_w,
            "expectancy_ci95_low": round(float(ci_lo), 5) if math.isfinite(ci_lo) else 0.0,
            "expectancy_ci95_high": round(float(ci_hi), 5) if math.isfinite(ci_hi) else 0.0,
            "newey_west_t": round(float(nw_t), 5) if math.isfinite(nw_t) else 0.0,
            "sharpe_per_trade": round(sharpe, 5),
            "skew": round(float(skew), 5),
            "kurtosis": round(float(kurt), 5),
            "horizon_bars": int(horizon_bars),
            "method": "dedup_uniqueness_stationary_bootstrap_newey_west",
        }

    def _prototype_bank_seed(self, window_size: int, cluster_id: int) -> int:
        """Deterministic per-cluster seed so reruns rebuild the same bank."""
        return int(self.random_state) * 1_000_003 + int(window_size) * 101 + int(cluster_id)

    def _match_tau_similarity(
        self,
        cluster_vectors: np.ndarray,
        centroid: np.ndarray,
        weights: np.ndarray | None = None,
    ) -> float:
        """Per-pattern matcher threshold from the intra-cluster similarity spread.

        Uses the same normalized-distance -> similarity mapping as
        NovelPatternMatcher so the persisted tau is directly comparable at match
        time. tau is the similarity such that match_tau_percentile% of real
        cluster members would pass; the global config threshold stays as a floor.
        """
        if cluster_vectors.size == 0:
            return 0.0
        similarities = FalseMatchHarness._similarities(cluster_vectors, centroid, weights)
        pct = min(max(float(self.match_tau_percentile), 50.0), 100.0)
        tau = float(np.quantile(similarities, 1.0 - pct / 100.0))
        return round(tau, 6)

    @staticmethod
    def _match_conformal_threshold(
        cluster_vectors: np.ndarray,
        centroid: np.ndarray,
    ) -> dict[str, object]:
        if cluster_vectors.size == 0:
            return {"blocked": True, "reason": "empty_cluster"}
        similarities = FalseMatchHarness._similarities(cluster_vectors, centroid)
        return split_conformal_similarity_threshold(
            similarities,
            alpha=0.10,
            min_calibration_count=20,
        )

    @staticmethod
    def _prototype_match_contract(
        cluster_vectors: np.ndarray,
        centroid: np.ndarray,
        *,
        medoid_count: int = 16,
        knn_k: int = 3,
    ) -> dict[str, object]:
        if cluster_vectors.size == 0:
            return {
                "matcher_medoids_scaled": [],
                "matcher_diag_variance_scaled": [],
                "match_knn_similarity_threshold": 0.0,
            }
        distances = np.linalg.norm(cluster_vectors - centroid, axis=1) / max(
            1.0, math.sqrt(cluster_vectors.shape[1])
        )
        medoid_indices = np.argsort(distances)[: max(1, min(medoid_count, cluster_vectors.shape[0]))]
        medoids = cluster_vectors[medoid_indices]
        k = max(1, min(knn_k, medoids.shape[0]))
        member_distances = []
        for vector in cluster_vectors:
            dists = np.linalg.norm(medoids - vector, axis=1) / max(
                1.0, math.sqrt(cluster_vectors.shape[1])
            )
            member_distances.append(float(np.mean(np.sort(dists)[:k])))
        member_similarities = 1.0 / (1.0 + np.asarray(member_distances, dtype=float))
        threshold = float(np.quantile(member_similarities, 0.10))
        variance = np.nan_to_num(np.var(cluster_vectors, axis=0), nan=1.0, posinf=1.0, neginf=1.0)
        variance = np.maximum(variance, 1e-6)
        return {
            "matcher_medoids_scaled": np.round(medoids, 6).tolist(),
            "matcher_diag_variance_scaled": np.round(variance, 6).tolist(),
            "match_knn_similarity_threshold": round(threshold, 6),
            "matcher_prototype_contract": {
                "method": "nearest_centroid_medoids_diag_variance_v1",
                "medoid_count": int(medoids.shape[0]),
                "knn_k": k,
                "threshold_recall_target": 0.90,
                "threshold_method": "p10_member_knn_similarity",
            },
        }

    def _false_match_metrics(
        self,
        *,
        cluster_id: int,
        all_labels: np.ndarray,
        ordered_samples: list[WindowSample],
        matrix_all_scaled: np.ndarray,
        cluster_samples: list[WindowSample],
        cluster_vectors: np.ndarray,
        centroid_scaled: np.ndarray,
        tau_similarity: float,
    ) -> dict[str, object]:
        """False-match harness per pattern (audit §3.1.5) + temporal variant (§2.2.a).

        Negative banks are disjoint: same-symbol windows outside the cluster are
        the hard negatives; labeled members of other clusters cover cross-pattern
        confusion; density noise is reported separately. Shadow occurrences only
        exist lab-side, so that bank is empty at research time. The temporal
        variant reweights the same banks with the gamma ramp and its own tau, so
        the gamma change is adopted only if this curve improves (§2.2.a gate).
        """
        outside = np.flatnonzero(np.asarray(all_labels) != cluster_id)
        cluster_symbols = {sample.symbol for sample in cluster_samples}
        same_symbol_mask = np.asarray(
            [ordered_samples[int(i)].symbol in cluster_symbols for i in outside],
            dtype=bool,
        )
        outside_labels = np.asarray(all_labels)[outside]
        noise_mask = outside_labels == -1
        banks = {
            "same_symbol_outside_cluster": matrix_all_scaled[outside[same_symbol_mask]],
            "other_cluster_members": matrix_all_scaled[outside[(~same_symbol_mask) & (~noise_mask)]],
            "noise_windows": matrix_all_scaled[outside[(~same_symbol_mask) & noise_mask]],
            "shadow_occurrences": np.empty((0, matrix_all_scaled.shape[1])),
        }
        harness = FalseMatchHarness(random_state=self.random_state)
        unweighted = harness.evaluate(
            positives=cluster_vectors,
            centroid=centroid_scaled,
            negative_banks=banks,
            tau_similarity=tau_similarity,
        )
        gamma = float(self.match_temporal_gamma)
        engine = PatternEmbeddingEngine()
        weights = engine.temporal_weights(matrix_all_scaled.shape[1], gamma=gamma)
        tau_temporal = self._match_tau_similarity(cluster_vectors, centroid_scaled, weights)
        temporal = harness.evaluate(
            positives=cluster_vectors,
            centroid=centroid_scaled,
            negative_banks=banks,
            tau_similarity=tau_temporal,
            weights=weights,
        )
        return {
            "unweighted": unweighted,
            "temporal": temporal,
            "tau_similarity_temporal": tau_temporal,
            "temporal_weighting": {
                "gamma": gamma,
                "matcher_scaling": str(
                    engine.contract(temporal_gamma=gamma)["matcher_scaling"]
                ),
                "adopted_in_matcher": False,
                "adoption_gate": "temporal fpr_at_recall must beat unweighted in purged validation",
            },
        }

    @staticmethod
    def _pattern_key(window_size: int, cluster_id: int, side: str, centroid: Iterable[float]) -> str:
        digest = blake2b(digest_size=10)
        digest.update(f"w={window_size}|c={cluster_id}|s={side}|".encode())
        arr = np.asarray(list(centroid), dtype=np.float32)
        digest.update(np.round(arr, 3).tobytes())
        return f"novel_{side}_w{window_size}_{digest.hexdigest()}"
