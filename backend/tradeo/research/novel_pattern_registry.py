from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

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

    def upsert_candidate(self, db: Session, candidate: ClusterCandidate, run_id: int | None = None) -> DiscoveredPattern:
        pattern = db.query(DiscoveredPattern).filter(DiscoveredPattern.pattern_key == candidate.pattern_key).one_or_none()
        if pattern is None:
            pattern = DiscoveredPattern(pattern_key=candidate.pattern_key)
        metrics = candidate.metrics
        pattern.run_id = run_id
        pattern.name = candidate.name
        status = str(metrics.get("promotion_status", "lab" if candidate.validation_passed else "rejected"))
        try:
            pattern.status = DiscoveredPatternStatus(status)
        except ValueError:
            pattern.status = DiscoveredPatternStatus.REJECTED
        pattern.promotion_status = status
        pattern.side = candidate.side
        pattern.timeframe = candidate.timeframe
        pattern.window_size = candidate.window_size
        pattern.cluster_id = candidate.cluster_id
        pattern.sample_count = candidate.sample_count
        pattern.symbol_count = candidate.symbol_count
        pattern.year_count = candidate.year_count
        pattern.score = candidate.score
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

    @staticmethod
    def list_patterns(
        db: Session,
        limit: int = 100,
        status: str | None = None,
    ) -> list[DiscoveredPattern]:
        query = db.query(DiscoveredPattern).order_by(DiscoveredPattern.score.desc(), DiscoveredPattern.created_at.desc())
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
