from __future__ import annotations

import csv
import importlib.util
import json
import sys
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
    assert summary["by_regime"]["available"] is False
    assert "metrics_by_regime.csv" in summary["by_regime"]["empty_reason"]
    assert summary["by_entry_variant"]["available"] is False
    assert summary["actionable_recommendations"][0]["action"] == "keep_all_patterns_research_only"
    assert summary["pattern_recommendations"][0]["trades_remaining_for_promotion"] == 30
    assert any(
        "entry_variant performance unavailable" in action
        for action in summary["pattern_recommendations"][0]["actions"]
    )


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


def test_export_leaves_operational_metrics_empty_without_closed_lab_trades() -> None:
    exporter = _load_audit_exporter()
    patterns = [
        {
            "id": 1,
            "sample_count": 120,
            "symbol_count": 10,
            "best_win_rate": 0.62,
            "best_profit_factor": 2.4,
            "best_expectancy_r": 0.5,
            "best_max_drawdown_r": 3.0,
            "rr_metrics_json": {"4": {"avg_win_r": 2.0, "avg_loss_r": 1.0, "median_result_r": 0.5}},
            "best_rr": 4.0,
        }
    ]

    rows = exporter.build_metrics_by_pattern(patterns, {1: []}, [])
    regime_rows = exporter.build_metrics_by_regime(patterns, [], [])
    variant_rows = exporter.build_metrics_by_entry_variant(patterns, [])

    assert rows[0]["trade_count"] == 0
    assert rows[0]["winrate"] == ""
    assert rows[0]["profit_factor"] == ""
    assert rows[0]["expectancy"] == ""
    assert rows[0]["max_drawdown"] == ""
    assert "No closed_lab_trades" in rows[0]["notes"]
    assert regime_rows[0]["analysis_available"] == "false"
    assert "no_closed_lab_trades" in regime_rows[0]["empty_reason"]
    assert variant_rows[0]["analysis_available"] == "false"
    assert "entry_variant_id" in variant_rows[0]["empty_reason"]


def test_export_groups_closed_lab_trade_performance_by_regime_and_entry_variant() -> None:
    exporter = _load_audit_exporter()
    patterns = [{"id": 1}]
    trades = [
        {
            "pattern_id": "PATTERN_000001",
            "gross_pnl": "10",
            "net_pnl": "9",
            "r_multiple": "1.0",
            "entry_fill_time": "2026-06-09T10:00:00+00:00",
            "notes": "entry_variant=next_bar_limit_retest; regime=market_up; execution_mode=paper",
        },
        {
            "pattern_id": "PATTERN_000001",
            "gross_pnl": "-5",
            "net_pnl": "-5",
            "r_multiple": "-0.5",
            "entry_fill_time": "2026-06-10T10:00:00+00:00",
            "notes": "entry_variant=momentum_close; regime=market_down; execution_mode=paper",
        },
    ]
    events = [
        {"pattern_id": "PATTERN_000001", "market_regime": "market_up"},
        {"pattern_id": "PATTERN_000001", "market_regime": "market_down"},
    ]

    regime_rows = exporter.build_metrics_by_regime(patterns, events, trades)
    variant_rows = exporter.build_metrics_by_entry_variant(patterns, trades)

    up = next(row for row in regime_rows if row["market_regime"] == "market_up")
    retest = next(row for row in variant_rows if row["entry_variant_id"] == "next_bar_limit_retest")
    assert up["analysis_available"] == "true"
    assert up["trade_count"] == 1
    assert up["expectancy_r"] == 1.0
    assert retest["net_pnl"] == 9.0
    assert retest["profit_factor"] == 9.0


def test_audit_validator_accepts_manifest_gate_buckets_and_reported_duplicates(tmp_path: Path) -> None:
    validator = _load_audit_validator()
    package = _write_minimal_audit_package(tmp_path, validator, duplicate_repeated_rows=2)

    errors, _ = validator.validate_package(package)

    assert errors == []


