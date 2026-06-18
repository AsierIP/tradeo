from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import time
import uuid
from collections.abc import Iterable
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
from tradeo.schemas import PatternCandidate
from tradeo.services.evidence import EvidenceQuality, EvidenceType
from tradeo.services.live_readiness_gate import LiveReadinessGate, LiveReadinessError
from tradeo.services.market_session import market_session_status
from tradeo.services.risk_manager import RiskManager

EXECUTION_PREFLIGHT_QUOTE_BASIS = "ibkr_execution_preflight_quote_snapshot"
EXECUTION_PREFLIGHT_WHATIF_BASIS = "ibkr_live_parent_order_what_if"
IBKR_UNSET_DOUBLE_ABS = 1e100


class IBKRSafetyError(RuntimeError):
    """Raised when a hard safety gate blocks IBKR execution."""


class IBKROperationalError(RuntimeError):
    """Raised for broker connectivity/API failures outside Tradeo safety gates."""


IBKR_LIVE_PORTS = {7496, 4001}


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


def _format_status_time(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _normalize_symbols(symbols: Iterable[str] | None) -> list[str]:
    if symbols is None:
        return []
    return sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})


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

    def account_readiness_preflight(
        self,
        *,
        symbols: Iterable[str] | None = None,
        require_live_port: bool = True,
        include_account_ids: bool = False,
    ) -> dict[str, Any]:
        """Non-order broker/account preflight for live-readiness surfaces.

        This deliberately avoids WhatIf, order construction and order placement. It only checks
        the configured endpoint, server time, managed accounts and local execution guardrails.
        """
        checks: list[dict[str, Any]] = []
        selected_account = str(self.settings.ibkr_account or "").strip() or None
        allowed_symbols = sorted(self.settings.ibkr_allowed_symbol_set)
        requested_symbols = _normalize_symbols(symbols)

        def add(name: str, ok: bool, reason: str, **details: Any) -> None:
            checks.append({"name": name, "ok": bool(ok), "reason": None if ok else reason, **details})

        ib = None
        server_time = None
        managed_accounts: list[str] = []
        try:
            ib = self._connect()
            server_time = ib.reqCurrentTime()
            managed_accounts = list(ib.managedAccounts() or [])
            add("connected", True, "ibkr_connection_failed")
        except Exception as exc:  # noqa: BLE001 - expose as readiness status, not an exception.
            add("connected", False, "ibkr_connection_failed", error=str(exc))
        finally:
            if ib and ib.isConnected():
                ib.disconnect()

        if not selected_account and len(managed_accounts) == 1:
            selected_account = managed_accounts[0]
        selected_account_configured = bool(str(self.settings.ibkr_account or "").strip())
        selected_account_managed = bool(
            selected_account and selected_account in set(managed_accounts)
        )
        symbol_misses = [symbol for symbol in requested_symbols if symbol not in set(allowed_symbols)]

        add("ibkr_readonly", not self.settings.ibkr_readonly, "ibkr_readonly")
        add(
            "ibkr_live_port",
            not require_live_port or int(self.settings.ibkr_port) in IBKR_LIVE_PORTS,
            "ibkr_live_port_required",
            live_ports=sorted(IBKR_LIVE_PORTS),
        )
        add(
            "ibkr_account_configured",
            selected_account_configured,
            "missing_ibkr_account",
        )
        add(
            "ibkr_account_managed",
            selected_account_managed,
            "configured_ibkr_account_not_managed"
            if selected_account_configured
            else "missing_ibkr_account",
            managed_accounts_count=len(managed_accounts),
        )
        add(
            "ibkr_allowed_symbols",
            bool(allowed_symbols),
            "missing_ibkr_allowed_symbols",
            symbol_count=len(allowed_symbols),
        )
        if requested_symbols:
            add(
                "requested_symbols_allowed",
                not symbol_misses,
                "symbols_not_allowed",
                checked_symbol_count=len(requested_symbols),
                missing_symbols=symbol_misses,
            )

        blocked = [check for check in checks if not check["ok"]]
        status: dict[str, Any] = {
            "ok": not blocked,
            "state": "ready" if not blocked else "blocked",
            "primary_block_reason": blocked[0]["reason"] if blocked else None,
            "block_reasons": [str(check["reason"]) for check in blocked],
            "checks": checks,
            "host": self.settings.ibkr_host,
            "port": self.settings.ibkr_port,
            "client_id": self.settings.ibkr_client_id,
            "readonly": self.settings.ibkr_readonly,
            "trading_mode": self.settings.trading_mode,
            "live_armed": self.settings.live_armed,
            "kill_switch_enabled": self.settings.kill_switch_enabled,
            "connected": bool(managed_accounts or server_time),
            "server_time": _format_status_time(server_time) if server_time is not None else None,
            "managed_accounts_count": len(managed_accounts),
            "selected_account_configured": selected_account_configured,
            "selected_account_present": selected_account is not None,
            "selected_account_managed": selected_account_managed,
            "allowed_symbol_count": len(allowed_symbols),
            "checked_symbol_count": len(requested_symbols),
            "require_live_port": require_live_port,
            "live_ports": sorted(IBKR_LIVE_PORTS),
            "account_summary_included": False,
            "order_checks_included": False,
        }
        if include_account_ids:
            status["selected_account"] = selected_account
            status["managed_accounts"] = managed_accounts
        return status

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

    def _validate_paper_account_target(self, ib) -> None:  # noqa: ANN001
        if self.settings.trading_mode != "paper":
            return
        account = self._selected_account(ib)
        if not account:
            raise IBKRSafetyError("paper IBKR execution requires a selected paper account")
        if not str(account).upper().startswith("DU"):
            raise IBKRSafetyError(
                "paper IBKR execution requires a DU paper account; "
                "refusing custom-port submit without paper-account proof"
            )

    def _build_parent_limit_order(self, signal: Signal):
        _ensure_event_loop()
        from ib_insync import Order

        action = self._action_for_signal(signal)
        order = Order()
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = int(signal.suggested_qty)
        order.lmtPrice = _finite_price(signal.entry, "entry")
        order.tif = "DAY"
        if action == "SELL":
            order.shortSaleSlot = 1
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
        live_port = int(self.settings.ibkr_port) in IBKR_LIVE_PORTS
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
        try:
            LiveReadinessGate(self.settings).require_ready(db, require_auto_submit=False)
        except LiveReadinessError as exc:
            reason = str(exc.status.get("primary_block_reason") or "live_readiness_blocked")
            raise IBKRSafetyError(f"live IBKR execution blocked by LiveReadinessGate: {reason}") from exc

    def _validate_final_live_risk(self, db: Session, signal: Signal) -> None:
        if not self._targets_live_execution():
            return
        candidate = self._risk_candidate_from_signal(signal, self.settings)
        risk = RiskManager(self.settings).validate_candidate(candidate, db, execution_context="live")
        if not risk.approved:
            raise IBKRSafetyError(f"live IBKR execution blocked by RiskManager: {risk.reason}")

    @staticmethod
    def _risk_candidate_from_signal(signal: Signal, settings: Settings) -> PatternCandidate:
        metadata = signal.metadata_json or {}
        match = metadata.get("match") if isinstance(metadata.get("match"), dict) else {}
        features: dict[str, Any] = {}
        for source in (match.get("features"), metadata.get("features")):
            if isinstance(source, dict):
                features.update(source)
        # The final broker-side risk pass is meant to catch dynamic account
        # state drift after approval. Older production signals may not carry
        # full scanner features, so do not turn missing feature metadata into
        # an unrelated liquidity/ATR rejection here.
        features.setdefault("avg_dollar_volume", settings.min_avg_dollar_volume)
        features.setdefault("atr_pct", 0.0)
        for key in ("pattern_family_key", "canonical_pattern_key", "pattern_key", "pattern_id"):
            value = metadata.get(key) or match.get(key)
            if value is not None:
                features[key] = value
        return PatternCandidate(
            symbol=signal.symbol,
            pattern=signal.pattern,
            side=signal.side,
            timeframe=signal.timeframe,
            entry=float(signal.entry),
            stop=float(signal.stop),
            target=float(signal.target),
            reward_risk=float(signal.reward_risk),
            confidence=float(signal.confidence),
            rule_score=float(metadata.get("rule_score") or 0.0),
            ml_score=float(metadata.get("ml_score") or 0.0),
            vision_score=float(metadata.get("vision_score") or 0.0),
            composite_score=float(signal.composite_score),
            features=features,
            notes=["final_live_risk_revalidation"],
        )

    def _live_execution_preflight(
        self,
        *,
        ib,  # noqa: ANN001 - ib_insync client or test double
        contract: Any,
        signal: Signal,
        bracket_prices: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Fail closed on execution-time market facts before live order placement."""
        if not self._targets_live_execution():
            return None

        session = market_session_status()
        if not bool(session.get("regular_session_open")):
            raise IBKRSafetyError(
                "live IBKR execution requires regular US equity session open "
                f"(state={session.get('state')})"
            )

        _validate_submitted_bracket_geometry(signal.side, bracket_prices["submitted"])
        quote_snapshot = self._capture_live_preflight_quote(
            ib,
            contract,
            signal,
            submitted_bracket=bracket_prices["submitted"],
        )
        what_if = self._live_parent_whatif_preflight(
            ib=ib,
            contract=contract,
            signal=signal,
            submitted_entry=bracket_prices["entry"],
        )
        return {
            "schema_version": 1,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "market_session": session,
            "quote_snapshot": quote_snapshot,
            "what_if": what_if,
            "submitted_bracket": bracket_prices["submitted"],
        }

    def _capture_live_preflight_quote(
        self,
        ib,  # noqa: ANN001 - ib_insync client or test double
        contract: Any,
        signal: Signal,
        *,
        submitted_bracket: dict[str, Any],
    ) -> dict[str, Any]:
        timeout = max(
            0.0,
            float(
                getattr(
                    self.settings,
                    "ibkr_execution_preflight_quote_timeout_seconds",
                    getattr(self.settings, "signal_spread_snapshot_timeout_seconds", 4.0),
                )
            ),
        )
        max_age_seconds = max(
            0.0,
            float(
                getattr(
                    self.settings,
                    "ibkr_execution_preflight_quote_max_age_seconds",
                    5.0,
                )
            ),
        )
        try:
            ticker = ib.reqMktData(contract, "", snapshot=True, regulatorySnapshot=False)
        except Exception as exc:  # noqa: BLE001 - fail closed before order placement.
            raise IBKRSafetyError(
                f"live execution preflight quote snapshot failed: {type(exc).__name__}: {exc}"
            ) from exc

        deadline = time.monotonic() + timeout
        while not (
            _usable_market_price(getattr(ticker, "bid", None))
            and _usable_market_price(getattr(ticker, "ask", None))
        ):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ib.sleep(min(0.25, remaining))

        captured_at = datetime.now(timezone.utc)
        bid = _clean_market_price(getattr(ticker, "bid", None))
        ask = _clean_market_price(getattr(ticker, "ask", None))
        last = _clean_market_price(getattr(ticker, "last", None)) or _clean_market_price(
            getattr(ticker, "close", None)
        )
        if bid is None or ask is None:
            raise IBKRSafetyError(
                "live IBKR execution requires a fresh usable bid/ask quote snapshot"
            )
        if ask < bid:
            raise IBKRSafetyError("live IBKR execution preflight rejected crossed bid/ask quote")

        quote_time = _quote_timestamp(ticker) or captured_at
        age_seconds = max(0.0, (captured_at - quote_time).total_seconds())
        if age_seconds > max_age_seconds:
            raise IBKRSafetyError(
                "live IBKR execution preflight rejected stale quote "
                f"({age_seconds:.1f}s old > {max_age_seconds:.1f}s max)"
            )

        mid = (bid + ask) / 2.0
        spread_abs = ask - bid
        spread_observed_pct = spread_abs / mid if mid > 0 else None
        submitted_entry = _finite_price(submitted_bracket.get("entry"), "submitted entry")
        submitted_stop = _finite_price(submitted_bracket.get("stop"), "submitted stop")
        risk_per_share = abs(submitted_entry - submitted_stop)
        spread_cost_r = spread_abs / risk_per_share if risk_per_share > 0 else None
        side = str(signal.side or "").lower().strip()
        if side == "long":
            entry_quote_price = ask
            entry_quote_slippage_abs = max(0.0, ask - submitted_entry)
        elif side == "short":
            entry_quote_price = bid
            entry_quote_slippage_abs = max(0.0, submitted_entry - bid)
        else:
            raise IBKRSafetyError(f"unsupported signal side: {signal.side}")
        entry_quote_slippage_pct = (
            entry_quote_slippage_abs / submitted_entry if submitted_entry > 0 else None
        )
        entry_quote_slippage_r = (
            entry_quote_slippage_abs / risk_per_share if risk_per_share > 0 else None
        )
        bid_size = _clean_market_size(getattr(ticker, "bidSize", None))
        ask_size = _clean_market_size(getattr(ticker, "askSize", None))
        top_of_book_notional = (
            min(bid_size, ask_size) * mid
            if bid_size is not None and ask_size is not None
            else None
        )
        self._validate_live_quote_thresholds(
            spread_observed_pct=spread_observed_pct,
            spread_cost_r=spread_cost_r,
            entry_quote_slippage_pct=entry_quote_slippage_pct,
            entry_quote_slippage_r=entry_quote_slippage_r,
            bid_size=bid_size,
            ask_size=ask_size,
            top_of_book_notional=top_of_book_notional,
        )
        return {
            "schema_version": 1,
            "data_basis": EXECUTION_PREFLIGHT_QUOTE_BASIS,
            "captured_at": captured_at.isoformat(),
            "quote_time": quote_time.isoformat(),
            "quote_age_seconds": round(age_seconds, 3),
            "max_age_seconds": max_age_seconds,
            "symbol": str(signal.symbol or "").upper(),
            "bid": bid,
            "ask": ask,
            "last": last,
            "bid_size": bid_size,
            "ask_size": ask_size,
            "mid": round(mid, 6),
            "spread_abs": round(spread_abs, 6),
            "spread_observed_pct": (
                round(spread_observed_pct, 6) if spread_observed_pct is not None else None
            ),
            "spread_cost_r": round(spread_cost_r, 6) if spread_cost_r is not None else None,
            "entry_quote_price": entry_quote_price,
            "entry_quote_slippage_abs": round(entry_quote_slippage_abs, 6),
            "entry_quote_slippage_pct": (
                round(entry_quote_slippage_pct, 6)
                if entry_quote_slippage_pct is not None
                else None
            ),
            "entry_quote_slippage_r": (
                round(entry_quote_slippage_r, 6) if entry_quote_slippage_r is not None else None
            ),
            "top_of_book_notional_usd": (
                round(top_of_book_notional, 2) if top_of_book_notional is not None else None
            ),
            "thresholds": self._live_quote_thresholds(),
        }

    def _validate_live_quote_thresholds(
        self,
        *,
        spread_observed_pct: float | None,
        spread_cost_r: float | None,
        entry_quote_slippage_pct: float | None,
        entry_quote_slippage_r: float | None,
        bid_size: float | None,
        ask_size: float | None,
        top_of_book_notional: float | None,
    ) -> None:
        thresholds = self._live_quote_thresholds()
        if spread_observed_pct is None or spread_observed_pct > thresholds["max_spread_pct"]:
            raise IBKRSafetyError(
                "live execution preflight rejected wide spread pct "
                f"({spread_observed_pct!r} > {thresholds['max_spread_pct']})"
            )
        if spread_cost_r is None or spread_cost_r > thresholds["max_spread_cost_r"]:
            raise IBKRSafetyError(
                "live execution preflight rejected wide spread cost R "
                f"({spread_cost_r!r} > {thresholds['max_spread_cost_r']})"
            )
        if (
            entry_quote_slippage_pct is None
            or entry_quote_slippage_pct > thresholds["max_entry_slippage_pct"]
        ):
            raise IBKRSafetyError(
                "live execution preflight rejected entry quote slippage pct "
                f"({entry_quote_slippage_pct!r} > {thresholds['max_entry_slippage_pct']})"
            )
        if (
            entry_quote_slippage_r is None
            or entry_quote_slippage_r > thresholds["max_entry_slippage_r"]
        ):
            raise IBKRSafetyError(
                "live execution preflight rejected entry quote slippage R "
                f"({entry_quote_slippage_r!r} > {thresholds['max_entry_slippage_r']})"
            )
        if bid_size is None or bid_size < thresholds["min_bid_size"]:
            raise IBKRSafetyError(
                "live execution preflight rejected low bid size "
                f"({bid_size!r} < {thresholds['min_bid_size']})"
            )
        if ask_size is None or ask_size < thresholds["min_ask_size"]:
            raise IBKRSafetyError(
                "live execution preflight rejected low ask size "
                f"({ask_size!r} < {thresholds['min_ask_size']})"
            )
        if (
            top_of_book_notional is None
            or top_of_book_notional < thresholds["min_top_of_book_notional_usd"]
        ):
            raise IBKRSafetyError(
                "live execution preflight rejected low top-of-book notional "
                f"({top_of_book_notional!r} < {thresholds['min_top_of_book_notional_usd']})"
            )

    def _live_quote_thresholds(self) -> dict[str, float]:
        return {
            "max_spread_pct": max(
                0.0,
                float(getattr(self.settings, "ibkr_execution_preflight_max_spread_pct", 0.005)),
            ),
            "max_spread_cost_r": max(
                0.0,
                float(getattr(self.settings, "ibkr_execution_preflight_max_spread_cost_r", 0.05)),
            ),
            "max_entry_slippage_pct": max(
                0.0,
                float(
                    getattr(
                        self.settings,
                        "ibkr_execution_preflight_max_entry_slippage_pct",
                        0.0025,
                    )
                ),
            ),
            "max_entry_slippage_r": max(
                0.0,
                float(getattr(self.settings, "ibkr_execution_preflight_max_entry_slippage_r", 0.10)),
            ),
            "min_bid_size": max(
                0.0, float(getattr(self.settings, "ibkr_execution_preflight_min_bid_size", 100.0))
            ),
            "min_ask_size": max(
                0.0, float(getattr(self.settings, "ibkr_execution_preflight_min_ask_size", 100.0))
            ),
            "min_top_of_book_notional_usd": max(
                0.0,
                float(
                    getattr(
                        self.settings,
                        "ibkr_execution_preflight_min_top_of_book_notional_usd",
                        1000.0,
                    )
                ),
            ),
        }

    def _live_parent_whatif_preflight(
        self,
        *,
        ib,  # noqa: ANN001 - ib_insync client or test double
        contract: Any,
        signal: Signal,
        submitted_entry: float,
    ) -> dict[str, Any] | None:
        if not bool(getattr(self.settings, "ibkr_execution_preflight_whatif_enabled", True)):
            raise IBKRSafetyError("live IBKR execution requires WhatIf preflight enabled")
        order = self._build_parent_limit_order(signal)
        order.lmtPrice = _finite_price(submitted_entry, "submitted entry")
        try:
            state = ib.whatIfOrder(contract, order)
        except Exception as exc:  # noqa: BLE001 - fail closed before order placement.
            raise IBKRSafetyError(
                f"live IBKR execution WhatIf preflight failed: {type(exc).__name__}: {exc}"
            ) from exc
        return self._validate_live_whatif_state(state, signal=signal)

    def _validate_live_whatif_state(self, state: Any, *, signal: Signal) -> dict[str, Any]:
        warning_text = str(getattr(state, "warningText", "") or "").strip()
        if warning_text:
            raise IBKRSafetyError(
                f"live IBKR execution WhatIf preflight warning: {warning_text}"
            )
        status = str(getattr(state, "status", "") or "").strip()
        if status.lower() in {"inactive", "rejected", "cancelled", "apierror"}:
            raise IBKRSafetyError(f"live IBKR execution WhatIf preflight rejected status={status}")

        init_margin_before = _finite_whatif_number(
            getattr(state, "initMarginBefore", None),
            "initMarginBefore",
        )
        init_margin_change = _finite_whatif_number(
            getattr(state, "initMarginChange", None),
            "initMarginChange",
        )
        init_margin_after = _finite_whatif_number(
            getattr(state, "initMarginAfter", None),
            "initMarginAfter",
        )
        maint_margin_before = _finite_whatif_number(
            getattr(state, "maintMarginBefore", None),
            "maintMarginBefore",
        )
        maint_margin_change = _finite_whatif_number(
            getattr(state, "maintMarginChange", None),
            "maintMarginChange",
        )
        maint_margin_after = _finite_whatif_number(
            getattr(state, "maintMarginAfter", None),
            "maintMarginAfter",
        )
        equity_with_loan_before = _finite_whatif_number(
            getattr(state, "equityWithLoanBefore", None),
            "equityWithLoanBefore",
        )
        equity_with_loan_change = _finite_whatif_number(
            getattr(state, "equityWithLoanChange", None),
            "equityWithLoanChange",
        )
        equity_with_loan_after = _finite_whatif_number(
            getattr(state, "equityWithLoanAfter", None),
            "equityWithLoanAfter",
        )
        if init_margin_after < 0 or maint_margin_after < 0:
            raise IBKRSafetyError("live IBKR execution WhatIf preflight invalid margin fields")
        if equity_with_loan_after <= 0:
            raise IBKRSafetyError(
                "live IBKR execution WhatIf preflight rejected insufficient margin "
                "(equityWithLoanAfter <= 0)"
            )
        if equity_with_loan_after < init_margin_after:
            raise IBKRSafetyError(
                "live IBKR execution WhatIf preflight rejected insufficient margin "
                "(initMarginAfter exceeds equityWithLoanAfter)"
            )
        if equity_with_loan_after < maint_margin_after:
            raise IBKRSafetyError(
                "live IBKR execution WhatIf preflight rejected insufficient margin "
                "(maintMarginAfter exceeds equityWithLoanAfter)"
            )

        commission = _required_whatif_number(
            getattr(state, "commission", None),
            field="commission",
            allow_negative=False,
        )
        min_commission = _optional_whatif_number(
            getattr(state, "minCommission", None),
            "minCommission",
            allow_negative=False,
        )
        max_commission = _optional_whatif_number(
            getattr(state, "maxCommission", None),
            "maxCommission",
            allow_negative=False,
        )
        commission_values = [
            value for value in (commission, min_commission, max_commission) if value is not None
        ]
        checked_commission = max(commission_values)
        max_commission_usd = max(
            0.0,
            float(getattr(self.settings, "ibkr_execution_preflight_max_commission_usd", 5.0)),
        )
        if checked_commission > max_commission_usd:
            raise IBKRSafetyError(
                "live IBKR execution WhatIf preflight rejected commission USD "
                f"({checked_commission:.4f} > {max_commission_usd:.4f})"
            )
        risk_per_share = abs(float(signal.entry or 0.0) - float(signal.stop or 0.0))
        qty = abs(float(signal.suggested_qty or 0.0))
        risk_usd = risk_per_share * qty
        commission_r = checked_commission / risk_usd if risk_usd > 0 else None
        max_commission_r = max(
            0.0,
            float(getattr(self.settings, "ibkr_execution_preflight_max_commission_r", 0.05)),
        )
        if commission_r is None or commission_r > max_commission_r:
            raise IBKRSafetyError(
                "live IBKR execution WhatIf preflight rejected commission R "
                f"({commission_r!r} > {max_commission_r:.4f})"
            )
        return {
            "schema_version": 1,
            "data_basis": EXECUTION_PREFLIGHT_WHATIF_BASIS,
            "status": status,
            "warning_text": warning_text,
            "init_margin_before": round(init_margin_before, 4),
            "init_margin_change": round(init_margin_change, 4),
            "init_margin_after": round(init_margin_after, 4),
            "maint_margin_before": round(maint_margin_before, 4),
            "maint_margin_change": round(maint_margin_change, 4),
            "maint_margin_after": round(maint_margin_after, 4),
            "equity_with_loan_before": round(equity_with_loan_before, 4),
            "equity_with_loan_change": round(equity_with_loan_change, 4),
            "equity_with_loan_after": round(equity_with_loan_after, 4),
            "commission": round(commission, 4),
            "min_commission": round(min_commission, 4) if min_commission is not None else None,
            "max_commission": round(max_commission, 4) if max_commission is not None else None,
            "checked_commission": round(checked_commission, 4),
            "commission_r": round(float(commission_r), 6),
            "thresholds": {
                "max_commission_usd": max_commission_usd,
                "max_commission_r": max_commission_r,
            },
        }

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
        self._validate_final_live_risk(db, signal)
        ib = self._connect()
        try:
            self._validate_paper_account_target(ib)
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
            execution_preflight = self._live_execution_preflight(
                ib=ib,
                contract=contract,
                signal=signal,
                bracket_prices=bracket_prices,
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
            if execution_preflight is not None:
                execution_observation["execution_preflight"] = execution_preflight
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
                    "execution_preflight": execution_preflight,
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
                        "execution_preflight": execution_preflight,
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


def _validate_submitted_bracket_geometry(side: str, submitted: dict[str, Any]) -> None:
    entry = _finite_price(submitted.get("entry"), "submitted entry")
    stop = _finite_price(submitted.get("stop"), "submitted stop")
    target = _finite_price(submitted.get("target"), "submitted target")
    normalized_side = side.lower().strip()
    if normalized_side == "long" and not (stop < entry < target):
        raise IBKRSafetyError(
            "live execution preflight requires valid long bracket geometry"
        )
    if normalized_side == "short" and not (target < entry < stop):
        raise IBKRSafetyError(
            "live execution preflight requires valid short bracket geometry"
        )
    if normalized_side not in {"long", "short"}:
        raise IBKRSafetyError(f"unsupported signal side: {side}")


def _usable_market_price(value: Any) -> bool:
    number = _float_or_none(value)
    return number is not None and math.isfinite(number) and number > 0


def _clean_market_price(value: Any) -> float | None:
    number = _float_or_none(value)
    if number is None or not math.isfinite(number) or number <= 0:
        return None
    return round(number, 6)


def _clean_market_size(value: Any) -> float | None:
    number = _float_or_none(value)
    if number is None or not math.isfinite(number) or number < 0:
        return None
    return number


def _quote_timestamp(ticker: Any) -> datetime | None:
    for attr in ("time", "rtTime"):
        value = getattr(ticker, attr, None)
        parsed = _parse_quote_timestamp(value)
        if parsed is not None:
            return parsed
    return None


def _parse_quote_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)) or value <= 0:
            return None
        seconds = float(value) / 1000.0 if value > 1_000_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    try:
        text = str(value).strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (
        parsed.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None
        else parsed.astimezone(timezone.utc)
    )


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


def _finite_whatif_number(value: Any, field: str, *, allow_negative: bool = True) -> float:
    return _required_whatif_number(value, field, allow_negative=allow_negative)


def _required_whatif_number(value: Any, field: str, *, allow_negative: bool = True) -> float:
    number = _whatif_number_or_none(value)
    if number is None:
        raise IBKRSafetyError(f"live IBKR execution WhatIf preflight missing/invalid {field}")
    if not allow_negative and number < 0:
        raise IBKRSafetyError(f"live IBKR execution WhatIf preflight invalid {field}")
    return float(number)


def _optional_whatif_number(
    value: Any,
    field: str,
    *,
    allow_negative: bool = True,
) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    number = _whatif_number_or_none(value)
    if number is None:
        raise IBKRSafetyError(f"live IBKR execution WhatIf preflight invalid {field}")
    if not allow_negative and number < 0:
        raise IBKRSafetyError(f"live IBKR execution WhatIf preflight invalid {field}")
    return float(number)


def _whatif_number_or_none(value: Any) -> float | None:
    if isinstance(value, str):
        value = value.strip().replace(",", "")
    number = _float_or_none(value)
    if number is None or not math.isfinite(number):
        return None
    if abs(number) >= IBKR_UNSET_DOUBLE_ABS:
        return None
    return float(number)


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
