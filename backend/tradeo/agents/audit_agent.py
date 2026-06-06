from __future__ import annotations

from typing import Any

from tradeo.agents.base import AgentResult
from tradeo.services.reports import ReportService


class AuditAgent:
    name = "audit_agent"

    def run(self, **kwargs: Any) -> AgentResult:
        pack = ReportService().generate_review_pack(kwargs["db"])
        return AgentResult(self.name, True, "review pack generated", {"paths": pack.get("paths")})
