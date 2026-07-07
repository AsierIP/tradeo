from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from tradeo.core.config import Settings
from tradeo.main import create_app
from tradeo.modules.daily_swing.setup_watchlist import DailySetupWatchlist, SetupEvaluation
from tradeo.modules.laboratory.paper_readiness import build_paper_readiness_report
from tradeo.modules.resource_policy.enforcement import (
    DENY_PAPER_SUBMIT,
    DENY_POLICY_DENIED,
    DENY_POLICY_MISSING,
    DENY_SESSION_UNKNOWN,
    ResourcePolicyDecision,
    assert_job_allowed,
    blocked_job_status,
)
from tradeo.modules.resource_policy.market_session_resource_policy import (
    JobType,
    MarketSessionResourcePolicy,
    PriorityLevel,
    SessionState,
)
from tradeo.routers import resource_policy_guard
from tradeo.tasks import worker

REPO_ROOT = Path(__file__).resolve().parents[3]
ACCOUNT_ID = re.compile(r"\b(?:DU|U|F|FA)\d{5,}\b", re.IGNORECASE)


def _policy(tmp_path: Path, state: str) -> MarketSessionResourcePolicy:
    return MarketSessionResourcePolicy(
        settings=Settings(artifacts_dir=str(tmp_path)),
        forced_session_state=state,
    )


def _auth() -> tuple[str, str]:
    return (
        os.environ.get("TRADEO_ADMIN_USERNAME", "admin"),
        os.environ.get("TRADEO_ADMIN_PASSWORD", "change-me"),
    )


def _safe_paper_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "trading_mode": "paper",
        "live_trading_enabled": False,
        "intraday_live_enabled": False,
        "intraday_paper_enabled": False,
        "ibkr_readonly": True,
        "ibkr_port": 7497,
        "ibkr_allow_market_orders": False,
        "laboratory_auto_submit_paper_orders": False,
        "fox_hunter_auto_submit_live_orders": False,
        "reconciliation_auto_repair_paper_exits": False,
        "kill_switch_enabled": False,
        "intraday_max_trades_per_day": 2,
        "intraday_daily_loss_limit_pct": 0.005,
        "max_position_value_pct": 0.10,
        "ibkr_max_order_value_usd": 500.0,
    }
    values.update(overrides)
    return Settings(**values)


def _daily_source(**overrides: object) -> dict[str, object]:
    source: dict[str, object] = {
        "symbol": "TMDX",
        "side": "long",
        "pattern_id": 7,
        "pattern_key": "daily_gap_follow_through",
        "detected_at": "2026-07-01T21:00:00+00:00",
        "entry": 100.0,
        "stop": 95.0,
        "target": 120.0,
    }
    source.update(overrides)
    return source


def test_policy_blocks_rth_heavy_allows_closed_and_persists_deny_reason(tmp_path: Path) -> None:
    regular = _policy(tmp_path, SessionState.REGULAR_MARKET)
    closed = _policy(tmp_path, SessionState.MARKET_CLOSED)

    blocked = assert_job_allowed(JobType.RESEARCH_HEAVY, "research", policy=regular)
    allowed = assert_job_allowed(JobType.RESEARCH_HEAVY, "research", policy=closed)

    assert blocked.allowed is False
    assert blocked.priority == PriorityLevel.BLOCKED
    assert blocked.can_submit_orders is False
    assert blocked.deny_reason
    assert blocked.deny_reason.startswith(f"{DENY_POLICY_DENIED}:")
    status = blocked_job_status(blocked)
    assert str(status["reason"]).startswith(DENY_POLICY_DENIED)
    assert status["details"]["resource_policy"]["deny_reason"] == blocked.deny_reason
    assert status["details"]["resource_policy"]["session_state"] == SessionState.REGULAR_MARKET

    assert allowed.allowed is True
    assert allowed.priority == PriorityLevel.HIGH
    assert allowed.can_submit_orders is False


def test_unknown_missing_and_direct_paper_submit_fail_closed(tmp_path: Path) -> None:
    unknown = assert_job_allowed(
        JobType.RESEARCH_HEAVY,
        "research",
        policy=_policy(tmp_path, SessionState.UNKNOWN),
    )
    missing = assert_job_allowed(JobType.RESEARCH_HEAVY, "research")
    regular = _policy(tmp_path, SessionState.REGULAR_MARKET)
    paper_direct = regular.decide_job("paper_submit")
    paper_wrapped = assert_job_allowed(JobType.PAPER_SUBMIT, "daily_watchlist", policy=regular)

    assert unknown.allowed is False
    assert unknown.session_state == SessionState.UNKNOWN
    assert unknown.deny_reason == DENY_SESSION_UNKNOWN
    assert missing.allowed is False
    assert missing.session_state == SessionState.UNKNOWN
    assert missing.deny_reason == DENY_POLICY_MISSING
    assert isinstance(regular.current_budget().ibkr_write_allowed, bool)
    assert paper_direct.allowed is False
    assert paper_direct.priority == PriorityLevel.BLOCKED
    assert paper_wrapped.allowed is False
    assert paper_wrapped.can_submit_orders is False
    assert paper_wrapped.deny_reason == DENY_PAPER_SUBMIT


