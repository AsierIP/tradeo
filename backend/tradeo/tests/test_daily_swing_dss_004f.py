from __future__ import annotations

import pandas as pd
import pytest

from tradeo.modules.daily_swing.dss_004d import _ensure_indicators, _signal_rows
from tradeo.modules.daily_swing.dss_004f import DSS004FConfig, build_episodes, offset_timing_audit, run_dss_004f
from tradeo.tests.test_daily_swing_dss_004d import _bars


def _fixture_004f(tmp_path, fake_holiday: bool = False):
    cache = tmp_path / "cache"
    cache.mkdir()
    for symbol in ("AAPL", "MSFT", "NVDA", "SPY", "QQQ"):
        _bars(symbol, days=800, fake_holiday=fake_holiday and symbol == "AAPL").to_csv(cache / f"{symbol}.csv", index=False)
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
    return cache, universe, tmp_path / "out", tmp_path / "research"


def _config(cache, universe, out, research) -> DSS004FConfig:
    return DSS004FConfig(
        cache_dir=cache,
        universe_path=universe,
        start_date="2023-07-05",
        end_date="2026-07-02",
        is_end_date="2024-12-31",
        oos_start_date="2025-01-01",
        output_dir=out,
        research_dir=research,
        bootstrap_iterations=2,
    )


def _signals(cache) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    frames = {
        symbol: _ensure_indicators(pd.read_csv(cache / f"{symbol}.csv"))
        for symbol in ("AAPL", "MSFT", "NVDA")
    }
    regime = pd.Series(True, index=pd.read_csv(cache / "SPY.csv")["date"].astype(str))
    return frames, _signal_rows(frames, regime)


def test_dss_004f_episode_builder_groups_contiguous_signals(tmp_path) -> None:
    cache, universe, out, research = _fixture_004f(tmp_path)
    frames, signals = _signals(cache)
    episodes, summary = build_episodes(signals, frames, _config(cache, universe, out, research))
    assert {"EPISODE_CONTIGUOUS", "EPISODE_GAP_3", "EPISODE_GAP_5"} <= set(episodes["episode_type"])
    assert summary["episodes_total"] < summary["raw_signals_total"]


def test_dss_004f_episode_offsets_do_not_use_future_data(tmp_path) -> None:
    cache, universe, out, research = _fixture_004f(tmp_path)
    frames, signals = _signals(cache)
    episodes, _ = build_episodes(signals, frames, _config(cache, universe, out, research))
    trades, _ = offset_timing_audit(episodes, frames, _config(cache, universe, out, research))
    assert (pd.to_datetime(trades["entry_date"]) > pd.to_datetime(trades["offset_signal_date"])).all()


def test_dss_004f_offset_audit_uses_same_episode_set(tmp_path) -> None:
    cache, universe, out, research = _fixture_004f(tmp_path)
    frames, signals = _signals(cache)
    episodes, _ = build_episodes(signals, frames, _config(cache, universe, out, research))
    _, summary = offset_timing_audit(episodes, frames, _config(cache, universe, out, research))
    counts = {metrics["episodes_OOS"] for metrics in summary["by_offset"].values()}
    assert len(counts) <= 2


def test_dss_004f_excludes_spy_qqq_from_episodes(tmp_path) -> None:
    cache, universe, out, research = _fixture_004f(tmp_path)
    result = run_dss_004f(_config(cache, universe, out, research))
    assert not (set(result["episodes"]["symbol"]) & {"SPY", "QQQ"})


def test_dss_004f_rejects_fake_2026_07_03_bar(tmp_path) -> None:
    cache, universe, out, research = _fixture_004f(tmp_path, fake_holiday=True)
    with pytest.raises(ValueError, match="2026-07-03"):
        run_dss_004f(_config(cache, universe, out, research))


def test_dss_004f_overlap_metrics_present(tmp_path) -> None:
    cache, universe, out, research = _fixture_004f(tmp_path)
    result = run_dss_004f(_config(cache, universe, out, research))
    assert "ALL_EVENTS" in result["overlap_summary"]["policy_summary"]
    assert "overlap_pct_by_symbol" in result["overlap_summary"]["policy_summary"]["ALL_EVENTS"]


def test_dss_004f_cluster_bootstrap_reproducible_seed(tmp_path) -> None:
    cache, universe, out, research = _fixture_004f(tmp_path)
    result = run_dss_004f(_config(cache, universe, out, research))
    assert result["overlap_summary"]["bootstrap_seed"] == 40406
    assert not result["bootstrap"].empty


def test_dss_004f_decision_requires_episode_and_overlap_results(tmp_path) -> None:
    cache, universe, out, research = _fixture_004f(tmp_path)
    result = run_dss_004f(_config(cache, universe, out, research))
    assert result["decision"]["episode_decision"]
    assert result["decision"]["overlap_effective_sample_decision"]
