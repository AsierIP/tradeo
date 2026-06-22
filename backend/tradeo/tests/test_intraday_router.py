from __future__ import annotations

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


def test_intraday_status_requires_admin() -> None:
    response = _client().get("/api/intraday/status")
    assert response.status_code == 401


def test_intraday_status_and_preview_are_safe() -> None:
    client = _client()

    status = client.get("/api/intraday/status", auth=_auth())
    assert status.status_code == 200
    payload = status.json()
    assert payload["config"]["enabled"] is False
    assert payload["config"]["live_armed"] is False

    preview = client.post("/api/intraday/flat/preview", auth=_auth())
    assert preview.status_code == 200
    assert preview.json()["preview"] is True


def test_intraday_request_flat_is_backend_gated() -> None:
    response = _client().post("/api/intraday/flat/request", auth=_auth())

    assert response.status_code == 409
    assert "not armed" in response.json()["detail"]
