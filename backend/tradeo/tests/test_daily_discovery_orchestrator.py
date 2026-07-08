from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import perf_counter, sleep

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import DiscoveryRun
from tradeo.db.session import Base
from tradeo.services.daily_discovery_orchestrator import DailyDiscoveryOrchestrator, _lane_lock_key
from tradeo.services.discovery_params import resolve_discovery_run_params
from tradeo.schemas import (
    DailyUniverseDiscoveryRunRequest,
    DiscoveryRunRequest,
    DiscoveryRunResponse,
)


class DummySession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class SlowAgent:
    def run(self, request, db):  # noqa: ANN001, ANN201
        sleep(0.08)
        segment = request.daily_cap_segment
        run_id = {"mega": 1, "large": 2, "mid": 3}[segment]
        return DiscoveryRunResponse(
            run_id=run_id,
            status="completed",
            symbols_scanned=run_id,
            windows_sampled=run_id * 10,
            clusters_evaluated=run_id * 100,
            accepted_patterns=run_id,
            rejected_patterns=run_id + 1,
            stored_patterns=run_id + 2,
            duration_seconds=0.08,
            actual_resolved_params={"daily_cap_segment": segment},
        )


class CountingSlowAgent(SlowAgent):
    calls: Counter[str] = Counter()
    calls_lock = Lock()

    def run(self, request, db):  # noqa: ANN001, ANN201
        with self.calls_lock:
            self.calls[request.daily_cap_segment] += 1
        return super().run(request, db)


def _orchestrator() -> DailyDiscoveryOrchestrator:
    settings = Settings(daily_universe_cap_segments="mega,large,mid")
    return DailyDiscoveryOrchestrator(
        settings=settings,
        session_factory=DummySession,
        agent_factory=SlowAgent,
    )


def test_daily_discovery_orchestrator_runs_segments_in_config_order() -> None:
    result = _orchestrator().run(DailyUniverseDiscoveryRunRequest(parallel=True, skip_running=False))

    assert result.status == "completed"
    assert result.parallel is True
    assert result.daily_cap_segments == ["mega", "large", "mid"]
    assert result.run_ids == [1, 2, 3]
    assert result.symbols_scanned == 6
    assert result.windows_sampled == 60
    assert [item.daily_cap_segment for item in result.segment_results] == ["mega", "large", "mid"]


def test_daily_discovery_orchestrator_parallel_benchmark_beats_sequential() -> None:
    orchestrator = _orchestrator()

    started = perf_counter()
    sequential = orchestrator.run(DailyUniverseDiscoveryRunRequest(parallel=False, skip_running=False))
    sequential_wall = perf_counter() - started

    started = perf_counter()
    parallel = orchestrator.run(
        DailyUniverseDiscoveryRunRequest(parallel=True, max_workers=3, skip_running=False)
    )
    parallel_wall = perf_counter() - started

    assert sequential.status == "completed"
    assert parallel.status == "completed"
    assert parallel_wall < sequential_wall * 0.65


def test_daily_discovery_orchestrator_skips_duplicate_active_lane() -> None:
    orchestrator = _orchestrator()
    request = DailyUniverseDiscoveryRunRequest(
        daily_cap_segments=["mega"],
        parallel=True,
        skip_running=False,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(orchestrator.run, [request, request]))

    statuses = sorted(result.status for result in results)
    assert statuses == ["completed", "skipped"]
    skipped = next(result for result in results if result.status == "skipped")
    assert skipped.segment_results[0].daily_cap_segment == "mega"
    assert skipped.segment_results[0].error == "daily_discovery_lane_lock_busy"


def test_daily_discovery_orchestrator_skips_duplicate_full_request_lanes() -> None:
    CountingSlowAgent.calls = Counter()
    settings = Settings(daily_universe_cap_segments="mega,large,mid")
    orchestrator = DailyDiscoveryOrchestrator(
        settings=settings,
        session_factory=DummySession,
        agent_factory=CountingSlowAgent,
    )
    request = DailyUniverseDiscoveryRunRequest(
        daily_cap_segments=["mega", "large", "mid"],
        parallel=True,
        max_workers=3,
        skip_running=False,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(orchestrator.run, [request, request]))

    skipped_lanes = sum(
        1
        for result in results
        for segment in result.segment_results
        if segment.status == "skipped"
    )
    completed_lanes = sum(
        1
        for result in results
        for segment in result.segment_results
        if segment.status == "completed"
    )
    assert CountingSlowAgent.calls == {"mega": 1, "large": 1, "mid": 1}
    assert completed_lanes == 3
    assert skipped_lanes == 3
    assert {result.status for result in results} <= {"completed", "skipped", "partial_skipped"}


