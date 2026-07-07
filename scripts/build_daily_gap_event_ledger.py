#!/usr/bin/env python3
"""Build the DSS-GAP-002 cache-only gap event ledger.

This runner is inventory/audit only. It refuses non-cache execution, IBKR,
orders, previews, signals, and execute modes.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from tradeo.core.config import get_settings  # noqa: E402
from tradeo.modules.daily_swing.gap_event_ledger import (  # noqa: E402
    CacheMissingError,
    GapLedgerConfig,
    GapLedgerError,
    audit_no_lookahead,
    build_gap_event_ledger,
    config_as_dict,
    validate_cache_and_universe,
    write_research_summaries,
)
from tradeo.modules.resource_policy.enforcement import (  # noqa: E402
    blocked_job_status,
    decide_with_market_session_policy,
)
from tradeo.modules.resource_policy.market_session_resource_policy import JobType  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=Path("artifacts/runtime/daily_swing/daily_ohlcv_research"))
    parser.add_argument("--universe", type=Path, default=Path("artifacts/runtime/daily_swing/dss_003e_research_universe_checked.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/runtime/daily_swing/gap"))
    parser.add_argument("--research-output-dir", type=Path, default=Path("research/daily_swing/gap"))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--min-history-days", type=int, default=20)
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--no-ibkr", action="store_true")
    parser.add_argument("--orders", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preview", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--signals", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--execute", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.orders or args.preview or args.signals or args.execute:
        print("DSS-GAP-002 refuses orders, previews, signals, and execute mode.", file=sys.stderr)
        return 2

    policy_decision = decide_with_market_session_policy(
        JobType.RESEARCH_HEAVY,
        "research",
        settings=get_settings(),
    )
    if not policy_decision.allowed:
        print(
            json.dumps(
                {
                    "decision": "blocked_resource_policy",
                    "resource_policy": policy_decision.to_dict(),
                    "research_result": blocked_job_status(policy_decision),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 5

    config = GapLedgerConfig(
        cache_dir=args.cache_dir,
        universe_path=args.universe,
        output_dir=args.output_dir,
        start_date=args.start_date,
        end_date=args.end_date,
        min_history_days=args.min_history_days,
        cache_only=args.cache_only,
        no_ibkr=args.no_ibkr,
        block_orders_preview_signals=not (args.orders or args.preview or args.signals or args.execute),
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )

    try:
        gate = validate_cache_and_universe(config)
        result = build_gap_event_ledger(config)
    except CacheMissingError as exc:
        payload = {
            "decision": exc.decision,
            "error": str(exc),
            "config": config_as_dict(config),
            "no_lookahead": audit_no_lookahead(),
            "security": _security_summary(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 3
    except GapLedgerError as exc:
        payload = {
            "decision": exc.decision,
            "error": str(exc),
            "config": config_as_dict(config),
            "security": _security_summary(),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 4
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    import pandas as pd

    ledger = pd.read_csv(result.ledger_path)
    research_paths = write_research_summaries(ledger, args.research_output_dir)
    payload = {
        "decision": result.decision,
        "gate": gate,
        "ledger_path": str(result.ledger_path),
        "summary_path": str(result.summary_path),
        "research_summary_paths": {key: str(value) for key, value in research_paths.items()},
        "rows": result.rows,
        "symbols_total": result.symbols_total,
        "symbols_operational": result.symbols_operational,
        "date_start": result.date_start,
        "date_end": result.date_end,
        "no_lookahead_status": result.no_lookahead_status,
        "security": _security_summary(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _security_summary() -> dict[str, bool]:
    return {
        "no_orders": True,
        "no_paper": True,
        "no_live": True,
        "no_preview": True,
        "no_signals": True,
        "no_backtest": True,
        "no_ibkr": True,
        "no_downloads": True,
        "no_cron": True,
        "no_gh": True,
    }


if __name__ == "__main__":
    raise SystemExit(main())
