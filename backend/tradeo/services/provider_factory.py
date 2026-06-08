from __future__ import annotations

from tradeo.core.config import get_settings
from tradeo.services.data_provider import MarketDataProvider
from tradeo.services.ibkr_data_provider import IBKRHistoricalDataProvider


def get_market_data_provider() -> MarketDataProvider:
    settings = get_settings()
    if settings.allow_synthetic_market_data:
        raise RuntimeError("Synthetic market data is forbidden")
    if settings.market_data_provider.lower() != "ibkr":
        raise RuntimeError("Tradeo only permits IBKR market data")
    return IBKRHistoricalDataProvider(settings=settings)
