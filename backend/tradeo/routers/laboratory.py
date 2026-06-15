from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from tradeo.core.security import require_admin
from tradeo.db.session import get_db
from tradeo.modules.laboratory.diagnostics import laboratory_diagnostics
from tradeo.modules.laboratory.scanner import LaboratoryScanner
from tradeo.modules.shared.entry_scanner import PatternEntryScannerSafetyError
from tradeo.schemas import LabDiagnosticsResponse, PatternEntryScanRequest, PatternEntryScanResponse
from tradeo.services.module_dashboard import module_overview

router = APIRouter(prefix="/laboratory", tags=["laboratory"])


@router.get("/status")
def laboratory_status(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return LaboratoryScanner().status(db)


@router.get("/overview")
def laboratory_overview(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return module_overview(db, "laboratory")


@router.get("/diagnostics", response_model=LabDiagnosticsResponse)
def laboratory_diagnostics_view(
    limit: int = Query(default=24, ge=1, le=100),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LabDiagnosticsResponse:
    return LabDiagnosticsResponse(**laboratory_diagnostics(db, limit=limit))


@router.post("/scan", response_model=PatternEntryScanResponse)
def scan_laboratory(
    request: PatternEntryScanRequest | None = None,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PatternEntryScanResponse:
    request = request or PatternEntryScanRequest()
    try:
        result = LaboratoryScanner().scan(
            db,
            symbols=request.symbols,
            limit=request.limit,
            max_patterns=request.max_patterns,
            max_results=request.max_results,
            similarity_threshold=request.similarity_threshold,
            store_signals=request.store_signals,
            execute_orders=request.execute_orders,
        )
    except PatternEntryScannerSafetyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PatternEntryScanResponse(**result)
