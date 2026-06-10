"""DB <-> IBKR reconciliation with automatic kill switch (informe §4.5).

On every run we compare what the database believes is open against what IBKR
reports (positions + open orders). Any confirmed divergence means the system's
model of its own exposure is wrong, which is exactly the failure mode the kill
switch exists for — so divergence activates the runtime kill switch and the
order paths stop until a human investigates.

Connection failures are NOT divergences: the broker being unreachable proves
nothing about state mismatch. They are audited and surfaced, never escalated
to the kill switch automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, Trade, TradeStatus
from tradeo.services.ibkr_broker import IBKRBroker
from tradeo.services.system_controls import (
    activate_runtime_kill_switch,
    runtime_kill_switch_active,
)

__all__ = ["ReconciliationService"]


def _is_ibkr_trade(trade: Trade) -> bool:
    metadata = trade.metadata_json or {}
    return str(metadata.get("execution_mode") or "") == "ibkr"


@dataclass(slots=True)
class ReconciliationService:
    settings: Settings | None = None
    broker: IBKRBroker | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.broker = self.broker or IBKRBroker(self.settings)

    def reconcile(self, db: Session) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        now = datetime.now(timezone.utc)
        open_trades = (
            db.query(Trade)
            .filter(Trade.status == TradeStatus.OPEN)
            .all()
        )
        db_ibkr_trades = [trade for trade in open_trades if _is_ibkr_trade(trade)]
        result: dict[str, Any] = {
            "ok": True,
            "checked_at": now.isoformat(),
            "db_open_ibkr_trades": len(db_ibkr_trades),
            "broker_positions": 0,
            "broker_open_orders": 0,
            "divergences": [],
            "kill_switch_activated": False,
            "kill_switch_already_active": runtime_kill_switch_active(db),
        }
        try:
            assert self.broker is not None
            positions = self.broker.positions()
            open_orders = self.broker.open_orders()
        except Exception as exc:  # noqa: BLE001
            # Unreachable broker is an availability problem, not a state
            # divergence; never auto-trip the kill switch on it.
            logger.warning("reconciliation skipped: broker unreachable: {}", exc)
            db.add(
                AuditLog(
                    actor="reconciliation",
                    action="reconciliation_broker_unreachable",
                    entity_type="system",
                    entity_id="ibkr",
                    details_json={
                        "error": f"{type(exc).__name__}: {exc}",
                        "db_open_ibkr_trades": len(db_ibkr_trades),
                    },
                )
            )
            db.commit()
            return {**result, "ok": False, "error": f"broker_unreachable: {exc}"}

        position_symbols = {
            str(row.get("symbol") or "").upper()
            for row in positions
            if abs(float(row.get("position") or 0.0)) > 0
        }
        order_symbols = {str(row.get("symbol") or "").upper() for row in open_orders}
        db_symbols = {trade.symbol.upper() for trade in db_ibkr_trades}
        result["broker_positions"] = len(position_symbols)
        result["broker_open_orders"] = len(open_orders)

        divergences: list[dict[str, Any]] = []
        for trade in db_ibkr_trades:
            symbol = trade.symbol.upper()
            if symbol not in position_symbols and symbol not in order_symbols:
                divergences.append(
                    {
                        "kind": "db_open_trade_missing_at_broker",
                        "symbol": symbol,
                        "trade_id": trade.id,
                        "broker_order_id": trade.broker_order_id,
                    }
                )
        for symbol in sorted(position_symbols - db_symbols):
            divergences.append(
                {
                    "kind": "broker_position_not_in_db",
                    "symbol": symbol,
                }
            )
        result["divergences"] = divergences

        db.add(
            AuditLog(
                actor="reconciliation",
                action="reconciliation_completed",
                entity_type="system",
                entity_id="ibkr",
                details_json={
                    "db_open_ibkr_trades": len(db_ibkr_trades),
                    "broker_positions": sorted(position_symbols),
                    "broker_open_order_count": len(open_orders),
                    "divergence_count": len(divergences),
                    "divergences": divergences,
                },
            )
        )
        if divergences and settings.reconciliation_auto_kill_switch:
            activate_runtime_kill_switch(
                db,
                reason="reconciliation divergence between DB open trades and IBKR state",
                actor="reconciliation",
                details={"divergences": divergences},
            )
            result["kill_switch_activated"] = True
            logger.error(
                "reconciliation divergence: kill switch activated ({} divergences)",
                len(divergences),
            )
        else:
            db.commit()
        return result
