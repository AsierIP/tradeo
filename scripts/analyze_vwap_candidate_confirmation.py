#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.research.intraday_vwap_confirmation import (  # noqa: E402
    analyze_vwap_candidate_confirmation,
    render_markdown,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only VWAP candidate confirmation analyzer.")
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--pattern-key", required=True)
    parser.add_argument("--wave-manifest", required=True)
    parser.add_argument("--forensics-json", required=True)
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--ohlcv-cache-dir", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    parser.add_argument("--min-event-count", type=int, default=30)
    args = parser.parse_args()

    report = analyze_vwap_candidate_confirmation(
        run_id=args.run_id,
        pattern_key=args.pattern_key,
        wave_manifest=args.wave_manifest,
        forensics_json=args.forensics_json,
        evidence_json=args.evidence_json,
        ohlcv_cache_dir=args.ohlcv_cache_dir,
        min_event_count=args.min_event_count,
    )
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False), encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
