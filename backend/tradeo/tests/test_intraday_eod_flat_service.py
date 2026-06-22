from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tradeo.modules.intraday.flat_service import (
    BrokerPosition,
    IntradayEodFlatService,
    IntradayFlatState,
)


NOW = datetime(2026, 6, 22, 19, 20, tzinfo=timezone.utc)


class BrokerMock:
    def __init__(self, positions, *, fail_symbols=None, flat_after_exit=True):
        self.positions = list(positions)
        self.fail_symbols = set(fail_symbols or [])
        self.flat_after_exit = flat_after_exit
        self.cancelled = []
        self.orders = []

    def cancel_open_entry_orders(self):
        self.cancelled.append("entry-1")
        return ["entry-1"]

    def snapshot_positions(self):
        return list(self.positions)

    def submit_reduce_only_exit(self, order):
        if order.symbol in self.fail_symbols:
            raise RuntimeError("reject")
        self.orders.append(order)
        if self.flat_after_exit and not order.preview:
            self.positions = [p for p in self.positions if p.symbol.upper() != order.symbol]
        return f"exit-{order.symbol}"

    def verify_flat_symbols(self, symbols):
        wanted = {symbol.upper() for symbol in symbols} if symbols else {p.symbol.upper() for p in self.positions}
        return all(abs(p.qty) == 0 or p.symbol.upper() not in wanted for p in self.positions)


def test_intraday_eod_flat_closes_long_and_short_reduce_only() -> None:
    broker = BrokerMock([BrokerPosition("SOUN", 10), BrokerPosition("RXRX", -4)])
    service = IntradayEodFlatService(broker)

    result = service.advance(
        now=NOW + timedelta(minutes=31),
        no_new_entries_at=NOW,
        cancel_entries_at=NOW + timedelta(minutes=20),
        force_flat_start_at=NOW + timedelta(minutes=30),
        hard_flat_deadline_at=NOW + timedelta(minutes=35),
    )

    assert result.state == IntradayFlatState.FLAT_CONFIRMED
    assert result.orders_submitted == ("exit-SOUN", "exit-RXRX")
    assert [(order.symbol, order.side, order.qty) for order in broker.orders] == [
        ("SOUN", "SELL", 10),
        ("RXRX", "BUY", 4),
    ]


def test_intraday_eod_flat_failure_requires_kill_switch() -> None:
    broker = BrokerMock([BrokerPosition("SOUN", 10)], fail_symbols={"SOUN"})
    service = IntradayEodFlatService(broker)

    result = service.advance(
        now=NOW + timedelta(minutes=31),
        no_new_entries_at=NOW,
        cancel_entries_at=NOW + timedelta(minutes=20),
        force_flat_start_at=NOW + timedelta(minutes=30),
        hard_flat_deadline_at=NOW + timedelta(minutes=35),
    )

    assert result.state == IntradayFlatState.FLAT_FAILED
    assert result.kill_switch_required is True
    assert result.reason_code == "reduce_only_exit_failed"


def test_intraday_eod_flat_state_cutoffs_are_ordered() -> None:
    broker = BrokerMock([])
    service = IntradayEodFlatService(broker)

    no_new = service.advance(
        now=NOW,
        no_new_entries_at=NOW,
        cancel_entries_at=NOW + timedelta(minutes=20),
        force_flat_start_at=NOW + timedelta(minutes=30),
        hard_flat_deadline_at=NOW + timedelta(minutes=35),
    )
    cancel = service.advance(
        now=NOW + timedelta(minutes=21),
        no_new_entries_at=NOW,
        cancel_entries_at=NOW + timedelta(minutes=20),
        force_flat_start_at=NOW + timedelta(minutes=30),
        hard_flat_deadline_at=NOW + timedelta(minutes=35),
    )

    assert no_new.state == IntradayFlatState.NO_NEW_ENTRIES
    assert cancel.state == IntradayFlatState.CANCEL_ENTRIES
    assert cancel.cancelled_order_ids == ("entry-1",)
