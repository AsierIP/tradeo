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


def test_context_filter_none_preserves_sample_count() -> None:
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
        session_filter="none",
        cost_filter="none",
    )

    assert len(explicit_none) == len(baseline)


def test_benchmark_regime_filter_accepts_only_matching_windows() -> None:
    sampler = WindowSampler()

    accepted = sampler.sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        benchmark_frames={"SPY": _benchmark_bars(up=True), "QQQ": _benchmark_bars(up=True)},
        benchmark_regime_filter="spy_qqq_positive",
    )
    rejected_sampler = WindowSampler()
    rejected = rejected_sampler.sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        benchmark_frames={"SPY": _benchmark_bars(up=False), "QQQ": _benchmark_bars(up=True)},
        benchmark_regime_filter="spy_qqq_positive",
    )

    assert accepted
    assert all(sample.features["benchmark_regime_filter"] == "spy_qqq_positive" for sample in accepted)
    assert all(sample.features["benchmark_regime_states"] == {"SPY": "positive", "QQQ": "positive"} for sample in accepted)
    assert rejected == []
    assert rejected_sampler.last_diagnostics["windows_benchmark_regime_rejected"] > 0


def test_benchmark_regime_filter_missing_benchmark_fails_closed() -> None:
    sampler = WindowSampler()

    samples = sampler.sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        benchmark_frames={"SPY": _benchmark_bars(up=True)},
        benchmark_regime_filter="spy_qqq_positive",
    )

    assert samples == []
    assert sampler.last_diagnostics["windows_benchmark_regime_missing"] > 0


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


def test_session_filter_mid_accepts_only_mid_session_samples() -> None:
    sampler = WindowSampler()

    samples = sampler.sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        session_filter="mid",
    )

    assert samples
    assert all(sample.features["session_bucket"] == "mid" for sample in samples)
    assert sampler.last_diagnostics["windows_session_rejected"] > 0


def test_session_filter_no_close_rejects_close_samples() -> None:
    samples = WindowSampler().sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        session_filter="no_close",
    )

    assert samples
    assert all(sample.features["session_bucket"] != "close" for sample in samples)


def test_low_cost_filter_accepts_and_rejects_by_execution_cost(monkeypatch) -> None:
    monkeypatch.setattr(
        WindowSampler,
        "_execution_cost_metrics_from_values",
        staticmethod(lambda **_: {"execution_cost_r": 0.14}),
    )
    accepted = WindowSampler().sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        cost_filter="low_cost",
        max_execution_cost_r=0.15,
    )

    monkeypatch.setattr(
        WindowSampler,
        "_execution_cost_metrics_from_values",
        staticmethod(lambda **_: {"execution_cost_r": 0.16}),
    )
    rejected_sampler = WindowSampler()
    rejected = rejected_sampler.sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        cost_filter="low_cost",
        max_execution_cost_r=0.15,
    )

    assert accepted
    assert rejected == []
    assert rejected_sampler.last_diagnostics["windows_cost_rejected"] > 0


def test_vwap_session_and_cost_filters_apply_before_sample_creation(monkeypatch) -> None:
    monkeypatch.setattr(
        WindowSampler,
        "_execution_cost_metrics_from_values",
        staticmethod(lambda **_: {"execution_cost_r": 0.14}),
    )
    sampler = WindowSampler()

    samples = sampler.sample(
        "AAA",
        _bars(),
        "30m",
        [10],
        [1],
        stride=1,
        max_windows_per_symbol=20,
        vwap_condition="vwap_above_rising",
        session_filter="mid",
        cost_filter="low_cost",
        max_execution_cost_r=0.15,
    )

    assert samples
    assert all(sample.features["vwap_condition_passed"] is True for sample in samples)
    assert all(sample.features["session_bucket"] == "mid" for sample in samples)
    assert all(sample.features["execution_execution_cost_r"] <= 0.15 for sample in samples)
    assert sampler.last_diagnostics["context_filters"]["windows_selected"] == len(samples)


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


def test_discovery_run_request_accepts_context_filter_fields() -> None:
    request = DiscoveryRunRequest(
        session_filter="mid",
        cost_filter="low_cost",
        max_execution_cost_r=0.15,
        benchmark_regime_filter="spy_qqq_positive",
        benchmark_symbols="QQQ,SPY",
    )

    assert request.session_filter == "mid"
    assert request.cost_filter == "low_cost"
    assert request.max_execution_cost_r == 0.15
    assert request.benchmark_regime_filter == "spy_qqq_positive"
    assert request.benchmark_symbols == "QQQ,SPY"


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


