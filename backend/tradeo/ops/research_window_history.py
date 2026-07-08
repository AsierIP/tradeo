from __future__ import annotations

import argparse
import gzip
import json
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import get_settings
from tradeo.db.models import ResearchAnalyzedWindow
from tradeo.db.session import SessionLocal

_MARKDOWN_EXAMPLE_RE = re.compile(r"\{[^{}]*'symbol': '([^']+)'[^{}]*'window_end': '([^']+)'[^{}]*\}")
_MARKDOWN_FIELD_RE = re.compile(r"'([^']+)': ('[^']*'|None|-?\d+(?:\.\d+)?|True|False)")
_MARKDOWN_PARAMS_RE = re.compile(r"## Par.metros\s+```json\s+(.*?)\s+```", re.DOTALL)
_RUN_ID_RE = re.compile(r"discovery_run_(\d+)_")
_WINDOW_SIZE_RE = re.compile(r"_W(\d+)_|_w(\d+)_")


def main() -> None:
    args = _parse_args()
    reports_root = Path(args.reports_root or get_settings().reports_path / "research")
    result = import_research_window_history(
        reports_root=reports_root,
        delete_after_import=bool(args.delete_after_import),
        dry_run=not bool(args.apply),
        limit=args.limit,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def import_research_window_history(
    *,
    reports_root: Path,
    delete_after_import: bool,
    dry_run: bool,
    limit: int | None = None,
) -> dict[str, Any]:
    db = SessionLocal()
    try:
        return _import_with_session(
            db,
            reports_root=reports_root,
            delete_after_import=delete_after_import,
            dry_run=dry_run,
            limit=limit,
        )
    finally:
        db.close()


def _import_with_session(
    db: Session,
    *,
    reports_root: Path,
    delete_after_import: bool,
    dry_run: bool,
    limit: int | None,
) -> dict[str, Any]:
    ledger_paths = sorted((reports_root / "event_ledgers").glob("run_*/*.json.gz"))
    if limit is not None:
        ledger_paths = ledger_paths[: max(0, int(limit))]
    report_cache: dict[int, dict[str, Any]] = {}
    manifest_cache: dict[int, dict[str, Any]] = {}
    inserted = 0
    duplicates = 0
    artifacts_seen: set[Path] = set()
    errors: list[dict[str, str]] = []
    now = datetime.now(timezone.utc)

    for ledger_path in ledger_paths:
        try:
            ledger = _read_json_gz(ledger_path)
            run_id = int(ledger.get("run_id") or _run_id_from_path(ledger_path) or 0)
            report = _report_for_run(reports_root, run_id, report_cache)
            manifest = _manifest_for_run(reports_root, run_id, manifest_cache)
            params = _params_for_legacy_run(report, manifest)
            records = _records_from_ledger(
                ledger,
                ledger_path=ledger_path,
                params=params,
                manifest=manifest,
                created_at=now,
            )
            if not records:
                continue
            artifacts_seen.add(ledger_path)
            artifacts_seen.update(_related_run_artifacts(reports_root, run_id))
            fingerprints = [record.fingerprint for record in records]
            existing = set()
            if not dry_run:
                existing = {
                    row[0]
                    for row in db.query(ResearchAnalyzedWindow.fingerprint)
                    .filter(ResearchAnalyzedWindow.fingerprint.in_(fingerprints))
                    .all()
                }
            new_records = [record for record in records if record.fingerprint not in existing]
            duplicates += len(records) - len(new_records)
            inserted += len(new_records)
            if not dry_run and new_records:
                db.add_all(new_records)
                db.flush()
        except Exception as exc:  # noqa: BLE001
            errors.append({"path": str(ledger_path), "error": f"{type(exc).__name__}: {exc}"})

    markdown_paths = sorted(reports_root.glob("discovery_run_*.md"))
    if limit is not None:
        markdown_paths = markdown_paths[: max(0, int(limit))]
    markdown_inserted = 0
    markdown_duplicates = 0
    markdown_files_with_records = 0
    for markdown_path in markdown_paths:
        try:
            run_id = _run_id_from_report_path(markdown_path) or 0
            records = _records_from_markdown(markdown_path, run_id=run_id, created_at=now)
            if not records:
                continue
            markdown_files_with_records += 1
            artifacts_seen.add(markdown_path)
            fingerprints = [record.fingerprint for record in records]
            existing = set()
            if not dry_run:
                existing = {
                    row[0]
                    for row in db.query(ResearchAnalyzedWindow.fingerprint)
                    .filter(ResearchAnalyzedWindow.fingerprint.in_(fingerprints))
                    .all()
                }
            new_records = [record for record in records if record.fingerprint not in existing]
            markdown_duplicates += len(records) - len(new_records)
            markdown_inserted += len(new_records)
            if not dry_run and new_records:
                db.add_all(new_records)
                db.flush()
        except Exception as exc:  # noqa: BLE001
            errors.append({"path": str(markdown_path), "error": f"{type(exc).__name__}: {exc}"})

    inserted += markdown_inserted
    duplicates += markdown_duplicates

    deleted: list[str] = []
    if not dry_run:
        db.commit()
        if delete_after_import and not errors:
            deleted = _delete_artifacts(artifacts_seen)
    else:
        db.rollback()

    return {
        "reports_root": str(reports_root),
        "dry_run": dry_run,
        "delete_after_import": delete_after_import,
        "ledger_files_scanned": len(ledger_paths),
        "markdown_files_scanned": len(markdown_paths),
        "markdown_files_with_records": markdown_files_with_records,
        "markdown_windows_inserted": markdown_inserted,
        "markdown_windows_duplicate": markdown_duplicates,
        "windows_inserted": inserted,
        "windows_duplicate": duplicates,
        "artifacts_eligible_for_delete": len(artifacts_seen),
        "artifacts_deleted": deleted,
        "errors": errors[:25],
        "error_count": len(errors),
    }


def _records_from_ledger(
    ledger: dict[str, Any],
    *,
    ledger_path: Path,
    params: dict[str, Any],
    manifest: dict[str, Any],
    created_at: datetime,
) -> list[ResearchAnalyzedWindow]:
    run_id = int(ledger.get("run_id") or 0)
    timeframe = str(ledger.get("timeframe") or params.get("interval") or "")
    window_size = int(ledger.get("window_size") or 0)
    manifest_hash = str(manifest.get("manifest_hash") or "")
    entries_by_symbol = _manifest_entries_by_symbol(manifest)
    records: list[ResearchAnalyzedWindow] = []
    for event in ledger.get("events") or []:
        if not isinstance(event, dict):
            continue
        symbol = str(event.get("symbol") or "").upper()
        window_end = str(event.get("window_end") or "")
        if not symbol or not window_end or window_size <= 0:
            continue
        entry = entries_by_symbol.get(symbol, {})
        fingerprint = PatternDiscoveryLabAgent._window_fingerprint(
            universe_key=str(params.get("universe_key") or ""),
            symbol=symbol,
            timeframe=timeframe,
            window_start="",
            window_end=window_end,
            window_size=window_size,
            source_kind="legacy_event_ledger",
        )
        records.append(
            ResearchAnalyzedWindow(
                fingerprint=fingerprint,
                run_id=run_id or None,
                cadence=str(params.get("cadence") or ""),
                universe_key=str(params.get("universe_key") or ""),
                universe_scope=str(params.get("universe_scope") or ""),
                universe_file=str(params.get("universe_file") or ""),
                universe_hash=str(params.get("universe_hash") or ""),
                symbol=symbol,
                timeframe=timeframe,
                window_start="",
                window_end=window_end,
                window_size=window_size,
                forward_end=str(event.get("forward_end") or ""),
                data_period=str(params.get("period") or ""),
                data_manifest_hash=manifest_hash,
                data_artifact_path=str(entry.get("path") or ""),
                data_artifact_sha256=str(entry.get("sha256") or ""),
                data_rows=int(entry.get("rows") or 0),
                source_kind="legacy_event_ledger",
                source_artifact_path=str(ledger_path),
                metadata_json={
                    "pattern_key": ledger.get("pattern_key"),
                    "side": event.get("side") or ledger.get("side"),
                    "split": event.get("split"),
                    "year": event.get("year"),
                    "rr": event.get("rr"),
                    "result_r": event.get("result_r"),
                    "sample_label": event.get("sample_label"),
                    "data_lineage": event.get("data_lineage") or {},
                },
                created_at=created_at,
            )
        )
    return _dedupe_records(records)


def _records_from_markdown(
    path: Path,
    *,
    run_id: int,
    created_at: datetime,
) -> list[ResearchAnalyzedWindow]:
    text = path.read_text(encoding="utf-8", errors="replace")
    params = _params_from_markdown(text)
    records: list[ResearchAnalyzedWindow] = []
    current_window_size = 0
    current_pattern_key = ""
    for line in text.splitlines():
        if line.startswith("### "):
            current_pattern_key = line.removeprefix("### ").strip()
            current_window_size = _window_size_from_text(current_pattern_key)
            continue
        if "'window_size':" in line and current_window_size <= 0:
            current_window_size = _int_field(line, "window_size")
        if "'pattern_key':" in line and not current_pattern_key:
            current_pattern_key = _str_field(line, "pattern_key")
        if "'examples':" not in line or "'window_end':" not in line or "'symbol':" not in line:
            continue
        for match in _MARKDOWN_EXAMPLE_RE.finditer(line):
            raw = match.group(0)
            symbol = match.group(1).upper()
            window_end = match.group(2)
            window_size = current_window_size or _window_size_from_text(raw)
            if not symbol or not window_end or window_size <= 0:
                continue
            fingerprint = PatternDiscoveryLabAgent._window_fingerprint(
                universe_key=str(params.get("universe_key") or ""),
                symbol=symbol,
                timeframe=str(params.get("interval") or ""),
                window_start="",
                window_end=window_end,
                window_size=window_size,
                source_kind="legacy_markdown_example",
            )
            records.append(
                ResearchAnalyzedWindow(
                    fingerprint=fingerprint,
                    run_id=run_id or None,
                    cadence=str(params.get("cadence") or ""),
                    universe_key=str(params.get("universe_key") or ""),
                    universe_scope=str(params.get("universe_scope") or ""),
                    universe_file=str(params.get("universe_file") or ""),
                    universe_hash=str(params.get("universe_hash") or ""),
                    symbol=symbol,
                    timeframe=str(params.get("interval") or ""),
                    window_start="",
                    window_end=window_end,
                    window_size=window_size,
                    forward_end="",
                    data_period=str(params.get("period") or ""),
                    source_kind="legacy_markdown_example",
                    source_artifact_path=str(path),
                    metadata_json={
                        "pattern_key": current_pattern_key,
                        "label": _str_field(raw, "label"),
                        "expected_result_r": _float_field(raw, "expected_result_r"),
                        "full_fill_result_r": _float_field(raw, "full_fill_result_r"),
                        "fill_probability": _float_field(raw, "fill_probability"),
                        "target_bar": _optional_int_field(raw, "target_bar"),
                        "stop_bar": _optional_int_field(raw, "stop_bar"),
                    },
                    created_at=created_at,
                )
            )
    return _dedupe_records(records)


def _params_from_markdown(text: str) -> dict[str, Any]:
    match = _MARKDOWN_PARAMS_RE.search(text)
    params: dict[str, Any] = {}
    if match:
        try:
            params = json.loads(match.group(1))
        except json.JSONDecodeError:
            params = {}
    interval = str(params.get("interval") or "")
    cadence = str(params.get("cadence") or ("intraday" if interval.endswith("m") else "daily"))
    universe_scope = str(params.get("universe_scope") or cadence)
    universe_file = str(params.get("universe_file") or "")
    universe_hash = str(params.get("universe_hash") or "")
    if not universe_hash and universe_file:
        universe_hash = PatternDiscoveryLabAgent._file_sha256(universe_file)
    universe_key = str(params.get("universe_key") or "")
    if not universe_key:
        universe_key = PatternDiscoveryLabAgent._universe_key(
            scope=universe_scope,
            universe_file=universe_file,
        )
    return {
        "cadence": cadence,
        "interval": interval,
        "period": str(params.get("period") or ""),
        "universe_scope": universe_scope,
        "universe_file": universe_file,
        "universe_hash": universe_hash,
        "universe_key": universe_key,
    }


def _window_size_from_text(value: str) -> int:
    match = _WINDOW_SIZE_RE.search(value)
    if not match:
        return 0
    return int(match.group(1) or match.group(2) or 0)


def _str_field(raw: str, field: str) -> str:
    match = re.search(rf"'{re.escape(field)}': '([^']*)'", raw)
    return match.group(1) if match else ""


def _int_field(raw: str, field: str) -> int:
    value = _optional_int_field(raw, field)
    return int(value or 0)


def _optional_int_field(raw: str, field: str) -> int | None:
    match = re.search(rf"'{re.escape(field)}': (None|-?\d+)", raw)
    if not match or match.group(1) == "None":
        return None
    return int(match.group(1))


def _float_field(raw: str, field: str) -> float | None:
    match = re.search(rf"'{re.escape(field)}': (None|-?\d+(?:\.\d+)?)", raw)
    if not match or match.group(1) == "None":
        return None
    return float(match.group(1))


def _dedupe_records(records: Iterable[ResearchAnalyzedWindow]) -> list[ResearchAnalyzedWindow]:
    seen: set[str] = set()
    unique: list[ResearchAnalyzedWindow] = []
    for record in records:
        if record.fingerprint in seen:
            continue
        seen.add(record.fingerprint)
        unique.append(record)
    return unique


def _params_for_legacy_run(report: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    params = dict(report.get("params") or {})
    interval = str(params.get("interval") or "")
    cadence = str(params.get("cadence") or ("intraday" if interval.endswith("min") else "daily"))
    universe_scope = str(params.get("universe_scope") or cadence)
    universe_file = str(params.get("universe_file") or "")
    universe_hash = str(params.get("universe_hash") or "")
    if not universe_hash and universe_file:
        universe_hash = PatternDiscoveryLabAgent._file_sha256(universe_file)
    universe_key = str(params.get("universe_key") or "")
    if not universe_key:
        universe_key = PatternDiscoveryLabAgent._universe_key(
            scope=universe_scope,
            universe_file=universe_file,
        )
    return {
        "cadence": cadence,
        "interval": interval,
        "period": str(params.get("period") or _manifest_period(manifest) or ""),
        "universe_scope": universe_scope,
        "universe_file": universe_file,
        "universe_hash": universe_hash,
        "universe_key": universe_key,
    }


def _manifest_entries_by_symbol(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = manifest.get("entries")
    if not isinstance(entries, dict):
        return {}
    return {
        str(entry.get("symbol") or "").upper(): entry
        for entry in entries.values()
        if isinstance(entry, dict)
    }


def _manifest_period(manifest: dict[str, Any]) -> str:
    for entry in _manifest_entries_by_symbol(manifest).values():
        period = entry.get("period")
        if period:
            return str(period)
    return ""


def _report_for_run(root: Path, run_id: int, cache: dict[int, dict[str, Any]]) -> dict[str, Any]:
    if run_id in cache:
        return cache[run_id]
    matches = sorted(root.glob(f"discovery_run_{run_id}_*.json"))
    cache[run_id] = _read_json(matches[-1]) if matches else {}
    return cache[run_id]


def _manifest_for_run(root: Path, run_id: int, cache: dict[int, dict[str, Any]]) -> dict[str, Any]:
    if run_id in cache:
        return cache[run_id]
    path = root / "data_manifests" / f"discovery_run_{run_id}_data_manifest.json"
    cache[run_id] = _read_json(path) if path.exists() else {}
    return cache[run_id]


def _related_run_artifacts(root: Path, run_id: int) -> set[Path]:
    artifacts = set(root.glob(f"discovery_run_{run_id}_*.*"))
    manifest = root / "data_manifests" / f"discovery_run_{run_id}_data_manifest.json"
    if manifest.exists():
        artifacts.add(manifest)
    return artifacts


def _delete_artifacts(paths: Iterable[Path]) -> list[str]:
    deleted: list[str] = []
    for path in sorted(paths):
        try:
            if path.exists() and path.is_file():
                path.unlink()
                deleted.append(str(path))
        except OSError:
            continue
    for parent in sorted({path.parent for path in paths}, reverse=True):
        try:
            parent.rmdir()
        except OSError:
            pass
    return deleted


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return json.load(handle)


def _read_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _run_id_from_path(path: Path) -> int | None:
    for part in path.parts:
        if part.startswith("run_"):
            try:
                return int(part.removeprefix("run_"))
            except ValueError:
                return None
    return None


def _run_id_from_report_path(path: Path) -> int | None:
    match = _RUN_ID_RE.search(path.name)
    return int(match.group(1)) if match else None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import historical research chart windows.")
    parser.add_argument("--reports-root", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true", help="write rows to the configured database")
    parser.add_argument(
        "--delete-after-import",
        action="store_true",
        help="delete imported local report artifacts after a successful --apply run",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
