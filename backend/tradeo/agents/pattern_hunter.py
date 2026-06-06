from __future__ import annotations

from typing import Any

from tradeo.agents.base import AgentResult
from tradeo.services.pattern_detector import CupPatternDetector


class PatternHunterAgent:
    name = "pattern_hunter"

    def run(self, **kwargs: Any) -> AgentResult:
        symbol = str(kwargs["symbol"])
        df = kwargs["df"]
        candidate = CupPatternDetector().detect(symbol, df, timeframe=kwargs.get("timeframe", "1d"))
        return AgentResult(
            self.name,
            candidate is not None,
            "candidate found" if candidate else "no valid cup/base candidate",
            {"candidate": candidate.model_dump() if candidate else None},
        )
