from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from tradeo.modules.daily_swing.gap_backtest_matrix import (
    GapBacktestMatrixRow,
    read_gap_backtest_matrix_json,
    validate_gap_backtest_matrix,
)

SCHEMA_VERSION = "tradeo.daily_swing.dss_gap_004.matrix_dry_run.v1"
IS_END = date.fromisoformat("2024-12-31")
OOS_START = date.fromisoformat("2025-01-01")
OOS_END = date.fromisoformat("2026-07-02")
COSTS = {"cost_x1": 0.0010, "cost_x2": 0.0020, "cost_x3": 0.0030}
SLIPPAGE = {
    "open_slippage_adverse_10bps": 0.0010,
    "open_slippage_adverse_25bps": 0.0025,
    "open_slippage_adverse_50bps": 0.0050,
}
RUNTIME_FILENAMES = {
    "by_test": "dss_gap_004_results_by_test.csv",
    "by_policy": "dss_gap_004_results_by_policy.csv",
    "by_family": "dss_gap_004_results_by_family.csv",
    "summary": "dss_gap_004_dry_run_summary.json",
}


class GapMatrixDryRunError(ValueError):
    decision = "GAP_DRY_RUN_EXECUTION_FAIL"


class GapDryRunLedgerMissing(GapMatrixDryRunError):
    decision = "GAP_DRY_RUN_BLOCKED_LEDGER_MISSING"


class GapDryRunInvalidMatrix(GapMatrixDryRunError):
    decision = "GAP_DRY_RUN_BLOCKED_MATRIX_INVALID"


@dataclass(frozen=True)
class GapDryRunConfig:
    ledger_path: Path
    matrix_path: Path
    output_dir: Path
    cache_only: bool
    no_ibkr: bool
    no_signals: bool
    no_preview: bool
    no_orders: bool
    research_output_dir: Path | None = None


@dataclass(frozen=True)
class GapDryRunResult:
    decision: str
    matrix_rows: int
    ledger_rows: int
    tests_executed: int
    families: list[str]
    policies: list[str]
    runtime_paths: dict[str, str]
    research_paths: dict[str, str]
    no_lookahead_status: str
    safety: dict[str, bool]


def enforce_dry_run_guards(config: GapDryRunConfig) -> None:
    if not config.cache_only:
        raise GapMatrixDryRunError("DSS-GAP-004 requires --cache-only.")
    if not config.no_ibkr:
        raise GapMatrixDryRunError("DSS-GAP-004 refuses IBKR access; pass --no-ibkr.")
    if not config.no_orders:
        raise GapMatrixDryRunError("DSS-GAP-004 refuses order outputs; pass --no-orders.")
    if not config.no_preview:
        raise GapMatrixDryRunError("DSS-GAP-004 refuses preview outputs; pass --no-preview.")
    if not config.no_signals:
        raise GapMatrixDryRunError("DSS-GAP-004 refuses signal outputs; pass --no-signals.")


