from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from tradeo.core.config import Settings
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.ibkr_data_provider import inspect_ibkr_connection


def test_settings_reject_synthetic_market_data() -> None:
    with pytest.raises(ValueError, match="Synthetic market data is forbidden"):
        Settings(allow_synthetic_market_data=True)


def test_settings_reject_non_ibkr_market_data_provider() -> None:
    with pytest.raises(ValueError, match="only permits IBKR market data"):
        Settings(market_data_provider="yfinance")


def test_market_data_factory_returns_ibkr_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADEO_MARKET_DATA_PROVIDER", "ibkr")
    monkeypatch.setenv("TRADEO_ALLOW_SYNTHETIC_MARKET_DATA", "false")
    from tradeo.core.config import get_settings

    get_settings.cache_clear()
    try:
        provider = get_market_data_provider()
    finally:
        get_settings.cache_clear()

    assert provider.__class__.__name__ == "IBKRHistoricalDataProvider"


class FakeIB:
    account_summary_calls = 0

    def __init__(self) -> None:
        self.connected = False

    def connect(self, host: str, port: int, clientId: int, timeout: int) -> None:  # noqa: N803
        self.connected = True

    def reqCurrentTime(self) -> datetime:  # noqa: N802
        return datetime(2026, 6, 6, tzinfo=timezone.utc)

    def managedAccounts(self) -> list[str]:  # noqa: N802
        return ["REDACTED_ACCOUNT"]

    def accountSummary(self, account: str) -> list[SimpleNamespace]:  # noqa: N802
        type(self).account_summary_calls += 1
        raise AssertionError("public health check must not request account summary")

    def isConnected(self) -> bool:  # noqa: N802
        return self.connected

    def disconnect(self) -> None:
        self.connected = False


def test_ibkr_health_check_omits_account_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeIB.account_summary_calls = 0
    monkeypatch.setitem(sys.modules, "ib_insync", SimpleNamespace(IB=FakeIB))

    status = inspect_ibkr_connection(
        Settings(
            ibkr_host="127.0.0.1",
            ibkr_port=7497,
            ibkr_client_id=17,
            ibkr_readonly=True,
            ibkr_account="REDACTED_ACCOUNT",
        )
    )

    assert status["ok"] is True
    assert status["readonly"] is True
    assert status["live_armed"] is False
    assert status["managed_accounts_count"] == 1
    assert status["selected_account_configured"] is True
    assert status["account_summary_included"] is False
    assert "account_summary" not in status
    assert FakeIB.account_summary_calls == 0
