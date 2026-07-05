from __future__ import annotations

from dataclasses import replace

import pytest

from tradeo.modules.daily_swing.gap_backtest_matrix import (
    CANDIDATE_SIZE_CAP,
    GapBacktestMatrixError,
    default_gap_backtest_matrix,
    validate_gap_backtest_matrix,
)


def test_gap_backtest_matrix_schema_valid() -> None:
    validation = validate_gap_backtest_matrix(default_gap_backtest_matrix())

    assert validation.decision == "GAP_BACKTEST_MATRIX_READY_FOR_CACHE_ONLY_DRY_RUN"
    assert validation.no_lookahead_status == "MATRIX_NO_LOOKAHEAD_PASS"
    assert validation.candidate_tests == CANDIDATE_SIZE_CAP


def test_gap_backtest_matrix_rejects_duplicate_test_id() -> None:
    rows = default_gap_backtest_matrix()
    rows[1] = replace(rows[1], test_id=rows[0].test_id)

    with pytest.raises(GapBacktestMatrixError, match="duplicate"):
        validate_gap_backtest_matrix(rows)


def test_gap_backtest_matrix_rejects_execution_flags() -> None:
    rows = default_gap_backtest_matrix()
    rows[0] = replace(rows[0], execution_allowed=True)

    with pytest.raises(GapBacktestMatrixError, match="execution"):
        validate_gap_backtest_matrix(rows)


def test_gap_backtest_matrix_same_day_forbids_close_high_low_outcomes() -> None:
    rows = default_gap_backtest_matrix()
    same_day = next(row for row in rows if row.family == "GAP_CONTINUATION_SAME_DAY")

    assert "close" not in same_day.required_known_fields.split("|")
    assert "high" in same_day.forbidden_fields_for_decision.split("|")
    assert "low" in same_day.forbidden_fields_for_decision.split("|")
    assert "gap_fill_ratio" in same_day.forbidden_fields_for_decision.split("|")

    bad = replace(same_day, required_known_fields=f"{same_day.required_known_fields}|close")
    with pytest.raises(GapBacktestMatrixError, match="leak"):
        validate_gap_backtest_matrix([bad, *[row for row in rows if row.test_id != same_day.test_id]])


def test_gap_backtest_matrix_next_day_allows_after_close_fields() -> None:
    rows = default_gap_backtest_matrix()
    next_day = next(row for row in rows if row.family == "GAP_CONTINUATION_NEXT_DAY")

    assert "close" in next_day.required_known_fields.split("|")
    assert "gap_fill_ratio" in next_day.required_known_fields.split("|")
    assert "next_open_to_close_return" in next_day.forbidden_fields_for_decision.split("|")


def test_gap_backtest_matrix_blocks_paper_live_preview_signals() -> None:
    rows = default_gap_backtest_matrix()
    rows[0] = replace(rows[0], paper_allowed=True, live_allowed=True, preview_allowed=True)

    with pytest.raises(GapBacktestMatrixError, match="paper"):
        validate_gap_backtest_matrix(rows)


def test_gap_backtest_matrix_has_baselines_and_placebos() -> None:
    validation = validate_gap_backtest_matrix(default_gap_backtest_matrix())

    assert validation.baseline_rows >= 8
    assert validation.placebo_rows >= 16


def test_gap_backtest_matrix_size_cap() -> None:
    rows = default_gap_backtest_matrix()
    extra = replace(rows[0], test_id="GAP003_EXTRA_CANDIDATE")
    rows.append(extra)

    with pytest.raises(GapBacktestMatrixError, match="exceeds cap"):
        validate_gap_backtest_matrix(rows)


def test_gap_backtest_matrix_no_best_threshold() -> None:
    rows = default_gap_backtest_matrix()

    assert not any("best" in row.test_id.lower() for row in rows)
    assert not any("best" in row.baseline_group.lower() for row in rows)