def run_gap_matrix_dry_run(config: GapDryRunConfig) -> GapDryRunResult:
    enforce_dry_run_guards(config)
    if not config.ledger_path.exists():
        raise GapDryRunLedgerMissing(f"ledger missing: {config.ledger_path}")
    if not config.matrix_path.exists():
        raise GapDryRunInvalidMatrix(f"matrix missing: {config.matrix_path}")

    try:
        rows = read_gap_backtest_matrix_json(config.matrix_path)
        validation = validate_gap_backtest_matrix(rows)
    except Exception as exc:
        raise GapDryRunInvalidMatrix(str(exc)) from exc

    ledger = _read_ledger(config.ledger_path)
    if not ledger:
        raise GapDryRunLedgerMissing(f"ledger empty: {config.ledger_path}")
    _validate_ledger_schema(ledger)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    by_test = [_run_one(row, ledger) for row in rows]
    by_policy = _aggregate(by_test, "portfolio_policy")
    by_family = _aggregate(by_test, "family")

    runtime_paths = {
        "by_test": str(config.output_dir / RUNTIME_FILENAMES["by_test"]),
        "by_policy": str(config.output_dir / RUNTIME_FILENAMES["by_policy"]),
        "by_family": str(config.output_dir / RUNTIME_FILENAMES["by_family"]),
        "summary": str(config.output_dir / RUNTIME_FILENAMES["summary"]),
    }
    _write_csv(Path(runtime_paths["by_test"]), by_test)
    _write_csv(Path(runtime_paths["by_policy"]), by_policy)
    _write_csv(Path(runtime_paths["by_family"]), by_family)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "decision": "GAP_DRY_RUN_COMPLETE_NO_CANDIDATE_APPROVAL",
        "matrix_validation": asdict(validation),
        "ledger_rows": len(ledger),
        "ledger_date_start": min(item["date"] for item in ledger).isoformat(),
        "ledger_date_end": max(item["date"] for item in ledger).isoformat(),
        "tests_executed": len(by_test),
        "families": sorted({item["family"] for item in by_test}),
        "policies": sorted({item["portfolio_policy"] for item in by_test}),
        "baseline_groups": sorted({item["baseline_group"] for item in by_test}),
        "no_lookahead_status": "GAP_DRY_RUN_NO_LOOKAHEAD_PASS",
        "candidate_approval": False,
        "best_threshold_selected": False,
        "runtime_paths": runtime_paths,
        "safety": _safety(),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    Path(runtime_paths["summary"]).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    research_dir = config.research_output_dir or _default_research_output_dir(config.output_dir)
    research_paths = _write_research_summaries(research_dir, by_test, by_policy, by_family, summary)
    return GapDryRunResult(
        decision="GAP_DRY_RUN_COMPLETE_NO_CANDIDATE_APPROVAL",
        matrix_rows=len(rows),
        ledger_rows=len(ledger),
        tests_executed=len(by_test),
        families=summary["families"],
        policies=summary["policies"],
        runtime_paths=runtime_paths,
        research_paths=research_paths,
        no_lookahead_status="GAP_DRY_RUN_NO_LOOKAHEAD_PASS",
        safety=_safety(),
    )


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            raw["date"] = date.fromisoformat(raw["date"])
            rows.append(raw)
    return rows


def _validate_ledger_schema(rows: list[dict[str, Any]]) -> None:
    required = {
        "symbol",
        "date",
        "open",
        "close",
        "volume",
        "gap_pct",
        "abs_gap_pct",
        "gap_vs_atr_prev",
        "gap_direction",
        "open_to_close_return",
        "next_open_to_close_return",
        "is_stock_operational",
        "product_class",
        "data_quality_status",
        "event_quality_status",
    }
    missing = required - set(rows[0])
    if missing:
        raise GapDryRunLedgerMissing(f"ledger schema missing columns: {sorted(missing)}")


