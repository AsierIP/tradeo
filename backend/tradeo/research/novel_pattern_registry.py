from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Any

import numpy as np
from sqlalchemy import insert
from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.db.models import (
    AuditLog,
    DiscoveredPattern,
    DiscoveredPatternExample,
    DiscoveredPatternMetric,
    DiscoveredPatternStatus,
)
from tradeo.research.types import ClusterCandidate
from tradeo.services.state_policy import is_legacy_promotion_state

DISCOVERY_BLOCKED_PROMOTION_STATES = {
    "approved",
    "live",
    "live_candidate",
    "paper_candidate",
    "paper_limited_candidate",
    "paper_extended_candidate",
    "premium_candidate",
    "production",
    "production_candidate",
}


@dataclass(slots=True)
class NovelPatternRegistry:
    """Persistence layer for newly discovered LAB patterns."""

    max_examples_per_pattern: int = 11
    similarity_threshold: float | None = None

    def __post_init__(self) -> None:
        if self.similarity_threshold is None:
            self.similarity_threshold = get_settings().discovery_registry_similarity_threshold

    def store_candidates(
        self,
        db: Session,
        candidates: list[ClusterCandidate],
        run_id: int | None = None,
        store_rejected: bool = True,
    ) -> list[DiscoveredPattern]:
        candidates_to_store = [
            candidate for candidate in candidates if candidate.validation_passed or store_rejected
        ]
        if not candidates_to_store:
            return []

        existing_by_key = self._existing_patterns_by_key(db, candidates_to_store)
        patterns_by_scope = self._existing_patterns_by_scope(db, candidates_to_store)
        stored: list[DiscoveredPattern] = []
        latest_examples_by_pattern: dict[int, tuple[DiscoveredPattern, ClusterCandidate]] = {}
        metric_snapshots: list[tuple[DiscoveredPattern, dict[str, Any]]] = []
        new_pattern_audits: list[tuple[DiscoveredPattern, dict[str, Any]]] = []

        with db.no_autoflush:
            for candidate in candidates_to_store:
                pattern, is_new_pattern, metrics_json = self._prepare_candidate(
                    db,
                    candidate,
                    run_id=run_id,
                    existing_by_key=existing_by_key,
                    patterns_by_scope=patterns_by_scope,
                )
                stored.append(pattern)
                latest_examples_by_pattern[id(pattern)] = (pattern, candidate)
                metric_snapshots.append((pattern, metrics_json))
                if is_new_pattern and pattern.status != DiscoveredPatternStatus.REJECTED:
                    new_pattern_audits.append((pattern, self._new_pattern_audit_details(pattern)))

        db.flush()
        latest_examples = list(latest_examples_by_pattern.values())
        pattern_ids = sorted({int(pattern.id) for pattern, _ in latest_examples if pattern.id})
        if pattern_ids:
            db.query(DiscoveredPatternExample).filter(
                DiscoveredPatternExample.pattern_id.in_(pattern_ids)
            ).delete(synchronize_session=False)
        audit_rows = [
            self._new_pattern_audit_row(pattern, details_json=details)
            for pattern, details in new_pattern_audits
        ]
        example_rows = [
            row
            for pattern, candidate in latest_examples
            for row in self._candidate_example_rows(pattern, candidate)
        ]
        metric_rows = [
            {"pattern_id": pattern.id, "split": "full", "metrics_json": metrics}
            for pattern, metrics in metric_snapshots
        ]
        if audit_rows:
            db.execute(insert(AuditLog), audit_rows)
        if example_rows:
            db.execute(insert(DiscoveredPatternExample), example_rows)
        if metric_rows:
            db.execute(insert(DiscoveredPatternMetric), metric_rows)

        db.commit()
        return stored

    def upsert_candidate(
        self,
        db: Session,
        candidate: ClusterCandidate,
        run_id: int | None = None,
    ) -> DiscoveredPattern:
        existing_by_key = self._existing_patterns_by_key(db, [candidate])
        patterns_by_scope = self._existing_patterns_by_scope(db, [candidate])
        pattern, is_new_pattern, metrics_json = self._prepare_candidate(
            db,
            candidate,
            run_id=run_id,
            existing_by_key=existing_by_key,
            patterns_by_scope=patterns_by_scope,
        )
        db.flush()
        # Replace examples with the latest representative set.
        db.query(DiscoveredPatternExample).filter(
            DiscoveredPatternExample.pattern_id == pattern.id
        ).delete()
        if is_new_pattern and pattern.status != DiscoveredPatternStatus.REJECTED:
            db.add(self._new_pattern_audit_log(pattern))
        self._add_candidate_examples(db, pattern, candidate)
        db.add(
            DiscoveredPatternMetric(
                pattern_id=pattern.id,
                split="full",
                metrics_json=metrics_json,
            )
        )
        return pattern

    def _prepare_candidate(
        self,
        db: Session,
        candidate: ClusterCandidate,
        *,
        run_id: int | None,
        existing_by_key: dict[str, DiscoveredPattern],
        patterns_by_scope: dict[tuple[str, str, int], list[DiscoveredPattern]],
    ) -> tuple[DiscoveredPattern, bool, dict[str, Any]]:
        pattern = existing_by_key.get(candidate.pattern_key)
        is_variant = False
        is_new_pattern = False
        if pattern is None:
            pattern, similarity = self._find_similar_pattern_from_scope(
                candidate,
                patterns_by_scope.get(self._scope_key(candidate), []),
            )
            if pattern is not None:
                is_variant = True
                candidate.metrics["registry_deduped"] = True
                candidate.metrics["registry_similarity"] = round(similarity, 6)
                candidate.metrics["registry_canonical_pattern_key"] = pattern.pattern_key
                candidate.metrics["registry_candidate_pattern_key"] = candidate.pattern_key
            else:
                pattern = DiscoveredPattern(pattern_key=candidate.pattern_key)
                is_new_pattern = True
                candidate.metrics["registry_deduped"] = False
                candidate.metrics["registry_similarity"] = 0.0
                candidate.metrics["registry_canonical_pattern_key"] = candidate.pattern_key
                candidate.metrics["registry_candidate_pattern_key"] = candidate.pattern_key
                existing_by_key[candidate.pattern_key] = pattern
        metrics = candidate.metrics
        drift = self._drift(pattern, candidate, is_variant=is_variant)
        registry_similarity = float(metrics.get("registry_similarity", 0.0))
        registry_novelty = max(0.0, min(1.0, 1.0 - registry_similarity))
        registry_eig = float(metrics.get("expected_information_gain", 0.0)) * (0.35 + 0.65 * registry_novelty)
        metrics["registry_novelty_score"] = round(registry_novelty, 6)
        metrics["registry_expected_information_gain"] = round(registry_eig, 6)
        metrics["registry_family_penalty"] = round(1.0 - (0.70 + 0.30 * registry_novelty), 6)
        metrics["registry_adjusted_score"] = round(
            float(candidate.score) * (0.70 + 0.30 * registry_novelty) + registry_eig * 0.04,
            5,
        )
        metrics["registry_score_scope"] = {
            "base": "lab_priority_score",
            "uses_descriptive_all": False,
            "novelty_adjustment": "registry_novelty_score",
            "expected_information_gain_adjustment": "registry_expected_information_gain",
        }
        pattern.run_id = run_id
        pattern.name = candidate.name
        raw_status = str(metrics.get("promotion_status", "lab" if candidate.validation_passed else "rejected"))
        status = self._canonical_promotion_status(
            raw_status,
            validation_passed=candidate.validation_passed,
            confirmation_recommended=bool(metrics.get("confirmation_recommended")),
        )
        if status != raw_status:
            metrics["legacy_promotion_status_blocked"] = raw_status
            metrics["runtime_promotion_blocked"] = True
            metrics["promotion_status"] = status
        try:
            pattern.status = DiscoveredPatternStatus(status)
        except ValueError:
            pattern.status = DiscoveredPatternStatus.REJECTED
        pattern.promotion_status = status
        pattern.side = candidate.side
        pattern.timeframe = candidate.timeframe
        pattern.window_size = candidate.window_size
        pattern.cluster_id = candidate.cluster_id
        if not pattern.pattern_family_key:
            pattern.pattern_family_key = self._family_key(candidate)
        if not pattern.canonical_pattern_key:
            pattern.canonical_pattern_key = pattern.pattern_key
        pattern.variant_key = candidate.pattern_key
        pattern.variant_count = max(1, int(pattern.variant_count or 1)) + (1 if is_variant else 0)
        pattern.drift_status = str(drift["status"])
        pattern.drift_score = float(drift["score"])
        metrics["pattern_family_key"] = pattern.pattern_family_key
        metrics["canonical_pattern_key"] = pattern.canonical_pattern_key
        metrics["variant_key"] = pattern.variant_key
        metrics["variant_count"] = pattern.variant_count
        metrics["drift_status"] = pattern.drift_status
        metrics["drift_score"] = pattern.drift_score
        pattern.sample_count = candidate.sample_count
        pattern.symbol_count = candidate.symbol_count
        pattern.year_count = candidate.year_count
        pattern.score = float(metrics.get("registry_adjusted_score", candidate.score))
        pattern.reward_risk_estimate = float(metrics.get("reward_risk_estimate", 0.0))
        pattern.expectancy_r = float(metrics.get("expectancy_r", 0.0))
        pattern.profit_factor = float(metrics.get("profit_factor", 0.0))
        pattern.win_rate = float(metrics.get("win_rate", 0.0))
        pattern.avg_mfe_r = float(metrics.get("avg_mfe_r", 0.0))
        pattern.avg_mae_r = float(metrics.get("avg_mae_r", 0.0))
        pattern.stability_score = float(metrics.get("stability_score", 0.0))
        pattern.out_of_sample_expectancy_r = float(metrics.get("out_of_sample_expectancy_r", 0.0))
        pattern.out_of_sample_profit_factor = float(metrics.get("out_of_sample_profit_factor", 0.0))
        pattern.best_rr = float(metrics.get("best_rr", 0.0))
        pattern.best_tested_rr = float(metrics.get("best_tested_rr", 0.0))
        pattern.best_expectancy_r = float(metrics.get("best_expectancy_r", 0.0))
        pattern.best_profit_factor = float(metrics.get("best_profit_factor", 0.0))
        pattern.best_win_rate = float(metrics.get("best_win_rate", 0.0))
        pattern.best_max_drawdown_r = float(metrics.get("best_max_drawdown_r", 0.0))
        pattern.preferred_rr_passed = bool(metrics.get("preferred_rr_passed", False))
        pattern.premium_rr_passed = bool(metrics.get("premium_rr_passed", False))
        pattern.promotion_reason = str(metrics.get("promotion_reason", ""))
        pattern.confirmation_status = str(metrics.get("confirmation_status", ""))
        if metrics.get("confirmation_recommended") and not pattern.confirmation_status:
            pattern.confirmation_status = "needs_confirmation"
        pattern.confirmation_priority_score = float(metrics.get("confirmation_priority_score", 0.0))
        pattern.confirmation_reason = str(metrics.get("confirmation_reason", ""))
        pattern.confirmation_next_action = str(metrics.get("confirmation_next_action", ""))
        pattern.rr_metrics_json = self._json_clean(metrics.get("rr_metrics", {}))
        pattern.rejection_reasons_json = self._json_clean(metrics.get("rejection_reasons", []))
        pattern.in_sample_expectancy_r = float(metrics.get("in_sample_expectancy_r", 0.0))
        pattern.in_sample_profit_factor = float(metrics.get("in_sample_profit_factor", 0.0))
        pattern.out_of_sample_win_rate = float(metrics.get("out_of_sample_win_rate", 0.0))
        pattern.out_of_sample_max_drawdown_r = float(metrics.get("out_of_sample_max_drawdown_r", 0.0))
        pattern.validation_passed = candidate.validation_passed
        pattern.validation_reasons_json = candidate.validation_reasons
        pattern.centroid_json = candidate.centroid
        metrics_json = self._json_clean(metrics)
        pattern.metrics_json = metrics_json
        pattern.feature_summary_json = self._json_clean(candidate.feature_summary)
        db.add(pattern)
        scope_key = self._scope_key(candidate)
        scope_patterns = patterns_by_scope.setdefault(scope_key, [])
        if all(existing is not pattern for existing in scope_patterns):
            scope_patterns.append(pattern)
            scope_patterns.sort(key=lambda row: float(row.score or 0.0), reverse=True)
        return pattern, is_new_pattern, metrics_json

    def _add_candidate_examples(
        self,
        db: Session,
        pattern: DiscoveredPattern,
        candidate: ClusterCandidate,
    ) -> None:
        for row in self._candidate_example_rows(pattern, candidate):
            db.add(DiscoveredPatternExample(**row))

    def _candidate_example_rows(
        self,
        pattern: DiscoveredPattern,
        candidate: ClusterCandidate,
    ) -> list[dict[str, Any]]:
        return [
            {
                "pattern_id": pattern.id,
                "symbol": str(example.get("symbol", "")),
                "timeframe": str(example.get("timeframe", candidate.timeframe)),
                "window_start": str(example.get("window_start", "")),
                "window_end": str(example.get("window_end", "")),
                "forward_end": str(example.get("forward_end", "")),
                "entry_price": float(example.get("entry_price", 0.0)),
                "risk_proxy": float(example.get("risk_proxy", 0.0)),
                "outcome_r": float(example.get("outcome_r", 0.0)),
                "mfe_r": float(example.get("mfe_r", 0.0)),
                "mae_r": float(example.get("mae_r", 0.0)),
                "similarity": float(example.get("similarity", 0.0)),
                "kind": str(example.get("kind", "typical")),
                "chart_json": self._json_clean(example.get("chart", {})),
                "features_json": self._json_clean(example.get("features", {})),
            }
            for example in candidate.examples[: self.max_examples_per_pattern]
        ]

    @staticmethod
    def _scope_key(candidate: ClusterCandidate) -> tuple[str, str, int]:
        return (str(candidate.side), str(candidate.timeframe), int(candidate.window_size))

    @staticmethod
    def _pattern_scope_key(pattern: DiscoveredPattern) -> tuple[str, str, int]:
        return (str(pattern.side), str(pattern.timeframe), int(pattern.window_size or 0))

    def _existing_patterns_by_key(
        self,
        db: Session,
        candidates: list[ClusterCandidate],
    ) -> dict[str, DiscoveredPattern]:
        pattern_keys = list(dict.fromkeys(candidate.pattern_key for candidate in candidates))
        if not pattern_keys:
            return {}
        return {
            pattern.pattern_key: pattern
            for pattern in db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.pattern_key.in_(pattern_keys))
            .all()
        }

    def _existing_patterns_by_scope(
        self,
        db: Session,
        candidates: list[ClusterCandidate],
    ) -> dict[tuple[str, str, int], list[DiscoveredPattern]]:
        scope_keys = list(dict.fromkeys(self._scope_key(candidate) for candidate in candidates))
        if not scope_keys:
            return {}
        patterns_by_scope: dict[tuple[str, str, int], list[DiscoveredPattern]] = {
            scope_key: [] for scope_key in scope_keys
        }
        for side, timeframe, window_size in scope_keys:
            patterns_by_scope[(side, timeframe, window_size)] = (
                db.query(DiscoveredPattern)
                .filter(DiscoveredPattern.side == side)
                .filter(DiscoveredPattern.timeframe == timeframe)
                .filter(DiscoveredPattern.window_size == window_size)
                .order_by(DiscoveredPattern.score.desc())
                .limit(250)
                .all()
            )
        return patterns_by_scope

    @staticmethod
    def _canonical_promotion_status(
        status: str,
        *,
        validation_passed: bool,
        confirmation_recommended: bool,
    ) -> str:
        if status in DISCOVERY_BLOCKED_PROMOTION_STATES or is_legacy_promotion_state(status):
            return "lab_candidate" if validation_passed else "rejected"
        if confirmation_recommended and status == "rejected":
            return "needs_confirmation"
        return status

    def _family_key(self, candidate: ClusterCandidate) -> str:
        digest = blake2b(digest_size=8)
        digest.update(f"{candidate.side}|{candidate.timeframe}|{candidate.window_size}|".encode())
        centroid = np.asarray(candidate.centroid, dtype=np.float32)
        digest.update(np.round(centroid, 2).tobytes())
        return f"family_{candidate.side}_{candidate.timeframe}_w{candidate.window_size}_{digest.hexdigest()}"

    @staticmethod
    def _drift(pattern: DiscoveredPattern, candidate: ClusterCandidate, *, is_variant: bool) -> dict[str, float | str]:
        if not is_variant and not pattern.id:
            return {"status": "stable", "score": 0.0}
        old_expectancy = float(pattern.best_expectancy_r or pattern.expectancy_r or 0.0)
        new_expectancy = float(candidate.metrics.get("best_expectancy_r", candidate.metrics.get("expectancy_r", 0.0)))
        delta = new_expectancy - old_expectancy
        score = delta / max(abs(old_expectancy), 0.25)
        if score <= -0.25:
            status = "degrading"
        elif score >= 0.25:
            status = "improving"
        else:
            status = "stable"
        return {"status": status, "score": round(float(score), 5)}

    def _find_similar_pattern(
        self,
        db: Session,
        candidate: ClusterCandidate,
    ) -> tuple[DiscoveredPattern | None, float]:
        patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.side == candidate.side)
            .filter(DiscoveredPattern.timeframe == candidate.timeframe)
            .filter(DiscoveredPattern.window_size == candidate.window_size)
            .order_by(DiscoveredPattern.score.desc())
            .limit(250)
            .all()
        )
        return self._find_similar_pattern_from_scope(candidate, patterns)

    def _find_similar_pattern_from_scope(
        self,
        candidate: ClusterCandidate,
        patterns: list[DiscoveredPattern],
    ) -> tuple[DiscoveredPattern | None, float]:
        threshold = float(self.similarity_threshold or 1.0)
        best_pattern: DiscoveredPattern | None = None
        best_similarity = 0.0
        for pattern in patterns:
            similarity = self._centroid_similarity(candidate.centroid, pattern.centroid_json)
            if similarity > best_similarity:
                best_pattern = pattern
                best_similarity = similarity
        if best_pattern is not None and best_similarity >= threshold:
            return best_pattern, best_similarity
        return None, 0.0

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

    @classmethod
    def _new_pattern_audit_log(
        cls,
        pattern: DiscoveredPattern,
        *,
        details_json: dict[str, Any] | None = None,
    ) -> AuditLog:
        details = dict(details_json) if details_json is not None else cls._new_pattern_audit_details(pattern)
        details["pattern_id"] = pattern.id
        return AuditLog(
            actor="pattern_discovery_lab",
            action="new_pattern_discovered",
            entity_type="discovered_pattern",
            entity_id=str(pattern.id),
            details_json=details,
        )

    @classmethod
    def _new_pattern_audit_row(
        cls,
        pattern: DiscoveredPattern,
        *,
        details_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        details = dict(details_json) if details_json is not None else cls._new_pattern_audit_details(pattern)
        details["pattern_id"] = pattern.id
        return {
            "actor": "pattern_discovery_lab",
            "action": "new_pattern_discovered",
            "entity_type": "discovered_pattern",
            "entity_id": str(pattern.id),
            "details_json": details,
        }

    @classmethod
    def _new_pattern_audit_details(cls, pattern: DiscoveredPattern) -> dict[str, Any]:
        timeframe = str(pattern.timeframe or "")
        lane = "intraday" if timeframe in {"1m", "2m", "3m", "5m", "10m", "15m", "30m", "60m"} else "daily"
        return {
            "schema_version": 1,
            "pattern_id": pattern.id,
            "pattern_key": pattern.pattern_key,
            "name": pattern.name,
            "status": cls._status_value(pattern.status),
            "promotion_status": pattern.promotion_status,
            "lane": lane,
            "timeframe": timeframe,
            "side": pattern.side,
            "window_size": pattern.window_size,
            "sample_count": pattern.sample_count,
            "symbol_count": pattern.symbol_count,
            "year_count": pattern.year_count,
            "score": round(float(pattern.score or 0.0), 5),
            "reward_risk_estimate": round(float(pattern.reward_risk_estimate or 0.0), 3),
            "expectancy_r": round(float(pattern.expectancy_r or 0.0), 4),
            "profit_factor": round(float(pattern.profit_factor or 0.0), 4),
            "win_rate": round(float(pattern.win_rate or 0.0), 4),
            "stability_score": round(float(pattern.stability_score or 0.0), 4),
            "out_of_sample_expectancy_r": round(float(pattern.out_of_sample_expectancy_r or 0.0), 4),
            "out_of_sample_profit_factor": round(float(pattern.out_of_sample_profit_factor or 0.0), 4),
            "quality": cls._quality(pattern),
        }

    @classmethod
    def _quality(cls, pattern: DiscoveredPattern) -> dict[str, Any]:
        status = cls._status_value(pattern.status)
        score = float(pattern.score or 0.0)
        expectancy = float(pattern.expectancy_r or 0.0)
        profit_factor = float(pattern.profit_factor or 0.0)
        reward_risk = float(pattern.reward_risk_estimate or 0.0)
        stability = float(pattern.stability_score or 0.0)
        oos_expectancy = float(pattern.out_of_sample_expectancy_r or 0.0)
        if status in {"production", "director_review"}:
            label = "alta"
        elif expectancy >= 0.45 and profit_factor >= 2.0 and reward_risk >= 4.0 and stability >= 0.6:
            label = "alta"
        elif expectancy >= 0.25 and profit_factor >= 1.5 and stability >= 0.45:
            label = "media"
        else:
            label = "baja"
        return {
            "label": label,
            "summary": (
                f"{label}: score={score:.3f}, expR={expectancy:.3f}, "
                f"PF={profit_factor:.2f}, RR={reward_risk:.2f}, "
                f"stability={stability:.2f}, OOS expR={oos_expectancy:.3f}"
            ),
        }

    @staticmethod
    def _status_value(status: DiscoveredPatternStatus | str) -> str:
        return status.value if isinstance(status, DiscoveredPatternStatus) else str(status)

    @staticmethod
    def list_patterns(
        db: Session,
        limit: int = 100,
        status: str | None = None,
    ) -> list[DiscoveredPattern]:
        query = db.query(DiscoveredPattern).order_by(
            DiscoveredPattern.score.desc(),
            DiscoveredPattern.created_at.desc(),
        )
        if status:
            try:
                query = query.filter(DiscoveredPattern.status == DiscoveredPatternStatus(status))
            except ValueError:
                query = query.filter(DiscoveredPattern.promotion_status == status)
        return query.limit(max(1, min(limit, 500))).all()

    @staticmethod
    def _json_clean(value: Any) -> Any:
        # SQLAlchemy JSON columns reject numpy scalars. Recursively convert them.
        try:
            import numpy as np
        except Exception:  # noqa: BLE001
            np = None  # type: ignore[assignment]
        if np is not None and isinstance(value, np.generic):
            return value.item()
        if isinstance(value, dict):
            return {str(k): NovelPatternRegistry._json_clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [NovelPatternRegistry._json_clean(v) for v in value]
        if isinstance(value, tuple):
            return [NovelPatternRegistry._json_clean(v) for v in value]
        return value
