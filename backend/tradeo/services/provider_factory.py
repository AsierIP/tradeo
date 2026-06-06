from __future__ import annotations

from tradeo.core.config import get_settings
from tradeo.services.data_provider import MarketDataProvider, YFinanceProvider
from tradeo.services.ibkr_data_provider import IBKRHistoricalDataProvider


def get_market_data_provider() -> MarketDataProvider:
    settings = get_settings()
    if settings.market_data_provider.lower() == "ibkr":
        return IBKRHistoricalDataProvider(settings=settings)
    return YFinanceProvider()
