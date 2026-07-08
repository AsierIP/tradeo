#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.modules.research_capacity.capacity_metrics import (  # noqa: E402
    CapacityRunConfig,
    ResearchCapacityError,
    run_capacity_microbench,
    write_capacity_docs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CAPACITY-001 safe cache-only microbenchmarks.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--runtime-root", type=Path, default=Path("artifacts/runtime"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/runtime/research_capacity"))
    parser.add_argument("--research-dir", type=Path, default=Path("research/capacity"))
    parser.add_argument("--max-workload", type=int, default=250)
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-downloads", action="store_true")
    parser.add_argument("--no-ibkr", action="store_true")
    parser.add_argument("--no-orders", action="store_true")
    parser.add_argument("--no-signals", action="store_true")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--no-candidate-approval", action="store_true")
    parser.add_argument("--ibkr", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--orders", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--signals", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preview", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--approve-candidates", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if any((args.ibkr, args.orders, args.signals, args.preview, args.approve_candidates)):
        print("CAPACITY-001 refuses IBKR, orders, signals, preview, and candidate approval.", file=sys.stderr)
        return 2
    config = CapacityRunConfig(
        repo_root=args.repo_root,
        runtime_root=args.runtime_root,
        output_dir=args.output_dir,
        research_dir=args.research_dir,
        max_workload=args.max_workload,
        cache_only=args.cache_only,
        dry_run=args.dry_run,
        no_downloads=args.no_downloads,
        no_ibkr=args.no_ibkr,
        no_orders=args.no_orders,
        no_signals=args.no_signals,
        no_preview=args.no_preview,
        no_candidate_approval=args.no_candidate_approval,
    )
    try:
        payload = run_capacity_microbench(config)
        docs = write_capacity_docs(args.repo_root, payload, args.research_dir)
    except ResearchCapacityError as exc:
        print(f"{exc.decision}: {exc}", file=sys.stderr)
        return 3
    payload["versioned_docs"] = docs
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
