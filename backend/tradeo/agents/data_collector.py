from __future__ import annotations

from typing import Any

from tradeo.agents.base import AgentResult
from tradeo.services.provider_factory import get_market_data_provider


class DataCollectorAgent:
    name = "data_collector"

    def run(self, **kwargs: Any) -> AgentResult:
        symbol = str(kwargs["symbol"])
        provider = get_market_data_provider()
        df = provider.fetch_ohlcv(symbol, kwargs.get("period", "2y"), kwargs.get("interval", "1d"))
        return AgentResult(self.name, True, f"Fetched {len(df)} bars for {symbol}", {"bars": len(df)})
