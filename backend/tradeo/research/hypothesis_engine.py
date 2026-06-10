from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from tradeo.research.types import ClusterCandidate, HypothesisPackage, freeze_json


@dataclass(slots=True)
class HypothesisEngine:
    """Create falsifiable market hypotheses from cluster evidence."""

    def build(self, candidate: ClusterCandidate) -> dict[str, Any]:
        return self.build_package(candidate).to_dict()

    def build_package(self, candidate: ClusterCandidate) -> HypothesisPackage:
        metrics = candidate.metrics
        rule = self._rule(metrics, candidate)
        mechanism = self._mechanism(metrics)
        works_when = self._works_when(metrics)
        fails_when = self._fails_when(metrics)
        kill_criteria = self._kill_criteria(metrics)
        evidence = self._evidence(candidate)
        return HypothesisPackage(
            version="hypothesis_package_v1",
            pattern_key=candidate.pattern_key,
            family_id=self._family_id(candidate),
            variant_id=self._variant_id(candidate),
            edge_claim="NO_DEMOSTRADO",
            falsifiable=True,
            thesis=(
                f"{candidate.side} edge: when {rule}, the pattern should produce "
                "positive replay-adjusted R before the death conditions trigger. "
                "Edge claim remains NO_DEMOSTRADO until formal paper/live evidence exists."
            ),
            rule=rule,
            causal_mechanism=mechanism,
            works_when=tuple(works_when),
            fails_when=tuple(fails_when),
            kill_conditions=tuple(kill_criteria),
            selection_split=freeze_json(self._selection_split(metrics)),
            fit_scope=freeze_json(self._fit_scope(metrics)),
            train_metrics=freeze_json(self._train_metrics(metrics)),
            out_of_sample_metrics=freeze_json(self._out_of_sample_metrics(metrics)),
            walk_forward_metrics=freeze_json(self._walk_forward_metrics(metrics)),
            global_trial_count=int(metrics.get("global_trial_count", metrics.get("multiple_testing_trials", 0)) or 0),
            event_ledger_hash=self._event_ledger_hash(metrics),
            nested_discovery_replay=freeze_json(
                metrics.get(
                    "nested_discovery_replay",
                    {
                        "status": "blocked_contract",
                        "implemented": False,
                        "blocking_reason": "nested discovery replay required before any edge claim upgrade",
                    },
                )
            ),
            evidence_accumulated=freeze_json(evidence),
            falsification_tests=(
                "rerun on fresh dates without changing thresholds",
                "rerun on expanded universe and require no top-3-symbol dependency",
                "opposite-side placebo must stay weaker than the selected side",
                "cost x2 and latency replay must keep expectancy above zero",
                "expected-fail buckets must remain excluded or improve with new evidence",
            ),
            current_verdict=self._verdict(metrics, candidate.validation_passed),
        )

    @staticmethod
    def _rule(metrics: dict[str, Any], candidate: ClusterCandidate) -> str:
        human_rule = metrics.get("human_rule")
        if isinstance(human_rule, dict) and human_rule.get("rule"):
            return str(human_rule["rule"])
        return f"centroid-similar {candidate.side} setup on {candidate.timeframe} W{candidate.window_size}"

    @staticmethod
    def _mechanism(metrics: dict[str, Any]) -> str:
        rule = metrics.get("human_rule", {})
        conditions = rule.get("conditions", []) if isinstance(rule, dict) else []
        labels = {str(item.get("feature", "")) for item in conditions if isinstance(item, dict)}
        fragments: list[str] = []
        if any("volume" in label for label in labels):
            fragments.append("volume participation may reveal institutional urgency")
        if any("gap" in label for label in labels):
            fragments.append("gap/reclaim behavior can trap late sellers or buyers")
        if any("swing" in label for label in labels):
            fragments.append("swing structure suggests trend persistence or failed breakdown")
        if any(label in {"slope", "last_quarter_return", "cumulative_return"} for label in labels):
            fragments.append("price momentum may create continuation pressure")
        if any("drawdown" in label or "v_reversal" in label for label in labels):
            fragments.append("mean-reversion pressure may appear after local exhaustion")
        if not fragments:
            fragments.append("similar chart geometry clusters future paths with asymmetric payoff")
        return "; ".join(fragments)

    @staticmethod
    def _works_when(metrics: dict[str, Any]) -> list[str]:
        regime = metrics.get("causal_invariance", {})
        replay = metrics.get("market_replay", {})
        works = [
            f"best_rr={metrics.get('best_rr')} keeps expectancy positive",
            f"walk-forward positive rate={metrics.get('walk_forward_positive_fold_rate', 0.0)}",
        ]
        if isinstance(replay, dict):
            works.append(
                "market replay expected expectancy="
                f"{replay.get('expected_expectancy_r', 0.0)}R with fill ratio {replay.get('avg_fill_ratio', 0.0)}"
            )
        if isinstance(regime, dict):
            works.append(f"invariance score={regime.get('invariance_score', 0.0)}")
        return works

    @staticmethod
    def _fails_when(metrics: dict[str, Any]) -> list[str]:
        fails: list[str] = []
        causal = metrics.get("causal_invariance", {})
        if isinstance(causal, dict):
            for bucket in causal.get("expected_fail_buckets", [])[:6]:
                if isinstance(bucket, dict):
                    fails.append(
                        f"{bucket.get('group')}={bucket.get('bucket')} expectancy {bucket.get('expectancy_r')}R"
                    )
        replay = metrics.get("market_replay", {})
        if isinstance(replay, dict) and replay.get("passed") is False:
            fails.append("latency/partial-fill replay removes edge")
        adversarial = metrics.get("adversarial_challenge", {})
        if isinstance(adversarial, dict):
            fails.extend(str(reason) for reason in adversarial.get("rejection_reasons", [])[:4])
        return fails or ["failure buckets not yet isolated; require more evidence"]

    @staticmethod
    def _kill_criteria(metrics: dict[str, Any]) -> list[str]:
        return [
            "fresh OOS expectancy <= 0R in two consecutive comparable runs",
            "market_replay.expected_expectancy_r <= 0R after latency and partial fills",
            "adversarial_challenge.challenge_score < 0.55 or hard leakage/placebo failure",
            "causal_invariance shows top-3-symbol dependency or invariance_score < 0.45",
            "cost_stress_passed is false at required multiplier",
            "edge_decay_parameter_score > 0.75 unless new evidence resurrects the family",
        ]

    @staticmethod
    def _evidence(candidate: ClusterCandidate) -> dict[str, Any]:
        metrics = candidate.metrics
        return {
            "sample_count": candidate.sample_count,
            "symbol_count": candidate.symbol_count,
            "year_count": candidate.year_count,
            "best_rr": metrics.get("best_rr"),
            "train_expectancy_r": metrics.get("in_sample_expectancy_r", metrics.get("expectancy_r")),
            "descriptive_all_expectancy_r": metrics.get("descriptive_all_expectancy_r"),
            "best_expectancy_r": metrics.get("best_expectancy_r"),
            "train_profit_factor": metrics.get("in_sample_profit_factor", metrics.get("profit_factor")),
            "descriptive_all_profit_factor": metrics.get("descriptive_all_profit_factor"),
            "out_of_sample_expectancy_r": metrics.get("out_of_sample_expectancy_r"),
            "walk_forward_positive_fold_rate": metrics.get("walk_forward_positive_fold_rate"),
            "purged_cv_positive_rate": metrics.get("purged_cv_positive_rate"),
            "expectancy_ci_low": metrics.get("expectancy_ci_low"),
            "bootstrap_reality_proxy": metrics.get("bootstrap_reality_proxy", {}),
            "market_replay": metrics.get("market_replay", {}),
            "adversarial_challenge": {
                "challenge_score": (metrics.get("adversarial_challenge") or {}).get("challenge_score")
                if isinstance(metrics.get("adversarial_challenge"), dict)
                else None,
                "challenge_passed": (metrics.get("adversarial_challenge") or {}).get("challenge_passed")
                if isinstance(metrics.get("adversarial_challenge"), dict)
                else None,
            },
            "teacher": (metrics.get("foundation_teacher") or {}).get("pretraining_digest")
            if isinstance(metrics.get("foundation_teacher"), dict)
            else {},
        }

    @staticmethod
    def _selection_split(metrics: dict[str, Any]) -> dict[str, Any]:
        existing = metrics.get("selection_split")
        if isinstance(existing, dict):
            return existing
        return {
            "method": metrics.get("validation_method", "train_holdout"),
            "train_start": metrics.get("train_start"),
            "train_end": metrics.get("train_cutoff"),
            "holdout_start": metrics.get("holdout_start"),
            "holdout_end": metrics.get("holdout_end"),
            "train_sample_count": metrics.get("train_sample_count"),
            "holdout_sample_count": metrics.get("holdout_sample_count"),
        }

    @staticmethod
    def _fit_scope(metrics: dict[str, Any]) -> dict[str, Any]:
        existing = metrics.get("fit_scope")
        if isinstance(existing, dict):
            return existing
        return {
            "scaler": "train_only",
            "cluster_model": "train_only",
            "rr_selection": "train_only",
            "side_selection": "train_metrics_only",
            "lab_priority_score": "train_oos_walk_forward_only",
            "descriptive_all_feeds_scores": False,
        }

    @staticmethod
    def _train_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
        existing = metrics.get("train_metrics")
        if isinstance(existing, dict):
            return existing
        return {
            "sample_count": metrics.get("train_sample_count"),
            "expectancy_r": metrics.get("in_sample_expectancy_r"),
            "profit_factor": metrics.get("in_sample_profit_factor"),
            "best_rr": metrics.get("best_rr"),
            "best_expectancy_r": metrics.get("best_expectancy_r"),
            "best_profit_factor": metrics.get("best_profit_factor"),
            "best_win_rate": metrics.get("best_win_rate"),
        }

    @staticmethod
    def _out_of_sample_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
        existing = metrics.get("out_of_sample_metrics")
        if isinstance(existing, dict):
            return existing
        return {
            "sample_count": metrics.get("out_of_sample_sample_count", metrics.get("holdout_sample_count")),
            "expectancy_r": metrics.get("out_of_sample_expectancy_r"),
            "profit_factor": metrics.get("out_of_sample_profit_factor"),
            "win_rate": metrics.get("out_of_sample_win_rate"),
            "max_drawdown_r": metrics.get("out_of_sample_max_drawdown_r"),
        }

    @staticmethod
    def _walk_forward_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
        existing = metrics.get("walk_forward_metrics")
        if isinstance(existing, dict):
            return existing
        return {
            "fold_count": metrics.get("walk_forward_fold_count", 0),
            "positive_fold_rate": metrics.get("walk_forward_positive_fold_rate", 0.0),
            "avg_expectancy_r": metrics.get("walk_forward_avg_expectancy_r", 0.0),
            "min_expectancy_r": metrics.get("walk_forward_min_expectancy_r", 0.0),
            "folds": metrics.get("walk_forward_folds", []),
            "pooled": metrics.get("walk_forward_pooled", {}),
        }

    @staticmethod
    def _event_ledger_hash(metrics: dict[str, Any]) -> str:
        for key in ("event_ledger_hash", "event_ledger_sha256"):
            value = metrics.get(key)
            if value:
                return str(value)
        ledger = metrics.get("event_ledger")
        if isinstance(ledger, list):
            raw = json.dumps(ledger, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
            return hashlib.sha256(raw).hexdigest()
        return ""

    @staticmethod
    def _variant_id(candidate: ClusterCandidate) -> str:
        for key in ("variant_id", "variant_key", "registry_candidate_pattern_key"):
            value = candidate.metrics.get(key)
            if value:
                return str(value)
        return candidate.pattern_key

    @staticmethod
    def _family_id(candidate: ClusterCandidate) -> str:
        memory = candidate.metrics.get("research_memory")
        if isinstance(memory, dict) and memory.get("family_key"):
            return str(memory["family_key"])
        for key in ("family_id", "pattern_family_key", "research_family_key"):
            value = candidate.metrics.get(key)
            if value:
                return str(value)
        from tradeo.research.research_memory_graph import ResearchMemoryGraph

        return ResearchMemoryGraph.family_key(candidate)

    @staticmethod
    def _verdict(metrics: dict[str, Any], validation_passed: bool) -> str:
        adversarial = metrics.get("adversarial_challenge", {})
        replay = metrics.get("market_replay", {})
        causal = metrics.get("causal_invariance", {})
        if not validation_passed:
            return "challenged_or_rejected"
        if (
            isinstance(adversarial, dict)
            and adversarial.get("challenge_passed")
            and isinstance(replay, dict)
            and replay.get("passed")
            and isinstance(causal, dict)
            and causal.get("passed")
        ):
            return "confirmed_research_candidate_needs_director_gate"
        return "discovered_needs_more_evidence"
