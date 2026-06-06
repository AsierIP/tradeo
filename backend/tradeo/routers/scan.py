from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tradeo.core.security import require_admin
from tradeo.db.session import get_db
from tradeo.schemas import ScanRequest, ScanResponse
from tradeo.services.scanner import MarketScanner

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", response_model=ScanResponse)
def run_scan(
    request: ScanRequest,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ScanResponse:
    scanner = MarketScanner()
    return scanner.run(request, db=db, store=True)
