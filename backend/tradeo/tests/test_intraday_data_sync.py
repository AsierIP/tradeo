from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from tradeo.modules.intraday.data_sync import IntradayDataSync


def test_intraday_data_sync_serves_only_closed_bars_and_manifest() -> None:
    idx = pd.date_range("2026-06-22 14:00", periods=4, freq="5min", tz="UTC")
    bars = pd.DataFrame(
        {
            "open": [10, 10.1, 10.2, 10.3],
            "high": [10.2, 10.3, 10.4, 10.5],
            "low": [9.9, 10.0, 10.1, 10.2],
            "close": [10.1, 10.2, 10.3, 10.4],
            "volume": [100, 120, 130, 140],
        },
        index=idx,
    )

    result = IntradayDataSync().sync(
        bars,
        symbol="soun",
        timeframe="5m",
        session_id="2026-06-22",
        now=datetime(2026, 6, 22, 14, 16, tzinfo=timezone.utc),
    )

    assert list(result.bars.index) == list(idx[:3])
    assert result.manifest.complete_bars == 3
    assert result.manifest.last_eligible_bar_at == idx[2].to_pydatetime()
    assert result.manifest.roles["trigger"] == 3
    assert result.reason_codes == ()


def test_intraday_data_sync_audits_duplicates_gaps_zero_volume_and_stale() -> None:
    idx = pd.to_datetime(
        [
            "2026-06-22T14:00:00Z",
            "2026-06-22T14:00:00Z",
            "2026-06-22T14:20:00Z",
        ]
    )
    bars = pd.DataFrame(
        {
            "open": [10, 10, 11],
            "high": [10.2, 10.2, 11.2],
            "low": [9.9, 9.9, 10.8],
            "close": [10.1, 10.1, 11],
            "volume": [100, 100, 0],
        },
        index=idx,
    )

    result = IntradayDataSync().sync(
        bars,
        symbol="soun",
        timeframe="5m",
        session_id="2026-06-22",
        now=datetime(2026, 6, 22, 15, 0, tzinfo=timezone.utc),
        stale_after_seconds=300,
    )

    assert result.manifest.duplicate_count == 1
    assert result.manifest.gap_count == 1
    assert result.manifest.zero_volume_count == 1
    assert result.manifest.stale is True
    assert result.manifest.last_eligible_bar_at is None
    assert set(result.reason_codes) == {"duplicates_removed", "unexpected_gaps", "zero_volume", "stale"}
