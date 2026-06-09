from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Iterable

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler

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

    def discover(self, samples: list[WindowSample]) -> list[ClusterCandidate]:
        candidates: list[ClusterCandidate] = []
        for window_size in sorted({sample.window_size for sample in samples}):
            window_samples = [sample for sample in samples if sample.window_size == window_size]
            candidates.extend(self._cluster_window_size(window_size, window_samples))
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
            tested_trials = n_clusters * 2 * len(self.rr_levels or [1.5, 2.0, 2.5, 3.0, 4.0, 5.0])
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
            metrics["validation_method"] = "train_fit_forward_holdout"
            metrics["train_cutoff"] = train_samples[-1].end if train_samples else None
            metrics["holdout_start"] = holdout_samples[0].end if holdout_samples else None
            metrics["model_fit_sample_count"] = len(train_samples)
            metrics["model_holdout_sample_count"] = len(holdout_samples)
            metrics["operational_trigger"] = self._operational_trigger_metrics(cluster_samples, side)
            metrics["event_ledger"] = self._event_ledger(
                cluster_samples,
                train_samples=cluster_train_samples,
                holdout_samples=cluster_holdout_samples,
                side=side,
                rr=float(metrics.get("best_rr", self.target_r)),
            )
            metrics["event_ledger_count"] = len(metrics["event_ledger"])
            score = self._candidate_score(metrics)
            feature_summary = self._feature_summary(cluster_samples)
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
        hits = np.asarray([RewardRiskAnalyzer._simulate_sample(s, side, 4.0)[0] >= 4.0 for s in all_samples], dtype=bool)
        wins = outcomes[outcomes > 0]
        losses = outcomes[outcomes < 0]
        profit_factor = float(wins.sum() / abs(losses.sum())) if len(losses) else float(wins.sum() or 0.0)
        by_year = self._group_expectancy(all_samples, outcomes, key="year")
        by_symbol = self._group_expectancy(all_samples, outcomes, key="symbol")
        oos = self._split_metrics(holdout_samples, side, best_rr)
        in_sample_metrics = self._split_metrics(train_samples, side, best_rr)
        null_baseline = self._null_baseline(
            baseline_samples,
            cluster_size=len(train_samples),
            side=side,
            rr=best_rr,
            observed_expectancy=float(in_sample_metrics["expectancy_r"]),
            multiple_testing_trials=multiple_testing_trials,
        )
        stability_year = self._positive_group_fraction(by_year)
        stability_symbol = self._positive_group_fraction(by_symbol)
        diversity_score = min(1.0, len(by_symbol) / 20.0) * 0.55 + min(1.0, len(by_year) / 4.0) * 0.45
        stability_score = 0.40 * stability_year + 0.35 * stability_symbol + 0.25 * diversity_score
        avg_mae = float(np.mean(mae)) if len(mae) else 0.0
        avg_mfe = float(np.mean(mfe)) if len(mfe) else 0.0
        return {
            "sample_count": len(all_samples),
            "train_sample_count": len(train_samples),
            "holdout_sample_count": len(holdout_samples),
            "symbol_count": len({s.symbol for s in all_samples}),
            "year_count": len({s.year for s in all_samples}),
            "expectancy_r": round(float(np.mean(outcomes)), 5) if len(outcomes) else 0.0,
            "median_r": round(float(np.median(outcomes)), 5) if len(outcomes) else 0.0,
            "win_rate": round(float(np.mean(outcomes > 0)), 5) if len(outcomes) else 0.0,
            "hit_4r_rate": round(float(np.mean(hits)), 5) if len(hits) else 0.0,
            "profit_factor": round(profit_factor, 5),
            "avg_mfe_r": round(avg_mfe, 5),
            "avg_mae_r": round(avg_mae, 5),
            "avg_execution_cost_r": float(best_rr_metrics.get("avg_execution_cost_r", 0.0))
            if isinstance(best_rr_metrics, dict)
            else 0.0,
            "mfe_mae_ratio": round(float(avg_mfe / max(avg_mae, 1e-9)), 5),
            "reward_risk_estimate": round(float(np.quantile(mfe, 0.60) / max(np.quantile(mae, 0.60), 1e-9)), 5)
            if len(mfe) and len(mae)
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
            "target_hit_rate": float(best_rr_metrics.get("target_hit_rate", 0.0)) if isinstance(best_rr_metrics, dict) else 0.0,
            "stop_hit_rate": float(best_rr_metrics.get("stop_hit_rate", 0.0)) if isinstance(best_rr_metrics, dict) else 0.0,
            "max_drawdown_r": float(best_rr_metrics.get("max_drawdown_r", 0.0)) if isinstance(best_rr_metrics, dict) else 0.0,
            "in_sample_expectancy_r": in_sample_metrics["expectancy_r"],
            "in_sample_profit_factor": in_sample_metrics["profit_factor"],
            "null_expectancy_r": null_baseline["expectancy_r"],
            "null_profit_factor": null_baseline["profit_factor"],
            "null_win_rate": null_baseline["win_rate"],
            "expectancy_lift_r": null_baseline["expectancy_lift_r"],
            "null_p_value": null_baseline["p_value"],
            "adjusted_p_value": null_baseline["adjusted_p_value"],
            "multiple_testing_trials": null_baseline["multiple_testing_trials"],
            "statistical_edge_passed": null_baseline["statistical_edge_passed"],
            "out_of_sample_expectancy_r": oos["expectancy_r"],
            "out_of_sample_profit_factor": oos["profit_factor"],
            "out_of_sample_win_rate": oos["win_rate"],
            "out_of_sample_max_drawdown_r": oos["max_drawdown_r"],
            "out_of_sample_sample_count": oos["sample_count"],
            "stability_year": round(stability_year, 5),
            "stability_symbol": round(stability_symbol, 5),
            "stability_score": round(float(stability_score), 5),
            "by_year_expectancy": by_year,
            "top_symbols_expectancy": dict(list(by_symbol.items())[:25]),
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
        cluster_size: int,
        side: Side,
        rr: float,
        observed_expectancy: float,
        multiple_testing_trials: int,
    ) -> dict[str, float | int | bool]:
        outcomes = np.asarray([RewardRiskAnalyzer._simulate_sample(s, side, rr)[0] for s in samples], dtype=float)
        if len(outcomes) == 0 or cluster_size <= 0:
            return {
                "expectancy_r": 0.0,
                "profit_factor": 0.0,
                "win_rate": 0.0,
                "expectancy_lift_r": observed_expectancy,
                "p_value": 1.0,
                "adjusted_p_value": 1.0,
                "multiple_testing_trials": max(1, int(multiple_testing_trials)),
                "statistical_edge_passed": False,
            }

        baseline = self._outcome_metrics(outcomes)
        draws = min(512, max(96, len(outcomes) * 2))
        seed = self._null_seed(side, rr, cluster_size, len(outcomes))
        rng = np.random.default_rng(seed)
        draw_size = min(cluster_size, len(outcomes))
        random_means = []
        for _ in range(draws):
            idxs = rng.choice(len(outcomes), size=draw_size, replace=False)
            random_means.append(float(np.mean(outcomes[idxs])))
        p_value = (1 + sum(1 for mean in random_means if mean >= observed_expectancy)) / (draws + 1)
        trial_count = max(1, int(multiple_testing_trials))
        adjusted_p = min(1.0, p_value * trial_count)
        expectancy_lift = observed_expectancy - float(baseline["expectancy_r"])
        return {
            "expectancy_r": baseline["expectancy_r"],
            "profit_factor": baseline["profit_factor"],
            "win_rate": baseline["win_rate"],
            "expectancy_lift_r": round(expectancy_lift, 5),
            "p_value": round(float(p_value), 5),
            "adjusted_p_value": round(float(adjusted_p), 5),
            "multiple_testing_trials": trial_count,
            "statistical_edge_passed": adjusted_p <= 0.25 and expectancy_lift > 0,
        }

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
        for sample in sorted(samples, key=lambda s: s.end)[: self.event_ledger_limit]:
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
                    "target_bar": target_bar,
                    "stop_bar": stop_bar,
                    "execution_cost_r": round(float(sample.outcome.execution_cost_r), 5),
                    "entry_trigger_score": round(float(sample.features.get(f"{side}_entry_trigger_score", 0.0)), 5),
                }
            )
        return ledger

    @staticmethod
    def _split_metrics(samples: list[WindowSample], side: Side, rr: float) -> dict[str, float | int]:
        outcomes = np.asarray([RewardRiskAnalyzer._simulate_sample(s, side, rr)[0] for s in samples], dtype=float)
        if len(outcomes) == 0:
            return {"sample_count": 0, "expectancy_r": 0.0, "profit_factor": 0.0, "win_rate": 0.0, "max_drawdown_r": 0.0}
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
        expectancy = float(metrics.get("in_sample_expectancy_r", metrics.get("expectancy_r", 0.0)))
        pf = min(float(metrics.get("in_sample_profit_factor", metrics.get("profit_factor", 0.0))), 8.0)
        hit_rate = float(metrics.get("target_hit_rate", metrics.get("hit_4r_rate", 0.0)))
        stability = float(metrics.get("stability_score", 0.0))
        return expectancy * 2.0 + pf * 0.15 + hit_rate * 1.5 + stability * 0.7

    @staticmethod
    def _candidate_score(metrics: dict[str, object]) -> float:
        expectancy = max(0.0, float(metrics.get("expectancy_r", 0.0)))
        pf = min(float(metrics.get("profit_factor", 0.0)), 8.0) / 8.0
        hit = float(metrics.get("target_hit_rate", metrics.get("hit_4r_rate", 0.0)))
        stability = float(metrics.get("stability_score", 0.0))
        oos = max(0.0, float(metrics.get("out_of_sample_expectancy_r", 0.0)))
        rr = min(float(metrics.get("best_rr", metrics.get("reward_risk_estimate", 0.0))), 8.0) / 8.0
        operational = metrics.get("operational_trigger", {})
        trigger_rate = float(operational.get("trigger_rate", 0.0)) if isinstance(operational, dict) else 0.0
        lift = min(max(0.0, float(metrics.get("expectancy_lift_r", 0.0))), 2.0)
        adjusted_p = min(max(float(metrics.get("adjusted_p_value", 1.0)), 0.0), 1.0)
        confidence = 1.0 - adjusted_p
        raw_score = (
            expectancy * 0.28
            + pf * 0.15
            + hit * 0.13
            + stability * 0.13
            + oos * 0.10
            + rr * 0.06
            + trigger_rate * 0.05
        )
        return raw_score * (0.45 + 0.55 * confidence) + lift * 0.05

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
