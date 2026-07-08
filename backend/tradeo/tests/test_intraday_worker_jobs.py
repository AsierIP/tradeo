from __future__ import annotations

from concurrent.futures import Future
import json
from types import SimpleNamespace

from tradeo.core.config import Settings
from tradeo.modules.resource_policy.market_session_resource_policy import SessionState
from tradeo.tasks import worker


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict[str, object]] = []

    def add_job(self, func, trigger, *args, **kwargs) -> None:  # noqa: ANN001
        self.jobs.append(
            {
                "func": func,
                "trigger": trigger,
                "args": args,
                "kwargs": kwargs,
            }
        )


def _job_ids(scheduler: FakeScheduler) -> list[str]:
    return [str(job["kwargs"]["id"]) for job in scheduler.jobs]


def _policy_decision(
    *,
    allowed: bool,
    reason: str = "resource_policy_denied:research_heavy:regular_market",
):
    return SimpleNamespace(
        allowed=allowed,
        deny_reason=None if allowed else reason,
        to_dict=lambda: {
            "allowed": allowed,
            "deny_reason": None if allowed else reason,
            "job_type": "research_heavy",
            "owner": "research",
            "session_state": SessionState.REGULAR_MARKET if not allowed else SessionState.MARKET_CLOSED,
            "can_submit_orders": False,
        },
    )


def test_register_intraday_jobs_is_noop_when_global_flag_disabled() -> None:
    scheduler = FakeScheduler()
    settings = Settings(
        intraday_enabled=False,
        intraday_universe_enabled=True,
        intraday_data_sync_enabled=True,
        intraday_candidate_scan_enabled=True,
        intraday_eod_flat_enabled=True,
    )

    registered = worker.register_intraday_jobs(scheduler, settings)

    assert registered == []
    assert scheduler.jobs == []


def test_register_daily_paper_jobs_is_noop_by_default() -> None:
    scheduler = FakeScheduler()

    registered = worker.register_daily_paper_jobs(
        scheduler,
        Settings(daily_paper_execution_enabled=False),
    )

    assert registered == []
    assert scheduler.jobs == []


def test_register_daily_paper_jobs_uses_post_close_or_interval_schedule() -> None:
    post_close_scheduler = FakeScheduler()
    post_close_settings = Settings(
        daily_paper_execution_enabled=True,
        daily_paper_scan_minutes=1440,
        daily_paper_post_close_hour_utc=22,
        daily_paper_post_close_minute_utc=30,
    )

    registered = worker.register_daily_paper_jobs(post_close_scheduler, post_close_settings)

    assert registered == ["daily_paper_entry_scanner"]
    assert _job_ids(post_close_scheduler) == registered
    assert post_close_scheduler.jobs[0]["func"] is worker.daily_paper_entry_job
    assert post_close_scheduler.jobs[0]["trigger"].__class__.__name__ == "CronTrigger"
    assert post_close_scheduler.jobs[0]["kwargs"]["max_instances"] == 1
    assert post_close_scheduler.jobs[0]["kwargs"]["coalesce"] is True

    interval_scheduler = FakeScheduler()
    interval_settings = Settings(
        daily_paper_execution_enabled=True,
        daily_paper_scan_minutes=60,
    )

    registered = worker.register_daily_paper_jobs(interval_scheduler, interval_settings)

    assert registered == ["daily_paper_entry_scanner"]
    assert interval_scheduler.jobs[0]["trigger"] == "interval"
    assert interval_scheduler.jobs[0]["kwargs"]["minutes"] == 60


def test_register_intraday_jobs_only_adds_enabled_intraday_specs() -> None:
    scheduler = FakeScheduler()
    settings = Settings(
        intraday_enabled=True,
        intraday_universe_enabled=True,
        intraday_data_sync_enabled=True,
        intraday_research_enabled=True,
        intraday_research_parallel_timeframes_enabled=False,
        intraday_research_interval_seconds=123,
        intraday_candidate_scan_enabled=True,
        intraday_observation_closer_enabled=True,
        intraday_risk_heartbeat_enabled=True,
        intraday_reconciliation_enabled=True,
        intraday_eod_flat_enabled=True,
        intraday_job_jitter_seconds=7,
    )

    registered = worker.register_intraday_jobs(scheduler, settings)

    assert registered == [
        "intraday_universe_premarket",
        "intraday_universe_early",
        "intraday_data_sync",
        "intraday_research",
        "intraday_candidate_scan",
        "intraday_observation_closer",
        "intraday_risk_heartbeat",
        "intraday_reconciliation",
        "intraday_eod_flat",
    ]
    assert _job_ids(scheduler) == registered
    assert all(job["kwargs"]["max_instances"] == 1 for job in scheduler.jobs)
    assert all(job["kwargs"]["coalesce"] is True for job in scheduler.jobs)
    interval_jobs = [job for job in scheduler.jobs if job["trigger"] == "interval"]
    assert interval_jobs
    assert all(job["kwargs"]["jitter"] == 7 for job in interval_jobs)
    research_job = next(job for job in scheduler.jobs if job["kwargs"]["id"] == "intraday_research")
    assert research_job["kwargs"]["seconds"] == 123


