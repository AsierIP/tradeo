from __future__ import annotations

import pandas as pd
import pytest

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
