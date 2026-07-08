from __future__ import annotations

import json
from pathlib import Path

from tradeo.core.config import Settings
from tradeo.services.intraday_research_readiness import (
    IntradayResearchReadinessGate,
    IntradayResearchWaveSpec,
)


def _write_universe(path: Path, symbols: list[str]) -> None:
    path.write_text(
        "symbol,name\n" + "\n".join(f"{symbol},{symbol}" for symbol in symbols) + "\n",
        encoding="utf-8",
    )


def _write_cache(cache_dir: Path, symbol: str, timeframe: str, period: str, rows: int = 100) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    stem = "_".join((symbol.upper(), timeframe, period))
    (cache_dir / f"{stem}.csv").write_text("timestamp,open,high,low,close,volume\n", encoding="utf-8")
    (cache_dir / f"{stem}.metadata.json").write_text(
        json.dumps(
            {
                "symbol": symbol.upper(),
                "interval": timeframe,
                "period": period,
                "rows": rows,
                "last_timestamp": "2026-01-01T15:30:00+0000",
                "sha256": "abc123",
            }
        ),
        encoding="utf-8",
    )


def _settings(tmp_path: Path, universe: Path) -> Settings:
    return Settings(
        market_data_cache_dir=str(tmp_path / "cache"),
        intraday_universe_file=str(universe),
        artifacts_dir=str(tmp_path / "artifacts"),
    )


def test_readiness_blocks_when_cache_is_missing(tmp_path: Path) -> None:
    universe = tmp_path / "universe.csv"
    _write_universe(universe, ["AAA", "BBB"])
    settings = _settings(tmp_path, universe)
    spec = IntradayResearchWaveSpec.from_settings(
        settings,
        period="60d",
        timeframes=("30m",),
        limit=2,
        min_cache_coverage=0.90,
    )

    result = IntradayResearchReadinessGate(settings).evaluate(spec)

    assert result.ready is False
    assert result.status == "DATA_MISSING"
    assert result.coverage == 0.0
    assert result.missing_or_bad == 2
    assert {row.reason for row in result.checks} == {"csv_missing"}


def test_readiness_passes_when_cache_coverage_is_high_enough(tmp_path: Path) -> None:
    universe = tmp_path / "universe.csv"
    _write_universe(universe, ["AAA", "BBB"])
    settings = _settings(tmp_path, universe)
    _write_cache(settings.market_data_cache_path, "AAA", "30m", "60d")
    _write_cache(settings.market_data_cache_path, "BBB", "30m", "60d")
    spec = IntradayResearchWaveSpec.from_settings(
        settings,
        period="60d",
        timeframes=("30m",),
        limit=2,
        min_cache_coverage=1.0,
    )

    result = IntradayResearchReadinessGate(settings).evaluate(spec)

    assert result.ready is True
    assert result.status == "DATA_READY"
    assert result.ok == 2
    assert result.total == 2
    assert result.manifest["manifest_hash"] == result.manifest_hash


def test_readiness_manifest_hash_changes_with_benchmark_regime_filter(tmp_path: Path) -> None:
    universe = tmp_path / "universe.csv"
    _write_universe(universe, ["AAA"])
    settings = _settings(tmp_path, universe)
    _write_cache(settings.market_data_cache_path, "AAA", "1h", "60d")

    base = IntradayResearchReadinessGate(settings).evaluate(
        IntradayResearchWaveSpec.from_settings(
            settings,
            period="60d",
            timeframes=("1h",),
            limit=1,
            benchmark_regime_filter="none",
        )
    )
    filtered = IntradayResearchReadinessGate(settings).evaluate(
        IntradayResearchWaveSpec.from_settings(
            settings,
            period="60d",
            timeframes=("1h",),
            limit=1,
            benchmark_regime_filter="spy_qqq_positive",
            benchmark_symbols=("SPY", "QQQ"),
        )
    )

    assert base.manifest_hash != filtered.manifest_hash
    assert filtered.manifest["spec"]["benchmark_regime_filter"] == "spy_qqq_positive"
    assert filtered.manifest["spec"]["benchmark_symbols"] == ["SPY", "QQQ"]


def test_readiness_detects_metadata_period_mismatch(tmp_path: Path) -> None:
    universe = tmp_path / "universe.csv"
    _write_universe(universe, ["AAA"])
    settings = _settings(tmp_path, universe)
    _write_cache(settings.market_data_cache_path, "AAA", "30m", "30d")
    spec = IntradayResearchWaveSpec.from_settings(
        settings,
        period="60d",
        timeframes=("30m",),
        limit=1,
    )

    result = IntradayResearchReadinessGate(settings).evaluate(spec)

    assert result.ready is False
    assert result.checks[0].reason == "csv_missing"
