from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import blake2b
from pathlib import Path
from typing import Any

import numpy as np

from tradeo.research.types import ClusterCandidate


@dataclass(slots=True)
class ResearchMemoryGraph:
    """Persist cumulative research knowledge as JSON graph artifacts."""

    path: Path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty_graph()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty_graph()
        if not isinstance(payload, dict):
            return self._empty_graph()
        payload.setdefault("schema_version", 1)
        payload.setdefault("families", {})
        payload.setdefault("patterns", {})
        payload.setdefault("relations", [])
        payload.setdefault("runs", [])
        return payload

    def update(
        self,
        candidates: list[ClusterCandidate],
        *,
        run_id: int | str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        graph = self.load()
        now = datetime.now(timezone.utc).isoformat()
        graph["updated_at"] = now
        graph.setdefault("runs", []).append(
            {
                "run_id": run_id,
                "updated_at": now,
                "candidate_count": len(candidates),
                "params": params or {},
            }
        )
        graph["runs"] = graph["runs"][-100:]
        for candidate in candidates:
            self._merge_candidate(graph, candidate, run_id=run_id, now=now)
        self._merge_relations(graph, candidates)
        graph["summary"] = self.summary(graph)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._json_clean(graph), indent=2, sort_keys=True), encoding="utf-8")
        return graph["summary"]

    def _merge_candidate(
        self,
        graph: dict[str, Any],
        candidate: ClusterCandidate,
        *,
        run_id: int | str,
        now: str,
    ) -> None:
        family_key = self.family_key(candidate)
        metrics = candidate.metrics
        patterns = graph.setdefault("patterns", {})
        families = graph.setdefault("families", {})
        previous_pattern = patterns.get(candidate.pattern_key, {})
        previous_expectancy = float(previous_pattern.get("best_expectancy_r", metrics.get("best_expectancy_r", 0.0)) or 0.0)
        current_expectancy = float(metrics.get("best_expectancy_r", metrics.get("expectancy_r", 0.0)) or 0.0)
        pattern_decay = self._decay(previous_expectancy, current_expectancy)
        patterns[candidate.pattern_key] = {
            "pattern_key": candidate.pattern_key,
            "family_key": family_key,
            "name": candidate.name,
            "side": candidate.side,
            "timeframe": candidate.timeframe,
            "window_size": candidate.window_size,
            "cluster_id": candidate.cluster_id,
            "last_run_id": run_id,
            "last_seen_at": now,
            "score": round(float(candidate.score), 5),
            "lab_priority_score": float(metrics.get("lab_priority_score", candidate.score) or 0.0),
            "score_scope": "train_oos_walk_forward_no_descriptive_all",
            "best_expectancy_r": round(current_expectancy, 5),
            "replay_expectancy_r": self._nested_float(metrics, "market_replay", "expected_expectancy_r"),
            "challenge_score": self._nested_float(metrics, "adversarial_challenge", "challenge_score"),
            "invariance_score": self._nested_float(metrics, "causal_invariance", "invariance_score"),
            "lifecycle_state": (metrics.get("pattern_lifecycle") or {}).get("state", "discovered")
            if isinstance(metrics.get("pattern_lifecycle"), dict)
            else "discovered",
            "decay_score": round(pattern_decay, 5),
        }
        family = families.setdefault(
            family_key,
            {
                "family_key": family_key,
                "side": candidate.side,
                "timeframe": candidate.timeframe,
                "window_size": candidate.window_size,
                "first_seen_run_id": run_id,
                "first_seen_at": now,
                "variants": [],
                "regimes": {},
                "best_score": 0.0,
                "best_expectancy_r": 0.0,
                "best_pattern_key": "",
                "best_pattern_selection_scope": "lab_priority_score_no_descriptive_all",
                "decay_score": 0.0,
                "state": "discovered",
            },
        )
        variants = {str(v) for v in family.get("variants", [])}
        variants.add(candidate.pattern_key)
        family["variants"] = sorted(variants)
        family["variant_count"] = len(variants)
        family["last_seen_run_id"] = run_id
        family["last_seen_at"] = now
        if float(candidate.score) >= float(family.get("best_score", 0.0)):
            family["best_score"] = round(float(candidate.score), 5)
            family["best_pattern_key"] = candidate.pattern_key
            family["best_pattern_selection_scope"] = "lab_priority_score_no_descriptive_all"
        if current_expectancy >= float(family.get("best_expectancy_r", -1e9)):
            family["best_expectancy_r"] = round(current_expectancy, 5)
        family["decay_score"] = round(
            max(float(family.get("decay_score", 0.0)), pattern_decay, float(metrics.get("edge_decay_parameter_score", 0.0) or 0.0) * 0.5),
            5,
        )
        family["state"] = self._family_state(family, metrics, candidate.validation_passed)
        self._merge_regimes(family, metrics)
        metrics["research_memory"] = {
            "family_key": family_key,
            "family_id": family_key,
            "variant_id": str(metrics.get("variant_id") or metrics.get("variant_key") or candidate.pattern_key),
            "known_variant_count": int(family["variant_count"]),
            "family_state": family["state"],
            "family_decay_score": family["decay_score"],
            "best_pattern_key": family.get("best_pattern_key", candidate.pattern_key),
            "best_pattern_selection_scope": family.get(
                "best_pattern_selection_scope",
                "lab_priority_score_no_descriptive_all",
            ),
            "graph_path": str(self.path),
        }

    @staticmethod
    def _merge_regimes(family: dict[str, Any], metrics: dict[str, Any]) -> None:
        regimes = family.setdefault("regimes", {})
        causal = metrics.get("causal_invariance", {})
        if not isinstance(causal, dict):
            return
        for fail in causal.get("expected_fail_buckets", [])[:10]:
            if not isinstance(fail, dict):
                continue
            key = f"{fail.get('group')}:{fail.get('bucket')}"
            entry = regimes.setdefault(
                key,
                {"expected_fail_count": 0, "last_expectancy_r": 0.0, "reason": fail.get("reason", "")},
            )
            entry["expected_fail_count"] = int(entry.get("expected_fail_count", 0)) + 1
            entry["last_expectancy_r"] = fail.get("expectancy_r", 0.0)
            entry["reason"] = fail.get("reason", entry.get("reason", ""))

    @staticmethod
    def _merge_relations(graph: dict[str, Any], candidates: list[ClusterCandidate]) -> None:
        relations = graph.setdefault("relations", [])
        existing = {
            (str(row.get("source")), str(row.get("target")), str(row.get("type")))
            for row in relations
            if isinstance(row, dict)
        }
        for idx, left in enumerate(candidates):
            for right in candidates[idx + 1 :]:
                relation = ResearchMemoryGraph._relation(left, right)
                if not relation:
                    continue
                key = (relation["source"], relation["target"], relation["type"])
                if key in existing:
                    continue
                existing.add(key)
                relations.append(relation)
        graph["relations"] = relations[-1000:]

    @staticmethod
    def _relation(left: ClusterCandidate, right: ClusterCandidate) -> dict[str, Any] | None:
        left_family = ResearchMemoryGraph.family_key(left)
        right_family = ResearchMemoryGraph.family_key(right)
        similarity = ResearchMemoryGraph.centroid_similarity(left.centroid, right.centroid)
        if left_family == right_family:
            return {
                "source": left.pattern_key,
                "target": right.pattern_key,
                "type": "family_variant",
                "weight": round(float(max(similarity, 0.75)), 5),
                "reason": "same deterministic family key",
            }
        if similarity >= 0.92:
            relation_type = "opposite_side_placebo" if left.side != right.side else "near_duplicate"
            return {
                "source": left.pattern_key,
                "target": right.pattern_key,
                "type": relation_type,
                "weight": round(float(similarity), 5),
                "reason": "high centroid similarity",
            }
        return None

    @staticmethod
    def summary(graph: dict[str, Any]) -> dict[str, Any]:
        families = graph.get("families", {})
        patterns = graph.get("patterns", {})
        family_rows = [row for row in families.values() if isinstance(row, dict)]
        decaying = [
            {
                "family_key": row.get("family_key", ""),
                "best_pattern_key": row.get("best_pattern_key", ""),
                "decay_score": row.get("decay_score", 0.0),
                "variant_count": row.get("variant_count", 0),
            }
            for row in family_rows
            if float(row.get("decay_score", 0.0) or 0.0) >= 0.35
        ]
        states: dict[str, int] = {}
        for row in family_rows:
            state = str(row.get("state", "unknown"))
            states[state] = states.get(state, 0) + 1
        return {
            "family_count": len(families),
            "pattern_count": len(patterns),
            "relation_count": len(graph.get("relations", [])),
            "state_counts": states,
            "decaying_families": sorted(decaying, key=lambda row: float(row["decay_score"]), reverse=True)[:20],
        }

    @staticmethod
    def family_key(candidate: ClusterCandidate) -> str:
        existing = candidate.metrics.get("pattern_family_key") or candidate.metrics.get("research_family_key")
        if existing:
            return str(existing)
        digest = blake2b(digest_size=8)
        digest.update(f"{candidate.side}|{candidate.timeframe}|{candidate.window_size}|".encode())
        centroid = np.asarray(candidate.centroid, dtype=np.float32)
        digest.update(np.round(centroid, 2).tobytes())
        return f"family_{candidate.side}_{candidate.timeframe}_w{candidate.window_size}_{digest.hexdigest()}"

    @staticmethod
    def centroid_similarity(left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        left_arr = np.asarray(left, dtype=float)
        right_arr = np.asarray(right, dtype=float)
        if not np.isfinite(left_arr).all() or not np.isfinite(right_arr).all():
            return 0.0
        distance = float(np.linalg.norm(left_arr - right_arr) / max(1.0, np.sqrt(len(left_arr))))
        return float(1.0 / (1.0 + distance))

    @staticmethod
    def _decay(previous_expectancy: float, current_expectancy: float) -> float:
        if previous_expectancy <= 0:
            return 0.0
        return max(0.0, min(1.0, (previous_expectancy - current_expectancy) / max(previous_expectancy, 0.25)))

    @staticmethod
    def _family_state(family: dict[str, Any], metrics: dict[str, Any], validation_passed: bool) -> str:
        if float(family.get("decay_score", 0.0)) >= 0.65:
            return "decaying"
        challenge = metrics.get("adversarial_challenge", {})
        replay = metrics.get("market_replay", {})
        causal = metrics.get("causal_invariance", {})
        if not validation_passed or (isinstance(challenge, dict) and challenge.get("rejection_recommended")):
            return "challenged"
        if (
            isinstance(challenge, dict)
            and challenge.get("challenge_passed")
            and isinstance(replay, dict)
            and replay.get("passed")
            and isinstance(causal, dict)
            and causal.get("passed")
        ):
            return "confirmed"
        return "discovered"

    @staticmethod
    def _nested_float(metrics: dict[str, Any], key: str, child: str) -> float:
        value = metrics.get(key, {})
        if not isinstance(value, dict):
            return 0.0
        return round(float(value.get(child, 0.0) or 0.0), 5)

    @staticmethod
    def _empty_graph() -> dict[str, Any]:
        return {
            "schema_version": 1,
            "updated_at": "",
            "runs": [],
            "families": {},
            "patterns": {},
            "relations": [],
            "summary": {},
        }

    @staticmethod
    def _json_clean(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, dict):
            return {str(k): ResearchMemoryGraph._json_clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [ResearchMemoryGraph._json_clean(v) for v in value]
        if isinstance(value, tuple):
            return [ResearchMemoryGraph._json_clean(v) for v in value]
        return value
