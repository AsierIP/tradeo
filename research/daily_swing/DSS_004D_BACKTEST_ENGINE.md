# DSS-004D Backtest Engine

The engine runs ALL_EVENTS, ONE_ACTIVE_PER_SYMBOL, and MAX_2_NEW_TRADES_PER_DAY_SIM from cache only. MAX_2 prioritizes lower ATR14_pct(t-1) because no reliable liquidity field is available in the pilot cache.
