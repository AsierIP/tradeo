from __future__ import annotations

from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, Signal, SignalStatus
from tradeo.schemas import PatternCandidate, SupervisorDecision
from tradeo.services.openai_supervisor import OpenAISupervisor
from tradeo.services.risk_manager import RiskManager


class TradeSupervisor:
    """Final deterministic + optional LLM supervision layer."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.risk = RiskManager(self.settings)
        self.llm = OpenAISupervisor(self.settings)

    def review_candidate(self, candidate: PatternCandidate, db: Session | None = None) -> SupervisorDecision:
        risk = self.risk.validate_candidate(candidate, db)
        llm_review = self.llm.review(candidate, risk)
        confidence = candidate.confidence
        notes = "; ".join(candidate.notes)
        if llm_review:
            confidence = max(0.0, min(0.99, confidence + float(llm_review["confidence_adjustment"])))
            notes = f"{notes}; supervisor_api: {llm_review['main_reason']}"
            if not llm_review["pattern_viable"]:
                risk.approved = False
                risk.hard_rejections.append("supervisor_api_rejected")
                risk.reason = "supervisor_api_rejected"

        if risk.approved and confidence >= 0.70:
            if self.settings.trading_mode == "live" and self.settings.live_armed:
                status = SignalStatus.PENDING_HUMAN_APPROVAL.value
                eligible_live = True
            else:
                status = SignalStatus.PAPER_APPROVED.value
                eligible_live = False
            approved_paper = True
        elif risk.approved:
            status = SignalStatus.WATCHLIST.value
            eligible_live = False
            approved_paper = False
        else:
            status = SignalStatus.REJECTED.value
            eligible_live = False
            approved_paper = False

        return SupervisorDecision(
            approved_for_paper=approved_paper,
            eligible_for_live_review=eligible_live,
            status=status,
            confidence=round(confidence, 4),
            notes=notes or risk.reason,
            risk=risk,
            candidate=candidate,
        )

    def store_decision(self, decision: SupervisorDecision, db: Session) -> Signal | None:
        if decision.status == SignalStatus.REJECTED.value:
            db.add(
                AuditLog(
                    actor="supervisor",
                    action="candidate_rejected",
                    entity_type="signal",
                    details_json=decision.model_dump(mode="json"),
                )
            )
            db.commit()
            return None
        c = decision.candidate
        signal = Signal(
            symbol=c.symbol,
            pattern=c.pattern,
            side=c.side,
            timeframe=c.timeframe,
            entry=c.entry,
            stop=c.stop,
            target=c.target,
            reward_risk=c.reward_risk,
            confidence=decision.confidence,
            composite_score=c.composite_score,
            risk_usd=decision.risk.risk_usd,
            suggested_qty=decision.risk.suggested_qty,
            status=SignalStatus(decision.status),
            supervisor_notes=decision.notes,
            strategy_version="cup_v0",
            metadata_json={"candidate": c.model_dump(mode="json"), "risk": decision.risk.model_dump(mode="json")},
        )
        db.add(signal)
        db.add(
            AuditLog(
                actor="supervisor",
                action="signal_stored",
                entity_type="signal",
                details_json=decision.model_dump(mode="json"),
            )
        )
        db.commit()
        db.refresh(signal)
        return signal
