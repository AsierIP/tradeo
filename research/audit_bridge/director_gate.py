#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXECUTION_PROMOTION_STATUSES = {
    "paper_candidate",
    "premium_candidate",
    "paper_limited_candidate",
    "paper_extended_candidate",
    "ready_for_paper_extended",
    "approved",
    "live_candidate",
    "production_candidate",
    "production",
}

RESEARCH_ONLY_STATUSES = {
    "lab",
    "lab_watchlist",
    "lab_candidate",
    "director_review",
    "needs_confirmation",
    "confirmed_candidate",
    "failed_confirmation",
    "rejected",
    "discard",
    "freeze",
    "refine",
}

REQUIRED_LOOKAHEAD_COLUMNS = {
    "available_data_cutoff_ts",
    "decision_ts",
    "entry_eligible_ts",
    "label_generated_ts",
    "source_bar_hash",
    "split_id",
}

TRAIN_ONLY_EVIDENCE_COLUMNS = {
    "fit_scope",
    "fit_on_train_only",
    "split_protocol",
    "purged_embargo_applied",
    "selection_split",
}

RESEARCH_METRIC_COLUMNS = {
    "winrate",
    "avg_win",
    "avg_loss",
    "payoff_ratio",
    "profit_factor",
    "expectancy",
    "max_drawdown",
    "median_trade",
}


