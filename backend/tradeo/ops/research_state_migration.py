from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradeo.db.models import (
    ResearchArtifactRetention,
    ResearchDirectorArtifact,
    ResearchExperimentRegistryExperiment,
    ResearchExperimentRegistryRun,
    ResearchExperimentRegistrySnapshot,
)
from tradeo.db.session import SessionLocal
from tradeo.research.global_experiment_registry import GlobalExperimentRegistry

_RUN_ID_RE = re.compile(r"(?:discovery_run_|run_)(\d+)")


def main() -> None:
    args = _parse_args()
    root = Path(args.reports_root)
    result = migrate_research_state(
        reports_root=root,
        apply=bool(args.apply),
        delete_after_import=bool(args.delete_after_import),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def migrate_research_state(
    *,
    reports_root: Path,
    apply: bool,
    delete_after_import: bool,
) -> dict[str, Any]:
    registry_path = reports_root / "global_experiment_registry.json"
    backup_paths = sorted((reports_root / ".backups").glob("global_experiment_registry.json.*.bak"))
    retention_paths = sorted(reports_root.glob("retention_registry_*.jsonl"))
    director_paths = sorted(
        path
        for pattern in ("*.json", "*.md")
        for path in (reports_root / "director").glob(pattern)
    )
    source_paths = [p for p in [registry_path, *backup_paths, *retention_paths, *director_paths] if p.exists()]
    source_manifest = [_file_manifest(path, reports_root=reports_root) for path in source_paths]
    db = SessionLocal()
    try:
        counts = {
            "registry_snapshots": 0,
            "registry_experiments": 0,
            "registry_runs": 0,
            "retention_rows": 0,
            "director_artifacts": 0,
        }
        if apply:
            if registry_path.exists():
                payload = _read_json(registry_path)
                _persist_registry_payload(db, payload, persist_current_state=True)
                counts["registry_snapshots"] += 1
                counts["registry_experiments"] = len(payload.get("experiments") or [])
                counts["registry_runs"] = len(payload.get("runs") or [])
            for backup_path in backup_paths:
                payload = _read_json(backup_path)
                _persist_registry_payload(db, payload, persist_current_state=False)
                counts["registry_snapshots"] += 1
            for retention_path in retention_paths:
                counts["retention_rows"] += _persist_retention_jsonl(db, retention_path)
            for director_path in director_paths:
                _persist_director_artifact(db, director_path)
                counts["director_artifacts"] += 1
            db.commit()
        else:
            if registry_path.exists():
                payload = _read_json(registry_path)
                counts["registry_snapshots"] += 1 + len(backup_paths)
                counts["registry_experiments"] = len(payload.get("experiments") or [])
                counts["registry_runs"] = len(payload.get("runs") or [])
            counts["retention_rows"] = sum(_count_jsonl(path) for path in retention_paths)
            counts["director_artifacts"] = len(director_paths)
            db.rollback()
        deleted: list[str] = []
        if apply and delete_after_import:
            deleted = _delete_imported_files(source_paths)
        return {
            "apply": apply,
            "delete_after_import": delete_after_import,
            "source_files": len(source_paths),
            "source_manifest": source_manifest,
            "counts": counts,
            "deleted": deleted,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _persist_registry_payload(db: Any, payload: dict[str, Any], *, persist_current_state: bool) -> None:
    registry_hash = _persist_registry_snapshot(db, payload)
    if not persist_current_state:
        return
    _persist_registry_current_state(db, payload, registry_hash=registry_hash)


def _persist_registry_snapshot(db: Any, payload: dict[str, Any]) -> str:
    registry = GlobalExperimentRegistry(Path("global_experiment_registry.json"))
    registry_hash = str(payload.get("registry_hash") or registry.registry_hash(payload))
    latest_manifest = payload.get("latest_run_manifest") if isinstance(payload.get("latest_run_manifest"), dict) else {}
    now = datetime.now(timezone.utc)
    snapshot = (
        db.query(ResearchExperimentRegistrySnapshot)
        .filter(ResearchExperimentRegistrySnapshot.registry_hash == registry_hash)
        .first()
    )
    if snapshot is None:
        snapshot = ResearchExperimentRegistrySnapshot(
            registry_hash=registry_hash,
            previous_registry_hash=str(latest_manifest.get("previous_registry_hash") or ""),
            run_manifest_hash=str(latest_manifest.get("run_manifest_hash") or ""),
            global_trial_count=int(payload.get("global_trial_count") or 0),
            experiment_count=len(payload.get("experiments") or []),
            run_count=len(payload.get("runs") or []),
            payload_json=payload,
            created_at=now,
        )
        db.add(snapshot)
    return registry_hash


def _persist_registry_current_state(db: Any, payload: dict[str, Any], *, registry_hash: str) -> None:
    now = datetime.now(timezone.utc)
    for row in payload.get("experiments") or []:
        if not isinstance(row, dict) or not row.get("experiment_id"):
            continue
        experiment = (
            db.query(ResearchExperimentRegistryExperiment)
            .filter(ResearchExperimentRegistryExperiment.experiment_id == str(row["experiment_id"]))
            .first()
        )
        if experiment is None:
            experiment = ResearchExperimentRegistryExperiment(
                experiment_id=str(row["experiment_id"]),
                created_at=now,
            )
            db.add(experiment)
        experiment.family_id = str(row.get("family_id") or "")
        experiment.pattern_key = str(row.get("pattern_key") or "")
        experiment.variant_id = str(row.get("variant_id") or "")
        experiment.side = str(row.get("side") or "")
        experiment.timeframe = str(row.get("timeframe") or "")
        experiment.window_size = int(row.get("window_size") or 0)
        experiment.first_run_id = str(row.get("first_run_id") or row.get("run_id") or "")
        experiment.latest_run_id = str(row.get("latest_run_id") or row.get("run_id") or "")
        experiment.replication_count = int(row.get("replication_count") or 1)
        experiment.candidate_trial_count = int(row.get("candidate_trial_count") or 1)
        experiment.global_trial_count_after = int(row.get("global_trial_count_after") or 0)
        experiment.edge_claim = str(row.get("edge_claim") or "NO_DEMOSTRADO")
        experiment.payload_json = row
        experiment.updated_at = now
    for row in payload.get("runs") or []:
        if not isinstance(row, dict) or row.get("run_id") is None:
            continue
        run_id = str(row.get("run_id"))
        run = (
            db.query(ResearchExperimentRegistryRun)
            .filter(ResearchExperimentRegistryRun.run_id == run_id)
            .first()
        )
        if run is None:
            run = ResearchExperimentRegistryRun(run_id=run_id, created_at=now)
            db.add(run)
        run.registered_at = str(row.get("registered_at") or "")
        run.candidate_count = int(row.get("candidate_count") or 0)
        run.new_experiments = int(row.get("new_experiments") or 0)
        run.repeated_experiments = int(row.get("repeated_experiments") or 0)
        run.previous_registry_hash = str(row.get("previous_registry_hash") or "")
        run.run_manifest_hash = str(row.get("run_manifest_hash") or "")
        run.registry_hash = registry_hash
        run.params_json = row.get("params") if isinstance(row.get("params"), dict) else {}
        run.payload_json = row
        run.updated_at = now


def _persist_retention_jsonl(db: Any, path: Path) -> int:
    inserted = 0
    source_registry = str(path)
    existing_by_path = {
        row.path: row
        for row in db.query(ResearchArtifactRetention)
        .filter(ResearchArtifactRetention.source_registry == source_registry)
        .all()
    }
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row_path = str(row.get("path") or "")
            existing = existing_by_path.get(row_path)
            if existing is None:
                existing = ResearchArtifactRetention(
                    source_registry=source_registry,
                    path=row_path,
                )
                db.add(existing)
                existing_by_path[row_path] = existing
                inserted += 1
            existing.content_hash = str(row.get("content_hash") or "")
            existing.kind = str(row.get("kind") or "")
            existing.bytes = int(row.get("bytes") or 0)
            existing.mtime = str(row.get("mtime") or "")
            existing.params_hash = str(row.get("params_hash") or "")
            existing.parse_ok = bool(row.get("parse_ok", True))
            existing.pattern_count = int(row.get("pattern_count") or 0)
            existing.params_json = row.get("params_summary") if isinstance(row.get("params_summary"), dict) else {}
            existing.patterns_json = row.get("patterns") if isinstance(row.get("patterns"), list) else []
            existing.payload_json = row
            if line_no % 5000 == 0:
                db.flush()
    return inserted


def _persist_director_artifact(db: Any, path: Path) -> None:
    content = path.read_text(encoding="utf-8", errors="replace")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        payload = {}
    if path.name == "latest_research_director.json":
        kind = "latest_research_director_json"
    elif path.name == "latest_research_director.md":
        kind = "latest_research_director_markdown"
    elif path.suffix == ".md":
        kind = "research_director_markdown"
    else:
        kind = "research_director_json"
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    artifact = (
        db.query(ResearchDirectorArtifact)
        .filter(ResearchDirectorArtifact.path == str(path))
        .filter(ResearchDirectorArtifact.content_hash == content_hash)
        .first()
    )
    if artifact is None:
        artifact = ResearchDirectorArtifact(
            path=str(path),
            content_hash=content_hash,
            created_at=datetime.now(timezone.utc),
        )
        db.add(artifact)
    artifact.kind = kind
    artifact.run_id = str(_run_id_from_name(path.name) or "")
    artifact.payload_json = payload if isinstance(payload, dict) else {}
    artifact.content_text = "" if path.suffix == ".json" and isinstance(payload, dict) else content


def _delete_imported_files(paths: list[Path]) -> list[str]:
    deleted: list[str] = []
    for path in paths:
        try:
            if path.exists() and path.is_file():
                path.unlink()
                deleted.append(str(path))
        except OSError:
            continue
    return deleted


def _file_manifest(path: Path, *, reports_root: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(reports_root.parent)),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _count_jsonl(path: Path) -> int:
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _run_id_from_name(name: str) -> int | None:
    match = _RUN_ID_RE.search(name)
    return int(match.group(1)) if match else None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate research registry state to DB.")
    parser.add_argument("--reports-root", default="reports/research")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--delete-after-import", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
