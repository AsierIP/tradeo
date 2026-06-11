from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from tradeo.core.config import Settings
from tradeo.services.data_provider import CachedMarketDataProvider, detect_unadjusted_splits
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.ibkr_data_provider import inspect_ibkr_connection
from tradeo.services.universe_snapshot import UniverseSnapshotService


def test_settings_reject_synthetic_market_data() -> None:
    with pytest.raises(ValueError, match="Synthetic market data is forbidden"):
        Settings(allow_synthetic_market_data=True)


def test_settings_reject_non_ibkr_market_data_provider() -> None:
    with pytest.raises(ValueError, match="only permits IBKR market data"):
        Settings(market_data_provider="yfinance")


def test_market_data_factory_returns_ibkr_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRADEO_MARKET_DATA_PROVIDER", "ibkr")
    monkeypatch.setenv("TRADEO_ALLOW_SYNTHETIC_MARKET_DATA", "false")
    monkeypatch.setenv("TRADEO_MARKET_DATA_CACHE_ENABLED", "false")
    from tradeo.core.config import get_settings

    get_settings.cache_clear()
    try:
        provider = get_market_data_provider()
    finally:
        get_settings.cache_clear()

    assert provider.__class__.__name__ == "IBKRHistoricalDataProvider"


def test_market_data_factory_wraps_ibkr_with_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TRADEO_MARKET_DATA_PROVIDER", "ibkr")
    monkeypatch.setenv("TRADEO_ALLOW_SYNTHETIC_MARKET_DATA", "false")
    monkeypatch.setenv("TRADEO_MARKET_DATA_CACHE_ENABLED", "true")
    monkeypatch.setenv("TRADEO_MARKET_DATA_CACHE_DIR", str(tmp_path / "cache"))
    from tradeo.core.config import get_settings

    get_settings.cache_clear()
    try:
        provider = get_market_data_provider()
    finally:
        get_settings.cache_clear()

    assert provider.__class__.__name__ == "CachedMarketDataProvider"


def _ohlcv_frame() -> pd.DataFrame:
    idx = pd.date_range("2026-01-02", periods=3, freq="B")
    return pd.DataFrame(
        {
            "open": [10.0, 10.5, 11.0],
            "high": [10.8, 11.2, 11.8],
            "low": [9.8, 10.1, 10.7],
            "close": [10.4, 11.0, 11.4],
            "volume": [100_000, 120_000, 140_000],
        },
        index=idx,
    )


def test_cached_market_data_provider_persists_manifest(tmp_path: Path) -> None:
    class Upstream:
        calls = 0

        def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
            self.calls += 1
            return _ohlcv_frame()

    upstream = Upstream()
    provider = CachedMarketDataProvider(
        upstream=upstream,
        cache_dir=tmp_path,
        adjusted=True,
        what_to_show="ADJUSTED_LAST",
    )

    first = provider.fetch_ohlcv("aaa", period="5y", interval="1d")
    second = provider.fetch_ohlcv("AAA", period="5y", interval="1d")
    manifest = provider.data_manifest(["AAA"])

    assert upstream.calls == 1
    assert first.equals(second)
    assert first["adjusted"].all()
    assert set(first["what_to_show"]) == {"ADJUSTED_LAST"}
    assert first["bar_complete"].all()
    assert manifest["artifact_format"] == "canonical_csv"
    assert manifest["manifest_hash"]
    entry = next(iter(manifest["entries"].values()))
    assert entry["symbol"] == "AAA"
    assert entry["adjusted"] is True
    assert entry["what_to_show"] == "ADJUSTED_LAST"


def _frame_ending(days_ago: int, *, periods: int, base: float = 10.0) -> pd.DataFrame:
    end = pd.Timestamp(datetime.now(timezone.utc).date()) - pd.Timedelta(days=days_ago)
    idx = pd.bdate_range(end=end, periods=periods)
    closes = [base + 0.1 * i for i in range(periods)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c * 1.02 for c in closes],
            "low": [c * 0.98 for c in closes],
            "close": closes,
            "volume": [100_000 + 1_000 * i for i in range(periods)],
        },
        index=idx,
    )


class _RecordingUpstream:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        self.calls: list[tuple[str, str, str]] = []

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        self.calls.append((symbol, period, interval))
        return self.df.copy()


