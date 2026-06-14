"""Rediscovery readiness audit for already-persisted discovered patterns.

Wave4 added three metadata contracts that discovery now writes into
``DiscoveredPattern.metrics_json`` but that legacy rows predate:

- embedding contract (``feature_parity_contract`` with a ``contract_id``),
- cluster signature with concentration metadata (``cluster_signature`` /
  ``concentration_checks``),
- benchmark-regime calibration buckets
  (``regime_profile.benchmark_regime_outcomes``).

This module audits persisted patterns against those contracts, can flag
laggards with a ``rediscovery_readiness`` block inside ``metrics_json`` and
emits a manifest with honest before/after counts. Flagging never populates
metadata: only a real discovery run does. This module never launches
discovery, market scans or any live/paper order path.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from tradeo.db.models import DiscoveredPattern
from tradeo.research.determinism import CONTENT_HASH_ALGO, content_hash
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine

CHECKER_VERSION = "wave4c_rediscovery_readiness_v1"
READINESS_KEY = "rediscovery_readiness"

EMBEDDING_CONTRACT = "embedding_contract"
CLUSTER_SIGNATURE = "cluster_signature"
REGIME_CALIBRATION = "regime_calibration_buckets"
REQUIRED_FIELDS = (EMBEDDING_CONTRACT, CLUSTER_SIGNATURE, REGIME_CALIBRATION)

# Hard cap so the audit never turns into an unbounded scan; the manifest
# reports truncation explicitly when the cap is hit.
DEFAULT_AUDIT_LIMIT = 2000


@dataclass
class PatternReadiness:
    pattern_id: int
    pattern_key: str
    status: str
    promotion_status: str
    missing: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)

    @property
    def needs_rediscovery(self) -> bool:
        return bool(self.missing or self.stale)

    def as_payload(self) -> dict[str, Any]:
        return {
            "pattern_key": self.pattern_key,
            "status": self.status,
            "promotion_status": self.promotion_status,
            "missing": list(self.missing),
            "stale": list(self.stale),
            "needs_rediscovery": self.needs_rediscovery,
        }


def evaluate_pattern_metrics(metrics: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    """Return (missing, stale) Wave4 metadata fields for one metrics blob."""
    metrics = metrics if isinstance(metrics, dict) else {}
    missing: list[str] = []
    stale: list[str] = []

    contract = metrics.get("feature_parity_contract")
    if not isinstance(contract, dict) or not contract.get("contract_id"):
        missing.append(EMBEDDING_CONTRACT)
    elif str(contract.get("contract_id")) != PatternEmbeddingEngine.CONTRACT_ID:
        stale.append(EMBEDDING_CONTRACT)

    signature = metrics.get("cluster_signature")
    checks = signature.get("concentration_checks") if isinstance(signature, dict) else None
    if (
        not isinstance(checks, dict)
        or "passed" not in checks
        or not isinstance(signature.get("medoid") if isinstance(signature, dict) else None, dict)
    ):
        missing.append(CLUSTER_SIGNATURE)

    profile = metrics.get("regime_profile")
    outcomes = profile.get("benchmark_regime_outcomes") if isinstance(profile, dict) else None
    if not isinstance(outcomes, dict) or "available" not in outcomes:
        missing.append(REGIME_CALIBRATION)

    return missing, stale


def audit_patterns(
    db: Session, *, limit: int = DEFAULT_AUDIT_LIMIT
) -> tuple[list[PatternReadiness], bool]:
    """Audit persisted patterns deterministically; returns (results, truncated)."""
    limit = max(1, int(limit))
    stmt = select(DiscoveredPattern).order_by(DiscoveredPattern.pattern_key.asc()).limit(limit + 1)
    rows = list(db.execute(stmt).scalars())
    truncated = len(rows) > limit
    results: list[PatternReadiness] = []
    for row in rows[:limit]:
        missing, stale = evaluate_pattern_metrics(row.metrics_json)
        results.append(
            PatternReadiness(
                pattern_id=int(row.id),
                pattern_key=str(row.pattern_key),
                status=str(getattr(row.status, "value", row.status)),
                promotion_status=str(row.promotion_status or ""),
                missing=missing,
                stale=stale,
            )
        )
    return results, truncated


def apply_rediscovery_flags(
    db: Session,
    results: list[PatternReadiness],
    *,
    flagged_at: str | None = None,
) -> int:
    """Write a ``rediscovery_readiness`` block into metrics_json of laggards.

    Marks intent only — it does not create, recompute or fake any metadata.
    Patterns already satisfying every contract get any stale flag cleared.
    """
    flagged = 0
    by_id = {result.pattern_id: result for result in results}
    if not by_id:
        return 0
    rows = db.execute(
        select(DiscoveredPattern).where(DiscoveredPattern.id.in_(by_id.keys()))
    ).scalars()
    now = flagged_at or datetime.now(timezone.utc).isoformat()
    for row in rows:
        result = by_id[int(row.id)]
        metrics = dict(row.metrics_json or {})
        if result.needs_rediscovery:
            existing = (
                metrics.get(READINESS_KEY) if isinstance(metrics.get(READINESS_KEY), dict) else {}
            )
            flagged_block = {
                "needs_rediscovery": True,
                "missing": list(result.missing),
                "stale": list(result.stale),
                "checker_version": CHECKER_VERSION,
                "flagged_at": existing.get("flagged_at") or now,
            }
            if existing == flagged_block:
                continue
            metrics[READINESS_KEY] = flagged_block
            if not existing.get("needs_rediscovery"):
                flagged += 1
        elif READINESS_KEY in metrics:
            existing = metrics.get(READINESS_KEY)
            existing_flagged_at = existing.get("flagged_at") if isinstance(existing, dict) else None
            cleared_block = {
                "needs_rediscovery": False,
                "missing": [],
                "stale": [],
                "checker_version": CHECKER_VERSION,
                "flagged_at": existing_flagged_at or now,
            }
            if (
                isinstance(existing, dict)
                and all(existing.get(key) == value for key, value in cleared_block.items())
                and existing.get("cleared_at")
            ):
                continue
            metrics[READINESS_KEY] = {
                **cleared_block,
                "cleared_at": (
                    existing.get("cleared_at")
                    if isinstance(existing, dict) and existing.get("cleared_at")
                    else now
                ),
            }
        else:
            continue
        row.metrics_json = metrics
        flag_modified(row, "metrics_json")
    db.commit()
    return flagged


def build_manifest(
    results: list[PatternReadiness],
    *,
    dry_run: bool,
    flagged_count: int,
    truncated: bool,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build an honest rediscovery manifest with before/after counts.

    ``metadata_complete_after`` always equals ``metadata_complete_before``:
    this tool only audits and flags, it never populates metadata. Counts only
    change after a real rediscovery run is executed and re-audited.
    """
    needs = [result for result in results if result.needs_rediscovery]
    missing_counts = {
        fieldname: sum(1 for result in results if fieldname in result.missing)
        for fieldname in REQUIRED_FIELDS
    }
    stale_counts = {
        fieldname: sum(1 for result in results if fieldname in result.stale)
        for fieldname in REQUIRED_FIELDS
    }
    complete_before = len(results) - len(needs)
    manifest: dict[str, Any] = {
        "checker_version": CHECKER_VERSION,
        "dry_run": dry_run,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "truncated": truncated,
        "counts": {
            "patterns_audited": len(results),
            "metadata_complete_before": complete_before,
            "metadata_complete_after": complete_before,
            "needs_rediscovery": len(needs),
            "flagged_this_run": flagged_count,
            "missing_by_field": missing_counts,
            "stale_by_field": stale_counts,
        },
        "honesty_note": (
            "flagging marks intent only; metadata_complete_after == before because "
            "no rediscovery was executed by this tool"
        ),
        "rediscovery_plan": {
            "command": "POST /api/research/run-discovery (see docs/research/wave4_rediscovery_runbook.md)",
            "verify": "re-run this audit after discovery; needs_rediscovery must drop to 0",
        },
        "patterns_needing_rediscovery": [result.as_payload() for result in needs],
    }
    manifest["determinism"] = {
        "algo": CONTENT_HASH_ALGO,
        "content_hash": content_hash(manifest),
    }
    return manifest


