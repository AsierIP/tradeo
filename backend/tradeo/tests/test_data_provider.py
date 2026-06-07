from __future__ import annotations

import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from tradeo.core.config import Settings
from tradeo.services.data_provider import YFinanceProvider
from tradeo.services.ibkr_data_provider import inspect_ibkr_connection


def test_yfinance_provider_does_not_use_synthetic_fallback_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tradeo.services.data_provider.yf.download", lambda *args, **kwargs: pd.DataFrame())

    with pytest.raises(ValueError, match="empty dataset"):
        YFinanceProvider().fetch_ohlcv("NARI")


def test_yfinance_provider_can_use_synthetic_fallback_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tradeo.services.data_provider.yf.download", lambda *args, **kwargs: pd.DataFrame())

    df = YFinanceProvider(allow_synthetic_fallback=True).fetch_ohlcv("DEMO")

    assert not df.empty
    assert {"open", "high", "low", "close", "volume"}.issubset(df.columns)


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
