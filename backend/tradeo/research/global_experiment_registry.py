from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from tradeo.research.types import ClusterCandidate


@dataclass(slots=True)
class GlobalExperimentRegistry:
    """Append-only-ish registry of discovery trials across research runs."""

    path: Path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()
        if not isinstance(payload, dict):
            return self._empty()
        payload.setdefault("schema_version", 1)
        payload.setdefault("global_trial_count", 0)
        payload.setdefault("runs", [])
        payload.setdefault("experiments", [])
        return payload

    def register(
        self,
        candidates: list[ClusterCandidate],
        *,
        run_id: int | str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self.load()
        now = datetime.now(timezone.utc).isoformat()
        payload["updated_at"] = now
        experiments = payload.setdefault("experiments", [])
        existing = {
            str(row.get("experiment_id")): row
            for row in experiments
            if isinstance(row, dict) and row.get("experiment_id")
        }
        global_trial_count = int(payload.get("global_trial_count", 0) or 0)
        added = 0
        for rank, candidate in enumerate(sorted(candidates, key=lambda c: c.score, reverse=True), start=1):
            trial_count = self._candidate_trial_count(candidate)
            variant_id = self._variant_id(candidate)
            experiment_id = f"run={run_id}|pattern={candidate.pattern_key}|variant={variant_id}"
            row = existing.get(experiment_id)
            if row is None:
                global_trial_count += trial_count
                row = {
                    "experiment_id": experiment_id,
                    "run_id": run_id,
                    "registered_at": now,
                    "pattern_key": candidate.pattern_key,
                    "family_id": self._family_id(candidate),
                    "variant_id": variant_id,
                    "rank_by_lab_priority": rank,
                    "candidate_trial_count": trial_count,
                    "global_trial_count_after": global_trial_count,
                    "fit_scope": candidate.metrics.get("fit_scope", {}),
                    "selection_split": candidate.metrics.get("selection_split", {}),
                    "score": candidate.score,
                    "lab_priority_score": candidate.metrics.get("lab_priority_score", candidate.score),
                    "promotion_status": candidate.metrics.get("promotion_status"),
                    "edge_claim": "NO_DEMOSTRADO",
                }
                experiments.append(row)
                existing[experiment_id] = row
                added += 1
            candidate.metrics["global_trial_count"] = int(row.get("global_trial_count_after", global_trial_count) or 0)
            candidate.metrics["global_experiment_registry"] = {
                "path": str(self.path),
                "experiment_id": experiment_id,
                "candidate_trial_count": trial_count,
                "global_trial_count": candidate.metrics["global_trial_count"],
                "edge_claim": "NO_DEMOSTRADO",
            }
        payload["global_trial_count"] = global_trial_count
        self._merge_run(payload, run_id=run_id, now=now, candidates=candidates, params=params or {})
        payload["summary"] = {
            "run_count": len(payload.get("runs", [])),
            "experiment_count": len(experiments),
            "global_trial_count": global_trial_count,
            "new_experiments": added,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._json_clean(payload), indent=2, sort_keys=True), encoding="utf-8")
        return {
            "path": str(self.path),
            "new_experiments": added,
            "experiment_count": len(experiments),
            "global_trial_count": global_trial_count,
        }

    @staticmethod
    def _merge_run(
        payload: dict[str, Any],
        *,
        run_id: int | str,
        now: str,
        candidates: list[ClusterCandidate],
        params: dict[str, Any],
    ) -> None:
        runs = [row for row in payload.setdefault("runs", []) if str(row.get("run_id")) != str(run_id)]
        runs.append(
            {
                "run_id": run_id,
                "registered_at": now,
                "candidate_count": len(candidates),
                "params": params,
            }
        )
        payload["runs"] = runs[-500:]

    @staticmethod
    def _candidate_trial_count(candidate: ClusterCandidate) -> int:
        metrics = candidate.metrics
        for key in ("real_variant_count", "multiple_testing_trials"):
            value = metrics.get(key)
            if value is not None:
                return max(1, int(value))
        return 1

    @staticmethod
    def _variant_id(candidate: ClusterCandidate) -> str:
        for key in ("variant_id", "variant_key", "registry_candidate_pattern_key"):
            value = candidate.metrics.get(key)
            if value:
                return str(value)
        return candidate.pattern_key

    @staticmethod
    def _family_id(candidate: ClusterCandidate) -> str:
        for key in ("family_id", "pattern_family_key", "research_family_key"):
            value = candidate.metrics.get(key)
            if value:
                return str(value)
        from tradeo.research.research_memory_graph import ResearchMemoryGraph

        return ResearchMemoryGraph.family_key(candidate)

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "schema_version": 1,
            "updated_at": "",
            "global_trial_count": 0,
            "runs": [],
            "experiments": [],
            "summary": {},
        }

    @staticmethod
    def _json_clean(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, dict):
            return {str(k): GlobalExperimentRegistry._json_clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [GlobalExperimentRegistry._json_clean(v) for v in value]
        if isinstance(value, tuple):
            return [GlobalExperimentRegistry._json_clean(v) for v in value]
        return value
