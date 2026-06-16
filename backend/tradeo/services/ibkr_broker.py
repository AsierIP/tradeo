from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, Signal, SignalStatus, Trade, TradeStatus
from tradeo.services.evidence import EvidenceQuality, EvidenceType


class IBKRSafetyError(RuntimeError):
    """Raised when a hard safety gate blocks IBKR execution."""


class IBKROperationalError(RuntimeError):
    """Raised for broker connectivity/API failures outside Tradeo safety gates."""


def _ensure_event_loop() -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def _finite_price(value: float | None, field: str) -> float:
    if value is None:
        raise IBKRSafetyError(f"{field} is required")
    value = float(value)
    if value <= 0:
        raise IBKRSafetyError(f"{field} must be positive")
    return round(value, 4)


@dataclass
class IBKRBroker:
    """Interactive Brokers adapter with conservative execution gates.

    This adapter is intentionally defensive:
    - read-only mode blocks every order path;
    - live ports require the explicit live-armed gate;
    - human approval is mandatory;
    - only simple STK/SMART/USD bracket orders are supported.
    """

    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    @property
    def connect_timeout(self) -> float:
        return float(getattr(self.settings, "ibkr_connect_timeout_seconds", 8.0))

    @property
    def order_timeout(self) -> float:
        return float(getattr(self.settings, "ibkr_order_timeout_seconds", 20.0))

    def _connect(self):
        _ensure_event_loop()
        from ib_insync import IB

        client_ids = random.sample(range(1000, 10000), 4)
        if self.settings.ibkr_client_id not in client_ids:
            client_ids.append(self.settings.ibkr_client_id)
        last_exc: Exception | None = None
        for client_id in client_ids:
            ib = IB()
            try:
                ib.connect(
                    self.settings.ibkr_host,
                    self.settings.ibkr_port,
                    clientId=client_id,
                    timeout=self.connect_timeout,
                )
                return ib
            except Exception as exc:  # noqa: BLE001 - ib_insync raises heterogeneous runtime errors.
                last_exc = exc
                if ib.isConnected():
                    ib.disconnect()
                continue
        if last_exc:
            raise IBKROperationalError(str(last_exc)) from last_exc
        raise IBKROperationalError("IBKR connection failed")

    def status(self) -> dict[str, Any]:
        from ib_insync import util

        ib = self._connect()
        try:
            server_time = ib.reqCurrentTime()
            accounts = ib.managedAccounts()
            return {
                "ok": True,
                "host": self.settings.ibkr_host,
                "port": self.settings.ibkr_port,
                "client_id": self.settings.ibkr_client_id,
                "readonly": self.settings.ibkr_readonly,
                "trading_mode": self.settings.trading_mode,
                "live_armed": self.settings.live_armed,
                "kill_switch_enabled": self.settings.kill_switch_enabled,
                "server_time": util.formatIBDatetime(server_time),
                "managed_accounts_count": len(accounts),
                "selected_account": self.settings.ibkr_account or (accounts[0] if accounts else None),
            }
        finally:
            if ib.isConnected():
                ib.disconnect()

    def account_snapshot(self) -> dict[str, Any]:
        ib = self._connect()
        try:
            accounts = ib.managedAccounts()
            account = self.settings.ibkr_account or (accounts[0] if accounts else None)
            if not account:
                raise IBKRSafetyError("IBKR returned no managed accounts")
            wanted = {
                "NetLiquidation",
                "TotalCashValue",
                "BuyingPower",
                "AvailableFunds",
                "GrossPositionValue",
                "ExcessLiquidity",
                "MaintMarginReq",
                "InitMarginReq",
            }
            summary: dict[str, dict[str, str]] = {}
            for item in ib.accountSummary(account):
                if item.tag in wanted:
                    summary[item.tag] = {"value": item.value, "currency": item.currency}
            return {
                "ok": True,
                "account": account,
                "readonly": self.settings.ibkr_readonly,
                "trading_mode": self.settings.trading_mode,
                "live_armed": self.settings.live_armed,
                "summary": summary,
            }
        finally:
            if ib.isConnected():
                ib.disconnect()

    def positions(self) -> list[dict[str, Any]]:
        ib = self._connect()
        try:
            rows: list[dict[str, Any]] = []
            for p in ib.positions():
                contract = p.contract
                rows.append(
                    {
                        "account": p.account,
                        "symbol": getattr(contract, "symbol", ""),
                        "sec_type": getattr(contract, "secType", ""),
                        "exchange": getattr(contract, "exchange", ""),
                        "currency": getattr(contract, "currency", ""),
                        "position": float(p.position),
                        "avg_cost": float(p.avgCost),
                    }
                )
            return rows
        finally:
            if ib.isConnected():
                ib.disconnect()

    def open_orders(self) -> list[dict[str, Any]]:
        ib = self._connect()
        try:
            ib.reqAllOpenOrders()
            ib.sleep(1.0)
            rows: list[dict[str, Any]] = []
            for trade in ib.openTrades():
                contract = trade.contract
                order = trade.order
                status = trade.orderStatus
                rows.append(
                    {
                        "symbol": getattr(contract, "symbol", ""),
                        "sec_type": getattr(contract, "secType", ""),
                        "order_id": order.orderId,
                        "perm_id": status.permId,
                        "action": order.action,
                        "order_type": order.orderType,
                        "quantity": float(order.totalQuantity),
                        "limit_price": getattr(order, "lmtPrice", None),
                        "aux_price": getattr(order, "auxPrice", None),
                        "status": status.status,
                        "filled": float(status.filled),
                        "remaining": float(status.remaining),
                        "parent_order_id": order.parentId,
                    }
                )
            return rows
        finally:
            if ib.isConnected():
                ib.disconnect()

    def _stock_contract(self, symbol: str):
        from ib_insync import Stock

        return Stock(symbol.upper(), "SMART", "USD")

    def _build_parent_limit_order(self, signal: Signal):
        from ib_insync import Order

        action = self._action_for_signal(signal)
        order = Order()
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = int(signal.suggested_qty)
        order.lmtPrice = _finite_price(signal.entry, "entry")
        order.tif = "DAY"
        if self.settings.ibkr_account:
            order.account = self.settings.ibkr_account
        return order

    def _action_for_signal(self, signal: Signal) -> str:
        side = signal.side.lower().strip()
        if side == "long":
            return "BUY"
        if side == "short":
            if not self.settings.allow_shorts:
                raise IBKRSafetyError("short orders are disabled by TRADEO_ALLOW_SHORTS")
            return "SELL"
        raise IBKRSafetyError(f"unsupported signal side: {signal.side}")

    def _validate_signal_for_order(self, signal: Signal, *, require_execution_enabled: bool) -> None:
        if self.settings.kill_switch_enabled:
            raise IBKRSafetyError("kill switch is enabled")
        if signal is None:
            raise IBKRSafetyError("signal is required")
        if signal.suggested_qty <= 0:
            raise IBKRSafetyError("signal suggested_qty must be positive")
        if signal.side.lower() not in {"long", "short"}:
            raise IBKRSafetyError(f"unsupported signal side: {signal.side}")
        if not signal.human_approved:
            raise IBKRSafetyError("human approval is required before IBKR order submission")
        if signal.status not in {SignalStatus.PAPER_APPROVED, SignalStatus.LIVE_APPROVED}:
            raise IBKRSafetyError(f"signal status is not executable through IBKR: {signal.status}")
        allowed_symbols = getattr(self.settings, "ibkr_allowed_symbol_set", set())
        if allowed_symbols and signal.symbol.upper() not in allowed_symbols:
            raise IBKRSafetyError(f"{signal.symbol} is not in TRADEO_IBKR_ALLOWED_SYMBOLS")

        entry = _finite_price(signal.entry, "entry")
        stop = _finite_price(signal.stop, "stop")
        target = _finite_price(signal.target, "target")
        notional = abs(entry * int(signal.suggested_qty))
        max_order_value = float(getattr(self.settings, "ibkr_max_order_value_usd", 1500.0))
        if notional > max_order_value:
            raise IBKRSafetyError(
                f"order notional ${notional:.2f} exceeds TRADEO_IBKR_MAX_ORDER_VALUE_USD=${max_order_value:.2f}"
            )

        if signal.side.lower() == "long" and not (stop < entry < target):
            raise IBKRSafetyError("long bracket requires stop < entry < target")
        if signal.side.lower() == "short" and not (target < entry < stop):
            raise IBKRSafetyError("short bracket requires target < entry < stop")

        if require_execution_enabled:
            if self.settings.ibkr_readonly:
                raise IBKRSafetyError("TRADEO_IBKR_READONLY=true blocks order submission")
            if self.settings.trading_mode == "research":
                raise IBKRSafetyError("research mode blocks order submission")
            live_port = int(self.settings.ibkr_port) in {7496, 4001}
            if self.settings.trading_mode == "live" or live_port:
                if not self.settings.live_armed:
                    raise IBKRSafetyError("live IBKR execution requires live_armed=true")

    def preview_signal_order(self, signal: Signal) -> dict[str, Any]:
        """Run an IBKR WhatIf preview for the parent limit order without submitting it."""
        self._validate_signal_for_order(signal, require_execution_enabled=False)
        ib = self._connect()
        try:
            contract = self._stock_contract(signal.symbol)
            qualified = ib.qualifyContracts(contract)
            if not qualified:
                raise IBKRSafetyError(f"IBKR could not qualify contract for {signal.symbol}")
            contract = qualified[0]
            order = self._build_parent_limit_order(signal)
            state = ib.whatIfOrder(contract, order)
            return {
                "ok": True,
                "signal_id": signal.id,
                "symbol": signal.symbol,
                "side": signal.side,
                "qty": int(signal.suggested_qty),
                "entry": float(signal.entry),
                "stop": float(signal.stop),
                "target": float(signal.target),
                "notional_usd": round(float(signal.entry) * int(signal.suggested_qty), 2),
                "contract": {
                    "con_id": contract.conId,
                    "symbol": contract.symbol,
                    "sec_type": contract.secType,
                    "exchange": contract.exchange,
                    "currency": contract.currency,
                },
                "what_if": {
                    "init_margin_change": getattr(state, "initMarginChange", ""),
                    "maint_margin_change": getattr(state, "maintMarginChange", ""),
                    "equity_with_loan_change": getattr(state, "equityWithLoanChange", ""),
                    "commission": getattr(state, "commission", None),
                    "min_commission": getattr(state, "minCommission", None),
                    "max_commission": getattr(state, "maxCommission", None),
                    "warning_text": getattr(state, "warningText", ""),
                    "status": getattr(state, "status", ""),
                },
            }
        finally:
            if ib.isConnected():
                ib.disconnect()

    def submit_signal_bracket(self, db: Session, signal: Signal, *, reason: str = "manual") -> Trade:
        """Submit a bracket order to IBKR and persist the Trade record.

        This method can target a paper TWS/Gateway session when TRADEO_TRADING_MODE=paper.
        For live ports or TRADEO_TRADING_MODE=live, the live_armed gate is mandatory.
        """
        from tradeo.services.system_controls import runtime_kill_switch_active

        if runtime_kill_switch_active(db):
            raise IBKRSafetyError("runtime kill switch is active (see system_controls)")
        self._validate_signal_for_order(signal, require_execution_enabled=True)
        ib = self._connect()
        try:
            contract = self._stock_contract(signal.symbol)
            qualified = ib.qualifyContracts(contract)
            if not qualified:
                raise IBKRSafetyError(f"IBKR could not qualify contract for {signal.symbol}")
            contract = qualified[0]
            action = self._action_for_signal(signal)
            bracket = ib.bracketOrder(
                action=action,
                quantity=int(signal.suggested_qty),
                limitPrice=_finite_price(signal.entry, "entry"),
                takeProfitPrice=_finite_price(signal.target, "target"),
                stopLossPrice=_finite_price(signal.stop, "stop"),
            )
            for order in bracket:
                order.tif = "DAY"
                if self.settings.ibkr_account:
                    order.account = self.settings.ibkr_account
            trades = []
            for order in bracket:
                trades.append(ib.placeOrder(contract, order))
                ib.sleep(0.25)
            deadline = time.monotonic() + self.order_timeout
            while time.monotonic() < deadline:
                ib.sleep(0.5)
                if all(t.orderStatus.permId for t in trades):
                    break
            if not all(t.orderStatus.permId for t in trades):
                for trade_status in trades:
                    ib.cancelOrder(trade_status.order)
                ib.sleep(1.0)
                raise IBKRSafetyError("IBKR did not acknowledge every bracket leg with a permId")

            parent_trade = trades[0]
            parent_order = parent_trade.order
            order_ids = [t.order.orderId for t in trades]
            perm_ids = [t.orderStatus.permId for t in trades]
            now = datetime.now(timezone.utc)
            signal_metadata = signal.metadata_json or {}
            evidence_type = (
                EvidenceType.LIVE_ORDER.value
                if self.settings.trading_mode == "live"
                else EvidenceType.IBKR_PAPER_ORDER.value
            )
            execution_observation = {
                "source": "ibkr_order_submission",
                "truth_status": "orders_accepted_waiting_fill_reconciliation",
                "submitted_at": now.isoformat(),
                "evidence_type": evidence_type,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "entry_variant_id": signal_metadata.get("entry_variant_id"),
                "regime_key": (signal_metadata.get("regime") or {}).get("regime_key"),
                "order_ids": order_ids,
                "perm_ids": perm_ids,
            }
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
                opened_at=now,
                broker_order_id=str(parent_order.orderId),
                evidence_type=evidence_type,
                evidence_quality=EvidenceQuality.NORMAL.value,
                metadata_json={
                    "evidence_type": evidence_type,
                    "evidence_quality": EvidenceQuality.NORMAL.value,
                    "execution_mode": "ibkr",
                    "ibkr_mode": self.settings.trading_mode,
                    "source_signal": signal.id,
                    "reason": reason,
                    "entry_variant_id": signal_metadata.get("entry_variant_id"),
                    "entry_variant": signal_metadata.get("entry_variant"),
                    "entry_audit": signal_metadata.get("entry_audit"),
                    "regime": signal_metadata.get("regime"),
                    "regime_fit": signal_metadata.get("regime_fit"),
                    "execution_observation": execution_observation,
                    "contract": {
                        "con_id": contract.conId,
                        "symbol": contract.symbol,
                        "sec_type": contract.secType,
                        "exchange": contract.exchange,
                        "currency": contract.currency,
                    },
                    "order_ids": order_ids,
                    "perm_ids": perm_ids,
                    "parent_order_id": parent_order.orderId,
                    "submitted_at": now.isoformat(),
                    "readonly": self.settings.ibkr_readonly,
                    "live_armed": self.settings.live_armed,
                },
            )
            signal.status = SignalStatus.EXECUTED
            signal.metadata_json = {
                **signal_metadata,
                "evidence_type": evidence_type,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "execution_observation": execution_observation,
            }
            db.add(trade)
            db.add(
                AuditLog(
                    actor="ibkr_broker",
                    action="ibkr_bracket_submitted",
                    entity_type="trade",
                    entity_id=str(signal.id),
                    details_json={
                        "signal_id": signal.id,
                        "symbol": signal.symbol,
                        "qty": signal.suggested_qty,
                        "order_ids": order_ids,
                        "perm_ids": perm_ids,
                        "trading_mode": self.settings.trading_mode,
                        "port": self.settings.ibkr_port,
                        "reason": reason,
                    },
                )
            )
            db.commit()
            db.refresh(trade)
            return trade
        finally:
            if ib.isConnected():
                ib.disconnect()
