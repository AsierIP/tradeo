#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.modules.lab_foxhunter.probe_state import ProbeStatePaths, final_daily_state, load_or_create, update_probe_metrics, write_state  # noqa: E402

PROBES = ("LAB-GAP-REV-001", "LAB-GAP-REV-002")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the post-close Lab nightly Director report.")
    parser.add_argument("--date", default="")
    parser.add_argument("--runtime-root", default="artifacts/runtime/lab_paper_probe")
    parser.add_argument("--reports-dir", default="research/lab_foxhunter/nightly")
    parser.add_argument("--phase", default="nightly-report")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    trading_day = _trading_day(args.date)
    runtime_root = ROOT / args.runtime_root
    paths = ProbeStatePaths(runtime_root=runtime_root, trading_day=trading_day)
    state = load_or_create(paths)
    summary = _summarize_runtime(paths.day_dir)
    for probe_id in PROBES:
        state = update_probe_metrics(state, probe_id, _probe_metrics(summary, probe_id))
    state = final_daily_state(state)
    write_state(paths, state)

    reports_dir = ROOT / args.reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    decision = _decision_payload(trading_day=trading_day, state=state, summary=summary, dry_run=args.dry_run)
    report = _render_report(decision)
    md_path = reports_dir / f"LAB_NIGHTLY_REPORT_{trading_day.isoformat()}.md"
    json_path = reports_dir / f"LAB_NIGHTLY_DECISION_{trading_day.isoformat()}.json"
    md_path.write_text(report, encoding="utf-8")
    json_path.write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(md_path), "decision": str(json_path), "state": state["state"]}, indent=2, sort_keys=True))
    return 0


def _trading_day(value: str):
    if value:
        return datetime.fromisoformat(value).date()
    return datetime.now(ZoneInfo("America/New_York")).date()


def _summarize_runtime(day_dir: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "runtime_dir": str(day_dir),
        "runtime_files": [],
        "orders_attempted": 0,
        "orders_submitted": 0,
        "orders_filled": 0,
        "orders_cancelled": 0,
        "orders_rejected": 0,
        "live_orders": 0,
        "operational_errors": 0,
        "reconciliation_errors": 0,
        "no_trade_reasons": [],
        "probes": {probe: {"trades_today": 0, "successes": 0} for probe in PROBES},
    }
    if not day_dir.exists():
        return summary
    for path in sorted(day_dir.glob("*.json")):
        if path.name == "probe_state.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            summary["operational_errors"] += 1
            continue
        summary["runtime_files"].append(str(path))
        _accumulate(summary, data)
    return summary


def _accumulate(summary: dict[str, Any], data: Any) -> None:
    summary["orders_attempted"] += _count(data, ("orders_attempted", "orders"))
    summary["orders_submitted"] += _count(data, ("orders_submitted", "paper_orders", "paper_orders_executed"))
    summary["orders_filled"] += _count(data, ("orders_filled", "fills"))
    summary["orders_cancelled"] += _count(data, ("orders_cancelled", "cancels"))
    summary["orders_rejected"] += _count(data, ("orders_rejected", "rejects"))
    summary["live_orders"] += _count(data, ("live_orders", "live_orders_executed"))
    summary["operational_errors"] += _count(data, ("operational_errors",))
    summary["reconciliation_errors"] += _count(data, ("reconciliation_errors",))
    reason = _find_reason(data)
    if reason:
        summary["no_trade_reasons"].append(reason)
    for probe in PROBES:
        if probe in json.dumps(data):
            summary["probes"][probe]["trades_today"] += _count(data, ("fills", "orders_filled", "paper_orders_executed"))


def _count(data: Any, names: tuple[str, ...]) -> int:
    if isinstance(data, dict):
        total = 0
        for key, value in data.items():
            low = key.lower()
            if any(name == low for name in names):
                if isinstance(value, list):
                    total += len(value)
                elif isinstance(value, (int, float)):
                    total += int(value)
                elif value:
                    total += 1
            total += _count(value, names)
        return total
    if isinstance(data, list):
        return sum(_count(item, names) for item in data)
    return 0


def _find_reason(data: Any) -> str | None:
    if isinstance(data, dict):
        for key in ("no_trade_reason", "decision"):
            value = data.get(key)
            if isinstance(value, str) and ("NO_TRADE" in value or "BLOCKED" in value or "PENDING" in value):
                return value
        for value in data.values():
            found = _find_reason(value)
            if found:
                return found
    if isinstance(data, list):
        for value in data:
            found = _find_reason(value)
            if found:
                return found
    return None


def _probe_metrics(summary: dict[str, Any], probe_id: str) -> dict[str, Any]:
    probe = summary["probes"][probe_id]
    trades = int(probe["trades_today"])
    successes = int(probe["successes"])
    return {
        "trades_today": trades,
        "total_trades_toward_20": trades,
        "successes": successes,
        "operational_errors": int(summary["operational_errors"]),
        "reconciliation_errors": int(summary["reconciliation_errors"]),
    }


def _decision_payload(*, trading_day, state: dict[str, Any], summary: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    automation_decision = "LAB_AUTOMATION_READY" if state["state"] in {"POST_CLOSE_ANALYZED", "NEEDS_DIRECTOR_REVIEW"} else "LAB_AUTOMATION_NEEDS_REVISION"
    return {
        "schema": "tradeo.lab_automation_001.nightly_decision.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trading_day": trading_day.isoformat(),
        "task_id": "T-LAB-AUTOMATION-001",
        "mode": "LAB_AUTOMATION_ONLY",
        "dry_run": dry_run,
        "decision": automation_decision,
        "daily_state": state["state"],
        "orders_attempted": summary["orders_attempted"],
        "orders_submitted": summary["orders_submitted"],
        "orders_filled": summary["orders_filled"],
        "orders_cancelled": summary["orders_cancelled"],
        "orders_rejected": summary["orders_rejected"],
        "live_orders": summary["live_orders"],
        "no_trade_reasons": sorted(set(summary["no_trade_reasons"])),
        "probes": state["probes"],
        "foxhunter_promotion": False,
        "live_candidate_created": False,
        "paper_candidate_classic_created": False,
        "redacted": True,
    }


def _render_report(payload: dict[str, Any]) -> str:
    lines = [
        f"# LAB_NIGHTLY_REPORT_{payload['trading_day']}",
        "",
        "## A. Resumen ejecutivo",
        f"Decision: `{payload['decision']}`. Informe nocturno generado sin promocion automatica y sin live.",
        "",
        "## B. Ordenes paper",
        f"- attempted: {payload['orders_attempted']}",
        f"- submitted: {payload['orders_submitted']}",
        f"- filled: {payload['orders_filled']}",
        f"- cancelled: {payload['orders_cancelled']}",
        f"- rejected: {payload['orders_rejected']}",
        f"- live_orders: {payload['live_orders']}",
        "",
        "## C. No-trade / errores",
        f"- no_trade_reasons: `{payload['no_trade_reasons']}`",
        "",
        "## D. Progreso por probe",
    ]
    for probe, metrics in payload["probes"].items():
        lines.append(f"- {probe}: trades_today={metrics['trades_today']}, total_to_20={metrics['total_trades_toward_20']}, successes={metrics['successes']}, eligible_review={metrics['eligible_for_lab_to_foxhunter_review']}, blocked={metrics['blocked_until_director_review']}")
    lines.extend(
        [
            "",
            "## E. Decision",
            f"- daily_state: `{payload['daily_state']}`",
            "- FoxHunter automatico: `false`",
            "- live_candidate: `false`",
            "- paper_candidate clasico: `false`",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
