from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import not_
from sqlalchemy.orm import Session, selectinload

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import get_settings
from tradeo.core.security import require_admin
from tradeo.db.models import (
    DiscoveredPattern,
    DiscoveredPatternExample,
    DiscoveredPatternMatch,
    DiscoveredPatternMetric,
    DiscoveredPatternStatus,
    DiscoveryRun,
)
from tradeo.db.session import get_db
from tradeo.research.autonomous_research_director import ResearchDirector
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.novel_pattern_registry import NovelPatternRegistry
from tradeo.services.director_review_gate import DirectorReviewGate
from tradeo.schemas import (
    DiscoveredPatternDetailOut,
    DiscoveredPatternExampleOut,
    DiscoveredPatternMetricOut,
    DiscoveredPatternOut,
    DiscoveryRunOut,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
    NovelPatternMatchOut,
    NovelPatternMatchRequest,
    NovelPatternMatchResponse,
    ResearchDirectorResponse,
)

router = APIRouter(prefix="/research", tags=["research"])

_DAILY_INTERVALS = {"1d", "1day", "daily", "day"}
_INTRADAY_INTERVAL_SUFFIXES = ("m", "min", "mins", "minute", "minutes", "h", "hour", "hours")
_GREEN_RESEARCH_STATUSES = {
    DiscoveredPatternStatus.LAB_CANDIDATE,
    DiscoveredPatternStatus.NEEDS_CONFIRMATION,
    DiscoveredPatternStatus.CONFIRMED_CANDIDATE,
    DiscoveredPatternStatus.DIRECTOR_REVIEW,
    DiscoveredPatternStatus.PREMIUM_CANDIDATE,
    DiscoveredPatternStatus.PAPER_CANDIDATE,
    DiscoveredPatternStatus.PRODUCTION,
}


def _normalize_research_cadence(cadence: str | None) -> str | None:
    if cadence is None:
        return None
    normalized = cadence.strip().lower()
    if normalized in {"", "all"}:
        return None
    if normalized not in {"daily", "intraday"}:
        raise HTTPException(422, "cadence must be daily, intraday, or all")
    return normalized


def _research_cadence_from_interval(interval: str | None) -> str:
    value = (interval or "1d").strip().lower()
    if value in _DAILY_INTERVALS:
        return "daily"
    if value.endswith(_INTRADAY_INTERVAL_SUFFIXES):
        return "intraday"
    return "daily"


def _research_cadence_from_run(run: DiscoveryRun) -> str:
    params = run.params_json or {}
    cadence = str(params.get("cadence") or "").strip().lower()
    if cadence in {"daily", "intraday"}:
        return cadence
    return _research_cadence_from_interval(str(params.get("interval") or "1d"))


