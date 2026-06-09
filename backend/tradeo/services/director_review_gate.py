from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, joinedload

from tradeo.db.models import AuditLog, DiscoveredPattern, DiscoveredPatternStatus, Trade, TradeStatus


@dataclass(slots=True)
class DirectorReviewGate:
    min_closed_lab_trades: int = 10

    def refresh(self, db: Session) -> dict[str, Any]:
        patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(DiscoveredPattern.status != DiscoveredPatternStatus.PRODUCTION)
            .filter(DiscoveredPattern.status != DiscoveredPatternStatus.REJECTED)
            .all()
        )
        closed_trades = (
            db.query(Trade)
            .options(joinedload(Trade.signal))
            .filter(Trade.status == TradeStatus.CLOSED)
            .all()
        )
        marked: list[dict[str, Any]] = []
        for pattern in patterns:
            trades = self._closed_lab_trades_for_pattern(closed_trades, pattern.id)
            if len(trades) < self.min_closed_lab_trades:
                self._store_lab_execution_metrics(pattern, trades, eligible=False)
                continue
            metrics = self._store_lab_execution_metrics(pattern, trades, eligible=True)
            previous_status = (
                pattern.status.value if hasattr(pattern.status, "value") else str(pattern.status)
            )
            pattern.status = DiscoveredPatternStatus.DIRECTOR_REVIEW
            pattern.promotion_status = DiscoveredPatternStatus.DIRECTOR_REVIEW.value
            pattern.promotion_reason = (
                f"Lab closed trades reached Director review threshold: "
                f"{len(trades)} >= {self.min_closed_lab_trades}"
            )
            db.add(
                AuditLog(
                    actor="director_review_gate",
                    action="pattern_marked_for_director_review",
                    entity_type="discovered_pattern",
                    entity_id=str(pattern.id),
                    details_json={
                        "pattern_id": pattern.id,
                        "previous_status": previous_status,
                        "new_status": DiscoveredPatternStatus.DIRECTOR_REVIEW.value,
                        "lab_execution": metrics,
                    },
                )
            )
            marked.append({"pattern_id": pattern.id, "name": pattern.name, "lab_execution": metrics})
        db.commit()
        return {
            "min_closed_lab_trades": self.min_closed_lab_trades,
            "patterns_checked": len(patterns),
            "marked_for_director_review": len(marked),
            "marked": marked,
        }

    @staticmethod
    def _closed_lab_trades_for_pattern(trades: list[Trade], pattern_id: int) -> list[Trade]:
        matched: list[Trade] = []
        for trade in trades:
            signal = trade.signal
            if signal is None:
                continue
            metadata = signal.metadata_json or {}
            if metadata.get("entry_module") != "laboratory":
                continue
            if int(metadata.get("pattern_id") or 0) == pattern_id:
                matched.append(trade)
        return matched

    def _store_lab_execution_metrics(
        self,
        pattern: DiscoveredPattern,
        trades: list[Trade],
        *,
        eligible: bool,
    ) -> dict[str, Any]:
        r_values = [float(trade.r_multiple or 0.0) for trade in trades]
        wins = [r for r in r_values if r > 0]
        losses = [abs(r) for r in r_values if r < 0]
        profit = sum(wins)
        loss = sum(losses)
        expectancy = sum(r_values) / len(r_values) if r_values else 0.0
        profit_factor = profit / loss if loss > 0 else profit if profit > 0 else 0.0
        win_rate = len(wins) / len(r_values) if r_values else 0.0
        research_expectancy = float(pattern.best_expectancy_r or pattern.expectancy_r or 0.0)
        research_profit_factor = float(pattern.best_profit_factor or pattern.profit_factor or 0.0)
        metrics = {
            "closed_lab_trades": len(trades),
            "min_closed_lab_trades": self.min_closed_lab_trades,
            "eligible_for_director_review": eligible,
            "lab_expectancy_r": round(expectancy, 4),
            "lab_profit_factor": round(profit_factor, 4),
            "lab_win_rate": round(win_rate, 4),
            "research_expectancy_r": round(research_expectancy, 4),
            "research_profit_factor": round(research_profit_factor, 4),
            "expectancy_delta_r": round(expectancy - research_expectancy, 4),
            "profit_factor_delta": round(profit_factor - research_profit_factor, 4),
        }
        pattern.metrics_json = {**(pattern.metrics_json or {}), "lab_execution": metrics}
        return metrics
