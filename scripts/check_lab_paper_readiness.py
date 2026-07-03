#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.laboratory.paper_readiness import (  # noqa: E402
    build_paper_readiness_report,
    settings_from_env_file,
    write_paper_readiness_artifacts,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Lab Paper readiness in dry-run mode without submitting orders.")
    parser.add_argument("--env-file")
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    args = parser.parse_args()

    settings = settings_from_env_file(args.env_file)
    report = build_paper_readiness_report(settings=settings)
    write_paper_readiness_artifacts(report, json_out=args.json_out, md_out=args.md_out)
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    if report["status"] == "BLOCKED":
        return 2
    if report["status"] == "NOT_READY":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
