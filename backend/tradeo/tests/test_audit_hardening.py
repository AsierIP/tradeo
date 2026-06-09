from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from tradeo.core.config import Settings
from tradeo.research.types import ClusterCandidate
from tradeo.research.validation_gate import ValidationGate
from tradeo.services.technical_indicators import normalize_ohlcv


def test_validation_gate_never_promotes_research_metric_to_paper_candidate() -> None:
    candidate = ClusterCandidate(
        pattern_key="pattern-key",
        name="DISCOVERED_LONG_W20_C01_TEST",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        centroid=[0.0, 1.0],
        sample_count=250,
        symbol_count=12,
        year_count=4,
        score=1.2,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "rr_metrics": {"4": {"expectancy_r": 0.55, "profit_factor": 2.5}},
            "best_rr": 4.0,
            "best_expectancy_r": 0.55,
            "best_profit_factor": 2.5,
            "best_max_drawdown_r": 4.0,
            "expectancy_r": 0.55,
            "profit_factor": 2.5,
            "stability_score": 0.75,
            "out_of_sample_expectancy_r": 0.35,
            "out_of_sample_profit_factor": 1.8,
            "hit_4r_rate": 0.15,
        },
        feature_summary={},
        examples=[],
    )

    result = ValidationGate(settings=Settings()).evaluate(candidate)

    assert result.validation_passed is True
    assert result.metrics["premium_rr_passed"] is True
    assert result.metrics["promotion_status"] == "lab_candidate"
    assert result.metrics["promotion_status"] not in {"premium_candidate", "paper_candidate"}
    assert result.metrics["execution_promotion_blocked"] is True


def test_director_gate_blocks_zero_trade_promotions_and_unproven_oos_fit() -> None:
    director_gate = _load_director_gate()
    rows = {
        "catalog": [
            {
                "pattern_id": "PATTERN_1",
                "status": "paper_candidate",
                "entry_rule_plaintext": "Research entry is the close of the final bar in the detected window.",
            }
        ],
        "events": [
            {
                "pattern_id": "PATTERN_1",
                "duplicate_group_id": "DUP_1",
                "is_independent_sample": "true",
                "market_regime": "not_persisted",
                "sector": "not_persisted",
            }
        ],
        "trades": [],
        "fills": [],
        "experiments": [
            {
                "experiment_id": "EXP_1",
                "out_of_sample_start": "2025-01-01T00:00:00+00:00",
                "out_of_sample_end": "2025-12-31T00:00:00+00:00",
            }
        ],
        "metrics": [
            {
                "pattern_id": "PATTERN_1",
                "trade_count": "0",
                "independent_sample_count": "1",
                "profit_factor": "2.4",
                "expectancy": "0.5",
                "max_drawdown": "3.0",
            }
        ],
    }

    blockers, summary = director_gate.evaluate(
        rows,
        min_paper_trades_for_promotion=30,
        min_fills_for_promotion=30,
        max_duplicate_event_share=0.0,
    )

    assert summary["director_gate"] == "blocked"
    assert any("paper_trades.csv has zero rows" in blocker for blocker in blockers)
    assert any("promoted statuses require linked paper trades" in blocker for blocker in blockers)
    assert any("research R metrics are populated" in blocker for blocker in blockers)
    assert any("anti-lookahead cutoff columns" in blocker for blocker in blockers)
    assert any("train-only fit evidence" in blocker for blocker in blockers)


def test_export_filters_fills_to_exported_paper_trade_ids() -> None:
    exporter = _load_audit_exporter()
    overview = {
        "trades": [
            {
                "id": 1,
                "symbol": "AAA",
                "side": "long",
                "qty": 1,
                "entry": 10.0,
                "opened_at": "2026-06-09T10:00:00+00:00",
                "status": "open",
                "metadata_json": {"execution_mode": "paper"},
            },
            {
                "id": 2,
                "symbol": "BBB",
                "side": "long",
                "qty": 1,
                "entry": 20.0,
                "opened_at": "2026-06-09T10:00:00+00:00",
                "status": "open",
                "metadata_json": {"execution_mode": "paper"},
            },
        ]
    }

    fills = exporter.build_ib_fills(overview, exported_trade_ids={"2"})

    assert [row["trade_id"] for row in fills] == ["2"]
    assert fills[0]["ticker"] == "BBB"


def test_normalize_ohlcv_rejects_invalid_market_bars() -> None:
    df = pd.DataFrame(
        {
            "open": [10.0],
            "high": [9.0],
            "low": [8.0],
            "close": [10.5],
            "volume": [1000.0],
        },
        index=pd.date_range("2026-01-01", periods=1, freq="D"),
    )

    with pytest.raises(ValueError, match="high must be greater"):
        normalize_ohlcv(df)


def test_normalize_ohlcv_rejects_duplicate_timestamps() -> None:
    idx = pd.to_datetime(["2026-01-01", "2026-01-01"])
    df = pd.DataFrame(
        {
            "open": [10.0, 11.0],
            "high": [11.0, 12.0],
            "low": [9.0, 10.0],
            "close": [10.5, 11.5],
            "volume": [1000.0, 1200.0],
        },
        index=idx,
    )

    with pytest.raises(ValueError, match="duplicate timestamps"):
        normalize_ohlcv(df)


def _load_director_gate():
    path = _repo_root() / "research" / "audit_bridge" / "director_gate.py"
    spec = importlib.util.spec_from_file_location("director_gate", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_audit_exporter():
    path = _repo_root() / "research" / "audit_bridge" / "export_audit_package.py"
    spec = importlib.util.spec_from_file_location("export_audit_package", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "research" / "audit_bridge").exists():
            return parent
    raise AssertionError("could not locate repo root")
