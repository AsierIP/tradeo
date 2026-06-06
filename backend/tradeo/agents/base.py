from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class AgentResult:
    agent: str
    ok: bool
    summary: str
    payload: dict[str, Any]


class Agent(Protocol):
    name: str

    def run(self, **kwargs: Any) -> AgentResult:
        ...
