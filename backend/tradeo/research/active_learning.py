from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tradeo.research.types import ClusterCandidate


@dataclass(slots=True)
class ActiveLearningAgenda:
    """Prioritize the next autonomous experiments after discovery."""

    max_items: int = 20

    def build(
        self,
        candidates: list[ClusterCandidate],
        *,
        memory_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        experiments: list[dict[str, Any]] = []
        for candidate in candidates:
            experiments.extend(self._candidate_experiments(candidate))
        experiments.extend(self._family_experiments(memory_summary or {}))
        experiments = sorted(
            experiments,
            key=lambda row: (float(row.get("priority", 0.0)), str(row.get("pattern_key", ""))),
            reverse=True,
        )[: self.max_items]
        for rank, experiment in enumerate(experiments, start=1):
            experiment["rank"] = rank
        counts: dict[str, int] = {}
        for experiment in experiments:
            kind = str(experiment.get("kind", "unknown"))
            counts[kind] = counts.get(kind, 0) + 1
        return {
            "method": "deterministic_active_learning_agenda_v1",
            "experiment_count": len(experiments),
            "kind_counts": counts,
            "experiments": experiments,
        }

    def _candidate_experiments(self, candidate: ClusterCandidate) -> list[dict[str, Any]]:
        metrics = candidate.metrics
        rows: list[dict[str, Any]] = []
        eig = float(
            metrics.get(
                "registry_expected_information_gain",
                metrics.get("expected_information_gain", 0.0),
            )
            or 0.0
        )
        challenge = metrics.get("adversarial_challenge", {})
        challenge_score = float(challenge.get("challenge_score", 0.0)) if isinstance(challenge, dict) else 0.0
        replay = metrics.get("market_replay", {})
        replay_expectancy = float(replay.get("expected_expectancy_r", 0.0)) if isinstance(replay, dict) else 0.0
        causal = metrics.get("causal_invariance", {})
        invariance = float(causal.get("invariance_score", 0.0)) if isinstance(causal, dict) else 0.0
        novelty = float(metrics.get("registry_novelty_score", metrics.get("novelty_score", 0.0)) or 0.0)
        base_quality = max(0.0, float(metrics.get("best_expectancy_r", 0.0))) + max(0.0, replay_expectancy)
        if candidate.sample_count < 120 and base_quality > 0:
            rows.append(
                self._row(
                    candidate,
                    kind="rare_promising",
                    priority=base_quality * 0.45 + novelty * 0.30 + challenge_score * 0.25,
                    question="Does the edge survive expanded sampling?",
                    action="rerun with larger universe/period using same side/window and no threshold changes",
                )
            )
        if candidate.symbol_count < 12 or candidate.year_count < 3 or invariance < 0.55:
            rows.append(
                self._row(
                    candidate,
                    kind="missing_evidence",
                    priority=(1.0 - min(invariance, 1.0)) * 0.55 + base_quality * 0.30 + eig * 0.15,
                    question="Which regimes or symbols are under-evidenced?",
                    action="expand symbols/years and require invariant bucket pass before confirmation",
                )
            )
        family_variants = int((metrics.get("research_memory") or {}).get("known_variant_count", 1)) if isinstance(
            metrics.get("research_memory"),
            dict,
        ) else 1
        if family_variants >= 5 and novelty < 0.35:
            rows.append(
                self._row(
                    candidate,
                    kind="saturated_family",
                    priority=family_variants / 10.0 + (1.0 - novelty) * 0.25,
                    question="Is this family saturated enough to stop exploring variants?",
                    action="freeze low-novelty variants and spend budget on unrelated families",
                )
            )
        if eig > 0.25 or (novelty > 0.65 and challenge_score >= 0.45):
            rows.append(
                self._row(
                    candidate,
                    kind="high_information_gain",
                    priority=eig * 0.50 + novelty * 0.25 + challenge_score * 0.15 + base_quality * 0.10,
                    question="Can this pattern teach the graph something new?",
                    action="run targeted confirmation with extra adversarial shocks and per-regime report",
                )
            )
        return rows

    @staticmethod
    def _family_experiments(memory_summary: dict[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        decaying = memory_summary.get("decaying_families", []) if isinstance(memory_summary, dict) else []
        for family in decaying[:5]:
            if not isinstance(family, dict):
                continue
            rows.append(
                {
                    "kind": "resurrection_check",
                    "pattern_key": family.get("best_pattern_key", ""),
                    "family_key": family.get("family_key", ""),
                    "priority": round(float(family.get("decay_score", 0.0)) + 0.25, 5),
                    "question": "Is this family dead or regime-specific?",
                    "action": "rerun only in historically good regimes; retire if replay remains negative",
                    "reason": "memory graph marks family as decaying",
                }
            )
        return rows

    @staticmethod
    def _row(
        candidate: ClusterCandidate,
        *,
        kind: str,
        priority: float,
        question: str,
        action: str,
    ) -> dict[str, Any]:
        return {
            "kind": kind,
            "pattern_key": candidate.pattern_key,
            "family_key": (candidate.metrics.get("research_memory") or {}).get("family_key", "")
            if isinstance(candidate.metrics.get("research_memory"), dict)
            else "",
            "priority": round(float(max(0.0, priority)), 5),
            "question": question,
            "action": action,
            "reason": candidate.metrics.get("promotion_reason", ""),
        }
