from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tradeo.core.security import require_admin
from tradeo.db.session import get_db
from tradeo.modules.resource_policy.market_session_resource_policy import JobType
from tradeo.routers.resource_policy_guard import assert_route_job_allowed
from tradeo.schemas import ScanRequest, ScanResponse
from tradeo.services.scanner import MarketScanner

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", response_model=ScanResponse)
def run_scan(
    request: ScanRequest,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ScanResponse:
    assert_route_job_allowed(JobType.LARGE_SCANNER, "scanner")
    scanner = MarketScanner()
    return scanner.run(request, db=db, store=True)
