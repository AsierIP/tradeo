from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "tradeo.daily_swing.research_bucket_matrix.v2"
UNIVERSE_VERSION = "daily_focus_universe_v2"
DECISION_READY = "DAILY_RESEARCH_BUCKET_MATRIX_READY_FOR_BUCKET_ONLY_FUTURE_TESTS"

BUCKETS = (
    "mega_large_cap",
    "large_cap_core",
    "liquid_mid_cap",
    "liquid_small_cap",
    "high_beta_growth",
    "defensive_quality",
    "sector_leaders",
    "etf_macro",
)
FAMILIES = (
    "pullback_in_trend",
    "gap_continuation_reversal_daily",
    "volatility_contraction_breakout",
    "relative_strength_sector_leadership",
)
SUMMARY_FAMILY = "summary"
SUMMARY_BUCKET = "all_buckets_summary_only"
ROW_SCOPE_BUCKET_TEST = "bucket_test"
ROW_SCOPE_SUMMARY_ONLY = "summary_only"
GLOBAL_DENIED_FOR_BUCKET_TEST = "DENIED_BUCKET_TEST_GLOBAL_AGGREGATE_CANNOT_APPROVE"
GLOBAL_APPROVED_SUMMARY_ONLY = "APPROVED_SUMMARY_ONLY_NO_PATTERN_APPROVAL"

MATRIX_COLUMNS = (
    "test_id",
    "family",
    "bucket",
    "universe_version",
    "timeframe",
    "entry_timing",
    "exit_horizon",
    "cost_model",
    "slippage_model",
    "baseline_group",
    "placebo_group",
    "min_sample_requirement",
    "fdr_wrc_spa_required",
    "bucket_level_metrics_required",
    "global_aggregate_allowed",
    "row_scope",
    "variant",
    "bucket_level_metrics",
    "approval_rule",
)
BOOL_COLUMNS = (
    "fdr_wrc_spa_required",
    "bucket_level_metrics_required",
    "global_aggregate_allowed",
)


class ResearchBucketMatrixError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ResearchBucketMatrixRow:
    test_id: str
    family: str
    bucket: str
    universe_version: str
    timeframe: str
    entry_timing: str
    exit_horizon: str
    cost_model: str
    slippage_model: str
    baseline_group: str
    placebo_group: str
    min_sample_requirement: int
    fdr_wrc_spa_required: bool
    bucket_level_metrics_required: bool
    global_aggregate_allowed: bool
    row_scope: str = ROW_SCOPE_BUCKET_TEST
    variant: str = ""
    bucket_level_metrics: str = "n|expectancy_r|win_rate|profit_factor|max_drawdown_r|coverage|cost_stress"
    approval_rule: str = GLOBAL_DENIED_FOR_BUCKET_TEST

    @property
    def bucket_key(self) -> str:
        return self.bucket

    @property
    def global_aggregate_approval(self) -> str:
        return self.approval_rule


@dataclass(frozen=True, slots=True)
class ResearchBucketMatrixValidation:
    decision: str
    rows: int
    bucket_test_rows: int
    summary_rows: int
    families: list[str]
    buckets: list[str]
    fdr_wrc_spa_required: bool
    bucket_level_metrics_required: bool
    global_aggregate_allowed_scopes: list[str]
    execution_surface_blocked: bool = True


def default_research_bucket_matrix() -> list[ResearchBucketMatrixRow]:
    rows: list[ResearchBucketMatrixRow] = []
    for bucket in BUCKETS:
        rows.extend(_pullback_rows(bucket))
        rows.extend(_gap_rows(bucket))
        rows.append(
            _row(
                test_id=f"DRBM_V2_VCB_{bucket}",
                family="volatility_contraction_breakout",
                bucket=bucket,
                variant="contraction_window_breakout_confirmation_fakeout_controls",
                entry_timing="daily_close_breakout_confirmation",
                exit_horizon="5d",
                baseline_group="same_bucket_non_contraction_breakouts",
                placebo_group="same_bucket_random_breakout_dates",
                min_sample_requirement=80,
            )
        )
        rows.extend(_relative_strength_rows(bucket))
    rows.append(_summary_row())
    return rows


