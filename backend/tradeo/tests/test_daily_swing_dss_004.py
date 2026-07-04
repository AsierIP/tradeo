from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from tradeo.modules.daily_swing.dss_004 import BacktestConfig, run_dss_pb_001_backtest


def _bars(symbol: str, days: int = 260, fake_holiday: bool = False) -> pd.DataFrame:
    rows = []
    cursor = date(2025, 1, 2)
    price = 100.0
    while len(rows) < days:
        if cursor.weekday() < 5 and cursor.isoformat() != "2026-07-03":
            if len(rows) % 20 in {16, 17, 18}:
                price *= 0.985
            else:
                price *= 1.004
            rows.append(
                {
                    "symbol": symbol,
                    "date": cursor.isoformat(),
                    "open": price * 0.998,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "close": price,
                    "volume": 1_000_000,
                }
            )
        cursor += timedelta(days=1)
    if fake_holiday:
        rows.append(
            {
                "symbol": symbol,
                "date": "2026-07-03",
                "open": 1,
                "high": 1,
                "low": 1,
                "close": 1,
                "volume": 1,
            }
        )
    return pd.DataFrame(rows)


def _write_fixture(tmp_path, universe_text: str | None = None, fake_holiday: bool = False) -> tuple:
    cache = tmp_path / "cache"
    cache.mkdir()
    for symbol in ("AAPL", "MSFT", "SPY", "QQQ"):
        _bars(symbol, fake_holiday=fake_holiday and symbol == "AAPL").to_csv(
            cache / f"{symbol}.csv", index=False
        )
    universe = tmp_path / "universe.csv"
    universe.write_text(
        universe_text
        or (
            "symbol,benchmark_only,operational_eligible,product_type\n"
            "AAPL,false,true,STK\n"
            "MSFT,false,true,STK\n"
            "SPY,true,false,STK\n"
            "QQQ,true,false,STK\n"
        ),
        encoding="utf-8",
    )
    return cache, universe, tmp_path / "out"


def _config(cache, universe, out) -> BacktestConfig:
    return BacktestConfig(
        cache_dir=cache,
        universe_path=universe,
        start_date="2025-01-02",
        end_date="2026-07-02",
        is_end_date="2025-12-31",
        oos_start_date="2026-01-01",
        output_dir=out,
    )


def test_dss_pb_001_generates_non_dummy_trades_from_cache(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_pb_001_backtest(_config(cache, universe, out))
    trades = pd.read_csv(out / "dss_pb_001_trades.csv")
    assert result["metrics"]["trades_total"] > 0
    assert set(trades["symbol"]) <= {"AAPL", "MSFT"}
    assert trades["trade_id"].str.startswith("DSS-PB-001-").all()


def test_dss_pb_001_no_lookahead_signal_t_entry_t_plus_1(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    run_dss_pb_001_backtest(_config(cache, universe, out))
    trades = pd.read_csv(out / "dss_pb_001_trades.csv")
    assert (pd.to_datetime(trades["entry_date"]) > pd.to_datetime(trades["signal_date"])).all()


def test_dss_pb_001_rejects_fake_2026_07_03_bar(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path, fake_holiday=True)
    with pytest.raises(ValueError, match="2026-07-03"):
        run_dss_pb_001_backtest(_config(cache, universe, out))


def test_dss_pb_001_excludes_spy_qqq_from_operational_trades(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    run_dss_pb_001_backtest(_config(cache, universe, out))
    trades = pd.read_csv(out / "dss_pb_001_trades.csv")
    assert not set(trades["symbol"]) & {"SPY", "QQQ"}


def test_dss_pb_001_blocks_etf_operational_symbol(tmp_path) -> None:
    cache, universe, out = _write_fixture(
        tmp_path,
        "symbol,benchmark_only,operational_eligible,product_type\n"
        "AAPL,false,true,ETF\n"
        "SPY,true,false,STK\n"
        "QQQ,true,false,STK\n",
    )
    with pytest.raises(ValueError, match="non-stock operational"):
        run_dss_pb_001_backtest(_config(cache, universe, out))


def test_dss_pb_001_cost_x2_metrics_present(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_pb_001_backtest(_config(cache, universe, out))
    assert "cost_x2" in result["metrics"]
    assert "profit_factor" in result["metrics"]["cost_x2"]


def test_dss_pb_001_oos_split_temporal(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_pb_001_backtest(_config(cache, universe, out))
    assert result["metrics"]["oos_start_date"] == "2026-01-01"
    assert result["metrics"]["trades_IS"] + result["metrics"]["trades_OOS"] <= result["metrics"]["trades_total"]


def test_dss_pb_001_concentration_metrics_present(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_pb_001_backtest(_config(cache, universe, out))
    assert "top_3_symbols_contribution_pct" in result["metrics"]["concentration"]


def test_dss_pb_001_decision_fails_when_no_trades(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    for path in cache.glob("*.csv"):
        df = pd.read_csv(path)
        df["close"] = 100.0
        df["open"] = 100.0
        df["high"] = 101.0
        df["low"] = 99.0
        df.to_csv(path, index=False)
    result = run_dss_pb_001_backtest(_config(cache, universe, out))
    assert result["decision"]["decision"] == "DSS_PB_001_INSUFFICIENT_TRADES"
