from __future__ import annotations

from typing import Any

from tradeo.agents.base import AgentResult
from tradeo.services.supervisor import TradeSupervisor


class SupervisorAgent:
    name = "supervisor_agent"

    def run(self, **kwargs: Any) -> AgentResult:
        decision = TradeSupervisor().review_candidate(kwargs["candidate"], kwargs.get("db"))
        return AgentResult(
            self.name,
            decision.approved_for_paper,
            decision.notes,
            {"decision": decision.model_dump()},
        )
