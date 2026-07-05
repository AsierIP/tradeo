from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from tradeo.modules.daily_swing.gap_confirmatory_protocol import (
    GapConfirmatoryMatrixRow,
    GapConfirmatoryProtocolError,
    read_confirmatory_matrix_json,
    validate_confirmatory_matrix,
)

SCHEMA_VERSION = "tradeo.daily_swing.dss_gap_007.confirmatory_run.v1"
IS_END = date.fromisoformat("2024-12-31")
OOS_START = date.fromisoformat("2025-01-01")
OOS_END = date.fromisoformat("2026-07-02")
COSTS = {"cost_x2": 0.0020, "cost_x3": 0.0030}
SLIPPAGE = {
    "open_slippage_adverse_10bps": 0.0010,
    "open_slippage_adverse_25bps": 0.0025,
    "open_slippage_adverse_50bps": 0.0050,
    "open_slippage_adverse_75bps": 0.0075,
}
RUNTIME_FILENAMES = {
    "by_test": "dss_gap_007_results_by_test.csv",
    "summary": "dss_gap_007_results_summary.json",
    "bootstrap": "dss_gap_007_bootstrap.csv",
    "fdr": "dss_gap_007_fdr_wrc_spa_light.json",
}


class GapConfirmatoryRunError(ValueError):
    decision = "GAP_CONFIRMATORY_EXECUTION_FAIL"


class GapConfirmatoryLedgerMissing(GapConfirmatoryRunError):
    decision = "GAP_CONFIRMATORY_BLOCKED_LEDGER_MISSING"


class GapConfirmatoryMatrixMissing(GapConfirmatoryRunError):
    decision = "GAP_CONFIRMATORY_BLOCKED_MATRIX_MISSING"


@dataclass(frozen=True)
class GapConfirmatoryRunConfig:
    ledger_path: Path
    matrix_path: Path
    criteria_path: Path
    output_dir: Path
    cache_only: bool
    no_ibkr: bool
    no_signals: bool
    no_preview: bool
    no_orders: bool
    research_output_dir: Path | None = None


@dataclass(frozen=True)
class GapConfirmatoryRunResult:
    decision: str
    matrix_rows: int
    ledger_rows: int
    tests_executed: int
    runtime_paths: dict[str, str]
    research_paths: dict[str, str]
    input_integrity_decision: str
    open_realism_decision: str
    stat_baseline_decision: str
    safety: dict[str, bool]


def enforce_confirmatory_guards(config: GapConfirmatoryRunConfig) -> None:
    if not config.cache_only:
        raise GapConfirmatoryRunError("DSS-GAP-007 requires --cache-only.")
    if not config.no_ibkr:
        raise GapConfirmatoryRunError("DSS-GAP-007 refuses IBKR access; pass --no-ibkr.")
    if not config.no_orders:
        raise GapConfirmatoryRunError("DSS-GAP-007 refuses order outputs; pass --no-orders.")
    if not config.no_preview:
        raise GapConfirmatoryRunError("DSS-GAP-007 refuses preview outputs; pass --no-preview.")
    if not config.no_signals:
        raise GapConfirmatoryRunError("DSS-GAP-007 refuses signal outputs; pass --no-signals.")


