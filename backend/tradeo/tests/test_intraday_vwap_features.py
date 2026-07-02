from __future__ import annotations

import math

import pandas as pd

from tradeo.research.intraday_vwap_features import build_intraday_vwap_features


def _frame(index: pd.DatetimeIndex, rows: list[dict[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, index=index)


def test_vwap_calculates_typical_price_over_synthetic_bars() -> None:
    idx = pd.date_range("2026-07-01 09:30", periods=4, freq="5min", tz="America/New_York")
    bars = _frame(
        idx,
        [
            {"high": 10.2, "low": 9.8, "close": 10.0, "volume": 100},
            {"high": 10.5, "low": 10.1, "close": 10.3, "volume": 200},
            {"high": 10.8, "low": 10.2, "close": 10.6, "volume": 300},
            {"high": 11.0, "low": 10.4, "close": 10.8, "volume": 400},
        ],
    )

    result = build_intraday_vwap_features(bars).frame

    typical = ((bars["high"] + bars["low"] + bars["close"]) / 3.0).tolist()
    expected = [
        typical[0],
        (typical[0] * 100 + typical[1] * 200) / 300,
        (typical[0] * 100 + typical[1] * 200 + typical[2] * 300) / 600,
        (typical[0] * 100 + typical[1] * 200 + typical[2] * 300 + typical[3] * 400) / 1000,
    ]
    assert result["vwap"].tolist() == expected
    assert math.isclose(result["vwap_distance_bps"].iloc[-1], (10.8 / expected[-1] - 1.0) * 10_000)


def test_vwap_resets_by_session_and_handles_zero_volume() -> None:
    idx = pd.DatetimeIndex(
        [
            "2026-07-01 09:30",
            "2026-07-01 09:35",
            "2026-07-02 09:30",
            "2026-07-02 09:35",
        ],
        tz="America/New_York",
    )
    bars = _frame(
        idx,
        [
            {"high": 10.0, "low": 10.0, "close": 10.0, "volume": 100},
            {"high": 12.0, "low": 12.0, "close": 12.0, "volume": 100},
            {"high": 20.0, "low": 20.0, "close": 20.0, "volume": 0},
            {"high": 22.0, "low": 22.0, "close": 22.0, "volume": 100},
        ],
    )

    result = build_intraday_vwap_features(bars, price_mode="close").frame

    assert result["vwap"].iloc[0] == 10.0
    assert result["vwap"].iloc[1] == 11.0
    assert pd.isna(result["vwap"].iloc[2])
    assert result["vwap"].iloc[3] == 22.0


def test_timezone_naive_index_is_marked_with_assumption() -> None:
    idx = pd.date_range("2026-07-01 09:30", periods=2, freq="5min")
    bars = _frame(
        idx,
        [
            {"high": 10.0, "low": 10.0, "close": 10.0, "volume": 100},
            {"high": 11.0, "low": 11.0, "close": 11.0, "volume": 100},
        ],
    )

    result = build_intraday_vwap_features(bars, price_mode="close")

    assert result.metadata["timezone_assumption"] == "naive_index_localized_to_America/New_York"
    assert str(result.frame.index.tz) == "America/New_York"


def test_above_below_crosses_and_bars_since_cross() -> None:
    idx = pd.date_range("2026-07-01 09:30", periods=5, freq="5min", tz="America/New_York")
    bars = _frame(
        idx,
        [
            {"high": 10.0, "low": 10.0, "close": 10.0, "volume": 100},
            {"high": 9.0, "low": 9.0, "close": 9.0, "volume": 100},
            {"high": 11.0, "low": 11.0, "close": 11.0, "volume": 100},
            {"high": 12.0, "low": 12.0, "close": 12.0, "volume": 100},
            {"high": 8.0, "low": 8.0, "close": 8.0, "volume": 100},
        ],
    )

    result = build_intraday_vwap_features(bars, price_mode="close", slope_lookback=1).frame

    assert result["below_vwap"].tolist() == [False, True, False, False, True]
    assert result["above_vwap"].tolist() == [False, False, True, True, False]
    assert result["crossed_above_vwap"].tolist() == [False, False, True, False, False]
    assert result["crossed_below_vwap"].tolist() == [False, True, False, False, True]
    assert result["bars_since_vwap_cross"].astype("Int64").tolist() == [pd.NA, 0, 0, 1, 0]


def test_vwap_slope_direction_and_session_buckets() -> None:
    idx = pd.DatetimeIndex(
        [
            "2026-07-01 09:29",
            "2026-07-01 09:30",
            "2026-07-01 09:35",
            "2026-07-01 12:00",
            "2026-07-01 15:30",
            "2026-07-01 16:00",
        ],
        tz="America/New_York",
    )
    bars = _frame(
        idx,
        [
            {"high": 9.0, "low": 9.0, "close": 9.0, "volume": 100},
            {"high": 10.0, "low": 10.0, "close": 10.0, "volume": 100},
            {"high": 10.0, "low": 10.0, "close": 10.0, "volume": 100},
            {"high": 11.0, "low": 11.0, "close": 11.0, "volume": 100},
            {"high": 12.0, "low": 12.0, "close": 12.0, "volume": 100},
            {"high": 13.0, "low": 13.0, "close": 13.0, "volume": 100},
        ],
    )

    result = build_intraday_vwap_features(bars, price_mode="close", slope_lookback=1).frame

    assert result["session_bucket"].tolist() == [
        "out_of_session",
        "open",
        "open",
        "mid",
        "close",
        "out_of_session",
    ]
    assert result["vwap_slope_direction"].iloc[1] == "unknown"
    assert result["vwap_slope_direction"].iloc[2] == "flat"
    assert result["vwap_slope_direction"].iloc[3] == "up"


def test_future_bars_do_not_change_past_features() -> None:
    idx = pd.date_range("2026-07-01 09:30", periods=5, freq="5min", tz="America/New_York")
    bars = _frame(
        idx,
        [
            {"high": 10.0, "low": 10.0, "close": 10.0, "volume": 100},
            {"high": 11.0, "low": 11.0, "close": 11.0, "volume": 100},
            {"high": 12.0, "low": 12.0, "close": 12.0, "volume": 100},
            {"high": 13.0, "low": 13.0, "close": 13.0, "volume": 100},
            {"high": 14.0, "low": 14.0, "close": 14.0, "volume": 100},
        ],
    )
    mutated = bars.copy()
    mutated.iloc[-1] = {"high": 50.0, "low": 50.0, "close": 50.0, "volume": 10_000}

    base = build_intraday_vwap_features(bars, price_mode="close").frame
    changed = build_intraday_vwap_features(mutated, price_mode="close").frame

    pd.testing.assert_frame_equal(base.iloc[:4], changed.iloc[:4])


def test_basic_vwap_events_reclaim_hold_reject_and_extensions() -> None:
    idx = pd.date_range("2026-07-01 09:30", periods=6, freq="5min", tz="America/New_York")
    bars = _frame(
        idx,
        [
            {"high": 10.0, "low": 10.0, "close": 10.0, "volume": 100},
            {"high": 9.0, "low": 9.0, "close": 9.0, "volume": 100},
            {"high": 12.0, "low": 12.0, "close": 12.0, "volume": 100},
            {"high": 12.0, "low": 10.0, "close": 11.5, "volume": 100},
            {"high": 10.6, "low": 8.0, "close": 8.2, "volume": 100},
            {"high": 9.8, "low": 7.5, "close": 7.8, "volume": 100},
        ],
    )

    result = build_intraday_vwap_features(
        bars,
        price_mode="close",
        slope_lookback=1,
        extension_bps=500,
    ).frame

    assert bool(result["vwap_reclaim_long"].iloc[2]) is True
    assert bool(result["vwap_hold_long"].iloc[3]) is True
    assert bool(result["vwap_loss_long_exit"].iloc[4]) is True
    assert bool(result["vwap_loss_short"].iloc[4]) is True
    assert bool(result["vwap_reject_short"].iloc[5]) is True
    assert bool(result["vwap_extension_up"].iloc[2]) is True
    assert bool(result["vwap_extension_down"].iloc[5]) is True
    assert bool(result["vwap_mean_reversion_candidate"].iloc[5]) is True
