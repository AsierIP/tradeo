#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.laboratory.vwap_shadow_runner import (  # noqa: E402
    ShadowBatchRequest,
    load_symbols,
    run_shadow_batch,
    write_shadow_batch_artifacts,
)


@dataclass(frozen=True, slots=True)
class ShadowCondition:
    vwap_condition: str
    side: str


def parse_conditions(raw: str) -> tuple[ShadowCondition, ...]:
    conditions: list[ShadowCondition] = []
    for item in raw.split(","):
        value = item.strip()
        if not value:
            continue
        if ":" not in value:
            raise ValueError(f"invalid condition {value!r}; expected condition:long|short")
        condition, side = (part.strip() for part in value.split(":", 1))
        if side not in {"long", "short"}:
            raise ValueError(f"invalid side {side!r} for {condition!r}; expected long or short")
        if not condition:
            raise ValueError("condition name cannot be empty")
        conditions.append(ShadowCondition(vwap_condition=condition, side=side))
    if not conditions:
        raise ValueError("at least one condition is required")
    return tuple(conditions)


def run_loop(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_iterations < 1:
        raise ValueError("--max-iterations must be >= 1")
    if args.interval_seconds < 0:
        raise ValueError("--interval-seconds must be >= 0")

    conditions = parse_conditions(args.conditions)
    symbols = load_symbols(symbols=args.symbols, universe_file=args.universe_file, limit=args.limit)
    if not symbols:
        raise ValueError("provide --symbols or --universe-file with at least one symbol")

    output_dir = Path(args.output_dir)
    jsonl_out = Path(args.jsonl_out) if args.jsonl_out else output_dir / "shadow_events_continuous.jsonl"
    summary_json = Path(args.summary_json) if args.summary_json else output_dir / "shadow_continuous_summary.json"
    summary_md = Path(args.summary_md) if args.summary_md else output_dir / "shadow_continuous_summary.md"
    stop_file = Path(args.stop_file) if args.stop_file else None

    started = datetime.now(timezone.utc)
    per_run: list[dict[str, Any]] = []
    total_forbidden = 0
    iterations_completed = 0
    stopped_by_file = False

    for iteration in range(1, args.max_iterations + 1):
        if stop_file and stop_file.exists():
            stopped_by_file = True
            break

        iterations_completed = iteration
        for condition in conditions:
            request = ShadowBatchRequest(
                symbols=tuple(symbols),
                side=condition.side,  # type: ignore[arg-type]
                vwap_condition=condition.vwap_condition,
                timeframe=args.timeframe,
            )
            records, batch_summary = run_shadow_batch(request)
            batch_summary = {
                **batch_summary,
                "iteration": iteration,
                "loop_started_at": started.isoformat(),
            }
            write_shadow_batch_artifacts(
                records,
                batch_summary,
                jsonl_out=jsonl_out,
                summary_json=summary_json,
                summary_md=summary_md,
            )
            per_run.append(batch_summary)
            total_forbidden += int(batch_summary.get("forbidden_outcomes", 0) or 0)

        if iteration < args.max_iterations:
            if stop_file and stop_file.exists():
                stopped_by_file = True
                break
            if args.interval_seconds:
                time.sleep(args.interval_seconds)

    summary = {
        "schema_version": "tradeo.lab_vwap_shadow_loop.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started.isoformat(),
        "status": "blocked_safety" if total_forbidden else "ok",
        "iterations_requested": args.max_iterations,
        "iterations_completed": iterations_completed,
        "stopped_by_file": stopped_by_file,
        "interval_seconds": args.interval_seconds,
        "symbols": symbols,
        "limit": args.limit,
        "conditions": [
            {"vwap_condition": condition.vwap_condition, "side": condition.side}
            for condition in conditions
        ],
        "timeframe": args.timeframe,
        "jsonl_out": str(jsonl_out),
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "orders_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
        "submit_order_called": False,
        "paper_order_submitted": False,
        "live_order_submitted": False,
        "forbidden_outcomes": total_forbidden,
        "runs": per_run,
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    summary_md.write_text(render_loop_markdown(summary), encoding="utf-8")
    return summary


def render_loop_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# VWAP Lab Shadow Continuous Loop",
        "",
        f"- status: `{summary.get('status')}`",
        f"- iterations_completed: `{summary.get('iterations_completed')}`",
        f"- stopped_by_file: `{summary.get('stopped_by_file')}`",
        f"- events_jsonl: `{summary.get('jsonl_out')}`",
        f"- forbidden_outcomes: `{summary.get('forbidden_outcomes')}`",
        f"- orders_allowed: `{summary.get('orders_allowed')}`",
        f"- paper_allowed: `{summary.get('paper_allowed')}`",
        f"- live_allowed: `{summary.get('live_allowed')}`",
        f"- submit_order_called: `{summary.get('submit_order_called')}`",
        "",
        "This loop is bounded by --max-iterations and defaults to one iteration. It only calls the read-only VWAP shadow batch runner.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run bounded read-only VWAP Lab shadow batches.")
    parser.add_argument("--symbols")
    parser.add_argument("--universe-file")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeframe", default="1m")
    parser.add_argument(
        "--conditions",
        default="vwap_reclaim_long:long,vwap_reject_short:short",
        help="Comma-separated condition:side pairs, e.g. vwap_reclaim_long:long,vwap_reject_short:short.",
    )
    parser.add_argument("--interval-seconds", type=float, default=0.0)
    parser.add_argument("--max-iterations", type=int, default=1)
    parser.add_argument("--stop-file")
    parser.add_argument("--output-dir", default="artifacts/runtime/lab_shadow")
    parser.add_argument("--jsonl-out")
    parser.add_argument("--summary-json")
    parser.add_argument("--summary-md")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        summary = run_loop(args)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 1 if summary["forbidden_outcomes"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
