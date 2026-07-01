#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.research.intraday_research_evidence import (  # noqa: E402
    render_markdown,
    summarize_evidence_directory,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize read-only intraday research evidence JSONL files.")
    parser.add_argument("--evidence-dir", default="artifacts/runtime/research_evidence")
    parser.add_argument("--json-out")
    parser.add_argument("--md-out")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    summary = summarize_evidence_directory(args.evidence_dir)
    markdown = render_markdown(summary)

    if args.json_out:
        json_out = Path(args.json_out)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if args.md_out:
        md_out = Path(args.md_out)
        md_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.write_text(markdown, encoding="utf-8")

    if args.json_only:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(markdown)
        print("JSON:")
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
