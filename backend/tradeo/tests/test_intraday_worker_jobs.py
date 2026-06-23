from __future__ import annotations

from tradeo.schemas import DiscoveryRunResponse
from tradeo.core.config import Settings
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


def test_register_intraday_jobs_only_adds_enabled_intraday_specs() -> None:
    scheduler = FakeScheduler()
    settings = Settings(
        intraday_enabled=True,
        intraday_universe_enabled=True,
        intraday_data_sync_enabled=True,
        intraday_research_enabled=True,
        intraday_candidate_scan_enabled=True,
        intraday_observation_closer_enabled=True,
        intraday_risk_heartbeat_enabled=True,
        intraday_reconciliation_enabled=True,
        intraday_eod_flat_enabled=True,
        intraday_job_jitter_seconds=7,
        intraday_research_interval_seconds=33,
        intraday_candidate_scan_interval_seconds=120,
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
    intervals_by_id = {str(job["kwargs"]["id"]): job["kwargs"]["seconds"] for job in interval_jobs}
    assert intervals_by_id["intraday_research"] == 33
    assert intervals_by_id["intraday_candidate_scan"] == 120


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


def test_intraday_research_cycle_runs_discovery_and_match_without_market_gate(monkeypatch) -> None:
    class FakeDb:
        closed = False

        def close(self) -> None:
            self.closed = True

    db = FakeDb()
    settings = Settings(
        intraday_enabled=True,
        intraday_research_enabled=True,
        discovery_match_enabled=True,
    )
    calls: list[str] = []

    monkeypatch.setattr(worker, "SessionLocal", lambda: db)
    def fake_discovery(_settings, _db, request=None):  # noqa: ANN001
        calls.append(f"discovery:{request.interval if request else 'default'}")
        return DiscoveryRunResponse(
            run_id=42,
            status="skipped",
            symbols_scanned=0,
            windows_sampled=0,
            clusters_evaluated=0,
            accepted_patterns=0,
            rejected_patterns=0,
            stored_patterns=0,
            duration_seconds=0.0,
            warnings=["recent_equivalent_discovery_run"],
        )

    monkeypatch.setattr(worker, "_run_discovery_cycle", fake_discovery)

    class FakeMatcher:
        def match_current(self, _db, **kwargs):  # noqa: ANN001
            calls.append("match")
            return {
                "patterns_checked": kwargs["max_patterns"],
                "symbols_checked": kwargs["limit"],
                "stored_matches": 3,
            }

    monkeypatch.setattr(worker, "NovelPatternMatcher", FakeMatcher)

    payload = worker._intraday_research_cycle(settings)

    assert calls == ["discovery:15m", "discovery:5m", "match"]
    assert db.closed is True
    assert payload["status"] == "ok"
    assert payload["reason"] == "research_cycle_closed_market_allowed"
    assert payload["details"]["market_hours_required"] is False
    assert payload["details"]["discovery_run_id"] == 42
    assert payload["details"]["stored_matches"] == 3
