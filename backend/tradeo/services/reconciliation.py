"""DB <-> IBKR reconciliation with automatic kill switch (informe §4.5).

On every run we compare what the database believes is open against what IBKR
reports (positions + open orders). Any confirmed divergence means the system's
model of its own exposure is wrong, which is exactly the failure mode the kill
switch exists for — so divergence activates the runtime kill switch and the
order paths stop until a human investigates.

Beyond symbol existence, reconciliation is explicit about *how much* and
*which order*:

- ``position_qty_mismatch_at_broker``: per symbol, the signed broker position
  is compared against the signed quantity the DB expects (sum of open IBKR
  trades, shorts negative). A position larger than expected, on the wrong
  side, or smaller with no open orders that could still fill it, is a
  divergence. A smaller-than-expected position *with* pending open orders on
  the symbol is the normal partial-entry state, so it is recorded as a
  warning, not a divergence.
- ``db_order_id_missing_at_broker``: a DB trade whose symbol shows up at the
  broker only through open orders must find its ``broker_order_id`` among
  those orders (as order id, perm id, or the parent id bracket children point
  to); otherwise the orders the broker holds are not the orders we think we
  placed.
- ``partial_fill_open_order``: an open order with ``0 < filled < quantity``
  is a legitimate transient state, never a divergence — it is surfaced as a
  warning and audited so partial fills are observable instead of silent.

Connection failures are NOT divergences: the broker being unreachable proves
nothing about state mismatch. They are audited and surfaced, never escalated
to the kill switch automatically. Warnings likewise never trip the kill
switch.
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


def _signed_qty(trade: Trade) -> float:
    sign = -1.0 if str(trade.side or "").lower().strip() == "short" else 1.0
    return sign * abs(float(trade.qty or 0))


def _order_matches_trade(order: dict[str, Any], broker_order_id: str) -> bool:
    """True when an open-order row references the trade's broker order id.

    Bracket children carry their own ids but point back to the parent via
    ``parent_order_id``, so a trade whose parent leg already filled is still
    matched through its surviving child legs.
    """
    for key in ("order_id", "perm_id", "parent_order_id"):
        value = order.get(key)
        if value is not None and str(value) == broker_order_id:
            return True
    return False


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
            "warnings": [],
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

        position_qty: dict[str, float] = {}
        for row in positions:
            symbol = str(row.get("symbol") or "").upper()
            qty = float(row.get("position") or 0.0)
            if symbol and abs(qty) > 0:
                position_qty[symbol] = position_qty.get(symbol, 0.0) + qty
        position_symbols = set(position_qty)
        orders_by_symbol: dict[str, list[dict[str, Any]]] = {}
        for row in open_orders:
            symbol = str(row.get("symbol") or "").upper()
            orders_by_symbol.setdefault(symbol, []).append(row)
        order_symbols = set(orders_by_symbol)
        db_symbols = {trade.symbol.upper() for trade in db_ibkr_trades}
        result["broker_positions"] = len(position_symbols)
        result["broker_open_orders"] = len(open_orders)

        divergences: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
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
            elif (
                symbol not in position_symbols
                and trade.broker_order_id
                and not any(
                    _order_matches_trade(order, str(trade.broker_order_id))
                    for order in orders_by_symbol.get(symbol, [])
                )
            ):
                divergences.append(
                    {
                        "kind": "db_order_id_missing_at_broker",
                        "symbol": symbol,
                        "trade_id": trade.id,
                        "broker_order_id": trade.broker_order_id,
                        "broker_open_order_ids": sorted(
                            str(order.get("order_id"))
                            for order in orders_by_symbol.get(symbol, [])
                            if order.get("order_id") is not None
                        ),
                    }
                )
        for symbol in sorted(position_symbols - db_symbols):
            divergences.append(
                {
                    "kind": "broker_position_not_in_db",
                    "symbol": symbol,
                }
            )

        expected_qty: dict[str, float] = {}
        for trade in db_ibkr_trades:
            symbol = trade.symbol.upper()
            expected_qty[symbol] = expected_qty.get(symbol, 0.0) + _signed_qty(trade)
        for symbol in sorted(position_symbols & set(expected_qty)):
            broker_qty = position_qty[symbol]
            db_qty = expected_qty[symbol]
            if broker_qty == db_qty:
                continue
            detail = {
                "symbol": symbol,
                "db_signed_qty": db_qty,
                "broker_signed_qty": broker_qty,
            }
            wrong_side = (broker_qty > 0) != (db_qty > 0)
            larger_than_expected = abs(broker_qty) > abs(db_qty)
            if not wrong_side and not larger_than_expected and symbol in order_symbols:
                # Smaller position with orders still working: the normal
                # partial-entry state, observable but not a divergence.
                warnings.append(
                    {"kind": "position_qty_below_db_pending_orders", **detail}
                )
                continue
            divergences.append({"kind": "position_qty_mismatch_at_broker", **detail})

        for symbol in sorted(order_symbols):
            for order in orders_by_symbol[symbol]:
                try:
                    filled = float(order.get("filled") or 0.0)
                    quantity = float(order.get("quantity") or 0.0)
                except (TypeError, ValueError):
                    continue
                if 0 < filled < quantity:
                    warnings.append(
                        {
                            "kind": "partial_fill_open_order",
                            "symbol": symbol,
                            "order_id": order.get("order_id"),
                            "filled": filled,
                            "quantity": quantity,
                            "remaining": order.get("remaining"),
                        }
                    )
        result["divergences"] = divergences
        result["warnings"] = warnings

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
                    "warning_count": len(warnings),
                    "warnings": warnings,
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
