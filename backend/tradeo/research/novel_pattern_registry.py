from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.db.models import (
    DiscoveredPattern,
    DiscoveredPatternExample,
    DiscoveredPatternMetric,
    DiscoveredPatternStatus,
)
from tradeo.research.types import ClusterCandidate


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
        stored: list[DiscoveredPattern] = []
        for candidate in candidates:
            if not candidate.validation_passed and not store_rejected:
                continue
            stored.append(self.upsert_candidate(db, candidate, run_id=run_id))
        db.commit()
        for pattern in stored:
            db.refresh(pattern)
        return stored

    def upsert_candidate(
        self,
        db: Session,
        candidate: ClusterCandidate,
        run_id: int | None = None,
    ) -> DiscoveredPattern:
        pattern = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.pattern_key == candidate.pattern_key)
            .one_or_none()
        )
        is_variant = False
        if pattern is None:
            pattern, similarity = self._find_similar_pattern(db, candidate)
            if pattern is not None:
                is_variant = True
                candidate.metrics["registry_deduped"] = True
                candidate.metrics["registry_similarity"] = round(similarity, 6)
                candidate.metrics["registry_canonical_pattern_key"] = pattern.pattern_key
                candidate.metrics["registry_candidate_pattern_key"] = candidate.pattern_key
            else:
                pattern = DiscoveredPattern(pattern_key=candidate.pattern_key)
                candidate.metrics["registry_deduped"] = False
                candidate.metrics["registry_similarity"] = 0.0
                candidate.metrics["registry_canonical_pattern_key"] = candidate.pattern_key
                candidate.metrics["registry_candidate_pattern_key"] = candidate.pattern_key
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
        pattern.run_id = run_id
        pattern.name = candidate.name
        status = str(metrics.get("promotion_status", "lab" if candidate.validation_passed else "rejected"))
        if metrics.get("confirmation_recommended") and status == "rejected":
            status = "needs_confirmation"
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
        pattern.metrics_json = self._json_clean(metrics)
        pattern.feature_summary_json = self._json_clean(candidate.feature_summary)
        db.add(pattern)
        db.flush()

        # Replace examples with the latest representative set.
        db.query(DiscoveredPatternExample).filter(DiscoveredPatternExample.pattern_id == pattern.id).delete()
        for example in candidate.examples[: self.max_examples_per_pattern]:
            db.add(
                DiscoveredPatternExample(
                    pattern_id=pattern.id,
                    symbol=str(example.get("symbol", "")),
                    timeframe=str(example.get("timeframe", candidate.timeframe)),
                    window_start=str(example.get("window_start", "")),
                    window_end=str(example.get("window_end", "")),
                    forward_end=str(example.get("forward_end", "")),
                    entry_price=float(example.get("entry_price", 0.0)),
                    risk_proxy=float(example.get("risk_proxy", 0.0)),
                    outcome_r=float(example.get("outcome_r", 0.0)),
                    mfe_r=float(example.get("mfe_r", 0.0)),
                    mae_r=float(example.get("mae_r", 0.0)),
                    similarity=float(example.get("similarity", 0.0)),
                    kind=str(example.get("kind", "typical")),
                    chart_json=self._json_clean(example.get("chart", {})),
                    features_json=self._json_clean(example.get("features", {})),
                )
            )
        db.add(
            DiscoveredPatternMetric(
                pattern_id=pattern.id,
                split="full",
                metrics_json=self._json_clean(metrics),
            )
        )
        return pattern

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
        threshold = float(self.similarity_threshold or 1.0)
        patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.side == candidate.side)
            .filter(DiscoveredPattern.timeframe == candidate.timeframe)
            .filter(DiscoveredPattern.window_size == candidate.window_size)
            .order_by(DiscoveredPattern.score.desc())
            .limit(250)
            .all()
        )
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
