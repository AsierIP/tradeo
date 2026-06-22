from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from tradeo.core.config import Settings, get_settings
from tradeo.core.security import require_admin
from tradeo.modules.intraday.flat_service import BrokerPosition, IntradayEodFlatService, ReduceOnlyOrder
from tradeo.services.ibkr_pacing import IbkrPacingBudget
from tradeo.services.runtime_status import intraday_session_status

router = APIRouter(prefix="/intraday", tags=["intraday"])


@router.get("/status")
def intraday_status(_: str = Depends(require_admin), settings: Settings = Depends(get_settings)) -> dict:
    return {
        "config": {
            "enabled": settings.intraday_enabled,
            "shadow_enabled": settings.intraday_shadow_enabled,
            "paper_enabled": settings.intraday_paper_enabled,
            "live_enabled": settings.intraday_live_enabled,
            "live_armed": settings.intraday_live_armed,
            "timeframes": settings.intraday_timeframe_list,
        },
        "session": intraday_session_status(settings),
    }


@router.get("/pacing")
def intraday_pacing(_: str = Depends(require_admin)) -> dict:
    return IbkrPacingBudget().metrics()


@router.get("/risk")
def intraday_risk(_: str = Depends(require_admin)) -> dict:
    return {"scope": "intraday", "status": "not_started", "reason": "no_active_session"}


@router.get("/flat/status")
def intraday_flat_status(_: str = Depends(require_admin), settings: Settings = Depends(get_settings)) -> dict:
    session = intraday_session_status(settings)
    return {"enabled": settings.intraday_eod_flat_enabled, "session": session}


@router.post("/flat/preview")
def intraday_flat_preview(_: str = Depends(require_admin)) -> dict:
    broker = _PreviewBroker([])
    service = IntradayEodFlatService(broker)
    result = service._flatten(preview=True)  # preview only; no real broker adapter is wired here.
    return {
        "ok": True,
        "preview": True,
        "state": result.state,
        "orders": [order.__dict__ for order in broker.orders],
        "reason_code": result.reason_code,
    }


@router.post("/flat/request")
def intraday_flat_request(_: str = Depends(require_admin), settings: Settings = Depends(get_settings)) -> dict:
    if not settings.intraday_enabled or not settings.intraday_eod_flat_enabled:
        raise HTTPException(status_code=409, detail="intraday flat request is not armed")
    raise HTTPException(status_code=409, detail="broker-backed flat request is not implemented; use preview")


class _PreviewBroker:
    def __init__(self, positions: list[BrokerPosition]) -> None:
        self.positions = positions
        self.orders: list[ReduceOnlyOrder] = []

    def cancel_open_entry_orders(self) -> list[str]:
        return []

    def snapshot_positions(self) -> list[BrokerPosition]:
        return list(self.positions)

    def submit_reduce_only_exit(self, order: ReduceOnlyOrder) -> str:
        self.orders.append(order)
        return f"preview-{order.symbol}"

    def verify_flat_symbols(self, symbols: list[str]) -> bool:
        return not symbols
