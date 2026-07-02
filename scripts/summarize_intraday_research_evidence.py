#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.db.session import SessionLocal  # noqa: E402
from tradeo.research.intraday_research_evidence import (  # noqa: E402
    build_evidence_report,
    render_markdown,
    resolve_run_ids,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only evidence capture for completed intraday research waves."
    )
    parser.add_argument("--wave-manifest", action="append", default=[], help="Completed wave manifest. Repeatable.")
    parser.add_argument("--run-ids", action="append", default=[], help="DiscoveryRun IDs, CSV or repeatable.")
    parser.add_argument("--top-candidates", type=int, default=25)
    parser.add_argument("--max-candidates", type=int, default=25)
    parser.add_argument("--max-samples-per-candidate", type=int, default=500)
    parser.add_argument("--max-total-samples", type=int, default=10_000)
    parser.add_argument("--artifact-root", default="artifacts/runtime/research_evidence")
    parser.add_argument("--json-out", default="artifacts/runtime/research_evidence/_summary.json")
    parser.add_argument("--md-out", default="artifacts/runtime/research_evidence/_summary.md")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    run_ids = resolve_run_ids(wave_manifests=args.wave_manifest, run_ids=args.run_ids)
    db = SessionLocal()
    try:
        report = build_evidence_report(
            db=db,
            wave_manifests=args.wave_manifest,
            run_ids=run_ids,
            top_candidates=args.top_candidates,
            max_candidates=args.max_candidates,
            max_samples_per_candidate=args.max_samples_per_candidate,
            max_total_samples=args.max_total_samples,
            artifact_root=args.artifact_root if not args.json_only else None,
        )
    finally:
        db.close()

    summary_payload = {key: value for key, value in report.items() if key != "samples_by_candidate"}
    markdown = render_markdown(summary_payload)
    if args.json_out and not args.json_only:
        json_out = Path(args.json_out)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    if args.md_out and not args.json_only:
        md_out = Path(args.md_out)
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(markdown, encoding="utf-8")

    if args.json_only:
        print(json.dumps(summary_payload, indent=2, sort_keys=True))
    else:
        print(markdown)
        print("JSON:")
        print(json.dumps(summary_payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