@router.post("/run-discovery", response_model=DiscoveryRunResponse)
def run_discovery(
    request: DiscoveryRunRequest,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DiscoveryRunResponse:
    return PatternDiscoveryLabAgent().run(request, db)


@router.get("/discovered-patterns", response_model=list[DiscoveredPatternOut])
def list_discovered_patterns(
    status: str | None = None,
    visibility: str | None = Query(default=None, pattern="^(green|all)$"),
    cadence: str | None = Query(default=None, pattern="^(daily|intraday|all)$"),
    limit: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[DiscoveredPattern]:
    normalized_cadence = _normalize_research_cadence(cadence)
    normalized_visibility = (visibility or "all").strip().lower()
    if normalized_cadence is None:
        if normalized_visibility == "green":
            query = db.query(DiscoveredPattern).filter(DiscoveredPattern.status.in_(_GREEN_RESEARCH_STATUSES))
            if status:
                query = query.filter(DiscoveredPattern.status == status)
            return query.order_by(DiscoveredPattern.created_at.desc()).limit(limit).all()
        return NovelPatternRegistry.list_patterns(db, limit=limit, status=status)
    query = db.query(DiscoveredPattern)
    if status:
        query = query.filter(DiscoveredPattern.status == status)
    if normalized_visibility == "green":
        query = query.filter(DiscoveredPattern.status.in_(_GREEN_RESEARCH_STATUSES))
    if normalized_cadence == "daily":
        query = query.filter(DiscoveredPattern.timeframe == "1d")
    else:
        query = query.filter(not_(DiscoveredPattern.timeframe == "1d"))
    return query.order_by(DiscoveredPattern.created_at.desc()).limit(limit).all()


@router.get("/discovered-patterns/{pattern_id}", response_model=DiscoveredPatternDetailOut)
def get_discovered_pattern(
    pattern_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> DiscoveredPattern:
    pattern = (
        db.query(DiscoveredPattern)
        .options(selectinload(DiscoveredPattern.examples), selectinload(DiscoveredPattern.metric_snapshots))
        .filter(DiscoveredPattern.id == pattern_id)
        .one_or_none()
    )
    if not pattern:
        raise HTTPException(404, "discovered pattern not found")
    return pattern


@router.get("/discovered-patterns/{pattern_id}/examples", response_model=list[DiscoveredPatternExampleOut])
def get_discovered_pattern_examples(
    pattern_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[DiscoveredPatternExample]:
    pattern = db.get(DiscoveredPattern, pattern_id)
    if not pattern:
        raise HTTPException(404, "discovered pattern not found")
    return (
        db.query(DiscoveredPatternExample)
        .filter(DiscoveredPatternExample.pattern_id == pattern_id)
        .order_by(DiscoveredPatternExample.kind.asc(), DiscoveredPatternExample.similarity.desc())
        .all()
    )


@router.get("/discovered-patterns/{pattern_id}/metrics", response_model=list[DiscoveredPatternMetricOut])
def get_discovered_pattern_metrics(
    pattern_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[DiscoveredPatternMetric]:
    pattern = db.get(DiscoveredPattern, pattern_id)
    if not pattern:
        raise HTTPException(404, "discovered pattern not found")
    return (
        db.query(DiscoveredPatternMetric)
        .filter(DiscoveredPatternMetric.pattern_id == pattern_id)
        .order_by(DiscoveredPatternMetric.as_of.desc())
        .limit(100)
        .all()
    )


@router.get("/discovered-patterns/{pattern_id}/rr-metrics")
def get_discovered_pattern_rr_metrics(
    pattern_id: int,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    pattern = db.get(DiscoveredPattern, pattern_id)
    if not pattern:
        raise HTTPException(404, "discovered pattern not found")
    return {
        "id": pattern.id,
        "name": pattern.name,
        "status": pattern.status.value if hasattr(pattern.status, "value") else str(pattern.status),
        "best_rr": pattern.best_rr,
        "best_expectancy_r": pattern.best_expectancy_r,
        "best_profit_factor": pattern.best_profit_factor,
        "best_win_rate": pattern.best_win_rate,
        "best_max_drawdown_r": pattern.best_max_drawdown_r,
        "preferred_rr_passed": pattern.preferred_rr_passed,
        "premium_rr_passed": pattern.premium_rr_passed,
        "promotion_reason": pattern.promotion_reason,
        "rejection_reasons": pattern.rejection_reasons_json,
        "rr_metrics": pattern.rr_metrics_json,
    }


@router.get("/confirmation-queue", response_model=list[DiscoveredPatternOut])
def list_confirmation_queue(
    limit: int = Query(default=50, ge=1, le=200),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[DiscoveredPattern]:
    return (
        db.query(DiscoveredPattern)
        .filter(DiscoveredPattern.confirmation_status == "needs_confirmation")
        .order_by(DiscoveredPattern.confirmation_priority_score.desc(), DiscoveredPattern.score.desc())
        .limit(limit)
        .all()
    )


@router.post("/match-current", response_model=NovelPatternMatchResponse)
def match_current_patterns(
    request: NovelPatternMatchRequest,
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> NovelPatternMatchResponse:
    result = NovelPatternMatcher().match_current(
        db=db,
        symbols=request.symbols,
        limit=request.limit,
        max_patterns=request.max_patterns,
        max_results=request.max_results,
        similarity_threshold=request.similarity_threshold,
        module=request.module,
        store=request.store,
    )
    return NovelPatternMatchResponse(**result)


@router.get("/current-matches", response_model=list[NovelPatternMatchOut])
def list_current_matches(
    limit: int = Query(default=100, ge=1, le=500),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[DiscoveredPatternMatch]:
    rows = (
        db.query(DiscoveredPatternMatch)
        .order_by(DiscoveredPatternMatch.matched_at.desc(), DiscoveredPatternMatch.score.desc())
        .limit(min(5000, limit * 10))
        .all()
    )
    deduped: dict[tuple[str, ...], DiscoveredPatternMatch] = {}
    for row in rows:
        key = NovelPatternMatcher.match_dedupe_key_from_model(row)
        if key not in deduped:
            deduped[key] = row
        if len(deduped) >= limit:
            break
    return list(deduped.values())


@router.get("/runs", response_model=list[DiscoveryRunOut])
def list_discovery_runs(
    cadence: str | None = Query(default=None, pattern="^(daily|intraday|all)$"),
    limit: int = Query(default=50, ge=1, le=200),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[DiscoveryRun]:
    normalized_cadence = _normalize_research_cadence(cadence)
    query = db.query(DiscoveryRun).order_by(DiscoveryRun.started_at.desc())
    if normalized_cadence is None:
        return query.limit(limit).all()
    candidates = query.limit(1000).all()
    return [run for run in candidates if _research_cadence_from_run(run) == normalized_cadence][:limit]


@router.post("/director/run", response_model=ResearchDirectorResponse)
def run_research_director(
    run_id: int | None = None,
    limit: int = Query(default=120, ge=1, le=500),
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ResearchDirectorResponse:
    result = ResearchDirector().run(db, run_id=run_id, limit=limit)
    return ResearchDirectorResponse(**result)


@router.get("/director/latest", response_model=ResearchDirectorResponse)
def latest_research_director(
    _: str = Depends(require_admin),
) -> ResearchDirectorResponse:
    path = get_settings().reports_path / "research" / "director" / "latest_research_director.json"
    if not path.exists():
        raise HTTPException(404, "research director has not generated a report yet")
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("summary") if isinstance(payload, dict) else None
    if not isinstance(summary, dict):
        raise HTTPException(500, "research director latest report is malformed")
    return ResearchDirectorResponse(**summary)


@router.post("/director-review/refresh")
def refresh_director_review_candidates(
    _: str = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return DirectorReviewGate().refresh(db)
