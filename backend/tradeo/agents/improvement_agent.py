from __future__ import annotations

from typing import Any

from tradeo.agents.base import AgentResult
from tradeo.services.self_improvement import SelfImprovementEngine


class ImprovementAgent:
    name = "improvement_agent"

    def run(self, **kwargs: Any) -> AgentResult:
        result = SelfImprovementEngine().run_lab_cycle(kwargs["db"], max_symbols=kwargs.get("max_symbols", 25))
        return AgentResult(self.name, True, "lab cycle completed", result.model_dump())
