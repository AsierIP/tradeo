from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tradeo.core.config import Settings
from tradeo.core.security import require_admin
from tradeo.modules.daily_swing.setup_watchlist import (
    DailySetupWatchlist,
    SetupEvaluation,
    build_watchlist_artifact,
    create_setup_watchlist_item,
    stable_source_evidence_hash,
    transition_setup_state,
)
from tradeo.routers.daily import router as daily_router


def _watchlist(tmp_path, **kwargs) -> DailySetupWatchlist:
    return DailySetupWatchlist(Settings(artifacts_dir=str(tmp_path), **kwargs))


def _source(**kwargs) -> dict[str, object]:
    base = {
        "symbol": "TMDX",
        "side": "long",
        "pattern_id": 7,
        "pattern_key": "daily_gap_follow_through",
        "detected_at": "2026-07-01T21:00:00+00:00",
        "entry": 100.0,
        "stop": 95.0,
        "target": 120.0,
    }
    base.update(kwargs)
    return base


@pytest.mark.parametrize(
    "reason",
    ["weak_trigger", "insufficient_volume", "needs_close_confirmation"],
)
def test_recoverable_reason_enters_watchlist(tmp_path, reason: str) -> None:
    setup = _watchlist(tmp_path).consider_setup(
        _source(),
        SetupEvaluation(recoverable_reasons=(reason,), reward_risk=4.2),
        now=datetime(2026, 7, 1, 21, 5, tzinfo=timezone.utc),
    )

    assert setup is not None
    assert setup.status == "watching"
    assert reason in setup.recoverable_reasons


@pytest.mark.parametrize(
    "reason",
    ["reward_risk_insufficient", "product_policy_fail", "lookahead_risk"],
)
def test_non_recoverable_reason_does_not_enter_watchlist(tmp_path, reason: str) -> None:
    setup = _watchlist(tmp_path).consider_setup(
        _source(),
        SetupEvaluation(non_recoverable_reasons=(reason,), reward_risk=4.2),
    )

    assert setup is None


def test_reward_risk_below_minimum_does_not_enter_watchlist(tmp_path) -> None:
    setup = _watchlist(tmp_path).consider_setup(
        _source(),
        SetupEvaluation(recoverable_reasons=("weak_trigger",), reward_risk=2.0),
    )

    assert setup is None


def test_setup_passes_to_entry_ready_without_sending_order(tmp_path) -> None:
    setup = _watchlist(tmp_path).consider_setup(
        _source(),
        SetupEvaluation(
            entry_gate_passed=True,
            reward_risk=4.5,
            entry_score=0.9,
            trigger_score=0.8,
        ),
    )

    assert setup is not None
    assert setup.status == "entry_ready"
    assert setup.lab_paper_probe_request is not None
    assert setup.lab_paper_probe_request["route"] == "lab_paper_probe"
    assert setup.lab_paper_probe_request["submits_order"] is False
    assert setup.lab_paper_probe_request["allow_paper_on_entry_ready"] is False
    assert setup.to_dict()["orders_allowed"] is False
    assert setup.to_dict()["paper_allowed"] is False
    assert setup.to_dict()["live_allowed"] is False


def test_entry_ready_routes_to_lab_request_when_config_allows(tmp_path) -> None:
    setup = _watchlist(tmp_path, daily_setup_route_entry_ready_to_lab=True).consider_setup(
        _source(),
        SetupEvaluation(entry_gate_passed=True, reward_risk=4.5),
    )

    assert setup is not None
    assert setup.lab_paper_probe_request is not None
    assert setup.lab_paper_probe_request["enabled"] is True


