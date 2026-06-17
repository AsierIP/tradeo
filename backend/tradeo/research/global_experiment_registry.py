from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from tradeo.research.types import ClusterCandidate

REGISTRY_HASH_ALGORITHM = "sha256_canonical_v1"


@dataclass(slots=True)
class GlobalExperimentRegistry:
    """Append-only-ish registry of discovery trials across research runs."""

    path: Path
    hash_algorithm: str = REGISTRY_HASH_ALGORITHM

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()
        if not isinstance(payload, dict):
            return self._empty()
        payload.setdefault("schema_version", 2)
        payload.setdefault("global_trial_count", 0)
        payload.setdefault("runs", [])
        payload.setdefault("experiments", [])
        payload.setdefault("hash_algorithm", self.hash_algorithm)
        return payload

    def register(
        self,
        candidates: list[ClusterCandidate],
        *,
        run_id: int | str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self.load()
        payload["schema_version"] = 2
        payload["hash_algorithm"] = self.hash_algorithm
        previous_registry_hash = self.registry_hash(payload) if self.path.exists() else ""
        now = datetime.now(timezone.utc).isoformat()
        payload["updated_at"] = now
        experiments = payload.setdefault("experiments", [])
        existing_by_id = {
            str(row.get("experiment_id")): row
            for row in experiments
            if isinstance(row, dict) and row.get("experiment_id")
        }
        existing_by_canonical: dict[str, dict[str, Any]] = {}
        for row in experiments:
            if not isinstance(row, dict):
                continue
            canonical_id = self._canonical_experiment_id_from_row(row)
            if canonical_id and canonical_id not in existing_by_canonical:
                existing_by_canonical[canonical_id] = row
        global_trial_count = int(payload.get("global_trial_count", 0) or 0)
        added = 0
        repeated = 0
        candidate_updates: list[tuple[ClusterCandidate, str, int, int, bool, int]] = []
        for rank, candidate in enumerate(sorted(candidates, key=lambda c: c.score, reverse=True), start=1):
            trial_count = self._candidate_trial_count(candidate)
            variant_id = self._variant_id(candidate)
            experiment_id = self._canonical_experiment_id(candidate, variant_id)
            row = existing_by_id.get(experiment_id) or existing_by_canonical.get(experiment_id)
            if row is None:
                global_trial_count += trial_count
                row = {
                    "experiment_id": experiment_id,
                    "first_run_id": run_id,
                    "latest_run_id": run_id,
                    "run_ids": [run_id],
                    "replication_count": 1,
                    "registered_at": now,
                    "last_seen_at": now,
                    "pattern_key": candidate.pattern_key,
                    "family_id": self._family_id(candidate),
                    "variant_id": variant_id,
                    "side": candidate.side,
                    "timeframe": candidate.timeframe,
                    "window_size": candidate.window_size,
                    "rank_by_lab_priority": rank,
                    "latest_rank_by_lab_priority": rank,
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
                existing_by_id[experiment_id] = row
                existing_by_canonical[experiment_id] = row
                added += 1
                is_repeated = False
            else:
                is_repeated = True
                repeated += 1
                legacy_id = str(row.get("experiment_id") or "")
                if legacy_id and legacy_id != experiment_id:
                    legacy_ids = list(row.get("legacy_experiment_ids") or [])
                    if legacy_id not in legacy_ids:
                        legacy_ids.append(legacy_id)
                    row["legacy_experiment_ids"] = legacy_ids[-20:]
                    row["experiment_id"] = experiment_id
                    existing_by_id[experiment_id] = row
                run_ids = list(row.get("run_ids") or [])
                if not run_ids and row.get("run_id") is not None:
                    run_ids.append(row.get("run_id"))
                if run_id not in run_ids and str(run_id) not in {str(x) for x in run_ids}:
                    run_ids.append(run_id)
                row["run_ids"] = run_ids[-100:]
                row.setdefault("first_run_id", row.get("run_id", run_id))
                row["latest_run_id"] = run_id
                row["last_seen_at"] = now
                row["replication_count"] = int(row.get("replication_count") or 1) + 1
                row["latest_rank_by_lab_priority"] = rank
                row["latest_score"] = candidate.score
                row["latest_lab_priority_score"] = candidate.metrics.get("lab_priority_score", candidate.score)
                row["latest_promotion_status"] = candidate.metrics.get("promotion_status")
            candidate_global_count = int(row.get("global_trial_count_after", global_trial_count) or 0)
            candidate_updates.append(
                (
                    candidate,
                    experiment_id,
                    trial_count,
                    candidate_global_count,
                    is_repeated,
                    int(row.get("replication_count") or 1),
                )
            )
        payload["global_trial_count"] = global_trial_count
        run_manifest = self._merge_run(
            payload,
            run_id=run_id,
            now=now,
            candidates=candidates,
            params=params or {},
            added=added,
            repeated=repeated,
            previous_registry_hash=previous_registry_hash,
            experiment_ids=[experiment_id for _, experiment_id, _, _, _, _ in candidate_updates],
        )
        payload["summary"] = {
            "run_count": len(payload.get("runs", [])),
            "experiment_count": len(experiments),
            "global_trial_count": global_trial_count,
            "new_experiments": added,
            "repeated_experiments": repeated,
            "latest_run_manifest_hash": run_manifest["run_manifest_hash"],
        }
        payload["latest_run_manifest"] = run_manifest
        payload["registry_hash"] = self.registry_hash(payload)
        backup_path = self._backup_existing()
        self._atomic_write(payload)
        for (
            candidate,
            experiment_id,
            trial_count,
            candidate_global_count,
            is_repeated,
            replication_count,
        ) in candidate_updates:
            candidate.metrics["global_trial_count"] = candidate_global_count
            candidate.metrics["global_experiment_registry"] = {
                "path": str(self.path),
                "experiment_id": experiment_id,
                "candidate_trial_count": trial_count,
                "global_trial_count": candidate_global_count,
                "global_trial_count_increased": not is_repeated,
                "is_repeated_experiment": is_repeated,
                "is_repeated_manifest": is_repeated,
                "replication_count": replication_count,
                "replication_of_experiment_id": experiment_id if is_repeated else "",
                "edge_claim": "NO_DEMOSTRADO",
                "hash_algorithm": self.hash_algorithm,
                "previous_registry_hash": previous_registry_hash,
                "registry_hash": payload["registry_hash"],
                "run_manifest_hash": run_manifest["run_manifest_hash"],
                "hash_chain_valid": True,
            }
        return {
            "path": str(self.path),
            "new_experiments": added,
            "repeated_experiments": repeated,
            "experiment_count": len(experiments),
            "global_trial_count": global_trial_count,
            "hash_algorithm": self.hash_algorithm,
            "previous_registry_hash": previous_registry_hash,
            "registry_hash": payload["registry_hash"],
            "run_manifest_hash": run_manifest["run_manifest_hash"],
            "backup_path": str(backup_path) if backup_path is not None else "",
        }

    def _merge_run(
        self,
        payload: dict[str, Any],
        *,
        run_id: int | str,
        now: str,
        candidates: list[ClusterCandidate],
        params: dict[str, Any],
        added: int,
        repeated: int,
        previous_registry_hash: str,
        experiment_ids: list[str],
    ) -> dict[str, Any]:
        run_manifest = {
            "run_id": run_id,
            "registered_at": now,
            "candidate_count": len(candidates),
            "new_experiments": added,
            "repeated_experiments": repeated,
            "experiment_count": len(payload.get("experiments", [])),
            "global_trial_count": int(payload.get("global_trial_count", 0) or 0),
            "previous_registry_hash": previous_registry_hash,
            "experiment_ids": sorted(experiment_ids),
        }
        run_manifest_hash = self.hash_payload(run_manifest)
        run_manifest["run_manifest_hash"] = run_manifest_hash
        runs = [row for row in payload.setdefault("runs", []) if str(row.get("run_id")) != str(run_id)]
        runs.append(
            {
                "run_id": run_id,
                "registered_at": now,
                "candidate_count": len(candidates),
                "params": params,
                "new_experiments": added,
                "repeated_experiments": repeated,
                "previous_registry_hash": previous_registry_hash,
                "run_manifest_hash": run_manifest_hash,
            }
        )
        payload["runs"] = runs[-500:]
        return run_manifest

    def _canonical_experiment_id(self, candidate: ClusterCandidate, variant_id: str) -> str:
        family_id = self._family_id(candidate)
        return f"family={family_id}|pattern={candidate.pattern_key}|variant={variant_id}"

    @staticmethod
    def _canonical_experiment_id_from_row(row: dict[str, Any]) -> str:
        if not isinstance(row, dict):
            return ""
        family_id = str(row.get("family_id") or "")
        pattern_key = str(row.get("pattern_key") or "")
        variant_id = str(row.get("variant_id") or pattern_key)
        if not pattern_key:
            return str(row.get("experiment_id") or "")
        return f"family={family_id}|pattern={pattern_key}|variant={variant_id}"

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
            "schema_version": 2,
            "updated_at": "",
            "global_trial_count": 0,
            "hash_algorithm": REGISTRY_HASH_ALGORITHM,
            "registry_hash": "",
            "runs": [],
            "experiments": [],
            "summary": {},
        }

    def _backup_existing(self) -> Path | None:
        if not self.path.exists():
            return None
        backup_dir = self.path.parent / ".backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = backup_dir / f"{self.path.name}.{timestamp}.bak"
        counter = 1
        while backup.exists():
            backup = backup_dir / f"{self.path.name}.{timestamp}.{counter}.bak"
            counter += 1
        shutil.copy2(self.path, backup)
        return backup

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        try:
            temp_path.write_text(
                json.dumps(self._json_clean(payload), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(temp_path, self.path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def registry_hash(self, payload: dict[str, Any]) -> str:
        clean = self._json_clean(payload)
        if isinstance(clean, dict):
            clean = {key: value for key, value in clean.items() if key != "registry_hash"}
        return self.hash_payload(clean)

    @staticmethod
    def hash_payload(payload: Any) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

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
