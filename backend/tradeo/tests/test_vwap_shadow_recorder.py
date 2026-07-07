from __future__ import annotations

from datetime import datetime, timezone
import sys

import pandas as pd

from tradeo.core.config import Settings
from tradeo.modules.laboratory.vwap_shadow_recorder import (
    ShadowQuote,
    build_vwap_shadow_record,
    redact_shadow_record,
)


def _forget_broker_modules() -> None:
    sys.modules.pop("tradeo.services.ibkr_broker", None)
    sys.modules.pop("tradeo.services.paper_broker", None)


def _bars(closes: list[float]) -> pd.DataFrame:
    timestamps = pd.date_range("2026-07-02 09:30", periods=len(closes), freq="1min", tz="America/New_York")
    return pd.DataFrame(
        [
            {
                "timestamp": ts.isoformat(),
                "open": close,
                "high": close + 0.05,
                "low": close - 0.05,
                "close": close,
                "volume": 1000,
            }
            for ts, close in zip(timestamps, closes, strict=True)
        ]
    )


def test_shadow_recorded_with_mock_quote_and_vwap_signal() -> None:
    record = build_vwap_shadow_record(
        symbol="aapl",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(bid=100.0, ask=100.02, last=100.01),
        bars=_bars([100.0, 99.9, 100.4]),
        market_open=True,
        now=datetime(2026, 7, 2, 14, 0, tzinfo=timezone.utc),
    )

    assert record["schema_version"] == "tradeo.lab_vwap_shadow.v1"
    assert record["decision"] == "shadow_recorded"
    assert record["symbol"] == "AAPL"
    assert record["quote_status"] == "available"
    assert record["spread_bps"] is not None
    assert record["orders_allowed"] is False
    assert record["paper_allowed"] is False
    assert record["live_allowed"] is False


def test_vwap_reclaim_signal_context_can_be_true() -> None:
    record = build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(bid=9.98, ask=10.02, last=10.0),
        bars=_bars([10.0, 9.0, 9.0, 12.0]),
        market_open=True,
    )

    assert record["candidate_signal"] is True
    assert record["entry_reason"] == "vwap_reclaim_long"
    assert record["entry_context"]["condition_passed"] is True
    assert record["entry_context"]["above_vwap"] is True


def test_quote_unavailable_does_not_fail_or_place_orders() -> None:
    record = build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(),
        market_open=True,
    )

    assert record["decision"] == "quote_unavailable"
    assert record["quote_status"] == "unavailable"
    assert record["submit_order_called"] is False
    assert record["paper_order_submitted"] is False
    assert record["live_order_submitted"] is False


def test_market_closed_is_acceptable_smoke_result() -> None:
    record = build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(),
        market_open=False,
    )

    assert record["decision"] == "market_closed"
    assert record["orders_allowed"] is False


def test_mfe_mae_and_net_r_estimates_from_future_bars() -> None:
    record = build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(bid=100.0, ask=100.02, last=100.0),
        future_bars=_bars([100.5, 101.0, 99.5]),
        market_open=True,
    )

    assert record["mfe_r"] is not None
    assert record["mae_r"] is not None
    assert record["gross_r"] is not None
    assert record["net_r_estimate"] is not None
    assert record["spread_cost_r"] is not None
    assert record["cost_x2_estimate"] is not None


def test_blocked_safety_when_live_mode_enabled() -> None:
    settings = Settings(live_trading_enabled=True)

    record = build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(bid=100.0, ask=100.02, last=100.01),
        settings=settings,
        market_open=True,
    )

    assert record["decision"] == "blocked_safety"
    assert record["decision_reason"] == "live_trading_enabled"
    assert record["orders_allowed"] is False


def test_blocked_safety_for_runtime_kill_switch_and_live_ibkr_port() -> None:
    runtime_block = build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(bid=100.0, ask=100.02, last=100.01),
        runtime_kill_switch_active=True,
        market_open=True,
    )
    live_port_block = build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(bid=100.0, ask=100.02, last=100.01),
        settings={"ibkr_port": 7496},
        market_open=True,
    )

    assert runtime_block["decision"] == "blocked_safety"
    assert runtime_block["decision_reason"] == "runtime_kill_switch_enabled"
    assert live_port_block["decision"] == "blocked_safety"
    assert live_port_block["decision_reason"] == "ibkr_live_port"


def test_recorder_does_not_import_broker_or_paper_paths() -> None:
    _forget_broker_modules()

    build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(bid=100.0, ask=100.02, last=100.01),
        market_open=True,
    )

    assert "tradeo.services.ibkr_broker" not in sys.modules
    assert "tradeo.services.paper_broker" not in sys.modules


def test_secret_redaction() -> None:
    record = redact_shadow_record(
        {
            "symbol": "AAPL",
            "api_key": "secret-value",
            "nested": {"account": "DU123", "quote_source": "safe"},
        }
    )

    assert record["api_key"] == "<redacted>"
    assert record["nested"]["account"] == "<redacted>"
    assert record["nested"]["quote_source"] == "safe"

    quote_record = build_vwap_shadow_record(
        symbol="AAPL",
        side="long",
        vwap_condition="vwap_reclaim_long",
        timeframe="1m",
        quote=ShadowQuote(bid=100.0, ask=100.02, last=100.01, source="secret-token-source"),
        market_open=True,
    )

    assert quote_record["quote_source"] == "<redacted>"
    assert "secret-token-source" not in repr(quote_record)
