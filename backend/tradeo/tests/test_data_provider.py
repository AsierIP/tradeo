from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from tradeo.core.config import Settings
from tradeo.services.ibkr_data_provider import inspect_ibkr_connection
from tradeo.services.data_provider import YFinanceProvider


def test_yfinance_provider_does_not_use_synthetic_fallback_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tradeo.services.data_provider.yf.download", lambda *args, **kwargs: pd.DataFrame())

    with pytest.raises(ValueError, match="empty dataset"):
        YFinanceProvider().fetch_ohlcv("NARI")


def test_yfinance_provider_can_use_synthetic_fallback_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tradeo.services.data_provider.yf.download", lambda *args, **kwargs: pd.DataFrame())

    df = YFinanceProvider(allow_synthetic_fallback=True).fetch_ohlcv("DEMO")

    assert not df.empty
    assert {"open", "high", "low", "close", "volume"}.issubset(df.columns)


def test_ibkr_health_check_is_readonly(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeIB:
        def __init__(self) -> None:
            self.connected = False

        def connect(self, host: str, port: int, clientId: int, timeout: int) -> None:  # noqa: N803
            self.connected = True

        def reqCurrentTime(self) -> datetime:
            return datetime(2026, 6, 6, tzinfo=timezone.utc)

        def managedAccounts(self) -> list[str]:
            return ["DU123456"]

        def accountSummary(self, account: str) -> list[SimpleNamespace]:
            return [
                SimpleNamespace(tag="NetLiquidation", value="100000", currency="USD"),
                SimpleNamespace(tag="BuyingPower", value="200000", currency="USD"),
            ]

        def isConnected(self) -> bool:  # noqa: N802
            return self.connected

        def disconnect(self) -> None:
            self.connected = False

    monkeypatch.setitem(__import__("sys").modules, "ib_insync", SimpleNamespace(IB=FakeIB))

    status = inspect_ibkr_connection(
        Settings(
            ibkr_host="127.0.0.1",
            ibkr_port=7497,
            ibkr_client_id=17,
            ibkr_readonly=True,
            ibkr_account="DU123456",
        )
    )

    assert status["ok"] is True
    assert status["readonly"] is True
    assert status["live_armed"] is False
    assert status["account_summary"]["NetLiquidation"] == "100000 USD"