def test_register_intraday_jobs_can_split_research_by_timeframe() -> None:
    scheduler = FakeScheduler()
    settings = Settings(
        intraday_enabled=True,
        intraday_research_enabled=True,
        intraday_research_parallel_timeframes_enabled=True,
        intraday_research_parallel_symbol_chunks=1,
        intraday_research_process_pool_enabled=False,
        intraday_timeframes="15m,5m",
        intraday_research_interval_seconds=123,
        intraday_risk_heartbeat_enabled=False,
        intraday_reconciliation_enabled=False,
        intraday_eod_flat_enabled=False,
    )

    registered = worker.register_intraday_jobs(scheduler, settings)

    assert registered == ["intraday_research_15m", "intraday_research_5m"]
    assert _job_ids(scheduler) == registered
    assert all(job["trigger"] == "interval" for job in scheduler.jobs)
    assert all(job["kwargs"]["seconds"] == 123 for job in scheduler.jobs)


def test_register_intraday_jobs_can_split_research_by_timeframe_and_symbol_chunks() -> None:
    scheduler = FakeScheduler()
    settings = Settings(
        intraday_enabled=True,
        intraday_research_enabled=True,
        intraday_research_parallel_timeframes_enabled=True,
        intraday_research_parallel_symbol_chunks=2,
        intraday_research_process_pool_enabled=False,
        intraday_timeframes="15m,5m",
        intraday_research_interval_seconds=123,
        intraday_risk_heartbeat_enabled=False,
        intraday_reconciliation_enabled=False,
        intraday_eod_flat_enabled=False,
    )

    registered = worker.register_intraday_jobs(scheduler, settings)

    assert registered == [
        "intraday_research_15m_chunk_1_of_2",
        "intraday_research_15m_chunk_2_of_2",
        "intraday_research_5m_chunk_1_of_2",
        "intraday_research_5m_chunk_2_of_2",
    ]
    assert _job_ids(scheduler) == registered
    assert all(job["trigger"] == "interval" for job in scheduler.jobs)
    assert all(job["kwargs"]["seconds"] == 123 for job in scheduler.jobs)


def test_register_intraday_jobs_can_use_research_process_pool() -> None:
    scheduler = FakeScheduler()
    settings = Settings(
        intraday_enabled=True,
        intraday_research_enabled=True,
        intraday_research_parallel_timeframes_enabled=True,
        intraday_research_parallel_symbol_chunks=5,
        intraday_research_process_pool_enabled=True,
        intraday_research_process_workers=3,
        intraday_timeframes="15m,5m",
        intraday_research_interval_seconds=123,
        intraday_risk_heartbeat_enabled=False,
        intraday_reconciliation_enabled=False,
        intraday_eod_flat_enabled=False,
    )

    registered = worker.register_intraday_jobs(scheduler, settings)

    assert registered == ["intraday_research_process_pool"]
    assert _job_ids(scheduler) == registered
    assert scheduler.jobs[0]["trigger"] == "interval"
    assert scheduler.jobs[0]["kwargs"]["seconds"] == 123


def test_intraday_research_process_pool_job_uses_runner(monkeypatch) -> None:
    calls: list[tuple[str, str, object]] = []

    def fake_run(job_id: str, enabled_attr: str, action) -> None:  # noqa: ANN001
        calls.append((job_id, enabled_attr, action))

    monkeypatch.setattr(worker, "_run_intraday_job", fake_run)

    worker.intraday_research_process_pool_job()

    assert calls == [
        (
            "intraday_research_process_pool",
            "intraday_research_enabled",
            worker._run_intraday_research_process_pool,
        )
    ]


