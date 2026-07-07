#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.postsession.improvement_agent import PostSessionImprovementAgent  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the post-session improvement agent without broker, market-data, or order access."
    )
    parser.add_argument("--date", help="Session date in YYYY-MM-DD format. Defaults to today UTC.")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--runtime-root")
    parser.add_argument("--research-root")
    parser.add_argument(
        "--allow-missing-runtime",
        action="store_true",
        help="Emit an inconclusive decision instead of skipping when no session runtime exists.",
    )
    parser.add_argument("--allow-rth", action="store_true", help="Test-only override for RTH guard.")
    parser.add_argument(
        "--no-auto-fixes",
        action="store_true",
        help="Do not apply even eligible safe auto-fixes; still emit proposals.",
    )
    args = parser.parse_args()

    session_date = date.fromisoformat(args.date) if args.date else datetime.now(timezone.utc).date()
    agent = PostSessionImprovementAgent(
        repo_root=args.repo_root,
        runtime_root=args.runtime_root,
        research_root=args.research_root,
    )
    result = agent.run(
        session_date=session_date,
        require_session_runtime=not args.allow_missing_runtime,
        allow_rth=args.allow_rth,
        apply_auto_fixes=not args.no_auto_fixes,
    )
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    decision = result.get("final_decision")
    if decision == "POSTSESSION_BLOCK_NEXT_SESSION":
        return 3
    if decision == "POSTSESSION_INCONCLUSIVE":
        return 2
    if decision in {"POSTSESSION_VALIDATION_FAIL", "POSTSESSION_SECURITY_BLOCKER"}:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