def _run_one(row: GapBacktestMatrixRow, ledger: list[dict[str, Any]]) -> dict[str, Any]:
    selected = _select_events(row, ledger)
    returns = [_return_for(row, item) for item in selected]
    is_returns = [value for value, item in zip(returns, selected, strict=True) if item["date"] <= IS_END]
    oos_returns = [
        value for value, item in zip(returns, selected, strict=True) if OOS_START <= item["date"] <= OOS_END
    ]
    symbols_oos = sorted({item["symbol"] for item in selected if OOS_START <= item["date"] <= OOS_END})
    symbol_contrib = _top_contribution(selected, returns, "symbol", 3)
    event_contrib = _top_events(selected, returns, 5)
    by_quarter = _period_counts(selected, returns)
    gross = _metrics(returns)
    net_x1 = _metrics([value - COSTS["cost_x1"] for value in returns])
    net_x2 = _metrics([value - COSTS["cost_x2"] for value in returns])
    net_x3 = _metrics([value - COSTS["cost_x3"] for value in returns])
    slip_10 = _metrics([value - SLIPPAGE["open_slippage_adverse_10bps"] for value in returns])
    slip_25 = _metrics([value - SLIPPAGE["open_slippage_adverse_25bps"] for value in returns])
    slip_50 = _metrics([value - SLIPPAGE["open_slippage_adverse_50bps"] for value in returns])
    max_date = max((item["date"] for item in ledger), default=OOS_END)
    return {
        "test_id": row.test_id,
        "family": row.family,
        "portfolio_policy": row.portfolio_policy,
        "baseline_group": row.baseline_group,
        "is_candidate": row.is_candidate,
        "is_baseline": row.is_baseline,
        "is_placebo": row.is_placebo,
        "events_total": len(selected),
        "events_IS": len(is_returns),
        "events_OOS": len(oos_returns),
        "symbols_OOS": len(symbols_oos),
        "expectancy_gross": gross["expectancy"],
        "expectancy_net_x1": net_x1["expectancy"],
        "expectancy_net_x2": net_x2["expectancy"],
        "expectancy_net_x3": net_x3["expectancy"],
        "pf_gross": gross["profit_factor"],
        "pf_x1": net_x1["profit_factor"],
        "pf_x2": net_x2["profit_factor"],
        "pf_x3": net_x3["profit_factor"],
        "winrate": gross["winrate"],
        "avg_win": gross["avg_win"],
        "avg_loss": gross["avg_loss"],
        "max_drawdown_approx": gross["max_drawdown_approx"],
        "worst_streak": gross["worst_streak"],
        "last12m_expectancy": _window_expectancy(selected, returns, max_date, 365),
        "last24m_expectancy": _window_expectancy(selected, returns, max_date, 730),
        "effective_sample_approx": min(len(returns), len(set((item["symbol"], item["date"]) for item in selected))),
        "top3_symbol_contribution": json.dumps(symbol_contrib, sort_keys=True),
        "top5_event_contribution": json.dumps(event_contrib, sort_keys=True),
        "result_by_year_quarter": json.dumps(by_quarter["returns"], sort_keys=True),
        "event_count_by_year_quarter": json.dumps(by_quarter["counts"], sort_keys=True),
        "cost_slippage_sensitivity": json.dumps(
            {
                "cost_x1": net_x1["expectancy"],
                "cost_x2": net_x2["expectancy"],
                "cost_x3": net_x3["expectancy"],
                "open_slippage_adverse_10bps": slip_10["expectancy"],
                "open_slippage_adverse_25bps": slip_25["expectancy"],
                "open_slippage_adverse_50bps": slip_50["expectancy"],
            },
            sort_keys=True,
        ),
        "safety_flags": "no_orders|no_paper|no_live|no_preview|no_signals|no_ibkr|no_candidate_approval",
    }


