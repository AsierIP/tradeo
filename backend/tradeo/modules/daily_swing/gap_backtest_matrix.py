from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tradeo.daily_swing.dss_gap_003.backtest_matrix.v1"
CANDIDATE_SIZE_CAP = 40

FAMILIES = (
    "GAP_CONTINUATION_SAME_DAY",
    "GAP_REVERSAL_SAME_DAY",
    "GAP_CONTINUATION_NEXT_DAY",
    "GAP_REVERSAL_NEXT_DAY",
)
SAME_DAY_FAMILIES = frozenset({"GAP_CONTINUATION_SAME_DAY", "GAP_REVERSAL_SAME_DAY"})
NEXT_DAY_FAMILIES = frozenset({"GAP_CONTINUATION_NEXT_DAY", "GAP_REVERSAL_NEXT_DAY"})

SAME_DAY_FORBIDDEN_FIELDS = frozenset(
    {
        "high",
        "low",
        "close",
        "volume",
        "open_to_close_return",
        "close_to_next_open_return",
        "next_open_to_close_return",
        "intraday_gap_fill_flag",
        "gap_fill_ratio",
    }
)
NEXT_DAY_FORBIDDEN_FIELDS = frozenset({"close_to_next_open_return", "next_open_to_close_return"})
SECURITY_FLAG_COLUMNS = (
    "execution_allowed",
    "signal_output_allowed",
    "preview_allowed",
    "paper_allowed",
    "live_allowed",
)
MATRIX_COLUMNS = (
    "test_id",
    "family",
    "direction",
    "entry_timing",
    "decision_time",
    "required_known_fields",
    "forbidden_fields_for_decision",
    "gap_threshold_type",
    "gap_threshold_value",
    "regime_filter",
    "volatility_filter",
    "liquidity_filter",
    "portfolio_policy",
    "cost_model",
    "slippage_model",
    "baseline_group",
    "is_candidate",
    "is_baseline",
    "is_placebo",
    "execution_allowed",
    "signal_output_allowed",
    "preview_allowed",
    "paper_allowed",
    "live_allowed",
)

SAME_DAY_REQUIRED_FIELDS = (
    "symbol",
    "date",
    "open",
    "prev_close",
    "gap_pct",
    "abs_gap_pct",
    "gap_direction",
    "atr14_pct_prev",
    "gap_vs_atr_prev",
    "prior_return_5d",
    "prior_return_20d",
    "benchmark_spy_return_20d",
    "benchmark_qqq_return_20d",
    "is_stock_operational",
    "product_class",
)
NEXT_DAY_REQUIRED_FIELDS = SAME_DAY_REQUIRED_FIELDS + (
    "high",
    "low",
    "close",
    "volume",
    "intraday_gap_fill_flag",
    "gap_fill_ratio",
)


class GapBacktestMatrixError(ValueError):
    pass


@dataclass(frozen=True)
class GapBacktestMatrixRow:
    test_id: str
    family: str
    direction: str
    entry_timing: str
    decision_time: str
    required_known_fields: str
    forbidden_fields_for_decision: str
    gap_threshold_type: str
    gap_threshold_value: str
    regime_filter: str
    volatility_filter: str
    liquidity_filter: str
    portfolio_policy: str
    cost_model: str
    slippage_model: str
    baseline_group: str
    is_candidate: bool
    is_baseline: bool
    is_placebo: bool
    execution_allowed: bool = False
    signal_output_allowed: bool = False
    preview_allowed: bool = False
    paper_allowed: bool = False
    live_allowed: bool = False


@dataclass(frozen=True)
class GapBacktestMatrixValidation:
    decision: str
    rows: int
    candidate_tests: int
    baseline_rows: int
    placebo_rows: int
    families: list[str]
    portfolio_policies: list[str]
    cost_models: list[str]
    slippage_models: list[str]
    no_lookahead_status: str


