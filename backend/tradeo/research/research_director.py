from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

from tradeo.core.config import Settings, get_settings
from tradeo.research.active_learning import ActiveLearningAgenda
from tradeo.research.global_experiment_registry import GlobalExperimentRegistry
from tradeo.research.hypothesis_engine import HypothesisEngine
from tradeo.research.research_memory_graph import ResearchMemoryGraph
from tradeo.research.types import ClusterCandidate, WindowSample


@dataclass(slots=True)
class ResearchDirector:
    """Autonomous research director for discovery completion.

    The director enriches candidates, updates JSON memory, writes paper-style
    artifacts and suggests lifecycle states. It never promotes to paper/live.
    """

    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def run(
        self,
        *,
        run_id: int | str,
        candidates: list[ClusterCandidate],
        samples: list[WindowSample] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        logger.info("Research Director: iniciando cierre autonomo del run {}", run_id)
        self._attach_nested_discovery_replay_contract(
            candidates,
            finalist_limit=settings.discovery_report_top_n,
        )
        experiment_registry = GlobalExperimentRegistry(settings.reports_path / "research" / "global_experiment_registry.json")
        experiment_registry_summary = experiment_registry.register(
            candidates,
            run_id=run_id,
            params=params or {},
        )
        hypothesis_engine = HypothesisEngine()
        for candidate in candidates:
            package = hypothesis_engine.build_package(candidate)
            candidate.metrics["research_hypothesis_package"] = package.to_dict()
            candidate.metrics["research_hypothesis"] = package.to_dict()
            candidate.metrics["pattern_lifecycle"] = self._lifecycle(candidate)

        graph = ResearchMemoryGraph(settings.reports_path / "research" / "research_memory_graph.json")
        memory_summary = graph.update(candidates, run_id=run_id, params=params or {})
        logger.info(
            "Research Director: memoria actualizada con {} familias y {} patrones",
            memory_summary.get("family_count", 0),
            memory_summary.get("pattern_count", 0),
        )

        for candidate in candidates:
            candidate.metrics["pattern_lifecycle"] = self._lifecycle(candidate)

        agenda = ActiveLearningAgenda(max_items=max(5, settings.discovery_report_top_n)).build(
            candidates,
            memory_summary=memory_summary,
        )
        self._attach_agenda(candidates, agenda)
        paper_paths = self._write_papers(run_id, candidates, agenda)
        summary = self._summary(
            run_id=run_id,
            candidates=candidates,
            samples=samples or [],
            memory_summary=memory_summary,
            agenda=agenda,
            paper_paths=paper_paths,
            graph_path=graph.path,
            experiment_registry_summary=experiment_registry_summary,
        )
        artifact_paths = self._write_director_artifacts(run_id, summary, candidates, agenda)
        summary["artifact_json_path"] = str(artifact_paths["json"])
        summary["artifact_markdown_path"] = str(artifact_paths["markdown"])
        for candidate in candidates:
            candidate.metrics["research_director"] = {
                "run_id": run_id,
                "summary_path": str(artifact_paths["json"]),
                "memory_graph_path": str(graph.path),
                "agenda_rank": self._agenda_rank(candidate, agenda),
                "paper_live_auto_promotion": False,
                "director_gate_required_for_paper_or_live": True,
                "global_experiment_registry_path": experiment_registry_summary.get("path"),
            }
        logger.info(
            "Research Director: artifacts escritos {} y {}",
            artifact_paths["json"],
            artifact_paths["markdown"],
        )
        return summary

    def _write_papers(
        self,
        run_id: int | str,
        candidates: list[ClusterCandidate],
        agenda: dict[str, Any],
    ) -> list[str]:
        settings = self.settings
        assert settings is not None
        papers_dir = settings.reports_path / "research" / "papers" / f"run_{run_id}"
        papers_dir.mkdir(parents=True, exist_ok=True)
        paths: list[str] = []
        top = sorted(candidates, key=lambda c: c.score, reverse=True)[: settings.discovery_report_top_n]
        for candidate in top:
            path = papers_dir / f"{self._safe_stem(candidate.pattern_key)}.md"
            path.write_text(self._paper_markdown(candidate, agenda), encoding="utf-8")
            candidate.metrics["research_paper_report_path"] = str(path)
            paths.append(str(path))
        return paths

    def _write_director_artifacts(
        self,
        run_id: int | str,
        summary: dict[str, Any],
        candidates: list[ClusterCandidate],
        agenda: dict[str, Any],
    ) -> dict[str, Path]:
        settings = self.settings
        assert settings is not None
        director_dir = settings.reports_path / "research" / "director"
        director_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_path = director_dir / f"run_{run_id}_director_{ts}.json"
        markdown_path = director_dir / f"run_{run_id}_director_{ts}.md"
        payload = {
            "summary": summary,
            "agenda": agenda,
            "patterns": [self._candidate_digest(candidate) for candidate in candidates],
        }
        json_path.write_text(json.dumps(self._json_clean(payload), indent=2, ensure_ascii=False), encoding="utf-8")
        markdown_path.write_text(self._director_markdown(summary, agenda, candidates), encoding="utf-8")
        return {"json": json_path, "markdown": markdown_path}

    @staticmethod
    def _summary(
        *,
        run_id: int | str,
        candidates: list[ClusterCandidate],
        samples: list[WindowSample],
        memory_summary: dict[str, Any],
        agenda: dict[str, Any],
        paper_paths: list[str],
        graph_path: Path,
        experiment_registry_summary: dict[str, Any],
    ) -> dict[str, Any]:
        lifecycle_counts: dict[str, int] = {}
        challenge_scores: list[float] = []
        replay_expectancies: list[float] = []
        for candidate in candidates:
            lifecycle = candidate.metrics.get("pattern_lifecycle", {})
            state = str(lifecycle.get("state", "unknown")) if isinstance(lifecycle, dict) else "unknown"
            lifecycle_counts[state] = lifecycle_counts.get(state, 0) + 1
            challenge = candidate.metrics.get("adversarial_challenge", {})
            if isinstance(challenge, dict):
                challenge_scores.append(float(challenge.get("challenge_score", 0.0)))
            replay = candidate.metrics.get("market_replay", {})
            if isinstance(replay, dict):
                replay_expectancies.append(float(replay.get("expected_expectancy_r", 0.0)))
        return {
            "run_id": run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "candidate_count": len(candidates),
            "sample_count": len(samples),
            "lifecycle_counts": lifecycle_counts,
            "avg_challenge_score": round(float(np.mean(challenge_scores)), 5) if challenge_scores else 0.0,
            "avg_replay_expectancy_r": round(float(np.mean(replay_expectancies)), 5)
            if replay_expectancies
            else 0.0,
            "memory_graph_path": str(graph_path),
            "memory_summary": memory_summary,
            "global_experiment_registry": experiment_registry_summary,
            "active_learning": {
                "experiment_count": agenda.get("experiment_count", 0),
                "kind_counts": agenda.get("kind_counts", {}),
                "top_experiments": agenda.get("experiments", [])[:10],
            },
            "paper_reports_written": len(paper_paths),
            "paper_report_paths": paper_paths,
            "paper_live_auto_promotion": False,
            "director_gate_required_for_paper_or_live": True,
        }

    @staticmethod
    def _attach_nested_discovery_replay_contract(
        candidates: list[ClusterCandidate],
        *,
        finalist_limit: int,
    ) -> None:
        finalists = {
            candidate.pattern_key: rank
            for rank, candidate in enumerate(
                sorted(candidates, key=lambda c: c.score, reverse=True)[: max(1, finalist_limit)],
                start=1,
            )
        }
        for candidate in candidates:
            rank = finalists.get(candidate.pattern_key)
            if rank is None:
                candidate.metrics["nested_discovery_replay"] = {
                    "status": "not_finalist",
                    "implemented": False,
                    "blocking": False,
                    "reason": "nested discovery replay contract applies to finalists only",
                }
                continue
            candidate.metrics["nested_discovery_replay"] = {
                "status": "blocked_contract",
                "implemented": False,
                "blocking": True,
                "finalist_rank": rank,
                "required_before": [
                    "edge_claim_upgrade",
                    "paper_candidate",
                    "live_candidate",
                ],
                "blocking_reason": (
                    "nested discovery replay for finalists is not implemented in this run; "
                    "edge_claim remains NO_DEMOSTRADO"
                ),
                "minimum_contract": {
                    "replay_original_discovery": "same params, frozen thresholds, fresh split",
                    "compare_selection": "finalist must reappear without descriptive_all metrics in selection",
                    "record": "selection_split, fit_scope, global_trial_count and event_ledger_hash",
                },
            }

    @staticmethod
    def _attach_agenda(candidates: list[ClusterCandidate], agenda: dict[str, Any]) -> None:
        by_pattern: dict[str, list[dict[str, Any]]] = {}
        for experiment in agenda.get("experiments", []):
            if not isinstance(experiment, dict):
                continue
            pattern_key = str(experiment.get("pattern_key", ""))
            by_pattern.setdefault(pattern_key, []).append(experiment)
        for candidate in candidates:
            experiments = by_pattern.get(candidate.pattern_key, [])
            candidate.metrics["active_learning"] = {
                "experiments": experiments[:5],
                "top_priority": float(experiments[0].get("priority", 0.0)) if experiments else 0.0,
                "next_action": str(experiments[0].get("action", "")) if experiments else "",
            }

    @staticmethod
    def _agenda_rank(candidate: ClusterCandidate, agenda: dict[str, Any]) -> int | None:
        for experiment in agenda.get("experiments", []):
            if isinstance(experiment, dict) and experiment.get("pattern_key") == candidate.pattern_key:
                rank = experiment.get("rank")
                return int(rank) if rank is not None else None
        return None

    @staticmethod
    def _lifecycle(candidate: ClusterCandidate) -> dict[str, Any]:
        metrics = candidate.metrics
        challenge = metrics.get("adversarial_challenge", {})
        replay = metrics.get("market_replay", {})
        causal = metrics.get("causal_invariance", {})
        memory = metrics.get("research_memory", {})
        replay_expectancy = float(replay.get("expected_expectancy_r", 0.0)) if isinstance(replay, dict) else 0.0
        challenge_score = float(challenge.get("challenge_score", 0.0)) if isinstance(challenge, dict) else 0.0
        invariance = float(causal.get("invariance_score", 0.0)) if isinstance(causal, dict) else 0.0
        decay_score = max(
            float(metrics.get("edge_decay_parameter_score", 0.0) or 0.0),
            float(memory.get("family_decay_score", 0.0) or 0.0) if isinstance(memory, dict) else 0.0,
        )
        rejection = bool(challenge.get("rejection_recommended", False)) if isinstance(challenge, dict) else False
        if decay_score >= 0.65 and replay_expectancy <= 0:
            state = "retired"
        elif decay_score >= 0.45:
            state = "decaying"
        elif not candidate.validation_passed or rejection:
            if replay_expectancy > 0.15 and challenge_score >= 0.50:
                state = "resurrectable"
            else:
                state = "challenged"
        elif replay_expectancy > 0 and challenge_score >= 0.55 and invariance >= 0.45:
            state = "confirmed"
        else:
            state = "discovered"
        return {
            "state": state,
            "allowed_states": [
                "discovered",
                "challenged",
                "confirmed",
                "decaying",
                "retired",
                "resurrectable",
            ],
            "suggestion_only": True,
            "paper_live_auto_promotion": False,
            "director_gate_required_for_paper_or_live": True,
            "reasons": {
                "validation_passed": candidate.validation_passed,
                "challenge_score": round(challenge_score, 5),
                "replay_expectancy_r": round(replay_expectancy, 5),
                "invariance_score": round(invariance, 5),
                "decay_score": round(decay_score, 5),
            },
        }

    @staticmethod
    def _candidate_digest(candidate: ClusterCandidate) -> dict[str, Any]:
        metrics = candidate.metrics
        return {
            "pattern_key": candidate.pattern_key,
            "name": candidate.name,
            "side": candidate.side,
            "score": candidate.score,
            "validation_passed": candidate.validation_passed,
            "promotion_status": metrics.get("promotion_status"),
            "lifecycle": metrics.get("pattern_lifecycle", {}),
            "hypothesis": metrics.get("research_hypothesis", {}),
            "hypothesis_package": metrics.get("research_hypothesis_package", {}),
            "nested_discovery_replay": metrics.get("nested_discovery_replay", {}),
            "global_experiment_registry": metrics.get("global_experiment_registry", {}),
            "market_replay": metrics.get("market_replay", {}),
            "adversarial_challenge": metrics.get("adversarial_challenge", {}),
            "causal_invariance": metrics.get("causal_invariance", {}),
            "foundation_teacher": metrics.get("foundation_teacher", {}),
            "research_memory": metrics.get("research_memory", {}),
            "active_learning": metrics.get("active_learning", {}),
            "paper_report_path": metrics.get("research_paper_report_path"),
        }

    @staticmethod
    def _paper_markdown(candidate: ClusterCandidate, agenda: dict[str, Any]) -> str:
        metrics = candidate.metrics
        hypothesis = metrics.get("research_hypothesis", {})
        replay = metrics.get("market_replay", {})
        challenge = metrics.get("adversarial_challenge", {})
        causal = metrics.get("causal_invariance", {})
        lifecycle = metrics.get("pattern_lifecycle", {})
        next_experiments = [
            exp
            for exp in agenda.get("experiments", [])
            if isinstance(exp, dict) and exp.get("pattern_key") == candidate.pattern_key
        ][:5]
        lines = [
            f"# Research Paper: {candidate.name}",
            "",
            "## Abstract",
            str(hypothesis.get("thesis", "")),
            "",
            "## Rule",
            str(hypothesis.get("rule", "")),
            "",
            "## Evidence",
            "```json",
            json.dumps(hypothesis.get("evidence_accumulated", {}), indent=2, ensure_ascii=False, default=str),
            "```",
            "",
            "## Hypothesis Package",
            f"- Edge claim: {hypothesis.get('edge_claim', 'NO_DEMOSTRADO')}",
            f"- Family: {hypothesis.get('family_id')}",
            f"- Variant: {hypothesis.get('variant_id')}",
            f"- Global trial count: {hypothesis.get('global_trial_count')}",
            f"- Event ledger hash: {hypothesis.get('event_ledger_hash')}",
            f"- Nested discovery replay: {hypothesis.get('nested_discovery_replay')}",
            "",
            "## Anti-Overfit",
            f"- Challenge score: {challenge.get('challenge_score') if isinstance(challenge, dict) else None}",
            f"- Challenge passed: {challenge.get('challenge_passed') if isinstance(challenge, dict) else None}",
            f"- Warnings: {challenge.get('warnings', []) if isinstance(challenge, dict) else []}",
            "",
            "## Regime",
            f"- Invariance score: {causal.get('invariance_score') if isinstance(causal, dict) else None}",
            f"- Expected fail buckets: {causal.get('expected_fail_buckets', []) if isinstance(causal, dict) else []}",
            "",
            "## Execution",
            f"- Replay expectancy: {replay.get('expected_expectancy_r') if isinstance(replay, dict) else None}R",
            f"- Fill ratio: {replay.get('avg_fill_ratio') if isinstance(replay, dict) else None}",
            f"- Latency bars: {replay.get('latency_bars') if isinstance(replay, dict) else None}",
            "",
            "## Risks",
            "\n".join(f"- {item}" for item in hypothesis.get("fails_when", [])),
            "",
            "## Death Conditions",
            "\n".join(f"- {item}" for item in hypothesis.get("kill_criteria", [])),
            "",
            "## Next Experiments",
            "\n".join(f"- {item.get('kind')}: {item.get('action')}" for item in next_experiments)
            or "- No active experiment queued",
            "",
            "## Lifecycle",
            f"- State suggestion: {lifecycle.get('state') if isinstance(lifecycle, dict) else None}",
            "- Paper/live auto-promotion: false",
            "- Director gate required: true",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _director_markdown(
        summary: dict[str, Any],
        agenda: dict[str, Any],
        candidates: list[ClusterCandidate],
    ) -> str:
        lines = [
            f"# Tradeo Research Director Run {summary['run_id']}",
            "",
            "## Summary",
            f"- Candidates: {summary['candidate_count']}",
            f"- Lifecycle counts: {summary['lifecycle_counts']}",
            f"- Avg challenge score: {summary['avg_challenge_score']}",
            f"- Avg replay expectancy: {summary['avg_replay_expectancy_r']}R",
            f"- Memory graph: {summary['memory_graph_path']}",
            f"- Global experiment registry: {summary.get('global_experiment_registry', {})}",
            f"- Paper reports: {summary['paper_reports_written']}",
            "- Paper/live auto-promotion: false",
            "- Director gate required: true",
            "",
            "## Active Learning Agenda",
        ]
        for experiment in agenda.get("experiments", [])[:20]:
            if not isinstance(experiment, dict):
                continue
            lines.append(
                f"- #{experiment.get('rank')} {experiment.get('kind')} "
                f"{experiment.get('pattern_key')}: {experiment.get('action')}"
            )
        lines.extend(["", "## Top Patterns"])
        for candidate in sorted(candidates, key=lambda c: c.score, reverse=True)[:10]:
            lifecycle = candidate.metrics.get("pattern_lifecycle", {})
            challenge = candidate.metrics.get("adversarial_challenge", {})
            replay = candidate.metrics.get("market_replay", {})
            lines.append(
                f"- {candidate.name}: state={lifecycle.get('state') if isinstance(lifecycle, dict) else None}, "
                f"challenge={challenge.get('challenge_score') if isinstance(challenge, dict) else None}, "
                f"replay={replay.get('expected_expectancy_r') if isinstance(replay, dict) else None}R"
            )
        return "\n".join(lines)

    @staticmethod
    def _safe_stem(value: object) -> str:
        stem = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(value))
        return stem.strip("._")[:120] or "pattern"

    @staticmethod
    def _json_clean(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, dict):
            return {str(k): ResearchDirector._json_clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [ResearchDirector._json_clean(v) for v in value]
        if isinstance(value, tuple):
            return [ResearchDirector._json_clean(v) for v in value]
        return value
