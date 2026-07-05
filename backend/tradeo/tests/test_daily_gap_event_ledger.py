from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tradeo.modules.daily_swing.gap_event_ledger import (
    CacheMissingError,
    GapLedgerConfig,
    audit_no_lookahead,
    build_gap_event_ledger,
    summarize_ledger,
    validate_cache_and_universe,
)


def test_gap_ledger_requires_cache_only(tmp_path: Path) -> None:
    config = _config(tmp_path, cache_only=False)
    with pytest.raises(ValueError, match="cache-only"):
        validate_cache_and_universe(config)


def test_gap_ledger_blocks_ibkr(tmp_path: Path) -> None:
    config = _config(tmp_path, no_ibkr=False)
    with pytest.raises(ValueError, match="IBKR"):
        validate_cache_and_universe(config)


def test_gap_ledger_blocks_orders_preview_signals(tmp_path: Path) -> None:
    config = _config(tmp_path, block_orders_preview_signals=False)
    with pytest.raises(ValueError, match="orders"):
        validate_cache_and_universe(config)


def test_gap_ledger_blocks_missing_cache(tmp_path: Path) -> None:
    config = _config(tmp_path)
    with pytest.raises(CacheMissingError):
        validate_cache_and_universe(config)


def test_gap_ledger_prev_close_uses_previous_trading_date(tmp_path: Path) -> None:
    ledger = _build_fixture_ledger(tmp_path)
    aapl = ledger[(ledger["symbol"] == "AAPL") & (ledger["date"] == "2026-01-08")].iloc[0]
    previous = ledger[(ledger["symbol"] == "AAPL") & (ledger["date"] == "2026-01-07")].iloc[0]
    assert aapl["previous_trading_date"] == "2026-01-07"
    assert aapl["prev_close"] == previous["close"]


def test_gap_ledger_gap_pct_uses_open_and_prev_close(tmp_path: Path) -> None:
    ledger = _build_fixture_ledger(tmp_path)
    row = ledger[(ledger["symbol"] == "AAPL") & (ledger["date"] == "2026-01-30")].iloc[0]
    assert row["gap_pct"] == pytest.approx(row["open"] / row["prev_close"] - 1)


def test_gap_ledger_atr_prev_uses_t_minus_1(tmp_path: Path) -> None:
    ledger = _build_fixture_ledger(tmp_path)
    row = ledger[(ledger["symbol"] == "AAPL") & (ledger["date"] == "2026-01-30")].iloc[0]
    assert pd.notna(row["atr14_pct_prev"])
    shifted_open = row["open"] * 100
    assert row["atr14_pct_prev"] < shifted_open


def test_gap_ledger_same_day_outcomes_marked_outcome_only(tmp_path: Path) -> None:
    ledger = _build_fixture_ledger(tmp_path)
    row = ledger[(ledger["symbol"] == "AAPL") & (ledger["date"] == "2026-01-30")].iloc[0]
    assert "open_to_close_return" in row["outcome_only_fields"]
    assert "gap_fill_ratio" in row["outcome_only_fields"]
    assert "close" not in row["known_at_open_fields"].split("|")
    assert audit_no_lookahead()["status"] == "NO_LOOKAHEAD_PASS"


def test_gap_ledger_excludes_spy_qqq_from_operational_events(tmp_path: Path) -> None:
    ledger = _build_fixture_ledger(tmp_path)
    spy = ledger[ledger["symbol"] == "SPY"].iloc[-1]
    assert spy["is_benchmark"] is True or spy["is_benchmark"] == True  # noqa: E712
    assert spy["is_stock_operational"] is False or spy["is_stock_operational"] == False  # noqa: E712
    assert spy["event_quality_status"] == "GAP_EVENT_BENCHMARK_ONLY"


def test_gap_ledger_rejects_fake_2026_07_03_bar(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    bad = pd.DataFrame(
        [
            {"date": "2026-07-02", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1_000_000},
            {"date": "2026-07-03", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1_000_000},
        ]
    )
    bad.to_csv(tmp_path / "cache" / "AAPL.csv", index=False)
    with pytest.raises(Exception, match="2026-07-03"):
        build_gap_event_ledger(_config(tmp_path))


def test_gap_ledger_distribution_has_no_best_threshold(tmp_path: Path) -> None:
    ledger = _build_fixture_ledger(tmp_path)
    summary = summarize_ledger(ledger)
    assert summary["distribution_has_best_threshold"] is False
    assert not any("best" in key.lower() for key in summary["threshold_counts"])


def _config(
    tmp_path: Path,
    *,
    cache_only: bool = True,
    no_ibkr: bool = True,
    block_orders_preview_signals: bool = True,
) -> GapLedgerConfig:
    return GapLedgerConfig(
        cache_dir=tmp_path / "cache",
        universe_path=tmp_path / "universe.csv",
        output_dir=tmp_path / "out",
        min_history_days=20,
        cache_only=cache_only,
        no_ibkr=no_ibkr,
        block_orders_preview_signals=block_orders_preview_signals,
        generated_at="2026-07-05T14:03:00Z",
    )


def _build_fixture_ledger(tmp_path: Path) -> pd.DataFrame:
    _write_fixture(tmp_path)
    result = build_gap_event_ledger(_config(tmp_path))
    return pd.read_csv(result.ledger_path)


def _write_fixture(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    universe = pd.DataFrame(
        [
            {"symbol": "AAPL", "product_class": "STK", "selected": True},
            {"symbol": "MSFT", "product_class": "STK", "selected": True},
            {"symbol": "SPY", "product_class": "STK", "selected": True},
            {"symbol": "QQQ", "product_class": "STK", "selected": True},
        ]
    )
    universe.to_csv(tmp_path / "universe.csv", index=False)
    for symbol, base in [("AAPL", 100.0), ("MSFT", 200.0), ("SPY", 400.0), ("QQQ", 300.0)]:
        _bars(base).to_csv(cache / f"{symbol}.csv", index=False)


def _bars(base: float) -> pd.DataFrame:
    dates = pd.bdate_range("2026-01-01", periods=35)
    rows = []
    close = base
    for i, date in enumerate(dates):
        open_ = close * (1.02 if i in {22, 29} else 1.001)
        high = max(open_, close * 1.004) * 1.01
        low = min(open_, close * 0.996) * 0.99
        close = open_ * (1.003 if i % 2 else 0.998)
        rows.append(
            {
                "date": date.date().isoformat(),
                "open": round(open_, 4),
                "high": round(high, 4),
                "low": round(low, 4),
                "close": round(close, 4),
                "volume": 1_000_000 + i,
            }
        )
    return pd.DataFrame(rows)