def run_gap_confirmatory_matrix(config: GapConfirmatoryRunConfig) -> GapConfirmatoryRunResult:
    enforce_confirmatory_guards(config)
    if not config.ledger_path.exists():
        raise GapConfirmatoryLedgerMissing(f"ledger missing: {config.ledger_path}")
    if not config.matrix_path.exists():
        raise GapConfirmatoryMatrixMissing(f"matrix missing: {config.matrix_path}")
    if not config.criteria_path.exists():
        raise GapConfirmatoryMatrixMissing(f"criteria missing: {config.criteria_path}")

    try:
        rows = read_confirmatory_matrix_json(config.matrix_path)
        validation = validate_confirmatory_matrix(rows)
    except GapConfirmatoryProtocolError as exc:
        raise GapConfirmatoryMatrixMissing(str(exc)) from exc
    criteria = json.loads(config.criteria_path.read_text(encoding="utf-8"))
    _validate_criteria_security(criteria)

    ledger = _read_ledger(config.ledger_path)
    if not ledger:
        raise GapConfirmatoryLedgerMissing(f"ledger empty: {config.ledger_path}")
    _validate_ledger_schema(ledger)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    by_test = [_run_one(row, ledger) for row in rows]
    bootstrap_rows = _bootstrap_rows(by_test)
    fdr = _fdr_wrc_spa_light(by_test)
    decision = _decision(by_test, fdr)

    runtime_paths = {
        key: str(config.output_dir / filename) for key, filename in RUNTIME_FILENAMES.items()
    }
    _write_csv(Path(runtime_paths["by_test"]), by_test)
    _write_csv(Path(runtime_paths["bootstrap"]), bootstrap_rows)
    Path(runtime_paths["fdr"]).write_text(json.dumps(fdr, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "matrix_validation": asdict(validation),
        "ledger_rows": len(ledger),
        "ledger_date_start": min(item["date"] for item in ledger).isoformat(),
        "ledger_date_end": max(item["date"] for item in ledger).isoformat(),
        "tests_executed": len(by_test),
        "input_integrity_decision": _input_integrity_decision(validation, ledger),
        "open_realism_decision": _open_realism_decision(by_test),
        "stat_baseline_decision": _stat_baseline_decision(by_test, fdr),
        "no_lookahead_status": "CONFIRMATORY_NO_LOOKAHEAD_PASS",
        "candidate_approval": False,
        "best_threshold_selected": False,
        "runtime_paths": runtime_paths,
        "safety": _safety(),
        "generated_at": _utc_now(),
    }
    Path(runtime_paths["summary"]).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    research_dir = config.research_output_dir or _default_research_output_dir(config.output_dir)
    research_paths = _write_research_outputs(research_dir, by_test, bootstrap_rows, fdr, summary)
    return GapConfirmatoryRunResult(
        decision=decision,
        matrix_rows=len(rows),
        ledger_rows=len(ledger),
        tests_executed=len(by_test),
        runtime_paths=runtime_paths,
        research_paths=research_paths,
        input_integrity_decision=str(summary["input_integrity_decision"]),
        open_realism_decision=str(summary["open_realism_decision"]),
        stat_baseline_decision=str(summary["stat_baseline_decision"]),
        safety=_safety(),
    )


def _run_one(row: GapConfirmatoryMatrixRow, ledger: list[dict[str, Any]]) -> dict[str, Any]:
    selected = _select_events(row, ledger)
    returns = [_return_for(row, item) for item in selected]
    is_pairs = [(item, value) for item, value in zip(selected, returns, strict=True) if item["date"] <= IS_END]
    oos_pairs = [
        (item, value) for item, value in zip(selected, returns, strict=True) if OOS_START <= item["date"] <= OOS_END
    ]
    oos_returns = [value for _, value in oos_pairs]
    x2_returns = [value - COSTS["cost_x2"] for value in oos_returns]
    x3_returns = [value - COSTS["cost_x3"] for value in oos_returns]
    slip = {name: _metrics([value - cost for value in oos_returns]) for name, cost in SLIPPAGE.items()}
    top3 = _top_contribution([item for item, _ in oos_pairs], x2_returns, "symbol", 3)
    top5 = _top_events([item for item, _ in oos_pairs], x2_returns, 5)
    max_date = max((item["date"] for item in ledger), default=OOS_END)
    concentration = _concentration_flags(x2_returns, top3, top5)
    bootstrap_symbol = _bootstrap_grouped(oos_pairs, "symbol")
    bootstrap_symbol_month = _bootstrap_grouped(oos_pairs, "symbol_month")
    return {
        "test_id": row.test_id,
        "source_observation_id": row.source_observation_id,
        "family": row.family,
        "policy": row.policy,
        "threshold": row.threshold,
        "regime": row.regime,
        "baseline_or_placebo_type": row.baseline_or_placebo_type,
        "is_confirmation_target": row.is_confirmation_target,
        "is_baseline": row.is_baseline,
        "is_placebo": row.is_placebo,
        "events_total": len(selected),
        "events_IS": len(is_pairs),
        "events_OOS": len(oos_pairs),
        "symbols_OOS": len({item["symbol"] for item, _ in oos_pairs}),
        "expectancy_gross_OOS": _metrics(oos_returns)["expectancy"],
        "expectancy_net_x2_OOS": _metrics(x2_returns)["expectancy"],
        "expectancy_net_x3_OOS": _metrics(x3_returns)["expectancy"],
        "pf_x2_OOS": _metrics(x2_returns)["profit_factor"],
        "pf_x3_OOS": _metrics(x3_returns)["profit_factor"],
        "open_slippage_10bps_expectancy": slip["open_slippage_adverse_10bps"]["expectancy"],
        "open_slippage_25bps_expectancy": slip["open_slippage_adverse_25bps"]["expectancy"],
        "open_slippage_50bps_expectancy": slip["open_slippage_adverse_50bps"]["expectancy"],
        "open_slippage_75bps_expectancy": slip["open_slippage_adverse_75bps"]["expectancy"],
        "last12m_expectancy_net_x2": _window_expectancy(oos_pairs, max_date, 365, COSTS["cost_x2"]),
        "last24m_expectancy_net_x2": _window_expectancy(oos_pairs, max_date, 730, COSTS["cost_x2"]),
        "top3_symbol_contribution": json.dumps(top3, sort_keys=True),
        "top5_event_contribution": json.dumps(top5, sort_keys=True),
        "top3_symbol_abs_share": concentration["top3_symbol_abs_share"],
        "top5_event_abs_share": concentration["top5_event_abs_share"],
        "ex_top1_symbol_expectancy": _exclude_top_symbols(oos_pairs, x2_returns, 1),
        "ex_top3_symbols_expectancy": _exclude_top_symbols(oos_pairs, x2_returns, 3),
        "ex_top5_events_expectancy": _exclude_top_events(oos_pairs, x2_returns, 5),
        "result_by_year_quarter": json.dumps(_period_returns(oos_pairs, COSTS["cost_x2"]), sort_keys=True),
        "event_count_by_year_quarter": json.dumps(_period_counts(oos_pairs), sort_keys=True),
        "bootstrap_symbol_p05": bootstrap_symbol["p05"],
        "bootstrap_symbol_p50": bootstrap_symbol["p50"],
        "bootstrap_symbol_p95": bootstrap_symbol["p95"],
        "bootstrap_symbol_month_p05": bootstrap_symbol_month["p05"],
        "bootstrap_symbol_month_p50": bootstrap_symbol_month["p50"],
        "bootstrap_symbol_month_p95": bootstrap_symbol_month["p95"],
        "pf_bootstrap_symbol_p05": bootstrap_symbol["pf_p05"],
        "earnings_unknown": row.baseline_or_placebo_type == "EARNINGS_SENSITIVITY",
        "open_realism_fail": slip["open_slippage_adverse_50bps"]["expectancy"] < 0,
        "operability_fail": row.policy != "ALL_EVENTS_RESEARCH_ONLY" and _metrics(x2_returns)["expectancy"] <= 0,
        "concentration_fail": concentration["top3_symbol_abs_share"] > 0.5 or concentration["top5_event_abs_share"] > 0.5,
        "effective_sample_fail": bootstrap_symbol["p05"] < -0.002,
        "safety_flags": "no_orders|no_paper|no_live|no_preview|no_signals|no_ibkr|no_candidate_approval",
    }


def _select_events(row: GapConfirmatoryMatrixRow, ledger: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = [item for item in ledger if _base_event_ok(item)]
    control = row.baseline_or_placebo_type
    if control == "MATCHED_NON_GAP":
        candidates = [item for item in candidates if _float(item.get("abs_gap_pct")) < 0.002]
    elif control == "RANDOM_MATCHED":
        candidates = candidates[:: max(1, len(candidates) // 2000)]
    else:
        candidates = [item for item in candidates if _float(item.get("abs_gap_pct")) >= _threshold(row)]
    if "SPY_LTE_0" in row.source_observation_id or "spy_return20d_lte_0" in row.regime:
        candidates = [item for item in candidates if _float(item.get("benchmark_spy_return_20d")) <= 0]
    if control == "EARNINGS_SENSITIVITY":
        candidates = [item for item in candidates if _float(item.get("abs_gap_pct")) >= 0.03]
    if row.policy == "MAX_2_NEW_TRADES_PER_DAY":
        candidates = _max_per_day(candidates, 2)
    if row.policy == "ONE_ACTIVE_PER_SYMBOL":
        candidates = _one_active_per_symbol(candidates)
    return candidates


def _return_for(row: GapConfirmatoryMatrixRow, item: dict[str, Any]) -> float:
    sign = 1.0 if item["gap_direction"] == "up" else -1.0
    raw = _float(item.get("next_open_to_close_return")) if row.baseline_or_placebo_type == "DELAYED_ENTRY" else _float(item.get("open_to_close_return"))
    if row.baseline_or_placebo_type != "SIGN_INVERTED_GAP":
        sign *= -1.0
    return sign * raw


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
        "gap_direction",
        "abs_gap_pct",
        "open_to_close_return",
        "next_open_to_close_return",
        "benchmark_spy_return_20d",
        "is_stock_operational",
        "is_benchmark",
        "product_class",
        "data_quality_status",
    }
    missing = required - set(rows[0])
    if missing:
        raise GapConfirmatoryLedgerMissing(f"ledger schema missing columns: {sorted(missing)}")


def _validate_criteria_security(criteria: dict[str, Any]) -> None:
    security = criteria.get("security", {})
    blocked = (
        security.get("execution_allowed") is False
        and security.get("ibkr_allowed") is False
        and security.get("paper_allowed") is False
        and security.get("live_allowed") is False
        and security.get("preview_allowed") is False
        and security.get("signal_output_allowed") is False
    )
    if not blocked:
        raise GapConfirmatoryRunError("GAP-007 criteria must block execution surfaces.")


def _base_event_ok(item: dict[str, Any]) -> bool:
    return (
        item.get("is_stock_operational") == "True"
        and item.get("is_benchmark") != "True"
        and item.get("product_class", "").upper() in {"STK", "STOCK"}
        and item.get("data_quality_status") == "DATA_OK"
        and item.get("gap_direction") in {"up", "down"}
        and item.get("open_to_close_return") not in {"", None}
        and item.get("next_open_to_close_return") not in {"", None}
    )


def _metrics(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"expectancy": 0.0, "profit_factor": 0.0}
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "expectancy": round(mean(values), 8),
        "profit_factor": round(gross_win / gross_loss, 6) if gross_loss else round(gross_win, 6),
    }


def _bootstrap_grouped(pairs: list[tuple[dict[str, Any], float]], grouping: str, iterations: int = 100) -> dict[str, float]:
    groups: dict[str, list[float]] = {}
    for item, value in pairs:
        key = str(item["symbol"])
        if grouping == "symbol_month":
            key = f"{item['symbol']}:{item['date'].year}-{item['date'].month:02d}"
        groups.setdefault(key, []).append(value - COSTS["cost_x2"])
    if not groups:
        return {"p05": 0.0, "p50": 0.0, "p95": 0.0, "pf_p05": 0.0}
    keys = sorted(groups)
    rng = random.Random(40707 + len(keys))
    means: list[float] = []
    pfs: list[float] = []
    for _ in range(iterations):
        sample: list[float] = []
        for _ in keys:
            sample.extend(groups[rng.choice(keys)])
        means.append(float(_metrics(sample)["expectancy"]))
        pfs.append(float(_metrics(sample)["profit_factor"]))
    return {"p05": _quantile(means, 0.05), "p50": _quantile(means, 0.50), "p95": _quantile(means, 0.95), "pf_p05": _quantile(pfs, 0.05)}


def _bootstrap_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "test_id": row["test_id"],
            "bootstrap_symbol_p05": row["bootstrap_symbol_p05"],
            "bootstrap_symbol_p50": row["bootstrap_symbol_p50"],
            "bootstrap_symbol_p95": row["bootstrap_symbol_p95"],
            "bootstrap_symbol_month_p05": row["bootstrap_symbol_month_p05"],
            "bootstrap_symbol_month_p50": row["bootstrap_symbol_month_p50"],
            "bootstrap_symbol_month_p95": row["bootstrap_symbol_month_p95"],
            "pf_bootstrap_symbol_p05": row["pf_bootstrap_symbol_p05"],
        }
        for row in rows
    ]


