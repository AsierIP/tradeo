from __future__ import annotations

import numpy as np
import pandas as pd

from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.research.window_sampler import WindowSampler
from tradeo.services.technical_indicators import atr


def test_fast_benchmark_alignment_keeps_pandas_dropna_semantics() -> None:
    window_index = pd.date_range("2026-06-22 13:30", periods=8, freq="5min", tz="UTC")
    benchmark_index = pd.date_range("2026-06-22 13:25", periods=5, freq="10min", tz="UTC")
    benchmark = pd.DataFrame(
        {"close": [100.0, np.nan, np.inf, 104.0, 105.0]},
        index=benchmark_index,
    ).sample(frac=1.0, random_state=11)

    expected = (
        benchmark.sort_index()
        .reindex(window_index, method="ffill")
        .dropna(subset=["close"])["close"]
        .to_numpy(dtype=float)
    )

    aligned = PatternEmbeddingEngine._aligned_benchmark_close_values(window_index, benchmark)

    assert aligned is not None
    assert np.array_equal(aligned, expected)


def test_fast_weekly_close_values_match_pandas_resample_with_timezone_and_empty_weeks() -> None:
    index = pd.DatetimeIndex(
        [
            "2026-03-06 15:55",
            "2026-03-08 15:55",
            "2026-03-09 09:35",
            "2026-03-13 15:55",
            "2026-03-30 09:35",
            "2026-04-03 15:55",
        ],
        tz="America/New_York",
    )
    close = np.array([10.0, np.nan, 10.8, 11.0, np.nan, 12.5], dtype=float)
    expected = pd.Series(close, index=index).resample("W").last().to_numpy(
        dtype=float,
        copy=False,
    )

    actual = PatternEmbeddingEngine._weekly_close_values(close, index)

    np.testing.assert_array_equal(actual, expected)


def test_fast_weekly_market_context_matches_pandas_resample_reference() -> None:
    index = pd.date_range("2026-06-19 09:35", periods=96, freq="4h", tz="UTC")
    close = np.linspace(10.0, 12.0, len(index)) + np.sin(np.arange(len(index)) * 0.17) * 0.08
    weekly_close = pd.Series(close, index=index).resample("W").last()
    expected_weekly_return = float(weekly_close.iloc[-1] / max(float(weekly_close.iloc[0]), 1e-9) - 1.0)
    expected_weekly_trend = PatternEmbeddingEngine._slope(
        (weekly_close / max(float(weekly_close.iloc[0]), 1e-9) - 1.0).to_numpy()
    )

    features = PatternEmbeddingEngine._market_context_features_from_values(close, index, {})

    assert features["weekly_return"] == expected_weekly_return
    assert features["weekly_trend"] == expected_weekly_trend


def test_precomputed_week_codes_match_weekly_close_reference() -> None:
    index = pd.DatetimeIndex(
        [
            "2026-03-06 15:55",
            "2026-03-08 15:55",
            "2026-03-09 09:35",
            "2026-03-13 15:55",
            "2026-03-30 09:35",
            "2026-04-03 15:55",
        ],
        tz="America/New_York",
    )
    close = np.array([10.0, np.nan, 10.8, 11.0, np.nan, 12.5], dtype=float)

    week_codes = WindowSampler._week_codes_for_embedding(index)
    assert week_codes is not None
    actual = PatternEmbeddingEngine._weekly_close_values_from_week_codes(close, week_codes)
    expected = PatternEmbeddingEngine._weekly_close_values(close, index)

    np.testing.assert_array_equal(actual, expected)


def test_market_context_aligns_each_benchmark_once(monkeypatch) -> None:
    window_index = pd.date_range("2026-06-22 13:30", periods=30, freq="5min", tz="UTC")
    window = pd.DataFrame(
        {
            "open": np.linspace(10.0, 11.0, len(window_index)),
            "high": np.linspace(10.2, 11.2, len(window_index)),
            "low": np.linspace(9.8, 10.8, len(window_index)),
            "close": np.linspace(10.1, 11.1, len(window_index)),
            "volume": np.full(len(window_index), 100_000),
        },
        index=window_index,
    )
    benchmark_index = pd.date_range("2026-06-22 13:25", periods=18, freq="10min", tz="UTC")
    spy = pd.DataFrame(
        {"close": np.linspace(100.0, 104.0, len(benchmark_index))},
        index=benchmark_index,
    )
    qqq = pd.DataFrame(
        {"close": np.linspace(200.0, 202.0, len(benchmark_index))},
        index=benchmark_index,
    )
    original = PatternEmbeddingEngine._aligned_benchmark_close_values
    calls: list[int] = []

    def counted_alignment(index: pd.DatetimeIndex, benchmark: pd.DataFrame) -> np.ndarray | None:
        calls.append(id(benchmark))
        return original(index, benchmark)

    monkeypatch.setattr(
        PatternEmbeddingEngine,
        "_aligned_benchmark_close_values",
        staticmethod(counted_alignment),
    )

    features = PatternEmbeddingEngine._market_context_features(
        window,
        {"SPY": spy, "QQQ": qqq},
    )

    assert calls == [id(spy), id(qqq)]
    assert features["relative_strength_spy"] != features["relative_strength_qqq"]
    assert features["market_breadth_proxy"] in {0.0, 0.5, 1.0}


