from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

from tradeo.modules.daily_swing.gap_backtest_matrix import default_gap_backtest_matrix, write_gap_backtest_matrix
from tradeo.modules.daily_swing.gap_matrix_dry_run import (
    GapDryRunConfig,
    GapDryRunInvalidMatrix,
    GapMatrixDryRunError,
    _select_events,
    run_gap_matrix_dry_run,
)


def test_gap_matrix_dry_run_requires_cache_only(tmp_path: Path) -> None:
    config = _config(tmp_path, cache_only=False)

    with pytest.raises(GapMatrixDryRunError, match="cache-only"):
        run_gap_matrix_dry_run(config)


def test_gap_matrix_dry_run_blocks_ibkr(tmp_path: Path) -> None:
    config = _config(tmp_path, no_ibkr=False)

    with pytest.raises(GapMatrixDryRunError, match="IBKR"):
        run_gap_matrix_dry_run(config)


def test_gap_matrix_dry_run_blocks_orders_preview_signals(tmp_path: Path) -> None:
    config = _config(tmp_path, no_orders=False)

    with pytest.raises(GapMatrixDryRunError, match="order"):
        run_gap_matrix_dry_run(config)


def test_gap_matrix_dry_run_rejects_invalid_matrix(tmp_path: Path) -> None:
    rows = default_gap_backtest_matrix()
    rows[0] = replace(rows[0], execution_allowed=True)
    write_gap_backtest_matrix(rows, tmp_path / "bad_matrix")
    config = _config(tmp_path, matrix_path=tmp_path / "bad_matrix" / "dss_gap_003_backtest_matrix.json")

    with pytest.raises(GapDryRunInvalidMatrix):
        run_gap_matrix_dry_run(config)


def test_gap_matrix_dry_run_same_day_uses_open_known_fields_only(tmp_path: Path) -> None:
    result = run_gap_matrix_dry_run(_config(tmp_path))

    assert result.no_lookahead_status == "GAP_DRY_RUN_NO_LOOKAHEAD_PASS"


def test_gap_matrix_dry_run_liquidity_filter_needs_previous_volume(tmp_path: Path) -> None:
    row = next(
        row
        for row in default_gap_backtest_matrix()
        if row.liquidity_filter == "volume_t_minus_1_gte_predefined_threshold"
    )
    ledger = [
        {
            "symbol": "AAA",
            "date": "2025-03-04",
            "open_to_close_return": "0.01",
            "next_open_to_close_return": "0.01",
            "is_stock_operational": "True",
            "product_class": "STK",
            "data_quality_status": "DATA_OK",
            "gap_direction": "up",
            "abs_gap_pct": "0.03",
            "gap_vs_atr_prev": "1.5",
            "volume": "999999999",
        }
    ]

    assert _select_events(row, ledger) == []


def test_gap_matrix_dry_run_next_day_uses_after_close_decision(tmp_path: Path) -> None:
    result = run_gap_matrix_dry_run(_config(tmp_path))

    assert "GAP_REVERSAL_NEXT_DAY" in result.families


def test_gap_matrix_dry_run_outputs_no_candidate_approval(tmp_path: Path) -> None:
    result = run_gap_matrix_dry_run(_config(tmp_path))

    assert result.safety["no_candidate_approval"] is True


def test_gap_matrix_dry_run_applies_cost_x2_and_slippage(tmp_path: Path) -> None:
    result = run_gap_matrix_dry_run(_config(tmp_path))
    by_test = Path(result.runtime_paths["by_test"]).read_text(encoding="utf-8")

    assert "expectancy_net_x2" in by_test
    assert "open_slippage_adverse_25bps" in by_test


def test_gap_matrix_dry_run_baselines_and_placebos_present(tmp_path: Path) -> None:
    result = run_gap_matrix_dry_run(_config(tmp_path))
    summary = Path(result.runtime_paths["summary"]).read_text(encoding="utf-8")

    assert "MATCHED_NON_GAP" in summary
    assert "SIGN_INVERTED_GAP" in summary


def test_gap_matrix_dry_run_no_best_threshold_selected(tmp_path: Path) -> None:
    result = run_gap_matrix_dry_run(_config(tmp_path))

    assert result.safety["no_best_threshold_selected"] is True


def _config(
    tmp_path: Path,
    *,
    matrix_path: Path | None = None,
    cache_only: bool = True,
    no_ibkr: bool = True,
    no_orders: bool = True,
) -> GapDryRunConfig:
    paths = _matrix(tmp_path)
    return GapDryRunConfig(
        ledger_path=_ledger(tmp_path),
        matrix_path=matrix_path or paths["json"],
        output_dir=tmp_path / "runtime",
        cache_only=cache_only,
        no_ibkr=no_ibkr,
        no_signals=True,
        no_preview=True,
        no_orders=no_orders,
    )


def _matrix(tmp_path: Path) -> dict[str, Path]:
    out = tmp_path / "matrix"
    if not (out / "dss_gap_003_backtest_matrix.json").exists():
        write_gap_backtest_matrix(default_gap_backtest_matrix(), out)
    return {"json": out / "dss_gap_003_backtest_matrix.json"}


def _ledger(tmp_path: Path) -> Path:
    path = tmp_path / "ledger.csv"
    if path.exists():
        return path
    fields = [
        "symbol",
        "date",
        "open",
        "close",
        "volume",
        "gap_pct",
        "abs_gap_pct",
        "gap_vs_atr_prev",
        "gap_direction",
        "benchmark_spy_return_20d",
        "atr14_pct_prev",
        "open_to_close_return",
        "next_open_to_close_return",
        "is_stock_operational",
        "product_class",
        "data_quality_status",
        "event_quality_status",
    ]
    rows = [
        ["AAA", "2024-01-03", "10", "10.2", "200000", "0.012", "0.012", "0.8", "up", "0.01", "0.02", "0.02", "0.01", "True", "STK", "DATA_OK", "GAP_EVENT_READY"],
        ["BBB", "2025-03-04", "20", "19.8", "220000", "-0.015", "0.015", "-0.9", "down", "-0.01", "0.03", "-0.01", "0.02", "True", "STK", "DATA_OK", "GAP_EVENT_READY"],
        ["CCC", "2026-02-05", "30", "30.3", "150000", "0.021", "0.021", "1.2", "up", "0.02", "0.01", "0.01", "-0.01", "True", "STK", "DATA_OK", "GAP_EVENT_READY"],
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)
    return path
