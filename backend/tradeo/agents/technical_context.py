from __future__ import annotations

from typing import Any

from tradeo.agents.base import AgentResult
from tradeo.services.technical_indicators import sma


class TechnicalContextAgent:
    name = "technical_context"

    def run(self, **kwargs: Any) -> AgentResult:
        df = kwargs["df"].copy()
        df["sma50"] = sma(df["close"], 50)
        df["sma200"] = sma(df["close"], 200)
        last = df.iloc[-1]
        regime = "neutral"
        if last["close"] > last["sma50"] and last["close"] > last["sma200"]:
            regime = "technical_uptrend"
        elif last["close"] < last["sma50"] and last["close"] < last["sma200"]:
            regime = "technical_downtrend"
        return AgentResult(self.name, True, f"Regime: {regime}", {"regime": regime})
