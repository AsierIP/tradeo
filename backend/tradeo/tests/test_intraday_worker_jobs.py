from __future__ import annotations

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
        intraday_universe_file="/tmp/small.csv",
    )

    request = worker._intraday_research_request(settings, "5m")
    expected = worker._intraday_research_expected_params(settings, request)

    assert request.period == "15d"
    assert request.interval == "5m"
    assert request.limit == 7
    assert request.window_sizes == [10, 20]
    assert request.forward_bars == [2, 4]
    assert expected["cadence"] == "intraday"
    assert expected["universe_file"] == "/tmp/small.csv"