def test_intraday_worker_blocks_heavy_research_when_resource_policy_denies(monkeypatch) -> None:
    statuses: list[dict[str, object]] = []
    settings = Settings(intraday_enabled=True, intraday_research_enabled=True)
    action_called = False

    def action(_settings: Settings) -> dict[str, object]:
        nonlocal action_called
        action_called = True
        return {"status": "ok", "reason": "should_not_run", "details": {}}

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "decide_with_market_session_policy", lambda *args, **kwargs: _policy_decision(allowed=False))
    monkeypatch.setattr(
        worker,
        "write_intraday_session_status",
        lambda job_id, payload, _settings: statuses.append({"job_id": job_id, **payload}),
    )

    payload = worker._run_intraday_job("intraday_research", "intraday_research_enabled", action)

    assert action_called is False
    assert payload["status"] == "skipped"
    assert payload["reason"] == "resource_policy_denied"
    assert payload["details"]["resource_policy"]["deny_reason"] == "resource_policy_denied:research_heavy:regular_market"
    assert payload["details"]["resource_policy"]["allowed"] is False
    assert statuses[-1]["job_id"] == "intraday_research"


def test_intraday_research_skips_completed_equivalent_runs_when_configured(monkeypatch) -> None:
    settings = Settings(
        intraday_timeframes="15m",
        intraday_research_skip_completed_equivalent_runs=True,
        intraday_universe_file="/tmp/small.csv",
    )
    request = worker._intraday_research_request(settings, "15m", store_rejected=False)
    expected = worker._intraday_research_expected_params(settings, request)
    completed_run = SimpleNamespace(id=42, params_json=expected)

    class FakeQuery:
        def __init__(self, rows: list[object]) -> None:
            self.rows = rows

        def filter(self, *args, **kwargs):  # noqa: ANN001
            return self

        def order_by(self, *args, **kwargs):  # noqa: ANN001
            return self

        def all(self) -> list[object]:
            return self.rows

        def first(self) -> object | None:
            return self.rows[0] if self.rows else None

    class FakeDb:
        def __init__(self) -> None:
            self.calls = 0
            self.rows_by_call = [
                [],
                [],
                [completed_run],
            ]

        def query(self, _model):  # noqa: ANN001
            rows = self.rows_by_call[self.calls]
            self.calls += 1
            return FakeQuery(rows)

        def close(self) -> None:
            pass

    monkeypatch.setattr(worker, "SessionLocal", FakeDb)
    monkeypatch.setattr(
        worker,
        "get_market_data_provider",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("provider should not be called")),
    )

    result = worker._run_intraday_research(settings, timeframes=["15m"], store_rejected=False)

    assert result["reason"] == "intraday_research_waiting"
    assert result["details"]["runs"] == []
    assert result["details"]["skipped"] == [
        {
            "timeframe": "15m",
            "reason": "completed_equivalent_run",
            "run_id": 42,
            "chunk": None,
        }
    ]


def test_intraday_research_process_jobs_precompute_symbols_in_chunk_major_order(monkeypatch) -> None:
    settings = Settings(
        intraday_timeframes="15m,5m",
        intraday_research_parallel_symbol_chunks=2,
        intraday_research_limit_default=4,
        intraday_universe_file="/tmp/small.csv",
    )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: [f"{interval}-{idx}" for idx in range(limit)],
    )

    jobs = worker._intraday_research_process_jobs(settings)

    assert [(job.timeframe, job.chunk_index) for job in jobs] == [
        ("15m", 0),
        ("5m", 0),
        ("15m", 1),
        ("5m", 1),
    ]
    assert [job.symbols for job in jobs] == [
        ("15m-0", "15m-2"),
        ("5m-0", "5m-2"),
        ("15m-1", "15m-3"),
        ("5m-1", "5m-3"),
    ]
    assert [job.estimated_cost for job in jobs] == [2, 2, 2, 2]
    assert len({job.pool_run_id for job in jobs}) == 1


def test_intraday_research_process_jobs_use_deterministic_symbol_chunks(monkeypatch) -> None:
    settings = Settings(
        intraday_timeframes="15m",
        intraday_research_parallel_symbol_chunks=3,
        intraday_research_limit_default=6,
        intraday_universe_file="/tmp/small.csv",
    )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: [f"S{idx}" for idx in range(limit)],
    )

    jobs = worker._intraday_research_process_jobs(settings)

    assert [job.symbols for job in jobs] == [
        ("S0", "S3"),
        ("S1", "S4"),
        ("S2", "S5"),
    ]
    assert [job.estimated_cost for job in jobs] == [2, 2, 2]
    assert sorted(symbol for job in jobs for symbol in (job.symbols or ())) == [
        "S0",
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
    ]


