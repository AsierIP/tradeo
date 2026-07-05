"""Daily swing research infrastructure helpers."""

__all__ = [
    "bars_to_cache_frame",
    "build_daily_universes",
    "cache_daily_ohlcv",
    "check_daily_ohlcv_quality",
    "classify_symbol_quality",
]


def __getattr__(name: str):
    if name in __all__:
        from tradeo.modules.daily_swing import dss_003

        return getattr(dss_003, name)
    raise AttributeError(name)
