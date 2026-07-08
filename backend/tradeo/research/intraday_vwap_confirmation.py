from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from tradeo.research.intraday_research_evidence import derive_time_features, safe_candidate_key
from tradeo.research.intraday_research_forensics import observed_run_ids_from_payload
from tradeo.research.intraday_vwap_features import build_intraday_vwap_features

SCHEMA_VERSION = "tradeo.intraday_vwap_confirmation.v1"
DEFAULT_RUN_ID = 6454
DEFAULT_PATTERN_KEY = "novel_long_w100_551e1329b8e371f19e35"

EVENT_FIELDS = (
    "run_id",
    "pattern_key",
    "candidate_id",
    "pattern_id",
    "symbol",
    "timeframe",
    "window_size",
    "window_start",
    "window_end",
    "entry_ts",
    "entry_price",
    "risk_proxy",
    "outcome_r",
    "mfe_r",
    "mae_r",
    "forward_end",
    "vwap_at_entry",
    "price_vs_vwap_bps",
    "vwap_slope_bps",
    "session_bucket",
    "month",
    "source",
    "data_quality",
)


class CandidateScopeError(ValueError):
    """Raised when requested candidate reconstruction would mix scope."""


@dataclass(frozen=True, slots=True)
class CandidateScope:
    run_id: int = DEFAULT_RUN_ID
    pattern_key: str = DEFAULT_PATTERN_KEY


@dataclass(frozen=True, slots=True)
class CandidateArtifacts:
    wave_manifest: dict[str, Any]
    forensics: dict[str, Any]
    evidence: dict[str, Any]
    wave_manifest_path: Path | None = None
    forensics_json_path: Path | None = None
    evidence_json_path: Path | None = None


@dataclass(frozen=True, slots=True)
class CandidateEventRecord:
    run_id: int | None
    pattern_key: str | None
    candidate_id: str | None
    pattern_id: int | None
    symbol: str | None
    timeframe: str | None
    window_size: int | None
    window_start: str | None
    window_end: str | None
    entry_ts: str | None
    entry_price: float | None
    risk_proxy: float | None
    outcome_r: float | None
    mfe_r: float | None
    mae_r: float | None
    forward_end: str | None
    vwap_at_entry: float | None
    price_vs_vwap_bps: float | None
    vwap_slope_bps: float | None
    session_bucket: str | None
    month: str | None
    source: str | None
    data_quality: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = {field: _json_safe(value) for field, value in asdict(self).items()}
        missing = [
            field
            for field in EVENT_FIELDS
            if field != "data_quality" and payload.get(field) is None
        ]
        quality = dict(payload.get("data_quality") or {})
        quality["missing_fields"] = missing
        payload["data_quality"] = _json_safe(quality)
        return {field: payload.get(field) for field in EVENT_FIELDS}


