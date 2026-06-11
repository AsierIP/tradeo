"""Post-promotion pattern decay detection with CUSUM (informe §4.8).

For every pattern in PRODUCTION or DIRECTOR_REVIEW we run a two-sided CUSUM
over the chronological series of realized R per trade, standardized against
the Research expectancy and dispersion. A downward trigger means the live
performance is drifting below what Research promised faster than chance
allows: the pattern is marked ``drift_status='decaying'`` and (with
``health_monitor_block_decaying``) the matcher stops generating new signals
for it until a fresh re-validation clears it.

Decay is one-way here: re-activation is an explicit human/Director decision
after re-running the discovery validation on fresh data, never automatic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
from loguru import logger
from sqlalchemy.orm import Session, joinedload

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import (
    AuditLog,
    DiscoveredPattern,
    DiscoveredPatternStatus,
    Trade,
    TradeStatus,
)
from tradeo.research.quant_validation import cusum_drift
from tradeo.services.director_review_gate import DirectorReviewGate
from tradeo.services.implementation_shortfall import trade_slippage_r

MONITORED_STATUSES = (
    DiscoveredPatternStatus.PRODUCTION,
    DiscoveredPatternStatus.DIRECTOR_REVIEW,
)

__all__ = ["PatternHealthMonitor", "MONITORED_STATUSES"]


@dataclass(slots=True)
class PatternHealthMonitor:
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def run(self, db: Session) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.status.in_(list(MONITORED_STATUSES)))
            .all()
        )
        closed_trades = (
            db.query(Trade)
            .options(joinedload(Trade.signal))
            .filter(Trade.status == TradeStatus.CLOSED)
            .order_by(Trade.closed_at.asc())
            .all()
        )
        checked = 0
        skipped: list[dict[str, Any]] = []
        decaying: list[dict[str, Any]] = []
        for pattern in patterns:
            trades = [
                trade
                for trade in closed_trades
                if DirectorReviewGate._lab_pattern_id_for_trade(trade) == pattern.id
                and DirectorReviewGate._counts_as_paper_fill(trade)
            ]
            r_values = [float(trade.r_multiple or 0.0) for trade in trades]
            if len(r_values) < settings.health_monitor_min_trades:
                skipped.append(
                    {
                        "pattern_id": pattern.id,
                        "reason": "insufficient_closed_fills",
                        "closed_fills": len(r_values),
                        "min_required": settings.health_monitor_min_trades,
                    }
                )
                continue
            checked += 1
            target = float(pattern.best_expectancy_r or pattern.expectancy_r or 0.0)
            scale = self._research_r_scale(pattern, fallback=r_values)
            verdict = cusum_drift(
                r_values,
                k=settings.health_monitor_cusum_k,
                h=settings.health_monitor_cusum_h,
                target=target,
                scale=scale,
            )
            shortfall_values = [
                float(row["slippage_r"])
                for row in (trade_slippage_r(trade) for trade in trades)
                if row is not None
            ]
            shortfall_verdict = None
            if len(shortfall_values) >= settings.director_min_slippage_samples:
                shortfall_verdict = cusum_drift(
                    shortfall_values,
                    k=settings.health_monitor_shortfall_cusum_k,
                    h=settings.health_monitor_shortfall_cusum_h,
                    target=settings.director_max_median_slippage_r,
                    scale=max(float(np.std(np.asarray(shortfall_values), ddof=1)), 0.05)
                    if len(shortfall_values) > 1
                    else 0.05,
                )
            health = {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "closed_fills": len(r_values),
                "shortfall_fills": len(shortfall_values),
                "target_expectancy_r": round(target, 4),
                "scale_r": round(scale, 4),
                "cusum_k": settings.health_monitor_cusum_k,
                "cusum_h": settings.health_monitor_cusum_h,
                "triggered": bool(verdict["triggered"]),
                "side": verdict["side"],
                "trigger_index": verdict["index"],
                "min_s_neg": round(float(np.min(verdict["s_neg"])), 4),
                "max_s_pos": round(float(np.max(verdict["s_pos"])), 4),
                "shortfall_cusum": self._shortfall_health(shortfall_verdict),
            }
            pattern.metrics_json = {**(pattern.metrics_json or {}), "pattern_health": health}
            shortfall_triggered = (
                shortfall_verdict is not None
                and bool(shortfall_verdict["triggered"])
                and shortfall_verdict["side"] == "up"
            )
            if (verdict["triggered"] and verdict["side"] == "down") or shortfall_triggered:
                previous = str(pattern.drift_status or "stable")
                pattern.drift_status = "decaying"
                r_drift = float(abs(np.min(verdict["s_neg"])))
                shortfall_drift = (
                    float(np.max(shortfall_verdict["s_pos"])) if shortfall_verdict is not None else 0.0
                )
                pattern.drift_score = round(max(r_drift, shortfall_drift), 4)
                db.add(
                    AuditLog(
                        actor="pattern_health_monitor",
                        action="pattern_health_decay_detected",
                        entity_type="discovered_pattern",
                        entity_id=str(pattern.id),
                        details_json={
                            "pattern_id": pattern.id,
                            "previous_drift_status": previous,
                            "health": health,
                            "decay_source": "shortfall" if shortfall_triggered else "realized_r",
                            "effect": (
                                "matcher stops generating new signals for this pattern "
                                "while drift_status='decaying'; re-validation required"
                            ),
                        },
                    )
                )
                decaying.append({"pattern_id": pattern.id, "name": pattern.name, **health})
                logger.warning(
                    "pattern {} ({}) marked decaying by CUSUM (min_s_neg={})",
                    pattern.id,
                    pattern.name,
                    health["min_s_neg"],
                )
            db.add(pattern)
        db.commit()
        return {
            "patterns_monitored": len(patterns),
            "patterns_checked": checked,
            "patterns_skipped": len(skipped),
            "skipped": skipped,
            "decay_detected": len(decaying),
            "decaying": decaying,
        }

    @staticmethod
    def _shortfall_health(verdict: dict[str, Any] | None) -> dict[str, Any]:
        if verdict is None:
            return {"available": False, "reason": "insufficient_real_fill_shortfall_samples"}
        return {
            "available": True,
            "triggered": bool(verdict["triggered"]),
            "side": verdict["side"],
            "trigger_index": verdict["index"],
            "min_s_neg": round(float(np.min(verdict["s_neg"])), 4),
            "max_s_pos": round(float(np.max(verdict["s_pos"])), 4),
        }

    @staticmethod
    def _research_r_scale(pattern: DiscoveredPattern, *, fallback: list[float]) -> float:
        """Dispersion of Research R for standardization, with honest fallbacks."""
        outcomes = [
            float(example.outcome_r)
            for example in (pattern.examples or [])
            if example.outcome_r is not None
        ]
        if len(outcomes) >= 5:
            sd = float(np.std(np.asarray(outcomes), ddof=1))
            if sd > 0:
                return sd
        quant = (pattern.metrics_json or {}).get("quant_validation")
        if isinstance(quant, dict):
            sd = quant.get("expectancy_sd_weighted") or quant.get("sd_weighted")
            try:
                if sd is not None and float(sd) > 0:
                    return float(sd)
            except (TypeError, ValueError):
                pass
        if len(fallback) > 1:
            sd = float(np.std(np.asarray(fallback), ddof=1))
            if sd > 0:
                return sd
        return 1.0