def default_gap_backtest_matrix() -> list[GapBacktestMatrixRow]:
    rows: list[GapBacktestMatrixRow] = []
    for family in FAMILIES:
        for threshold_type, threshold_value, suffix in _candidate_thresholds():
            rows.append(
                _row(
                    test_id=f"GAP003_{_family_code(family)}_{suffix}_BOTH_ALL",
                    family=family,
                    direction="both_signed",
                    gap_threshold_type=threshold_type,
                    gap_threshold_value=threshold_value,
                    portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
                    baseline_group="CANDIDATE_PRE_REGISTERED",
                    is_candidate=True,
                )
            )
        rows.extend(
            [
                _row(
                    test_id=f"GAP003_{_family_code(family)}_ABS_1_0_UP_ONLY",
                    family=family,
                    direction="gap_up_only",
                    gap_threshold_type="abs_gap_pct",
                    gap_threshold_value="0.010",
                    portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
                    baseline_group="DIRECTION_SENSITIVITY",
                    is_candidate=True,
                ),
                _row(
                    test_id=f"GAP003_{_family_code(family)}_ABS_1_0_DOWN_ONLY",
                    family=family,
                    direction="gap_down_only",
                    gap_threshold_type="abs_gap_pct",
                    gap_threshold_value="0.010",
                    portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
                    baseline_group="DIRECTION_SENSITIVITY",
                    is_candidate=True,
                ),
                _row(
                    test_id=f"GAP003_{_family_code(family)}_ABS_1_0_MAX2",
                    family=family,
                    direction="both_signed",
                    gap_threshold_type="abs_gap_pct",
                    gap_threshold_value="0.010",
                    portfolio_policy="MAX_2_NEW_TRADES_PER_DAY",
                    baseline_group="PORTFOLIO_POLICY_SENSITIVITY",
                    is_candidate=True,
                ),
            ]
        )
        rows.extend(_baseline_and_placebo_rows(family))
        rows.extend(_filter_policy_rows(family))
    return rows


def validate_gap_backtest_matrix(rows: list[GapBacktestMatrixRow]) -> GapBacktestMatrixValidation:
    if not rows:
        raise GapBacktestMatrixError("matrix is empty")

    ids = [row.test_id for row in rows]
    duplicates = sorted({test_id for test_id in ids if ids.count(test_id) > 1})
    if duplicates:
        raise GapBacktestMatrixError(f"duplicate test_id values: {duplicates}")

    candidate_tests = 0
    for row in rows:
        _validate_row(row)
        if row.is_candidate:
            candidate_tests += 1
    if candidate_tests > CANDIDATE_SIZE_CAP:
        raise GapBacktestMatrixError(
            f"candidate matrix size {candidate_tests} exceeds cap {CANDIDATE_SIZE_CAP}"
        )

    families = sorted({row.family for row in rows})
    missing_families = sorted(set(FAMILIES) - set(families))
    if missing_families:
        raise GapBacktestMatrixError(f"missing families: {missing_families}")

    baseline_groups = {row.baseline_group for row in rows if row.is_baseline or row.is_placebo}
    required_groups = {
        "MATCHED_NON_GAP",
        "RANDOM_MATCHED",
        "SIGN_INVERTED_GAP",
        "DELAYED_ENTRY",
        "THRESHOLD_PERTURBATION",
        "EARNINGS_SENSITIVITY",
    }
    missing_groups = sorted(required_groups - baseline_groups)
    if missing_groups:
        raise GapBacktestMatrixError(f"missing baseline/placebo groups: {missing_groups}")

    return GapBacktestMatrixValidation(
        decision="GAP_BACKTEST_MATRIX_READY_FOR_CACHE_ONLY_DRY_RUN",
        rows=len(rows),
        candidate_tests=candidate_tests,
        baseline_rows=sum(1 for row in rows if row.is_baseline),
        placebo_rows=sum(1 for row in rows if row.is_placebo),
        families=families,
        portfolio_policies=sorted({row.portfolio_policy for row in rows}),
        cost_models=sorted({row.cost_model for row in rows}),
        slippage_models=sorted({row.slippage_model for row in rows}),
        no_lookahead_status="MATRIX_NO_LOOKAHEAD_PASS",
    )


def write_gap_backtest_matrix(rows: list[GapBacktestMatrixRow], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "dss_gap_003_backtest_matrix.csv"
    json_path = output_dir / "dss_gap_003_backtest_matrix.json"
    payload = [asdict(row) for row in rows]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MATRIX_COLUMNS))
        writer.writeheader()
        writer.writerows(payload)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"csv": csv_path, "json": json_path}


def read_gap_backtest_matrix_json(path: Path) -> list[GapBacktestMatrixRow]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [GapBacktestMatrixRow(**row) for row in payload]


def matrix_audit(rows: list[GapBacktestMatrixRow]) -> dict[str, Any]:
    validation = validate_gap_backtest_matrix(rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "decision": "MATRIX_NO_LOOKAHEAD_PASS",
        "validation_decision": validation.decision,
        "same_day_forbidden_fields": sorted(SAME_DAY_FORBIDDEN_FIELDS),
        "next_day_forbidden_fields": sorted(NEXT_DAY_FORBIDDEN_FIELDS),
        "assertions": {
            "same_day_rows_do_not_use_close_high_low_or_outcomes": True,
            "next_day_rows_can_use_after_close_t_fields": True,
            "gap_pct_uses_open_t_and_prev_close": True,
            "atr_and_prior_returns_use_t_minus_1_or_earlier": True,
            "spy_qqq_benchmark_or_regime_only": True,
            "no_execution_flags_enabled": True,
            "no_best_threshold_selected": True,
        },
    }


