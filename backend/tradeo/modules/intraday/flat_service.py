from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class IntradayFlatState(str, Enum):
    NORMAL = "NORMAL"
    NO_NEW_ENTRIES = "NO_NEW_ENTRIES"
    CANCEL_ENTRIES = "CANCEL_ENTRIES"
    FLATTENING = "FLATTENING"
    VERIFY_FLAT = "VERIFY_FLAT"
    FLAT_CONFIRMED = "FLAT_CONFIRMED"
    FLAT_FAILED = "FLAT_FAILED"


@dataclass(frozen=True, slots=True)
class BrokerPosition:
    symbol: str
    qty: float


@dataclass(frozen=True, slots=True)
class ReduceOnlyOrder:
    symbol: str
    side: str
    qty: float
    reason: str
    preview: bool = False


class IntradayFlatBroker(Protocol):
    def cancel_open_entry_orders(self) -> list[str]: ...

    def snapshot_positions(self) -> list[BrokerPosition]: ...

    def submit_reduce_only_exit(self, order: ReduceOnlyOrder) -> str: ...

    def verify_flat_symbols(self, symbols: list[str]) -> bool: ...


@dataclass(frozen=True, slots=True)
class IntradayFlatResult:
    state: IntradayFlatState
    orders_submitted: tuple[str, ...] = ()
    cancelled_order_ids: tuple[str, ...] = ()
    unresolved_symbols: tuple[str, ...] = ()
    kill_switch_required: bool = False
    reason_code: str = "ok"


@dataclass(slots=True)
class IntradayEodFlatService:
    broker: IntradayFlatBroker
    state: IntradayFlatState = IntradayFlatState.NORMAL
    submitted_symbols: set[str] = field(default_factory=set)

    def advance(
        self,
        *,
        now: datetime | None = None,
        no_new_entries_at: datetime,
        cancel_entries_at: datetime,
        force_flat_start_at: datetime,
        hard_flat_deadline_at: datetime,
        preview: bool = False,
    ) -> IntradayFlatResult:
        current = _as_utc(now)
        if current >= hard_flat_deadline_at and self.state != IntradayFlatState.FLAT_CONFIRMED:
            if self.broker.verify_flat_symbols([]):
                self.state = IntradayFlatState.FLAT_CONFIRMED
                return IntradayFlatResult(state=self.state)
            self.state = IntradayFlatState.FLAT_FAILED
            return IntradayFlatResult(
                state=self.state,
                kill_switch_required=True,
                reason_code="hard_flat_deadline_unresolved",
            )
        if current >= force_flat_start_at:
            return self._flatten(preview=preview)
        if current >= cancel_entries_at:
            cancelled = tuple(self.broker.cancel_open_entry_orders())
            self.state = IntradayFlatState.CANCEL_ENTRIES
            return IntradayFlatResult(state=self.state, cancelled_order_ids=cancelled)
        if current >= no_new_entries_at:
            self.state = IntradayFlatState.NO_NEW_ENTRIES
            return IntradayFlatResult(state=self.state, reason_code="no_new_entries")
        self.state = IntradayFlatState.NORMAL
        return IntradayFlatResult(state=self.state)

    def _flatten(self, *, preview: bool) -> IntradayFlatResult:
        self.state = IntradayFlatState.FLATTENING
        order_ids: list[str] = []
        unresolved: list[str] = []
        positions = [p for p in self.broker.snapshot_positions() if abs(p.qty) > 0]
        for position in positions:
            symbol = position.symbol.upper()
            if symbol in self.submitted_symbols and not preview:
                continue
            side = "SELL" if position.qty > 0 else "BUY"
            order = ReduceOnlyOrder(
                symbol=symbol,
                side=side,
                qty=abs(position.qty),
                reason="intraday_eod_flat",
                preview=preview,
            )
            try:
                order_ids.append(self.broker.submit_reduce_only_exit(order))
                if not preview:
                    self.submitted_symbols.add(symbol)
            except Exception:  # noqa: BLE001 - broker failures are fail-closed.
                unresolved.append(symbol)
        if unresolved:
            self.state = IntradayFlatState.FLAT_FAILED
            return IntradayFlatResult(
                state=self.state,
                orders_submitted=tuple(order_ids),
                unresolved_symbols=tuple(sorted(unresolved)),
                kill_switch_required=True,
                reason_code="reduce_only_exit_failed",
            )
        self.state = IntradayFlatState.VERIFY_FLAT
        symbols = sorted({p.symbol.upper() for p in positions})
        if self.broker.verify_flat_symbols(symbols):
            self.state = IntradayFlatState.FLAT_CONFIRMED
            return IntradayFlatResult(state=self.state, orders_submitted=tuple(order_ids))
        return IntradayFlatResult(
            state=self.state,
            orders_submitted=tuple(order_ids),
            unresolved_symbols=tuple(symbols),
            reason_code="awaiting_flat_verification",
        )


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