def validate_research_bucket_matrix(rows: list[ResearchBucketMatrixRow]) -> ResearchBucketMatrixValidation:
    if not rows:
        raise ResearchBucketMatrixError("research bucket matrix is empty")
    ids = [row.test_id for row in rows]
    duplicates = sorted({test_id for test_id in ids if ids.count(test_id) > 1})
    if duplicates:
        raise ResearchBucketMatrixError(f"duplicate test_id values: {duplicates}")
    for row in rows:
        _validate_row(row)

    bucket_rows = [row for row in rows if row.row_scope == ROW_SCOPE_BUCKET_TEST]
    summary_rows = [row for row in rows if row.row_scope == ROW_SCOPE_SUMMARY_ONLY]
    if len(summary_rows) != 1:
        raise ResearchBucketMatrixError("matrix must contain exactly one summary-only row")

    families = sorted({row.family for row in bucket_rows})
    missing_families = sorted(set(FAMILIES) - set(families))
    if missing_families:
        raise ResearchBucketMatrixError(f"missing families: {missing_families}")
    buckets = sorted({row.bucket for row in bucket_rows})
    missing_buckets = sorted(set(BUCKETS) - set(buckets))
    if missing_buckets:
        raise ResearchBucketMatrixError(f"missing buckets: {missing_buckets}")
    missing_pairs = [
        f"{family}:{bucket}"
        for family in FAMILIES
        for bucket in BUCKETS
        if not any(row.family == family and row.bucket == bucket for row in bucket_rows)
    ]
    if missing_pairs:
        raise ResearchBucketMatrixError(f"missing family bucket pairs: {missing_pairs}")

    return ResearchBucketMatrixValidation(
        decision=DECISION_READY,
        rows=len(rows),
        bucket_test_rows=len(bucket_rows),
        summary_rows=len(summary_rows),
        families=families,
        buckets=buckets,
        fdr_wrc_spa_required=all(row.fdr_wrc_spa_required for row in rows),
        bucket_level_metrics_required=all(row.bucket_level_metrics_required for row in rows),
        global_aggregate_allowed_scopes=sorted(
            {row.row_scope for row in rows if row.global_aggregate_allowed}
        ),
    )


def write_research_bucket_matrix(rows: list[ResearchBucketMatrixRow], output_dir: Path) -> dict[str, Path]:
    validate_research_bucket_matrix(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "daily_research_bucket_matrix.csv"
    json_path = output_dir / "daily_research_bucket_matrix.json"
    md_path = output_dir / "DAILY_RESEARCH_BUCKET_MATRIX.md"
    payload = [asdict(row) for row in rows]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(MATRIX_COLUMNS))
        writer.writeheader()
        writer.writerows(payload)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(rows), encoding="utf-8")
    return {"csv": csv_path, "json": json_path, "markdown": md_path}


def read_research_bucket_matrix_json(path: Path) -> list[ResearchBucketMatrixRow]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["rows"] if isinstance(payload, dict) else payload
    return [_row_from_mapping(row) for row in rows]


