from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, StrategyVersion
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
        accepted: list[dict[str, Any]] = []
        for cfg in candidates:
            detector = CupPatternDetector.from_config(cfg)
            metrics = Backtester(
                provider=provider,
                detector=detector,
                starting_equity=self.settings.initial_capital_usd,
            ).run(symbols, period="3y", interval="1d")
            record = {"config": cfg, "metrics": metrics.model_dump()}
            if self._passes_lab_gate(metrics.model_dump()):
                accepted.append(record)
                name = f"cup_lab_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{len(accepted)}"
                db.add(
                    StrategyVersion(
                        name=name,
                        state="lab_candidate",
                        parent_name="cup_v0",
                        params_json=cfg,
                        metrics_json=metrics.model_dump(),
                    )
                )
        best = None
        if accepted:
            best = sorted(
                accepted,
                key=lambda x: (x["metrics"]["expectancy_r"], x["metrics"]["profit_factor"]),
                reverse=True,
            )[0]
        report_path = self._write_report(candidates, accepted, best)
        db.add(
            AuditLog(
                actor="self_improvement",
                action="lab_cycle_completed",
                entity_type="strategy",
                details_json={
                    "generated": len(candidates),
                    "accepted": len(accepted),
                    "report_path": str(report_path),
                    "best": best,
                },
            )
        )
        db.commit()
        return SelfImprovementResponse(
            generated=len(candidates),
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
        return out[:80]

    def _passes_lab_gate(self, metrics: dict[str, Any]) -> bool:
        return (
            metrics.get("total_trades", 0) >= 40
            and metrics.get("profit_factor", 0.0) >= 1.8
            and metrics.get("expectancy_r", 0.0) >= 0.25
            and metrics.get("max_drawdown_pct", 100.0) <= 12.0
        )

    def _write_report(
        self, generated: list[dict[str, Any]], accepted: list[dict[str, Any]], best: dict[str, Any] | None
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
                        "promotion": "requires human/API supervisor approval after paper trading",
                    },
                    "best": best,
                    "accepted": accepted,
                },
                indent=2,
            )
        )
        return path