class GateInputsError(RuntimeError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Conservative Director gate for Tradeo audit packages.")
    parser.add_argument("package", type=Path)
    parser.add_argument("--min-paper-trades-for-promotion", type=int, default=30)
    parser.add_argument("--min-fills-for-promotion", type=int, default=30)
    parser.add_argument("--max-duplicate-event-share", type=float, default=0.0)
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--markdown-output", type=Path, default=None)
    parser.add_argument(
        "--allow-blocked-exit-zero",
        action="store_true",
        help="Write BLOCKED status but exit 0. Use this for scheduled audits that must not stop the worker.",
    )
    args = parser.parse_args()

    try:
        rows = load_rows(args.package)
    except (FileNotFoundError, GateInputsError) as exc:
        result = result_payload(
            package=args.package,
            status="invalid",
            blockers=[str(exc)],
            summary={"director_gate": "invalid"},
        )
        write_outputs(result, args.json_output, args.markdown_output)
        print("DIRECTOR GATE INVALID")
        for blocker in result["blockers"]:
            print(f"- {blocker}")
        return 1

    blockers, summary = evaluate(
        rows,
        min_paper_trades_for_promotion=args.min_paper_trades_for_promotion,
        min_fills_for_promotion=args.min_fills_for_promotion,
        max_duplicate_event_share=args.max_duplicate_event_share,
    )
    status = "blocked" if blockers else "passed"
    result = result_payload(package=args.package, status=status, blockers=blockers, summary=summary)
    write_outputs(result, args.json_output, args.markdown_output)

    if blockers:
        print("DIRECTOR GATE BLOCKED")
        for blocker in blockers:
            print(f"- {blocker}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if args.allow_blocked_exit_zero else 2

    print("DIRECTOR GATE PASSED")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def load_rows(package: Path) -> dict[str, list[dict[str, str]]]:
    rows = {
        "catalog": read_csv(package / "pattern_catalog.csv"),
        "events": read_csv(package / "pattern_events.csv"),
        "trades": read_csv(package / "paper_trades.csv"),
        "fills": read_csv(package / "ib_fills.csv"),
        "experiments": read_csv(package / "experiment_registry.csv"),
        "metrics": read_csv(package / "metrics_by_pattern.csv"),
        "metrics_by_regime": read_csv_optional(package / "metrics_by_regime.csv"),
        "metrics_by_entry_variant": read_csv_optional(package / "metrics_by_entry_variant.csv"),
    }
    return rows


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise GateInputsError(f"{path.name} has no CSV header")
        return list(reader)


def read_csv_optional(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv(path)


def evaluate(
    rows: dict[str, list[dict[str, str]]],
    *,
    min_paper_trades_for_promotion: int,
    min_fills_for_promotion: int,
    max_duplicate_event_share: float,
) -> tuple[list[str], dict[str, Any]]:
    catalog = rows["catalog"]
    events = rows["events"]
    trades = rows["trades"]
    fills = rows["fills"]
    experiments = rows["experiments"]
    metrics = rows["metrics"]
    metrics_by_regime = rows.get("metrics_by_regime", [])
    metrics_by_entry_variant = rows.get("metrics_by_entry_variant", [])

    blockers: list[str] = []
    statuses = {row.get("pattern_id", ""): (row.get("status") or "").strip().lower() for row in catalog}
    promoted = sorted(pid for pid, status in statuses.items() if status in EXECUTION_PROMOTION_STATUSES)
    unknown_statuses = sorted(
        {status for status in statuses.values() if status and status not in EXECUTION_PROMOTION_STATUSES | RESEARCH_ONLY_STATUSES}
    )

    if not catalog:
        blockers.append("pattern_catalog.csv has zero rows; no pattern inventory is auditable.")
    if not events:
        blockers.append("pattern_events.csv has zero rows; sample counts cannot be reconstructed from an event ledger.")
    if not trades:
        blockers.append("paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.")
    if not fills:
        blockers.append("ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.")
    if unknown_statuses:
        blockers.append("unknown pattern statuses require explicit Director mapping: " + preview(unknown_statuses))

    zero_trade_promotions = []
    for row in metrics:
        pid = row.get("pattern_id", "")
        if statuses.get(pid) not in EXECUTION_PROMOTION_STATUSES:
            continue
        if as_int(row.get("trade_count")) < min_paper_trades_for_promotion:
            zero_trade_promotions.append(pid)
    if zero_trade_promotions:
        blockers.append("promoted statuses require linked paper trades; offenders: " + preview(zero_trade_promotions))

    if promoted and len(fills) < min_fills_for_promotion:
        blockers.append(
            f"promoted statuses require at least {min_fills_for_promotion} IB Paper fills; package has {len(fills)}."
        )

    research_metric_offenders = research_metrics_in_operational_columns(metrics)
    if research_metric_offenders:
        blockers.append(
            "research R metrics are populated in operational metric columns while trade_count is zero; offenders: "
            + preview(research_metric_offenders)
        )

    event_columns = set().union(*(row.keys() for row in events)) if events else set()
    missing_lookahead_columns = sorted(REQUIRED_LOOKAHEAD_COLUMNS - event_columns)
    if missing_lookahead_columns:
        blockers.append("event ledger lacks anti-lookahead cutoff columns: " + ", ".join(missing_lookahead_columns))

    close_entry_patterns = [
        row.get("pattern_id", "")
        for row in catalog
        if "close of the final bar" in (row.get("entry_rule_plaintext") or "").lower()
        or "latest close as signal/entry" in (row.get("entry_rule_plaintext") or "").lower()
    ]
    if close_entry_patterns and "entry_eligible_ts" not in event_columns:
        blockers.append(
            "same-bar close entry model lacks entry_eligible_ts proof; offenders: " + preview(close_entry_patterns)
        )

    duplicate_counts = Counter(
        (row.get("duplicate_group_id") or "").strip()
        for row in events
        if (row.get("duplicate_group_id") or "").strip()
    )
    duplicate_repeated_rows = sum(count for count in duplicate_counts.values() if count > 1)
    duplicate_share = duplicate_repeated_rows / len(events) if events else 0.0
    if duplicate_share > max_duplicate_event_share:
        blockers.append(
            f"duplicate_group_id repeats exceed gate: {duplicate_repeated_rows}/{len(events)} rows ({duplicate_share:.2%})."
        )

    independent_events_by_pattern: Counter[str] = Counter()
    non_independent_rows = 0
    pending_independence_rows = 0
    for row in events:
        value = (row.get("is_independent_sample") or "").strip().lower()
        if value == "true":
            independent_events_by_pattern[row.get("pattern_id", "")] += 1
        else:
            non_independent_rows += 1
            if value not in {"false", "0", "no"}:
                pending_independence_rows += 1
    if non_independent_rows:
        blockers.append(f"{non_independent_rows} event rows are not verified independent samples.")
    if pending_independence_rows:
        blockers.append(f"{pending_independence_rows} event rows have pending/unknown independence labels.")

    sample_mismatch_patterns = []
    for row in metrics:
        pid = row.get("pattern_id", "")
        reported = as_int(row.get("independent_sample_count"))
        observed = independent_events_by_pattern.get(pid, 0)
        if reported and observed and reported > observed:
            sample_mismatch_patterns.append(pid)
    if sample_mismatch_patterns:
        blockers.append(
            "independent_sample_count is not reconstructable from exported event rows for "
            f"{len(sample_mismatch_patterns)} patterns."
        )

    regimes = {(row.get("market_regime") or "").strip().lower() for row in events if row.get("market_regime")}
    if not regimes or regimes <= {"not_persisted", "unknown", "none"}:
        blockers.append("market_regime is not persisted; cross-regime robustness cannot be audited.")
    sectors = {(row.get("sector") or "").strip().lower() for row in events if row.get("sector")}
    if not sectors or sectors <= {"not_persisted", "unknown", "none"}:
        blockers.append("sector is not persisted; cross-sector concentration cannot be audited.")

    missing_oos = [
        row.get("experiment_id", "")
        for row in experiments
        if not (row.get("out_of_sample_start") or "").strip()
        or not (row.get("out_of_sample_end") or "").strip()
    ]
    if experiments and len(missing_oos) == len(experiments):
        blockers.append("no experiment has explicit out_of_sample_start/out_of_sample_end boundaries.")

    train_only_evidence_missing = False
    if experiments:
        experiment_columns = set().union(*(row.keys() for row in experiments))
        train_only_evidence_missing = not bool(experiment_columns & TRAIN_ONLY_EVIDENCE_COLUMNS)
        if train_only_evidence_missing:
            blockers.append(
                "no train-only fit evidence fields found; cannot prove scaler/clustering/R:R selection avoided OOS contamination."
            )

    if len(experiments) >= 20 and not has_multiple_testing_columns(experiments):
        blockers.append(
            f"{len(experiments)} experiment variants were exported without multiple-testing adjusted evidence."
        )

    by_regime = bucket_breakdown(
        metrics_by_regime,
        bucket_column="market_regime",
        missing_reason=(
            "metrics_by_regime.csv is missing or empty; regenerate audit export with closed_lab_trades "
            "or an explicit no_closed_lab_trades reason."
        ),
    )
    by_entry_variant = bucket_breakdown(
        metrics_by_entry_variant,
        bucket_column="entry_variant_id",
        missing_reason=(
            "metrics_by_entry_variant.csv is missing or empty; regenerate audit export with "
            "signal.metadata_json.entry_variant_id on closed_lab_trades or an explicit no_closed_lab_trades reason."
        ),
    )
    pattern_recommendations = build_pattern_recommendations(
        catalog=catalog,
        events=events,
        metrics=metrics,
        metrics_by_regime=metrics_by_regime,
        metrics_by_entry_variant=metrics_by_entry_variant,
        min_paper_trades_for_promotion=min_paper_trades_for_promotion,
        statuses=statuses,
    )
    actionable_recommendations = package_recommendations(
        blockers=blockers,
        pattern_recommendations=pattern_recommendations,
        min_paper_trades_for_promotion=min_paper_trades_for_promotion,
        min_fills_for_promotion=min_fills_for_promotion,
    )

    summary = {
        "patterns": len(catalog),
        "events": len(events),
        "paper_trades": len(trades),
        "fills": len(fills),
        "experiments": len(experiments),
        "promoted_patterns": len(promoted),
        "promoted_pattern_ids_preview": promoted[:20],
        "unknown_statuses": unknown_statuses,
        "duplicate_repeated_rows": duplicate_repeated_rows,
        "duplicate_repeated_row_share": round(duplicate_share, 6),
        "non_independent_event_rows": non_independent_rows,
        "pending_independence_rows": pending_independence_rows,
        "sample_count_mismatch_patterns": len(sample_mismatch_patterns),
        "missing_oos_experiments": len(missing_oos),
        "missing_lookahead_columns": missing_lookahead_columns,
        "research_metric_column_offenders": len(research_metric_offenders),
        "train_only_evidence_missing": train_only_evidence_missing,
        "by_regime": by_regime,
        "by_entry_variant": by_entry_variant,
        "actionable_recommendations": actionable_recommendations,
        "pattern_recommendation_count": len(pattern_recommendations),
        "pattern_recommendations": pattern_recommendations,
        "director_gate": "blocked" if blockers else "passed",
    }
    return blockers, summary


def research_metrics_in_operational_columns(metrics: list[dict[str, str]]) -> list[str]:
    offenders = []
    for row in metrics:
        if as_int(row.get("trade_count")) != 0:
            continue
        if any(nonzero_or_nonblank(row.get(column)) for column in RESEARCH_METRIC_COLUMNS):
            offenders.append(row.get("pattern_id", "unknown"))
    return offenders


def bucket_breakdown(
    rows: list[dict[str, str]],
    *,
    bucket_column: str,
    missing_reason: str,
) -> dict[str, Any]:
    if not rows:
        return {"available": False, "buckets": [], "empty_reason": missing_reason}
    available_rows = [
        row
        for row in rows
        if truthy(row.get("analysis_available")) and as_int(row.get("trade_count")) > 0
    ]
    if not available_rows:
        reason = next((row.get("empty_reason", "").strip() for row in rows if row.get("empty_reason")), "")
        return {
            "available": False,
            "buckets": [],
            "empty_reason": reason or missing_reason,
        }
    ranked = sorted(
        available_rows,
        key=lambda row: (
            as_float(row.get("expectancy_r")),
            as_float(row.get("net_pnl")),
            as_int(row.get("trade_count")),
        ),
        reverse=True,
    )
    buckets = [bucket_summary_row(row, bucket_column) for row in ranked[:20]]
    return {
        "available": True,
        "bucket_count": len(available_rows),
        "best": bucket_summary_row(ranked[0], bucket_column),
        "worst": bucket_summary_row(ranked[-1], bucket_column),
        "buckets": buckets,
        "empty_reason": "",
    }


def bucket_summary_row(row: dict[str, str], bucket_column: str) -> dict[str, Any]:
    return {
        "pattern_id": row.get("pattern_id", ""),
        "bucket": row.get(bucket_column, "") or "unknown",
        "trade_count": as_int(row.get("trade_count")),
        "net_pnl": as_float(row.get("net_pnl")),
        "expectancy_r": as_float(row.get("expectancy_r")),
        "winrate": as_float(row.get("winrate")),
        "profit_factor": as_float(row.get("profit_factor")),
        "max_drawdown": as_float(row.get("max_drawdown")),
    }


def build_pattern_recommendations(
    *,
    catalog: list[dict[str, str]],
    events: list[dict[str, str]],
    metrics: list[dict[str, str]],
    metrics_by_regime: list[dict[str, str]],
    metrics_by_entry_variant: list[dict[str, str]],
    min_paper_trades_for_promotion: int,
    statuses: dict[str, str],
) -> list[dict[str, Any]]:
    metrics_by_pattern = {row.get("pattern_id", ""): row for row in metrics}
    events_by_pattern: dict[str, list[dict[str, str]]] = {}
    for row in events:
        events_by_pattern.setdefault(row.get("pattern_id", ""), []).append(row)
    best_regime_by_pattern, worst_regime_by_pattern = pattern_bucket_extremes(
        metrics_by_regime,
        bucket_column="market_regime",
    )
    best_variant_by_pattern, worst_variant_by_pattern = pattern_bucket_extremes(
        metrics_by_entry_variant,
        bucket_column="entry_variant_id",
    )

    recommendations: list[dict[str, Any]] = []
    for row in catalog:
        pid = row.get("pattern_id", "")
        metric = metrics_by_pattern.get(pid, {})
        trade_count = as_int(metric.get("trade_count"))
        independent_samples = as_int(metric.get("independent_sample_count"))
        ticker_count = as_int(metric.get("ticker_count"))
        status = statuses.get(pid, "")
        trades_remaining = max(0, min_paper_trades_for_promotion - trade_count)
        event_blockers = event_gate_blockers(events_by_pattern.get(pid, []))
        actions: list[str] = []

        active_research_statuses = {
            "lab",
            "lab_watchlist",
            "lab_candidate",
            "director_review",
            "needs_confirmation",
            "confirmed_candidate",
        }
        rejected_statuses = {"rejected", "discard", "freeze", "failed_confirmation"}
        if status in EXECUTION_PROMOTION_STATUSES and trades_remaining:
            actions.append(
                f"freeze promoted status; needs {trades_remaining} more linked paper trades before promotion evidence exists"
            )
        elif (
            status in active_research_statuses
            and trade_count == 0
            and independent_samples >= 100
            and ticker_count >= 8
        ):
            actions.append(
                "promising research candidate without confirmation; collect controlled paper trades before ranking by PnL"
            )
        elif status in rejected_statuses and trade_count == 0 and independent_samples >= 100:
            actions.append(
                "broad rejected research memory; keep frozen unless a new hypothesis explains the prior rejection"
            )
        elif trades_remaining:
            actions.append(f"collect {trades_remaining} more closed paper trades before Director review")

        if event_blockers["entry_gate"]:
            actions.append(
                f"debug entry gate before more paper allocation; {event_blockers['entry_gate']} events mention entry-gate blockage"
            )
        if event_blockers["volume"]:
            actions.append(
                f"review volume/liquidity filter; {event_blockers['volume']} events mention volume blockage"
            )
        if not best_variant_by_pattern.get(pid):
            actions.append("entry_variant performance unavailable; missing closed_lab_trades with entry_variant_id")
        if not best_regime_by_pattern.get(pid):
            actions.append("regime performance unavailable; missing closed_lab_trades with regime_key")

        if not actions:
            actions.append("review Director packet; no automatic promotion")

        recommendations.append(
            {
                "pattern_id": pid,
                "pattern_name": row.get("pattern_name", ""),
                "status": status,
                "independent_sample_count": independent_samples,
                "ticker_count": ticker_count,
                "trade_count": trade_count,
                "trades_remaining_for_promotion": trades_remaining,
                "best_entry_variant": best_variant_by_pattern.get(pid, {}),
                "worst_entry_variant": worst_variant_by_pattern.get(pid, {}),
                "best_regime": best_regime_by_pattern.get(pid, {}),
                "worst_regime": worst_regime_by_pattern.get(pid, {}),
                "actions": actions,
            }
        )
    return sorted(
        recommendations,
        key=lambda item: (
            int(item["trades_remaining_for_promotion"] == 0),
            int(item["status"] in EXECUTION_PROMOTION_STATUSES),
            int(item["independent_sample_count"]),
            int(item["ticker_count"]),
        ),
        reverse=True,
    )


def pattern_bucket_extremes(
    rows: list[dict[str, str]],
    *,
    bucket_column: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if not truthy(row.get("analysis_available")) or as_int(row.get("trade_count")) <= 0:
            continue
        grouped.setdefault(row.get("pattern_id", ""), []).append(row)
    best: dict[str, dict[str, Any]] = {}
    worst: dict[str, dict[str, Any]] = {}
    for pid, pattern_rows in grouped.items():
        ranked = sorted(
            pattern_rows,
            key=lambda row: (
                as_float(row.get("expectancy_r")),
                as_float(row.get("net_pnl")),
                as_int(row.get("trade_count")),
            ),
            reverse=True,
        )
        best[pid] = bucket_summary_row(ranked[0], bucket_column)
        worst[pid] = bucket_summary_row(ranked[-1], bucket_column)
    return best, worst


def event_gate_blockers(rows: list[dict[str, str]]) -> dict[str, int]:
    entry_gate = 0
    volume = 0
    for row in rows:
        text = " ".join(
            str(row.get(column, "")).lower()
            for column in ("reason_not_traded", "notes")
        )
        if "entry gate" in text or "entry_gate" in text or "no_operational_trigger" in text:
            entry_gate += 1
        if "volume" in text or "liquidity" in text:
            volume += 1
    return {"entry_gate": entry_gate, "volume": volume}


def package_recommendations(
    *,
    blockers: list[str],
    pattern_recommendations: list[dict[str, Any]],
    min_paper_trades_for_promotion: int,
    min_fills_for_promotion: int,
) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    if any("paper_trades.csv has zero rows" in blocker for blocker in blockers):
        recommendations.append(
            {
                "action": "keep_all_patterns_research_only",
                "priority": "P0",
                "reason": "paper_trades.csv has zero rows; no closed_lab_trades can confirm any pattern",
                "required_data": f"at least {min_paper_trades_for_promotion} linked paper trades for any promoted pattern",
            }
        )
    if any("ib_fills.csv has zero rows" in blocker for blocker in blockers):
        recommendations.append(
            {
                "action": "ingest_ib_paper_fills",
                "priority": "P0",
                "reason": "fills, commissions, spread and slippage are unavailable",
                "required_data": f"at least {min_fills_for_promotion} anonymized IB Paper fills for promoted patterns",
            }
        )
    if any("duplicate_group_id repeats" in blocker for blocker in blockers):
        recommendations.append(
            {
                "action": "deduplicate_or_explain_events",
                "priority": "P0",
                "reason": "duplicate event rows can inflate sample counts and apparent edge",
            }
        )
    if any("out_of_sample" in blocker or "train-only" in blocker for blocker in blockers):
        recommendations.append(
            {
                "action": "add_oos_and_train_only_evidence",
                "priority": "P0",
                "reason": "Director cannot separate discovery from validation without split evidence",
            }
        )
    promising = [
        item
        for item in pattern_recommendations
        if any("promising research candidate" in action for action in item.get("actions", []))
    ][:10]
    if promising:
        recommendations.append(
            {
                "action": "prioritize_controlled_confirmation",
                "priority": "P1",
                "patterns": [item["pattern_id"] for item in promising],
                "reason": "these patterns have samples/tickers but no paper confirmation",
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "action": "prepare_director_review_packet",
                "priority": "P2",
                "reason": "gate did not find blocking package-level issues; Director still decides manually",
            }
        )
    return recommendations


def nonzero_or_nonblank(value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    try:
        return float(text) != 0.0
    except ValueError:
        return True


def result_payload(package: Path, status: str, blockers: list[str], summary: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "package": str(package),
        "status": status,
        "blockers": blockers,
        "summary": summary,
    }
    if summary.get("actionable_recommendations"):
        payload["recommendations"] = summary["actionable_recommendations"]
    if summary.get("pattern_recommendations"):
        payload["pattern_recommendations"] = summary["pattern_recommendations"]
    return payload


def write_outputs(result: dict[str, Any], json_output: Path | None, markdown_output: Path | None) -> None:
    if json_output:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if markdown_output:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Director Gate Result",
            "",
            f"- Created at: `{result['created_at']}`",
            f"- Package: `{result['package']}`",
            f"- Status: `{result['status']}`",
            "",
            "## Blockers",
            "",
        ]
        blockers = result.get("blockers") or []
        if blockers:
            lines.extend(f"- {blocker}" for blocker in blockers)
        else:
            lines.append("- None")
        recommendations = result.get("recommendations") or []
        lines.extend(["", "## Recommendations", ""])
        if recommendations:
            for recommendation in recommendations:
                action = recommendation.get("action", "review")
                priority = recommendation.get("priority", "")
                reason = recommendation.get("reason", "")
                lines.append(f"- `{priority}` `{action}`: {reason}".strip())
        else:
            lines.append("- None")
        pattern_recommendations = result.get("pattern_recommendations") or []
        lines.extend(["", "## Pattern Actions", ""])
        if pattern_recommendations:
            for item in pattern_recommendations[:40]:
                actions = "; ".join(str(action) for action in item.get("actions", [])[:3])
                lines.append(
                    f"- `{item.get('pattern_id')}` trades={item.get('trade_count')} "
                    f"remaining={item.get('trades_remaining_for_promotion')}: {actions}"
                )
        else:
            lines.append("- None")
        lines.extend(["", "## Summary", "", "```json", json.dumps(result.get("summary", {}), indent=2, ensure_ascii=False), "```", ""])
        markdown_output.write_text("\n".join(lines), encoding="utf-8")


def as_int(value: str | None) -> int:
    try:
        text = (value or "").strip()
        return int(float(text)) if text else 0
    except ValueError:
        return 0


def as_float(value: str | None) -> float:
    try:
        text = (value or "").strip()
        return float(text) if text else 0.0
    except ValueError:
        return 0.0


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"true", "1", "yes", "y"}


def has_multiple_testing_columns(rows: list[dict[str, str]]) -> bool:
    if not rows:
        return False
    columns = set().union(*(row.keys() for row in rows))
    wanted = {
        "multiple_testing_adjusted_p_value",
        "adjusted_p_value",
        "deflated_sharpe",
        "permutation_p_value",
    }
    return bool(columns & wanted)


def preview(values: list[str], limit: int = 10) -> str:
    shown = ", ".join(values[:limit])
    if len(values) > limit:
        return f"{shown} (+{len(values) - limit} more)"
    return shown


if __name__ == "__main__":
    sys.exit(main())