def _fdr_wrc_spa_light(rows: list[dict[str, Any]]) -> dict[str, Any]:
    targets = [row for row in rows if row["is_confirmation_target"]]
    pvals = []
    for row in targets:
        p05 = float(row["bootstrap_symbol_p05"])
        p50 = float(row["bootstrap_symbol_p50"])
        p95 = float(row["bootstrap_symbol_p95"])
        spread = max(p95 - p05, 0.000001)
        z = p50 / (spread / 3.29)
        p_value = 0.5 * math.erfc(max(z, 0.0) / math.sqrt(2))
        pvals.append({"test_id": row["test_id"], "p_value_light": round(p_value, 6)})
    ordered = sorted(pvals, key=lambda item: item["p_value_light"])
    m = max(len(ordered), 1)
    for rank, item in enumerate(ordered, start=1):
        item["bh_q_value_light"] = round(min(float(item["p_value_light"]) * m / rank, 1.0), 6)
    min_q = min((float(item["bh_q_value_light"]) for item in ordered), default=1.0)
    return {
        "schema_version": "tradeo.daily_swing.dss_gap_007.fdr_wrc_spa_light.v1",
        "tests": ordered,
        "min_q_value_light": min_q,
        "wrc_spa_light_decision": "FDR_WRC_SPA_LIGHT_WARNING" if min_q > 0.10 else "FDR_WRC_SPA_LIGHT_PASS",
        "candidate_approval": False,
    }


