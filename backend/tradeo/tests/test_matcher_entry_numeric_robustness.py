from __future__ import annotations

from datetime import timedelta

import numpy as np
import pandas as pd

from tradeo.core.config import Settings
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.services.entry_variants import _timeframe_delta, build_entry_variants
from tradeo.services.opportunity_ranking import rank_entry_matches
from tradeo.services.signal_quality import build_entry_quality


class _Risk:
    approved = True
    risk_usd = 10.0
    suggested_qty = 1
    notional_usd = 10.0
    reason = ""
    warnings: list[str] = []


def _settings(**overrides) -> Settings:
    defaults = {
        "min_avg_dollar_volume": 0,
        "max_atr_pct": 1.0,
        "entry_min_quality_score": 0.0,
        "artifacts_dir": "/tmp/tradeo-test-artifacts",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_non_finite_rank_and_quality_inputs_do_not_score_as_perfect() -> None:
    settings = _settings()
    match = {
        "symbol": "NANX",
        "pattern_name": "nan_pattern",
        "side": "long",
        "timeframe": "1d",
        "similarity": float("nan"),
        "score": 0.2,
        "entry_score": float("nan"),
        "reward_risk": 4.0,
        "regime_fit": {"score": float("nan")},
        "metrics": {
            "pattern_expectancy_r": float("nan"),
            "pattern_profit_factor": float("inf"),
            "pattern_stability_score": float("nan"),
            "features": {"avg_dollar_volume": float("nan")},
            "entry_gate": {
                "passed": True,
                "trigger": "breakout",
                "entry_score": float("nan"),
                "volume_ratio": float("nan"),
                "extension_atr": float("nan"),
                "regime_ok": True,
            },
        },
    }

    ranked = rank_entry_matches([match], settings=settings)[0]
    rank_components = ranked["opportunity_rank_components"]
    quality = build_entry_quality(
        match=match,
        risk=_Risk(),
        settings=settings,
        execution_requested=False,
    )

    assert rank_components["similarity"] == 0.0
    assert rank_components["entry"] == 0.2
    assert rank_components["research_edge"] == 0.0
    assert quality["components"]["similarity"] == 0.0
    assert quality["components"]["entry"] == 0.2
    assert quality["score"] < 0.60


def test_entry_variants_reject_non_finite_ohlc_and_parse_intraday_aliases() -> None:
    settings = _settings(entry_gate_enabled=False)
    index = pd.date_range("2026-06-10 14:00:00+00:00", periods=22, freq="15min")
    df = pd.DataFrame(
        {
            "open": [10.0] * 22,
            "high": [10.5] * 22,
            "low": [9.5] * 22,
            "close": [10.0] * 21 + [float("nan")],
            "volume": [100_000] * 22,
        },
        index=index,
    )

    variants = build_entry_variants(
        side="long",
        df=df,
        base_entry_gate={
            "passed": True,
            "trigger": "breakout",
            "entry_score": 0.8,
            "volume_ratio": 2.0,
        },
        score=0.8,
        reward_risk=4.0,
        settings=settings,
    )

    assert variants == []
    assert _timeframe_delta("15 mins") == timedelta(minutes=15)
    assert _timeframe_delta("1 min") == timedelta(minutes=1)
    assert _timeframe_delta("2 hours") == timedelta(hours=2)


def test_matcher_rejects_non_finite_scaler_and_vector_inputs() -> None:
    vector = np.asarray([1.0, float("nan")], dtype=float)
    centroid = np.asarray([1.0, 2.0], dtype=float)
    mean = np.asarray([0.0, 1.0], dtype=float)
    scale = np.asarray([1.0, 2.0], dtype=float)

    assert NovelPatternMatcher._scaled_vector_for_pattern(vector, centroid, mean, scale) is None
    assert (
        NovelPatternMatcher._scaled_vector_for_pattern(
            np.asarray([1.0, 2.0], dtype=float),
            np.asarray([1.0, float("inf")], dtype=float),
            mean,
            scale,
        )
        is None
    )


def test_entry_gate_blocks_non_finite_market_data() -> None:
    settings = _settings(entry_gate_enabled=True)
    index = pd.date_range("2026-06-01", periods=55, freq="1D")
    df = pd.DataFrame(
        {
            "open": [10.0] * 55,
            "high": [10.5] * 55,
            "low": [9.5] * 55,
            "close": [10.0] * 54 + [float("nan")],
            "volume": [100_000] * 55,
        },
        index=index,
    )

    gate = NovelPatternMatcher._entry_gate("long", df, score=0.8, settings=settings)

    assert gate["passed"] is False
    assert gate["trigger"] == "invalid_market_data"
    assert gate["rejection_reasons"] == ["non_finite_market_data"]
