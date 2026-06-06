from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from tradeo.db.models import AuditLog, Signal, SignalStatus, Trade, TradeStatus


class PaperBroker:
    """Paper execution adapter.

    It records simulated fills at the signal entry price. A future mark-to-market task can
    close positions against stop/target using fresh market data.
    """

    def execute_signal(self, db: Session, signal: Signal) -> Trade:
        if signal.status not in {SignalStatus.PAPER_APPROVED, SignalStatus.LIVE_APPROVED}:
            raise ValueError(f"Signal status not executable in paper broker: {signal.status}")
        if signal.suggested_qty <= 0:
            raise ValueError("Signal suggested_qty is zero")
        trade = Trade(
            signal_id=signal.id,
            symbol=signal.symbol,
            pattern=signal.pattern,
            side=signal.side,
            qty=signal.suggested_qty,
            entry=signal.entry,
            stop=signal.stop,
            target=signal.target,
            status=TradeStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            metadata_json={"execution_mode": "paper", "source_signal": signal.id},
        )
        signal.status = SignalStatus.EXECUTED
        db.add(trade)
        db.add(
            AuditLog(
                actor="paper_broker",
                action="paper_trade_opened",
                entity_type="trade",
                entity_id=str(signal.id),
                details_json={"signal_id": signal.id, "symbol": signal.symbol, "qty": signal.suggested_qty},
            )
        )
        db.commit()
        db.refresh(trade)
        return trade
