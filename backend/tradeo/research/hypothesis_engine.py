from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tradeo.research.types import ClusterCandidate


@dataclass(slots=True)
class HypothesisEngine:
    """Create falsifiable market hypotheses from cluster evidence."""

    def build(self, candidate: ClusterCandidate) -> dict[str, Any]:
        metrics = candidate.metrics
        rule = self._rule(metrics, candidate)
        mechanism = self._mechanism(metrics)
        works_when = self._works_when(metrics)
        fails_when = self._fails_when(metrics)
        kill_criteria = self._kill_criteria(metrics)
        evidence = self._evidence(candidate)
        return {
            "version": "hypothesis_v1",
            "falsifiable": True,
            "pattern_key": candidate.pattern_key,
            "thesis": (
                f"{candidate.side} edge: when {rule}, the pattern should produce "
                f"positive replay-adjusted R before the death conditions trigger."
            ),
            "rule": rule,
            "causal_mechanism": mechanism,
            "works_when": works_when,
            "fails_when": fails_when,
            "kill_criteria": kill_criteria,
            "evidence_accumulated": evidence,
            "falsification_tests": [
                "rerun on fresh dates without changing thresholds",
                "rerun on expanded universe and require no top-3-symbol dependency",
                "opposite-side placebo must stay weaker than the selected side",
                "cost x2 and latency replay must keep expectancy above zero",
                "expected-fail buckets must remain excluded or improve with new evidence",
            ],
            "current_verdict": self._verdict(metrics, candidate.validation_passed),
        }

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
            "expectancy_r": metrics.get("expectancy_r"),
            "best_expectancy_r": metrics.get("best_expectancy_r"),
            "profit_factor": metrics.get("profit_factor"),
            "out_of_sample_expectancy_r": metrics.get("out_of_sample_expectancy_r"),
            "walk_forward_positive_fold_rate": metrics.get("walk_forward_positive_fold_rate"),
            "purged_cv_positive_rate": metrics.get("purged_cv_positive_rate"),
            "expectancy_ci_low": metrics.get("expectancy_ci_low"),
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