def _seed_cache(tmp_path: Path, stale: pd.DataFrame) -> None:
    seeder = CachedMarketDataProvider(
        upstream=_RecordingUpstream(stale),
        cache_dir=tmp_path,
        adjusted=True,
        what_to_show="ADJUSTED_LAST",
    )
    seeder.fetch_ohlcv("AAA", period="2y", interval="1d")


def test_incremental_refresh_appends_missing_tail(tmp_path: Path) -> None:
    full = _frame_ending(1, periods=60)
    stale = full.iloc[:-7]
    _seed_cache(tmp_path, stale)

    upstream = _RecordingUpstream(full)
    provider = CachedMarketDataProvider(
        upstream=upstream,
        cache_dir=tmp_path,
        adjusted=True,
        what_to_show="ADJUSTED_LAST",
        incremental_enabled=True,
        incremental_overlap_bars=5,
        incremental_min_gap_days=1,
        incremental_max_gap_days=45,
    )
    refreshed = provider.fetch_ohlcv("AAA", period="2y", interval="1d")

    assert len(upstream.calls) == 1
    assert upstream.calls[0][1].endswith("d")
    assert pd.Timestamp(refreshed.index[-1]) == pd.Timestamp(full.index[-1])
    metadata = json.loads((tmp_path / "AAA_1d_2y.metadata.json").read_text())
    assert metadata["refresh_mode"] == "incremental_append"
    assert metadata["rows_appended"] == 7
    assert metadata["incremental_fetch_supported"] is True
    manifest_entry = provider.data_manifest(["AAA"])["entries"]["AAA_1d_2y"]
    assert manifest_entry["refresh_mode"] == "incremental_append"
    assert manifest_entry["incremental_fetch_supported"] is True


def test_incremental_refresh_full_refetch_on_overlap_mismatch(tmp_path: Path) -> None:
    stale = _frame_ending(1, periods=60).iloc[:-7]
    _seed_cache(tmp_path, stale)

    readjusted = _frame_ending(1, periods=60, base=9.0)
    upstream = _RecordingUpstream(readjusted)
    provider = CachedMarketDataProvider(
        upstream=upstream,
        cache_dir=tmp_path,
        adjusted=True,
        what_to_show="ADJUSTED_LAST",
        incremental_enabled=True,
        incremental_overlap_bars=5,
        incremental_min_gap_days=1,
        incremental_max_gap_days=45,
    )
    refreshed = provider.fetch_ohlcv("AAA", period="2y", interval="1d")

    assert [call[1] for call in upstream.calls[-1:]] == ["2y"]
    assert len(upstream.calls) == 2
    assert float(refreshed["close"].iloc[0]) == 9.0
    metadata = json.loads((tmp_path / "AAA_1d_2y.metadata.json").read_text())
    assert metadata["refresh_mode"] == "full_refetch_overlap_mismatch"


def test_incremental_refresh_disabled_keeps_cache_untouched(tmp_path: Path) -> None:
    stale = _frame_ending(10, periods=40)
    _seed_cache(tmp_path, stale)

    upstream = _RecordingUpstream(_frame_ending(1, periods=60))
    provider = CachedMarketDataProvider(
        upstream=upstream,
        cache_dir=tmp_path,
        adjusted=True,
        what_to_show="ADJUSTED_LAST",
        incremental_enabled=False,
    )
    cached = provider.fetch_ohlcv("AAA", period="2y", interval="1d")

    assert upstream.calls == []
    assert pd.Timestamp(cached.index[-1]) == pd.Timestamp(stale.index[-1])


def test_incremental_refresh_skips_fresh_cache(tmp_path: Path) -> None:
    fresh = _frame_ending(1, periods=40)
    _seed_cache(tmp_path, fresh)

    upstream = _RecordingUpstream(fresh)
    provider = CachedMarketDataProvider(
        upstream=upstream,
        cache_dir=tmp_path,
        adjusted=True,
        what_to_show="ADJUSTED_LAST",
        incremental_enabled=True,
        incremental_min_gap_days=1,
    )
    provider.fetch_ohlcv("AAA", period="2y", interval="1d")

    assert upstream.calls == []


