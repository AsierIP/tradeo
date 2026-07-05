from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

SCHEMA_VERSION = "tradeo.daily_swing.dss_gap_006.confirmatory_protocol.v1"
DECISION_READY = "GAP_CONFIRMATORY_PROTOCOL_READY"
MAX_CONFIRMATORY_TESTS = 12

ALLOWED_OBSERVATIONS = frozenset(
    {
        "GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL",
        "GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0",
    }
)
REQUIRED_POLICIES = frozenset({"ONE_ACTIVE_PER_SYMBOL", "MAX_2_NEW_TRADES_PER_DAY"})
REQUIRED_CONTROL_TYPES = frozenset(
    {
        "MATCHED_NON_GAP",
        "RANDOM_MATCHED",
        "SIGN_INVERTED_GAP",
        "DELAYED_ENTRY",
        "THRESHOLD_PERTURBATION",
        "EARNINGS_SENSITIVITY",
    }
)
REQUIRED_SLIPPAGE_STRESSES = frozenset({"10bps", "25bps", "50bps"})
SECURITY_FLAG_COLUMNS = (
    "paper_allowed",
    "live_allowed",
    "preview_allowed",
    "signal_output_allowed",
    "execution_allowed",
)
MATRIX_COLUMNS = (
    "test_id",
    "source_observation_id",
    "family",
    "policy",
    "threshold",
    "direction",
    "regime",
    "baseline_or_placebo_type",
    "slippage_model",
    "cost_model",
    "is_confirmation_target",
    "is_baseline",
    "is_placebo",
    "paper_allowed",
    "live_allowed",
    "preview_allowed",
    "signal_output_allowed",
    "execution_allowed",
)


class GapConfirmatoryProtocolError(ValueError):
    pass


@dataclass(frozen=True)
class GapConfirmatoryMatrixRow:
    test_id: str
    source_observation_id: str
    family: str
    policy: str
    threshold: str
    direction: str
    regime: str
    baseline_or_placebo_type: str
    slippage_model: str
    cost_model: str
    is_confirmation_target: bool
    is_baseline: bool
    is_placebo: bool
    paper_allowed: bool = False
    live_allowed: bool = False
    preview_allowed: bool = False
    signal_output_allowed: bool = False
    execution_allowed: bool = False


@dataclass(frozen=True)
class GapConfirmatoryProtocolValidation:
    decision: str
    rows: int
    confirmation_targets: int
    baseline_rows: int
    placebo_rows: int
    policies: list[str]
    control_types: list[str]
    slippage_stresses: list[str]
    allowed_observations: list[str]
    execution_surface_blocked: bool


def read_confirmatory_matrix_json(path: Path) -> list[GapConfirmatoryMatrixRow]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["rows"] if isinstance(payload, dict) else payload
    return [_row_from_mapping(row) for row in rows]


