#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import text  # noqa: E402

from tradeo.db.session import SessionLocal  # noqa: E402
from tradeo.research.intraday_research_forensics import (  # noqa: E402
    observed_run_ids_from_payload,
    run_ids_from_wave_manifest,
)

SCHEMA_VERSION = "tradeo.wave_traceability_audit.v1"


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only intraday wave traceability audit.")
    parser.add_argument("--wave-manifest", required=True)
    parser.add_argument("--compare-run-ids", action="append", default=[])
    parser.add_argument("--forensics-json", required=True)
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.wave_manifest)
    forensics_path = Path(args.forensics_json)
    evidence_path = Path(args.evidence_json)
    manifest_run_ids = run_ids_from_wave_manifest(manifest_path)
    compare_run_ids = _parse_run_id_args(args.compare_run_ids)
    forensics = _read_json(forensics_path)
    evidence = _read_json(evidence_path)

    db = SessionLocal()
    try:
        db_runs = _db_runs(db, compare_run_ids)
        patterns_by_run_id = _counts_by_run_id(db, "discovered_patterns", compare_run_ids)
        examples_by_run_id = _joined_counts_by_run_id(db, "discovered_pattern_examples", compare_run_ids)
        metrics_by_run_id = _joined_counts_by_run_id(db, "discovered_pattern_metrics", compare_run_ids)
    finally:
        db.close()

    report = build_traceability_report(
        manifest_run_ids=manifest_run_ids,
        compare_run_ids=compare_run_ids,
        db_runs=db_runs,
        patterns_by_run_id=patterns_by_run_id,
        examples_by_run_id=examples_by_run_id,
        metrics_by_run_id=metrics_by_run_id,
        forensics=forensics,
        evidence=evidence,
        artifact_hashes={
            "wave_manifest": _sha256_file(manifest_path),
            "forensics_json": _sha256_file(forensics_path),
            "evidence_json": _sha256_file(evidence_path),
        },
    )

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str), encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Intraday Wave Traceability Audit",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: `{report['status']}`",
        f"Decision: `{report['decision']}`",
        "",
        "## Scope",
        f"- manifest_run_ids: `{', '.join(str(item) for item in report['manifest_run_ids'])}`",
        f"- compare_run_ids: `{', '.join(str(item) for item in report['compare_run_ids'])}`",
        f"- forensics_out_of_scope_run_ids: `{report['forensics_out_of_scope_run_ids']}`",
        f"- evidence_out_of_scope_run_ids: `{report['evidence_out_of_scope_run_ids']}`",
        "",
        "## Duplicate Batches",
    ]
    for batch in report["duplicate_wave_batches"]:
        lines.append(
            f"- run_ids=`{batch['run_ids']}` windows=`{batch['windows']}` "
            f"clusters=`{batch['clusters']}` patterns=`{batch['patterns']}`"
        )
    lines.extend(["", "## Artifact Hashes"])
    for key, value in report["artifact_hashes"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def build_traceability_report(
    *,
    manifest_run_ids: list[int],
    compare_run_ids: list[int],
    db_runs: list[dict[str, Any]],
    patterns_by_run_id: dict[str, int],
    examples_by_run_id: dict[str, int],
    metrics_by_run_id: dict[str, int],
    forensics: dict[str, Any],
    evidence: dict[str, Any],
    artifact_hashes: dict[str, str],
) -> dict[str, Any]:
    forensics_scope_run_ids = _scope_run_ids(forensics)
    forensics_candidate_run_ids = observed_run_ids_from_payload(
        {
            "candidate_forensics": forensics.get("candidate_forensics"),
            "near_misses": forensics.get("near_misses"),
        }
    )
    evidence_scope_run_ids = _scope_run_ids(evidence)
    evidence_candidate_run_ids = observed_run_ids_from_payload(
        {
            "candidate_manifests": evidence.get("candidate_manifests"),
            "samples_by_candidate": evidence.get("samples_by_candidate"),
            "summary": evidence.get("summary"),
        }
    )
    forensics_out = _out_of_scope(forensics_candidate_run_ids, manifest_run_ids)
    evidence_out = _out_of_scope(evidence_candidate_run_ids, manifest_run_ids)
    status = "VIOLATION" if forensics_out or evidence_out else "OK"
    decision = "invalid_scope_mixed" if status == "VIOLATION" else "valid_exact_scope"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "manifest_run_ids": manifest_run_ids,
        "compare_run_ids": compare_run_ids,
        "db_runs": db_runs,
        "patterns_by_run_id": patterns_by_run_id,
        "examples_by_run_id": examples_by_run_id,
        "metrics_by_run_id": metrics_by_run_id,
        "forensics_scope_run_ids": forensics_scope_run_ids,
        "forensics_candidate_run_ids": forensics_candidate_run_ids,
        "forensics_out_of_scope_run_ids": forensics_out,
        "evidence_scope_run_ids": evidence_scope_run_ids,
        "evidence_candidate_run_ids": evidence_candidate_run_ids,
        "evidence_out_of_scope_run_ids": evidence_out,
        "duplicate_wave_batches": _duplicate_batches(db_runs, patterns_by_run_id),
        "artifact_hashes": artifact_hashes,
        "decision": decision,
    }


