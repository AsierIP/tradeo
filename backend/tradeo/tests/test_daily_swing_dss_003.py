from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from tradeo.modules.daily_swing.dss_003 import (
    build_daily_universes,
    cache_daily_ohlcv,
    check_daily_ohlcv_quality,
    classify_symbol_quality,
)


def _valid_rows(symbol: str = "AAPL", days: int = 260) -> pd.DataFrame:
    start = date(2025, 6, 30)
    rows = []
    cursor = start
    while len(rows) < days - 1:
        if cursor.weekday() < 5 and cursor.isoformat() != "2026-07-03":
            rows.append(
                {
                    "symbol": symbol,
                    "date": cursor.isoformat(),
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "volume": 1_000_000,
                }
            )
        cursor += timedelta(days=1)
    rows.append(
        {
            "symbol": symbol,
            "date": "2026-07-02",
            "open": 100.0,
            "high": 102.0,
            "low": 99.0,
            "close": 101.0,
            "volume": 1_000_000,
        }
    )
    return pd.DataFrame(rows)


def test_daily_cache_manifest_schema(tmp_path, monkeypatch) -> None:
    universe = tmp_path / "universe.csv"
    universe.write_text(
        "symbol,benchmark_only\nAAPL,false\nSPY,true\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    result = cache_daily_ohlcv(
        universe_path=universe,
        out_dir=tmp_path / "daily_ohlcv",
        duration="3Y",
        end_date="2026-07-06",
        read_only=True,
        dry_run=True,
    )
    assert result.status == "DRY_RUN_OK"
    manifest = result.manifest_path.read_text(encoding="utf-8")
    assert '"schema_version": "tradeo.daily_swing.dss_003.v1"' in manifest
    assert '"dry_run": true' in manifest


def test_daily_quality_rejects_fake_2026_07_03_bar() -> None:
    df = _valid_rows()
    df.loc[len(df)] = {
        "symbol": "AAPL",
        "date": "2026-07-03",
        "open": 100,
        "high": 101,
        "low": 99,
        "close": 100,
        "volume": 1,
    }
    status, reason = classify_symbol_quality(df, expected_last_date="2026-07-02")
    assert status == "HOLIDAY_BAR_ERROR"
    assert "2026-07-03" in reason


def test_daily_quality_rejects_invalid_ohlc() -> None:
    df = _valid_rows()
    df.loc[0, "high"] = 90
    status, _ = classify_symbol_quality(df, expected_last_date="2026-07-02")
    assert status == "INVALID_OHLC"


def test_daily_quality_rejects_duplicate_dates() -> None:
    df = _valid_rows()
    df = pd.concat([df, df.tail(1)], ignore_index=True)
    status, _ = classify_symbol_quality(df, expected_last_date="2026-07-02")
    assert status == "DUPLICATE_DATES"


def test_daily_quality_accepts_valid_symbol() -> None:
    status, reason = classify_symbol_quality(_valid_rows(), expected_last_date="2026-07-02")
    assert status == "DATA_READY"
    assert reason == "ok"


def test_daily_cache_loader_requires_read_only(tmp_path) -> None:
    universe = tmp_path / "universe.csv"
    universe.write_text("symbol,benchmark_only\nAAPL,false\n", encoding="utf-8")
    result = cache_daily_ohlcv(
        universe_path=universe,
        out_dir=tmp_path / "daily_ohlcv",
        duration="3Y",
        end_date="2026-07-06",
        read_only=False,
        dry_run=True,
    )
    assert result.status == "BLOCKED_READ_ONLY_REQUIRED"


def test_daily_universe_excludes_etfs_operational(tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "universe_us_mid_caps.csv").write_text(
        "symbol,name,cap_segment,note\nAAPL,Apple,midcap,seed\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "universe_us_small_caps.csv").write_text(
        "symbol,name,cap_segment,note\n",
        encoding="utf-8",
    )
    paths = build_daily_universes(tmp_path)
    rows = pd.read_csv(paths["pilot"])
    operational = rows[rows["operational_eligible"] == True]  # noqa: E712 - pandas scalar comparison.
    assert set(operational["product_type"]) == {"STK"}
    assert "SPY" not in set(operational["symbol"])


def test_daily_benchmarks_marked_benchmark_only(tmp_path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "universe_us_mid_caps.csv").write_text(
        "symbol,name,cap_segment,note\nAAPL,Apple,midcap,seed\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "universe_us_small_caps.csv").write_text(
        "symbol,name,cap_segment,note\n",
        encoding="utf-8",
    )
    paths = build_daily_universes(tmp_path)
    rows = pd.read_csv(paths["smoke"])
    benchmarks = rows[rows["symbol"].isin(["SPY", "QQQ"])]
    assert set(benchmarks["benchmark_only"]) == {True}
    assert set(benchmarks["operational_eligible"]) == {False}


def test_daily_quality_summary_passes_with_ready_symbols(tmp_path) -> None:
    universe = tmp_path / "universe.csv"
    symbols = ["AAPL", "MSFT", "SPY", "QQQ"]
    universe.write_text(
        "symbol,benchmark_only\n"
        + "\n".join(f"{symbol},{str(symbol in {'SPY', 'QQQ'}).lower()}" for symbol in symbols)
        + "\n",
        encoding="utf-8",
    )
    cache = tmp_path / "daily_ohlcv"
    cache.mkdir()
    for symbol in symbols:
        _valid_rows(symbol).to_csv(cache / f"{symbol}.csv", index=False)
    summary = check_daily_ohlcv_quality(
        cache_dir=cache,
        universe_path=universe,
        end_date="2026-07-06",
        report_csv=tmp_path / "quality.csv",
        summary_json=tmp_path / "quality.json",
        min_operational_ready=2,
    )
    assert summary["data_gate"] == "PASS"
    assert summary["last_valid_bar_date"] == "2026-07-02"
