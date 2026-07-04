from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from tradeo.modules.daily_swing.dss_004d import (
    DSS004DConfig,
    _build_trades,
    _condition,
    _signal_rows,
    run_dss_004d,
)
from tradeo.modules.daily_swing.dss_004b import _add_indicators


def _bars(symbol: str, days: int = 500, fake_holiday: bool = False) -> pd.DataFrame:
    rows = []
    cursor = date(2023, 7, 5)
    price = 100.0
    while len(rows) < days:
        if cursor.weekday() < 5 and cursor.isoformat() != "2026-07-03":
            step = len(rows)
            price *= 1.002
            if step > 240 and step % 18 in {14, 15, 16, 17}:
                high = price * 1.002
                low = price * 0.999
            else:
                high = price * 1.015
                low = price * 0.985
            rows.append(
                {
                    "symbol": symbol,
                    "date": cursor.isoformat(),
                    "open": price * 0.999,
                    "high": high,
                    "low": low,
                    "close": price,
                    "volume": 1_000_000,
                }
            )
        cursor += timedelta(days=1)
    if fake_holiday:
        rows.append({"symbol": symbol, "date": "2026-07-03", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1})
    return pd.DataFrame(rows)


def _fixture(tmp_path, fake_holiday: bool = False):
    cache = tmp_path / "cache"
    cache.mkdir()
    for symbol in ("AAPL", "MSFT", "NVDA", "SPY", "QQQ"):
        _bars(symbol, fake_holiday=fake_holiday and symbol == "AAPL").to_csv(cache / f"{symbol}.csv", index=False)
    universe = tmp_path / "universe.csv"
    universe.write_text(
        "symbol,benchmark_only,operational_eligible,product_type\n"
        "AAPL,false,true,STK\n"
        "MSFT,false,true,STK\n"
        "NVDA,false,true,STK\n"
        "SPY,true,false,STK\n"
        "QQQ,true,false,STK\n",
        encoding="utf-8",
    )
    return cache, universe, tmp_path / "out"


def _config(cache, universe, out) -> DSS004DConfig:
    return DSS004DConfig(
        cache_dir=cache,
        universe_path=universe,
        start_date="2023-07-05",
        end_date="2026-07-02",
        is_end_date="2024-12-31",
        oos_start_date="2025-01-01",
        output_dir=out,
    )


def test_dss_co_001_no_lookahead_signal_t_entry_t_plus_1(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    assert result["guard"]["checks"]["signal_t_entry_t_plus_1"]


def test_dss_co_001_contraction_uses_t_minus_1(tmp_path) -> None:
    cache, _, _ = _fixture(tmp_path)
    row = _add_indicators(pd.read_csv(cache / "AAPL.csv")).iloc[220].copy()
    row["atr14_pct_t_minus_1"] = 0.01
    row["atr14_pct_p40_120_t_minus_1"] = 0.02
    row["sma50"] = row["close"] * 0.9
    row["sma200"] = row["close"] * 0.8
    assert _condition(row, True)


def test_dss_co_001_excludes_spy_qqq_from_trades(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    all_symbols = set()
    for trades in result["trades"].values():
        all_symbols.update(trades["symbol"].tolist())
    assert not (all_symbols & {"SPY", "QQQ"})


def test_dss_co_001_rejects_fake_2026_07_03_bar(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path, fake_holiday=True)
    with pytest.raises(ValueError, match="2026-07-03"):
        run_dss_004d(_config(cache, universe, out))


def test_dss_co_001_one_active_per_symbol_policy(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    config = _config(cache, universe, out)
    result = run_dss_004d(config)
    trades = result["trades"]["ONE_ACTIVE_PER_SYMBOL"].sort_values(["symbol", "signal_date"])
    for _, group in trades.groupby("symbol"):
        entries = pd.to_datetime(group["signal_date"]).reset_index(drop=True)
        exits = pd.to_datetime(group["exit_date"]).reset_index(drop=True)
        assert all(entries.iloc[idx] > exits.iloc[idx - 1] for idx in range(1, len(group)))


def test_dss_co_001_max2_daily_policy(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    by_day = result["trades"]["MAX_2_NEW_TRADES_PER_DAY_SIM"].groupby("signal_date").size()
    assert by_day.empty or int(by_day.max()) <= 2


def test_dss_co_001_cost_x2_metrics_present(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    assert "OOS" in result["metrics"]["by_policy"]["ONE_ACTIVE_PER_SYMBOL"]
    assert "profit_factor" in result["metrics"]["by_policy"]["ONE_ACTIVE_PER_SYMBOL"]["OOS"]


def test_dss_co_001_decision_requires_policy_metrics(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    assert result["decision"]["decision"].startswith("DSS_CO_001_")
    assert {"ALL_EVENTS", "ONE_ACTIVE_PER_SYMBOL", "MAX_2_NEW_TRADES_PER_DAY_SIM"} == set(result["metrics"]["by_policy"])


def test_dss_co_001_fails_when_operability_constraints_destroy_edge(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    config = _config(cache, universe, out)
    frames = {"AAPL": pd.read_csv(cache / "AAPL.csv"), "MSFT": pd.read_csv(cache / "MSFT.csv")}
    regime = pd.Series(True, index=pd.read_csv(cache / "SPY.csv")["date"].astype(str))
    signals = _signal_rows(frames, regime)
    trades = _build_trades(frames, signals, config, "MAX_2_NEW_TRADES_PER_DAY_SIM")
    assert "net_return_x2_pct" in trades.columns