def test_intraday_research_process_jobs_keep_remainder_chunks_stable(monkeypatch) -> None:
    settings = Settings(
        intraday_timeframes="15m,5m",
        intraday_research_parallel_symbol_chunks=3,
        intraday_research_limit_default=4,
        intraday_universe_file="/tmp/small.csv",
    )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: [f"{interval}-{idx}" for idx in range(limit)],
    )

    jobs = worker._intraday_research_process_jobs(settings)
    symbols_by_key = {(job.timeframe, job.chunk_index): job.symbols for job in jobs}

    assert symbols_by_key[("15m", 0)] == ("15m-0", "15m-3")
    assert symbols_by_key[("5m", 0)] == ("5m-0", "5m-3")
    assert symbols_by_key[("15m", 1)] == ("15m-1",)
    assert symbols_by_key[("5m", 1)] == ("5m-1",)
    assert symbols_by_key[("15m", 2)] == ("15m-2",)
    assert symbols_by_key[("5m", 2)] == ("5m-2",)


def test_intraday_research_process_jobs_keep_configured_chunk_count_by_default(monkeypatch) -> None:
    monkeypatch.delenv(worker._INTRADAY_RESEARCH_ADAPTIVE_CHUNKS_ENV, raising=False)
    settings = Settings(
        intraday_timeframes="15m,5m",
        intraday_research_parallel_symbol_chunks=5,
        intraday_research_process_pool_enabled=True,
        intraday_research_process_workers=3,
        intraday_research_limit_default=20,
        intraday_universe_file="/tmp/small.csv",
    )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: [f"{interval}-{idx}" for idx in range(limit)],
    )

    jobs = worker._intraday_research_process_jobs(settings)

    assert len(jobs) == 10
    assert {job.chunk_count for job in jobs} == {5}
    assert [job.estimated_cost for job in jobs] == [4] * 10
    for timeframe in ("15m", "5m"):
        assert {
            symbol
            for job in jobs
            if job.timeframe == timeframe
            for symbol in (job.symbols or ())
        } == {f"{timeframe}-{idx}" for idx in range(20)}


def test_intraday_research_process_jobs_can_adapt_chunk_count_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv(worker._INTRADAY_RESEARCH_ADAPTIVE_CHUNKS_ENV, "true")
    settings = Settings(
        intraday_timeframes="15m,5m",
        intraday_research_parallel_symbol_chunks=5,
        intraday_research_process_pool_enabled=True,
        intraday_research_process_workers=3,
        intraday_research_limit_default=20,
        intraday_universe_file="/tmp/small.csv",
    )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: [f"{interval}-{idx}" for idx in range(limit)],
    )

    jobs = worker._intraday_research_process_jobs(settings)

    assert len(jobs) == 12
    assert {job.chunk_count for job in jobs} == {6}
    assert [job.estimated_cost for job in jobs] == [4, 4, 4, 4, 3, 3, 3, 3, 3, 3, 3, 3]
    for timeframe in ("15m", "5m"):
        assert {
            symbol
            for job in jobs
            if job.timeframe == timeframe
            for symbol in (job.symbols or ())
        } == {f"{timeframe}-{idx}" for idx in range(20)}


def test_intraday_research_process_jobs_can_adapt_exactly_full_pool(monkeypatch) -> None:
    monkeypatch.setenv(worker._INTRADAY_RESEARCH_ADAPTIVE_CHUNKS_ENV, "true")
    settings = Settings(
        intraday_timeframes="15m,5m",
        intraday_research_parallel_symbol_chunks=5,
        intraday_research_process_pool_enabled=True,
        intraday_research_process_workers=10,
        intraday_research_limit_default=20,
        intraday_universe_file="/tmp/small.csv",
    )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: [f"{interval}-{idx}" for idx in range(limit)],
    )

    jobs = worker._intraday_research_process_jobs(settings)

    assert len(jobs) == 12
    assert {job.chunk_count for job in jobs} == {6}
    for timeframe in ("15m", "5m"):
        assert {
            symbol
            for job in jobs
            if job.timeframe == timeframe
            for symbol in (job.symbols or ())
        } == {f"{timeframe}-{idx}" for idx in range(20)}


