from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tradeo.core.security import require_admin
from tradeo.db.session import get_db
from tradeo.modules.resource_policy.market_session_resource_policy import JobType
from tradeo.routers.resource_policy_guard import assert_route_job_allowed
from tradeo.schemas import SelfImprovementResponse
from tradeo.services.self_improvement import SelfImprovementEngine

router = APIRouter(prefix="/self-improvement", tags=["self-improvement"])


@router.post("/run", response_model=SelfImprovementResponse)
def run_self_improvement(
    max_symbols: int = 25,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SelfImprovementResponse:
    assert_route_job_allowed(JobType.HEAVY_BACKTEST, "research")
    return SelfImprovementEngine().run_lab_cycle(db, max_symbols=max_symbols)
