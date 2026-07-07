from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tradeo.modules.daily_swing.research_bucket_matrix import (
    BUCKETS,
    DECISION_READY,
    FAMILIES,
    GLOBAL_APPROVED_SUMMARY_ONLY,
    GLOBAL_DENIED_FOR_BUCKET_TEST,
    ROW_SCOPE_SUMMARY_ONLY,
    SUMMARY_BUCKET,
    ResearchBucketMatrixError,
    default_research_bucket_matrix,
    read_research_bucket_matrix_csv,
    read_research_bucket_matrix_json,
    validate_research_bucket_matrix,
    validation_payload,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MATRIX_JSON = REPO_ROOT / "research/daily_swing/universe/daily_research_bucket_matrix.json"
MATRIX_CSV = REPO_ROOT / "research/daily_swing/universe/daily_research_bucket_matrix.csv"


def _rows():
    return read_research_bucket_matrix_json(MATRIX_JSON)


def test_daily_research_bucket_matrix_schema_valid() -> None:
    validation = validate_research_bucket_matrix(default_research_bucket_matrix())

    assert validation.decision == DECISION_READY
    assert validation.rows == 161
    assert validation.bucket_test_rows == 160
    assert validation.summary_rows == 1
    assert validation.execution_surface_blocked is True


def test_daily_research_bucket_matrix_artifacts_match_default_contract() -> None:
    json_rows = _rows()
    csv_rows = read_research_bucket_matrix_csv(MATRIX_CSV)
    default_rows = default_research_bucket_matrix()

    assert [row.test_id for row in json_rows] == [row.test_id for row in default_rows]
    assert [row.test_id for row in csv_rows] == [row.test_id for row in default_rows]
    assert validate_research_bucket_matrix(json_rows).decision == DECISION_READY


def test_daily_research_bucket_matrix_has_families_a_d_for_each_bucket() -> None:
    rows = _rows()

    pairs = {(row.family, row.bucket) for row in rows if row.family in FAMILIES}
    assert pairs == {(family, bucket) for family in FAMILIES for bucket in BUCKETS}


def test_daily_research_bucket_matrix_requires_fdr_wrc_spa_and_bucket_metrics() -> None:
    rows = _rows()

    assert all(row.fdr_wrc_spa_required for row in rows)
    assert all(row.bucket_level_metrics_required for row in rows)

    bad = replace(rows[0], fdr_wrc_spa_required=False)
    with pytest.raises(ResearchBucketMatrixError, match="fdr_wrc_spa_required"):
        validate_research_bucket_matrix([bad, *rows[1:]])


def test_daily_research_bucket_matrix_global_aggregate_false_except_summary() -> None:
    rows = _rows()
    summary = [row for row in rows if row.row_scope == ROW_SCOPE_SUMMARY_ONLY]
    bucket_rows = [row for row in rows if row.row_scope != ROW_SCOPE_SUMMARY_ONLY]

    assert len(summary) == 1
    assert summary[0].bucket == SUMMARY_BUCKET
    assert summary[0].global_aggregate_allowed is True
    assert summary[0].global_aggregate_approval == GLOBAL_APPROVED_SUMMARY_ONLY
    assert not any(row.global_aggregate_allowed for row in bucket_rows)
    assert {row.global_aggregate_approval for row in bucket_rows} == {GLOBAL_DENIED_FOR_BUCKET_TEST}


def test_daily_research_bucket_matrix_blocks_missing_bucket_approval() -> None:
    rows = _rows()
    rows[0] = replace(rows[0], bucket="")

    with pytest.raises(ResearchBucketMatrixError, match="bucket"):
        validate_research_bucket_matrix(rows)


def test_daily_research_bucket_matrix_blocks_missing_global_approval() -> None:
    rows = _rows()
    rows[0] = replace(rows[0], approval_rule="")

    with pytest.raises(ResearchBucketMatrixError, match="approval"):
        validate_research_bucket_matrix(rows)


def test_daily_research_bucket_matrix_blocks_bucket_test_global_aggregate() -> None:
    rows = _rows()
    rows[0] = replace(rows[0], global_aggregate_allowed=True)

    with pytest.raises(ResearchBucketMatrixError, match="global aggregate"):
        validate_research_bucket_matrix(rows)


def test_daily_research_bucket_matrix_blocks_serious_backtest_and_execution_flags() -> None:
    rows = _rows()
    rows[0] = replace(rows[0], timeframe="5m")

    with pytest.raises(ResearchBucketMatrixError, match="timeframe"):
        validate_research_bucket_matrix(rows)


def test_daily_research_bucket_matrix_validation_payload_is_summary_only_global() -> None:
    payload = validation_payload(_rows())

    assert payload["contract"]["global_aggregate_allowed"] == "summary_only"
    assert payload["contract"]["global_pattern_approval_allowed"] is False
    assert payload["validation"]["global_aggregate_allowed_scopes"] == [ROW_SCOPE_SUMMARY_ONLY]
