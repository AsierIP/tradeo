from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


REASON_CODES = {
    "bar_not_closed",
    "bucket_not_allowed",
    "calendar_unknown",
    "cooldown_active",
    "duplicate_exposure",
    "flat_not_perfect",
    "hard_flat_deadline_unresolved",
    "low_dollar_volume",
    "max_open_positions",
    "net_ev_below_threshold",
    "no_new_entries_cutoff",
    "pacing_exhausted",
    "reduce_only_exit_failed",
    "slippage_too_high",
    "spread_too_wide",
    "stale_data",
}


@dataclass(frozen=True, slots=True)
class IntradaySessionReport:
    session_id: str
    generated_at: datetime
    mode: str
    candidates_total: int
    trades_total: int
    pnl_usd: float
    realized_ev_r: float
    expected_ev_r: float
    flat_status: str
    flat_compliant: bool
    reason_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "generated_at": self.generated_at.isoformat(),
            "mode": self.mode,
            "candidates_total": self.candidates_total,
            "trades_total": self.trades_total,
            "pnl_usd": self.pnl_usd,
            "realized_ev_r": self.realized_ev_r,
            "expected_ev_r": self.expected_ev_r,
            "flat_status": self.flat_status,
            "flat_compliant": self.flat_compliant,
            "reason_counts": self.reason_counts,
        }


def build_intraday_session_report(
    *,
    session_id: str,
    mode: str,
    candidates: Iterable[dict[str, Any]],
    trades: Iterable[dict[str, Any]],
    flat_status: str,
) -> IntradaySessionReport:
    candidate_rows = list(candidates)
    trade_rows = list(trades)
    reasons: Counter[str] = Counter()
    for row in candidate_rows + trade_rows:
        codes = row.get("reason_codes") or row.get("reasons") or []
        if isinstance(codes, str):
            codes = [codes]
        reasons.update(str(code) for code in codes)
    pnl = sum(float(row.get("pnl_usd") or 0.0) for row in trade_rows)
    realized_ev = sum(float(row.get("r_multiple") or 0.0) for row in trade_rows)
    expected_ev = sum(float(row.get("expected_ev_r") or 0.0) for row in candidate_rows)
    return IntradaySessionReport(
        session_id=session_id,
        generated_at=datetime.now(timezone.utc),
        mode=mode,
        candidates_total=len(candidate_rows),
        trades_total=len(trade_rows),
        pnl_usd=round(pnl, 2),
        realized_ev_r=round(realized_ev, 6),
        expected_ev_r=round(expected_ev, 6),
        flat_status=flat_status,
        flat_compliant=flat_status == "FLAT_CONFIRMED",
        reason_counts=dict(sorted(reasons.items())),
    )
