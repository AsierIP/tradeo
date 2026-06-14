from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from tradeo.core.security import require_admin
from tradeo.db.models import Signal
from tradeo.db.session import SessionLocal
from tradeo.schemas import TradeOut
from tradeo.services.ibkr_broker import IBKRBroker, IBKROperationalError, IBKRSafetyError
from tradeo.services.ibkr_data_provider import inspect_ibkr_connection
from tradeo.services.order_outcomes import mark_signal_order_failure

router = APIRouter(prefix="/ibkr", tags=["ibkr"])


class IBKRSignalOrderRequest(BaseModel):
    reason: str = Field(default="manual", max_length=300)


async def _run_ibkr_call(func, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
    return await run_in_threadpool(func, *args, **kwargs)


@router.get("/health")
async def ibkr_health() -> dict[str, object]:
    """Read-only IBKR connectivity check."""
    return await _run_ibkr_call(inspect_ibkr_connection)


@router.get("/account")
async def ibkr_account(_: str = Depends(require_admin)) -> dict[str, object]:
    try:
        return await _run_ibkr_call(IBKRBroker().account_snapshot)
    except (IBKROperationalError, RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/positions")
async def ibkr_positions(_: str = Depends(require_admin)) -> list[dict[str, object]]:
    try:
        return await _run_ibkr_call(IBKRBroker().positions)
    except (IBKROperationalError, RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/open-orders")
async def ibkr_open_orders(_: str = Depends(require_admin)) -> list[dict[str, object]]:
    try:
        return await _run_ibkr_call(IBKRBroker().open_orders)
    except (IBKROperationalError, RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/signals/{signal_id}/preview")
async def ibkr_preview_signal_order(
    signal_id: int,
    _: str = Depends(require_admin),
) -> dict[str, object]:
    try:
        return await _run_ibkr_call(_preview_signal_order_sync, signal_id)
    except IBKRSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IBKROperationalError, RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/signals/{signal_id}/submit-bracket", response_model=TradeOut)
async def ibkr_submit_signal_bracket(
    signal_id: int,
    request: IBKRSignalOrderRequest | None = None,
    _: str = Depends(require_admin),
):
    try:
        return await _run_ibkr_call(
            _submit_signal_bracket_sync,
            signal_id,
            request.reason if request else "manual",
        )
    except IBKRSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (IBKROperationalError, RuntimeError, ValueError, OSError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _preview_signal_order_sync(signal_id: int) -> dict[str, object]:
    db = SessionLocal()
    try:
        signal = db.get(Signal, signal_id)
        if not signal:
            raise LookupError("signal not found")
        return IBKRBroker().preview_signal_order(signal)
    finally:
        db.close()


def _submit_signal_bracket_sync(signal_id: int, reason: str):
    db = SessionLocal()
    try:
        signal = db.get(Signal, signal_id)
        if not signal:
            raise LookupError("signal not found")
        try:
            return IBKRBroker().submit_signal_bracket(db, signal, reason=reason)
        except IBKRSafetyError as exc:
            mark_signal_order_failure(signal, str(exc))
            db.commit()
            raise
        except (IBKROperationalError, RuntimeError, ValueError, OSError) as exc:
            mark_signal_order_failure(signal, str(exc))
            db.commit()
            raise
    finally:
        db.close()
