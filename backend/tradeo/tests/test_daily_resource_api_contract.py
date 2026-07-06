from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

from tradeo.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def _auth() -> tuple[str, str]:
    return (
        os.environ.get("TRADEO_ADMIN_USERNAME", "admin"),
        os.environ.get("TRADEO_ADMIN_PASSWORD", "change-me"),
    )


def test_resource_policy_status_requires_admin() -> None:
    response = _client().get("/api/resource-policy/status")

    assert response.status_code == 401


def test_resource_policy_status_is_read_only_and_blocks_orders() -> None:
    response = _client().get("/api/resource-policy/status", auth=_auth())

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "tradeo.resource_policy.status.v1"
    assert payload["read_only"] is True
    assert payload["safety"]["write_endpoints_exposed"] is False
    assert payload["safety"]["paper_order_submission_allowed"] is False
    assert payload["safety"]["live_order_submission_allowed"] is False
    assert "order.live" in payload["policy"]["blocked_resources"]
    assert "order.paper" in payload["policy"]["blocked_resources"]
    assert "change-me" not in json.dumps(payload).lower()


def test_daily_setup_watchlist_status_is_read_only_contract(tmp_path, monkeypatch) -> None:
    artifact_path = tmp_path / "runtime" / "daily_setup_watchlist" / "latest.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text(
        json.dumps(
            {
                "schema_version": "tradeo.daily_swing.setup_watchlist_artifact.v1",
                "generated_at": "2026-07-06T20:05:00Z",
                "status": "ok",
                "items": [
                    {
                        "setup_id": "daily-1",
                        "symbol": "TMDX",
                        "side": "long",
                        "state": "watchlist",
                        "metadata": {"api_key": "should-not-leak"},
                    }
                ],
                "state_counts": {"watchlist": 1},
                "entry_ready_count": 0,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TRADEO_ARTIFACTS_DIR", str(tmp_path))
    from tradeo.core.config import get_settings

    get_settings.cache_clear()
    try:
        response = _client().get("/api/daily/setup-watchlist/status", auth=_auth())
        summary = _client().get("/api/daily/setup-watchlist/summary", auth=_auth())
        item = _client().get("/api/daily/setup-watchlist/daily-1", auth=_auth())
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    assert payload["contract"]["allowed_methods"] == ["GET"]
    assert payload["contract"]["write_endpoint_available"] is False
    assert payload["contract"]["order_submission_allowed"] is False
    assert payload["contract"]["fox_hunter_promotion_allowed"] is False
    assert payload["watchlist"]["count"] == 1
    assert payload["watchlist"]["symbols"] == ["TMDX"]
    assert "should-not-leak" not in json.dumps(payload)

    assert summary.status_code == 200
    assert summary.json()["active_count"] == 1
    assert item.status_code == 200
    assert item.json()["setup_id"] == "daily-1"


def test_daily_setup_watchlist_post_is_not_available() -> None:
    response = _client().post("/api/daily/setup-watchlist", auth=_auth())

    assert response.status_code == 405
