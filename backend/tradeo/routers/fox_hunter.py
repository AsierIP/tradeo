from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from tradeo.core.security import require_admin
from tradeo.db.session import get_db
from tradeo.modules.fox_hunter.scanner import FoxHunterScanner
from tradeo.modules.shared.entry_scanner import PatternEntryScannerSafetyError
from tradeo.schemas import PatternEntryScanRequest, PatternEntryScanResponse
from tradeo.services.module_dashboard import module_overview

router = APIRouter(prefix="/fox-hunter", tags=["fox-hunter"])


@router.get("/status")
def fox_hunter_status(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return FoxHunterScanner().status(db)


@router.get("/overview")
def fox_hunter_overview(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return module_overview(db, "fox_hunter")


@router.post("/scan", response_model=PatternEntryScanResponse)
def scan_fox_hunter(
    request: PatternEntryScanRequest | None = None,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PatternEntryScanResponse:
    request = request or PatternEntryScanRequest()
    try:
        result = FoxHunterScanner().scan(
            db,
            symbols=request.symbols,
            limit=request.limit,
            max_patterns=request.max_patterns,
            similarity_threshold=request.similarity_threshold,
            store_signals=request.store_signals,
            execute_orders=request.execute_orders,
        )
    except PatternEntryScannerSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PatternEntryScanResponse(**result)