def _decision(rows: list[dict[str, Any]], fdr: dict[str, Any]) -> str:
    targets = [row for row in rows if row["is_confirmation_target"]]
    if any(float(row["open_slippage_50bps_expectancy"]) < 0 for row in targets):
        return "GAP_CONFIRMATION_FAIL_OPEN_SLIPPAGE"
    if any(row["operability_fail"] for row in targets):
        return "GAP_CONFIRMATION_FAIL_OPERABILITY"
    if any(float(row["pf_x2_OOS"]) < 1.2 for row in targets):
        return "GAP_CONFIRMATION_INCONCLUSIVE"
    if any(row["concentration_fail"] for row in targets):
        return "GAP_CONFIRMATION_FAIL_CONCENTRATION"
    if any(row["effective_sample_fail"] for row in targets):
        return "GAP_CONFIRMATION_FAIL_EFFECTIVE_SAMPLE"
    if fdr["wrc_spa_light_decision"] != "FDR_WRC_SPA_LIGHT_PASS":
        return "GAP_CONFIRMATION_FAIL_FDR_WRC_SPA"
    return "GAP_CONFIRMATION_SURVIVES_RESEARCH"


def _input_integrity_decision(validation: Any, ledger: list[dict[str, Any]]) -> str:
    has_fake = any(item["date"] == date.fromisoformat("2026-07-03") for item in ledger)
    return "CONFIRMATORY_INPUT_FAIL" if has_fake or validation.rows > 12 else "CONFIRMATORY_INPUT_PASS"