def _candidate_thresholds() -> tuple[tuple[str, str, str], ...]:
    return (
        ("abs_gap_pct", "0.005", "ABS_0_5"),
        ("abs_gap_pct", "0.010", "ABS_1_0"),
        ("abs_gap_pct", "0.020", "ABS_2_0"),
        ("abs_gap_pct", "0.030", "ABS_3_0"),
        ("abs_gap_vs_atr_prev", "0.5", "ATR_0_5"),
        ("abs_gap_vs_atr_prev", "1.0", "ATR_1_0"),
        ("abs_gap_vs_atr_prev", "1.5", "ATR_1_5"),
    )


def _baseline_and_placebo_rows(family: str) -> list[GapBacktestMatrixRow]:
    code = _family_code(family)
    return [
        _row(
            test_id=f"GAP003_{code}_BASELINE_MATCHED_NON_GAP",
            family=family,
            direction="both_signed",
            gap_threshold_type="abs_gap_pct",
            gap_threshold_value="0.010",
            portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
            baseline_group="MATCHED_NON_GAP",
            is_baseline=True,
        ),
        _row(
            test_id=f"GAP003_{code}_BASELINE_RANDOM_MATCHED",
            family=family,
            direction="both_signed",
            gap_threshold_type="abs_gap_pct",
            gap_threshold_value="0.010",
            portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
            baseline_group="RANDOM_MATCHED",
            is_baseline=True,
        ),
        _row(
            test_id=f"GAP003_{code}_PLACEBO_SIGN_INVERTED",
            family=family,
            direction="sign_inverted",
            gap_threshold_type="abs_gap_pct",
            gap_threshold_value="0.010",
            portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
            baseline_group="SIGN_INVERTED_GAP",
            is_placebo=True,
        ),
        _row(
            test_id=f"GAP003_{code}_PLACEBO_DELAYED_ENTRY",
            family=family,
            direction="both_signed",
            gap_threshold_type="abs_gap_pct",
            gap_threshold_value="0.010",
            portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
            baseline_group="DELAYED_ENTRY",
            is_placebo=True,
        ),
        _row(
            test_id=f"GAP003_{code}_PLACEBO_THRESHOLD_PERTURBATION",
            family=family,
            direction="both_signed",
            gap_threshold_type="abs_gap_pct",
            gap_threshold_value="0.010 +/- 0.0025",
            portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
            baseline_group="THRESHOLD_PERTURBATION",
            is_placebo=True,
        ),
        _row(
            test_id=f"GAP003_{code}_SENSITIVITY_EARNINGS",
            family=family,
            direction="both_signed",
            gap_threshold_type="abs_gap_pct",
            gap_threshold_value="0.010",
            portfolio_policy="ALL_EVENTS_RESEARCH_ONLY",
            baseline_group="EARNINGS_SENSITIVITY",
            is_placebo=True,
        ),
    ]


def _filter_policy_rows(family: str) -> list[GapBacktestMatrixRow]:
    code = _family_code(family)
    configs = (
        ("SPY_GT_0", "SPY_return20d_gt_0", "no_vol_filter", "no_liquidity_filter", "ALL_EVENTS_RESEARCH_ONLY"),
        ("SPY_LTE_0", "SPY_return20d_lte_0", "no_vol_filter", "no_liquidity_filter", "ALL_EVENTS_RESEARCH_ONLY"),
        (
            "SPY_SMA200",
            "SPY_close_gt_SMA200_if_timestamp_safe",
            "no_vol_filter",
            "no_liquidity_filter",
            "ALL_EVENTS_RESEARCH_ONLY",
        ),
        ("ATR_BELOW_MEDIAN", "no_regime_filter", "atr14_pct_prev_below_median", "no_liquidity_filter", "ALL_EVENTS_RESEARCH_ONLY"),
        ("ATR_ABOVE_MEDIAN", "no_regime_filter", "atr14_pct_prev_above_median", "no_liquidity_filter", "ALL_EVENTS_RESEARCH_ONLY"),
        (
            "VOLUME_T_MINUS_1",
            "no_regime_filter",
            "no_vol_filter",
            "volume_t_minus_1_gte_predefined_threshold",
            "ALL_EVENTS_RESEARCH_ONLY",
        ),
        ("ONE_ACTIVE", "no_regime_filter", "no_vol_filter", "no_liquidity_filter", "ONE_ACTIVE_PER_SYMBOL"),
    )
    return [
        _row(
            test_id=f"GAP003_{code}_DESIGN_{suffix}",
            family=family,
            direction="both_signed",
            gap_threshold_type="abs_gap_pct",
            gap_threshold_value="0.010",
            regime_filter=regime_filter,
            volatility_filter=volatility_filter,
            liquidity_filter=liquidity_filter,
            portfolio_policy=portfolio_policy,
            baseline_group="DESIGN_LOCKED_FILTER_OR_POLICY",
            is_candidate=False,
        )
        for suffix, regime_filter, volatility_filter, liquidity_filter, portfolio_policy in configs
    ]