def run_readiness(
    db: Session,
    *,
    apply_flags: bool = False,
    limit: int = DEFAULT_AUDIT_LIMIT,
    manifest_path: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Audit patterns, optionally flag laggards, and return the manifest."""
    results, truncated = audit_patterns(db, limit=limit)
    flagged = apply_rediscovery_flags(db, results, flagged_at=generated_at) if apply_flags else 0
    manifest = build_manifest(
        results,
        dry_run=not apply_flags,
        flagged_count=flagged,
        truncated=truncated,
        generated_at=generated_at,
    )
    if manifest_path is not None:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wave4-C rediscovery readiness audit (no discovery is run)"
    )
    parser.add_argument(
        "--apply-flags",
        action="store_true",
        help="write rediscovery_readiness flags into metrics_json (default: dry-run)",
    )
    parser.add_argument(
        "--limit", type=int, default=DEFAULT_AUDIT_LIMIT, help="max patterns to audit"
    )
    parser.add_argument(
        "--manifest-out", type=Path, default=None, help="path for the JSON manifest"
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="optional ISO-8601 timestamp for bit-for-bit reproducible manifests",
    )
    args = parser.parse_args(argv)

    from tradeo.db.session import SessionLocal

    db = SessionLocal()
    try:
        manifest = run_readiness(
            db,
            apply_flags=args.apply_flags,
            limit=args.limit,
            manifest_path=args.manifest_out,
            generated_at=args.generated_at,
        )
    finally:
        db.close()
    print(json.dumps(manifest["counts"], indent=2, sort_keys=True))
    if manifest["truncated"]:
        print(f"WARNING: audit truncated at --limit={args.limit}; rerun with a higher limit")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
