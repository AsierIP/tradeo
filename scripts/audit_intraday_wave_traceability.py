#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tradeo.db.models import (  # noqa: E402
    DiscoveredPattern,
    DiscoveredPatternExample,
    DiscoveredPatternMetric,
    DiscoveryRun,
)
from tradeo.db.session import SessionLocal  # noqa: E402
from tradeo.research.intraday_research_forensics import run_ids_from_wave_manifest  # noqa: E402

SCHEMA_VERSION = "tradeo.wave_traceability_audit.v1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only traceability audit for intraday research waves.")
    parser.add_argument("--wave-manifest", required=True)
    parser.add_argument("--compare-run-ids", required=True)
    parser.add_argument("--forensics-json", required=True)
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    args = parser.parse_args()

    report = build_traceability_audit(
        wave_manifest=Path(args.wave_manifest),
        compare_run_ids=_parse_run_range(args.compare_run_ids),
        forensics_json=Path(args.forensics_json),
        evidence_json=Path(args.evidence_json),
    )
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report["status"] == "OK" else 2


def build_traceability_audit(
    *,
    wave_manifest: Path,
    compare_run_ids: list[int],
    forensics_json: Path,
    evidence_json: Path,
) -> dict[str, Any]:
    manifest_run_ids = run_ids_from_wave_manifest(wave_manifest)
    forensics = _load_json(forensics_json)
    evidence = _load_json(evidence_json)
    forensics_scope = _scope_run_ids(forensics)
    forensics_observed = _artifact_run_ids(forensics, keys=("candidate_forensics", "near_misses"))
    evidence_scope = _scope_run_ids(evidence)
    evidence_observed = _evidence_run_ids(evidence)
    manifest_set = set(manifest_run_ids)
    forensics_out = sorted(set(forensics_observed) - manifest_set)
    evidence_out = sorted(set(evidence_observed) - manifest_set)

    db = SessionLocal()
    try:
        runs = (
            db.query(DiscoveryRun)
            .filter(DiscoveryRun.id.in_(compare_run_ids))
            .order_by(DiscoveryRun.id.asc())
            .all()
        )
        patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.run_id.in_(compare_run_ids))
            .order_by(DiscoveredPattern.run_id.asc(), DiscoveredPattern.id.asc())
            .all()
        )
        pattern_ids = [int(pattern.id) for pattern in patterns]
        examples_by_pattern = _counts_by_pattern(db, DiscoveredPatternExample, pattern_ids)
        metrics_by_pattern = _counts_by_pattern(db, DiscoveredPatternMetric, pattern_ids)
    finally:
        db.close()

    patterns_by_run_id: dict[str, int] = Counter(str(int(pattern.run_id)) for pattern in patterns)
    examples_by_run_id: defaultdict[str, int] = defaultdict(int)
    metrics_by_run_id: defaultdict[str, int] = defaultdict(int)
    for pattern in patterns:
        key = str(int(pattern.run_id))
        examples_by_run_id[key] += examples_by_pattern.get(int(pattern.id), 0)
        metrics_by_run_id[key] += metrics_by_pattern.get(int(pattern.id), 0)

    violation = bool(forensics_out or evidence_out)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "VIOLATION" if violation else "OK",
        "manifest_run_ids": manifest_run_ids,
        "compare_run_ids": compare_run_ids,
        "db_runs": [_run_row(run) for run in runs],
        "patterns_by_run_id": dict(sorted(patterns_by_run_id.items())),
        "examples_by_run_id": dict(sorted(examples_by_run_id.items())),
        "metrics_by_run_id": dict(sorted(metrics_by_run_id.items())),
        "forensics_scope_run_ids": forensics_scope,
        "forensics_candidate_run_ids": forensics_observed,
        "forensics_out_of_scope_run_ids": forensics_out,
        "evidence_scope_run_ids": evidence_scope,
        "evidence_candidate_run_ids": evidence_observed,
        "evidence_out_of_scope_run_ids": evidence_out,
        "duplicate_wave_batches": _duplicate_wave_batches(runs),
        "artifact_hashes": {
            str(wave_manifest): _sha256(wave_manifest),
            str(forensics_json): _sha256(forensics_json),
            str(evidence_json): _sha256(evidence_json),
        },
        "decision": "invalid_scope_mixed" if violation else "valid_exact_scope",
    }
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Intraday Wave Traceability Audit",
        "",
        f"Status: `{report['status']}`",
        f"Decision: `{report['decision']}`",
        "",
        "## Scope",
        f"- manifest_run_ids: `{report['manifest_run_ids']}`",
        f"- compare_run_ids: `{report['compare_run_ids']}`",
        f"- forensics_out_of_scope_run_ids: `{report['forensics_out_of_scope_run_ids']}`",
        f"- evidence_out_of_scope_run_ids: `{report['evidence_out_of_scope_run_ids']}`",
        "",
        "## DB Runs",
    ]
    for row in report["db_runs"]:
        lines.append(
            f"- {row['id']}: status=`{row['status']}` windows=`{row['windows_sampled']}` "
            f"clusters=`{row['clusters_evaluated']}` accepted=`{row['accepted_patterns']}` "
            f"rejected=`{row['rejected_patterns']}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def _parse_run_range(raw: str) -> list[int]:
    out: list[int] = []
    for chunk in str(raw).split(","):
        item = chunk.strip()
        if not item:
            continue
        if "-" in item:
            start, end = item.split("-", 1)
            out.extend(range(int(start), int(end) + 1))
        else:
            out.append(int(item))
    return _dedupe_ints(out)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _scope_run_ids(payload: dict[str, Any]) -> list[int]:
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    return _dedupe_ints(_iter_ints(scope.get("run_ids") or scope.get("requested_run_ids") or []))


def _artifact_run_ids(payload: dict[str, Any], *, keys: Iterable[str]) -> list[int]:
    values: list[int] = []
    for key in keys:
        for row in payload.get(key) or []:
            if isinstance(row, dict):
                run_id = _optional_int(row.get("run_id"))
                if run_id is not None:
                    values.append(run_id)
    return _dedupe_ints(values)


def _evidence_run_ids(payload: dict[str, Any]) -> list[int]:
    values = _artifact_run_ids(payload, keys=("candidate_manifests",))
    samples = payload.get("samples_by_candidate") or {}
    if isinstance(samples, dict):
        for rows in samples.values():
            for row in rows or []:
                if isinstance(row, dict):
                    run_id = _optional_int(row.get("run_id"))
                    if run_id is not None:
                        values.append(run_id)
    return _dedupe_ints(values)


def _counts_by_pattern(db: Any, model: Any, pattern_ids: list[int]) -> dict[int, int]:
    if not pattern_ids:
        return {}
    return dict(Counter(int(row[0]) for row in db.query(model.pattern_id).filter(model.pattern_id.in_(pattern_ids)).all()))


def _run_row(run: DiscoveryRun) -> dict[str, Any]:
    return {
        "id": int(run.id),
        "status": str(run.status),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "params_json": run.params_json if isinstance(run.params_json, dict) else {},
        "windows_sampled": int(run.windows_sampled or 0),
        "clusters_evaluated": int(run.clusters_evaluated or 0),
        "accepted_patterns": int(run.accepted_patterns or 0),
        "rejected_patterns": int(run.rejected_patterns or 0),
    }


def _duplicate_wave_batches(runs: list[DiscoveryRun]) -> list[dict[str, Any]]:
    grouped: defaultdict[str, list[int]] = defaultdict(list)
    for run in runs:
        params = run.params_json if isinstance(run.params_json, dict) else {}
        key = json.dumps(
            {
                "interval": params.get("interval"),
                "period": params.get("period"),
                "window_sizes": params.get("window_sizes"),
                "forward_bars": params.get("forward_bars"),
                "vwap_condition": params.get("vwap_condition"),
                "vwap_side_bias": params.get("vwap_side_bias"),
            },
            sort_keys=True,
            default=str,
        )
        grouped[key].append(int(run.id))
    return [{"signature": key, "run_ids": ids} for key, ids in grouped.items() if len(ids) > 1]


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _iter_ints(values: Iterable[Any]) -> list[int]:
    out: list[int] = []
    for value in values:
        parsed = _optional_int(value)
        if parsed is not None:
            out.append(parsed)
    return out


def _dedupe_ints(values: Iterable[int]) -> list[int]:
    out: list[int] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
