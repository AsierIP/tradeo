from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from tradeo.services import ibkr_data_provider
from tradeo.services.ibkr_data_provider import (
    IBKRHistoricalDataProvider,
    _bar_size_from_interval,
    _duration_from_period,
)


class DummyIB:
    def disconnect(self) -> None:
        return None


def test_ibkr_provider_sets_event_loop_before_thread_import(monkeypatch) -> None:
    def fake_connect(settings):  # noqa: ANN001
        return DummyIB(), 123

    monkeypatch.setattr(ibkr_data_provider, "_connect_ibkr", fake_connect)

    def fetch_in_thread() -> None:
        provider = IBKRHistoricalDataProvider()
        try:
            provider.fetch_ohlcv("TMDX", period="3mo", interval="1d")
        except AttributeError:
            pass

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(fetch_in_thread).result()


def test_ibkr_bar_size_accepts_interval_aliases() -> None:
    assert _bar_size_from_interval("1 day") == "1 day"
    assert _bar_size_from_interval("5 min") == "5 mins"
    assert _bar_size_from_interval("15 mins") == "15 mins"
    assert _bar_size_from_interval("60 min") == "1 hour"


def test_ibkr_duration_uses_years_for_long_month_ranges() -> None:
    assert _duration_from_period("12mo") == "12 M"
    assert _duration_from_period("13mo") == "2 Y"
    assert _duration_from_period("18mo") == "2 Y"
    assert _duration_from_period("24mo") == "2 Y"