def _select_events(row: GapBacktestMatrixRow, ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [item for item in ledger if _base_event_ok(item)]
    if row.baseline_group == "MATCHED_NON_GAP":
        candidates = [item for item in candidates if _float(item.get("abs_gap_pct")) < 0.002]
    elif row.baseline_group == "RANDOM_MATCHED":
        candidates = candidates[:: max(1, len(candidates) // 2000)]
    else:
        threshold = _threshold(row)
        candidates = [item for item in candidates if _threshold_value(item, row.gap_threshold_type) >= threshold]

    if row.direction == "gap_up_only":
        candidates = [item for item in candidates if item["gap_direction"] == "up"]
    elif row.direction == "gap_down_only":
        candidates = [item for item in candidates if item["gap_direction"] == "down"]

    candidates = _apply_design_filters(row, candidates)
    if row.portfolio_policy == "MAX_2_NEW_TRADES_PER_DAY":
        candidates = _max_per_day(candidates, 2)
    if row.portfolio_policy == "ONE_ACTIVE_PER_SYMBOL":
        candidates = _one_active_per_symbol(candidates)
    return candidates


def _return_for(row: GapBacktestMatrixRow, item: dict[str, Any]) -> float:
    sign = 1.0 if item["gap_direction"] == "up" else -1.0
    if row.direction == "sign_inverted":
        sign *= -1.0
    if row.baseline_group == "DELAYED_ENTRY":
        raw = _float(item.get("next_open_to_close_return"))
    elif "SAME_DAY" in row.family:
        raw = _float(item.get("open_to_close_return"))
    else:
        raw = _float(item.get("next_open_to_close_return"))
    if "REVERSAL" in row.family:
        sign *= -1.0
    return sign * raw


def _base_event_ok(item: dict[str, Any]) -> bool:
    return (
        item.get("is_stock_operational") == "True"
        and item.get("product_class", "").upper() in {"STK", "STOCK"}
        and item.get("data_quality_status") == "DATA_OK"
        and item.get("gap_direction") in {"up", "down"}
        and item.get("open_to_close_return") not in {"", None}
        and item.get("next_open_to_close_return") not in {"", None}
    )


def _apply_design_filters(row: GapBacktestMatrixRow, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = rows
    if row.regime_filter == "SPY_return20d_gt_0":
        filtered = [item for item in filtered if _float(item.get("benchmark_spy_return_20d")) > 0]
    elif row.regime_filter == "SPY_return20d_lte_0":
        filtered = [item for item in filtered if _float(item.get("benchmark_spy_return_20d")) <= 0]
    if row.volatility_filter == "atr14_pct_prev_below_median":
        med = _median([_float(item.get("atr14_pct_prev")) for item in filtered if item.get("atr14_pct_prev")])
        filtered = [item for item in filtered if _float(item.get("atr14_pct_prev")) <= med]
    elif row.volatility_filter == "atr14_pct_prev_above_median":
        med = _median([_float(item.get("atr14_pct_prev")) for item in filtered if item.get("atr14_pct_prev")])
        filtered = [item for item in filtered if _float(item.get("atr14_pct_prev")) > med]
    if row.liquidity_filter == "volume_t_minus_1_gte_predefined_threshold":
        filtered = [
            item
            for item in filtered
            if _has_previous_volume(item) and _float(item.get("volume_t_minus_1") or item.get("prev_volume")) >= 100_000
        ]
    return filtered


def _has_previous_volume(item: dict[str, Any]) -> bool:
    return item.get("volume_t_minus_1") not in {"", None} or item.get("prev_volume") not in {"", None}


def _metrics(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {
            "expectancy": 0.0,
            "profit_factor": 0.0,
            "winrate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "max_drawdown_approx": 0.0,
            "worst_streak": 0,
        }
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    streak = worst = 0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)
        streak = streak + 1 if value <= 0 else 0
        worst = max(worst, streak)
    return {
        "expectancy": round(mean(values), 8),
        "profit_factor": round(gross_win / gross_loss, 6) if gross_loss else round(gross_win, 6),
        "winrate": round(len(wins) / len(values), 6),
        "avg_win": round(mean(wins), 8) if wins else 0.0,
        "avg_loss": round(mean(losses), 8) if losses else 0.0,
        "max_drawdown_approx": round(max_dd, 8),
        "worst_streak": worst,
    }


def _aggregate(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    output = []
    for value in sorted({str(row[key]) for row in rows}):
        group = [row for row in rows if row[key] == value]
        events = sum(int(row["events_total"]) for row in group)
        weighted = sum(float(row["expectancy_gross"]) * int(row["events_total"]) for row in group)
        output.append(
            {
                key: value,
                "tests": len(group),
                "events_total": events,
                "events_OOS": sum(int(row["events_OOS"]) for row in group),
                "expectancy_gross_weighted": round(weighted / events, 8) if events else 0.0,
                "candidate_approval": False,
            }
        )
    return output


def _write_research_summaries(
    research_dir: Path,
    by_test: list[dict[str, Any]],
    by_policy: list[dict[str, Any]],
    by_family: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, str]:
    research_dir.mkdir(parents=True, exist_ok=True)
    by_family_path = research_dir / "dss_gap_004_results_summary_by_family.csv"
    by_policy_path = research_dir / "dss_gap_004_results_summary_by_policy.csv"
    observations_path = research_dir / "dss_gap_004_results_summary_top_observations.csv"
    final_json_path = research_dir / "DSS_GAP_004_DECISION.json"
    _write_csv(by_family_path, by_family)
    _write_csv(by_policy_path, by_policy)
    observations = _observations(by_test)
    _write_csv(observations_path, observations)
    final_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "by_family": str(by_family_path),
        "by_policy": str(by_policy_path),
        "observations": str(observations_path),
        "decision": str(final_json_path),
    }


def _default_research_output_dir(output_dir: Path) -> Path:
    normalized = output_dir.as_posix().rstrip("/")
    if normalized.endswith("artifacts/runtime/daily_swing/gap"):
        return Path("research/daily_swing/gap")
    return output_dir / "research_summary"


def _observations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda item: (float(item["expectancy_net_x3"]), int(item["events_OOS"])), reverse=True)
    output = []
    for row in ranked[:10]:
        output.append(
            {
                "observation_type": "OBSERVATION_ONLY_NO_CANDIDATE_APPROVAL",
                "test_id": row["test_id"],
                "family": row["family"],
                "baseline_group": row["baseline_group"],
                "events_OOS": row["events_OOS"],
                "expectancy_net_x3": row["expectancy_net_x3"],
                "candidate_approval": False,
            }
        )
    return output


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _threshold(row: GapBacktestMatrixRow) -> float:
    first = str(row.gap_threshold_value).split()[0]
    return float(first)


def _threshold_value(item: dict[str, Any], threshold_type: str) -> float:
    if threshold_type == "abs_gap_vs_atr_prev":
        return abs(_float(item.get("gap_vs_atr_prev")))
    return _float(item.get(threshold_type))


def _float(value: Any) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def _max_per_day(rows: list[dict[str, Any]], maximum: int) -> list[dict[str, Any]]:
    counts: dict[date, int] = {}
    output = []
    for item in sorted(rows, key=lambda row: (row["date"], row["symbol"])):
        counts[item["date"]] = counts.get(item["date"], 0) + 1
        if counts[item["date"]] <= maximum:
            output.append(item)
    return output


def _one_active_per_symbol(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    last: dict[str, date] = {}
    output = []
    for item in sorted(rows, key=lambda row: (row["symbol"], row["date"])):
        previous = last.get(item["symbol"])
        if previous == item["date"]:
            continue
        output.append(item)
        last[item["symbol"]] = item["date"]
    return output


def _top_contribution(rows: list[dict[str, Any]], returns: list[float], key: str, limit: int) -> list[dict[str, Any]]:
    contrib: dict[str, float] = {}
    for item, value in zip(rows, returns, strict=True):
        contrib[str(item[key])] = contrib.get(str(item[key]), 0.0) + value
    ranked = sorted(contrib.items(), key=lambda pair: abs(pair[1]), reverse=True)[:limit]
    return [{"key": key_value, "contribution": round(value, 8)} for key_value, value in ranked]


def _top_events(rows: list[dict[str, Any]], returns: list[float], limit: int) -> list[dict[str, Any]]:
    ranked = sorted(zip(rows, returns, strict=True), key=lambda pair: abs(pair[1]), reverse=True)[:limit]
    return [
        {"symbol": item["symbol"], "date": item["date"].isoformat(), "return": round(value, 8)}
        for item, value in ranked
    ]


def _period_counts(rows: list[dict[str, Any]], returns: list[float]) -> dict[str, dict[str, Any]]:
    counts: dict[str, int] = {}
    buckets: dict[str, list[float]] = {}
    for item, value in zip(rows, returns, strict=True):
        quarter = (item["date"].month - 1) // 3 + 1
        key = f"{item['date'].year}Q{quarter}"
        counts[key] = counts.get(key, 0) + 1
        buckets.setdefault(key, []).append(value)
    return {"counts": counts, "returns": {key: round(mean(vals), 8) for key, vals in buckets.items()}}


def _window_expectancy(rows: list[dict[str, Any]], returns: list[float], max_date: date, days: int) -> float:
    cutoff = date.fromordinal(max_date.toordinal() - days)
    values = [value for item, value in zip(rows, returns, strict=True) if item["date"] >= cutoff]
    return round(mean(values), 8) if values else 0.0


def _safety() -> dict[str, bool]:
    return {
        "no_orders": True,
        "no_paper": True,
        "no_live": True,
        "no_preview": True,
        "no_signals": True,
        "no_ibkr": True,
        "no_downloads": True,
        "no_cron": True,
        "no_gh": True,
        "no_candidate_approval": True,
        "no_best_threshold_selected": True,
    }