def test_audit_validator_rejects_orphan_fills_and_empty_bucket_without_reason(tmp_path: Path) -> None:
    validator = _load_audit_validator()
    package = _write_minimal_audit_package(tmp_path, validator, duplicate_repeated_rows=2)
    _write_csv(
        package / "ib_fills.csv",
        validator.CSV_COLUMNS["ib_fills.csv"],
        [
            {
                "fill_id_hash": "fill_hash",
                "trade_id": "MISSING",
                "order_id_hash": "12345",
                "ib_execution_time": "2026-06-09T10:01:00+00:00",
                "timezone": "UTC",
                "ticker": "AAA",
                "side": "long",
                "quantity": "1",
                "price": "10",
                "commission": "1",
                "liquidity_flag": "",
                "exchange": "SMART/IBKR",
                "order_type": "limit",
                "account_id_redacted": "false",
                "raw_status": "closed",
                "notes": "",
            }
        ],
    )
    _write_csv(
        package / "metrics_by_regime.csv",
        validator.CSV_COLUMNS["metrics_by_regime.csv"],
        [{"analysis_available": "false", "empty_reason": ""}],
    )

    errors, _ = validator.validate_package(package)

    assert any("unknown trade_id MISSING" in error for error in errors)
    assert any("order_id_hash appears to contain raw numeric order id" in error for error in errors)
    assert any("account_id_redacted must be true" in error for error in errors)
    assert any("metrics_by_regime.csv: empty breakdown requires non-empty empty_reason" in error for error in errors)


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


def test_audit_runner_parses_compose_ps_json_without_container_name_dependency() -> None:
    runner = _load_audit_runner()
    stdout = "\n".join(
        [
            json.dumps(
                {
                    "Name": "tradeo-backend-1",
                    "Service": "backend",
                    "State": "running",
                    "Health": "healthy",
                }
            ),
            json.dumps(
                {
                    "Name": "tradeo-worker-1",
                    "Service": "worker",
                    "State": "running",
                    "Status": "Up 10 minutes (healthy)",
                }
            ),
        ]
    )

    services = runner.parse_compose_ps_json(stdout)

    assert [service["service"] for service in services] == ["backend", "worker"]
    assert [service["health"] for service in services] == ["healthy", "healthy"]


def test_audit_runner_ignores_nonblocking_compose_ps_failures() -> None:
    runner = _load_audit_runner()

    review = runner.deterministic_review(
        "TEST_AUDIT",
        "manual",
        {"status": "passed", "blockers": []},
        [runner.CommandRun("docker_compose_ps", ["docker", "compose", "ps"], 1, blocking=False)],
    )

    assert review["failed_commands"] == []
    assert review["priority"] == "P2"


def test_audit_runner_writes_artifacts_when_gate_command_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _load_audit_runner()
    requests = tmp_path / "requests"
    monkeypatch.setattr(runner, "REQUESTS", requests)
    monkeypatch.setattr(
        runner,
        "collect_compose_status",
        lambda: (
            runner.CommandRun("docker_compose_ps", ["docker", "compose", "ps"], 1, blocking=False),
            {"available": False, "reason": "docker_compose_ps_unavailable"},
        ),
    )

    def raise_from_gate(*_args, **_kwargs):
        raise RuntimeError("gate exploded")

    monkeypatch.setattr(runner, "run_subprocess", raise_from_gate)
    monkeypatch.setattr(
        runner.sys,
        "argv",
        [
            "run_director_audit.py",
            "--cadence",
            "manual",
            "--audit-id",
            "TEST_AUDIT",
            "--skip-export",
        ],
    )

    exit_code = runner.main()

    run_json = requests / "TEST_AUDIT" / "director_audit_run.json"
    review_json = requests / "TEST_AUDIT" / "internal_auditor_agent_review.json"
    assert exit_code == 1
    assert run_json.exists()
    assert review_json.exists()
    payload = json.loads(run_json.read_text(encoding="utf-8"))
    assert payload["director_gate_status"] == "runner_error"
    assert payload["commands"][-1]["name"] == "runner_error"
    assert payload["artifact_paths"]["run_json"].endswith("director_audit_run.json")


