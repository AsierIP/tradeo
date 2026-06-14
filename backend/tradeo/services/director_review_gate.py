from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from sqlalchemy.orm import Session, joinedload

from tradeo.core.config import Settings
from tradeo.db.models import AuditLog, DiscoveredPattern, DiscoveredPatternStatus, Trade, TradeStatus
from tradeo.research.sequential_tests import (
    alpha_spending_evaluation,
    ks_two_sample,
    normal_msprt_edge,
    posterior_probability_edge,
    sprt_inferiority,
)
from tradeo.services.effective_sample import (
    effective_sample_summary,
    persist_effective_sample_weights,
)
from tradeo.services.execution_quality import (
    pattern_execution_quality_summary,
    persist_execution_quality,
)
from tradeo.services.implementation_shortfall import pattern_slippage_summary
from tradeo.services.evidence import (
    PAPER_FILL_EVIDENCE_TYPES,
    evidence_metadata_with_stored_columns,
    evidence_quality_from_metadata,
    evidence_type_from_metadata,
    is_director_review_paper_fill_evidence,
)
from tradeo.modules.fox_hunter.production_manifest import build_production_manifest
from tradeo.services.state_policy import REVIEW_TRIGGER_STATES


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
    # Sequential evaluation (informe §4.7): n=10 stays a *review trigger*; the
    # decision additionally uses a Bayesian posterior shrunk toward Research,
    # an SPRT fast-kill and a KS mechanism-change check.
    sequential_evaluation_enabled: bool = True
    posterior_min_probability: float = 0.80
    posterior_min_edge_r: float = 0.10
    sprt_alpha: float = 0.05
    sprt_beta: float = 0.20
    ks_mechanism_change_pvalue: float = 0.01
    # Implementation shortfall gate (informe §4.6): a research edge that costs
    # more than this median slippage_R to execute is not an executable edge.
    max_median_slippage_r: float = 0.10
    min_slippage_samples: int = 5
    min_effective_lab_trades: int = 25
    # Skip-rate evidence (Wave4-A): research/backtest skip accounting is
    # surfaced as Director evidence and a warning only — never a blocker, so
    # gate behavior is unchanged. A high skip_rate means reported expectancy
    # excludes many non-trades and executable coverage must be reviewed.
    skip_rate_warning_threshold: float = 0.25

    @classmethod
    def from_settings(cls, settings: Settings) -> "DirectorReviewGate":
        return cls(
            min_lab_symbols=settings.director_min_symbols,
            min_lab_trading_days=settings.director_min_days,
            sequential_evaluation_enabled=settings.director_sequential_evaluation_enabled,
            posterior_min_probability=settings.director_posterior_min_probability,
            posterior_min_edge_r=settings.director_posterior_min_edge_r,
            sprt_alpha=settings.director_sprt_alpha,
            sprt_beta=settings.director_sprt_beta,
            max_median_slippage_r=settings.director_max_median_slippage_r,
            min_slippage_samples=settings.director_min_slippage_samples,
            min_effective_lab_trades=settings.director_min_eff_trades,
        )

    def refresh(self, db: Session) -> dict[str, Any]:
        patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(DiscoveredPattern.status.in_(list(REVIEW_TRIGGER_STATES)))
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
            excluded_trades = self._excluded_lab_trades_for_pattern(closed_trades, pattern.id)
            metrics = self._store_lab_execution_metrics(
                pattern,
                trades,
                baseline_trades=baseline_trades,
                excluded_trades=excluded_trades,
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
                "Director review trigger reached, not production approval: "
                f"{len(trades)} normal IBKR paper fills >= {self.min_closed_lab_trades}"
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
            "review_trigger_min_closed_lab_trades": self.min_closed_lab_trades,
            "gate_scope": "director_review_trigger_not_production_approval",
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
            if pattern == pattern_id and DirectorReviewGate._counts_as_paper_fill(trade):
                matched.append(trade)
        return matched

    @staticmethod
    def _excluded_lab_trades_for_pattern(trades: list[Trade], pattern_id: int) -> list[Trade]:
        excluded: list[Trade] = []
        for trade in trades:
            pattern = DirectorReviewGate._lab_pattern_id_for_trade(trade)
            if pattern == pattern_id and not DirectorReviewGate._counts_as_paper_fill(trade):
                excluded.append(trade)
        return excluded

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

    @staticmethod
    def _counts_as_paper_fill(trade: Trade) -> bool:
        metadata = evidence_metadata_with_stored_columns(
            trade.metadata_json or {},
            evidence_type=trade.evidence_type,
            evidence_quality=trade.evidence_quality,
        )
        signal_metadata = trade.signal.metadata_json if trade.signal is not None else {}
        return is_director_review_paper_fill_evidence(
            metadata,
            signal_metadata=signal_metadata,
            trade_status=DirectorReviewGate._status_value(trade.status),
            broker_order_id=trade.broker_order_id,
        )

    @staticmethod
    def _status_value(status: Any) -> str:
        return str(status.value if hasattr(status, "value") else status)

    @classmethod
    def _baseline_lab_trades_for_pattern(cls, trades: list[Trade], pattern_id: int) -> list[Trade]:
        baseline: list[Trade] = []
        for trade in trades:
            lab_pattern_id = cls._lab_pattern_id_for_trade(trade)
            if (
                lab_pattern_id is not None
                and lab_pattern_id != pattern_id
                and cls._counts_as_paper_fill(trade)
            ):
                baseline.append(trade)
        return baseline

    def _store_lab_execution_metrics(
        self,
        pattern: DiscoveredPattern,
        trades: list[Trade],
        *,
        baseline_trades: list[Trade],
        excluded_trades: list[Trade],
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
        research_r_values = self._research_r_values(pattern)
        effective_sample = effective_sample_summary(trades)
        persist_effective_sample_weights(trades, effective_sample)
        effective_trades = float(effective_sample["n_eff"])
        slippage = pattern_slippage_summary(trades)
        execution_quality = pattern_execution_quality_summary(trades)
        persist_execution_quality(trades)
        sequential = self._sequential_evaluation(
            lab_r=r_values,
            research_r=research_r_values,
            research_expectancy=research_expectancy,
        )
        skip_accounting = self._research_skip_accounting(pattern)
        skip_rate_warning = bool(
            skip_accounting.get("available")
            and float(skip_accounting.get("skip_rate") or 0.0) >= self.skip_rate_warning_threshold
        )
        blockers = self._promotion_blockers(
            closed_trades=len(trades),
            effective_trades=effective_trades,
            unique_symbols=unique_symbols,
            unique_days=unique_days,
            max_drawdown=max_drawdown,
            expectancy=expectancy,
            profit_factor=profit_factor,
            baseline_expectancy=baseline_expectancy,
            research_expectancy=research_expectancy,
            slippage=slippage,
            sequential=sequential,
        )
        metrics = {
            "gate_scope": "director_review_trigger",
            "not_production_approval": True,
            "production_gate_required": "DirectorProductionGate",
            "evidence_count_policy": (
                "Only normal ibkr_paper_fill evidence counts. Shadow, near-miss, "
                "no_ibkr_order and degraded fallback rows are excluded."
            ),
            "closed_lab_trades": len(trades),
            "paper_fill_trades": len(trades),
            "effective_lab_trades": round(effective_trades, 4),
            "min_effective_lab_trades": self.min_effective_lab_trades,
            "effective_lab_trades_note": (
                "Weighted effective sample: each normal IBKR paper fill weighs "
                "1/cluster_size for its (symbol, trading day) cluster, so correlated "
                "same-symbol same-day fills count as one sample. Per-trade weights are "
                "persisted in trade.metadata_json.effective_sample."
            ),
            "effective_sample": effective_sample,
            "director_review_trigger_trades": len(trades),
            "min_closed_lab_trades": self.min_closed_lab_trades,
            "review_trigger_min_closed_lab_trades": self.min_closed_lab_trades,
            "excluded_lab_evidence_trades": len(excluded_trades),
            "excluded_evidence_type_counts": self._evidence_type_counts(excluded_trades),
            "excluded_evidence_quality_counts": self._evidence_quality_counts(excluded_trades),
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
            "implementation_shortfall": {
                key: value for key, value in slippage.items() if key != "per_trade"
            },
            "max_median_slippage_r": self.max_median_slippage_r,
            "execution_quality": {
                key: value
                for key, value in execution_quality.items()
                if key != "per_trade"
            },
            "execution_quality_note": (
                "Diagnostic only — not a promotion blocker. Per-trade reports are "
                "persisted in trade.metadata_json.execution_quality. No real-time "
                "microstructure feed backs these numbers (informe §4.3, no provider)."
            ),
            "sequential_evaluation": sequential,
            "research_skip_accounting": skip_accounting,
            "skip_rate_warning_threshold": self.skip_rate_warning_threshold,
            "research_skip_rate_warning": skip_rate_warning,
            "research_skip_accounting_note": (
                "Evidence only — never a promotion blocker. Skipped signals are "
                "true non-trades: research expectancy/profit factor exclude them, "
                "so a high skip_rate means the edge was measured on fewer "
                "executable signals than were generated."
            ),
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
            skip_accounting=skip_accounting,
            skip_rate_warning=skip_rate_warning,
        )
        pattern.metrics_json = {**(pattern.metrics_json or {}), "lab_execution": metrics}
        return metrics

    @staticmethod
    def _evidence_type_counts(trades: list[Trade]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for trade in trades:
            signal_metadata = trade.signal.metadata_json if trade.signal is not None else {}
            metadata = evidence_metadata_with_stored_columns(
                trade.metadata_json or {},
                evidence_type=trade.evidence_type,
                evidence_quality=trade.evidence_quality,
            )
            evidence_type = (
                evidence_type_from_metadata(
                    metadata,
                    status=DirectorReviewGate._status_value(trade.status),
                    signal_metadata=signal_metadata,
                    broker_order_id=trade.broker_order_id,
                )
                or "unknown"
            )
            counts[evidence_type] = counts.get(evidence_type, 0) + 1
        return counts

    @staticmethod
    def _evidence_quality_counts(trades: list[Trade]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for trade in trades:
            metadata = evidence_metadata_with_stored_columns(
                trade.metadata_json or {},
                evidence_type=trade.evidence_type,
                evidence_quality=trade.evidence_quality,
            )
            quality = evidence_quality_from_metadata(metadata)
            counts[quality] = counts.get(quality, 0) + 1
        return counts

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
            f"normal IBKR paper fill evidence rows yet; missing {required_data}."
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
        skip_accounting: dict[str, Any] | None = None,
        skip_rate_warning: bool = False,
    ) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        if skip_rate_warning and skip_accounting:
            recommendations.append(
                {
                    "action": "review_research_skip_rate",
                    "priority": "high",
                    "skip_rate": float(skip_accounting.get("skip_rate") or 0.0),
                    "signal_count": int(skip_accounting.get("signal_count") or 0),
                    "skipped_count": int(skip_accounting.get("skipped_count") or 0),
                    "skip_reason_counts": skip_accounting.get("skip_reason_counts") or {},
                    "reason": (
                        "research metrics report a high non-trade skip_rate; reported "
                        "expectancy and profit factor exclude skipped signals, so verify "
                        "executable signal coverage before relying on this evidence"
                    ),
                }
            )
        trades_remaining = max(0, self.min_closed_lab_trades - len(trades))
        if trades_remaining:
            recommendations.append(
                {
                    "action": "collect_closed_lab_trades",
                    "priority": "high",
                    "trades_remaining": trades_remaining,
                    "reason": (
                        f"needs {trades_remaining} more normal IBKR paper fills before "
                        "Director review can rely on execution evidence; this is not production approval"
                    ),
                }
            )
        if not trades:
            recommendations.append(
                {
                    "action": "keep_research_only",
                    "priority": "high",
                    "reason": (
                        "no closed_lab_trades normal IBKR paper fill evidence exists, so by_regime "
                        "and by_entry_variant performance cannot be ranked yet"
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
                    "reason": (
                        "minimum review-trigger paper evidence is present; this is not production "
                        "approval and still requires Director audit"
                    ),
                }
            )
        return recommendations

    def _promotion_blockers(
        self,
        *,
        closed_trades: int,
        effective_trades: float | None = None,
        unique_symbols: int,
        unique_days: int,
        max_drawdown: float,
        expectancy: float,
        profit_factor: float,
        baseline_expectancy: float,
        research_expectancy: float,
        slippage: dict[str, Any] | None = None,
        sequential: dict[str, Any] | None = None,
    ) -> list[str]:
        blockers: list[str] = []
        if closed_trades < self.min_closed_lab_trades:
            blockers.append(f"closed_lab_trades_below_{self.min_closed_lab_trades}")
        effective = float(closed_trades if effective_trades is None else effective_trades)
        if effective < self.min_effective_lab_trades:
            blockers.append(f"effective_lab_trades_below_{self.min_effective_lab_trades}")
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
        if slippage and slippage.get("count", 0) >= self.min_slippage_samples:
            median = slippage.get("median_slippage_r")
            if median is not None and float(median) > self.max_median_slippage_r:
                blockers.append(f"median_slippage_above_{self.max_median_slippage_r}r")
        if sequential and self.sequential_evaluation_enabled:
            sprt = sequential.get("sprt") or {}
            if sprt.get("decision") == "no_edge":
                blockers.append("sprt_concludes_no_edge")
            posterior = sequential.get("posterior") or {}
            probability = posterior.get("probability_edge")
            if (
                closed_trades >= self.min_closed_lab_trades
                and probability is not None
                and np.isfinite(probability)
                and float(probability) < self.posterior_min_probability
            ):
                blockers.append(
                    f"posterior_probability_below_{self.posterior_min_probability}"
                )
            ks = sequential.get("ks") or {}
            ks_p = ks.get("p_value")
            if (
                ks_p is not None
                and np.isfinite(ks_p)
                and float(ks_p) < self.ks_mechanism_change_pvalue
            ):
                blockers.append("lab_research_r_distribution_mismatch")
        return blockers

    @staticmethod
    def _normalized_skip_evidence(data: Any) -> dict[str, Any] | None:
        """Normalize research (`signal_count`/`skipped_count`) or backtest
        (`total_signals`/`skipped_signals`) skip accounting; None if absent."""
        if not isinstance(data, dict) or "skip_rate" not in data:
            return None
        signal_count = data.get("signal_count", data.get("total_signals"))
        skipped_count = data.get("skipped_count", data.get("skipped_signals"))
        if signal_count is None and skipped_count is None:
            return None
        evidence: dict[str, Any] = {
            "skip_rate": float(data.get("skip_rate") or 0.0),
            "signal_count": int(signal_count or 0),
            "skipped_count": int(skipped_count or 0),
        }
        reasons = data.get("skip_reason_counts")
        if isinstance(reasons, dict):
            evidence["skip_reason_counts"] = {
                str(reason): int(count or 0) for reason, count in reasons.items()
            }
        return evidence

    @classmethod
    def _research_skip_accounting(cls, pattern: DiscoveredPattern) -> dict[str, Any]:
        """Locate stored skip accounting for Director evidence.

        Reads what research/backtest runs already persisted on the pattern;
        never derives or invents numbers when the run predates skip accounting.
        """
        metrics = pattern.metrics_json or {}
        best_rr_key = f"{float(pattern.best_rr or 0.0):g}"
        rr_metric_sources = (
            ("pattern.rr_metrics_json", pattern.rr_metrics_json or {}),
            ("pattern.metrics_json.rr_metrics", metrics.get("rr_metrics") or {}),
        )
        for source, rr_metrics in rr_metric_sources:
            if not isinstance(rr_metrics, dict):
                continue
            keys = [key for key in (best_rr_key,) if key in rr_metrics]
            keys.extend(key for key in sorted(rr_metrics) if key not in keys)
            for key in keys:
                evidence = cls._normalized_skip_evidence(rr_metrics.get(key))
                if evidence is not None:
                    return {
                        "available": True,
                        "source": f"{source}[{key}]",
                        "rr_key": key,
                        **evidence,
                    }
        for key in ("backtest", "lab_backtest", "backtest_summary"):
            evidence = cls._normalized_skip_evidence(metrics.get(key))
            if evidence is not None:
                return {
                    "available": True,
                    "source": f"pattern.metrics_json.{key}",
                    **evidence,
                }
        evidence = cls._normalized_skip_evidence(metrics)
        if evidence is not None:
            return {"available": True, "source": "pattern.metrics_json", **evidence}
        return {
            "available": False,
            "reason": (
                "no skip accounting (skip_rate + signal/skipped counts) found in "
                "pattern.rr_metrics_json or pattern.metrics_json; the research run "
                "likely predates non-trade accounting"
            ),
        }

    @staticmethod
    def _research_r_values(pattern: DiscoveredPattern) -> list[float]:
        """Research-side R sample for distribution and dispersion estimates."""
        try:
            examples = pattern.examples or []
        except Exception:  # noqa: BLE001 - detached instance without session
            return []
        return [
            float(example.outcome_r)
            for example in examples
            if example.outcome_r is not None
        ]

    def _sequential_evaluation(
        self,
        *,
        lab_r: list[float],
        research_r: list[float],
        research_expectancy: float,
    ) -> dict[str, Any]:
        """Posterior + SPRT + KS package for the Director decision (§4.7)."""
        if not self.sequential_evaluation_enabled:
            return {"enabled": False}
        research_sd = (
            float(np.std(np.asarray(research_r), ddof=1)) if len(research_r) >= 5 else 0.0
        )
        lab_sd = float(np.std(np.asarray(lab_r), ddof=1)) if len(lab_r) >= 3 else 0.0
        sigma = research_sd if research_sd > 0 else (lab_sd if lab_sd > 0 else 1.0)
        prior_sd = max(sigma / 2.0, 0.05)
        posterior = posterior_probability_edge(
            lab_r,
            prior_mean=research_expectancy,
            prior_sd=prior_sd,
            min_edge_r=self.posterior_min_edge_r,
        )
        sprt = sprt_inferiority(
            lab_r,
            research_mean=research_expectancy,
            sigma=sigma,
            alpha=self.sprt_alpha,
            beta=self.sprt_beta,
        )
        msprt = normal_msprt_edge(
            lab_r,
            null_mean=0.0,
            prior_mean=research_expectancy,
            prior_sd=prior_sd,
            sigma=sigma,
            alpha=self.sprt_alpha,
        )
        alpha_spending = alpha_spending_evaluation(
            lab_r,
            max_looks=max(self.min_closed_lab_trades, int(self.min_effective_lab_trades)),
            min_edge_r=self.posterior_min_edge_r,
            sigma=sigma,
            alpha=self.sprt_alpha,
            method="obrien_fleming",
        )
        ks = (
            ks_two_sample(lab_r, research_r)
            if len(lab_r) >= 10 and len(research_r) >= 10
            else {
                "n_a": len(lab_r),
                "n_b": len(research_r),
                "statistic": None,
                "p_value": None,
                "skipped_reason": "needs >=10 lab and >=10 research R values",
            }
        )
        return _json_safe(
            {
                "enabled": True,
                "sigma_r": round(sigma, 4),
                "research_r_count": len(research_r),
                "posterior": posterior,
                "sprt": sprt,
                "msprt": msprt,
                "alpha_spending": alpha_spending,
                "ks": ks,
            }
        )


@dataclass(slots=True)
class DirectorProductionGate:
    """Hard production approval gate.

    DirectorReviewGate is only a review trigger. This gate is the first runtime
    path allowed to create a production manifest.
    """

    min_paper_fills: int = 30
    min_fill_symbols: int = 3
    min_fill_trading_days: int = 10
    max_drawdown_r: float = 4.0
    min_profit_factor: float = 1.3
    min_expectancy_r: float = 0.05
    required_edge_claim: str = "NO_DEMOSTRADO"

    def evaluate_pattern(
        self,
        pattern: DiscoveredPattern,
        closed_trades: list[Trade],
    ) -> dict[str, Any]:
        fills = [
            trade
            for trade in closed_trades
            if DirectorReviewGate._lab_pattern_id_for_trade(trade) == pattern.id
            and DirectorReviewGate._counts_as_paper_fill(trade)
        ]
        r_values = [float(trade.r_multiple or 0.0) for trade in fills]
        wins = [r for r in r_values if r > 0]
        losses = [abs(r) for r in r_values if r < 0]
        loss = sum(losses)
        profit_factor = sum(wins) / loss if loss > 0 else sum(wins) if wins else 0.0
        expectancy = sum(r_values) / len(r_values) if r_values else 0.0
        unique_symbols = len({trade.symbol for trade in fills})
        unique_days = len(
            {
                (trade.closed_at or trade.opened_at).date().isoformat()
                for trade in fills
                if trade.closed_at or trade.opened_at
            }
        )
        max_drawdown = _max_drawdown_r(r_values)
        blockers: list[str] = []
        if len(fills) < self.min_paper_fills:
            blockers.append(f"ibkr_paper_fills_below_{self.min_paper_fills}")
        if unique_symbols < self.min_fill_symbols:
            blockers.append(f"fill_symbols_below_{self.min_fill_symbols}")
        if unique_days < self.min_fill_trading_days:
            blockers.append(f"fill_days_below_{self.min_fill_trading_days}")
        if max_drawdown > self.max_drawdown_r:
            blockers.append(f"paper_fill_drawdown_above_{self.max_drawdown_r}r")
        if expectancy < self.min_expectancy_r:
            blockers.append(f"paper_fill_expectancy_below_{self.min_expectancy_r}r")
        if profit_factor < self.min_profit_factor:
            blockers.append(f"paper_fill_profit_factor_below_{self.min_profit_factor}")
        scientific_contracts = self._scientific_contracts(pattern, fills)
        blockers.extend(scientific_contracts["blockers"])
        return {
            "gate_scope": "director_production_gate",
            "approved_for_production": not blockers,
            "blockers": blockers,
            "scientific_contracts": scientific_contracts,
            "ibkr_paper_fills": len(fills),
            "min_paper_fills": self.min_paper_fills,
            "unique_fill_symbols": unique_symbols,
            "min_fill_symbols": self.min_fill_symbols,
            "unique_fill_days": unique_days,
            "min_fill_trading_days": self.min_fill_trading_days,
            "paper_fill_expectancy_r": round(expectancy, 4),
            "paper_fill_profit_factor": round(profit_factor, 4),
            "paper_fill_max_drawdown_r": round(max_drawdown, 4),
            "evidence_types_accepted": sorted(PAPER_FILL_EVIDENCE_TYPES),
            # Evidence only (Wave4-A): research/backtest skip accounting is
            # surfaced for the Director packet, never used as a blocker here.
            "research_skip_accounting": DirectorReviewGate._research_skip_accounting(pattern),
        }

    def _scientific_contracts(
        self,
        pattern: DiscoveredPattern,
        fills: list[Trade],
    ) -> dict[str, Any]:
        metrics = pattern.metrics_json or {}
        blockers: list[str] = []

        nested = self._first_dict(
            metrics,
            ("nested_discovery_replay",),
            ("research_hypothesis", "nested_discovery_replay"),
            ("research_hypothesis_package", "nested_discovery_replay"),
        )
        nested_state = self._nested_replay_state(nested)
        if not nested_state["present"]:
            blockers.append("nested_discovery_replay_missing")
        else:
            if not nested_state["implemented"]:
                blockers.append("nested_discovery_replay_not_implemented")
            if not nested_state["passed"]:
                blockers.append("nested_discovery_replay_not_passed")
            if nested_state["blocking"]:
                blockers.append("nested_discovery_replay_blocking")

        director_gate = self._first_dict(
            metrics,
            ("director_gate",),
            ("director_gate_result",),
            ("audit_gate",),
            ("audit_package", "director_gate"),
        )
        director_status = self._first_string(
            metrics,
            ("director_gate_status",),
            ("audit_gate_status",),
            ("director_gate", "status"),
            ("director_gate_result", "status"),
            ("audit_gate", "status"),
            ("audit_package", "director_gate_status"),
        ).lower()
        if not director_status and director_gate:
            director_status = str(director_gate.get("director_gate_status") or "").strip().lower()
        director_passed = director_status == "passed" or _truthy(director_gate.get("passed") if director_gate else None)
        if not director_passed:
            blockers.append("director_audit_gate_not_passed" if director_status else "director_audit_gate_missing")

        active_blockers = self._active_contract_blockers(metrics, director_gate)
        if active_blockers:
            blockers.append("active_director_blockers_present")

        event_ledger_hash = self._first_string(
            metrics,
            ("event_ledger_sha256",),
            ("event_ledger_hash",),
            ("research_hypothesis", "event_ledger_hash"),
            ("research_hypothesis_package", "event_ledger_hash"),
        )
        if not event_ledger_hash:
            blockers.append("event_ledger_hash_missing")

        evidence_packet = self._first_dict(
            metrics,
            ("production_evidence_packet",),
            ("evidence_packet",),
            ("director_packet",),
            ("audit_package", "evidence_packet"),
        )
        evidence_packet_ref = self._evidence_packet_ref(evidence_packet)
        evidence_packet_hash = self._first_string(
            metrics,
            ("evidence_packet_hash",),
            ("production_evidence_packet_hash",),
            ("audit_package_hash",),
            ("production_evidence_packet", "hash"),
            ("production_evidence_packet", "sha256"),
            ("production_evidence_packet", "packet_hash"),
            ("evidence_packet", "hash"),
            ("evidence_packet", "sha256"),
            ("evidence_packet", "packet_hash"),
        )
        if not evidence_packet_ref:
            blockers.append("evidence_packet_ref_missing")
        if not evidence_packet_hash:
            blockers.append("evidence_packet_hash_missing")

        provenance_state = self._execution_provenance_state(metrics, fills)
        if not provenance_state["costs_reconciled"]:
            blockers.append("cost_provenance_not_reconciled")
        if not provenance_state["slippage_reconciled"]:
            blockers.append("slippage_provenance_not_reconciled")
        if not provenance_state["fills_reconciled"]:
            blockers.append("fill_provenance_not_reconciled")

        drift_status = self._first_string(
            metrics,
            ("drift_status",),
            ("research_hypothesis", "drift_status"),
            ("research_hypothesis_package", "drift_status"),
        ) or str(getattr(pattern, "drift_status", "") or "")
        if drift_status.strip().lower() in {"degrading", "regressing", "deteriorating"}:
            blockers.append("drift_status_degrading")

        edge_claim = self._first_string(
            metrics,
            ("edge_claim",),
            ("research_hypothesis", "edge_claim"),
            ("research_hypothesis_package", "edge_claim"),
            ("global_experiment_registry", "edge_claim"),
        )
        if not edge_claim:
            blockers.append("edge_claim_missing")
        elif edge_claim != self.required_edge_claim:
            blockers.append("edge_claim_inflated")

        registry = self._first_dict(metrics, ("global_experiment_registry",))
        registry_hash = self._first_string(
            metrics,
            ("global_experiment_registry", "registry_hash"),
            ("global_experiment_registry", "hash"),
            ("global_experiment_registry", "sha256"),
        )
        registry_run_manifest_hash = self._first_string(
            metrics,
            ("global_experiment_registry", "run_manifest_hash"),
            ("global_experiment_registry", "latest_run_manifest_hash"),
        )
        registry_chain_valid = (
            True
            if not registry or "hash_chain_valid" not in registry
            else _truthy(registry.get("hash_chain_valid"))
        )
        if not registry_hash:
            blockers.append("global_experiment_registry_hash_missing")
        if not registry_run_manifest_hash:
            blockers.append("global_experiment_registry_run_manifest_hash_missing")
        if not registry_chain_valid:
            blockers.append("global_experiment_registry_hash_chain_invalid")

        return {
            "blockers": blockers,
            "nested_discovery_replay": nested_state,
            "director_gate_status": director_status or "missing",
            "director_gate_passed": director_passed,
            "active_blockers": active_blockers,
            "event_ledger_hash": event_ledger_hash,
            "evidence_packet": {
                "ref": evidence_packet_ref,
                "hash": evidence_packet_hash,
            },
            "execution_provenance": provenance_state,
            "drift_status": drift_status or "unknown",
            "edge_claim": edge_claim,
            "global_experiment_registry": {
                "path": registry.get("path") if registry else None,
                "registry_hash": registry_hash,
                "previous_registry_hash": registry.get("previous_registry_hash") if registry else None,
                "run_manifest_hash": registry_run_manifest_hash,
                "hash_chain_valid": registry_chain_valid,
            },
        }

    @staticmethod
    def _nested_replay_state(replay: dict[str, Any]) -> dict[str, Any]:
        if not replay:
            return {
                "present": False,
                "implemented": False,
                "passed": False,
                "blocking": False,
                "status": "missing",
            }
        status = str(replay.get("status") or "").strip().lower()
        passed_statuses = {"passed", "pass", "ok", "complete", "completed", "succeeded", "success"}
        return {
            "present": True,
            "implemented": _truthy(replay.get("implemented")),
            "passed": _truthy(replay.get("passed")) or status in passed_statuses,
            "blocking": _truthy(replay.get("blocking")),
            "status": status or "unknown",
        }

    @classmethod
    def _execution_provenance_state(
        cls,
        metrics: dict[str, Any],
        fills: list[Trade],
    ) -> dict[str, Any]:
        provenance = cls._first_dict(
            metrics,
            ("execution_provenance",),
            ("cost_slippage_fill_provenance",),
            ("production_execution_provenance",),
        )
        if provenance:
            costs = _truthy(
                provenance.get("costs_reconciled")
                if "costs_reconciled" in provenance
                else provenance.get("cost_provenance_reconciled")
            )
            slippage = _truthy(
                provenance.get("slippage_reconciled")
                if "slippage_reconciled" in provenance
                else provenance.get("slippage_provenance_reconciled")
            )
            fill_state = _truthy(
                provenance.get("fills_reconciled")
                if "fills_reconciled" in provenance
                else provenance.get("fill_provenance_reconciled")
            )
            return {
                "source": "pattern.metrics_json",
                "costs_reconciled": costs,
                "slippage_reconciled": slippage,
                "fills_reconciled": fill_state,
            }

        trade_count = len(fills)
        cost_rows = 0
        slippage_rows = 0
        fill_rows = 0
        for trade in fills:
            metadata = trade.metadata_json or {}
            if (
                _truthy(metadata.get("cost_provenance_reconciled"))
                or (
                    metadata.get("commission") is not None
                    and metadata.get("commission_source")
                    and metadata.get("estimated_spread_cost") is not None
                    and metadata.get("spread_cost_source")
                )
            ):
                cost_rows += 1
            if _truthy(metadata.get("slippage_provenance_reconciled")) or (
                metadata.get("estimated_slippage") is not None and metadata.get("slippage_source")
            ):
                slippage_rows += 1
            if _truthy(metadata.get("fill_provenance_reconciled")) or (
                trade.broker_order_id
                or metadata.get("broker_order_id")
                or metadata.get("parent_order_id")
                or metadata.get("fill_id_hash")
                or metadata.get("entry_fill_time")
            ):
                fill_rows += 1
        return {
            "source": "trade.metadata_json",
            "costs_reconciled": trade_count > 0 and cost_rows == trade_count,
            "slippage_reconciled": trade_count > 0 and slippage_rows == trade_count,
            "fills_reconciled": trade_count > 0 and fill_rows == trade_count,
            "trade_count": trade_count,
            "cost_rows": cost_rows,
            "slippage_rows": slippage_rows,
            "fill_rows": fill_rows,
        }

    @staticmethod
    def _active_contract_blockers(metrics: dict[str, Any], director_gate: dict[str, Any]) -> list[str]:
        values: list[Any] = []
        for key in ("active_blockers", "promotion_blockers", "director_blockers"):
            if key in metrics:
                values.append(metrics.get(key))
        if director_gate:
            values.append(director_gate.get("blockers"))
            summary = director_gate.get("summary")
            if isinstance(summary, dict):
                values.append(summary.get("blockers"))
        lab_execution = metrics.get("lab_execution")
        if isinstance(lab_execution, dict):
            values.append(lab_execution.get("promotion_blockers"))
        blockers: list[str] = []
        for value in values:
            if isinstance(value, list):
                blockers.extend(str(item) for item in value if str(item).strip())
            elif isinstance(value, str) and value.strip():
                blockers.append(value.strip())
        return blockers

    @staticmethod
    def _evidence_packet_ref(packet: dict[str, Any]) -> str:
        if not packet:
            return ""
        for key in ("id", "packet_id", "uri", "path"):
            value = str(packet.get(key) or "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _first_dict(metrics: dict[str, Any], *paths: tuple[str, ...]) -> dict[str, Any]:
        for path in paths:
            value: Any = metrics
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            if isinstance(value, dict) and value:
                return value
        return {}

    @staticmethod
    def _first_string(metrics: dict[str, Any], *paths: tuple[str, ...]) -> str:
        for path in paths:
            value: Any = metrics
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            text = str(value or "").strip()
            if text:
                return text
        return ""

    def approve_pattern(
        self,
        db: Session,
        *,
        pattern: DiscoveredPattern,
        reviewer: str = "director",
    ) -> dict[str, Any]:
        closed_trades = (
            db.query(Trade)
            .options(joinedload(Trade.signal))
            .filter(Trade.status == TradeStatus.CLOSED)
            .all()
        )
        decision = self.evaluate_pattern(pattern, closed_trades)
        if not bool(decision["approved_for_production"]):
            pattern.metrics_json = {
                **(pattern.metrics_json or {}),
                "production_gate": decision,
            }
            db.add(pattern)
            db.commit()
            return decision
        manifest = build_production_manifest(
            pattern,
            reviewer=reviewer,
            evidence_packet=decision,
        )
        previous_status = (
            pattern.status.value if hasattr(pattern.status, "value") else str(pattern.status)
        )
        pattern.status = DiscoveredPatternStatus.PRODUCTION
        pattern.promotion_status = DiscoveredPatternStatus.PRODUCTION.value
        pattern.promotion_reason = "DirectorProductionGate approved normal IBKR paper fill evidence"
        pattern.metrics_json = {
            **(pattern.metrics_json or {}),
            "production_gate": decision,
            "production_manifest": manifest,
        }
        db.add(
            AuditLog(
                actor="director_production_gate",
                action="pattern_production_manifest_approved",
                entity_type="discovered_pattern",
                entity_id=str(pattern.id),
                details_json={
                    "previous_status": previous_status,
                    "new_status": DiscoveredPatternStatus.PRODUCTION.value,
                    "production_gate": decision,
                    "production_manifest": manifest,
                },
            )
        )
        db.add(pattern)
        db.commit()
        return {**decision, "production_manifest": manifest}


def _json_safe(value: Any) -> Any:
    """Replace non-finite floats with None so metrics survive JSONB storage."""
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def _max_drawdown_r(r_values: list[float]) -> float:
    peak = 0.0
    cumulative = 0.0
    max_drawdown = 0.0
    for value in r_values:
        cumulative += value
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
    return max_drawdown


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes", "y", "ok", "passed", "pass"}
