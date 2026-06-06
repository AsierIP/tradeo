from __future__ import annotations

from typing import Any

from tradeo.agents.base import AgentResult
from tradeo.services.risk_manager import RiskManager


class RiskAgent:
    name = "risk_agent"

    def run(self, **kwargs: Any) -> AgentResult:
        decision = RiskManager().validate_candidate(kwargs["candidate"], kwargs.get("db"))
        return AgentResult(self.name, decision.approved, decision.reason, {"risk": decision.model_dump()})
