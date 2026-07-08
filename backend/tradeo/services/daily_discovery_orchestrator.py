from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import hashlib
from threading import Lock
from time import perf_counter
from typing import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings, get_settings
from tradeo.db.models import DiscoveryRun
from tradeo.db.session import SessionLocal
from tradeo.schemas import (
    DailyUniverseDiscoveryRunRequest,
    DailyUniverseDiscoveryRunResponse,
    DailyUniverseDiscoverySegmentResult,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
)
from tradeo.services.data_provider import DAILY_UNIVERSE_SCOPE_BY_CAP_SEGMENT, normalize_daily_cap_segment
from tradeo.services.discovery_params import resolve_discovery_run_params

SessionFactory = Callable[[], Session]
AgentFactory = Callable[[], PatternDiscoveryLabAgent]
_LANE_LOCKS_GUARD = Lock()
_LANE_LOCKS: dict[str, Lock] = {}


def _lane_lock(segment: str) -> Lock:
    key = _lane_lock_key(segment)
    with _LANE_LOCKS_GUARD:
        lock = _LANE_LOCKS.get(key)
        if lock is None:
            lock = Lock()
            _LANE_LOCKS[key] = lock
        return lock


def _lane_lock_key(segment: str) -> str:
    normalized = normalize_daily_cap_segment(segment)
    scope = DAILY_UNIVERSE_SCOPE_BY_CAP_SEGMENT[normalized]
    return f"tradeo:daily_discovery_lane:v1:scope={scope}:segment={normalized}"


def _advisory_lock_id(key: str) -> int:
    raw = hashlib.sha256(key.encode("utf-8")).digest()[:8]
    return int.from_bytes(raw, byteorder="big", signed=True)


def _is_postgres_session(db: Session) -> bool:
    bind = getattr(db, "bind", None) or getattr(db, "get_bind", lambda: None)()
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", "") in {"postgresql", "postgres"}


def _try_pg_advisory_lock(db: Session, key: str) -> int | None:
    if not _is_postgres_session(db):
        return None
    lock_id = _advisory_lock_id(key)
    acquired = db.execute(
        text("SELECT pg_try_advisory_lock(:lock_id)"),
        {"lock_id": lock_id},
    ).scalar()
    return lock_id if bool(acquired) else 0


def _release_pg_advisory_lock(db: Session, lock_id: int | None) -> None:
    if lock_id:
        db.execute(
            text("SELECT pg_advisory_unlock(:lock_id)"),
            {"lock_id": lock_id},
        ).scalar()


class DailyDiscoveryOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        session_factory: SessionFactory = SessionLocal,
        agent_factory: AgentFactory | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.session_factory = session_factory
        self.agent_factory = agent_factory or PatternDiscoveryLabAgent

    def run(self, request: DailyUniverseDiscoveryRunRequest) -> DailyUniverseDiscoveryRunResponse:
        segments = self._segments(request)
        parallel = bool(request.parallel) and len(segments) > 1
        max_workers = min(int(request.max_workers or len(segments)), len(segments))
        started = perf_counter()

        if parallel:
            results = self._run_parallel(request, segments, max_workers=max_workers)
        else:
            results = [self._run_segment(request, segment) for segment in segments]

        return self._response(
            request=request,
            segments=segments,
            results=results,
            elapsed=perf_counter() - started,
            parallel=parallel,
        )

    def _segments(self, request: DailyUniverseDiscoveryRunRequest) -> list[str]:
        if request.daily_cap_segments:
            return request.daily_cap_segments
        configured = getattr(self.settings, "daily_universe_cap_segment_list", None) or ["mid"]
        return [normalize_daily_cap_segment(segment) for segment in configured]

    def _run_parallel(
        self,
        request: DailyUniverseDiscoveryRunRequest,
        segments: list[str],
        *,
        max_workers: int,
    ) -> list[DailyUniverseDiscoverySegmentResult]:
        by_segment: dict[str, DailyUniverseDiscoverySegmentResult] = {}
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="daily-discovery") as executor:
            future_map = {
                executor.submit(self._run_segment, request, segment): segment for segment in segments
            }
            for future in as_completed(future_map):
                segment = future_map[future]
                try:
                    by_segment[segment] = future.result()
                except Exception as exc:  # noqa: BLE001
                    by_segment[segment] = DailyUniverseDiscoverySegmentResult(
                        daily_cap_segment=segment,
                        status="failed",
                        error=str(exc),
                    )
        return [by_segment[segment] for segment in segments]

    def _run_segment(
        self,
        request: DailyUniverseDiscoveryRunRequest,
        segment: str,
    ) -> DailyUniverseDiscoverySegmentResult:
        lock_key = _lane_lock_key(segment)
        lane_lock = _lane_lock(segment)
        if not lane_lock.acquire(blocking=False):
            return DailyUniverseDiscoverySegmentResult(
                daily_cap_segment=segment,
                status="skipped",
                error="daily_discovery_lane_lock_busy",
            )
        db = self.session_factory()
        advisory_lock_id: int | None = None
        try:
            advisory_lock_id = _try_pg_advisory_lock(db, lock_key)
            if advisory_lock_id == 0:
                return DailyUniverseDiscoverySegmentResult(
                    daily_cap_segment=segment,
                    status="skipped",
                    error="daily_discovery_lane_lock_busy",
                )
            segment_request = self._segment_request(request, segment)
            skip_result = self._existing_run_skip(
                db,
                segment_request,
                skip_running=request.skip_running,
                skip_recent_seconds=request.skip_recent_seconds,
            )
            if skip_result is not None:
                skip_result.daily_cap_segment = segment
                return skip_result
            response = self.agent_factory().run(segment_request, db)
            return self._segment_result(segment, response)
        except Exception as exc:  # noqa: BLE001
            return DailyUniverseDiscoverySegmentResult(
                daily_cap_segment=segment,
                status="failed",
                error=str(exc),
            )
        finally:
            try:
                try:
                    _release_pg_advisory_lock(db, advisory_lock_id)
                finally:
                    db.close()
            finally:
                lane_lock.release()

    @staticmethod
    def _segment_request(
        request: DailyUniverseDiscoveryRunRequest,
        segment: str,
    ) -> DiscoveryRunRequest:
        payload = request.model_dump(
            exclude={"daily_cap_segments", "parallel", "max_workers"},
            exclude_none=True,
        )
        payload["daily_cap_segment"] = segment
        return DiscoveryRunRequest(**payload)

    def _existing_run_skip(
        self,
        db: Session,
        segment_request: DiscoveryRunRequest,
        *,
        skip_running: bool,
        skip_recent_seconds: int | None,
    ) -> DailyUniverseDiscoverySegmentResult | None:
        if not skip_running and skip_recent_seconds is None:
            return None
        expected = resolve_discovery_run_params(self.settings, segment_request)
        if skip_running:
            running = db.query(DiscoveryRun).filter(DiscoveryRun.status == "running").all()
            matching_running = next(
                (run for run in running if self._params_match(run.params_json or {}, expected)),
                None,
            )
            if matching_running is not None:
                return DailyUniverseDiscoverySegmentResult(
                    daily_cap_segment=segment_request.daily_cap_segment or "",
                    status="skipped",
                    run_id=matching_running.id,
                    error="daily_discovery_run_already_running",
                )
        if skip_recent_seconds is None:
            return None
        recent_cutoff = datetime.now(timezone.utc) - timedelta(seconds=skip_recent_seconds)
        recent_completed = (
            db.query(DiscoveryRun)
            .filter(DiscoveryRun.status == "completed", DiscoveryRun.started_at >= recent_cutoff)
            .order_by(DiscoveryRun.started_at.desc())
            .all()
        )
        recent = next(
            (run for run in recent_completed if self._params_match(run.params_json or {}, expected)),
            None,
        )
        if recent is not None:
            return DailyUniverseDiscoverySegmentResult(
                daily_cap_segment=segment_request.daily_cap_segment or "",
                status="skipped",
                run_id=recent.id,
                error="daily_discovery_recent_equivalent_run",
            )
        return None

    @staticmethod
    def _params_match(stored: dict[str, object], expected: dict[str, object]) -> bool:
        return all(stored.get(key) == value for key, value in expected.items())

    @staticmethod
    def _segment_result(
        segment: str,
        response: DiscoveryRunResponse,
    ) -> DailyUniverseDiscoverySegmentResult:
        return DailyUniverseDiscoverySegmentResult(
            daily_cap_segment=segment,
            status=response.status,
            run_id=response.run_id,
            duration_seconds=response.duration_seconds,
            symbols_scanned=response.symbols_scanned,
            windows_sampled=response.windows_sampled,
            clusters_evaluated=response.clusters_evaluated,
            accepted_patterns=response.accepted_patterns,
            rejected_patterns=response.rejected_patterns,
            stored_patterns=response.stored_patterns,
            report_path=response.report_path,
        )

    @staticmethod
    def _response(
        *,
        request: DailyUniverseDiscoveryRunRequest,
        segments: list[str],
        results: list[DailyUniverseDiscoverySegmentResult],
        elapsed: float,
        parallel: bool,
    ) -> DailyUniverseDiscoveryRunResponse:
        failed = [result for result in results if result.status == "failed"]
        skipped = [result for result in results if result.status == "skipped"]
        completed = [result for result in results if result.status == "completed"]
        status = "completed" if len(completed) == len(results) else "partial_failed"
        if len(failed) == len(results):
            status = "failed"
        elif skipped and not failed:
            status = "skipped" if len(skipped) == len(results) else "partial_skipped"
        return DailyUniverseDiscoveryRunResponse(
            status=status,
            parallel=parallel,
            daily_cap_segments=segments,
            duration_seconds=elapsed,
            run_ids=[result.run_id for result in results if result.run_id is not None],
            symbols_scanned=sum(result.symbols_scanned for result in results),
            windows_sampled=sum(result.windows_sampled for result in results),
            clusters_evaluated=sum(result.clusters_evaluated for result in results),
            accepted_patterns=sum(result.accepted_patterns for result in results),
            rejected_patterns=sum(result.rejected_patterns for result in results),
            stored_patterns=sum(result.stored_patterns for result in results),
            segment_results=results,
        )
