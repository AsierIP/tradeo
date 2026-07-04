from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from tradeo.modules.daily_swing.dss_004c_r import (
    RANDOM_MATCHED_SEED,
    ReconciliationConfig,
    _condition,
    method_diff,
    run_dss_004c_r_reconciliation,
    side_by_side_recompute,
)
from tradeo.modules.daily_swing.dss_004b import _add_indicators, generate_trades


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


def _config(cache, universe, out, repo_root) -> ReconciliationConfig:
    return ReconciliationConfig(
        cache_dir=cache,
        universe_path=universe,
        start_date="2024-01-02",
        end_date="2026-07-02",
        is_end_date="2024-12-31",
        oos_start_date="2025-01-01",
        output_dir=out,
        repo_root=repo_root,
    )


def test_dss_004c_r_side_by_side_has_unmatched_and_matched_modes(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_004c_r_reconciliation(_config(cache, universe, out, tmp_path))
    table = pd.read_csv(out / "dss_004c_r_side_by_side_baselines.csv")
    assert set(table["mode"]) == {"UNMATCHED_ALL_EVENTS", "MATCHED_SAMPLE"}
    assert {"DSS_BO_001_BASE", "TREND_ONLY", "BREAKOUT_ONLY", "CONTRACTION_ONLY", "RANDOM_MATCHED"} <= set(table["variant"])
    assert result["side_by_side"]["summary"]["matching"].startswith("Exact symbol-year")


def test_dss_004c_r_contraction_uses_t_minus_1(tmp_path) -> None:
    cache, _, _, = _write_fixture(tmp_path)
    row = _add_indicators(pd.read_csv(cache / "AAPL.csv")).iloc[220].copy()
    row["atr14_pct_t_minus_1"] = 0.01
    row["atr14_pct_p40_120_t_minus_1"] = 0.02
    row["prior_high20"] = row["close"] * 2
    row["sma50"] = row["close"] * 0.9
    row["sma200"] = row["close"] * 0.8
    assert _condition(row, True, "CONTRACTION_ONLY")


def test_dss_004c_r_breakout_uses_prior_high20(tmp_path) -> None:
    cache, _, _, = _write_fixture(tmp_path)
    row = _add_indicators(pd.read_csv(cache / "AAPL.csv")).iloc[220].copy()
    row["prior_high20"] = row["close"] * 0.99
    row["atr14_pct_t_minus_1"] = 0.01
    row["atr14_pct_p40_120_t_minus_1"] = 0.02
    row["sma50"] = row["close"] * 0.9
    row["sma200"] = row["close"] * 0.8
    assert _condition(row, True, "BREAKOUT_ONLY")


def test_dss_004c_r_excludes_spy_qqq_from_trades(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_004c_r_reconciliation(_config(cache, universe, out, tmp_path))
    assert not set(result["base_trades"]["symbol"]) & {"SPY", "QQQ"}
    assert result["guards"]["checks"]["excludes_spy_qqq_from_trades"]


def test_dss_004c_r_rejects_fake_2026_07_03_bar(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path, fake_holiday=True)
    with pytest.raises(ValueError, match="2026-07-03"):
        run_dss_004c_r_reconciliation(_config(cache, universe, out, tmp_path))


def test_dss_004c_r_random_matched_seed_reproducible(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    first = run_dss_004c_r_reconciliation(_config(cache, universe, out, tmp_path))
    frames = {symbol: pd.read_csv(cache / f"{symbol}.csv") for symbol in ("AAPL", "MSFT")}
    regime = pd.Series(True, index=pd.read_csv(cache / "SPY.csv")["date"].astype(str))
    base_trades = generate_trades(frames, regime, _config(cache, universe, out, tmp_path).backtest_config())
    second, summary = side_by_side_recompute(frames, regime, _config(cache, universe, out, tmp_path), base_trades)
    first_random = first["side_by_side"]["table"].query("variant == 'RANDOM_MATCHED'").reset_index(drop=True)
    second_random = second.query("variant == 'RANDOM_MATCHED'").reset_index(drop=True)
    pd.testing.assert_frame_equal(first_random, second_random)
    assert summary["random_seed"] == RANDOM_MATCHED_SEED


def test_dss_004c_r_decision_requires_method_diff_and_guard_audit(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_004c_r_reconciliation(_config(cache, universe, out, tmp_path))
    assert result["method_diff"]["probable_cause"] == method_diff()["probable_cause"]
    assert result["guards"]["status"] == "PASS"
    assert result["decision"]["decision"] in {
        "DSS_BO_001_BASELINE_EXPLAINED_CONFIRMED",
        "DSS_004C_METHOD_BUG",
        "DSS_BO_001_TIMING_WINDOW_WARNING_CONFIRMED",
    }