def test_daily_watchlist_entry_ready_does_not_submit_or_mix_runtime_metrics(tmp_path: Path) -> None:
    watchlist = DailySetupWatchlist(
        Settings(artifacts_dir=str(tmp_path), daily_setup_route_entry_ready_to_lab=True)
    )
    setup = watchlist.consider_setup(
        _daily_source(),
        SetupEvaluation(entry_gate_passed=True, reward_risk=4.5, entry_score=0.9),
    )

    assert setup is not None
    assert setup.status == "entry_ready"
    assert setup.lab_paper_probe_request is not None
    assert setup.lab_paper_probe_request["enabled"] is True
    assert setup.lab_paper_probe_request["submits_order"] is False
    assert setup.lab_paper_probe_request["allow_paper_on_entry_ready"] is False

    artifact = watchlist.write_artifacts([setup])
    text = json.dumps(artifact, sort_keys=True)
    assert artifact["orders_allowed"] is False
    assert artifact["paper_allowed"] is False
    assert artifact["live_allowed"] is False
    assert artifact["submit_order_called"] is False
    assert "orders_submitted" not in text
    assert "submitted_to_broker" not in text
    assert "broker_order_id" not in text
    assert "intraday_" not in text
    assert "live_trade" not in text


def test_lab_paper_probe_policy_priority_does_not_bypass_probe_runner_gate(tmp_path: Path) -> None:
    policy_decision = assert_job_allowed(
        JobType.LAB_PAPER_PROBE,
        "lab",
        policy=_policy(tmp_path, SessionState.REGULAR_MARKET),
    )
    report = build_paper_readiness_report(settings=_safe_paper_settings())

    assert policy_decision.allowed is True
    assert policy_decision.can_submit_orders is False
    assert report["status"] == "READY_FOR_DIRECTOR_PAPER_REVIEW"
    assert report["dry_run_only"] is True
    assert report["submit_allowed"] is False
    assert report["submit_order_called"] is False
    assert report["paper_orders_sent"] is False
    assert report["live_orders_sent"] is False


def test_resource_policy_and_daily_endpoints_are_get_only_read_only_and_redacted() -> None:
    app = create_app()
    client = TestClient(app)
    watched_paths = {
        "/api/resource-policy/status",
        "/api/daily/setup-watchlist",
        "/api/daily/setup-watchlist/status",
        "/api/daily/setup-watchlist/summary",
        "/api/daily/setup-watchlist/contract",
    }

    unsafe_routes: list[str] = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if path not in watched_paths:
            continue
        methods = set(getattr(route, "methods", set()) or set())
        unsafe = methods - {"GET", "HEAD"}
        if unsafe:
            unsafe_routes.append(f"{path}:{sorted(unsafe)}")
    assert unsafe_routes == []

    policy_response = client.get("/api/resource-policy/status", auth=_auth())
    daily_response = client.get("/api/daily/setup-watchlist/status", auth=_auth())
    assert policy_response.status_code == 200
    assert daily_response.status_code == 200
    for payload in (policy_response.json(), daily_response.json()):
        serialized = json.dumps(payload, sort_keys=True)
        assert payload["read_only"] is True
        assert "change-me" not in serialized.lower()
        assert "should-not-leak" not in serialized
        assert ACCOUNT_ID.search(serialized) is None

    assert client.post("/api/resource-policy/status", auth=_auth()).status_code == 405
    assert client.post("/api/daily/setup-watchlist/status", auth=_auth()).status_code == 405


def test_admin_heavy_launch_routes_have_resource_policy_guard() -> None:
    expected = {
        "backend/tradeo/routers/scan.py": ("assert_route_job_allowed", "LARGE_SCANNER"),
        "backend/tradeo/routers/research.py": ("assert_route_job_allowed", "RESEARCH_HEAVY"),
        "backend/tradeo/routers/backtests.py": ("assert_route_job_allowed", "HEAVY_BACKTEST"),
        "backend/tradeo/routers/self_improvement.py": ("assert_route_job_allowed", "HEAVY_BACKTEST"),
    }

    missing: list[str] = []
    for relative_path, needles in expected.items():
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        if not all(needle in text for needle in needles):
            missing.append(relative_path)
    assert missing == []


