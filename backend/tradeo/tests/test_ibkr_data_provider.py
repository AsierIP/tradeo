from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from tradeo.services import ibkr_data_provider
from tradeo.services.ibkr_data_provider import IBKRHistoricalDataProvider


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
