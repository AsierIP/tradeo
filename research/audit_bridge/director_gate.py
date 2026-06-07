#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PROMOTION_STATUSES = {
    "paper_candidate",
    "premium_candidate",
    "paper_limited_candidate",
    "paper_extended_candidate",
    "ready_for_paper_extended",
    "approved",
    "live_candidate",
    "production_candidate",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Conservative Director gate for Tradeo audit packages.")
    parser.add_argument("package", type=Path)
    parser.add_argument("--min-paper-trades-for-promotion", type=int, default=30)
    parser.add_argument("--max-duplicate-event-share", type=float, default=0.0)
    args = parser.parse_args()

    try:
        rows = {
            "catalog": read_csv(args.package / "pattern_catalog.csv"),
            "events": read_csv(args.package / "pattern_events.csv"),
            "trades": read_csv(args.package / "paper_trades.csv"),
            "fills": read_csv(args.package / "ib_fills.csv"),
            "experiments": read_csv(args.package / "experiment_registry.csv"),
            "metrics": read_csv(args.package / "metrics_by_pattern.csv"),
        }
    except FileNotFoundError as exc:
        print("DIRECTOR GATE INVALID")
        print(f"- missing required file: {exc.filename}")
        return 1

    blockers, summary = evaluate(
        rows,
        min_paper_trades_for_promotion=args.min_paper_trades_for_promotion,
        max_duplicate_event_share=args.max_duplicate_event_share,
    )

    if blockers:
        print("DIRECTOR GATE BLOCKED")
        for blocker in blockers:
            print(f"- {blocker}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 2

    print("DIRECTOR GATE PASSED")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def evaluate(
    rows: dict[str, list[dict[str, str]]],
    *,
    min_paper_trades_for_promotion: int,
    max_duplicate_event_share: float,
) -> tuple[list[str], dict[str, Any]]:
    catalog = rows["catalog"]
    events = rows["events"]
    trades = rows["trades"]
    fills = rows["fills"]
    experiments = rows["experiments"]
    metrics = rows["metrics"]

    blockers: list[str] = []
    statuses = {row.get("pattern_id", ""): (row.get("status") or "").strip().lower() for row in catalog}
    promoted = sorted(pid for pid, status in statuses.items() if status in PROMOTION_STATUSES)

    if not trades:
        blockers.append("paper_trades.csv has zero rows; no pattern can be approved beyond research/watchlist.")
    if not fills:
        blockers.append("ib_fills.csv has zero rows; execution, commission, spread and slippage validation are unavailable.")

    zero_trade_promotions = []
    for row in metrics:
        pid = row.get("pattern_id", "")
        if statuses.get(pid) not in PROMOTION_STATUSES:
            continue
        if as_int(row.get("trade_count")) < min_paper_trades_for_promotion:
            zero_trade_promotions.append(pid)
    if zero_trade_promotions:
        blockers.append("promoted statuses require linked paper trades/fills; offenders: " + preview(zero_trade_promotions))

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

    if len(experiments) >= 100 and not has_multiple_testing_columns(experiments):
        blockers.append(
            f"{len(experiments)} experiment variants were exported without multiple-testing adjusted evidence."
        )

    summary = {
        "patterns": len(catalog),
        "events": len(events),
        "paper_trades": len(trades),
        "fills": len(fills),
        "experiments": len(experiments),
        "promoted_patterns": len(promoted),
        "promoted_pattern_ids_preview": promoted[:20],
        "duplicate_repeated_rows": duplicate_repeated_rows,
        "duplicate_repeated_row_share": round(duplicate_share, 6),
        "non_independent_event_rows": non_independent_rows,
        "pending_independence_rows": pending_independence_rows,
        "sample_count_mismatch_patterns": len(sample_mismatch_patterns),
        "missing_oos_experiments": len(missing_oos),
        "director_gate": "blocked" if blockers else "passed",
    }
    return blockers, summary


def as_int(value: str | None) -> int:
    try:
        text = (value or "").strip()
        return int(float(text)) if text else 0
    except ValueError:
        return 0


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
