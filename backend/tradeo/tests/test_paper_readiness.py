from __future__ import annotations

import sys

from tradeo.core.config import Settings
from tradeo.modules.laboratory.paper_readiness import build_paper_readiness_report


def _forget_broker_modules() -> None:
    sys.modules.pop("tradeo.services.ibkr_broker", None)
    sys.modules.pop("tradeo.services.paper_broker", None)


def _safe_settings(**overrides):
    base = {
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
    base.update(overrides)
    return Settings(**base)


def test_paper_readiness_ready_for_director_review_only_in_safe_config() -> None:
    report = build_paper_readiness_report(settings=_safe_settings())

    assert report["status"] == "READY_FOR_DIRECTOR_PAPER_REVIEW"
    assert report["dry_run_only"] is True
    assert report["submit_allowed"] is False
    assert report["bracket_order_preview"]["submit_allowed"] is False
    assert report["paper_orders_sent"] is False
    assert report["live_orders_sent"] is False


def test_paper_readiness_blocks_live_mode_and_live_flags() -> None:
    report = build_paper_readiness_report(settings=_safe_settings(trading_mode="live"))
    enabled = build_paper_readiness_report(settings=_safe_settings(live_trading_enabled=True))

    assert report["status"] == "BLOCKED"
    assert "trading_mode_not_live" in report["blockers"]
    assert enabled["status"] == "BLOCKED"
    assert "live_trading_disabled" in enabled["blockers"]


def test_paper_readiness_blocks_market_orders_and_auto_submit() -> None:
    market = build_paper_readiness_report(settings=_safe_settings(ibkr_allow_market_orders=True))
    paper_auto = build_paper_readiness_report(settings=_safe_settings(laboratory_auto_submit_paper_orders=True))
    live_auto = build_paper_readiness_report(settings=_safe_settings(fox_hunter_auto_submit_live_orders=True))

    assert "market_orders_disabled" in market["blockers"]
    assert "lab_auto_submit_paper_disabled" in paper_auto["blockers"]
    assert "fox_auto_submit_live_disabled" in live_auto["blockers"]


def test_paper_readiness_blocks_readonly_false() -> None:
    report = build_paper_readiness_report(settings=_safe_settings(ibkr_readonly=False))

    assert report["status"] == "BLOCKED"
    assert "ibkr_readonly" in report["blockers"]


def test_paper_readiness_blocks_paper_enabled_and_live_port() -> None:
    paper = build_paper_readiness_report(settings=_safe_settings(intraday_paper_enabled=True))
    live_port = build_paper_readiness_report(settings=_safe_settings(ibkr_port=7496))

    assert paper["status"] == "BLOCKED"
    assert "intraday_paper_disabled_for_tlab002" in paper["blockers"]
    assert live_port["status"] == "BLOCKED"
    assert "ibkr_not_live_port" in live_port["blockers"]


def test_paper_readiness_detects_kill_switch_as_not_ready_gap() -> None:
    report = build_paper_readiness_report(settings=_safe_settings(kill_switch_enabled=True))

    assert report["status"] == "NOT_READY"
    assert "kill_switch_clear" in report["gaps"]


def test_paper_readiness_requires_limits() -> None:
    report = build_paper_readiness_report(settings=_safe_settings(intraday_max_trades_per_day=0))

    assert report["status"] == "NOT_READY"
    assert "max_trades_per_day_defined" in report["gaps"]


def test_paper_readiness_redacts_secrets_and_does_not_import_brokers() -> None:
    _forget_broker_modules()

    report = build_paper_readiness_report(settings=_safe_settings(ibkr_account="DU123456"))

    assert report["redacted"] is True
    assert "DU123456" not in repr(report)
    assert "tradeo.services.ibkr_broker" not in sys.modules
    assert "tradeo.services.paper_broker" not in sys.modules