def load_wave_manifest(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def load_forensics_json(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def load_evidence_json(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def load_candidate_artifacts(
    *,
    wave_manifest_path: str | Path,
    forensics_json_path: str | Path,
    evidence_json_path: str | Path,
) -> CandidateArtifacts:
    wave_path = Path(wave_manifest_path)
    forensics_path = Path(forensics_json_path)
    evidence_path = Path(evidence_json_path)
    return CandidateArtifacts(
        wave_manifest=load_wave_manifest(wave_path),
        forensics=load_forensics_json(forensics_path),
        evidence=load_evidence_json(evidence_path),
        wave_manifest_path=wave_path,
        forensics_json_path=forensics_path,
        evidence_json_path=evidence_path,
    )


def build_candidate_confirmation_dataset(
    *,
    wave_manifest_path: str | Path,
    forensics_json_path: str | Path,
    evidence_json_path: str | Path,
    requested_run_id: int = DEFAULT_RUN_ID,
    pattern_key: str = DEFAULT_PATTERN_KEY,
    db: Any | None = None,
    ohlcv_cache_dir: str | Path | None = None,
    project_root: str | Path | None = None,
    strict_artifact_scope: bool = False,
    max_events: int | None = None,
) -> dict[str, Any]:
    """Build a read-only candidate event dataset for the requested VWAP pattern."""

    scope = CandidateScope(run_id=int(requested_run_id), pattern_key=str(pattern_key))
    artifacts = load_candidate_artifacts(
        wave_manifest_path=wave_manifest_path,
        forensics_json_path=forensics_json_path,
        evidence_json_path=evidence_json_path,
    )
    scope_report = validate_requested_scope(
        artifacts,
        scope=scope,
        strict_artifact_scope=strict_artifact_scope,
    )
    evidence_records = load_evidence_candidate_events(
        artifacts.evidence,
        evidence_json_path=artifacts.evidence_json_path,
        scope=scope,
        project_root=project_root,
        max_events=max_events,
    )
    db_records = (
        load_db_candidate_events(db, scope=scope, max_events=max_events)
        if db is not None
        else []
    )
    records = merge_candidate_event_records(evidence_records, db_records)
    if max_events is not None:
        records = records[: max(0, int(max_events))]
    if ohlcv_cache_dir is not None:
        spec = _wave_spec(artifacts.wave_manifest)
        period = _clean_text(spec.get("period"))
        cache = OhlcvVwapCache(ohlcv_cache_dir, period=period)
        records = [cache.enrich(record) for record in records]
    validate_event_records_scope(records, scope=scope)
    events = [record.to_dict() for record in records]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": {
            "exact_scope": True,
            "requested_run_id": scope.run_id,
            "requested_pattern_key": scope.pattern_key,
            **scope_report,
        },
        "event_count": len(events),
        "events": events,
        "missing_fields_summary": missing_fields_summary(events),
        "safety": safety_manifest(),
    }


def validate_requested_scope(
    artifacts: CandidateArtifacts,
    *,
    scope: CandidateScope = CandidateScope(),
    strict_artifact_scope: bool = False,
) -> dict[str, Any]:
    manifest_run_ids = _manifest_run_ids(artifacts.wave_manifest)
    forensics_scope_run_ids = _scope_run_ids(artifacts.forensics)
    evidence_scope_run_ids = _scope_run_ids(artifacts.evidence)
    artifact_run_ids = _dedupe_ints(
        [*manifest_run_ids, *forensics_scope_run_ids, *evidence_scope_run_ids]
    )
    target_candidates = [
        row
        for row in [*_candidate_rows(artifacts.forensics), *_candidate_rows(artifacts.evidence)]
        if _candidate_matches(row, scope.pattern_key)
    ]
    errors: list[str] = []
    warnings: list[str] = []
    if manifest_run_ids and scope.run_id not in manifest_run_ids:
        errors.append(f"requested run_id {scope.run_id} is absent from wave manifest")
    if not target_candidates:
        errors.append(
            f"requested pattern_key {scope.pattern_key!r} is absent from candidate artifacts"
        )
    for candidate in target_candidates:
        candidate_run_id = _optional_int(candidate.get("run_id"))
        if candidate_run_id is not None and candidate_run_id != scope.run_id:
            errors.append(
                "requested pattern_key appears with out-of-scope run_id "
                f"{candidate_run_id}"
            )
    out_of_scope_artifact_run_ids = [
        run_id for run_id in artifact_run_ids if run_id != scope.run_id
    ]
    if out_of_scope_artifact_run_ids:
        message = (
            "source artifact contains additional run IDs; reconstruction filters the requested "
            "candidate only"
        )
        if strict_artifact_scope:
            errors.append(message)
        else:
            warnings.append(message)
    if errors:
        raise CandidateScopeError("; ".join(errors))
    return {
        "manifest_run_ids": manifest_run_ids,
        "forensics_scope_run_ids": forensics_scope_run_ids,
        "evidence_scope_run_ids": evidence_scope_run_ids,
        "artifact_run_ids": artifact_run_ids,
        "out_of_scope_artifact_run_ids": out_of_scope_artifact_run_ids,
        "strict_artifact_scope": bool(strict_artifact_scope),
        "warnings": warnings,
    }


def load_evidence_candidate_events(
    evidence: dict[str, Any],
    *,
    evidence_json_path: str | Path | None,
    scope: CandidateScope = CandidateScope(),
    project_root: str | Path | None = None,
    max_events: int | None = None,
) -> list[CandidateEventRecord]:
    metadata = _target_candidate_metadata(evidence, scope) or {
        "run_id": scope.run_id,
        "pattern_key": scope.pattern_key,
        "candidate_key": scope.pattern_key,
    }
    records: list[CandidateEventRecord] = []
    for sample in _inline_evidence_samples(evidence, scope):
        _validate_raw_event_scope(sample, scope)
        records.append(
            _event_from_evidence_sample(
                sample,
                metadata=metadata,
                source_label="evidence_json",
            )
        )
        if _limit_reached(records, max_events):
            return records

    for jsonl_path in _candidate_jsonl_paths(
        evidence,
        evidence_json_path=evidence_json_path,
        scope=scope,
        project_root=project_root,
    ):
        for sample in _read_jsonl(jsonl_path):
            _validate_raw_event_scope(sample, scope)
            records.append(
                _event_from_evidence_sample(
                    sample,
                    metadata=metadata,
                    source_label=f"evidence_jsonl:{jsonl_path.name}",
                )
            )
            if _limit_reached(records, max_events):
                return records
    return _dedupe_records(records)


def load_db_candidate_events(
    db: Any,
    *,
    scope: CandidateScope = CandidateScope(),
    max_events: int | None = None,
) -> list[CandidateEventRecord]:
    if db is None:
        return []
    from tradeo.db.models import DiscoveredPattern, DiscoveredPatternExample

    pattern = (
        db.query(DiscoveredPattern)
        .filter(DiscoveredPattern.run_id == scope.run_id)
        .filter(DiscoveredPattern.pattern_key == scope.pattern_key)
        .one_or_none()
    )
    if pattern is None:
        return []
    query = (
        db.query(DiscoveredPatternExample)
        .filter(DiscoveredPatternExample.pattern_id == int(pattern.id))
        .order_by(DiscoveredPatternExample.id.asc())
    )
    if max_events is not None:
        query = query.limit(max(0, int(max_events)))
    return [_event_from_db_example(pattern, example) for example in query.all()]


def merge_candidate_event_records(
    primary: Sequence[CandidateEventRecord],
    secondary: Sequence[CandidateEventRecord],
) -> list[CandidateEventRecord]:
    merged: list[CandidateEventRecord] = list(primary)
    index = {_event_key(record): idx for idx, record in enumerate(merged)}
    for record in secondary:
        key = _event_key(record)
        if key in index:
            merged[index[key]] = _merge_record(merged[index[key]], record)
        else:
            index[key] = len(merged)
            merged.append(record)
    return merged


def validate_event_records_scope(
    records: Sequence[CandidateEventRecord],
    *,
    scope: CandidateScope = CandidateScope(),
) -> None:
    errors: list[str] = []
    for idx, record in enumerate(records):
        if record.run_id != scope.run_id:
            errors.append(f"event {idx} has run_id {record.run_id!r}")
        if record.pattern_key != scope.pattern_key:
            errors.append(f"event {idx} has pattern_key {record.pattern_key!r}")
    if errors:
        raise CandidateScopeError("; ".join(errors))


class OhlcvVwapCache:
    def __init__(self, cache_dir: str | Path, *, period: str | None = None) -> None:
        self.cache_dir = Path(cache_dir)
        self.period = period
        self._frames: dict[tuple[str, str], pd.DataFrame | None] = {}

    def enrich(self, record: CandidateEventRecord) -> CandidateEventRecord:
        missing_inputs = [
            field
            for field, value in (
                ("symbol", record.symbol),
                ("timeframe", record.timeframe),
                ("entry_ts", record.entry_ts),
            )
            if value is None
        ]
        if missing_inputs:
            return _add_quality_warning(
                record,
                "ohlcv_cache_missing_inputs:" + ",".join(missing_inputs),
            )
        frame = self._feature_frame(str(record.symbol), str(record.timeframe))
        if frame is None or frame.empty:
            return _add_quality_warning(record, "ohlcv_cache_unavailable")
        target = _parse_timestamp(record.entry_ts, tz=frame.index.tz)
        if target is None:
            return _add_quality_warning(record, "entry_ts_parse_failed")
        if target not in frame.index:
            return _add_quality_warning(record, "ohlcv_exact_entry_bar_missing")
        row = frame.loc[target]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[-1]
        vwap = _optional_float(row.get("vwap"))
        close = _optional_float(row.get("close"))
        slope = _optional_float(row.get("vwap_slope_bps"))
        entry_price = record.entry_price
        filled_from: dict[str, str] = {}
        if entry_price is None and close is not None:
            entry_price = close
            filled_from["entry_price"] = "ohlcv_cache_close"
        price_vs_vwap = None
        if entry_price is not None and vwap not in (None, 0.0):
            price_vs_vwap = round((entry_price / float(vwap) - 1.0) * 10_000.0, 6)
        updated = replace(
            record,
            entry_price=entry_price,
            vwap_at_entry=vwap if record.vwap_at_entry is None else record.vwap_at_entry,
            price_vs_vwap_bps=(
                price_vs_vwap if record.price_vs_vwap_bps is None else record.price_vs_vwap_bps
            ),
            vwap_slope_bps=slope if record.vwap_slope_bps is None else record.vwap_slope_bps,
        )
        quality = _merged_quality(record.data_quality, {})
        if filled_from:
            quality.setdefault("filled_from", {}).update(filled_from)
        quality.setdefault("filled_from", {}).update(
            {
                key: "ohlcv_cache"
                for key, old_value, new_value in (
                    ("vwap_at_entry", record.vwap_at_entry, updated.vwap_at_entry),
                    (
                        "price_vs_vwap_bps",
                        record.price_vs_vwap_bps,
                        updated.price_vs_vwap_bps,
                    ),
                    ("vwap_slope_bps", record.vwap_slope_bps, updated.vwap_slope_bps),
                )
                if old_value is None and new_value is not None
            }
        )
        return replace(updated, data_quality=quality)

    def _feature_frame(self, symbol: str, timeframe: str) -> pd.DataFrame | None:
        key = (symbol.upper(), timeframe)
        if key in self._frames:
            return self._frames[key]
        csv_path = self._cache_path(symbol, timeframe)
        if csv_path is None:
            self._frames[key] = None
            return None
        try:
            bars = pd.read_csv(csv_path)
            timestamp_column = "timestamp" if "timestamp" in bars.columns else None
            frame = build_intraday_vwap_features(
                bars,
                timestamp_column=timestamp_column,
            ).frame
        except (OSError, ValueError, KeyError, pd.errors.ParserError):
            self._frames[key] = None
            return None
        self._frames[key] = frame
        return frame

    def _cache_path(self, symbol: str, timeframe: str) -> Path | None:
        symbol = symbol.upper()
        if self.period:
            exact = self.cache_dir / f"{symbol}_{timeframe}_{self.period}.csv"
            if exact.exists():
                return exact
        matches = sorted(self.cache_dir.glob(f"{symbol}_{timeframe}_*.csv"))
        return matches[0] if matches else None


def missing_fields_summary(events: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        for field in EVENT_FIELDS:
            if field == "data_quality":
                continue
            if event.get(field) is None:
                counts[field] = counts.get(field, 0) + 1
    return dict(sorted(counts.items()))


def safety_manifest() -> dict[str, bool]:
    return {
        "live_allowed": False,
        "paper_allowed": False,
        "orders_allowed": False,
        "order_code_allowed": False,
        "broker_allowed": False,
        "gates_allowed": False,
        "scoring_changes_allowed": False,
        "read_only": True,
    }


def _event_from_evidence_sample(
    sample: dict[str, Any],
    *,
    metadata: dict[str, Any],
    source_label: str,
) -> CandidateEventRecord:
    entry_ts = _clean_text(_first_present(sample.get("entry_ts"), sample.get("window_end_ts")))
    time_features = derive_time_features(entry_ts)
    source = _join_sources(source_label, _clean_text(sample.get("source")))
    quality = {
        "source_artifact": source_label,
        "source_type": "evidence",
        "filled_from": {},
        "warnings": [],
    }
    return CandidateEventRecord(
        run_id=_optional_int(_first_present(sample.get("run_id"), metadata.get("run_id"))),
        pattern_key=_clean_text(
            _first_present(sample.get("pattern_key"), metadata.get("pattern_key"))
        ),
        candidate_id=_clean_text(
            _first_present(
                sample.get("candidate_id"),
                sample.get("candidate_key"),
                metadata.get("candidate_id"),
                metadata.get("candidate_key"),
            )
        ),
        pattern_id=_optional_int(
            _first_present(sample.get("pattern_id"), metadata.get("pattern_id"))
        ),
        symbol=_symbol(_first_present(sample.get("symbol"), metadata.get("symbol"))),
        timeframe=_clean_text(_first_present(sample.get("timeframe"), metadata.get("timeframe"))),
        window_size=_optional_int(
            _first_present(sample.get("window_size"), metadata.get("window_size"))
        ),
        window_start=_clean_text(
            _first_present(sample.get("window_start"), sample.get("window_start_ts"))
        ),
        window_end=_clean_text(
            _first_present(sample.get("window_end"), sample.get("window_end_ts"))
        ),
        entry_ts=entry_ts,
        entry_price=_optional_float(sample.get("entry_price")),
        risk_proxy=_optional_float(sample.get("risk_proxy")),
        outcome_r=_optional_float(sample.get("outcome_r")),
        mfe_r=_optional_float(sample.get("mfe_r")),
        mae_r=_optional_float(sample.get("mae_r")),
        forward_end=_clean_text(_first_present(sample.get("forward_end"), sample.get("exit_ts"))),
        vwap_at_entry=_optional_float(sample.get("vwap_at_entry")),
        price_vs_vwap_bps=_optional_float(sample.get("price_vs_vwap_bps")),
        vwap_slope_bps=_optional_float(sample.get("vwap_slope_bps")),
        session_bucket=_session_bucket_value(
            _first_present(sample.get("session_bucket"), time_features["session_bucket"])
        ),
        month=_clean_text(sample.get("month")) or time_features["month"],
        source=source,
        data_quality=quality,
    )


def _event_from_db_example(pattern: Any, example: Any) -> CandidateEventRecord:
    features = example.features_json if isinstance(example.features_json, dict) else {}
    chart = example.chart_json if isinstance(example.chart_json, dict) else {}
    entry_ts = _clean_text(_first_present(features.get("entry_ts"), example.window_end))
    time_features = derive_time_features(entry_ts)
    return CandidateEventRecord(
        run_id=_optional_int(pattern.run_id),
        pattern_key=_clean_text(pattern.pattern_key),
        candidate_id=_clean_text(pattern.pattern_key),
        pattern_id=_optional_int(pattern.id),
        symbol=_symbol(example.symbol),
        timeframe=_clean_text(_first_present(example.timeframe, pattern.timeframe)),
        window_size=_optional_int(pattern.window_size),
        window_start=_clean_text(example.window_start),
        window_end=_clean_text(example.window_end),
        entry_ts=entry_ts,
        entry_price=_optional_float(example.entry_price),
        risk_proxy=_optional_float(example.risk_proxy),
        outcome_r=_optional_float(example.outcome_r),
        mfe_r=_optional_float(example.mfe_r),
        mae_r=_optional_float(example.mae_r),
        forward_end=_clean_text(_first_present(example.forward_end, features.get("forward_end"))),
        vwap_at_entry=_optional_float(
            _first_present(features.get("vwap_at_entry"), chart.get("vwap_at_entry"))
        ),
        price_vs_vwap_bps=_optional_float(
            _first_present(features.get("price_vs_vwap_bps"), chart.get("price_vs_vwap_bps"))
        ),
        vwap_slope_bps=_optional_float(
            _first_present(features.get("vwap_slope_bps"), chart.get("vwap_slope_bps"))
        ),
        session_bucket=_session_bucket_value(time_features["session_bucket"]),
        month=time_features["month"],
        source="db_discovered_pattern_examples",
        data_quality={
            "source_artifact": "db",
            "source_type": "db_discovered_pattern_examples",
            "filled_from": {},
            "warnings": [],
        },
    )


def _merge_record(base: CandidateEventRecord, extra: CandidateEventRecord) -> CandidateEventRecord:
    data = asdict(base)
    other = asdict(extra)
    filled_from: dict[str, str] = {}
    conflicts: list[str] = []
    for field in EVENT_FIELDS:
        if field == "data_quality":
            continue
        if field == "source":
            data[field] = _join_sources(data.get(field), other.get(field))
            continue
        if data.get(field) is None and other.get(field) is not None:
            data[field] = other[field]
            filled_from[field] = extra.source or "secondary"
        elif (
            data.get(field) is not None
            and other.get(field) is not None
            and data.get(field) != other.get(field)
            and field in {"entry_price", "risk_proxy", "outcome_r", "mfe_r", "mae_r"}
        ):
            conflicts.append(field)
    quality = _merged_quality(base.data_quality, extra.data_quality)
    if filled_from:
        quality.setdefault("filled_from", {}).update(filled_from)
    if conflicts:
        quality.setdefault("warnings", []).append(
            "secondary_source_conflicts_retained_primary:" + ",".join(sorted(conflicts))
        )
    data["data_quality"] = quality
    return CandidateEventRecord(**data)


def _candidate_jsonl_paths(
    evidence: dict[str, Any],
    *,
    evidence_json_path: str | Path | None,
    scope: CandidateScope,
    project_root: str | Path | None,
) -> list[Path]:
    paths: list[Path] = []
    runs = ((evidence.get("artifacts") or {}).get("runs") or {})
    if not isinstance(runs, dict):
        return paths
    for raw_run_id, entries in runs.items():
        run_id = _optional_int(raw_run_id)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            raw_path = _clean_text(entry.get("jsonl"))
            if raw_path is None:
                continue
            candidate_file = scope.pattern_key in Path(raw_path).name
            if candidate_file and run_id is not None and run_id != scope.run_id:
                raise CandidateScopeError(
                    f"candidate JSONL for {scope.pattern_key} is under out-of-scope run {run_id}"
                )
            if not candidate_file:
                continue
            paths.append(
                _resolve_artifact_path(
                    raw_path,
                    anchor=evidence_json_path,
                    project_root=project_root,
                )
            )
    return paths


def _inline_evidence_samples(
    evidence: dict[str, Any],
    scope: CandidateScope,
) -> list[dict[str, Any]]:
    groups = evidence.get("samples_by_candidate") or {}
    if not isinstance(groups, dict):
        return []
    samples = (
        groups.get(scope.pattern_key)
        or groups.get(safe_candidate_key(scope.pattern_key))
        or []
    )
    return [sample for sample in samples if isinstance(sample, dict)]


def _target_candidate_metadata(
    artifact: dict[str, Any],
    scope: CandidateScope,
) -> dict[str, Any] | None:
    for row in _candidate_rows(artifact):
        if _candidate_matches(row, scope.pattern_key):
            return dict(row)
    return None


def _candidate_rows(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in ("candidate_manifests", "candidate_forensics", "near_misses"):
        value = artifact.get(key) or []
        if isinstance(value, list):
            rows.extend(row for row in value if isinstance(row, dict))
    candidate = artifact.get("candidate")
    if isinstance(candidate, dict):
        rows.append(candidate)
    return rows


def _candidate_matches(row: dict[str, Any], pattern_key: str) -> bool:
    values = [
        _clean_text(row.get("pattern_key")),
        _clean_text(row.get("candidate_key")),
        _clean_text(row.get("candidate_id")),
    ]
    return pattern_key in values


def _validate_raw_event_scope(raw: dict[str, Any], scope: CandidateScope) -> None:
    run_id = _optional_int(raw.get("run_id"))
    if run_id is not None and run_id != scope.run_id:
        raise CandidateScopeError(f"event row has out-of-scope run_id {run_id}")
    keys = {
        value
        for value in (
            _clean_text(raw.get("pattern_key")),
            _clean_text(raw.get("candidate_key")),
            _clean_text(raw.get("candidate_id")),
        )
        if value is not None
    }
    if keys and scope.pattern_key not in keys:
        raise CandidateScopeError(
            f"event row is for out-of-scope pattern key(s): {sorted(keys)}"
        )


def _manifest_run_ids(manifest: dict[str, Any]) -> list[int]:
    rows = (((manifest.get("research_result") or {}).get("details") or {}).get("runs") or [])
    if isinstance(rows, list):
        return _dedupe_ints(
            _optional_int(row.get("run_id")) for row in rows if isinstance(row, dict)
        )
    return observed_run_ids_from_payload(manifest)


def _scope_run_ids(artifact: dict[str, Any]) -> list[int]:
    scope = artifact.get("scope") or {}
    if not isinstance(scope, dict):
        return []
    values = scope.get("run_ids") or scope.get("requested_run_ids") or []
    if isinstance(values, list):
        return _dedupe_ints(_optional_int(value) for value in values)
    value = _optional_int(values)
    return [value] if value is not None else []


def _wave_spec(wave_manifest: dict[str, Any]) -> dict[str, Any]:
    readiness = wave_manifest.get("readiness") or {}
    spec = readiness.get("spec") or {}
    return spec if isinstance(spec, dict) else {}


def _event_key(record: CandidateEventRecord) -> tuple[Any, ...]:
    return (
        record.run_id,
        record.pattern_key,
        record.symbol,
        record.timeframe,
        record.window_start,
        record.window_end,
        record.entry_ts,
    )


def _dedupe_records(records: Sequence[CandidateEventRecord]) -> list[CandidateEventRecord]:
    out: list[CandidateEventRecord] = []
    seen: set[tuple[Any, ...]] = set()
    for record in records:
        key = _event_key(record)
        if key in seen:
            continue
        seen.add(key)
        out.append(record)
    return out


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _load_json(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON artifact root must be an object")
    return payload


def _resolve_artifact_path(
    raw_path: str,
    *,
    anchor: str | Path | None,
    project_root: str | Path | None,
) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        if path.exists():
            return path
        raise FileNotFoundError(path)
    candidates: list[Path] = []
    if project_root is not None:
        candidates.append(Path(project_root) / path)
    if anchor is not None:
        anchor_path = Path(anchor)
        candidates.append(anchor_path.parent / path)
        candidates.extend(parent / path for parent in anchor_path.parents)
    candidates.append(path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(raw_path)


def _parse_timestamp(raw: Any, *, tz: Any) -> pd.Timestamp | None:
    text = _clean_text(raw)
    if text is None:
        return None
    try:
        ts = pd.Timestamp(text)
    except (TypeError, ValueError):
        return None
    if ts.tzinfo is None:
        return ts.tz_localize(tz)
    return ts.tz_convert(tz)


def _first_present(*values: Any) -> Any:
    for value in values:
        if _is_present(value):
            return value
    return None


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and value.strip().lower() in {"", "none", "null", "not_available"}:
        return False
    try:
        return not bool(pd.isna(value))
    except (TypeError, ValueError):
        return True


def _clean_text(value: Any) -> str | None:
    if not _is_present(value):
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if not _is_present(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> float | None:
    if not _is_present(value):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


def _symbol(value: Any) -> str | None:
    text = _clean_text(value)
    return text.upper() if text else None


def _session_bucket_value(value: Any) -> str | None:
    text = _clean_text(value)
    if text == "unknown":
        return None
    return text


def _dedupe_ints(values: Iterable[int | None]) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        out.append(int(value))
    return out


def _join_sources(*sources: Any) -> str | None:
    out: list[str] = []
    seen: set[str] = set()
    for source in sources:
        text = _clean_text(source)
        if text is None:
            continue
        for item in text.split("+"):
            item = item.strip()
            if item and item not in seen:
                seen.add(item)
                out.append(item)
    return "+".join(out) if out else None


def _merged_quality(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left or {})
    for key, value in (right or {}).items():
        if key == "warnings":
            warnings = list(merged.get("warnings") or [])
            warnings.extend(str(item) for item in value or [])
            merged["warnings"] = _dedupe_strings(warnings)
        elif key == "filled_from":
            current = dict(merged.get("filled_from") or {})
            current.update(value or {})
            merged["filled_from"] = current
        elif key not in merged:
            merged[key] = value
    return merged


def _add_quality_warning(record: CandidateEventRecord, warning: str) -> CandidateEventRecord:
    quality = _merged_quality(record.data_quality, {"warnings": [warning]})
    return replace(record, data_quality=quality)


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _limit_reached(records: Sequence[CandidateEventRecord], max_events: int | None) -> bool:
    return max_events is not None and len(records) >= max(0, int(max_events))


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value
