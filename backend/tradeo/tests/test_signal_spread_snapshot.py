"""Per-signal spread snapshot tests (informe §3.3.1)."""

from __future__ import annotations

import pytest

from tradeo.core.config import Settings
from tradeo.db.models import DiscoveredPatternStatus, Signal
from tradeo.services.market_quotes import QuoteSnapshot, capture_signal_spread_snapshot
from tradeo.tests.test_pattern_entry_scanner import (
    FixtureProvider,
    add_pattern,
    scanner,
    session_factory,
)


class FakeQuoteProvider:
    def __init__(self, bid: float | None = 9.98, ask: float | None = 10.02, last: float | None = 10.0):
        self.bid, self.ask, self.last = bid, ask, last
        self.calls: list[str] = []

    def snapshot(self, symbol: str) -> QuoteSnapshot:
        self.calls.append(symbol)
        return QuoteSnapshot(symbol=symbol, bid=self.bid, ask=self.ask, last=self.last)


class FailingQuoteProvider:
    def snapshot(self, symbol: str) -> QuoteSnapshot:
        raise ConnectionError("TWS unreachable")


def _settings(**overrides) -> Settings:
    return Settings(signal_spread_snapshot_enabled=True, **overrides)


def test_snapshot_records_observed_spread_and_cost_in_r() -> None:
    record = capture_signal_spread_snapshot(
        symbol="labx",
        entry=10.0,
        stop=9.0,
        settings=_settings(),
        provider=FakeQuoteProvider(bid=9.98, ask=10.02),
    )
    assert record["available"] is True
    assert record["symbol"] == "LABX"
    assert record["bid"] == 9.98
    assert record["ask"] == 10.02
    assert record["mid"] == 10.0
    assert record["spread_abs"] == pytest.approx(0.04)
    assert record["spread_observed_pct"] == pytest.approx(0.04 / 10.0, rel=1e-6)
    assert record["spread_cost_r"] == pytest.approx(0.04 / 1.0, rel=1e-6)
    assert record["data_basis"] == "ibkr_quote_snapshot_at_signal"
    # One snapshot is not a microstructure feed: the honest marker stays.
    assert record["microstructure_feed"] == "none_available"
    assert record["schema_version"] == 1


def test_snapshot_is_fail_soft_on_provider_error() -> None:
    record = capture_signal_spread_snapshot(
        symbol="LABX",
        entry=10.0,
        stop=9.0,
        settings=_settings(),
        provider=FailingQuoteProvider(),
    )
    assert record["available"] is False
    assert record["reason"].startswith("snapshot_failed: ConnectionError")
    assert record["spread_observed_pct"] is None


def test_snapshot_disabled_flag_short_circuits() -> None:
    record = capture_signal_spread_snapshot(
        symbol="LABX",
        entry=10.0,
        stop=9.0,
        settings=Settings(signal_spread_snapshot_enabled=False),
        provider=FailingQuoteProvider(),  # must not even be called
    )
    assert record["available"] is False
    assert record["reason"] == "disabled"


def test_snapshot_without_usable_bid_ask_is_marked_unavailable() -> None:
    record = capture_signal_spread_snapshot(
        symbol="LABX",
        entry=10.0,
        stop=9.0,
        settings=_settings(),
        provider=FakeQuoteProvider(bid=None, ask=10.02, last=10.0),
    )
    assert record["available"] is False
    assert record["reason"] == "no_usable_bid_ask"
    assert record["last"] == 10.0


def test_stored_signal_carries_spread_snapshot() -> None:
    """End to end: the lab scanner persists the snapshot on the signal."""
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    quote_provider = FakeQuoteProvider(bid=9.98, ask=10.02)
    sc = scanner(provider, signal_spread_snapshot_enabled=True)
    sc.quote_provider = quote_provider

    result = sc.scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )

    assert result["signals_created"] == 1
    assert quote_provider.calls  # snapshot requested at signal time
    signal = db.get(Signal, result["signal_ids"][0])
    snapshot = signal.metadata_json["spread_snapshot"]
    assert snapshot["available"] is True
    assert snapshot["spread_observed_pct"] == pytest.approx(0.004, rel=1e-6)
    assert signal.metadata_json["spread_observed_pct"] == snapshot["spread_observed_pct"]


def test_stored_signal_survives_snapshot_failure() -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    sc = scanner(provider, signal_spread_snapshot_enabled=True)
    sc.quote_provider = FailingQuoteProvider()

    result = sc.scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )

    assert result["signals_created"] == 1
    signal = db.get(Signal, result["signal_ids"][0])
    snapshot = signal.metadata_json["spread_snapshot"]
    assert snapshot["available"] is False
    assert snapshot["reason"].startswith("snapshot_failed")
    assert signal.metadata_json["spread_observed_pct"] is None
