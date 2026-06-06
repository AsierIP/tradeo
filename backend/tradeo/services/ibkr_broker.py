from __future__ import annotations

from dataclasses import dataclass

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import Signal


@dataclass
class BrokerOrderResult:
    accepted: bool
    broker_order_id: str | None
    message: str


class IBKRBroker:
    """Interactive Brokers adapter guarded by hard live-trading checks.

    v0 supports stock bracket orders only. Shorts can be sent if IBKR account permissions,
    borrow availability and Tradeo risk gates allow it. Options/margin remain disabled by
    default and require separate strategy validation.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def place_stock_bracket_order(self, signal: Signal) -> BrokerOrderResult:
        if not self.settings.live_armed:
            return BrokerOrderResult(False, None, "live trading is not armed")
        if self.settings.ibkr_readonly:
            return BrokerOrderResult(False, None, "IBKR readonly mode is enabled")
        if signal.human_approved is not True:
            return BrokerOrderResult(False, None, "human approval missing")
        try:
            from ib_insync import IB, Stock

            ib = IB()
            ib.connect(self.settings.ibkr_host, self.settings.ibkr_port, clientId=self.settings.ibkr_client_id)
            contract = Stock(signal.symbol, "SMART", "USD")
            action = "BUY" if signal.side == "long" else "SELL"
            bracket = ib.bracketOrder(
                action=action,
                quantity=signal.suggested_qty,
                limitPrice=signal.entry,
                takeProfitPrice=signal.target,
                stopLossPrice=signal.stop,
            )
            trades = [ib.placeOrder(contract, order) for order in bracket]
            ib.sleep(1)
            order_ids = ",".join(str(t.order.orderId) for t in trades)
            ib.disconnect()
            return BrokerOrderResult(True, order_ids, "submitted bracket order")
        except Exception as exc:  # noqa: BLE001
            return BrokerOrderResult(False, None, f"IBKR order failed: {exc}")