def test_detect_unadjusted_splits_flags_split_like_gap() -> None:
    idx = pd.date_range("2026-01-02", periods=4, freq="B")
    df = pd.DataFrame(
        {
            "open": [100.0, 101.0, 50.0, 51.0],
            "high": [102.0, 103.0, 52.0, 53.0],
            "low": [99.0, 100.0, 49.0, 50.5],
            "close": [101.0, 100.0, 51.0, 52.0],
            "volume": [1_000_000, 1_050_000, 1_100_000, 1_000_000],
        },
        index=idx,
    )

    flagged = detect_unadjusted_splits(df)

    assert flagged == [pd.Timestamp(idx[2]).isoformat()]


def test_universe_snapshot_filters_and_marks_survivorship(tmp_path: Path) -> None:
    settings = Settings(
        universe_snapshot_dir=str(tmp_path / "snapshots"),
        universe_file=str(tmp_path / "universe.csv"),
        universe_point_in_time_available=False,
        min_price=2.0,
        min_avg_dollar_volume=5_000_000,
    )
    universe = pd.DataFrame(
        [
            {"symbol": "aaa", "price": 3.0, "avg_dollar_volume": 6_000_000, "exchange": "NASDAQ"},
            {"symbol": "bbb", "price": 1.0, "avg_dollar_volume": 6_000_000, "exchange": "NASDAQ"},
            {"symbol": "ccc", "price": 8.0, "avg_dollar_volume": 1_000_000, "exchange": "NYSE"},
            {"symbol": "ddd", "price": 8.0, "avg_dollar_volume": 8_000_000, "exchange": "OTC"},
        ]
    )

    snapshot = UniverseSnapshotService(settings).build_monthly_snapshot("2026-06-10", universe=universe)
    df = pd.read_csv(snapshot["path"])

    assert snapshot["snapshot_month"] == "2026-06"
    assert snapshot["row_count"] == 1
    assert snapshot["symbols"] == ["AAA"]
    assert snapshot["survivorship_biased"] is True
    assert df["symbol"].tolist() == ["AAA"]


def test_universe_snapshot_content_hash_is_deterministic(tmp_path: Path) -> None:
    settings = Settings(
        universe_snapshot_dir=str(tmp_path / "snapshots"),
        universe_file=str(tmp_path / "universe.csv"),
        universe_point_in_time_available=False,
        min_price=2.0,
        min_avg_dollar_volume=5_000_000,
    )
    universe = pd.DataFrame(
        [
            {"symbol": "aaa", "price": 3.0, "avg_dollar_volume": 6_000_000, "exchange": "NASDAQ"},
            {"symbol": "zzz", "price": 9.0, "avg_dollar_volume": 9_000_000, "exchange": "NYSE"},
        ]
    )
    service = UniverseSnapshotService(settings)

    first = service.build_monthly_snapshot("2026-06-10", universe=universe)
    second = service.build_monthly_snapshot("2026-06-10", universe=universe)

    assert first["content_hash"] == second["content_hash"]
    assert first["delisting_data_available"] is False
    assert first["survivorship_biased"] is True


class FakeIB:
    account_summary_calls = 0

    def __init__(self) -> None:
        self.connected = False

    def connect(self, host: str, port: int, clientId: int, timeout: int) -> None:  # noqa: N803
        self.connected = True

    def reqCurrentTime(self) -> datetime:  # noqa: N802
        return datetime(2026, 6, 6, tzinfo=timezone.utc)

    def managedAccounts(self) -> list[str]:  # noqa: N802
        return ["REDACTED_ACCOUNT"]

    def accountSummary(self, account: str) -> list[SimpleNamespace]:  # noqa: N802
        type(self).account_summary_calls += 1
        raise AssertionError("public health check must not request account summary")

    def isConnected(self) -> bool:  # noqa: N802
        return self.connected

    def disconnect(self) -> None:
        self.connected = False


def test_ibkr_health_check_omits_account_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeIB.account_summary_calls = 0
    monkeypatch.setitem(sys.modules, "ib_insync", SimpleNamespace(IB=FakeIB))

    status = inspect_ibkr_connection(
        Settings(
            ibkr_host="127.0.0.1",
            ibkr_port=7497,
            ibkr_client_id=17,
            ibkr_readonly=True,
            ibkr_account="REDACTED_ACCOUNT",
        )
    )

    assert status["ok"] is True
    assert status["readonly"] is True
    assert status["live_armed"] is False
    assert status["managed_accounts_count"] == 1
    assert status["selected_account_configured"] is True
    assert status["account_summary_included"] is False
    assert "account_summary" not in status
    assert FakeIB.account_summary_calls == 0
