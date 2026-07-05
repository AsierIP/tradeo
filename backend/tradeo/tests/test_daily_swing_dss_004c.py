from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from tradeo.modules.daily_swing.dss_004c import AutopsyConfig, run_dss_004c_autopsy


def _bars(symbol: str, days: int = 430, fake_holiday: bool = False) -> pd.DataFrame:
    rows = []
    cursor = date(2024, 1, 2)
    price = 100.0
    while len(rows) < days:
        if cursor.weekday() < 5 and cursor.isoformat() != "2026-07-03":
            step = len(rows)
            if step > 260 and step % 28 == 0:
                price *= 1.08
            elif step > 250 and step % 28 in {25, 26, 27}:
                price *= 0.996
            else:
                price *= 1.0017
            rows.append(
                {
                    "symbol": symbol,
                    "date": cursor.isoformat(),
                    "open": price * 0.999,
                    "high": price * 1.004,
                    "low": price * 0.996,
                    "close": price,
                    "volume": 1_000_000,
                }
            )
        cursor += timedelta(days=1)
    if fake_holiday:
        rows.append({"symbol": symbol, "date": "2026-07-03", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1})
    return pd.DataFrame(rows)


def _write_fixture(tmp_path, fake_holiday: bool = False) -> tuple:
    cache = tmp_path / "cache"
    cache.mkdir()
    for symbol in ("AAPL", "MSFT", "SPY", "QQQ"):
        _bars(symbol, fake_holiday=fake_holiday and symbol == "AAPL").to_csv(cache / f"{symbol}.csv", index=False)
    universe = tmp_path / "universe.csv"
    universe.write_text(
        "symbol,benchmark_only,operational_eligible,product_type\n"
        "AAPL,false,true,STK\n"
        "MSFT,false,true,STK\n"
        "SPY,true,false,STK\n"
        "QQQ,true,false,STK\n",
        encoding="utf-8",
    )
    return cache, universe, tmp_path / "out"


def _config(cache, universe, out) -> AutopsyConfig:
    return AutopsyConfig(
        cache_dir=cache,
        universe_path=universe,
        start_date="2024-01-02",
        end_date="2026-07-02",
        is_end_date="2024-12-31",
        oos_start_date="2025-01-01",
        output_dir=out,
    )


def test_dss_004c_placebo_oos_separated_from_full_sample(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    run_dss_004c_autopsy(_config(cache, universe, out))
    placebo = pd.read_csv(out / "dss_004c_placebo_oos.csv")
    assert {"trades_total", "trades_OOS", "expectancy_net_x2_OOS_pct"} <= set(placebo.columns)
    assert (placebo["trades_total"] >= placebo["trades_OOS"]).all()


def test_dss_004c_baselines_do_not_use_future_data(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    run_dss_004c_autopsy(_config(cache, universe, out))
    baselines = pd.read_csv(out / "dss_004c_matched_baselines.csv")
    assert {"DSS_BO_001_BASE", "TREND_ONLY", "BREAKOUT_ONLY", "CONTRACTION_ONLY", "RANDOM_MATCHED"} <= set(baselines["variant"])


def test_dss_004c_random_matched_reproducible_seed(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    first = run_dss_004c_autopsy(_config(cache, universe, out))["baselines"]["table"]
    second = run_dss_004c_autopsy(_config(cache, universe, out))["baselines"]["table"]
    pd.testing.assert_frame_equal(first, second)


def test_dss_004c_return_decomposition_sums_to_trade_return(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    run_dss_004c_autopsy(_config(cache, universe, out))
    decomposition = pd.read_csv(out / "dss_004c_return_decomposition.csv")
    assert "signal_close_to_next_open_pct" in decomposition
    assert "mae_pct" in decomposition
    assert "mfe_pct" in decomposition


def test_dss_004c_excludes_spy_qqq_from_trades(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_004c_autopsy(_config(cache, universe, out))
    assert not set(result["base_trades"]["symbol"]) & {"SPY", "QQQ"}


def test_dss_004c_rejects_fake_2026_07_03_bar(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path, fake_holiday=True)
    with pytest.raises(ValueError, match="2026-07-03"):
        run_dss_004c_autopsy(_config(cache, universe, out))


def test_dss_004c_stability_ex_top_symbols_present(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_004c_autopsy(_config(cache, universe, out))
    stability = result["stability"]["summary"]
    assert "exclude_top_1_symbol" in stability
    assert "exclude_top_3_symbols" in stability
    assert "exclude_top_5_trades" in stability


def test_dss_004c_decision_requires_all_partial_decisions(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_004c_autopsy(_config(cache, universe, out))
    partial = result["decision"]["partial_decisions"]
    assert {"placebo", "baseline", "timing", "stability"} == set(partial)
    assert result["decision"]["decision"].startswith("DSS_BO_001_")
