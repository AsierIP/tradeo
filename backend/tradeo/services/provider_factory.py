from __future__ import annotations

from tradeo.core.config import get_settings
from tradeo.services.data_provider import CachedMarketDataProvider, MarketDataProvider
from tradeo.services.ibkr_data_provider import IBKRHistoricalDataProvider


def get_market_data_provider() -> MarketDataProvider:
    settings = get_settings()
    if settings.allow_synthetic_market_data:
        raise RuntimeError("Synthetic market data is forbidden")
    if settings.market_data_provider.lower() != "ibkr":
        raise RuntimeError("Tradeo only permits IBKR market data")
    upstream = IBKRHistoricalDataProvider(settings=settings)
    if not settings.market_data_cache_enabled:
        return upstream
    return CachedMarketDataProvider(
        upstream=upstream,
        cache_dir=settings.market_data_cache_path,
        adjusted=settings.market_data_adjusted,
        what_to_show=settings.market_data_what_to_show,
    )
