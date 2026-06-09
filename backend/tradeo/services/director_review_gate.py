from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session, joinedload

from tradeo.db.models import AuditLog, DiscoveredPattern, DiscoveredPatternStatus, Trade, TradeStatus


@dataclass(slots=True)
class DirectorReviewGate:
    min_closed_lab_trades: int = 10
    min_lab_symbols: int = 3
    min_lab_trading_days: int = 3
    max_lab_drawdown_r: float = 4.0
    min_lab_profit_factor: float = 1.2
    min_lab_expectancy_r: float = 0.0
    min_baseline_edge_r: float = 0.05
    min_research_expectancy_ratio: float = 0.5

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
        blocked: list[dict[str, Any]] = []
        for pattern in patterns:
            trades = self._closed_lab_trades_for_pattern(closed_trades, pattern.id)
            baseline_trades = self._baseline_lab_trades_for_pattern(closed_trades, pattern.id)
            metrics = self._store_lab_execution_metrics(
                pattern,
                trades,
                baseline_trades=baseline_trades,
            )
            blockers = list(metrics["promotion_blockers"])
            if blockers:
                blocked.append(
                    {
                        "pattern_id": pattern.id,
                        "name": pattern.name,
                        "promotion_blockers": blockers,
                        "lab_execution": metrics,
                    }
                )
                continue
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
            "blocked": blocked,
        }

    @staticmethod
    def _closed_lab_trades_for_pattern(trades: list[Trade], pattern_id: int) -> list[Trade]:
        matched: list[Trade] = []
        for trade in trades:
            signal = trade.signal
            if signal is None:
                continue
            pattern = DirectorReviewGate._lab_pattern_id_for_trade(trade)
            if pattern is None:
                continue
            if pattern == pattern_id:
                matched.append(trade)
        return matched

    @staticmethod
    def _lab_pattern_id_for_trade(trade: Trade) -> int | None:
        signal = trade.signal
        if signal is None:
            return None
        metadata = signal.metadata_json or {}
        if metadata.get("entry_module") != "laboratory":
            return None
        try:
            return int(metadata.get("pattern_id") or 0)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _baseline_lab_trades_for_pattern(cls, trades: list[Trade], pattern_id: int) -> list[Trade]:
        baseline: list[Trade] = []
        for trade in trades:
            lab_pattern_id = cls._lab_pattern_id_for_trade(trade)
            if lab_pattern_id is not None and lab_pattern_id != pattern_id:
                baseline.append(trade)
        return baseline

    def _store_lab_execution_metrics(
        self,
        pattern: DiscoveredPattern,
        trades: list[Trade],
        *,
        baseline_trades: list[Trade],
    ) -> dict[str, Any]:
        r_values = [float(trade.r_multiple or 0.0) for trade in trades]
        wins = [r for r in r_values if r > 0]
        losses = [abs(r) for r in r_values if r < 0]
        profit = sum(wins)
        loss = sum(losses)
        expectancy = sum(r_values) / len(r_values) if r_values else 0.0
        profit_factor = profit / loss if loss > 0 else profit if profit > 0 else 0.0
        win_rate = len(wins) / len(r_values) if r_values else 0.0
        unique_symbols = len({trade.symbol for trade in trades})
        unique_days = len(
            {
                (trade.closed_at or trade.opened_at).date().isoformat()
                for trade in trades
                if trade.closed_at or trade.opened_at
            }
        )
        max_drawdown = _max_drawdown_r(r_values)
        baseline_r_values = [float(trade.r_multiple or 0.0) for trade in baseline_trades]
        baseline_expectancy = (
            sum(baseline_r_values) / len(baseline_r_values) if baseline_r_values else 0.0
        )
        research_expectancy = float(pattern.best_expectancy_r or pattern.expectancy_r or 0.0)
        research_profit_factor = float(pattern.best_profit_factor or pattern.profit_factor or 0.0)
        blockers = self._promotion_blockers(
            closed_trades=len(trades),
            unique_symbols=unique_symbols,
            unique_days=unique_days,
            max_drawdown=max_drawdown,
            expectancy=expectancy,
            profit_factor=profit_factor,
            baseline_expectancy=baseline_expectancy,
            research_expectancy=research_expectancy,
        )
        metrics = {
            "closed_lab_trades": len(trades),
            "min_closed_lab_trades": self.min_closed_lab_trades,
            "trades_remaining_for_director_review": max(
                0, self.min_closed_lab_trades - len(trades)
            ),
            "unique_lab_symbols": unique_symbols,
            "min_lab_symbols": self.min_lab_symbols,
            "unique_lab_days": unique_days,
            "min_lab_trading_days": self.min_lab_trading_days,
            "max_lab_drawdown_r": round(max_drawdown, 4),
            "max_allowed_lab_drawdown_r": self.max_lab_drawdown_r,
            "eligible_for_director_review": not blockers,
            "promotion_blockers": blockers,
            "lab_expectancy_r": round(expectancy, 4),
            "lab_profit_factor": round(profit_factor, 4),
            "lab_win_rate": round(win_rate, 4),
            "baseline_expectancy_r": round(baseline_expectancy, 4),
            "baseline_delta_r": round(expectancy - baseline_expectancy, 4),
            "min_baseline_edge_r": self.min_baseline_edge_r,
            "research_expectancy_r": round(research_expectancy, 4),
            "research_profit_factor": round(research_profit_factor, 4),
            "expectancy_delta_r": round(expectancy - research_expectancy, 4),
            "profit_factor_delta": round(profit_factor - research_profit_factor, 4),
            "by_entry_variant": self._bucket_metrics(
                trades,
                lambda trade: str(((trade.signal.metadata_json or {}) if trade.signal else {}).get("entry_variant_id") or "unknown"),
            ),
            "by_regime": self._bucket_metrics(
                trades,
                lambda trade: str(
                    ((((trade.signal.metadata_json or {}) if trade.signal else {}).get("regime") or {}).get("regime_key"))
                    or "unknown"
                ),
            ),
        }
        metrics["by_entry_variant_empty_reason"] = self._empty_bucket_reason(
            trades,
            "closed lab trades with signal.metadata_json.entry_variant_id",
        )
        metrics["by_regime_empty_reason"] = self._empty_bucket_reason(
            trades,
            "closed lab trades with signal.metadata_json.regime.regime_key",
        )
        metrics["best_entry_variant"] = self._best_bucket(metrics["by_entry_variant"])
        metrics["worst_entry_variant"] = self._worst_bucket(metrics["by_entry_variant"])
        metrics["best_regime"] = self._best_bucket(metrics["by_regime"])
        metrics["worst_regime"] = self._worst_bucket(metrics["by_regime"])
        metrics["director_recommendations"] = self._director_recommendations(
            trades=trades,
            blockers=blockers,
            expectancy=expectancy,
            profit_factor=profit_factor,
            baseline_expectancy=baseline_expectancy,
            research_expectancy=research_expectancy,
            by_entry_variant=metrics["by_entry_variant"],
            by_regime=metrics["by_regime"],
        )
        pattern.metrics_json = {**(pattern.metrics_json or {}), "lab_execution": metrics}
        return metrics

    @staticmethod
    def _bucket_metrics(trades: list[Trade], key_fn: Callable[[Trade], str]) -> dict[str, dict[str, Any]]:
        buckets: dict[str, list[float]] = {}
        for trade in trades:
            buckets.setdefault(key_fn(trade), []).append(float(trade.r_multiple or 0.0))
        result: dict[str, dict[str, Any]] = {}
        for key, values in sorted(buckets.items()):
            wins = [value for value in values if value > 0]
            losses = [abs(value) for value in values if value < 0]
            loss = sum(losses)
            result[key] = {
                "closed_trades": len(values),
                "expectancy_r": round(sum(values) / len(values), 4) if values else 0.0,
                "win_rate": round(len(wins) / len(values), 4) if values else 0.0,
                "profit_factor": round(sum(wins) / loss, 4) if loss > 0 else round(sum(wins), 4),
            }
        return result

    @staticmethod
    def _empty_bucket_reason(trades: list[Trade], required_data: str) -> str:
        if trades:
            return ""
        return (
            "no_closed_lab_trades: bucket performance is empty because there are no closed "
            f"laboratory paper trades yet; missing {required_data}."
        )

    @staticmethod
    def _best_bucket(buckets: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if not buckets:
            return {}
        key, metrics = max(
            buckets.items(),
            key=lambda item: (
                float(item[1].get("expectancy_r", 0.0) or 0.0),
                float(item[1].get("profit_factor", 0.0) or 0.0),
                int(item[1].get("closed_trades", 0) or 0),
            ),
        )
        return {"key": key, **metrics}

    @staticmethod
    def _worst_bucket(buckets: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if not buckets:
            return {}
        key, metrics = min(
            buckets.items(),
            key=lambda item: (
                float(item[1].get("expectancy_r", 0.0) or 0.0),
                float(item[1].get("profit_factor", 0.0) or 0.0),
                int(item[1].get("closed_trades", 0) or 0),
            ),
        )
        return {"key": key, **metrics}

    def _director_recommendations(
        self,
        *,
        trades: list[Trade],
        blockers: list[str],
        expectancy: float,
        profit_factor: float,
        baseline_expectancy: float,
        research_expectancy: float,
        by_entry_variant: dict[str, dict[str, Any]],
        by_regime: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        trades_remaining = max(0, self.min_closed_lab_trades - len(trades))
        if trades_remaining:
            recommendations.append(
                {
                    "action": "collect_closed_lab_trades",
                    "priority": "high",
                    "trades_remaining": trades_remaining,
                    "reason": (
                        f"needs {trades_remaining} more closed laboratory paper trades "
                        "before Director review can rely on execution evidence"
                    ),
                }
            )
        if not trades:
            recommendations.append(
                {
                    "action": "keep_research_only",
                    "priority": "high",
                    "reason": (
                        "no closed_lab_trades exist, so by_regime and by_entry_variant "
                        "performance cannot be ranked yet"
                    ),
                }
            )
            return recommendations
        if any(blocker.startswith("unique_lab_symbols_below_") for blocker in blockers) or any(
            blocker.startswith("unique_lab_days_below_") for blocker in blockers
        ):
            recommendations.append(
                {
                    "action": "diversify_paper_validation",
                    "priority": "medium",
                    "reason": "paper evidence is too concentrated by symbol or day",
                }
            )
        if expectancy <= baseline_expectancy + self.min_baseline_edge_r:
            recommendations.append(
                {
                    "action": "compare_against_baseline_before_promotion",
                    "priority": "high",
                    "reason": "lab expectancy does not clear the configured baseline edge",
                }
            )
        if research_expectancy > 0 and expectancy < research_expectancy * self.min_research_expectancy_ratio:
            recommendations.append(
                {
                    "action": "freeze_and_explain_research_decay",
                    "priority": "high",
                    "reason": "paper expectancy degraded materially versus research expectancy",
                }
            )
        if profit_factor < self.min_lab_profit_factor:
            recommendations.append(
                {
                    "action": "refine_or_reject_profit_factor",
                    "priority": "high",
                    "reason": "paper profit factor is below Director threshold",
                }
            )
        best_variant = self._best_bucket(by_entry_variant)
        worst_variant = self._worst_bucket(by_entry_variant)
        if best_variant and worst_variant and best_variant.get("key") != worst_variant.get("key"):
            recommendations.append(
                {
                    "action": "prioritize_entry_variant",
                    "priority": "medium",
                    "best_entry_variant": best_variant.get("key"),
                    "worst_entry_variant": worst_variant.get("key"),
                    "reason": "entry variants have materially different paper outcomes",
                }
            )
        best_regime = self._best_bucket(by_regime)
        worst_regime = self._worst_bucket(by_regime)
        if best_regime and worst_regime and best_regime.get("key") != worst_regime.get("key"):
            recommendations.append(
                {
                    "action": "gate_by_regime_until_confirmed",
                    "priority": "medium",
                    "best_regime": best_regime.get("key"),
                    "worst_regime": worst_regime.get("key"),
                    "reason": "paper performance differs by market regime",
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "action": "prepare_director_packet",
                    "priority": "medium",
                    "reason": "minimum paper evidence is present; still requires Director audit, not live trading",
                }
            )
        return recommendations

    def _promotion_blockers(
        self,
        *,
        closed_trades: int,
        unique_symbols: int,
        unique_days: int,
        max_drawdown: float,
        expectancy: float,
        profit_factor: float,
        baseline_expectancy: float,
        research_expectancy: float,
    ) -> list[str]:
        blockers: list[str] = []
        if closed_trades < self.min_closed_lab_trades:
            blockers.append(f"closed_lab_trades_below_{self.min_closed_lab_trades}")
        if unique_symbols < self.min_lab_symbols:
            blockers.append(f"unique_lab_symbols_below_{self.min_lab_symbols}")
        if unique_days < self.min_lab_trading_days:
            blockers.append(f"unique_lab_days_below_{self.min_lab_trading_days}")
        if max_drawdown > self.max_lab_drawdown_r:
            blockers.append(f"lab_drawdown_above_{self.max_lab_drawdown_r}r")
        if expectancy < self.min_lab_expectancy_r:
            blockers.append(f"lab_expectancy_below_{self.min_lab_expectancy_r}r")
        if profit_factor < self.min_lab_profit_factor:
            blockers.append(f"lab_profit_factor_below_{self.min_lab_profit_factor}")
        if expectancy < baseline_expectancy + self.min_baseline_edge_r:
            blockers.append("lab_expectancy_not_above_baseline")
        if research_expectancy > 0 and expectancy < research_expectancy * self.min_research_expectancy_ratio:
            blockers.append("lab_expectancy_degraded_vs_research")
        return blockers


def _max_drawdown_r(r_values: list[float]) -> float:
    peak = 0.0
    cumulative = 0.0
    max_drawdown = 0.0
    for value in r_values:
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
    return max_drawdown
