#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.lab_foxhunter.probe_state import ProbeStatePaths, acquire_session_lock, load_or_create, transition, write_state  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Lab Paper Probe daily state and duplicate locks.")
    parser.add_argument("--runtime-root", default="artifacts/runtime/lab_paper_probe")
    parser.add_argument("--date", default="")
    parser.add_argument("--state", choices=sorted({"PREMARKET_READY", "SESSION_ARMED", "SESSION_RUNNING", "SESSION_BLOCKED", "SESSION_COMPLETE", "POST_CLOSE_ANALYZED", "NEEDS_DIRECTOR_REVIEW"}))
    parser.add_argument("--reason", default="manual_state_check")
    parser.add_argument("--lock-session-runner", action="store_true")
    parser.add_argument("--mark-final", action="store_true")
    args = parser.parse_args()

    trading_day = _trading_day(args.date)
    paths = ProbeStatePaths(runtime_root=ROOT / args.runtime_root, trading_day=trading_day)
    state = load_or_create(paths)
    acquired = None

    if args.state:
        state = transition(state, args.state, reason=args.reason)
    if args.lock_session_runner:
        acquired, state = acquire_session_lock(paths, state)
    if args.mark_final:
        paths.final_marker.write_text(json.dumps({"trading_day": trading_day.isoformat(), "marked_at": datetime.now(ZoneInfo("UTC")).isoformat()}) + "\n", encoding="utf-8")
        state["runtime_final_exists"] = True
        state = transition(state, "SESSION_COMPLETE", reason=args.reason or "session_final_marked")

    write_state(paths, state)
    result = {"acquired_session_lock": acquired, "state_file": str(paths.state_file), "state": state}
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.lock_session_runner and acquired is False:
        return 2
    return 0


def _trading_day(value: str):
    if value:
        return datetime.fromisoformat(value).date()
    return datetime.now(ZoneInfo("America/New_York")).date()


if __name__ == "__main__":
    raise SystemExit(main())
