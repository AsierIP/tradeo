from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tradeo.modules.daily_swing.gap_confirmatory_protocol import (
    ALLOWED_OBSERVATIONS,
    MAX_CONFIRMATORY_TESTS,
    REQUIRED_CONTROL_TYPES,
    REQUIRED_POLICIES,
    REQUIRED_SLIPPAGE_STRESSES,
    GapConfirmatoryProtocolError,
    read_confirmatory_matrix_json,
    validate_confirmatory_matrix,
)

MATRIX_PATH = Path("research/daily_swing/gap/dss_gap_006_confirmatory_matrix.json")


def _rows():
    return read_confirmatory_matrix_json(MATRIX_PATH)


def test_gap_confirmatory_protocol_schema_valid() -> None:
    validation = validate_confirmatory_matrix(_rows())

    assert validation.decision == "GAP_CONFIRMATORY_PROTOCOL_READY"
    assert validation.rows == MAX_CONFIRMATORY_TESTS
    assert validation.confirmation_targets == 6


def test_gap_confirmatory_protocol_max_12_tests() -> None:
    rows = _rows()
    rows.append(replace(rows[0], test_id="GAP006_EXTRA_FORBIDDEN"))

    with pytest.raises(GapConfirmatoryProtocolError, match="max"):
        validate_confirmatory_matrix(rows)


def test_gap_confirmatory_protocol_only_allowed_observations() -> None:
    rows = _rows()
    rows[0] = replace(rows[0], source_observation_id="GAP003_FORBIDDEN")

    with pytest.raises(GapConfirmatoryProtocolError, match="not allowed"):
        validate_confirmatory_matrix(rows)

    validation = validate_confirmatory_matrix(_rows())
    assert set(validation.allowed_observations) == set(ALLOWED_OBSERVATIONS)


def test_gap_confirmatory_protocol_requires_operable_policies() -> None:
    rows = [row for row in _rows() if row.policy != "ONE_ACTIVE_PER_SYMBOL"]

    with pytest.raises(GapConfirmatoryProtocolError, match="operable policies"):
        validate_confirmatory_matrix(rows)

    policies = {row.policy for row in _rows()}
    assert REQUIRED_POLICIES <= policies


def test_gap_confirmatory_protocol_requires_slippage_stress() -> None:
    rows = [replace(row, slippage_model="10bps|25bps") for row in _rows()]

    with pytest.raises(GapConfirmatoryProtocolError, match="slippage"):
        validate_confirmatory_matrix(rows)

    stresses = set().union(*(row.slippage_model.split("|") for row in _rows()))
    assert REQUIRED_SLIPPAGE_STRESSES <= stresses


def test_gap_confirmatory_protocol_requires_baselines_placebos() -> None:
    rows = [row for row in _rows() if row.baseline_or_placebo_type != "RANDOM_MATCHED"]

    with pytest.raises(GapConfirmatoryProtocolError, match="baseline/placebo"):
        validate_confirmatory_matrix(rows)

    controls = {row.baseline_or_placebo_type for row in _rows() if row.is_baseline or row.is_placebo}
    assert REQUIRED_CONTROL_TYPES <= controls


def test_gap_confirmatory_protocol_blocks_execution_flags() -> None:
    rows = _rows()
    rows[0] = replace(rows[0], execution_allowed=True)

    with pytest.raises(GapConfirmatoryProtocolError, match="execution"):
        validate_confirmatory_matrix(rows)


def test_gap_confirmatory_protocol_blocks_paper_live_preview_signals() -> None:
    rows = _rows()
    rows[0] = replace(rows[0], paper_allowed=True, live_allowed=True, preview_allowed=True)

    with pytest.raises(GapConfirmatoryProtocolError, match="paper"):
        validate_confirmatory_matrix(rows)


def test_gap_confirmatory_protocol_direction_locked() -> None:
    assert {row.direction for row in _rows()} == {"both_signed"}