def read_research_bucket_matrix_csv(path: Path) -> list[ResearchBucketMatrixRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [_row_from_mapping(row) for row in csv.DictReader(handle)]


def validation_payload(rows: list[ResearchBucketMatrixRow]) -> dict[str, Any]:
    validation = validate_research_bucket_matrix(rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation": asdict(validation),
        "contract": {
            "families": list(FAMILIES),
            "buckets": list(BUCKETS),
            "universe_version": UNIVERSE_VERSION,
            "timeframe": "1d",
            "fdr_wrc_spa_required": True,
            "bucket_level_metrics_required": True,
            "global_aggregate_allowed": "summary_only",
            "global_pattern_approval_allowed": False,
        },
    }


def render_markdown(rows: list[ResearchBucketMatrixRow]) -> str:
    validation = validate_research_bucket_matrix(rows)
    lines = [
        "# Daily Research Bucket Matrix",
        "",
        "Task: T-DAILY-FOCUS-UNIVERSE-001",
        f"Decision: {validation.decision}",
        "",
        "This is a bucket-aware preregistration matrix only. It does not run a backtest,",
        "approve a pattern, create a paper/live candidate, emit previews, or send orders.",
        "",
        "## Contract",
        "",
        f"- Universe version: `{UNIVERSE_VERSION}`.",
        "- Timeframe: `1d` for every future test row.",
        "- Every bucket-test row requires FDR plus WRC/SPA controls.",
        "- Every bucket-test row requires bucket-level metrics.",
        "- Global aggregates are summary-only and cannot approve a Daily pattern.",
        "- ETF macro rows remain separate from stock buckets.",
        "",
        "## Buckets",
        "",
        *[f"- `{bucket}`" for bucket in BUCKETS],
        "",
        "## Families",
        "",
        "- Pullback in trend: W20, W50, W100 with forward 3/5/10/20 day horizons.",
        "- Gap continuation/reversal daily: same-day close, next-day close, 3-day and 5-day follow-through.",
        "- Volatility contraction breakout: contraction window, breakout confirmation, fakeout controls.",
        "- Relative strength / sector leadership: stock vs SPY, stock vs sector ETF, sector ETF vs SPY.",
        "",
        "## Machine Artifacts",
        "",
        "- `daily_research_bucket_matrix.csv`",
        "- `daily_research_bucket_matrix.json`",
        "",
        "## Rows",
        "",
        "| test_id | family | bucket | variant | exit_horizon | global_aggregate_allowed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.test_id} | {row.family} | {row.bucket} | {row.variant} | "
            f"{row.exit_horizon} | {str(row.global_aggregate_allowed).lower()} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def _pullback_rows(bucket: str) -> list[ResearchBucketMatrixRow]:
    rows: list[ResearchBucketMatrixRow] = []
    for window in ("W20", "W50", "W100"):
        for horizon in ("3d", "5d", "10d", "20d"):
            rows.append(
                _row(
                    test_id=f"DRBM_V2_PB_{window}_{horizon}_{bucket}",
                    family="pullback_in_trend",
                    bucket=bucket,
                    variant=window,
                    entry_timing=f"daily_close_pullback_to_{window}",
                    exit_horizon=horizon,
                    baseline_group=f"same_bucket_same_trend_no_{window}_pullback",
                    placebo_group=f"same_bucket_random_{window}_pullback_dates",
                    min_sample_requirement=120,
                )
            )
    return rows


def _gap_rows(bucket: str) -> list[ResearchBucketMatrixRow]:
    specs = (
        ("same_day_close", "same_day_close", "same_day_bucket_matched_non_gap"),
        ("next_day_close", "next_day_close", "next_day_bucket_matched_non_gap"),
        ("3_day_follow_through", "3d", "three_day_bucket_matched_non_gap"),
        ("5_day_follow_through", "5d", "five_day_bucket_matched_non_gap"),
    )
    return [
        _row(
            test_id=f"DRBM_V2_GAP_{variant}_{bucket}",
            family="gap_continuation_reversal_daily",
            bucket=bucket,
            variant=variant,
            entry_timing="daily_gap_open_then_close_policy",
            exit_horizon=horizon,
            baseline_group=baseline,
            placebo_group="same_bucket_random_gap_dates_same_regime",
            min_sample_requirement=100,
        )
        for variant, horizon, baseline in specs
    ]


def _relative_strength_rows(bucket: str) -> list[ResearchBucketMatrixRow]:
    specs = (
        ("stock_vs_spy", "daily_close_rs_stock_vs_spy"),
        ("stock_vs_sector_etf", "daily_close_rs_stock_vs_sector_etf"),
        ("sector_etf_vs_spy", "daily_close_rs_sector_etf_vs_spy"),
    )
    return [
        _row(
            test_id=f"DRBM_V2_RS_{variant}_{bucket}",
            family="relative_strength_sector_leadership",
            bucket=bucket,
            variant=variant,
            entry_timing=entry_timing,
            exit_horizon="10d",
            baseline_group="same_bucket_rs_neutral_symbols",
            placebo_group="same_bucket_sector_shuffled_rs",
            min_sample_requirement=100,
        )
        for variant, entry_timing in specs
    ]


def _row(
    *,
    test_id: str,
    family: str,
    bucket: str,
    variant: str,
    entry_timing: str,
    exit_horizon: str,
    baseline_group: str,
    placebo_group: str,
    min_sample_requirement: int,
) -> ResearchBucketMatrixRow:
    return ResearchBucketMatrixRow(
        test_id=test_id,
        family=family,
        bucket=bucket,
        universe_version=UNIVERSE_VERSION,
        timeframe="1d",
        entry_timing=entry_timing,
        exit_horizon=exit_horizon,
        cost_model="daily_equity_cost_model_v1_bucket_specific",
        slippage_model="daily_bucket_liquidity_slippage_model_v1",
        baseline_group=baseline_group,
        placebo_group=placebo_group,
        min_sample_requirement=min_sample_requirement,
        fdr_wrc_spa_required=True,
        bucket_level_metrics_required=True,
        global_aggregate_allowed=False,
        variant=variant,
    )


def _summary_row() -> ResearchBucketMatrixRow:
    return ResearchBucketMatrixRow(
        test_id="DRBM_V2_SUMMARY_ONLY",
        family=SUMMARY_FAMILY,
        bucket=SUMMARY_BUCKET,
        universe_version=UNIVERSE_VERSION,
        timeframe="1d",
        entry_timing="summary_only_no_entry",
        exit_horizon="summary_only",
        cost_model="summary_only_no_cost_decision",
        slippage_model="summary_only_no_slippage_decision",
        baseline_group="summary_only_bucket_coverage",
        placebo_group="summary_only_no_placebo_decision",
        min_sample_requirement=0,
        fdr_wrc_spa_required=True,
        bucket_level_metrics_required=True,
        global_aggregate_allowed=True,
        row_scope=ROW_SCOPE_SUMMARY_ONLY,
        variant="summary_only",
        bucket_level_metrics="bucket_row_count|missing_bucket_count|coverage_by_bucket",
        approval_rule=GLOBAL_APPROVED_SUMMARY_ONLY,
    )


def _validate_row(row: ResearchBucketMatrixRow) -> None:
    if row.row_scope == ROW_SCOPE_BUCKET_TEST:
        if row.family not in FAMILIES:
            raise ResearchBucketMatrixError(f"{row.test_id}: unknown family {row.family}")
        if row.bucket not in BUCKETS:
            raise ResearchBucketMatrixError(f"{row.test_id}: missing or unknown bucket {row.bucket}")
        if row.universe_version != UNIVERSE_VERSION:
            raise ResearchBucketMatrixError(f"{row.test_id}: wrong universe_version")
        if row.timeframe != "1d":
            raise ResearchBucketMatrixError(f"{row.test_id}: timeframe must be 1d")
        if row.global_aggregate_allowed:
            raise ResearchBucketMatrixError(f"{row.test_id}: global aggregate cannot approve bucket tests")
        if row.approval_rule != GLOBAL_DENIED_FOR_BUCKET_TEST:
            raise ResearchBucketMatrixError(f"{row.test_id}: global approval denial is required")
        if row.min_sample_requirement <= 0:
            raise ResearchBucketMatrixError(f"{row.test_id}: min_sample_requirement must be positive")
    elif row.row_scope == ROW_SCOPE_SUMMARY_ONLY:
        if row.family != SUMMARY_FAMILY or row.bucket != SUMMARY_BUCKET:
            raise ResearchBucketMatrixError(f"{row.test_id}: invalid summary row")
        if not row.global_aggregate_allowed:
            raise ResearchBucketMatrixError(f"{row.test_id}: summary row must allow aggregate summary")
        if row.approval_rule != GLOBAL_APPROVED_SUMMARY_ONLY:
            raise ResearchBucketMatrixError(f"{row.test_id}: summary approval rule is required")
    else:
        raise ResearchBucketMatrixError(f"{row.test_id}: unknown row_scope {row.row_scope}")

    for field_name in (
        "test_id",
        "family",
        "bucket",
        "entry_timing",
        "exit_horizon",
        "cost_model",
        "slippage_model",
        "baseline_group",
        "placebo_group",
        "bucket_level_metrics",
        "approval_rule",
    ):
        if not str(getattr(row, field_name, "")).strip():
            raise ResearchBucketMatrixError(f"{row.test_id}: {field_name} is required")
    if not row.fdr_wrc_spa_required:
        raise ResearchBucketMatrixError(f"{row.test_id}: fdr_wrc_spa_required must be true")
    if not row.bucket_level_metrics_required:
        raise ResearchBucketMatrixError(f"{row.test_id}: bucket_level_metrics_required must be true")


def _row_from_mapping(mapping: dict[str, Any]) -> ResearchBucketMatrixRow:
    row = dict(mapping)
    for column in BOOL_COLUMNS:
        row[column] = _coerce_bool(row[column])
    row["min_sample_requirement"] = int(row["min_sample_requirement"])
    return ResearchBucketMatrixRow(**row)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no", ""}:
            return False
    raise ResearchBucketMatrixError(f"cannot coerce boolean value: {value!r}")
