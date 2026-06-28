from __future__ import annotations

from datetime import datetime, timezone

import pytest

from tradeo.core.config import Settings
from tradeo.routers import health
from tradeo.services.ibkr_broker import IBKRBroker, IBKROperationalError


class FakeIB:
    def __init__(self, accounts: list[str] | None = None) -> None:
        self.accounts = accounts or []
        self.connected = True
        self.disconnected = False

    def reqCurrentTime(self) -> datetime:  # noqa: N802
        return datetime(2026, 6, 18, 12, 0, tzinfo=timezone.utc)

    def managedAccounts(self) -> list[str]:  # noqa: N802
        return self.accounts

    def isConnected(self) -> bool:  # noqa: N802
        return self.connected

    def disconnect(self) -> None:
        self.connected = False
        self.disconnected = True


def _live_settings(**overrides) -> Settings:
    defaults = {
        "trading_mode": "live",
        "live_trading_enabled": True,
        "live_trading_confirmation_value": "I_ACCEPT_LIVE_MARKET_RISK",
        "ibkr_readonly": False,
        "ibkr_port": 7496,
        "ibkr_account": "DU123456",
        "ibkr_allowed_symbols": "AAPL,MSFT",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_account_readiness_preflight_passes_without_order_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_ib = FakeIB(["DU123456"])
    broker = IBKRBroker(settings=_live_settings())
    monkeypatch.setattr(broker, "_connect", lambda: fake_ib)

    status = broker.account_readiness_preflight(symbols=["aapl"])

    assert status["ok"] is True
    assert status["state"] == "ready"
    assert status["selected_account_configured"] is True
    assert status["selected_account_present"] is True
    assert status["selected_account_managed"] is True
    assert status["allowed_symbol_count"] == 2
    assert status["checked_symbol_count"] == 1
    assert status["account_summary_included"] is False
    assert status["order_checks_included"] is False
    assert "selected_account" not in status
    assert "managed_accounts" not in status
    assert fake_ib.disconnected is True
    assert all(check["ok"] for check in status["checks"])


def test_account_readiness_preflight_blocks_unmanaged_account_and_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_ib = FakeIB(["DU111111"])
    broker = IBKRBroker(settings=_live_settings(ibkr_allowed_symbols="AAPL"))
    monkeypatch.setattr(broker, "_connect", lambda: fake_ib)

    status = broker.account_readiness_preflight(symbols=["AAPL", "MSFT"])

    assert status["ok"] is False
    assert "configured_ibkr_account_not_managed" in status["block_reasons"]
    assert "symbols_not_allowed" in status["block_reasons"]
    symbol_check = next(check for check in status["checks"] if check["name"] == "requested_symbols_allowed")
    assert symbol_check["missing_symbols"] == ["MSFT"]


def test_account_readiness_preflight_blocks_explicitly_blocked_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_ib = FakeIB(["DU123456"])
    broker = IBKRBroker(
        settings=_live_settings(
            ibkr_account="DU123456",
            ibkr_blocked_accounts="U999999, du123456",
        )
    )
    monkeypatch.setattr(broker, "_connect", lambda: fake_ib)

    status = broker.account_readiness_preflight(symbols=["AAPL"])

    assert status["ok"] is False
    assert status["selected_account_blocked"] is True
    assert "blocked_ibkr_account" in status["block_reasons"]


def test_account_readiness_preflight_reports_static_live_blockers_without_order_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_ib = FakeIB(["DU123456"])
    broker = IBKRBroker(
        settings=_live_settings(
            ibkr_readonly=True,
            ibkr_port=7497,
            ibkr_account="",
            ibkr_allowed_symbols="",
        )
    )
    monkeypatch.setattr(broker, "_connect", lambda: fake_ib)

    status = broker.account_readiness_preflight()

    assert status["ok"] is False
    assert "ibkr_readonly" in status["block_reasons"]
    assert "ibkr_live_port_required" in status["block_reasons"]
    assert "missing_ibkr_account" in status["block_reasons"]
    assert "missing_ibkr_allowed_symbols" in status["block_reasons"]


def test_account_readiness_preflight_returns_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broker = IBKRBroker(settings=_live_settings())
    monkeypatch.setattr(
        broker,
        "_connect",
        lambda: (_ for _ in ()).throw(IBKROperationalError("gateway down")),
    )

    status = broker.account_readiness_preflight()

    assert status["ok"] is False
    assert status["primary_block_reason"] == "ibkr_connection_failed"
    assert "ibkr_connection_failed" in status["block_reasons"]
    assert status["connected"] is False
    assert status["managed_accounts_count"] == 0


def test_health_live_preflight_uses_sanitized_broker_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeBroker:
        def account_readiness_preflight(self) -> dict[str, object]:
            return {
                "ok": True,
                "selected_account_present": True,
                "managed_accounts_count": 1,
                "account_summary_included": False,
                "order_checks_included": False,
            }

    monkeypatch.setattr(health, "IBKRBroker", FakeBroker)

    status = health.ibkr_live_preflight()

    assert status["ok"] is True
    assert status["selected_account_present"] is True
    assert "selected_account" not in status
