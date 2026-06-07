from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from tradeo.core.security import require_admin
from tradeo.db.models import Signal
from tradeo.db.session import get_db
from tradeo.schemas import TradeOut
from tradeo.services.ibkr_broker import IBKRBroker, IBKRSafetyError
from tradeo.services.ibkr_data_provider import inspect_ibkr_connection

router = APIRouter(prefix="/ibkr", tags=["ibkr"])


class IBKRSignalOrderRequest(BaseModel):
    reason: str = Field(default="manual", max_length=300)


@router.get("/health")
def ibkr_health() -> dict[str, object]:
    """Read-only IBKR connectivity check."""
    return inspect_ibkr_connection()


@router.get("/account")
def ibkr_account(_: str = Depends(require_admin)) -> dict[str, object]:
    try:
        return IBKRBroker().account_snapshot()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/positions")
def ibkr_positions(_: str = Depends(require_admin)) -> list[dict[str, object]]:
    try:
        return IBKRBroker().positions()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/open-orders")
def ibkr_open_orders(_: str = Depends(require_admin)) -> list[dict[str, object]]:
    try:
        return IBKRBroker().open_orders()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/signals/{signal_id}/preview")
def ibkr_preview_signal_order(
    signal_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    signal = db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="signal not found")
    try:
        return IBKRBroker().preview_signal_order(signal)
    except IBKRSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/signals/{signal_id}/submit-bracket", response_model=TradeOut)
def ibkr_submit_signal_bracket(
    signal_id: int,
    request: IBKRSignalOrderRequest | None = None,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
):
    signal = db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="signal not found")
    try:
        return IBKRBroker().submit_signal_bracket(
            db,
            signal,
            reason=(request.reason if request else "manual"),
        )
    except IBKRSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
