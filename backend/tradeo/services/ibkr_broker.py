from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import (
    AuditLog,
    DiscoveredPattern,
    DiscoveredPatternStatus,
    Signal,
    SignalStatus,
    Trade,
    TradeStatus,
)
from tradeo.modules.fox_hunter.production_manifest import production_manifest_is_active
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
        timeout = float(getattr(self.settings, "ibkr_order_timeout_seconds", 20.0))
        if self.settings.trading_mode == "paper":
            return max(timeout, 45.0)
        return timeout

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

    def fills(self) -> list[dict[str, Any]]:
        """Return recent IBKR executions normalized for DB reconciliation."""
        ib = self._connect()
        try:
            try:
                from ib_insync import ExecutionFilter

                raw_fills = ib.reqExecutions(ExecutionFilter())
            except TypeError:
                raw_fills = ib.reqExecutions()
            except Exception:  # noqa: BLE001 - fall back to session fills if request fails.
                raw_fills = ib.fills()
            ib.sleep(1.0)
            return [_normalize_fill(fill) for fill in (raw_fills or [])]
        finally:
            if ib.isConnected():
                ib.disconnect()

    def _stock_contract(self, symbol: str):
        from ib_insync import Stock

        return Stock(symbol.upper(), "SMART", "USD")

    def _selected_account(self, ib) -> str | None:  # noqa: ANN001
        if self.settings.ibkr_account:
            return self.settings.ibkr_account
        managed_accounts = getattr(ib, "managedAccounts", None)
        if not callable(managed_accounts):
            return None
        accounts = managed_accounts()
        return accounts[0] if len(accounts) == 1 else None

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
            if self._targets_live_execution():
                if not self.settings.live_armed:
                    raise IBKRSafetyError("live IBKR execution requires live_armed=true")
                if signal.status != SignalStatus.LIVE_APPROVED:
                    raise IBKRSafetyError("live IBKR execution requires signal status live_approved")
                if not str(self.settings.ibkr_account or "").strip():
                    raise IBKRSafetyError("live IBKR execution requires explicit TRADEO_IBKR_ACCOUNT")
                if not self.settings.ibkr_allowed_symbol_set:
                    raise IBKRSafetyError("live IBKR execution requires non-empty TRADEO_IBKR_ALLOWED_SYMBOLS")

    def _targets_live_execution(self) -> bool:
        live_port = int(self.settings.ibkr_port) in {7496, 4001}
        return bool(self.settings.trading_mode == "live" or live_port)

    def _validate_live_production_signal(self, db: Session, signal: Signal) -> None:
        if not self._targets_live_execution():
            return
        metadata = signal.metadata_json or {}
        if str(metadata.get("entry_module") or "") != "fox_hunter":
            raise IBKRSafetyError("live IBKR execution requires a Fox Hunter production signal")
        try:
            pattern_id = int(metadata.get("pattern_id") or 0)
        except (TypeError, ValueError) as exc:
            raise IBKRSafetyError("live IBKR execution requires signal.metadata_json.pattern_id") from exc
        pattern = db.get(DiscoveredPattern, pattern_id)
        if pattern is None:
            raise IBKRSafetyError("live IBKR execution requires an existing discovered pattern")
        if pattern.status != DiscoveredPatternStatus.PRODUCTION:
            raise IBKRSafetyError("live IBKR execution requires pattern status production")
        if not production_manifest_is_active(pattern):
            raise IBKRSafetyError("live IBKR execution requires an active production manifest")

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
        self._validate_live_production_signal(db, signal)
        ib = self._connect()
        try:
            contract = self._stock_contract(signal.symbol)
            qualified = ib.qualifyContracts(contract)
            if not qualified:
                raise IBKRSafetyError(f"IBKR could not qualify contract for {signal.symbol}")
            contract = qualified[0]
            action = self._action_for_signal(signal)
            bracket_prices = _operational_bracket_prices(
                signal,
                paper_mode=self.settings.trading_mode == "paper",
                max_distance_pct=float(
                    getattr(self.settings, "ibkr_paper_bracket_max_distance_pct", 0.20)
                ),
            )
            bracket = ib.bracketOrder(
                action=action,
                quantity=int(signal.suggested_qty),
                limitPrice=bracket_prices["entry"],
                takeProfitPrice=bracket_prices["target"],
                stopLossPrice=bracket_prices["stop"],
            )
            for order in bracket:
                order.tif = "DAY"
                account = self._selected_account(ib)
                if account:
                    order.account = account
            if action == "SELL":
                bracket[0].shortSaleSlot = 1
            trades = []
            for order in bracket:
                trades.append(ib.placeOrder(contract, order))
                ib.sleep(0.25)
            bracket_degraded_to_parent_only = False
            bracket_failure_snapshot: list[dict[str, Any]] | None = None
            deadline = time.monotonic() + self.order_timeout
            while time.monotonic() < deadline:
                ib.sleep(0.5)
                if _bracket_acknowledged(trades, paper_mode=self.settings.trading_mode != "live"):
                    break
            if not _bracket_acknowledged(trades, paper_mode=self.settings.trading_mode != "live"):
                status_snapshot = _bracket_status_snapshot(trades)
                for trade_status in trades:
                    ib.cancelOrder(trade_status.order)
                ib.sleep(1.0)
                raise IBKRSafetyError(
                    "IBKR did not acknowledge the bracket safely: "
                    f"{json.dumps(status_snapshot, sort_keys=True)}"
                )

            parent_trade = trades[0]
            parent_order = parent_trade.order
            order_ids = [t.order.orderId for t in trades]
            perm_ids = [t.orderStatus.permId or None for t in trades]
            paper_bracket_ack_mode = (
                "order_id_status_no_terminal"
                if self.settings.trading_mode == "paper" and not all(perm_ids)
                else "perm_id_all_legs"
            )
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
                "paper_bracket_ack_mode": paper_bracket_ack_mode,
            }
            bracket_legs = {
                "entry": {"order_id": order_ids[0], "perm_id": perm_ids[0]},
                "target": {
                    "order_id": order_ids[1] if len(order_ids) > 1 else None,
                    "perm_id": perm_ids[1] if len(perm_ids) > 1 else None,
                },
                "stop": {
                    "order_id": order_ids[2] if len(order_ids) > 2 else None,
                    "perm_id": perm_ids[2] if len(perm_ids) > 2 else None,
                },
            }
            trade = Trade(
                signal_id=signal.id,
                symbol=signal.symbol,
                pattern=signal.pattern,
                side=signal.side,
                qty=signal.suggested_qty,
                entry=bracket_prices["entry"],
                stop=bracket_prices["stop"],
                target=bracket_prices["target"],
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
                    "requested_bracket": bracket_prices["requested"],
                    "submitted_bracket": bracket_prices["submitted"],
                    "paper_bracket_adjusted": bracket_prices["adjusted"],
                    "paper_bracket_ack_mode": paper_bracket_ack_mode,
                    "paper_bracket_degraded_to_parent_only": bracket_degraded_to_parent_only,
                    "bracket_failure_snapshot": bracket_failure_snapshot,
                    "order_ids": order_ids,
                    "perm_ids": perm_ids,
                    "bracket_legs": bracket_legs,
                    "entry_order_id": order_ids[0],
                    "target_order_id": order_ids[1] if len(order_ids) > 1 else None,
                    "stop_order_id": order_ids[2] if len(order_ids) > 2 else None,
                    "entry_perm_id": perm_ids[0],
                    "target_perm_id": perm_ids[1] if len(perm_ids) > 1 else None,
                    "stop_perm_id": perm_ids[2] if len(perm_ids) > 2 else None,
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

    def repair_trade_exit_protection(
        self,
        db: Session,
        trade: Trade,
        *,
        reason: str = "reconciliation_exit_repair",
    ) -> dict[str, Any]:
        """Place paper OCA stop/target exits for an already-open IBKR trade."""
        if self.settings.trading_mode != "paper":
            raise IBKRSafetyError("exit protection auto-repair is paper-only")
        if self.settings.ibkr_readonly:
            raise IBKRSafetyError("TRADEO_IBKR_READONLY=true blocks exit protection repair")
        if self.settings.kill_switch_enabled:
            raise IBKRSafetyError("kill switch is enabled")
        if trade.status != TradeStatus.OPEN:
            raise IBKRSafetyError("trade is not open")
        if not trade.broker_order_id:
            raise IBKRSafetyError("trade has no broker_order_id")

        ib = self._connect()
        try:
            contract = self._stock_contract(trade.symbol)
            qualified = ib.qualifyContracts(contract)
            if not qualified:
                raise IBKRSafetyError(f"IBKR could not qualify contract for {trade.symbol}")
            contract = qualified[0]
            exit_action = "BUY" if str(trade.side or "").lower().strip() == "short" else "SELL"
            prices = _operational_bracket_prices(
                trade,
                paper_mode=True,
                max_distance_pct=float(
                    getattr(self.settings, "ibkr_paper_bracket_max_distance_pct", 0.20)
                ),
            )
            qty = abs(int(trade.qty or 0))
            if qty <= 0:
                raise IBKRSafetyError("trade qty must be positive")

            from ib_insync import Order

            oca_group = f"TRADEO_EXIT_{trade.id}_{uuid.uuid4().hex[:10]}"
            target_order = Order()
            target_order.action = exit_action
            target_order.orderType = "LMT"
            target_order.totalQuantity = qty
            target_order.lmtPrice = prices["target"]
            target_order.tif = "DAY"
            target_order.ocaGroup = oca_group
            target_order.ocaType = 1
            target_order.transmit = True

            stop_order = Order()
            stop_order.action = exit_action
            stop_order.orderType = "STP"
            stop_order.totalQuantity = qty
            stop_order.auxPrice = prices["stop"]
            stop_order.tif = "DAY"
            stop_order.ocaGroup = oca_group
            stop_order.ocaType = 1
            stop_order.transmit = True

            account = self._selected_account(ib)
            for order in (target_order, stop_order):
                if account:
                    order.account = account

            ib.reqAllOpenOrders()
            ib.sleep(1.0)
            existing_exit_orders = [
                open_trade
                for open_trade in ib.openTrades()
                if str(getattr(open_trade.contract, "symbol", "") or "").upper() == trade.symbol.upper()
                and str(getattr(open_trade.order, "action", "") or "").upper() == exit_action
                and str(getattr(open_trade.orderStatus, "status", "") or "").lower()
                not in {"filled", "cancelled", "apicancelled", "inactive"}
            ]

            placed = [
                ib.placeOrder(contract, target_order),
                ib.placeOrder(contract, stop_order),
            ]
            deadline = time.monotonic() + self.order_timeout
            while time.monotonic() < deadline:
                ib.sleep(0.5)
                if all(_parent_order_acknowledged(row) for row in placed):
                    break
            if not all(_parent_order_acknowledged(row) for row in placed):
                snapshot = _bracket_status_snapshot(placed)
                for row in placed:
                    ib.cancelOrder(row.order)
                ib.sleep(1.0)
                raise IBKRSafetyError(
                    "IBKR did not acknowledge repaired exit protection safely: "
                    f"{json.dumps(snapshot, sort_keys=True)}"
                )

            placed_ids = {int(row.order.orderId) for row in placed if getattr(row.order, "orderId", None)}
            for row in existing_exit_orders:
                order_id = getattr(row.order, "orderId", None)
                if order_id is not None and int(order_id) in placed_ids:
                    continue
                ib.cancelOrder(row.order)
            ib.sleep(1.0)

            now = datetime.now(timezone.utc)
            target_trade, stop_trade = placed
            target_perm_id = target_trade.orderStatus.permId or None
            stop_perm_id = stop_trade.orderStatus.permId or None
            metadata = dict(trade.metadata_json or {})
            bracket_legs = dict(metadata.get("bracket_legs") or {})
            bracket_legs["target"] = {
                "order_id": target_trade.order.orderId,
                "perm_id": target_perm_id,
                "repaired": True,
            }
            bracket_legs["stop"] = {
                "order_id": stop_trade.order.orderId,
                "perm_id": stop_perm_id,
                "repaired": True,
            }
            metadata.update(
                {
                    "exit_protection_mode": "oca_stop_target",
                    "exit_protection_repaired_at": now.isoformat(),
                    "exit_protection_repair_reason": reason,
                    "protective_orders": {
                        "oca_group": oca_group,
                        "action": exit_action,
                        "quantity": qty,
                        "target": {
                            "order_id": target_trade.order.orderId,
                            "perm_id": target_perm_id,
                            "limit_price": prices["target"],
                        },
                        "stop": {
                            "order_id": stop_trade.order.orderId,
                            "perm_id": stop_perm_id,
                            "aux_price": prices["stop"],
                        },
                        "requested_bracket": prices["requested"],
                        "submitted_bracket": prices["submitted"],
                        "paper_bracket_adjusted": prices["adjusted"],
                    },
                    "bracket_legs": bracket_legs,
                    "target_order_id": target_trade.order.orderId,
                    "target_perm_id": target_perm_id,
                    "stop_order_id": stop_trade.order.orderId,
                    "stop_perm_id": stop_perm_id,
                }
            )
            trade.metadata_json = metadata
            db.add(trade)
            db.add(
                AuditLog(
                    actor="ibkr_broker",
                    action="ibkr_exit_protection_repaired",
                    entity_type="trade",
                    entity_id=str(trade.id),
                    details_json={
                        "trade_id": trade.id,
                        "symbol": trade.symbol,
                        "side": trade.side,
                        "qty": qty,
                        "action": exit_action,
                        "reason": reason,
                        "oca_group": oca_group,
                        "target_order_id": target_trade.order.orderId,
                        "target_perm_id": target_perm_id,
                        "stop_order_id": stop_trade.order.orderId,
                        "stop_perm_id": stop_perm_id,
                        "cancelled_existing_exit_order_ids": [
                            getattr(row.order, "orderId", None)
                            for row in existing_exit_orders
                            if getattr(row.order, "orderId", None) not in placed_ids
                        ],
                        "requested_bracket": prices["requested"],
                        "submitted_bracket": prices["submitted"],
                    },
                )
            )
            db.commit()
            db.refresh(trade)
            return {
                "trade_id": trade.id,
                "symbol": trade.symbol,
                "target_order_id": target_trade.order.orderId,
                "stop_order_id": stop_trade.order.orderId,
                "target_perm_id": target_perm_id,
                "stop_perm_id": stop_perm_id,
                "oca_group": oca_group,
                "submitted_bracket": prices["submitted"],
            }
        finally:
            if ib.isConnected():
                ib.disconnect()


def _normalize_fill(fill: Any) -> dict[str, Any]:
    contract = getattr(fill, "contract", None)
    execution = getattr(fill, "execution", fill)
    commission_report = getattr(fill, "commissionReport", None)
    executed_at = _iso_ts(getattr(execution, "time", None) or getattr(fill, "time", None))
    exec_id = _str_or_none(getattr(execution, "execId", None))
    order_id = _str_or_none(getattr(execution, "orderId", None))
    perm_id = _str_or_none(getattr(execution, "permId", None))
    symbol = _str_or_none(getattr(contract, "symbol", None) or getattr(execution, "symbol", None))
    quantity = _float_or_none(getattr(execution, "shares", None))
    price = _float_or_none(getattr(execution, "price", None) or getattr(execution, "avgPrice", None))
    raw = {
        "exec_id": exec_id,
        "order_id": order_id,
        "perm_id": perm_id,
        "symbol": symbol,
        "time": executed_at,
        "price": price if not exec_id else None,
        "quantity": quantity if not exec_id else None,
    }
    fill_id_hash = hashlib.sha256(json.dumps(raw, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "symbol": symbol,
        "sec_type": _str_or_none(getattr(contract, "secType", None)),
        "exchange": _str_or_none(getattr(execution, "exchange", None) or getattr(contract, "exchange", None)),
        "currency": _str_or_none(
            getattr(commission_report, "currency", None) or getattr(contract, "currency", None)
        ),
        "side": _normalize_side(getattr(execution, "side", None)),
        "quantity": quantity,
        "price": price,
        "avg_price": _float_or_none(getattr(execution, "avgPrice", None)),
        "order_id": order_id,
        "perm_id": perm_id,
        "exec_id": exec_id,
        "execution_time": executed_at,
        "commission": _float_or_none(getattr(commission_report, "commission", None)),
        "commission_currency": _str_or_none(getattr(commission_report, "currency", None)),
        "realized_pnl": _float_or_none(getattr(commission_report, "realizedPNL", None)),
        "fill_id_hash": fill_id_hash,
        "broker_execution_hash": fill_id_hash,
        "account_id_redacted": True,
    }


def _bracket_acknowledged(trades: list[Any], *, paper_mode: bool) -> bool:
    if len(trades) != 3:
        return False
    if _bracket_has_terminal_rejection(trades):
        return False
    if not all(getattr(trade.order, "orderId", 0) for trade in trades):
        return False
    if paper_mode:
        return True
    return all(getattr(trade.orderStatus, "permId", 0) for trade in trades)


def _bracket_has_terminal_rejection(trades: list[Any]) -> bool:
    bad_statuses = {"cancelled", "apicancelled", "inactive"}
    for trade in trades:
        status = str(getattr(trade.orderStatus, "status", "") or "").lower()
        if status in bad_statuses:
            return True
        log_entries = getattr(trade, "log", []) or []
        for entry in log_entries:
            entry_status = str(getattr(entry, "status", "") or "").lower()
            if entry_status in bad_statuses:
                return True
            error_code = int(getattr(entry, "errorCode", 0) or 0)
            if error_code and error_code not in {161, 10147}:
                return True
    return False


def _parent_order_acknowledged(trade: Any) -> bool:
    if not getattr(trade.order, "orderId", 0):
        return False
    if not getattr(trade.orderStatus, "permId", 0):
        return False
    status = str(getattr(trade.orderStatus, "status", "") or "").lower()
    return status not in {"cancelled", "apicancelled", "inactive"}


def _bracket_status_snapshot(trades: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for trade in trades:
        rows.append(
            {
                "order_id": getattr(trade.order, "orderId", None),
                "parent_id": getattr(trade.order, "parentId", None),
                "action": getattr(trade.order, "action", None),
                "order_type": getattr(trade.order, "orderType", None),
                "perm_id": getattr(trade.orderStatus, "permId", None),
                "status": getattr(trade.orderStatus, "status", None),
            }
        )
    return rows


def _operational_bracket_prices(
    signal: Signal,
    *,
    paper_mode: bool,
    max_distance_pct: float,
) -> dict[str, Any]:
    entry = _finite_price(signal.entry, "entry")
    stop = _finite_price(signal.stop, "stop")
    target = _finite_price(signal.target, "target")
    requested = {"entry": entry, "stop": stop, "target": target}
    submitted = dict(requested)
    if paper_mode and max_distance_pct > 0:
        distance = max(0.01, float(max_distance_pct))
        side = signal.side.lower().strip()
        if side == "long":
            submitted["target"] = min(target, round(entry * (1 + distance), 4))
            submitted["stop"] = max(stop, round(entry * (1 - distance), 4))
        elif side == "short":
            submitted["target"] = max(target, round(entry * (1 - distance), 4))
            submitted["stop"] = min(stop, round(entry * (1 + distance), 4))
    return {
        "entry": submitted["entry"],
        "stop": submitted["stop"],
        "target": submitted["target"],
        "requested": requested,
        "submitted": submitted,
        "adjusted": submitted != requested,
    }


def _normalize_side(value: Any) -> str | None:
    side = str(value or "").upper().strip()
    if side in {"BOT", "BUY", "BOUGHT"}:
        return "BUY"
    if side in {"SLD", "SELL", "SOLD"}:
        return "SELL"
    return side or None


def _float_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _iso_ts(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)