def _parse_run_id_args(raw_values: Iterable[str]) -> list[int]:
    values: list[int] = []
    for raw in raw_values:
        for item in str(raw).replace(";", ",").split(","):
            text_value = item.strip()
            if not text_value:
                continue
            if "-" in text_value:
                start_raw, end_raw = text_value.split("-", 1)
                start = int(start_raw)
                end = int(end_raw)
                values.extend(range(min(start, end), max(start, end) + 1))
            else:
                values.append(int(text_value))
    return _dedupe(values)


def _db_runs(db: Any, run_ids: list[int]) -> list[dict[str, Any]]:
    if not run_ids:
        return []
    rows = db.execute(
        text(
            """
            select id, status, coalesce(symbols_scanned,0), coalesce(windows_sampled,0),
                   coalesce(clusters_evaluated,0), coalesce(accepted_patterns,0),
                   coalesce(rejected_patterns,0), started_at, finished_at
            from discovery_runs
            where id = any(:run_ids)
            order by id
            """
        ),
        {"run_ids": run_ids},
    ).fetchall()
    return [
        {
            "run_id": int(row[0]),
            "status": str(row[1]),
            "symbols_scanned": int(row[2] or 0),
            "windows_sampled": int(row[3] or 0),
            "clusters_evaluated": int(row[4] or 0),
            "accepted_patterns": int(row[5] or 0),
            "rejected_patterns": int(row[6] or 0),
            "started_at": str(row[7]) if row[7] is not None else None,
            "finished_at": str(row[8]) if row[8] is not None else None,
        }
        for row in rows
    ]


def _counts_by_run_id(db: Any, table: str, run_ids: list[int]) -> dict[str, int]:
    if not run_ids:
        return {}
    rows = db.execute(
        text(f"select run_id, count(*) from {table} where run_id = any(:run_ids) group by run_id order by run_id"),
        {"run_ids": run_ids},
    ).fetchall()
    return {str(int(row[0])): int(row[1]) for row in rows}


def _joined_counts_by_run_id(db: Any, table: str, run_ids: list[int]) -> dict[str, int]:
    if not run_ids:
        return {}
    rows = db.execute(
        text(
            f"""
            select p.run_id, count(*)
            from {table} child
            join discovered_patterns p on p.id = child.pattern_id
            where p.run_id = any(:run_ids)
            group by p.run_id
            order by p.run_id
            """
        ),
        {"run_ids": run_ids},
    ).fetchall()
    return {str(int(row[0])): int(row[1]) for row in rows}


def _duplicate_batches(db_runs: list[dict[str, Any]], patterns_by_run_id: dict[str, int]) -> list[dict[str, Any]]:
    batches: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    for run in db_runs:
        key = (
            int(run.get("windows_sampled") or 0),
            int(run.get("clusters_evaluated") or 0),
            int(run.get("rejected_patterns") or 0),
        )
        batches[key].append(run)
    output = []
    for (_windows, _clusters, _rejected), rows in batches.items():
        if len(rows) < 2:
            continue
        output.append(
            {
                "run_ids": [int(row["run_id"]) for row in rows],
                "windows": sum(int(row.get("windows_sampled") or 0) for row in rows),
                "clusters": sum(int(row.get("clusters_evaluated") or 0) for row in rows),
                "rejected": sum(int(row.get("rejected_patterns") or 0) for row in rows),
                "patterns": sum(int(patterns_by_run_id.get(str(row["run_id"]), 0)) for row in rows),
            }
        )
    return output


def _scope_run_ids(payload: dict[str, Any]) -> list[int]:
    integrity = payload.get("scope_integrity") or {}
    if integrity.get("scope_run_ids"):
        return _dedupe(int(item) for item in integrity["scope_run_ids"])
    scope = payload.get("scope") or {}
    return _dedupe(int(item) for item in scope.get("run_ids") or [])


def _out_of_scope(observed_run_ids: Iterable[int], manifest_run_ids: Iterable[int]) -> list[int]:
    scope = {int(item) for item in manifest_run_ids}
    return [run_id for run_id in _dedupe(int(item) for item in observed_run_ids) if run_id not in scope]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _dedupe(values: Iterable[int]) -> list[int]:
    output: list[int] = []
    for value in values:
        parsed = int(value)
        if parsed not in output:
            output.append(parsed)
    return output


if __name__ == "__main__":
    raise SystemExit(main())
