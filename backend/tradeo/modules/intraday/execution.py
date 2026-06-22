from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class IntradayPaperOrderRequest:
    symbol: str
    pattern_state: str
    director_approved: bool
    paper_enabled: bool
    has_flat_plan: bool
    expected_ev_r: float
    fill_price: float | None = None
    expected_price: float | None = None
    commission: float = 0.0
    partial_fill_qty: float = 0.0
    requested_qty: float = 0.0


@dataclass(frozen=True, slots=True)
class IntradayPaperExecutionResult:
    allowed: bool
    reason_codes: tuple[str, ...]
    metrics: dict[str, Any]


class IntradayPaperExecutionService:
    def evaluate(self, request: IntradayPaperOrderRequest) -> IntradayPaperExecutionResult:
        reasons: list[str] = []
        if not request.paper_enabled:
            reasons.append("paper_disabled")
        if not request.director_approved or request.pattern_state != "INTRADAY_PRODUCTION":
            reasons.append("director_not_approved")
        if not request.has_flat_plan:
            reasons.append("flat_plan_required")
        metrics = self._metrics(request)
        return IntradayPaperExecutionResult(
            allowed=not reasons,
            reason_codes=tuple(reasons),
            metrics=metrics,
        )

    @staticmethod
    def _metrics(request: IntradayPaperOrderRequest) -> dict[str, Any]:
        fill_ratio = (
            request.partial_fill_qty / request.requested_qty
            if request.requested_qty > 0
            else 0.0
        )
        slippage_bps = 0.0
        if request.fill_price and request.expected_price and request.expected_price > 0:
            slippage_bps = (request.fill_price / request.expected_price - 1.0) * 10_000.0
        return {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "expected_ev_r": request.expected_ev_r,
            "fill_price": request.fill_price,
            "slippage_bps": round(slippage_bps, 6),
            "commission": request.commission,
            "fill_ratio": round(fill_ratio, 6),
        }
