#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.db.session import SessionLocal  # noqa: E402
from tradeo.research.intraday_research_forensics import (  # noqa: E402
    build_forensics_report,
    ensure_forensics_scope_integrity,
    render_markdown,
    resolve_run_ids,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only forensics for completed intraday research waves.")
    parser.add_argument("--wave-manifest", action="append", default=[], help="Completed wave manifest. Repeatable.")
    parser.add_argument("--run-ids", action="append", default=[], help="DiscoveryRun IDs, CSV or repeatable.")
    parser.add_argument("--top-candidates", type=int, default=25)
    parser.add_argument("--json-out", default="artifacts/runtime/research_forensics/_forensics.json")
    parser.add_argument("--md-out", default="artifacts/runtime/research_forensics/_forensics.md")
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--allow-scope-violation", action="store_true")
    args = parser.parse_args()

    run_ids = resolve_run_ids(wave_manifests=args.wave_manifest, run_ids=args.run_ids)
    db = SessionLocal()
    try:
        report = build_forensics_report(
            db=db,
            wave_manifests=args.wave_manifest,
            run_ids=run_ids,
            top_candidates=args.top_candidates,
        )
    finally:
        db.close()
    if not args.allow_scope_violation:
        ensure_forensics_scope_integrity(report)

    markdown = render_markdown(report)
    if args.json_out:
        json_out = Path(args.json_out)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if args.md_out:
        md_out = Path(args.md_out)
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(markdown, encoding="utf-8")

    if args.json_only:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(markdown)
        print("JSON:")
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