def test_daily_discovery_orchestrator_rejects_intraday_interval() -> None:
    try:
        DailyUniverseDiscoveryRunRequest(interval="5m")
    except ValidationError as exc:
        assert "daily universe discovery requires a daily interval" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("intraday intervals must be rejected")


def test_daily_discovery_lane_lock_key_normalizes_aliases() -> None:
    assert _lane_lock_key("Mega Cap") == _lane_lock_key("mega")
    assert len({_lane_lock_key("mega"), _lane_lock_key("large"), _lane_lock_key("mid")}) == 3


def test_daily_discovery_orchestrator_skips_recent_equivalent_run(tmp_path: Path) -> None:
    mega = tmp_path / "mega.csv"
    mega.write_text("symbol\nMEGA1\n", encoding="utf-8")
    settings = Settings(
        daily_mega_universe_file=str(mega),
        daily_universe_cap_segments="mega",
        reports_dir=str(tmp_path / "reports"),
        universe_snapshot_monthly=False,
    )
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    segment_request = DiscoveryRunRequest(
        interval="1d",
        daily_cap_segment="mega",
        limit=1,
        period=settings.discovery_period,
        max_total_windows=settings.discovery_max_total_windows,
        max_windows_per_symbol=settings.discovery_max_windows_per_symbol,
    )
    expected = resolve_discovery_run_params(settings, segment_request)
    db = Session()
    db.add(
        DiscoveryRun(
            status="completed",
            started_at=datetime.now(timezone.utc),
            params_json=expected,
        )
    )
    db.commit()
    db.close()
    CountingSlowAgent.calls = Counter()
    orchestrator = DailyDiscoveryOrchestrator(
        settings=settings,
        session_factory=Session,
        agent_factory=CountingSlowAgent,
    )

    result = orchestrator.run(
        DailyUniverseDiscoveryRunRequest(
            daily_cap_segments=["mega"],
            interval="1d",
            limit=1,
            skip_recent_seconds=60,
        )
    )

    assert result.status == "skipped"
    assert result.segment_results[0].error == "daily_discovery_recent_equivalent_run"
    assert CountingSlowAgent.calls == {}


def test_daily_discovery_orchestrator_does_not_skip_recent_by_default(tmp_path: Path) -> None:
    mega = tmp_path / "mega.csv"
    mega.write_text("symbol\nMEGA1\n", encoding="utf-8")
    settings = Settings(
        daily_mega_universe_file=str(mega),
        daily_universe_cap_segments="mega",
        reports_dir=str(tmp_path / "reports"),
        universe_snapshot_monthly=False,
    )
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    segment_request = DiscoveryRunRequest(
        interval="1d",
        daily_cap_segment="mega",
        limit=1,
        period=settings.discovery_period,
        max_total_windows=settings.discovery_max_total_windows,
        max_windows_per_symbol=settings.discovery_max_windows_per_symbol,
    )
    expected = resolve_discovery_run_params(settings, segment_request)
    db = Session()
    db.add(
        DiscoveryRun(
            status="completed",
            started_at=datetime.now(timezone.utc),
            params_json=expected,
        )
    )
    db.commit()
    db.close()
    CountingSlowAgent.calls = Counter()
    orchestrator = DailyDiscoveryOrchestrator(
        settings=settings,
        session_factory=Session,
        agent_factory=CountingSlowAgent,
    )

    result = orchestrator.run(
        DailyUniverseDiscoveryRunRequest(
            daily_cap_segments=["mega"],
            interval="1d",
            limit=1,
        )
    )

    assert result.status == "completed"
    assert CountingSlowAgent.calls == {"mega": 1}