def test_route_resource_policy_guard_blocks_before_heavy_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_policy(*_args: object, **_kwargs: object) -> ResourcePolicyDecision:
        return ResourcePolicyDecision(
            allowed=False,
            job_type=JobType.HEAVY_BACKTEST,
            owner="research",
            priority=PriorityLevel.BLOCKED,
            deny_reason="resource_policy_denied:heavy_backtest:regular_market",
            session_state=SessionState.REGULAR_MARKET,
            can_submit_orders=False,
        )

    monkeypatch.setattr(
        resource_policy_guard,
        "decide_with_market_session_policy",
        fake_policy,
        raising=False,
    )

    with pytest.raises(HTTPException) as exc_info:
        resource_policy_guard.assert_route_job_allowed(JobType.HEAVY_BACKTEST, "research")

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["decision"] == "blocked_resource_policy"
    assert exc_info.value.detail["can_submit_orders"] is False
    assert (
        exc_info.value.detail["resource_policy"]["deny_reason"]
        == "resource_policy_denied:heavy_backtest:regular_market"
    )


def test_daily_setup_panel_has_no_live_submit_or_foxhunter_action_button() -> None:
    source = (REPO_ROOT / "frontend" / "app" / "page.tsx").read_text(encoding="utf-8")
    start = source.index("function DailySetupWatchlistPanel")
    end = source.index("function OperationsModule", start)
    panel = source[start:end]

    assert "<button" not in panel
    assert "onClick" not in panel
    assert "order_submission_allowed" in panel
    assert "fox_hunter_promotion_allowed" in panel


def test_no_artifacts_runtime_paths_are_tracked() -> None:
    if not (REPO_ROOT / ".git").exists():
        pytest.skip("git metadata unavailable")
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    tracked_runtime = [
        path
        for path in result.stdout.splitlines()
        if "/artifacts/runtime/" in f"/{path}" or path.startswith("artifacts/runtime/")
    ]
    assert tracked_runtime == []


def test_capacity_runner_has_heavy_research_resource_policy_gate() -> None:
    text = (REPO_ROOT / "scripts" / "intraday_history_capacity_loop.py").read_text(
        encoding="utf-8"
    )

    assert "assert_job_allowed" in text or "decide_with_market_session_policy" in text
    assert "research_heavy" in text or "RESEARCH_HEAVY" in text


def test_intraday_wave_runner_has_execute_resource_policy_gate() -> None:
    text = (REPO_ROOT / "scripts" / "run_intraday_research_wave.py").read_text(
        encoding="utf-8"
    )

    assert "assert_job_allowed" in text or "decide_with_market_session_policy" in text
    assert "research_light" in text or "research_heavy" in text or "RESEARCH_" in text


def test_daily_gap_runners_have_daily_resource_policy_gate() -> None:
    paths = [
        REPO_ROOT / "scripts" / "run_daily_gap_matrix_dry_run.py",
        REPO_ROOT / "scripts" / "run_daily_gap_confirmatory_matrix.py",
    ]

    missing: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        has_policy = "assert_job_allowed" in text or "decide_with_market_session_policy" in text
        has_policy_job = (
            "heavy_backtest" in text
            or "HEAVY_BACKTEST" in text
            or "research_heavy" in text
            or "RESEARCH_HEAVY" in text
        )
        if not (has_policy and has_policy_job):
            missing.append(path.relative_to(REPO_ROOT).as_posix())
    assert missing == []


def test_worker_blocks_heavy_research_before_running_action_when_policy_denies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = Settings(
        artifacts_dir=str(tmp_path),
        intraday_enabled=True,
        intraday_research_enabled=True,
    )
    statuses: list[dict[str, object]] = []
    action_called = False

    def fake_policy(*_args: object, **_kwargs: object) -> ResourcePolicyDecision:
        return ResourcePolicyDecision(
            allowed=False,
            job_type=JobType.RESEARCH_HEAVY,
            owner="research",
            priority=PriorityLevel.BLOCKED,
            deny_reason="resource_policy_denied:research_heavy:regular_market",
            session_state=SessionState.REGULAR_MARKET,
            can_submit_orders=False,
        )

    def forbidden_action(_settings: Settings) -> dict[str, object]:
        nonlocal action_called
        action_called = True
        return {"status": "ok", "reason": "should_not_run", "details": {}}

    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "decide_with_market_session_policy", fake_policy, raising=False)
    monkeypatch.setattr(
        worker,
        "write_intraday_session_status",
        lambda job_id, payload, _settings: statuses.append({"job_id": job_id, **payload}),
    )

    payload = worker._run_intraday_job(
        "intraday_research_process_pool",
        "intraday_research_enabled",
        forbidden_action,
    )

    assert action_called is False
    assert payload["status"] == "skipped"
    assert payload["reason"] == "resource_policy_denied"
    assert (
        payload["details"]["resource_policy"]["deny_reason"]
        == "resource_policy_denied:research_heavy:regular_market"
    )
    assert statuses[-1]["details"]["resource_policy"]["deny_reason"]


def test_intraday_data_sync_is_classified_as_heavy_research() -> None:
    assert worker._resource_policy_job_type("intraday_data_sync") == JobType.RESEARCH_HEAVY
