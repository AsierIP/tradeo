from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, StrategyVersion
from tradeo.research.nested_optimization import nested_optimization_report
from tradeo.research.quant_validation import pbo_cscv
from tradeo.schemas import SelfImprovementResponse
from tradeo.services.backtester import Backtester
from tradeo.services.data_provider import CachedMarketDataProvider, pick_symbols
from tradeo.services.pattern_detector import CupPatternDetector
from tradeo.services.strategy_config import load_strategy_config
from tradeo.services.provider_factory import get_market_data_provider


class SelfImprovementEngine:
    """Strategy mutation and promotion gate.

    It can propose lab candidates, but it never promotes to live automatically. The
    promotion path is: lab backtest -> walk-forward -> paper trading -> human/API review.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run_lab_cycle(self, db: Session, max_symbols: int = 25) -> SelfImprovementResponse:
        base = load_strategy_config(self.settings.strategy_config_file)
        symbols = pick_symbols(limit=max_symbols)
        candidates = self._mutations(base)
        provider = CachedMarketDataProvider(upstream=get_market_data_provider())
        records: list[dict[str, Any]] = []
        trial_budget = max(1, int(self.settings.self_improvement_max_trials))
        candidates = candidates[:trial_budget]
        trial_count = len(candidates)
        for trial_index, cfg in enumerate(candidates, start=1):
            detector = CupPatternDetector.from_config(cfg)
            metrics = Backtester(
                provider=provider,
                detector=detector,
                starting_equity=self.settings.initial_capital_usd,
            ).run(symbols, period="3y", interval="1d")
            records.append(
                {
                    "config": cfg,
                    "metrics": metrics.model_dump(),
                    "trial_accounting": {
                        "trial_index": trial_index,
                        "n_trials_this_cycle": trial_count,
                        "trial_budget": trial_budget,
                        "counts_toward_family_n_trials": True,
                    },
                }
            )
        guard_by_index, guard_summary = self._anti_overfit_guards(records)
        accepted: list[dict[str, Any]] = []
        for idx, record in enumerate(records):
            guard = guard_by_index.get(idx, {})
            record["anti_overfit"] = guard
            metrics = dict(record["metrics"])
            metrics["anti_overfit"] = guard
            metrics["trial_accounting"] = record["trial_accounting"]
            record["metrics"] = metrics
            if self._passes_lab_gate(metrics, guard):
                accepted.append(record)
                name = f"cup_lab_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{len(accepted)}"
                db.add(
                    StrategyVersion(
                        name=name,
                        state="lab_candidate",
                        parent_name="cup_v0",
                        params_json=record["config"],
                        metrics_json=metrics,
                    )
                )
        best = None
        if accepted:
            best = sorted(
                accepted,
                key=lambda x: (x["metrics"]["expectancy_r"], x["metrics"]["profit_factor"]),
                reverse=True,
            )[0]
        report_path = self._write_report(records, accepted, best, guard_summary)
        db.add(
            AuditLog(
                actor="self_improvement",
                action="lab_cycle_completed",
                entity_type="strategy",
                details_json={
                    "generated": len(records),
                    "accepted": len(accepted),
                    "report_path": str(report_path),
                    "best": best,
                    "anti_overfit": guard_summary,
                },
            )
        )
        db.commit()
        return SelfImprovementResponse(
            generated=len(records),
            accepted_lab_candidates=len(accepted),
            best_candidate=best,
            report_path=str(report_path),
        )

    def _mutations(self, base: dict[str, Any]) -> list[dict[str, Any]]:
        grids = {
            "min_depth": [0.10, 0.12, 0.16],
            "max_depth": [0.34, 0.42],
            "rim_tolerance": [0.08, 0.12],
            "max_handle_depth": [0.12, 0.16, 0.18],
            "min_breakout_volume_ratio": [1.10, 1.20, 1.35],
            "min_composite_score": [0.68, 0.72, 0.76],
        }
        out: list[dict[str, Any]] = []
        for min_depth in grids["min_depth"]:
            for max_depth in grids["max_depth"]:
                for rim_tolerance in grids["rim_tolerance"]:
                    for handle in grids["max_handle_depth"]:
                        for vol in grids["min_breakout_volume_ratio"]:
                            for score in grids["min_composite_score"]:
                                cfg = deepcopy(base)
                                cfg.update(
                                    {
                                        "min_depth": min_depth,
                                        "max_depth": max_depth,
                                        "rim_tolerance": rim_tolerance,
                                        "max_handle_depth": handle,
                                        "min_breakout_volume_ratio": vol,
                                        "min_composite_score": score,
                                        "target_r_multiple": max(4.0, float(base.get("target_r_multiple", 4.0))),
                                    }
                                )
                                out.append(cfg)
        return out[: max(1, int(self.settings.self_improvement_max_trials))]

    def _passes_lab_gate(self, metrics: dict[str, Any], anti_overfit: dict[str, Any] | None = None) -> bool:
        guard = anti_overfit or {}
        return (
            metrics.get("total_trades", 0) >= 40
            and metrics.get("profit_factor", 0.0) >= 1.8
            and metrics.get("expectancy_r", 0.0) >= 0.25
            and metrics.get("max_drawdown_pct", 100.0) <= 12.0
            and bool(guard.get("pbo_passed", False))
            and bool(guard.get("plateau_passed", False))
            and bool(guard.get("nested_passed", False))
        )

    def _anti_overfit_guards(self, records: list[dict[str, Any]]) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
        pbo_report = self._pbo_report(records)
        nested_report = self._nested_report(records)
        out: dict[int, dict[str, Any]] = {}
        for idx, record in enumerate(records):
            plateau = self._plateau_report(idx, records)
            out[idx] = {
                "pbo": pbo_report,
                "pbo_passed": bool(pbo_report.get("passed", False)),
                "plateau": plateau,
                "plateau_passed": bool(plateau.get("passed", False)),
                "nested": nested_report,
                "nested_passed": bool(nested_report.get("passed", False)),
                "accepted_only_if_outer_evidence": True,
            }
        summary = dict(pbo_report)
        summary["nested"] = nested_report
        return out, summary

    def _nested_report(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.settings.self_improvement_nested_enabled:
            return {
                "method": "nested_outer_fold_pbo_v1",
                "passed": False,
                "blocked": True,
                "reason": "nested_optimization_disabled_fail_closed",
            }
        matrix, periods = self._performance_matrix(records)
        report = nested_optimization_report(
            matrix,
            n_outer_folds=max(4, int(self.settings.self_improvement_nested_outer_folds)),
            inner_trials=max(1, int(self.settings.self_improvement_nested_inner_trials)),
            max_pbo=float(self.settings.self_improvement_nested_max_pbo),
            seed=int(self.settings.self_improvement_nested_seed),
            use_optuna=bool(self.settings.self_improvement_nested_use_optuna),
        )
        report["period_kind"] = "monthly_realized_r_buckets"
        report["period_count_available"] = len(periods)
        return report

    def _pbo_report(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        matrix, periods = self._performance_matrix(records)
        min_blocks = max(4, int(self.settings.self_improvement_min_pbo_blocks))
        if matrix.shape[1] < 2 or matrix.shape[0] < min_blocks:
            return {
                "method": "cscv_pbo",
                "passed": False,
                "blocked": True,
                "reason": "insufficient_variants_or_periods_for_pbo",
                "period_count": int(matrix.shape[0]),
                "variant_count": int(matrix.shape[1]),
                "required_periods": min_blocks,
            }
        n_blocks = min(min_blocks if min_blocks % 2 == 0 else min_blocks - 1, matrix.shape[0])
        n_blocks = max(4, n_blocks)
        try:
            result = pbo_cscv(matrix, n_blocks=n_blocks, rng=17)
        except ValueError as exc:
            return {
                "method": "cscv_pbo",
                "passed": False,
                "blocked": True,
                "reason": str(exc),
                "period_count": int(matrix.shape[0]),
                "variant_count": int(matrix.shape[1]),
            }
        pbo = float(result["pbo"])
        return {
            "method": "cscv_pbo",
            "passed": pbo < float(self.settings.self_improvement_max_pbo),
            "blocked": False,
            "pbo": round(pbo, 5),
            "max_pbo": float(self.settings.self_improvement_max_pbo),
            "period_count": len(periods),
            "variant_count": int(matrix.shape[1]),
            "n_combinations": int(result["n_combinations"]),
            "best_counts": np.asarray(result["best_counts"], dtype=int).tolist(),
        }

    @staticmethod
    def _performance_matrix(records: list[dict[str, Any]]) -> tuple[np.ndarray, list[str]]:
        period_values: dict[str, list[float]] = {}
        for idx, record in enumerate(records):
            for trade in record.get("metrics", {}).get("trades", []):
                period = str(trade.get("exit_date", ""))[:7]
                if not period:
                    continue
                period_values.setdefault(period, [0.0 for _ in records])
                period_values[period][idx] += float(trade.get("r_multiple", 0.0) or 0.0)
        periods = sorted(period_values)
        if not periods:
            return np.zeros((0, len(records)), dtype=float), []
        matrix = np.asarray([period_values[p] for p in periods], dtype=float)
        return matrix, periods

    def _plateau_report(self, idx: int, records: list[dict[str, Any]]) -> dict[str, Any]:
        current = records[idx]
        cfg = current["config"]
        pf = float(current.get("metrics", {}).get("profit_factor", 0.0) or 0.0)
        if pf <= 0:
            return {"passed": False, "reason": "non_positive_profit_factor", "neighbor_count": 0}
        neighbors: list[float] = []
        for j, other in enumerate(records):
            if j == idx:
                continue
            if self._within_parameter_plateau(cfg, other["config"]):
                neighbors.append(float(other.get("metrics", {}).get("profit_factor", 0.0) or 0.0))
        if len(neighbors) < 2:
            return {"passed": False, "reason": "insufficient_neighbor_trials", "neighbor_count": len(neighbors)}
        neighbor_median = float(np.median(neighbors))
        threshold = pf * float(self.settings.self_improvement_plateau_pf_fraction)
        return {
            "passed": neighbor_median >= threshold,
            "neighbor_count": len(neighbors),
            "neighbor_median_profit_factor": round(neighbor_median, 5),
            "required_profit_factor": round(threshold, 5),
            "plateau_fraction": float(self.settings.self_improvement_plateau_pf_fraction),
        }

    @staticmethod
    def _within_parameter_plateau(left: dict[str, Any], right: dict[str, Any]) -> bool:
        keys = (
            "min_depth",
            "max_depth",
            "rim_tolerance",
            "max_handle_depth",
            "min_breakout_volume_ratio",
            "min_composite_score",
        )
        comparable = 0
        close = 0
        for key in keys:
            if key not in left or key not in right:
                continue
            a = float(left[key])
            b = float(right[key])
            comparable += 1
            if abs(a - b) <= max(abs(a), 1e-9) * 0.20:
                close += 1
        return comparable > 0 and close == comparable

    def _write_report(
        self,
        generated: list[dict[str, Any]],
        accepted: list[dict[str, Any]],
        best: dict[str, Any] | None,
        guard_summary: dict[str, Any],
    ) -> Path:
        now = datetime.now(timezone.utc)
        path = self.settings.reports_path / f"self_improvement_{now:%Y%m%d_%H%M%S}.json"
        path.write_text(
            json.dumps(
                {
                    "generated_at_utc": now.isoformat(),
                    "generated_count": len(generated),
                    "accepted_count": len(accepted),
                    "acceptance_gate": {
                        "min_trades": 40,
                        "min_profit_factor": 1.8,
                        "min_expectancy_r": 0.25,
                        "max_drawdown_pct": 12.0,
                        "max_pbo": self.settings.self_improvement_max_pbo,
                        "plateau_pf_fraction": self.settings.self_improvement_plateau_pf_fraction,
                        "nested_max_pbo": self.settings.self_improvement_nested_max_pbo,
                        "nested_outer_folds": self.settings.self_improvement_nested_outer_folds,
                        "promotion": "requires human/API supervisor approval after paper trading",
                    },
                    "anti_overfit": guard_summary,
                    "best": best,
                    "accepted": accepted,
                },
                indent=2,
            )
        )
        return path
