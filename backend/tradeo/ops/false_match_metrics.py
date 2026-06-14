from __future__ import annotations

import argparse
import json
from typing import Any

from sqlalchemy.orm import Session

from tradeo.db.models import AuditLog, DiscoveredPattern
from tradeo.db.session import SessionLocal
from tradeo.services.ops_alerts import add_internal_alert

DRIFT_STATUSES = {"decaying", "degrading", "regressing", "deteriorating"}


def collect_false_match_drift_metrics(
    db: Session,
    *,
    high_fpr_threshold: float = 0.25,
) -> dict[str, Any]:
    """Summarize persisted false-match and drift metrics without fetching data."""
    patterns = db.query(DiscoveredPattern).all()
    rows: list[dict[str, Any]] = []
    missing_harness = 0
    high_fpr = 0
    drifted = 0
    for pattern in patterns:
        metrics = pattern.metrics_json or {}
        fpr = _false_match_fpr(metrics)
        temporal_fpr = _nested_float(metrics, "false_match_harness_temporal", "fpr_at_recall")
        drift_status = str(pattern.drift_status or metrics.get("drift_status") or "stable")
        row = {
            "pattern_id": pattern.id,
            "pattern_key": pattern.pattern_key,
            "status": str(pattern.status.value if hasattr(pattern.status, "value") else pattern.status),
            "drift_status": drift_status,
            "drift_score": float(pattern.drift_score or metrics.get("drift_score") or 0.0),
            "fpr_at_recall90": fpr,
            "temporal_fpr_at_recall90": temporal_fpr,
            "match_tau_similarity": _as_float(metrics.get("match_tau_similarity")),
        }
        rows.append(row)
        if fpr is None:
            missing_harness += 1
        elif fpr >= high_fpr_threshold:
            high_fpr += 1
        if drift_status.strip().lower() in DRIFT_STATUSES:
            drifted += 1

    rows.sort(
        key=lambda row: (
            row["fpr_at_recall90"] is None,
            -(row["fpr_at_recall90"] or -1.0),
            -row["drift_score"],
            row["pattern_key"],
        )
    )
    return {
        "schema_version": 1,
        "pattern_count": len(patterns),
        "patterns_with_false_match_harness": len(patterns) - missing_harness,
        "patterns_missing_false_match_harness": missing_harness,
        "high_fpr_threshold": high_fpr_threshold,
        "patterns_high_fpr": high_fpr,
        "patterns_drifted": drifted,
        "worst_patterns": rows[:25],
    }


def persist_false_match_drift_report(db: Session, report: dict[str, Any]) -> None:
    db.add(
        AuditLog(
            actor="false_match_metrics",
            action="false_match_drift_metrics_report",
            entity_type="ops_report",
            entity_id="false_match_drift",
            details_json=report,
        )
    )
    if report["patterns_high_fpr"] or report["patterns_drifted"]:
        add_internal_alert(
            db,
            source="false_match_metrics",
            severity="warning",
            message="false-match/drift metrics exceeded review thresholds",
            details={
                "patterns_high_fpr": report["patterns_high_fpr"],
                "patterns_drifted": report["patterns_drifted"],
                "high_fpr_threshold": report["high_fpr_threshold"],
            },
            entity_type="ops_report",
            entity_id="false_match_drift",
        )
    db.commit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize persisted Tradeo false-match/drift metrics.")
    parser.add_argument("--high-fpr-threshold", type=float, default=0.25)
    parser.add_argument("--audit-log", action="store_true", help="Persist the report to audit_logs.")
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        report = collect_false_match_drift_metrics(
            db,
            high_fpr_threshold=float(args.high_fpr_threshold),
        )
        if args.audit_log:
            persist_false_match_drift_report(db, report)
        print(json.dumps(report, sort_keys=True, indent=2))
    finally:
        db.close()
    return 0


def _false_match_fpr(metrics: dict[str, Any]) -> float | None:
    top_level = _as_float(metrics.get("fpr_at_recall90"))
    if top_level is not None:
        return top_level
    return _nested_float(metrics, "false_match_harness", "fpr_at_recall")


def _nested_float(metrics: dict[str, Any], *path: str) -> float | None:
    value: Any = metrics
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return _as_float(value)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
