from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from tradeo.core.security import require_admin
from tradeo.db.session import get_db
from tradeo.services.reports import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate")
def generate_report(_: str = Depends(require_admin), db: Session = Depends(get_db)) -> dict:
    return ReportService().generate_review_pack(db)


@router.get("/latest")
def latest_report(_: str = Depends(require_admin)) -> dict:
    report = ReportService().latest_report()
    if not report:
        raise HTTPException(404, "no report generated yet")
    return report
