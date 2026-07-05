from __future__ import annotations

import pandas as pd
import pytest

from tradeo.modules.daily_swing.dss_004d import _ensure_indicators, _signal_rows
from tradeo.modules.daily_swing.dss_004g_b import DSS004GBConfig, build_cw_episodes, build_cw_trades, run_dss_004g_b
from tradeo.tests.test_daily_swing_dss_004d import _bars, _fixture


def _fixture_004g_b(tmp_path, fake_holiday: bool = False):
    cache, universe, out = _fixture(tmp_path, fake_holiday=fake_holiday)
    return cache, universe, out, tmp_path / "research"


def _config(cache, universe, out, research) -> DSS004GBConfig:
    end_date = str(pd.read_csv(cache / "SPY.csv")["date"].max())
    return DSS004GBConfig(
        cache_dir=cache,
        universe_path=universe,
        start_date="2023-07-05",
        end_date=end_date,
        is_end_date="2024-12-31",
        oos_start_date="2025-01-01",
        output_dir=out,
        research_dir=research,
        bootstrap_iterations=2,
        min_operational_ready=3,
    )


def _frames_and_signals(cache):
    frames = {
        symbol: _ensure_indicators(pd.read_csv(cache / f"{symbol}.csv"))
        for symbol in ("AAPL", "MSFT")
    }
    regime = pd.Series(True, index=pd.read_csv(cache / "SPY.csv")["date"].astype(str))
    signals = _signal_rows(frames, regime)
    return frames, signals


def test_dss_cw_001_uses_research_cache_not_pilot(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    result = run_dss_004g_b(_config(cache, universe, out, research))
    assert result["metrics"]["cache_dir"] == str(cache)
    assert (out / "dss_cw_001_metrics.json").exists()


def test_dss_cw_001_episode_gap5_by_signal_idx(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    frames, signals = _frames_and_signals(cache)
    episodes = build_cw_episodes(signals, frames, _config(cache, universe, out, research))
    assert not episodes.empty
    assert set(episodes["episode_type"]) == {"EPISODE_GAP_5"}
    assert (episodes["raw_signal_count"] >= 1).all()


def test_dss_cw_001_no_lookahead_entry_t_plus_1(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    result = run_dss_004g_b(_config(cache, universe, out, research))
    assert result["guard"]["checks"]["signal_t_decision_t_entry_t_plus_1"]


def test_dss_cw_001_window_does_not_pick_best_offset(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    frames, signals = _frames_and_signals(cache)
    episodes = build_cw_episodes(signals, frames, _config(cache, universe, out, research))
    trades, _ = build_cw_trades(episodes, frames, _config(cache, universe, out, research), "ALL_ELIGIBLE_EPISODES")
    assert set(trades["selected_decision_offset"].unique()) <= {0}


def test_dss_cw_001_excludes_spy_qqq_from_trades(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    result = run_dss_004g_b(_config(cache, universe, out, research))
    symbols = set()
    for trades in result["trades"].values():
        symbols.update(trades["symbol"].tolist())
    assert not (symbols & {"SPY", "QQQ"})


def test_dss_cw_001_rejects_fake_2026_07_03_bar(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path, fake_holiday=True)
    with pytest.raises(ValueError, match="2026-07-03"):
        run_dss_004g_b(_config(cache, universe, out, research))


def test_dss_cw_001_one_active_per_symbol_episode(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    result = run_dss_004g_b(_config(cache, universe, out, research))
    trades = result["trades"]["ONE_ACTIVE_PER_SYMBOL_EPISODE"].sort_values(["symbol", "selected_decision_date"])
    for _, group in trades.groupby("symbol"):
        entries = pd.to_datetime(group["selected_decision_date"]).reset_index(drop=True)
        exits = pd.to_datetime(group["exit_date"]).reset_index(drop=True)
        assert all(entries.iloc[idx] > exits.iloc[idx - 1] for idx in range(1, len(group)))


def test_dss_cw_001_max2_new_episodes_per_day(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    result = run_dss_004g_b(_config(cache, universe, out, research))
    by_day = result["trades"]["MAX_2_NEW_EPISODES_PER_DAY"].groupby("selected_decision_date").size()
    assert by_day.empty or int(by_day.max()) <= 2


def test_dss_cw_001_selected_offset_distribution_present(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    run_dss_004g_b(_config(cache, universe, out, research))
    assert (out / "dss_cw_001_selected_offset_distribution.csv").exists()


def test_dss_cw_001_decision_requires_bias_results(tmp_path) -> None:
    cache, universe, out, research = _fixture_004g_b(tmp_path)
    result = run_dss_004g_b(_config(cache, universe, out, research))
    assert result["decision"]["bias_decision"]


def test_dss_cw_001_fixture_has_enough_bars() -> None:
    assert len(_bars("AAPL", days=260)) == 260