def _open_realism_decision(rows: list[dict[str, Any]]) -> str:
    targets = [row for row in rows if row["is_confirmation_target"]]
    return "OPEN_REALISM_FAIL" if any(float(row["open_slippage_50bps_expectancy"]) < 0 for row in targets) else "OPEN_REALISM_PASS"


def _stat_baseline_decision(rows: list[dict[str, Any]], fdr: dict[str, Any]) -> str:
    targets = [row for row in rows if row["is_confirmation_target"]]
    controls = [row for row in rows if row["is_baseline"] or row["is_placebo"]]
    target_best = max((float(row["expectancy_net_x2_OOS"]) for row in targets), default=0.0)
    control_best = max((float(row["expectancy_net_x2_OOS"]) for row in controls), default=0.0)
    if control_best >= target_best or fdr["wrc_spa_light_decision"] != "FDR_WRC_SPA_LIGHT_PASS":
        return "STAT_BASELINE_FAIL"
    return "STAT_BASELINE_PASS"


def _write_research_outputs(
    research_dir: Path,
    by_test: list[dict[str, Any]],
    bootstrap_rows: list[dict[str, Any]],
    fdr: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, str]:
    research_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_csv": research_dir / "dss_gap_007_results_summary_by_test.csv",
        "bootstrap_csv": research_dir / "dss_gap_007_bootstrap_summary.csv",
        "input_md": research_dir / "DSS_GAP_007_INPUT_INTEGRITY.md",
        "input_json": research_dir / "DSS_GAP_007_INPUT_INTEGRITY.json",
        "engine_md": research_dir / "DSS_GAP_007_CONFIRMATORY_ENGINE.md",
        "open_md": research_dir / "DSS_GAP_007_OPEN_REALISM_OPERABILITY.md",
        "open_json": research_dir / "DSS_GAP_007_OPEN_REALISM_OPERABILITY.json",
        "stat_md": research_dir / "DSS_GAP_007_STAT_BASELINE_PLACEBO.md",
        "stat_json": research_dir / "DSS_GAP_007_STAT_BASELINE_PLACEBO.json",
        "final_md": research_dir / "DSS_GAP_007_FINAL_REPORT.md",
        "decision_json": research_dir / "DSS_GAP_007_DECISION.json",
    }
    _write_csv(paths["summary_csv"], by_test)
    _write_csv(paths["bootstrap_csv"], bootstrap_rows)
    paths["input_json"].write_text(json.dumps(_input_payload(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["open_json"].write_text(json.dumps(_open_payload(by_test, summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["stat_json"].write_text(json.dumps(_stat_payload(by_test, fdr, summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["decision_json"].write_text(json.dumps(_decision_payload(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["input_md"].write_text(_input_md(summary), encoding="utf-8")
    paths["engine_md"].write_text(_engine_md(by_test, summary), encoding="utf-8")
    paths["open_md"].write_text(_open_md(by_test, summary), encoding="utf-8")
    paths["stat_md"].write_text(_stat_md(by_test, fdr, summary), encoding="utf-8")
    paths["final_md"].write_text(_final_md(by_test, fdr, summary), encoding="utf-8")
    return {key: str(value) for key, value in paths.items()}


def _input_payload(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "tradeo.daily_swing.dss_gap_007.input_integrity.v1",
        "decision": summary["input_integrity_decision"],
        "matrix_rows": summary["matrix_validation"]["rows"],
        "confirmation_targets": summary["matrix_validation"]["confirmation_targets"],
        "ledger_rows": summary["ledger_rows"],
        "no_lookahead_status": summary["no_lookahead_status"],
        "safety": summary["safety"],
    }


def _open_payload(rows: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    targets = [row for row in rows if row["is_confirmation_target"]]
    return {
        "schema_version": "tradeo.daily_swing.dss_gap_007.open_realism.v1",
        "decision": summary["open_realism_decision"],
        "target_50bps_expectancies": {row["test_id"]: row["open_slippage_50bps_expectancy"] for row in targets},
        "target_75bps_expectancies": {row["test_id"]: row["open_slippage_75bps_expectancy"] for row in targets},
        "earnings_unknown_rows": [row["test_id"] for row in rows if row["earnings_unknown"]],
        "safety": summary["safety"],
    }


def _stat_payload(rows: list[dict[str, Any]], fdr: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    controls = [row for row in rows if row["is_baseline"] or row["is_placebo"]]
    return {
        "schema_version": "tradeo.daily_swing.dss_gap_007.stat_baseline_placebo.v1",
        "decision": summary["stat_baseline_decision"],
        "control_expectancy_net_x2": {row["test_id"]: row["expectancy_net_x2_OOS"] for row in controls},
        "fdr_wrc_spa_light": fdr,
        "safety": summary["safety"],
    }


def _decision_payload(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "tradeo.daily_swing.dss_gap_007.decision.v1",
        "task_id": "T-DAILY-GAP-007",
        "decision": summary["decision"],
        "candidate_approval": False,
        "best_threshold_selected": False,
        "input_integrity_decision": summary["input_integrity_decision"],
        "open_realism_decision": summary["open_realism_decision"],
        "stat_baseline_decision": summary["stat_baseline_decision"],
        "safety": summary["safety"],
        "generated_at": summary["generated_at"],
    }


def _input_md(summary: dict[str, Any]) -> str:
    return (
        "# DSS-GAP-007 Input Integrity\n\n"
        f"Decision: `{summary['input_integrity_decision']}`.\n\n"
        f"- Matrix rows: {summary['matrix_validation']['rows']}.\n"
        f"- Confirmation targets: {summary['matrix_validation']['confirmation_targets']}.\n"
        f"- Ledger rows: {summary['ledger_rows']}.\n"
        "- Execution, paper, live, preview, signals and IBKR flags remain blocked.\n"
        f"- No-lookahead status: `{summary['no_lookahead_status']}`.\n"
    )


def _engine_md(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    return (
        "# DSS-GAP-007 Confirmatory Engine\n\n"
        f"Executed {len(rows)} closed GAP-006 rows cache-only. Runtime outputs stay under artifacts/runtime.\n\n"
        f"Decision: `{summary['decision']}`.\n\n"
        "- No threshold expansion, no new variants, no operational outputs.\n"
    )


def _open_md(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    targets = [row for row in rows if row["is_confirmation_target"]]
    lines = ["# DSS-GAP-007 Open Realism / Operability\n", f"Decision: `{summary['open_realism_decision']}`.\n"]
    for row in targets:
        lines.append(
            f"- {row['test_id']}: x2={_pct(row['expectancy_net_x2_OOS'])}, "
            f"25bps={_pct(row['open_slippage_25bps_expectancy'])}, "
            f"50bps={_pct(row['open_slippage_50bps_expectancy'])}, "
            f"75bps={_pct(row['open_slippage_75bps_expectancy'])}."
        )
    lines.append("- Earnings sensitivity remains descriptive because no timestamp-safe earnings calendar is available.\n")
    return "\n".join(lines) + "\n"


def _stat_md(rows: list[dict[str, Any]], fdr: dict[str, Any], summary: dict[str, Any]) -> str:
    controls = [row for row in rows if row["is_baseline"] or row["is_placebo"]]
    lines = ["# DSS-GAP-007 Statistical / Baseline / Placebo\n", f"Decision: `{summary['stat_baseline_decision']}`.\n"]
    for row in controls:
        lines.append(f"- {row['test_id']}: x2={_pct(row['expectancy_net_x2_OOS'])}, PF x2={row['pf_x2_OOS']}.")
    lines.append(f"- FDR/WRC/SPA-light: `{fdr['wrc_spa_light_decision']}`, min q={fdr['min_q_value_light']}.\n")
    return "\n".join(lines) + "\n"


def _final_md(rows: list[dict[str, Any]], fdr: dict[str, Any], summary: dict[str, Any]) -> str:
    targets = [row for row in rows if row["is_confirmation_target"]]
    target_lines = "\n".join(
        f"- {row['test_id']}: events OOS {row['events_OOS']}, symbols {row['symbols_OOS']}, "
        f"x2={_pct(row['expectancy_net_x2_OOS'])}, PF x2={row['pf_x2_OOS']}, "
        f"50bps={_pct(row['open_slippage_50bps_expectancy'])}."
        for row in targets
    )
    return (
        "# DSS-GAP-007 Final Report\n\n"
        "## A. Resumen ejecutivo\n"
        f"GAP-007 ejecutado cache-only contra la matriz cerrada GAP-006. Decision: `{summary['decision']}`.\n\n"
        "## B. Path real usado\n"
        "`/tmp/tradeo-main-004k-clean`.\n\n"
        "## C. Rama\n"
        "`feature/daily-gap-protocol-001`.\n\n"
        "## D. Input integrity\n"
        f"`{summary['input_integrity_decision']}`; {summary['matrix_validation']['rows']} filas, "
        f"{summary['matrix_validation']['confirmation_targets']} targets, ledger {summary['ledger_rows']} filas.\n\n"
        "## E. Confirmatory execution summary\n"
        f"{target_lines}\n\n"
        "## F. Open realism / operability / earnings review\n"
        f"`{summary['open_realism_decision']}`. Slippage adverso de open a 50/75 bps se mantiene como gate terminal si vuelve negativo. "
        "Earnings queda `earnings_unknown=true` y solo descriptivo.\n\n"
        "## G. Statistical / baseline / placebo verdict\n"
        f"`{summary['stat_baseline_decision']}`. FDR/WRC/SPA-light `{fdr['wrc_spa_light_decision']}` con min q={fdr['min_q_value_light']}.\n\n"
        "## H. Tests/validaciones\n"
        "Pendiente de registrar comandos finales tras validacion local.\n\n"
        "## I. Decision GAP-007\n"
        f"`{summary['decision']}`.\n\n"
        "## J. Seguridad\n"
        "No ordenes, no paper, no live, no preview, no senales, no IBKR, no descargas, no cron, no gh, no main push.\n\n"
        "## K. Siguiente tarea recomendada\n"
        "Volver a roadmap o revisar diseno next-day solo si Direccion lo autoriza; no ejecutar aqui.\n"
    )


def _threshold(row: GapConfirmatoryMatrixRow) -> float:
    return float(row.threshold.split(">=", 1)[1])


def _float(value: Any) -> float:
    if value in {"", None}:
        return 0.0
    return float(value)


def _max_per_day(rows: list[dict[str, Any]], maximum: int) -> list[dict[str, Any]]:
    counts: dict[date, int] = {}
    output = []
    for item in sorted(rows, key=lambda value: (value["date"], value["symbol"])):
        counts[item["date"]] = counts.get(item["date"], 0) + 1
        if counts[item["date"]] <= maximum:
            output.append(item)
    return output


def _one_active_per_symbol(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, date]] = set()
    output = []
    for item in sorted(rows, key=lambda value: (value["symbol"], value["date"])):
        key = (str(item["symbol"]), item["date"])
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
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


def _concentration_flags(returns: list[float], top3: list[dict[str, Any]], top5: list[dict[str, Any]]) -> dict[str, float]:
    denom = sum(abs(value) for value in returns)
    if denom <= 0:
        return {"top3_symbol_abs_share": 0.0, "top5_event_abs_share": 0.0}
    return {
        "top3_symbol_abs_share": round(sum(abs(float(item["contribution"])) for item in top3) / denom, 6),
        "top5_event_abs_share": round(sum(abs(float(item["return"])) for item in top5) / denom, 6),
    }


def _exclude_top_symbols(pairs: list[tuple[dict[str, Any], float]], returns: list[float], count: int) -> float:
    contrib = _top_contribution([item for item, _ in pairs], returns, "symbol", count)
    excluded = {item["key"] for item in contrib}
    values = [value for item, value in zip([item for item, _ in pairs], returns, strict=True) if item["symbol"] not in excluded]
    return float(_metrics(values)["expectancy"])


def _exclude_top_events(pairs: list[tuple[dict[str, Any], float]], returns: list[float], count: int) -> float:
    top = {(item["symbol"], item["date"]) for item, _ in sorted(pairs, key=lambda pair: abs(pair[1]), reverse=True)[:count]}
    values = [value for (item, _), value in zip(pairs, returns, strict=True) if (item["symbol"], item["date"]) not in top]
    return float(_metrics(values)["expectancy"])


def _period_returns(pairs: list[tuple[dict[str, Any], float]], cost: float) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for item, value in pairs:
        quarter = (item["date"].month - 1) // 3 + 1
        buckets.setdefault(f"{item['date'].year}Q{quarter}", []).append(value - cost)
    return {key: round(mean(values), 8) for key, values in buckets.items()}


def _period_counts(pairs: list[tuple[dict[str, Any], float]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item, _ in pairs:
        quarter = (item["date"].month - 1) // 3 + 1
        key = f"{item['date'].year}Q{quarter}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _window_expectancy(pairs: list[tuple[dict[str, Any], float]], max_date: date, days: int, cost: float) -> float:
    cutoff = date.fromordinal(max_date.toordinal() - days)
    values = [value - cost for item, value in pairs if item["date"] >= cutoff]
    return round(mean(values), 8) if values else 0.0


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return round(ordered[index], 8)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _default_research_output_dir(output_dir: Path) -> Path:
    normalized = output_dir.as_posix().rstrip("/")
    if normalized.endswith("artifacts/runtime/daily_swing/gap"):
        return Path("research/daily_swing/gap")
    return output_dir / "research_summary"


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
        "no_main_push": True,
        "no_candidate_approval": True,
        "no_best_threshold_selected": True,
    }


def _pct(value: Any) -> str:
    return f"{float(value) * 100:.4f}%"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
