from __future__ import annotations

from typing import Any

from loguru import logger

from tradeo.core.config import Settings, get_settings
from tradeo.schemas import PatternCandidate, RiskDecision


class OpenAISupervisor:
    """Optional API supervisor using structured JSON output.

    This does not replace hard risk rules. It is a final qualitative reviewer for
    pattern viability, inconsistencies and audit notes. If disabled or unavailable,
    Tradeo falls back to deterministic supervision.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def review(self, candidate: PatternCandidate, risk: RiskDecision) -> dict[str, Any] | None:
        if not self.settings.openai_supervisor_enabled or not self.settings.openai_api_key:
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.settings.openai_api_key)
            import json

            schema = {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "pattern_viable": {"type": "boolean"},
                    "confidence_adjustment": {"type": "number", "minimum": -0.25, "maximum": 0.25},
                    "main_reason": {"type": "string"},
                    "red_flags": {"type": "array", "items": {"type": "string"}},
                    "required_human_checks": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "pattern_viable",
                    "confidence_adjustment",
                    "main_reason",
                    "red_flags",
                    "required_human_checks",
                ],
            }
            payload = {
                "candidate": candidate.model_dump(),
                "risk": risk.model_dump(),
                "policy": {
                    "min_reward_risk": self.settings.min_reward_risk,
                    "risk_per_trade_pct": self.settings.risk_per_trade_pct,
                    "live_trading_armed": self.settings.live_armed,
                },
            }
            response = client.responses.create(
                model=self.settings.openai_supervisor_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are Tradeo's final technical-pattern supervisor. "
                            "Assess only whether the supplied technical setup is internally coherent, "
                            "risk-controlled and audit-ready. Return JSON only."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload)},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "tradeo_supervisor_review",
                        "schema": schema,
                        "strict": True,
                    }
                },
                store=False,
            )
            return json.loads(response.output_text)
        except Exception as exc:  # noqa: BLE001
            logger.exception("OpenAI supervisor failed: {}", exc)
            return None
