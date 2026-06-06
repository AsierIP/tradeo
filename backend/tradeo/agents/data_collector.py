from __future__ import annotations

from typing import Any

from tradeo.agents.base import AgentResult
from tradeo.services.data_provider import YFinanceProvider


class DataCollectorAgent:
    name = "data_collector"

    def run(self, **kwargs: Any) -> AgentResult:
        symbol = str(kwargs["symbol"])
        provider = YFinanceProvider()
        df = provider.fetch_ohlcv(symbol, kwargs.get("period", "2y"), kwargs.get("interval", "1d"))
        return AgentResult(self.name, True, f"Fetched {len(df)} bars for {symbol}", {"bars": len(df)})