def test_intraday_research_process_jobs_balance_cached_window_estimates(
    monkeypatch,
    tmp_path,
) -> None:
    symbols = ["A", "B", "C", "D", "E", "F"]
    rows_by_symbol = {
        "A": 240,
        "B": 220,
        "C": 80,
        "D": 70,
        "E": 60,
        "F": 50,
    }
    settings = Settings(
        intraday_timeframes="5m",
        intraday_research_parallel_symbol_chunks=3,
        intraday_research_limit_default=len(symbols),
        intraday_research_period="30d",
        intraday_research_window_sizes="20",
        intraday_research_forward_bars="3",
        intraday_research_max_windows_per_symbol=1000,
        intraday_universe_file="/tmp/small.csv",
        market_data_cache_dir=str(tmp_path),
    )
    for symbol, rows in rows_by_symbol.items():
        metadata_path = tmp_path / (
            "_".join(
                worker._intraday_market_data_cache_safe_part(part)
                for part in (symbol, "5m", "30d")
            )
            + ".metadata.json"
        )
        metadata_path.write_text(
            json.dumps(
                {
                    "symbol": symbol,
                    "period": "30d",
                    "interval": "5m",
                    "rows": rows,
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: symbols[:limit],
    )

    jobs = worker._intraday_research_process_jobs(settings)

    assert [job.symbols for job in jobs] == [
        ("A",),
        ("B",),
        ("C", "D", "E", "F"),
    ]
    assert [job.estimated_cost for job in jobs] == [217, 197, 168]
    assert sorted(symbol for job in jobs for symbol in (job.symbols or ())) == symbols


def test_intraday_research_process_worker_uses_precomputed_symbols(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    settings = Settings(intraday_research_native_threads_per_process=1)
    job = worker.IntradayResearchProcessJob(
        timeframe="5m",
        chunk_index=1,
        chunk_count=3,
        symbols=("BBB", "DDD"),
        pool_run_id="test-run",
    )

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "_reset_intraday_research_process_worker_state", lambda _run_id: None)

    def fake_run(  # noqa: ANN001
        _settings,
        *,
        timeframes=None,
        symbol_chunk=None,
        chunk_symbols=None,
        store_rejected=None,
        allow_recent_duplicates=None,
    ):
        calls.append(
            {
                "timeframes": timeframes,
                "symbol_chunk": symbol_chunk,
                "chunk_symbols": chunk_symbols,
                "store_rejected": store_rejected,
                "allow_recent_duplicates": allow_recent_duplicates,
            }
        )
        return {
            "status": "ok",
            "reason": "done",
            "details": {"runs": [], "skipped": []},
        }

    monkeypatch.setattr(worker, "_run_intraday_research", fake_run)

    result = worker._run_intraday_research_process_worker(job)

    assert calls == [
        {
            "timeframes": ["5m"],
            "symbol_chunk": (1, 3),
            "chunk_symbols": ("BBB", "DDD"),
            "store_rejected": False,
            "allow_recent_duplicates": False,
        }
    ]
    assert result["details"]["process_job"]["timeframe"] == "5m"
    assert result["details"]["process_job"]["symbols"] == 2
    assert result["details"]["process_job"]["elapsed_seconds"] >= 0


def test_intraday_research_process_worker_state_preserves_benchmark_caches(monkeypatch) -> None:
    from tradeo.agents import pattern_discovery_lab_agent as lab_module

    resets: list[bool] = []
    lab_module._BENCHMARK_FRAMES_CACHE[("30d", "5m")] = {"SPY": object()}
    lab_module._BENCHMARK_REGIME_CACHE["30d"] = object()
    monkeypatch.setattr(worker, "_INTRADAY_RESEARCH_PROCESS_WORKER_RUN_ID", None)
    monkeypatch.setattr(worker, "_reset_intraday_research_process_db_state", lambda: resets.append(True))

    worker._reset_intraday_research_process_worker_state("pool-run-1")

    assert resets == [True]
    assert ("30d", "5m") in lab_module._BENCHMARK_FRAMES_CACHE
    assert "30d" in lab_module._BENCHMARK_REGIME_CACHE

    lab_module._BENCHMARK_FRAMES_CACHE.pop(("30d", "5m"), None)
    lab_module._BENCHMARK_REGIME_CACHE.pop("30d", None)


def test_intraday_research_process_jobs_can_mark_benchmark_duplicate_bypass(monkeypatch) -> None:
    settings = Settings(
        intraday_timeframes="15m",
        intraday_research_parallel_symbol_chunks=2,
        intraday_research_limit_default=2,
        intraday_universe_file="/tmp/small.csv",
    )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: [f"S{idx}" for idx in range(limit)],
    )

    jobs = worker._intraday_research_process_jobs(settings, allow_recent_duplicates=True)

    assert jobs
    assert all(job.allow_recent_duplicates is True for job in jobs)


def test_intraday_research_process_jobs_can_mark_rejected_storage(monkeypatch) -> None:
    settings = Settings(
        intraday_timeframes="15m",
        intraday_research_parallel_symbol_chunks=2,
        intraday_research_limit_default=2,
        intraday_universe_file="/tmp/small.csv",
    )

    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: [f"S{idx}" for idx in range(limit)],
    )

    jobs = worker._intraday_research_process_jobs(settings, store_rejected=True)

    assert jobs
    assert all(job.store_rejected is True for job in jobs)