def test_entry_ready_includes_focus_bucket_metadata_without_orders(tmp_path) -> None:
    watchlist = _watchlist(tmp_path, daily_setup_route_entry_ready_to_lab=True)
    setup = watchlist.consider_setup(
        _source(
            universe_bucket="daily_focus_core",
            bucket_reason="post close daily focus universe",
            bucket_version="daily_focus_universe_v1",
            pattern_family_key="family_daily_gap_follow_through",
        ),
        SetupEvaluation(
            entry_gate_passed=True,
            reward_risk=4.5,
            entry_score=0.9,
            trigger_score=0.8,
        ),
        now=datetime(2026, 7, 1, 21, 5, tzinfo=timezone.utc),
    )

    assert setup is not None
    record = setup.to_dict()
    request = setup.lab_paper_probe_request

    assert record["universe_bucket"] == "daily_focus_core"
    assert record["bucket_reason"] == "post close daily focus universe"
    assert record["bucket_version"] == "daily_focus_universe_v1"
    assert record["pattern_family"] == "family_daily_gap_follow_through"
    assert record["bucket_specific_gate_status"] == "pass"
    assert record["route_to_lab_reason"] == "entry_ready_lab_paper_probe_metadata"
    assert record["lab_probe_allowed"] is True
    assert isinstance(record["lab_probe_id"], str)
    assert request is not None
    assert request["universe_bucket"] == record["universe_bucket"]
    assert request["bucket_reason"] == record["bucket_reason"]
    assert request["bucket_version"] == record["bucket_version"]
    assert request["pattern_family"] == record["pattern_family"]
    assert request["bucket_specific_gate_status"] == record["bucket_specific_gate_status"]
    assert request["route_to_lab_reason"] == record["route_to_lab_reason"]
    assert request["lab_probe_allowed"] is True
    assert request["lab_probe_id"] == record["lab_probe_id"]

    for payload in (record, request):
        assert payload["orders_allowed"] is False
        assert payload["paper_allowed"] is False
        assert payload["live_allowed"] is False
        assert payload["submit_order_called"] is False

    artifact = watchlist.write_artifacts([setup])
    text = str(artifact).lower()
    assert artifact["items"][0]["lab_probe_id"] == record["lab_probe_id"]
    assert "foxhunter" not in text
    assert "paper_order_submitted" not in text


def test_entry_ready_route_disabled_keeps_probe_metadata_blocked(tmp_path) -> None:
    setup = _watchlist(tmp_path, daily_setup_route_entry_ready_to_lab=False).consider_setup(
        _source(universe_bucket="daily_focus_core"),
        SetupEvaluation(entry_gate_passed=True, reward_risk=4.5),
    )

    assert setup is not None
    assert setup.status == "entry_ready"
    assert setup.lab_probe_allowed is False
    assert setup.lab_probe_id is None
    assert setup.route_to_lab_reason == "daily_setup_route_entry_ready_to_lab_disabled"
    assert setup.lab_paper_probe_request is not None
    assert setup.lab_paper_probe_request["enabled"] is False
    assert setup.lab_paper_probe_request["lab_probe_allowed"] is False
    assert setup.lab_paper_probe_request["lab_probe_id"] is None
    assert setup.lab_paper_probe_request["orders_allowed"] is False
    assert setup.lab_paper_probe_request["paper_allowed"] is False


def test_bucket_specific_gate_status_is_validated(tmp_path) -> None:
    with pytest.raises(ValueError, match="bucket_specific_gate_status"):
        _watchlist(tmp_path).consider_setup(
            _source(bucket_specific_gate_status="ready_for_paper"),
            SetupEvaluation(entry_gate_passed=True, reward_risk=4.5),
        )


def test_watchlist_item_artifact_includes_focus_metadata_without_orders() -> None:
    item = create_setup_watchlist_item(
        symbol="tmdx",
        side="long",
        setup_id="daily-1",
        metadata={
            "universe_bucket": "daily_focus_core",
            "bucket_reason": "post close daily focus universe",
            "bucket_version": "daily_focus_universe_v1",
            "pattern_family": "family_daily_gap_follow_through",
            "lab_probe_allowed": True,
            "bucket_specific_gate_status": "pass",
        },
        now=datetime(2026, 7, 1, 21, 5, tzinfo=timezone.utc),
    )
    ready = transition_setup_state(
        item,
        "entry_ready",
        reason="entry_ready_watchlist_only",
        now=datetime(2026, 7, 1, 21, 10, tzinfo=timezone.utc),
    )

    artifact = build_watchlist_artifact([ready])
    record = artifact["items"][0]

    assert record["universe_bucket"] == "daily_focus_core"
    assert record["bucket_reason"] == "post close daily focus universe"
    assert record["bucket_version"] == "daily_focus_universe_v1"
    assert record["pattern_family"] == "family_daily_gap_follow_through"
    assert record["bucket_specific_gate_status"] == "pass"
    assert record["lab_probe_allowed"] is True
    assert isinstance(record["lab_probe_id"], str)
    assert record["route_to_lab_reason"] == "entry_ready_lab_paper_probe_metadata"
    assert record["orders_allowed"] is False
    assert record["paper_allowed"] is False
    assert record["live_allowed"] is False
    assert record["submit_order_called"] is False
    assert record["paper_order_submitted"] is False
    assert record["live_order_submitted"] is False


