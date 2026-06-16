from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from tradeo.routers import ibkr
from tradeo.services.ibkr_broker import IBKROperationalError


def test_ibkr_account_route_uses_threadpool_wrapper(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeBroker:
        def account_snapshot(self) -> dict[str, object]:
            return {"ok": True}

    async def fake_run(func, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        calls.append(func.__name__)
        return func(*args, **kwargs)

    monkeypatch.setattr(ibkr, "IBKRBroker", FakeBroker)
    monkeypatch.setattr(ibkr, "_run_ibkr_call", fake_run)

    result = asyncio.run(ibkr.ibkr_account("admin"))

    assert result == {"ok": True}
    assert calls == ["account_snapshot"]


def test_ibkr_account_operational_error_stays_502(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeBroker:
        def account_snapshot(self) -> dict[str, object]:
            raise IBKROperationalError("gateway down")

    async def fake_run(func, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return func(*args, **kwargs)

    monkeypatch.setattr(ibkr, "IBKRBroker", FakeBroker)
    monkeypatch.setattr(ibkr, "_run_ibkr_call", fake_run)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(ibkr.ibkr_account("admin"))

    assert excinfo.value.status_code == 502
    assert excinfo.value.detail == "gateway down"