def test_intraday_research_process_worker_forwards_benchmark_duplicate_bypass(monkeypatch) -> None:
    calls: list[bool | None] = []
    settings = Settings(intraday_research_native_threads_per_process=1)
    job = worker.IntradayResearchProcessJob(
        timeframe="5m",
        chunk_index=0,
        chunk_count=1,
        symbols=("AAA",),
        pool_run_id="test-run",
        allow_recent_duplicates=True,
    )

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "_reset_intraday_research_process_worker_state", lambda _run_id: None)

    def fake_run(_settings, **kwargs):  # noqa: ANN001
        calls.append(kwargs.get("allow_recent_duplicates"))
        return {"status": "ok", "reason": "done", "details": {"runs": [], "skipped": []}}

    monkeypatch.setattr(worker, "_run_intraday_research", fake_run)

    worker._run_intraday_research_process_worker(job)

    assert calls == [True]


def test_intraday_research_process_worker_forwards_rejected_storage(monkeypatch) -> None:
    calls: list[bool | None] = []
    settings = Settings(intraday_research_native_threads_per_process=1)
    job = worker.IntradayResearchProcessJob(
        timeframe="5m",
        chunk_index=0,
        chunk_count=1,
        symbols=("AAA",),
        pool_run_id="test-run",
        store_rejected=True,
    )

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "_reset_intraday_research_process_worker_state", lambda _run_id: None)

    def fake_run(_settings, **kwargs):  # noqa: ANN001
        calls.append(kwargs.get("store_rejected"))
        return {"status": "ok", "reason": "done", "details": {"runs": [], "skipped": []}}

    monkeypatch.setattr(worker, "_run_intraday_research", fake_run)

    worker._run_intraday_research_process_worker(job)

    assert calls == [True]


def test_intraday_research_process_start_method_prefers_fork_on_linux(monkeypatch) -> None:
    monkeypatch.delenv(worker._INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV, raising=False)
    monkeypatch.setattr(worker.sys, "platform", "linux")
    monkeypatch.setattr(
        worker.multiprocessing,
        "get_all_start_methods",
        lambda: ["forkserver", "fork", "spawn"],
    )

    assert worker._intraday_research_process_start_method() == "fork"


def test_intraday_research_process_start_method_allows_default_override(monkeypatch) -> None:
    monkeypatch.setenv(worker._INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV, "default")
    monkeypatch.setattr(worker.sys, "platform", "linux")
    monkeypatch.setattr(
        worker.multiprocessing,
        "get_all_start_methods",
        lambda: ["forkserver", "fork", "spawn"],
    )

    assert worker._intraday_research_process_start_method() is None


def test_intraday_research_process_executor_passes_selected_context(monkeypatch) -> None:
    created: list[object] = []

    class FakeContext:
        def __init__(self, method: str) -> None:
            self.method = method

    class FakeProcessExecutor:
        def __init__(self, **kwargs):  # noqa: ANN001
            self.kwargs = kwargs
            created.append(self)

        def shutdown(self, wait=True, cancel_futures=False) -> None:  # noqa: ANN001, FBT002
            return None

    monkeypatch.delenv(worker._INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV, raising=False)
    monkeypatch.setattr(worker.sys, "platform", "linux")
    monkeypatch.setattr(
        worker.multiprocessing,
        "get_all_start_methods",
        lambda: ["forkserver", "fork", "spawn"],
    )
    monkeypatch.setattr(
        worker.multiprocessing,
        "get_context",
        lambda method: FakeContext(method),
    )
    monkeypatch.setattr(worker, "ProcessPoolExecutor", FakeProcessExecutor)
    worker._shutdown_intraday_research_process_pool()

    try:
        worker._intraday_research_process_executor(max_workers=2, native_threads=1)
    finally:
        worker._shutdown_intraday_research_process_pool()

    assert len(created) == 1
    assert created[0].kwargs["mp_context"].method == "fork"


