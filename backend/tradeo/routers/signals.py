from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from tradeo.core.security import require_admin
from tradeo.db.models import AuditLog, Signal, SignalStatus
from tradeo.db.session import get_db
from tradeo.schemas import SignalOut, TradeOut
from tradeo.services.paper_broker import PaperBroker

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[SignalOut])
def list_signals(_: str = Depends(require_admin), db: Session = Depends(get_db)) -> list[Signal]:
    return db.query(Signal).order_by(Signal.created_at.desc()).limit(200).all()


@router.post("/{signal_id}/human-approve", response_model=SignalOut)
def human_approve_signal(
    signal_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Signal:
    signal = db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(404, "signal not found")
    signal.human_approved = True
    if signal.status == SignalStatus.PENDING_HUMAN_APPROVAL:
        signal.status = SignalStatus.LIVE_APPROVED
    db.add(AuditLog(actor="human", action="signal_human_approved", entity_type="signal", entity_id=str(signal.id)))
    db.commit()
    db.refresh(signal)
    return signal


@router.post("/{signal_id}/paper-execute", response_model=TradeOut)
def paper_execute_signal(
    signal_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    signal = db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(404, "signal not found")
    return PaperBroker().execute_signal(db, signal)
