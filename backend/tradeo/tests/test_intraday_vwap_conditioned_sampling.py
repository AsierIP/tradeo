from __future__ import annotations

import pandas as pd

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings
from tradeo.research.intraday_research_planner import ResearchWaveSpec, filter_prohibited_waves
from tradeo.research.intraday_vwap_conditions import expected_side_from_vwap_condition
from tradeo.research.window_sampler import WindowSampler
from tradeo.schemas import DiscoveryRunRequest
from tradeo.tasks import worker


def test_vwap_condition_none_preserves_sample_count() -> None:
    bars = _bars()
    sampler = WindowSampler()

    baseline = sampler.sample("AAA", bars, "30m", [10], [1], stride=1, max_windows_per_symbol=20)
    explicit_none = sampler.sample(
        "AAA",
        bars,
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        vwap_condition="none",
    )

    assert len(explicit_none) == len(baseline)


def test_vwap_reclaim_long_filters_to_compatible_events() -> None:
    samples = WindowSampler().sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        vwap_condition="vwap_reclaim_long",
        vwap_min_slope_bps=0.0,
    )

    assert samples
    assert all(sample.features["vwap_condition"] == "vwap_reclaim_long" for sample in samples)
    assert all(sample.features["vwap_condition_passed"] is True for sample in samples)
    assert all(sample.features["above_vwap"] is True for sample in samples)
    assert any(sample.features["vwap_reclaim_long"] is True for sample in samples)


def test_vwap_reject_short_filters_to_compatible_events() -> None:
    samples = WindowSampler().sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        vwap_condition="vwap_reject_short",
    )

    assert samples
    assert all(sample.features["vwap_side_bias"] == "short" for sample in samples)
    assert all(sample.features["vwap_condition_passed"] is True for sample in samples)
    assert all(sample.features["below_vwap"] is True for sample in samples)


def test_expected_side_from_vwap_condition_prefers_explicit_bias() -> None:
    assert expected_side_from_vwap_condition("vwap_reject_short", "long") == "long"
    assert expected_side_from_vwap_condition("vwap_reject_short", None) == "short"
    assert expected_side_from_vwap_condition("vwap_reclaim_long", None) == "long"
    assert expected_side_from_vwap_condition("none", None) is None


def test_vwap_features_appear_on_conditioned_window_samples() -> None:
    sample = WindowSampler().sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        vwap_condition="vwap_above_rising",
    )[0]

    assert "vwap_distance_bps" in sample.features
    assert "vwap_slope_bps" in sample.features
    assert "crossed_above_vwap" in sample.features


def test_vwap_condition_uses_no_future_bars() -> None:
    bars = _bars()
    mutated = bars.copy()
    mutated.loc[mutated.index[11]:, ["open", "high", "low", "close", "volume"]] = [
        50.0,
        55.0,
        45.0,
        52.0,
        10_000.0,
    ]
    kwargs = {
        "symbol": "AAA",
        "timeframe": "30m",
        "window_sizes": [10],
        "forward_bars": [1],
        "stride": 1,
        "max_windows_per_symbol": 1,
        "vwap_condition": "vwap_reclaim_long",
        "vwap_min_slope_bps": 0.0,
    }

    base = WindowSampler().sample(df=bars, **kwargs)
    changed = WindowSampler().sample(df=mutated, **kwargs)

    assert len(base) == len(changed) == 1
    assert base[0].features["vwap_condition_passed"] == changed[0].features["vwap_condition_passed"]
    assert base[0].features["vwap_distance_bps"] == changed[0].features["vwap_distance_bps"]


def test_discovery_run_request_accepts_vwap_fields() -> None:
    request = DiscoveryRunRequest(
        vwap_condition="vwap_reclaim_long",
        vwap_side_bias="long",
        vwap_max_distance_bps=150.0,
        vwap_min_slope_bps=0.0,
    )

    assert request.vwap_condition == "vwap_reclaim_long"
    assert request.vwap_side_bias == "long"
    assert request.vwap_max_distance_bps == 150.0
    assert request.vwap_min_slope_bps == 0.0


def test_agent_resolved_params_include_vwap_contract() -> None:
    agent = PatternDiscoveryLabAgent(provider=object(), settings=Settings())
    request = DiscoveryRunRequest(
        vwap_condition="vwap_reclaim_long",
        vwap_side_bias="long",
        vwap_max_distance_bps=150.0,
        vwap_min_slope_bps=0.0,
    )

    params = agent._resolve_params(request)

    assert params["vwap_condition"] == "vwap_reclaim_long"
    assert params["vwap_side_bias"] == "long"
    assert params["vwap_expected_side"] == "long"
    assert params["vwap_max_distance_bps"] == 150.0
    assert params["vwap_min_slope_bps"] == 0.0


def test_worker_expected_params_include_vwap_contract() -> None:
    settings = Settings()
    request = DiscoveryRunRequest(
        vwap_condition="vwap_reject_short",
        vwap_side_bias="short",
        vwap_max_distance_bps=250.0,
        vwap_min_slope_bps=0.0,
    )

    expected = worker._intraday_research_expected_params(settings, request)

    assert expected["vwap_condition"] == "vwap_reject_short"
    assert expected["vwap_side_bias"] == "short"
    assert expected["vwap_max_distance_bps"] == 250.0
    assert expected["vwap_min_slope_bps"] == 0.0


def test_vwap_signature_is_distinct_but_tracks_legacy_overlap() -> None:
    wave = ResearchWaveSpec(
        name="30m_W100_vwap_reclaim_slow",
        timeframe="30m",
        window_sizes=(100,),
        forward_bars=(8, 13, 21),
        max_total_windows=120000,
        max_windows_per_symbol=1200,
        hypothesis="explicit VWAP reclaim hypothesis",
        priority=1,
        vwap_condition="vwap_reclaim_long",
    )

    allowed, blocked = filter_prohibited_waves((wave,), ("30m W100 8,13,21",))

    assert blocked == ()
    assert allowed[0].signatures == ("30m W100 8,13,21 vwap_reclaim_long",)
    assert allowed[0].legacy_overlap is True


def _bars() -> pd.DataFrame:
    index = pd.date_range("2026-07-01 09:30", periods=18, freq="30min", tz="America/New_York")
    closes = [10, 9, 9, 9, 9, 9, 9, 9, 9, 12, 9, 9, 8.8, 9.2, 11, 8.5, 12, 11]
    rows = []
    for close in closes:
        rows.append(
            {
                "open": close,
                "high": close + 1.2,
                "low": close - 0.4,
                "close": close,
                "volume": 1000.0,
            }
        )
    return pd.DataFrame(rows, index=index)
