from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tradeo.modules.daily_swing.gap_confirmatory_run import (
    GapConfirmatoryRunConfig,
    GapConfirmatoryRunError,
    run_gap_confirmatory_matrix,
)

MATRIX_PATH = Path("research/daily_swing/gap/dss_gap_006_confirmatory_matrix.json")
CRITERIA_PATH = Path("research/daily_swing/gap/DSS_GAP_006_CONFIRMATION_CRITERIA.json")


def test_gap_confirmatory_run_requires_cache_only(tmp_path: Path) -> None:
    with pytest.raises(GapConfirmatoryRunError, match="cache-only"):
        run_gap_confirmatory_matrix(_config(tmp_path, cache_only=False))


def test_gap_confirmatory_run_blocks_ibkr(tmp_path: Path) -> None:
    with pytest.raises(GapConfirmatoryRunError, match="IBKR"):
        run_gap_confirmatory_matrix(_config(tmp_path, no_ibkr=False))


def test_gap_confirmatory_run_blocks_orders_preview_signals(tmp_path: Path) -> None:
    with pytest.raises(GapConfirmatoryRunError, match="order"):
        run_gap_confirmatory_matrix(_config(tmp_path, no_orders=False))


def test_gap_confirmatory_run_uses_only_gap006_matrix(tmp_path: Path) -> None:
    result = run_gap_confirmatory_matrix(_config(tmp_path))

    assert result.matrix_rows == 12
    assert result.input_integrity_decision == "CONFIRMATORY_INPUT_PASS"


def test_gap_confirmatory_run_outputs_no_candidate_approval(tmp_path: Path) -> None:
    result = run_gap_confirmatory_matrix(_config(tmp_path))
    summary = Path(result.runtime_paths["summary"]).read_text(encoding="utf-8")

    assert result.safety["no_candidate_approval"] is True
    assert "candidate_approval" in summary


def test_gap_confirmatory_run_rejects_paper_live_flags(tmp_path: Path) -> None:
    result = run_gap_confirmatory_matrix(_config(tmp_path))

    assert result.safety["no_paper"] is True
    assert result.safety["no_live"] is True


def test_gap_confirmatory_run_applies_slippage_50bps(tmp_path: Path) -> None:
    result = run_gap_confirmatory_matrix(_config(tmp_path))
    by_test = Path(result.runtime_paths["by_test"]).read_text(encoding="utf-8")

    assert "open_slippage_50bps_expectancy" in by_test


def test_gap_confirmatory_run_reports_earnings_unknown(tmp_path: Path) -> None:
    result = run_gap_confirmatory_matrix(_config(tmp_path))
    by_test = Path(result.runtime_paths["by_test"]).read_text(encoding="utf-8")

    assert "GAP006_EARNINGS_SENSITIVITY_PAIR" in by_test
    assert "earnings_unknown" in by_test


def test_gap_confirmatory_run_fails_if_open_slippage_negative(tmp_path: Path) -> None:
    result = run_gap_confirmatory_matrix(_config(tmp_path))

    assert result.decision == "GAP_CONFIRMATION_FAIL_OPEN_SLIPPAGE"


def test_gap_confirmatory_run_decision_not_candidate_terms(tmp_path: Path) -> None:
    result = run_gap_confirmatory_matrix(_config(tmp_path))

    assert "candidate" not in result.decision.lower()


def _config(
    tmp_path: Path,
    *,
    cache_only: bool = True,
    no_ibkr: bool = True,
    no_orders: bool = True,
) -> GapConfirmatoryRunConfig:
    return GapConfirmatoryRunConfig(
        ledger_path=_ledger(tmp_path),
        matrix_path=MATRIX_PATH,
        criteria_path=CRITERIA_PATH,
        output_dir=tmp_path / "runtime",
        cache_only=cache_only,
        no_ibkr=no_ibkr,
        no_signals=True,
        no_preview=True,
        no_orders=no_orders,
    )


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
        "gap_direction",
        "benchmark_spy_return_20d",
        "open_to_close_return",
        "next_open_to_close_return",
        "is_stock_operational",
        "is_benchmark",
        "product_class",
        "data_quality_status",
    ]
    rows = [
        ["AAA", "2025-03-04", "20", "19.8", "220000", "-0.035", "0.035", "down", "-0.01", "-0.002", "0.01", "True", "False", "STK", "DATA_OK"],
        ["BBB", "2025-03-05", "30", "30.3", "200000", "0.032", "0.032", "up", "-0.01", "0.002", "-0.01", "True", "False", "STK", "DATA_OK"],
        ["CCC", "2025-03-06", "40", "40.1", "180000", "0.012", "0.012", "up", "-0.02", "0.001", "-0.005", "True", "False", "STK", "DATA_OK"],
        ["DDD", "2025-03-07", "50", "49.9", "180000", "-0.001", "0.001", "down", "-0.02", "-0.001", "0.004", "True", "False", "STK", "DATA_OK"],
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)
    return path