def read_confirmatory_matrix_csv(path: Path) -> list[GapConfirmatoryMatrixRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [_row_from_mapping(row) for row in csv.DictReader(handle)]


def validate_confirmatory_matrix(
    rows: list[GapConfirmatoryMatrixRow],
) -> GapConfirmatoryProtocolValidation:
    if not rows:
        raise GapConfirmatoryProtocolError("confirmatory matrix is empty")
    if len(rows) > MAX_CONFIRMATORY_TESTS:
        raise GapConfirmatoryProtocolError(
            f"confirmatory matrix has {len(rows)} rows; max is {MAX_CONFIRMATORY_TESTS}"
        )

    ids = [row.test_id for row in rows]
    duplicates = sorted({test_id for test_id in ids if ids.count(test_id) > 1})
    if duplicates:
        raise GapConfirmatoryProtocolError(f"duplicate test_id values: {duplicates}")

    for row in rows:
        _validate_row(row)

    source_observations = _source_observation_set(rows)
    if source_observations != ALLOWED_OBSERVATIONS:
        raise GapConfirmatoryProtocolError(
            f"matrix must cover exactly the allowed observations: {sorted(ALLOWED_OBSERVATIONS)}"
        )

    policies = {row.policy for row in rows}
    missing_policies = sorted(REQUIRED_POLICIES - policies)
    if missing_policies:
        raise GapConfirmatoryProtocolError(f"missing operable policies: {missing_policies}")

    control_types = {
        row.baseline_or_placebo_type
        for row in rows
        if row.is_baseline or row.is_placebo or row.baseline_or_placebo_type == "EARNINGS_SENSITIVITY"
    }
    missing_controls = sorted(REQUIRED_CONTROL_TYPES - control_types)
    if missing_controls:
        raise GapConfirmatoryProtocolError(f"missing baseline/placebo controls: {missing_controls}")

    slippage_stresses = _slippage_stress_set(rows)
    missing_slippage = sorted(REQUIRED_SLIPPAGE_STRESSES - slippage_stresses)
    if missing_slippage:
        raise GapConfirmatoryProtocolError(f"missing slippage stresses: {missing_slippage}")

    return GapConfirmatoryProtocolValidation(
        decision=DECISION_READY,
        rows=len(rows),
        confirmation_targets=sum(row.is_confirmation_target for row in rows),
        baseline_rows=sum(row.is_baseline for row in rows),
        placebo_rows=sum(row.is_placebo for row in rows),
        policies=sorted(policies),
        control_types=sorted(control_types),
        slippage_stresses=sorted(slippage_stresses),
        allowed_observations=sorted(source_observations),
        execution_surface_blocked=True,
    )


def validation_payload(rows: list[GapConfirmatoryMatrixRow]) -> dict[str, object]:
    validation = validate_confirmatory_matrix(rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation": asdict(validation),
        "security": {
            "no_orders": True,
            "no_paper": True,
            "no_live": True,
            "no_preview": True,
            "no_signals": True,
            "no_backtest": True,
            "no_ibkr": True,
            "no_downloads": True,
            "no_cron": True,
            "no_gh": True,
            "no_main_push": True,
        },
    }


def _validate_row(row: GapConfirmatoryMatrixRow) -> None:
    if not row.test_id.startswith("GAP006_"):
        raise GapConfirmatoryProtocolError(f"{row.test_id}: test_id must start with GAP006_")
    if row.family != "GAP_REVERSAL_SAME_DAY":
        raise GapConfirmatoryProtocolError(f"{row.test_id}: only same-day reversal is allowed")
    if row.threshold not in {"abs_gap_pct>=0.030", "abs_gap_pct>=0.010"}:
        raise GapConfirmatoryProtocolError(f"{row.test_id}: threshold is not allowed")
    if any(getattr(row, flag) for flag in SECURITY_FLAG_COLUMNS):
        raise GapConfirmatoryProtocolError(f"{row.test_id}: execution/paper/live/preview/signal flag enabled")
    if row.is_confirmation_target and (row.is_baseline or row.is_placebo):
        raise GapConfirmatoryProtocolError(f"{row.test_id}: target row cannot also be control row")
    if row.is_baseline and row.is_placebo:
        raise GapConfirmatoryProtocolError(f"{row.test_id}: row cannot be both baseline and placebo")
    if row.baseline_or_placebo_type == "EARNINGS_SENSITIVITY" and "earnings_unknown=true" not in row.regime:
        raise GapConfirmatoryProtocolError(f"{row.test_id}: earnings sensitivity must mark earnings_unknown=true")

    for source in _split_sources(row.source_observation_id):
        if source not in ALLOWED_OBSERVATIONS:
            raise GapConfirmatoryProtocolError(f"{row.test_id}: source observation is not allowed: {source}")


def _source_observation_set(rows: list[GapConfirmatoryMatrixRow]) -> set[str]:
    observations: set[str] = set()
    for row in rows:
        observations.update(_split_sources(row.source_observation_id))
    return observations


def _slippage_stress_set(rows: list[GapConfirmatoryMatrixRow]) -> set[str]:
    stresses: set[str] = set()
    for row in rows:
        stresses.update(part for part in row.slippage_model.split("|") if part.endswith("bps"))
    return stresses


def _split_sources(value: str) -> list[str]:
    return [part for part in value.split("|") if part]


def _row_from_mapping(mapping: dict[str, object]) -> GapConfirmatoryMatrixRow:
    return GapConfirmatoryMatrixRow(
        test_id=str(mapping["test_id"]),
        source_observation_id=str(mapping["source_observation_id"]),
        family=str(mapping["family"]),
        policy=str(mapping["policy"]),
        threshold=str(mapping["threshold"]),
        direction=str(mapping["direction"]),
        regime=str(mapping["regime"]),
        baseline_or_placebo_type=str(mapping["baseline_or_placebo_type"]),
        slippage_model=str(mapping["slippage_model"]),
        cost_model=str(mapping["cost_model"]),
        is_confirmation_target=_as_bool(mapping["is_confirmation_target"]),
        is_baseline=_as_bool(mapping["is_baseline"]),
        is_placebo=_as_bool(mapping["is_placebo"]),
        paper_allowed=_as_bool(mapping["paper_allowed"]),
        live_allowed=_as_bool(mapping["live_allowed"]),
        preview_allowed=_as_bool(mapping["preview_allowed"]),
        signal_output_allowed=_as_bool(mapping["signal_output_allowed"]),
        execution_allowed=_as_bool(mapping["execution_allowed"]),
    )


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"