def test_agent_resolved_params_include_context_filter_contract() -> None:
    agent = PatternDiscoveryLabAgent(provider=object(), settings=Settings())
    request = DiscoveryRunRequest(
        session_filter="mid_session",
        cost_filter="low_cost",
    )

    params = agent._resolve_params(request)

    assert params["session_filter"] == "mid"
    assert params["cost_filter"] == "low_cost"
    assert params["max_execution_cost_r"] == 0.15


def test_agent_resolved_params_include_benchmark_regime_filter_contract() -> None:
    agent = PatternDiscoveryLabAgent(provider=object(), settings=Settings())
    request = DiscoveryRunRequest(
        benchmark_regime_filter="spy_qqq_positive",
        benchmark_symbols="QQQ,SPY",
    )

    params = agent._resolve_params(request)

    assert params["benchmark_regime_filter"] == "spy_qqq_positive"
    assert params["benchmark_symbols"] == ["QQQ", "SPY"]


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


def test_worker_expected_params_include_context_filter_contract() -> None:
    settings = Settings()
    request = DiscoveryRunRequest(
        session_filter="mid",
        cost_filter="low_cost",
        max_execution_cost_r=0.15,
    )

    expected = worker._intraday_research_expected_params(settings, request)

    assert expected["session_filter"] == "mid"
    assert expected["cost_filter"] == "low_cost"
    assert expected["max_execution_cost_r"] == 0.15


def test_worker_expected_params_include_benchmark_regime_filter_contract() -> None:
    settings = Settings()
    request = DiscoveryRunRequest(
        benchmark_regime_filter="spy_qqq_positive",
        benchmark_symbols="SPY,QQQ",
    )

    expected = worker._intraday_research_expected_params(settings, request)

    assert expected["benchmark_regime_filter"] == "spy_qqq_positive"
    assert expected["benchmark_symbols"] == ["SPY", "QQQ"]


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


def test_context_filter_signature_distinguishes_from_unfiltered_repeat() -> None:
    wave = ResearchWaveSpec(
        name="30m_W50_cost_regime",
        timeframe="30m",
        window_sizes=(50,),
        forward_bars=(4, 8, 13),
        max_total_windows=120000,
        max_windows_per_symbol=1200,
        hypothesis="cost/regime filtered VWAP hypothesis",
        priority=1,
        vwap_condition="vwap_above_rising",
        session_filter="mid",
        cost_filter="low_cost",
        max_execution_cost_r=0.15,
    )

    allowed, blocked = filter_prohibited_waves((wave,), ("30m W50 4,8,13 vwap_above_rising",))

    assert blocked == ()
    assert allowed[0].signatures == (
        "30m W50 4,8,13 vwap_above_rising session_mid low_cost_0.15",
    )
    assert allowed[0].legacy_overlap is False


def test_benchmark_filter_signature_distinguishes_from_vwap_repeat() -> None:
    wave = ResearchWaveSpec(
        name="1h_W100_spy_qqq_positive",
        timeframe="1h",
        window_sizes=(100,),
        forward_bars=(2, 4, 6),
        max_total_windows=80000,
        max_windows_per_symbol=800,
        hypothesis="VWAP above rising only when SPY/QQQ regime is positive",
        priority=1,
        vwap_condition="vwap_above_rising",
        benchmark_regime_filter="spy_qqq_positive",
    )

    allowed, blocked = filter_prohibited_waves((wave,), ("1h W100 2,4,6 vwap_above_rising",))

    assert blocked == ()
    assert allowed[0].signatures == (
        "1h W100 2,4,6 vwap_above_rising benchmark_spy_qqq_positive",
    )
    assert allowed[0].legacy_overlap is False


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


def _benchmark_bars(*, up: bool) -> pd.DataFrame:
    index = pd.date_range("2026-07-01 09:30", periods=18, freq="30min", tz="America/New_York")
    closes = list(range(100, 118)) if up else list(range(118, 100, -1))
    rows = [
        {
            "open": float(close),
            "high": float(close) + 0.5,
            "low": float(close) - 0.5,
            "close": float(close),
            "volume": 1000.0,
        }
        for close in closes
    ]
    return pd.DataFrame(rows, index=index)
