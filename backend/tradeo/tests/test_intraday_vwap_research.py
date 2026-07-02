from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from tradeo.research.intraday_vwap_research import analyze_intraday_vwap_research, render_markdown


def test_analyzer_produces_summary_ok_with_synthetic_cache(tmp_path: Path) -> None:
    cache_dir, universe = _fixture_cache(tmp_path)

    summary = analyze_intraday_vwap_research(
        ohlcv_cache_dir=cache_dir,
        universe_file=universe,
        limit=2,
        period="60d",
        timeframe="30m",
    )

    assert summary["status"] == "OK"
    assert summary["universe"]["symbols_requested"] == 2
    assert summary["universe"]["symbols_analyzed"] == 2
    assert summary["vwap_summary"]["bars_analyzed"] > 0
    assert summary["safety"]["orders_allowed"] is False


def test_analyzer_returns_not_available_when_cache_missing(tmp_path: Path) -> None:
    universe = _write_universe(tmp_path, ["AAA"])

    summary = analyze_intraday_vwap_research(
        ohlcv_cache_dir=tmp_path / "missing_cache",
        universe_file=universe,
        limit=1,
        period="60d",
        timeframe="30m",
    )

    assert summary["status"] == "NOT_AVAILABLE"
    assert summary["vwap_summary"]["bars_analyzed"] == 0
    assert summary["symbol_stats"] == []


def test_symbol_stats_calculates_above_below_crosses_and_chop(tmp_path: Path) -> None:
    cache_dir, universe = _fixture_cache(tmp_path, symbols=("AAA",))

    summary = analyze_intraday_vwap_research(
        ohlcv_cache_dir=cache_dir,
        universe_file=universe,
        limit=1,
        period="60d",
        timeframe="30m",
    )

    stats = summary["symbol_stats"][0]
    assert stats["above_vwap_pct"] > 0
    assert stats["below_vwap_pct"] > 0
    assert stats["crosses_count"] >= 2
    assert stats["chop_rate"] > 0
    assert stats["trend_bias"] in {"above_rising", "below_falling", "mixed", "chop", "unknown"}


def test_recommended_next_waves_include_vwap_aware_waves(tmp_path: Path) -> None:
    cache_dir, universe = _fixture_cache(tmp_path)

    summary = analyze_intraday_vwap_research(
        ohlcv_cache_dir=cache_dir,
        universe_file=universe,
        limit=2,
        period="60d",
        timeframe="30m",
    )

    names = {row["name"] for row in summary["recommended_next_waves"]}
    assert "30m_W100_vwap_reclaim_slow" in names
    assert "30m_W100_vwap_reject_slow" in names
    assert "15m_W50_vwap_pullback_fast" in names
    assert "1h_W100_vwap_regime_filter" in names


def test_prohibited_repeats_filter_candidate_and_block_reason(tmp_path: Path) -> None:
    cache_dir, universe = _fixture_cache(tmp_path)
    forensics = tmp_path / "forensics.json"
    forensics.write_text(json.dumps({"prohibited_repeats": ["30m W100 8,13,21"]}), encoding="utf-8")

    summary = analyze_intraday_vwap_research(
        ohlcv_cache_dir=cache_dir,
        universe_file=universe,
        limit=2,
        period="60d",
        timeframe="30m",
        forensics_json=forensics,
    )

    assert all(row["signature"] != "30m W100 8,13,21" for row in summary["recommended_next_waves"])
    assert any(row["reason"] == "prohibited_repeat" for row in summary["blocked_waves"])


def test_safety_flags_false_and_markdown_mentions_no_orders(tmp_path: Path) -> None:
    cache_dir, universe = _fixture_cache(tmp_path)

    summary = analyze_intraday_vwap_research(
        ohlcv_cache_dir=cache_dir,
        universe_file=universe,
        limit=2,
        period="60d",
        timeframe="30m",
    )
    markdown = render_markdown(summary)

    assert set(summary["safety"].values()) == {False}
    assert "## Safety" in markdown
    assert "No orders." in markdown
    assert "No wave executed." in markdown


def _fixture_cache(tmp_path: Path, symbols: tuple[str, ...] = ("AAA", "BBB")) -> tuple[Path, Path]:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    universe = _write_universe(tmp_path, list(symbols))
    for offset, symbol in enumerate(symbols):
        _write_cache(cache_dir / f"{symbol}_30m_60d.csv", offset=offset)
    return cache_dir, universe


def _write_universe(tmp_path: Path, symbols: list[str]) -> Path:
    universe = tmp_path / "universe.csv"
    with universe.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["symbol", "selected", "status"])
        writer.writeheader()
        for symbol in symbols:
            writer.writerow({"symbol": symbol, "selected": "True", "status": "selected"})
    return universe


def _write_cache(path: Path, *, offset: int) -> None:
    index = pd.date_range("2026-07-01 09:30", periods=8, freq="30min", tz="America/New_York")
    closes = [10, 9, 11, 12, 8, 7.8, 10.5, 11.2]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        for timestamp, close in zip(index, closes, strict=True):
            shifted = close + offset
            writer.writerow(
                {
                    "timestamp": timestamp.isoformat(),
                    "open": shifted,
                    "high": shifted + 0.2,
                    "low": shifted - 0.2,
                    "close": shifted,
                    "volume": 1000,
                }
            )
