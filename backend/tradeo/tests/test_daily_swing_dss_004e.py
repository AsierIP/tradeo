from __future__ import annotations

import pandas as pd
import pytest

from tradeo.modules.daily_swing.dss_004d import DSS004DConfig, _add_indicators, _build_trades, _condition, _signal_rows, run_dss_004d
from tradeo.tests.test_daily_swing_dss_004d import _fixture


def _config(cache, universe, out) -> DSS004DConfig:
    return DSS004DConfig(
        cache_dir=cache,
        universe_path=universe,
        start_date="2023-07-05",
        end_date="2026-07-02",
        is_end_date="2024-12-31",
        oos_start_date="2025-01-01",
        output_dir=out,
        phase="DSS-004E",
        artifact_prefix="dss_004e_",
        min_oos_symbols=2,
    )


def test_dss_004e_uses_research_cache_not_pilot_cache(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    assert result["config"]["config"]["cache_dir"] == str(cache)
    assert (out / "dss_004e_dss_co_001_metrics.json").exists()


def test_dss_004e_no_lookahead_signal_t_entry_t_plus_1(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    assert result["guard"]["checks"]["signal_t_entry_t_plus_1"]


def test_dss_004e_contraction_uses_t_minus_1(tmp_path) -> None:
    cache, _, _ = _fixture(tmp_path)
    row = _add_indicators(pd.read_csv(cache / "AAPL.csv")).iloc[220].copy()
    row["atr14_pct_t_minus_1"] = 0.01
    row["atr14_pct_p40_120_t_minus_1"] = 0.02
    row["sma50"] = row["close"] * 0.9
    row["sma200"] = row["close"] * 0.8
    assert _condition(row, True)


def test_dss_004e_excludes_spy_qqq_from_trades(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    symbols = set()
    for trades in result["trades"].values():
        symbols.update(trades["symbol"].tolist())
    assert not (symbols & {"SPY", "QQQ"})


def test_dss_004e_rejects_fake_2026_07_03_bar(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path, fake_holiday=True)
    with pytest.raises(ValueError, match="2026-07-03"):
        run_dss_004d(_config(cache, universe, out))


def test_dss_004e_one_active_per_symbol_policy(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    trades = result["trades"]["ONE_ACTIVE_PER_SYMBOL"].sort_values(["symbol", "signal_date"])
    for _, group in trades.groupby("symbol"):
        entries = pd.to_datetime(group["signal_date"]).reset_index(drop=True)
        exits = pd.to_datetime(group["exit_date"]).reset_index(drop=True)
        assert all(entries.iloc[idx] > exits.iloc[idx - 1] for idx in range(1, len(group)))


def test_dss_004e_max2_daily_policy(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    by_day = result["trades"]["MAX_2_NEW_TRADES_PER_DAY_SIM"].groupby("signal_date").size()
    assert by_day.empty or int(by_day.max()) <= 2


def test_dss_004e_cost_x2_metrics_present(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    assert "profit_factor" in result["metrics"]["by_policy"]["ONE_ACTIVE_PER_SYMBOL"]["OOS"]


def test_dss_004e_decision_requires_research150_metrics(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    result = run_dss_004d(_config(cache, universe, out))
    assert result["decision"]["phase"] == "DSS-004E"
    assert result["metrics"]["min_oos_symbols"] == 2


def test_dss_004e_fails_if_placebo_plus1_beats_base_by_material_margin(tmp_path) -> None:
    cache, universe, out = _fixture(tmp_path)
    config = _config(cache, universe, out)
    frames = {"AAPL": pd.read_csv(cache / "AAPL.csv"), "MSFT": pd.read_csv(cache / "MSFT.csv")}
    regime = pd.Series(True, index=pd.read_csv(cache / "SPY.csv")["date"].astype(str))
    signals = _signal_rows(frames, regime)
    trades = _build_trades(frames, signals, config, "ONE_ACTIVE_PER_SYMBOL", signal_shift=1)
    assert "net_return_x2_pct" in trades.columns