def test_intraday_research_process_pool_reuses_executor_and_records_workers(monkeypatch) -> None:
    created: list[FakeProcessExecutor] = []
    monkeypatch.delenv(worker._INTRADAY_RESEARCH_PROCESS_START_METHOD_ENV, raising=False)

    class FakeProcessExecutor:
        def __init__(self, max_workers, initializer=None, initargs=(), **_kwargs):  # noqa: ANN001
            self.max_workers = max_workers
            self.submitted: list[worker.IntradayResearchProcessJob] = []
            self.shutdown_calls = 0
            created.append(self)
            if initializer is not None:
                initializer(*initargs)

        def submit(self, fn, job):  # noqa: ANN001
            self.submitted.append(job)
            future: Future = Future()
            future.set_result(
                {
                    "status": "ok",
                    "details": {
                        "runs": [
                            {
                                "timeframe": job.timeframe,
                                "chunk": {
                                    "index": job.chunk_index,
                                    "number": job.chunk_index + 1,
                                    "count": job.chunk_count,
                                    "symbols": len(job.symbols),
                                },
                            }
                        ],
                        "skipped": [],
                        "process_job": {
                            "timeframe": job.timeframe,
                            "chunk_index": job.chunk_index,
                            "symbols": len(job.symbols),
                            "elapsed_seconds": 0.01,
                        },
                    },
                }
            )
            return future

        def shutdown(self, wait=True, cancel_futures=False) -> None:  # noqa: ANN001, FBT002
            self.shutdown_calls += 1

    settings = Settings(
        intraday_timeframes="15m,5m",
        intraday_research_parallel_symbol_chunks=2,
        intraday_research_process_workers=2,
        intraday_research_native_threads_per_process=1,
    )

    monkeypatch.setattr(worker, "ProcessPoolExecutor", FakeProcessExecutor)
    monkeypatch.setattr(worker, "decide_with_market_session_policy", lambda *args, **kwargs: _policy_decision(allowed=True))
    monkeypatch.setattr(
        worker,
        "_intraday_research_process_symbol_chunks",
        lambda _settings, timeframe, chunk_count: [
            (chunk_index, (f"{timeframe}-{chunk_index}",), 1)
            for chunk_index in range(chunk_count)
        ],
    )
    worker._shutdown_intraday_research_process_pool()

    try:
        first = worker._run_intraday_research_process_pool(settings)
        second = worker._run_intraday_research_process_pool(settings)
    finally:
        worker._shutdown_intraday_research_process_pool()

    assert len(created) == 1
    assert [(job.timeframe, job.chunk_index) for job in created[0].submitted[:4]] == [
        ("15m", 0),
        ("5m", 0),
        ("15m", 1),
        ("5m", 1),
    ]
    assert created[0].shutdown_calls == 1
    assert first["status"] == "ok"
    assert second["details"]["process_workers"] == 2
    assert second["details"]["process_start_method"] in {"fork", "default"}
    assert second["details"]["jobs"] == 4
    assert len(second["details"]["worker_results"]) == 4
    assert {item["submitted_order"] for item in second["details"]["worker_results"]} == {0, 1, 2, 3}
    assert {item["completed_order"] for item in second["details"]["worker_results"]} == {0, 1, 2, 3}


def test_intraday_job_runner_uses_lock_and_redacts_sensitive_details(monkeypatch) -> None:
    statuses: list[dict[str, object]] = []
    settings = Settings(intraday_enabled=True, intraday_risk_heartbeat_enabled=True)

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(
        worker,
        "write_intraday_session_status",
        lambda job_id, payload, _settings: statuses.append({"job_id": job_id, **payload}),
    )

    def action(_settings: Settings) -> dict[str, object]:
        return {
            "status": "ok",
            "reason": "tested",
            "details": {"api_key": "do-not-print", "component": "risk"},
        }

    payload = worker._run_intraday_job("intraday_risk_heartbeat", "intraday_risk_heartbeat_enabled", action)

    assert payload["status"] == "ok"
    assert statuses[-1]["job_id"] == "intraday_risk_heartbeat"
    assert statuses[-1]["details"] == {"api_key": "<redacted>", "component": "risk"}