def test_setup_expires_after_max_age_days(tmp_path) -> None:
    watchlist = _watchlist(tmp_path, daily_setup_max_age_days=5)
    setup = watchlist.consider_setup(
        _source(detected_at="2026-07-01T21:00:00+00:00"),
        SetupEvaluation(recoverable_reasons=("weak_trigger",), reward_risk=4.2),
        now=datetime(2026, 7, 1, 22, 0, tzinfo=timezone.utc),
    )

    assert setup is not None
    watchlist.reevaluate(
        setup,
        SetupEvaluation(recoverable_reasons=("weak_trigger",), reward_risk=4.2),
        now=datetime(2026, 7, 6, 22, 0, tzinfo=timezone.utc),
    )

    assert setup.status == "expired"


def test_setup_invalidates_when_stop_or_context_breaks(tmp_path) -> None:
    watchlist = _watchlist(tmp_path)
    setup = watchlist.consider_setup(
        _source(),
        SetupEvaluation(recoverable_reasons=("weak_trigger",), reward_risk=4.2),
    )

    assert setup is not None
    watchlist.reevaluate(
        setup,
        SetupEvaluation(reward_risk=4.2, stop_context_broken=True, invalidation_reason="stop_lost"),
    )

    assert setup.status == "invalidated"
    assert setup.invalidation_reason == "stop_lost"


def test_watchlist_max_active_is_respected(tmp_path) -> None:
    watchlist = _watchlist(tmp_path, daily_setup_max_active=1)
    setups = []
    for idx in range(2):
        setup = watchlist.consider_setup(
            _source(
                symbol=f"SYM{idx}",
                detected_at=(
                    datetime(2026, 7, 1, tzinfo=timezone.utc) + timedelta(minutes=idx)
                ).isoformat(),
            ),
            SetupEvaluation(
                recoverable_reasons=("weak_trigger",),
                reward_risk=4.2,
                entry_score=float(idx),
            ),
        )
        assert setup is not None
        setups.append(setup)

    watchlist.enforce_max_active(setups)

    assert (
        sum(1 for setup in setups if setup.status not in {"expired", "invalidated", "entered"})
        == 1
    )


def test_source_evidence_hash_is_stable() -> None:
    assert stable_source_evidence_hash({"b": 2, "a": 1}) == stable_source_evidence_hash(
        {"a": 1, "b": 2}
    )


def test_no_daily_intraday_metric_mix_in_payload(tmp_path) -> None:
    setup = _watchlist(tmp_path).consider_setup(
        _source(),
        SetupEvaluation(recoverable_reasons=("weak_trigger",), reward_risk=4.2),
    )

    assert setup is not None
    assert setup.timeframe == "1d"
    assert "intraday" not in str(setup.to_dict()).lower()
    assert "foxhunter" not in str(setup.to_dict()).lower()


def test_direct_transition_to_entered_is_blocked(tmp_path) -> None:
    setup = _watchlist(tmp_path).consider_setup(
        _source(),
        SetupEvaluation(recoverable_reasons=("weak_trigger",), reward_risk=4.2),
    )

    assert setup is not None
    with pytest.raises(ValueError):
        setup.transition_to("entered")


def test_daily_watchlist_read_only_endpoints(tmp_path, monkeypatch) -> None:
    watchlist = _watchlist(tmp_path)
    setup = watchlist.consider_setup(
        _source(setup_id="setup-1"),
        SetupEvaluation(recoverable_reasons=("weak_trigger",), reward_risk=4.2),
    )
    assert setup is not None
    watchlist.write_artifacts([setup])

    app = FastAPI()
    app.include_router(daily_router, prefix="/api")
    app.dependency_overrides[require_admin] = lambda: "test"
    monkeypatch.setattr(
        "tradeo.modules.daily_swing.setup_watchlist.get_settings",
        lambda: Settings(artifacts_dir=str(tmp_path)),
    )

    client = TestClient(app)
    assert client.get("/api/daily/setup-watchlist").status_code == 200
    assert client.get("/api/daily/setup-watchlist/setup-1").json()["setup_id"] == "setup-1"
    summary = client.get("/api/daily/setup-watchlist/summary").json()
    assert summary["active_count"] == 1
    assert "change-me" not in str(summary).lower()
    assert "should-not-leak" not in str(summary).lower()