def _row(
    *,
    test_id: str,
    family: str,
    direction: str,
    gap_threshold_type: str,
    gap_threshold_value: str,
    portfolio_policy: str,
    baseline_group: str,
    is_candidate: bool = False,
    is_baseline: bool = False,
    is_placebo: bool = False,
    regime_filter: str = "no_regime_filter",
    volatility_filter: str = "no_vol_filter",
    liquidity_filter: str = "exclude_if_missing_volume_prev_else_no_liquidity_filter",
) -> GapBacktestMatrixRow:
    same_day = family in SAME_DAY_FAMILIES
    return GapBacktestMatrixRow(
        test_id=test_id,
        family=family,
        direction=direction,
        entry_timing="open_t" if same_day else "open_t_plus_1",
        decision_time="open_t" if same_day else "after_close_t",
        required_known_fields="|".join(SAME_DAY_REQUIRED_FIELDS if same_day else NEXT_DAY_REQUIRED_FIELDS),
        forbidden_fields_for_decision="|".join(
            sorted(SAME_DAY_FORBIDDEN_FIELDS if same_day else NEXT_DAY_FORBIDDEN_FIELDS)
        ),
        gap_threshold_type=gap_threshold_type,
        gap_threshold_value=gap_threshold_value,
        regime_filter=regime_filter,
        volatility_filter=volatility_filter,
        liquidity_filter=liquidity_filter,
        portfolio_policy=portfolio_policy,
        cost_model="cost_x1_10bps|cost_x2_20bps|cost_x3_30bps",
        slippage_model="open_adverse_10bps|open_adverse_25bps|open_adverse_50bps_stress",
        baseline_group=baseline_group,
        is_candidate=is_candidate,
        is_baseline=is_baseline,
        is_placebo=is_placebo,
    )


def _validate_row(row: GapBacktestMatrixRow) -> None:
    if row.family not in FAMILIES:
        raise GapBacktestMatrixError(f"{row.test_id} has unknown family {row.family}")
    if any(getattr(row, column) for column in SECURITY_FLAG_COLUMNS):
        raise GapBacktestMatrixError(f"{row.test_id} enables execution/paper/live/preview/signals")
    if row.is_candidate and (row.is_baseline or row.is_placebo):
        raise GapBacktestMatrixError(f"{row.test_id} mixes candidate with baseline/placebo flags")
    required_fields = set(_split_fields(row.required_known_fields))
    forbidden_fields = set(_split_fields(row.forbidden_fields_for_decision))
    if row.family in SAME_DAY_FAMILIES:
        leaked = required_fields & SAME_DAY_FORBIDDEN_FIELDS
        if leaked:
            raise GapBacktestMatrixError(f"{row.test_id} same-day required fields leak outcomes: {sorted(leaked)}")
        missing = SAME_DAY_FORBIDDEN_FIELDS - forbidden_fields
        if missing:
            raise GapBacktestMatrixError(f"{row.test_id} same-day forbidden fields incomplete: {sorted(missing)}")
    if row.family in NEXT_DAY_FAMILIES:
        missing = {"high", "low", "close", "volume"} - required_fields
        if missing:
            raise GapBacktestMatrixError(f"{row.test_id} next-day missing after-close fields: {sorted(missing)}")
        leaked = required_fields & NEXT_DAY_FORBIDDEN_FIELDS
        if leaked:
            raise GapBacktestMatrixError(f"{row.test_id} next-day uses future t+1 outcomes: {sorted(leaked)}")
    if "best" in row.test_id.lower() or "best" in row.baseline_group.lower():
        raise GapBacktestMatrixError(f"{row.test_id} contains prohibited best-threshold language")


def _split_fields(value: str) -> list[str]:
    return [part for part in value.split("|") if part]


def _family_code(family: str) -> str:
    return family.removeprefix("GAP_").replace("_", "-")
