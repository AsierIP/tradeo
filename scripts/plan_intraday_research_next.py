#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tradeo.research.intraday_research_planner import (
    IntradayResearchPlanner,
    PlannerInput,
    load_planner_input,
    render_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan the next intraday research experiments from a failed wave.")
    parser.add_argument("--diagnostic-json", default=None, help="Path to a diagnostic JSON payload, if available.")
    parser.add_argument("--selected-count", type=int, default=None)
    parser.add_argument("--readiness-ready", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--readiness-coverage", type=float, default=1.0)
    parser.add_argument("--universe-file", default="/app/artifacts/runtime/universe_intraday_stock_only_v3.csv")
    parser.add_argument("--product-policy", default="stock_only")
    parser.add_argument("--period", default="60d")
    parser.add_argument("--windows", type=int, default=0)
    parser.add_argument("--clusters", type=int, default=0)
    parser.add_argument("--accepted", type=int, default=0)
    parser.add_argument("--rejected", type=int, default=0)
    parser.add_argument("--persisted-candidates", type=int, default=0)
    parser.add_argument(
        "--blocker",
        action="append",
        default=[],
        help="Dominant blocker as key=count. Can be repeated.",
    )
    parser.add_argument(
        "--exact-reason",
        action="append",
        default=[],
        help="Exact rejection reason as key=count. Can be repeated.",
    )
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--md-out", default=None)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    if args.diagnostic_json:
        planner_input = load_planner_input(args.diagnostic_json)
    else:
        if args.selected_count is None:
            raise SystemExit("--selected-count is required unless --diagnostic-json is supplied")
        planner_input = PlannerInput(
            selected_count=args.selected_count,
            readiness_ready=bool(args.readiness_ready),
            readiness_coverage=float(args.readiness_coverage),
            universe_file=args.universe_file,
            product_policy=args.product_policy,
            period=args.period,
            windows=args.windows,
            clusters=args.clusters,
            accepted=args.accepted,
            rejected=args.rejected,
            persisted_candidates=args.persisted_candidates,
            blockers=_pairs(args.blocker),
            exact_rejection_reasons=_pairs(args.exact_reason),
            source="cli",
        )

    plan = IntradayResearchPlanner().plan(planner_input)
    payload = plan.to_dict()
    markdown = render_markdown(plan)

    json_out = Path(args.json_out) if args.json_out else None
    md_out = Path(args.md_out) if args.md_out else None
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(markdown, encoding="utf-8")

    if args.json_only:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(markdown)
        print("JSON:")
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _pairs(values: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        if "=" not in value:
            raise SystemExit(f"expected key=count pair, got {value!r}")
        key, raw_count = value.split("=", 1)
        try:
            count = int(raw_count)
        except ValueError as exc:
            raise SystemExit(f"invalid count in {value!r}") from exc
        out[key.strip()] = count
    return out


if __name__ == "__main__":
    raise SystemExit(main())
