from __future__ import annotations

from datetime import date

from tradeo.modules.daily_swing import (
    DEFAULT_CONFIG,
    DailySwingConfig,
    MarketBar,
    build_order,
    check_daily_swing_operability,
    classify_paper_probe_candidate,
    generate_daily_swing_preview,
    last_valid_trading_day,
    preview_spec_hash,
)
from tradeo.modules.daily_swing.paper_probe import select_pullback_candidates


def test_daily_no_lookahead_signal_uses_only_previous_valid_bar() -> None:
    config = DailySwingConfig(signal_date="2026-07-02", run_date="2026-07-06")
    good = MarketBar("AAPL", date(2026, 7, 2), 212.4, 205.1, 184.2, 4.8, 12.0, 54_000_000, 1_000_000_000)
    future = MarketBar("MSFT", date(2026, 7, 6), 498.1, 486.0, 430.4, 8.7, 18.0, 23_000_000, 1_000_000_000)
    selected = select_pullback_candidates([future, good], config=config)
    assert [item.symbol for item in selected] == ["AAPL"]
    assert selected[0].last_valid_bar_date == date(2026, 7, 2)


def test_daily_market_holiday_2026_07_03_no_fake_bar() -> None:
    assert last_valid_trading_day(date(2026, 7, 6)) == date(2026, 7, 2)


def test_daily_paper_blocks_live_account(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TRADEO_TRADING_MODE=paper\nTRADEO_IBKR_ACCOUNT=U123456\nTRADEO_KILL_SWITCH_ENABLED=true\nTRADEO_IBKR_READONLY=true\n",
        encoding="utf-8",
    )
    result = check_daily_swing_operability(repo=tmp_path, env_file=env_file)
    assert result["status"] == "BLOCKED"
    assert "IBKR account does not look like a paper account" in result["reasons"]


def test_daily_paper_blocks_live_armed_true(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "TRADEO_TRADING_MODE=paper\nTRADEO_LIVE_ARMED=true\nTRADEO_KILL_SWITCH_ENABLED=true\nTRADEO_IBKR_READONLY=true\n",
        encoding="utf-8",
    )
    result = check_daily_swing_operability(repo=tmp_path, env_file=env_file)
    assert result["status"] == "BLOCKED"
    assert "live_armed=true" in result["reasons"]


def test_daily_paper_blocks_non_stock_product() -> None:
    bar = MarketBar("SPY", date(2026, 7, 2), 625.0, 612.0, 560.0, 6.0, 12.0, 60_000_000, 1_000_000_000, "ETF")
    assert select_pullback_candidates([bar]) == []


def test_daily_position_size_caps() -> None:
    order = generate_daily_swing_preview(DEFAULT_CONFIG)[0]
    assert order.quantity * order.limit_price <= DEFAULT_CONFIG.max_position_value


def test_daily_order_preview_matches_execution_spec_hash() -> None:
    orders = generate_daily_swing_preview(DEFAULT_CONFIG)
    assert preview_spec_hash(orders, DEFAULT_CONFIG) == preview_spec_hash(orders, DEFAULT_CONFIG)


def test_daily_kill_switch_blocks_new_orders(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("TRADEO_TRADING_MODE=paper\nTRADEO_KILL_SWITCH_ENABLED=false\nTRADEO_IBKR_READONLY=true\n", encoding="utf-8")
    result = check_daily_swing_operability(repo=tmp_path, env_file=env_file)
    assert result["status"] == "BLOCKED"
    assert "kill-switch is not enabled" in result["reasons"]


def test_daily_time_stop_generation() -> None:
    order = generate_daily_swing_preview(DEFAULT_CONFIG)[0]
    assert order.time_stop_date == "2026-07-14"


def test_daily_bracket_order_payload_valid() -> None:
    candidate = select_pullback_candidates(
        [MarketBar("AAPL", date(2026, 7, 2), 212.4, 205.1, 184.2, 4.8, 12.0, 54_000_000, 1_000_000_000)]
    )[0]
    order = build_order(candidate)
    assert order.entry_order_type == "LMT"
    assert order.stop_price < order.limit_price < order.target_price
    assert len(order.spec_hash) == 64


def test_daily_classification_blocks_without_real_backtest() -> None:
    assert classify_paper_probe_candidate({"real_backtest": False, "oos_expectancy_net": 0.5}) == "research_gap"