def test_array_embedding_path_matches_dataframe_embedding_with_precomputed_inputs() -> None:
    full_index = pd.date_range("2026-06-22 12:40", periods=70, freq="5min", tz="UTC")
    positions = np.arange(len(full_index))
    base = np.linspace(10.0, 12.7, len(full_index)) + np.sin(positions) * 0.05
    open_values = base * (1.0 + np.sin(positions * 0.3) * 0.005)
    close_values = base * (1.0 + np.cos(positions * 0.2) * 0.005)
    full = pd.DataFrame(
        {
            "open": open_values,
            "high": np.maximum(open_values, close_values) + 0.18,
            "low": np.minimum(open_values, close_values) - 0.16,
            "close": close_values,
            "volume": np.linspace(100_000, 180_000, len(full_index)),
        },
        index=full_index,
    )
    start_pos = 10
    end_pos = 59
    window = full.iloc[start_pos : end_pos + 1]
    benchmark_index = pd.date_range("2026-06-22 12:35", periods=40, freq="10min", tz="UTC")
    benchmarks = {
        "SPY": pd.DataFrame(
            {"close": np.linspace(100.0, 104.0, len(benchmark_index))},
            index=benchmark_index,
        ),
        "sector_etf": pd.DataFrame(
            {"close": np.linspace(50.0, 51.0, len(benchmark_index))},
            index=benchmark_index,
        ).sample(frac=1.0, random_state=17),
    }
    engine = PatternEmbeddingEngine()

    expected_vector, expected_features, expected_chart = engine.embed(window, benchmarks)
    benchmark_close_values = {
        key: PatternEmbeddingEngine._aligned_benchmark_close_values(window.index, frame)
        for key, frame in benchmarks.items()
    }
    vector, features, chart = engine.embed_arrays(
        open_values=window["open"].to_numpy(dtype=float, copy=False),
        high_values=window["high"].to_numpy(dtype=float, copy=False),
        low_values=window["low"].to_numpy(dtype=float, copy=False),
        close_values=window["close"].to_numpy(dtype=float, copy=False),
        volume_values=window["volume"].to_numpy(dtype=float, copy=False),
        index=window.index,
        benchmark_frames=benchmarks,
        benchmark_close_values=benchmark_close_values,
        atr_raw=atr(window, 14).to_numpy(dtype=float, copy=False),
    )

    np.testing.assert_array_equal(vector, expected_vector)
    assert features == expected_features
    assert chart == expected_chart

    full_benchmark_close_values = WindowSampler._benchmark_close_arrays_for_embedding(
        full.index,
        benchmarks,
    )
    full_week_codes = WindowSampler._week_codes_for_embedding(full.index)
    assert full_benchmark_close_values is not None
    assert full_week_codes is not None
    vector, features, chart = engine.embed_arrays(
        open_values=full["open"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        high_values=full["high"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        low_values=full["low"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        close_values=full["close"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        volume_values=full["volume"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        index=full.index[start_pos : end_pos + 1],
        benchmark_frames=benchmarks,
        benchmark_close_values=full_benchmark_close_values,
        benchmark_close_slice=(start_pos, end_pos),
        week_codes=full_week_codes[start_pos : end_pos + 1],
        atr_raw=atr(window, 14).to_numpy(dtype=float, copy=False),
    )

    np.testing.assert_array_equal(vector, expected_vector)
    assert features == expected_features
    assert chart == expected_chart

    vector, features, chart = engine.embed_arrays(
        open_values=full["open"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        high_values=full["high"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        low_values=full["low"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        close_values=full["close"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        volume_values=full["volume"].to_numpy(dtype=float, copy=False)[start_pos : end_pos + 1],
        index=pd.RangeIndex(len(window)),
        benchmark_frames=benchmarks,
        benchmark_close_values=full_benchmark_close_values,
        benchmark_close_slice=(start_pos, end_pos),
        week_codes=full_week_codes[start_pos : end_pos + 1],
        atr_raw=atr(window, 14).to_numpy(dtype=float, copy=False),
    )

    np.testing.assert_array_equal(vector, expected_vector)
    assert features == expected_features
    assert chart == expected_chart


def test_cached_shapelet_features_match_reference_path() -> None:
    engine = PatternEmbeddingEngine()
    cases = [
        (
            np.linspace(-0.2, 0.35, 73) + np.sin(np.arange(73) * 0.31) * 0.07,
            np.clip(
                np.linspace(0.1, 1.3, 73) + np.cos(np.arange(73) * 0.17) * 0.08,
                0,
                5,
            ),
        ),
        (np.ones(37), np.linspace(0.2, 1.1, 37)),
        (np.linspace(-0.4, 0.4, 41), np.ones(41)),
    ]

    for price_norm, volume_rel in cases:
        expected = PatternEmbeddingEngine._shapelet_features(price_norm, volume_rel)
        actual = engine._shapelet_features_cached(price_norm, volume_rel)

        assert actual == expected


def test_fast_corr_matches_previous_corrcoef_semantics() -> None:
    cases = [
        (
            np.linspace(-1.0, 1.0, 16),
            np.sin(np.arange(16) * 0.3),
        ),
        (
            np.ones(16),
            np.linspace(2.0, 4.0, 16),
        ),
        (
            np.array([1.0, np.nan, 3.0, 4.0]),
            np.array([4.0, 3.0, 2.0, 1.0]),
        ),
    ]

    for left, right in cases:
        left_std = float(np.std(left))
        right_std = float(np.std(right))
        expected = 0.0 if left_std == 0.0 or right_std == 0.0 else float(np.corrcoef(left, right)[0, 1])
        actual = PatternEmbeddingEngine._corr(left, right)

        if np.isnan(expected):
            assert np.isnan(actual)
        else:
            assert actual == expected


def test_phase_features_match_array_split_reference() -> None:
    for length in range(0, 31):
        volume_rel = np.linspace(0.1, 1.7, length) if length else np.array([], dtype=float)
        range_pct = np.cos(np.arange(length) * 0.29) if length else np.array([], dtype=float)
        returns = np.sin(np.arange(length) * 0.17) * 0.02 if length else np.array([], dtype=float)
        thirds = np.array_split(np.arange(length), 3)
        volume_means = [float(np.mean(volume_rel[idxs])) if len(idxs) else 0.0 for idxs in thirds]
        range_means = [float(np.mean(range_pct[idxs])) if len(idxs) else 0.0 for idxs in thirds]
        return_means = [float(np.mean(returns[idxs])) if len(idxs) else 0.0 for idxs in thirds]
        expected = {
            "volume_phase_early": volume_means[0] * 5.0,
            "volume_phase_mid": volume_means[1] * 5.0,
            "volume_phase_late": volume_means[2] * 5.0,
            "volume_phase_acceleration": volume_means[2] - volume_means[0],
            "range_phase_expansion": range_means[2] - range_means[0],
            "return_phase_acceleration": return_means[2] - return_means[0],
        }

        assert PatternEmbeddingEngine._phase_features(volume_rel, range_pct, returns) == expected


def test_window_sampler_embedding_atr_raw_matches_pandas_window_atr() -> None:
    index = pd.date_range("2026-01-01", periods=160, freq="D", tz="UTC")
    base = np.linspace(10.0, 24.0, len(index)) + np.sin(np.arange(len(index))) * 0.35
    open_values = base * (1.0 + np.sin(np.arange(len(index)) * 0.7) * 0.01)
    close_values = base * (1.0 + np.cos(np.arange(len(index)) * 0.5) * 0.01)
    high_values = np.maximum(open_values, close_values) + 0.2
    low_values = np.minimum(open_values, close_values) - 0.2
    df = pd.DataFrame(
        {
            "open": open_values,
            "high": high_values,
            "low": low_values,
            "close": close_values,
            "volume": np.linspace(100_000, 500_000, len(index)),
        },
        index=index,
    )
    full_atr_raw = atr(df, 14).to_numpy(dtype=float, copy=False)
    true_ranges = WindowSampler._true_range_values(high_values, low_values, close_values)
    bar_ranges = high_values - low_values

    for window_size in (10, 14, 15, 20, 50, 100):
        for end in (window_size - 1, 79, 159):
            start = end - window_size + 1
            if start < 0:
                continue
            expected = (
                atr(df.iloc[start : end + 1], 14).to_numpy(dtype=float, copy=False)
                if window_size >= 15
                else np.zeros(window_size, dtype=float)
            )
            actual = WindowSampler._embedding_atr_raw_for_window(
                full_atr_raw=full_atr_raw,
                true_ranges=true_ranges,
                bar_ranges=bar_ranges,
                start=start,
                end=end,
            )

            np.testing.assert_array_equal(actual, expected)
