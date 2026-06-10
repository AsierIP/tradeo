from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from itertools import combinations
import math
from typing import Iterable

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

from tradeo.research.adversarial_research import AdversarialResearchEngine
from tradeo.research.causal_invariance import CausalInvariantTester
from tradeo.research.foundation_teacher import FoundationChartTeacher
from tradeo.research.market_replay import MarketReplayEngine
from tradeo.research.reward_risk_analyzer import RewardRiskAnalyzer
from tradeo.research.types import ClusterCandidate, Side, WindowSample


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
        n_clusters = min(self.max_clusters_per_window, max(2, len(train_samples) // self.min_cluster_size))
        model = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=self.random_state,
            n_init=10,
            batch_size=min(2048, max(128, len(train_samples))),
        )
        train_labels = model.fit_predict(matrix_train_scaled)
        all_labels = model.predict(matrix_all_scaled)
        candidates: list[ClusterCandidate] = []
        holdout_ids = {id(sample) for sample in holdout_samples}
        for cluster_id in sorted(set(train_labels.tolist())):
            train_idxs = np.flatnonzero(train_labels == cluster_id)
            if len(train_idxs) < max(10, self.min_cluster_size // 2):
                continue
            all_idxs = np.flatnonzero(all_labels == cluster_id)
            cluster_samples = [ordered_samples[int(i)] for i in all_idxs]
            cluster_train_samples = [train_samples[int(i)] for i in train_idxs]
            cluster_holdout_samples = [sample for sample in cluster_samples if id(sample) in holdout_ids]
            cluster_vectors = matrix_all_scaled[all_idxs]
            centroid_scaled = model.cluster_centers_[cluster_id]
            rr_trial_count = len(self.rr_levels or [1.5, 2.0, 2.5, 3.0, 4.0, 5.0])
            tested_trials = n_clusters * 2 * rr_trial_count
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
            metrics["embedding_length"] = int(matrix_all.shape[1])
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
                "clusters": n_clusters,
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
            metrics["regime_profile"] = self._regime_profile(cluster_samples)
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
        outcomes = np.asarray(
            [RewardRiskAnalyzer._simulate_sample(s, side, rr, cost_multiplier=cost_multiplier)[0] for s in samples],
            dtype=float,
        )
        if len(outcomes) == 0:
            return {
                "sample_count": 0,
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
        keys = sorted({key for s in samples for key in s.features})
        summary: dict[str, object] = {}
        for key in keys:
            values = np.asarray([s.features.get(key, 0.0) for s in samples], dtype=float)
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
        return [key for key in preferred if key in available]

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
        return {
            "dominant_regime": dominant,
            "preferred_regime_keys": [dominant],
            "bucket_counts": sorted_buckets,
            "buckets": sorted_buckets,
            "top_trend_regime": dominant_parts[1] if len(dominant_parts) > 1 else "",
            "top_market_regime": dominant_parts[2] if len(dominant_parts) > 2 else "",
            "feature_means": means,
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
                    "features": {k: round(float(v), 6) for k, v in sample.features.items()},
                }
            )
        return examples

    @staticmethod
    def _pattern_key(window_size: int, cluster_id: int, side: str, centroid: Iterable[float]) -> str:
        digest = blake2b(digest_size=10)
        digest.update(f"w={window_size}|c={cluster_id}|s={side}|".encode())
        arr = np.asarray(list(centroid), dtype=np.float32)
        digest.update(np.round(arr, 3).tobytes())
        return f"novel_{side}_w{window_size}_{digest.hexdigest()}"