def _write_minimal_audit_package(tmp_path: Path, validator, *, duplicate_repeated_rows: int) -> Path:
    bridge = tmp_path / "research" / "audit_bridge"
    package = bridge / "requests" / "TEST_AUDIT"
    (package / "config_snapshot").mkdir(parents=True)
    for rel in validator.REQUIRED_BRIDGE_FILES:
        (bridge / rel).parent.mkdir(parents=True, exist_ok=True)
        (bridge / rel).write_text("ok\n", encoding="utf-8")
    for rel in validator.REQUIRED_FILES:
        path = package / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".csv") or rel in {"manifest.json", "director_gate_result.json"}:
            continue
        if rel.endswith(".json"):
            path.write_text(json.dumps({"redacted": True}), encoding="utf-8")
        else:
            path.write_text("ok\n", encoding="utf-8")

    pattern = {
        "pattern_id": "PATTERN_000001",
        "pattern_name": "TEST_PATTERN",
        "pattern_version": "run_1",
        "description": "test",
        "hypothesis": "test",
        "detection_rule_plaintext": "test",
        "entry_rule_plaintext": "test",
        "exit_rule_plaintext": "test",
        "stop_rule_plaintext": "test",
        "take_profit_rule_plaintext": "test",
        "time_stop_rule_plaintext": "test",
        "timeframe": "1d",
        "asset_class": "US equities",
        "universe": "test",
        "session_filter": "regular",
        "min_volume_filter": "0",
        "min_price_filter": "0",
        "uses_fundamental_data": "false",
        "uses_news_data": "false",
        "uses_options_data": "false",
        "uses_future_data": "false",
        "known_risks": "",
        "status": "lab_candidate",
        "created_at": "2026-06-09T00:00:00+00:00",
        "first_seen": "2026-06-09T00:00:00+00:00",
        "last_seen": "2026-06-10T00:00:00+00:00",
    }
    events = [
        {
            "event_id": "EVT_1",
            "pattern_id": "PATTERN_000001",
            "detected_at": "2026-06-09T00:00:00+00:00",
            "market_timestamp": "2026-06-09T00:00:00+00:00",
            "timezone": "UTC",
            "ticker": "AAA",
            "exchange": "SMART/IBKR",
            "timeframe": "1d",
            "bar_open_time": "2026-06-09T00:00:00+00:00",
            "bar_close_time": "2026-06-09T00:00:00+00:00",
            "signal_price": "10",
            "bid_at_signal": "",
            "ask_at_signal": "",
            "spread_at_signal": "",
            "volume_at_signal": "",
            "atr_at_signal": "",
            "volatility_context": "",
            "market_regime": "market_up",
            "sector": "sector_strong",
            "was_trade_triggered": "true",
            "trade_id": "T1",
            "reason_not_traded": "",
            "duplicate_group_id": "DUP_1",
            "is_independent_sample": "true",
            "data_available_at_signal": "true",
            "features_used_json": "{}",
            "notes": "",
        },
        {
            "event_id": "EVT_2",
            "pattern_id": "PATTERN_000001",
            "detected_at": "2026-06-10T00:00:00+00:00",
            "market_timestamp": "2026-06-10T00:00:00+00:00",
            "timezone": "UTC",
            "ticker": "AAA",
            "exchange": "SMART/IBKR",
            "timeframe": "1d",
            "bar_open_time": "2026-06-10T00:00:00+00:00",
            "bar_close_time": "2026-06-10T00:00:00+00:00",
            "signal_price": "10",
            "bid_at_signal": "",
            "ask_at_signal": "",
            "spread_at_signal": "",
            "volume_at_signal": "",
            "atr_at_signal": "",
            "volatility_context": "",
            "market_regime": "market_up",
            "sector": "sector_strong",
            "was_trade_triggered": "false",
            "trade_id": "",
            "reason_not_traded": "",
            "duplicate_group_id": "DUP_1",
            "is_independent_sample": "true",
            "data_available_at_signal": "true",
            "features_used_json": "{}",
            "notes": "",
        },
    ]
    trade = {
        "trade_id": "T1",
        "event_id": "EVT_1",
        "pattern_id": "PATTERN_000001",
        "ticker": "AAA",
        "side": "long",
        "quantity": "1",
        "entry_signal_time": "2026-06-09T10:00:00+00:00",
        "entry_order_time": "2026-06-09T10:00:00+00:00",
        "entry_fill_time": "2026-06-09T10:01:00+00:00",
        "entry_signal_price": "10",
        "entry_order_type": "limit",
        "entry_limit_price": "10",
        "entry_fill_price": "10",
        "exit_signal_time": "2026-06-09T11:00:00+00:00",
        "exit_order_time": "2026-06-09T11:00:00+00:00",
        "exit_fill_time": "2026-06-09T11:01:00+00:00",
        "exit_order_type": "limit",
        "exit_limit_price": "12",
        "exit_fill_price": "12",
        "exit_reason": "target",
        "gross_pnl": "10",
        "commission": "1",
        "estimated_spread_cost": "1",
        "estimated_slippage": "1",
        "other_fees": "0",
        "net_pnl": "7",
        "return_pct": "0.7",
        "mae": "",
        "mfe": "",
        "holding_period_seconds": "3600",
        "risk_amount": "10",
        "r_multiple": "1",
        "account_equity_snapshot": "",
        "position_size_method": "test",
        "notes": "entry_variant=next_bar_limit_retest; regime=market_up; execution_mode=paper",
    }
    fill = {
        "fill_id_hash": "fill_hash",
        "trade_id": "T1",
        "order_id_hash": "hash_order",
        "ib_execution_time": "2026-06-09T10:01:00+00:00",
        "timezone": "UTC",
        "ticker": "AAA",
        "side": "long",
        "quantity": "1",
        "price": "10",
        "commission": "1",
        "liquidity_flag": "",
        "exchange": "SMART/IBKR",
        "order_type": "limit",
        "account_id_redacted": "true",
        "raw_status": "closed",
        "notes": "",
    }
    experiment = {
        "experiment_id": "EXP_1",
        "pattern_id": "PATTERN_000001",
        "variant_id": "RR_4",
        "created_at": "2026-06-09T00:00:00+00:00",
        "tested_at": "2026-06-09T00:00:00+00:00",
        "status": "active",
        "reason_status": "",
        "parameters_json": "{}",
        "dataset_start": "2026-06-09T00:00:00+00:00",
        "dataset_end": "2026-06-10T00:00:00+00:00",
        "in_sample_start": "2026-06-09T00:00:00+00:00",
        "in_sample_end": "2026-06-09T00:00:00+00:00",
        "out_of_sample_start": "2026-06-10T00:00:00+00:00",
        "out_of_sample_end": "2026-06-10T00:00:00+00:00",
        "paper_live_start": "2026-06-09T10:00:00+00:00",
        "paper_live_end": "2026-06-09T11:00:00+00:00",
        "number_of_assets_tested": "1",
        "number_of_events": "2",
        "number_of_trades": "1",
        "gross_pnl": "10",
        "net_pnl": "7",
        "winrate": "1",
        "profit_factor": "7",
        "sharpe": "",
        "sortino": "",
        "max_drawdown": "0",
        "notes": "",
    }
    metric = {
        "pattern_id": "PATTERN_000001",
        "sample_count": "2",
        "independent_sample_count": "2",
        "trade_count": "1",
        "ticker_count": "1",
        "sector_count": "1",
        "first_seen": "2026-06-09T00:00:00+00:00",
        "last_seen": "2026-06-10T00:00:00+00:00",
        "gross_pnl": "10",
        "net_pnl": "7",
        "avg_trade": "7",
        "median_trade": "7",
        "std_trade": "",
        "winrate": "1",
        "avg_win": "7",
        "avg_loss": "",
        "payoff_ratio": "",
        "profit_factor": "7",
        "expectancy": "1",
        "max_drawdown": "0",
        "max_consecutive_losses": "0",
        "best_trade": "7",
        "worst_trade": "7",
        "top_5_trades_pnl": "7",
        "bottom_5_trades_pnl": "7",
        "pnl_without_best_trade": "0",
        "pnl_without_top_5_trades": "0",
        "pnl_without_worst_trade": "0",
        "sharpe": "",
        "sortino": "",
        "calmar": "",
        "avg_holding_period_seconds": "3600",
        "notes": "",
    }
    ticker_metric = {
        "pattern_id": "PATTERN_000001",
        "ticker": "AAA",
        "trade_count": "1",
        "event_count": "2",
        "net_pnl": "7",
        "winrate": "1",
        "profit_factor": "7",
        "avg_trade": "7",
        "max_drawdown": "0",
        "first_seen": "2026-06-09T00:00:00+00:00",
        "last_seen": "2026-06-10T00:00:00+00:00",
        "notes": "",
    }
    period_metric = {
        "period_start": "2026-06-09T00:00:00+00:00",
        "period_end": "2026-06-09T00:00:00+00:00",
        "period_type": "day",
        "pattern_id": "PATTERN_000001",
        "event_count": "2",
        "trade_count": "1",
        "gross_pnl": "10",
        "net_pnl": "7",
        "winrate": "1",
        "profit_factor": "7",
        "max_drawdown": "0",
        "market_regime": "market_up",
        "notes": "",
    }
    regime_metric = {
        "pattern_id": "PATTERN_000001",
        "market_regime": "market_up",
        "analysis_available": "true",
        "empty_reason": "",
        "trade_count": "1",
        "event_count": "2",
        "gross_pnl": "10",
        "net_pnl": "7",
        "avg_trade": "7",
        "expectancy_r": "1",
        "winrate": "1",
        "profit_factor": "7",
        "max_drawdown": "0",
        "best_trade": "7",
        "worst_trade": "7",
        "first_seen": "2026-06-09T10:00:00+00:00",
        "last_seen": "2026-06-09T11:00:00+00:00",
        "notes": "",
    }
    variant_metric = dict(regime_metric)
    variant_metric.pop("market_regime")
    variant_metric["entry_variant_id"] = "next_bar_limit_retest"

    _write_csv(package / "pattern_catalog.csv", validator.CSV_COLUMNS["pattern_catalog.csv"], [pattern])
    _write_csv(package / "pattern_events.csv", validator.CSV_COLUMNS["pattern_events.csv"], events)
    _write_csv(package / "paper_trades.csv", validator.CSV_COLUMNS["paper_trades.csv"], [trade])
    _write_csv(package / "ib_fills.csv", validator.CSV_COLUMNS["ib_fills.csv"], [fill])
    _write_csv(package / "experiment_registry.csv", validator.CSV_COLUMNS["experiment_registry.csv"], [experiment])
    _write_csv(package / "metrics_by_pattern.csv", validator.CSV_COLUMNS["metrics_by_pattern.csv"], [metric])
    _write_csv(package / "metrics_by_ticker.csv", validator.CSV_COLUMNS["metrics_by_ticker.csv"], [ticker_metric])
    _write_csv(package / "metrics_by_period.csv", validator.CSV_COLUMNS["metrics_by_period.csv"], [period_metric])
    _write_csv(package / "metrics_by_regime.csv", validator.CSV_COLUMNS["metrics_by_regime.csv"], [regime_metric])
    _write_csv(package / "metrics_by_entry_variant.csv", validator.CSV_COLUMNS["metrics_by_entry_variant.csv"], [variant_metric])

    manifest_paths = sorted(set(validator.REQUIRED_FILES) - {"director_gate_result.json"})
    manifest = {
        "audit_id": "TEST_AUDIT",
        "created_at": "2026-06-09T00:00:00+00:00",
        "created_by": "test",
        "repo_commit": "abc",
        "repo_branch": "main",
        "patterns_detected": 1,
        "total_pattern_events": 2,
        "total_paper_trades": 1,
        "total_ib_fills": 1,
        "total_experiment_variants": 1,
        "total_metrics_by_regime_rows": 1,
        "total_metrics_by_entry_variant_rows": 1,
        "duplicate_event_groups": 1 if duplicate_repeated_rows else 0,
        "duplicate_repeated_rows": duplicate_repeated_rows,
        "metric_breakdowns": {
            "by_regime": {"available": True, "rows": 1, "empty_reason": ""},
            "by_entry_variant": {"available": True, "rows": 1, "empty_reason": ""},
        },
        "director_gate_required": True,
        "contains_sensitive_data": False,
        "account_ids_redacted": True,
        "orders_anonymized": True,
        "files": [{"path": rel, "description": "test"} for rel in manifest_paths],
    }
    (package / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    gate = {
        "status": "blocked",
        "summary": {
            "director_gate": "blocked",
            "by_regime": {"available": True, "buckets": [{"pattern_id": "PATTERN_000001"}], "empty_reason": ""},
            "by_entry_variant": {"available": True, "buckets": [{"pattern_id": "PATTERN_000001"}], "empty_reason": ""},
        },
    }
    (package / "director_gate_result.json").write_text(json.dumps(gate), encoding="utf-8")
    return package


def _write_csv(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


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


def _load_audit_validator():
    path = _repo_root() / "research" / "audit_bridge" / "validate_audit_package.py"
    spec = importlib.util.spec_from_file_location("validate_audit_package", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_audit_runner():
    path = _repo_root() / "research" / "audit_bridge" / "run_director_audit.py"
    spec = importlib.util.spec_from_file_location("run_director_audit", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "research" / "audit_bridge").exists():
            return parent
    raise AssertionError("could not locate repo root")