def test_intraday_research_job_wires_real_runner(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(job_id, enabled_attr, action):  # noqa: ANN001
        captured["job_id"] = job_id
        captured["enabled_attr"] = enabled_attr
        captured["result"] = action(Settings())

    monkeypatch.setattr(worker, "_run_intraday_job", fake_run)
    monkeypatch.setattr(
        worker,
        "_run_intraday_research",
        lambda _settings: {"status": "ok", "reason": "wired", "details": {}},
    )

    worker.intraday_research_job()

    assert captured == {
        "job_id": "intraday_research",
        "enabled_attr": "intraday_research_enabled",
        "result": {"status": "ok", "reason": "wired", "details": {}},
    }


def test_intraday_data_sync_fetches_intraday_research_universe(monkeypatch) -> None:
    calls: list[tuple[str, str, str]] = []

    class Provider:
        def fetch_ohlcv(self, symbol: str, period: str, interval: str):  # noqa: ANN001
            calls.append((symbol, period, interval))

    settings = Settings(
        intraday_timeframes="15m,5m",
        intraday_research_period="30d",
        intraday_research_limit_default=2,
        intraday_universe_file="/tmp/small.csv",
    )
    monkeypatch.setattr(worker, "get_market_data_provider", lambda *, cache_refresh_enabled: Provider())
    monkeypatch.setattr(worker, "pick_symbols", lambda **_: ["AAA", "BBB"])

    result = worker._run_intraday_data_sync(settings)

    assert result["status"] == "ok"
    assert result["details"]["fetched"] == 4
    assert calls == [
        ("AAA", "30d", "15m"),
        ("BBB", "30d", "15m"),
        ("AAA", "30d", "5m"),
        ("BBB", "30d", "5m"),
    ]


def test_intraday_research_timeframe_job_wires_single_timeframe_runner(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(job_id, enabled_attr, action):  # noqa: ANN001
        captured["job_id"] = job_id
        captured["enabled_attr"] = enabled_attr
        captured["result"] = action(Settings())

    monkeypatch.setattr(worker, "_run_intraday_job", fake_run)
    monkeypatch.setattr(
        worker,
        "_run_intraday_research",
        lambda _settings, *, timeframes=None: {
            "status": "ok",
            "reason": "wired",
            "details": {"timeframes": timeframes},
        },
    )

    worker.intraday_research_timeframe_job("15m")

    assert captured == {
        "job_id": "intraday_research_15m",
        "enabled_attr": "intraday_research_enabled",
        "result": {"status": "ok", "reason": "wired", "details": {"timeframes": ["15m"]}},
    }


def test_intraday_research_timeframe_chunk_job_wires_symbol_chunk_runner(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(job_id, enabled_attr, action):  # noqa: ANN001
        captured["job_id"] = job_id
        captured["enabled_attr"] = enabled_attr
        captured["result"] = action(Settings())

    monkeypatch.setattr(worker, "_run_intraday_job", fake_run)
    monkeypatch.setattr(
        worker,
        "_run_intraday_research",
        lambda _settings, *, timeframes=None, symbol_chunk=None: {
            "status": "ok",
            "reason": "wired",
            "details": {"timeframes": timeframes, "symbol_chunk": symbol_chunk},
        },
    )

    worker.intraday_research_timeframe_chunk_job("15m", 1, 2)

    assert captured == {
        "job_id": "intraday_research_15m_chunk_2_of_2",
        "enabled_attr": "intraday_research_enabled",
        "result": {
            "status": "ok",
            "reason": "wired",
            "details": {"timeframes": ["15m"], "symbol_chunk": (1, 2)},
        },
    }


def test_intraday_research_request_uses_intraday_specific_parameters() -> None:
    settings = Settings(
        intraday_research_period="15d",
        intraday_research_limit_default=7,
        intraday_research_window_sizes="10,20",
        intraday_research_forward_bars="2,4",
        intraday_research_stride=2,
        intraday_research_max_total_windows=500,
        intraday_research_max_windows_per_symbol=50,
        intraday_research_min_cluster_size=12,
        intraday_research_max_clusters_per_window=3,
        intraday_research_min_samples=25,
        intraday_research_min_effective_samples=5.0,
        intraday_research_min_symbols=3,
        intraday_research_min_years=1,
        intraday_universe_file="/tmp/small.csv",
    )

    request = worker._intraday_research_request(settings, "5m", symbols=["AAPL", "MSFT"])
    expected = worker._intraday_research_expected_params(settings, request)

    assert request.period == "15d"
    assert request.interval == "5m"
    assert request.symbols == ["AAPL", "MSFT"]
    assert request.store_rejected is None
    assert request.limit == 7
    assert request.window_sizes == [10, 20]
    assert request.forward_bars == [2, 4]
    assert expected["cadence"] == "intraday"
    assert expected["universe_file"] == "/tmp/small.csv"
    assert expected["min_samples"] == 25
    assert expected["min_effective_samples"] == 5.0
    assert expected["min_symbols"] == 3
    assert expected["min_years"] == 1
    assert expected["symbols"] == ["AAPL", "MSFT"]


def test_intraday_research_request_can_disable_rejected_storage_for_process_chunks() -> None:
    settings = Settings()

    request = worker._intraday_research_request(
        settings,
        "5m",
        symbols=["AAPL", "MSFT"],
        store_rejected=False,
    )

    assert request.store_rejected is False


def test_intraday_research_symbol_chunks_are_disjoint(monkeypatch) -> None:
    settings = Settings(intraday_research_limit_default=6, intraday_universe_file="/tmp/small.csv")
    monkeypatch.setattr(
        worker,
        "pick_symbols",
        lambda *, limit, interval, universe_file: ["A", "B", "C", "D", "E", "F"],
    )

    first = worker._intraday_research_symbols_for_chunk(settings, "5m", (0, 2))
    second = worker._intraday_research_symbols_for_chunk(settings, "5m", (1, 2))

    assert first == ["A", "C", "E"]
    assert second == ["B", "D", "F"]
    assert set(first).isdisjoint(second)
