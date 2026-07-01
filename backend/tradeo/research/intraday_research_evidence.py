from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, time
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "tradeo.intraday_research_evidence.v1"
DEFAULT_OUTPUT_DIR = Path("artifacts/runtime/research_evidence")


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    run_id: int | None
    candidate_key: str | None
    pattern_key: str | None
    cluster_id: int | None
    symbol: str | None
    timeframe: str | None
    window_size: int | None
    forward_bars: int | None
    side: str | None
    window_start_ts: str | None
    window_end_ts: str | None
    entry_ts: str | None
    exit_ts: str | None
    entry_price: float | None
    exit_price: float | None
    forward_return: float | None
    outcome_r: float | None
    split: str | None
    cost_base_r: float | None
    cost_x2_r: float | None
    hour_of_day: int | None
    session_bucket: str
    month: str | None
    source: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvidenceManifest:
    schema_version: str
    run_id: int | None
    output_dir: str
    candidate_count: int
    record_count: int
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["errors"] = list(self.errors)
        return payload


@dataclass(slots=True)
class ResearchEvidenceWriter:
    enabled: bool = False
    output_dir: Path = DEFAULT_OUTPUT_DIR
    max_candidates_per_run: int = 50
    max_samples_per_candidate: int = 300

    def write(
        self,
        *,
        run_id: int | None,
        evidence_by_candidate: dict[str, Iterable[EvidenceRecord | dict[str, Any]]],
    ) -> EvidenceManifest:
        warnings: list[str] = []
        errors: list[str] = []
        if not self.enabled:
            return EvidenceManifest(
                schema_version=SCHEMA_VERSION,
                run_id=run_id,
                output_dir=str(self._run_dir(run_id)),
                candidate_count=0,
                record_count=0,
                warnings=("disabled",),
                errors=(),
            )

        run_dir = self._run_dir(run_id)
        selected = list(evidence_by_candidate.items())[: max(0, int(self.max_candidates_per_run))]
        if len(evidence_by_candidate) > len(selected):
            warnings.append("candidate_limit_applied")

        record_count = 0
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            for candidate_key, raw_records in selected:
                raw_record_list = list(raw_records)
                records = raw_record_list[: max(0, int(self.max_samples_per_candidate))]
                if len(raw_record_list) > len(records):
                    warnings.append(f"sample_limit_applied:{candidate_key}")
                path = run_dir / f"candidate_{_safe_key(candidate_key)}.jsonl"
                with path.open("w", encoding="utf-8") as handle:
                    for raw in records:
                        record = coerce_record(raw, run_id=run_id, candidate_key=candidate_key)
                        handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
                        record_count += 1
        except Exception as exc:  # pragma: no cover - defensive contract
            errors.append(f"{type(exc).__name__}: {exc}")

        manifest = EvidenceManifest(
            schema_version=SCHEMA_VERSION,
            run_id=run_id,
            output_dir=str(run_dir),
            candidate_count=len(selected),
            record_count=record_count,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "manifest.json").write_text(
                json.dumps(manifest.to_dict(), indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:  # pragma: no cover - defensive contract
            errors.append(f"manifest_write_failed:{type(exc).__name__}: {exc}")
        return manifest

    def _run_dir(self, run_id: int | None) -> Path:
        suffix = "unknown" if run_id is None else str(run_id)
        return Path(self.output_dir) / f"run_{suffix}"


def coerce_record(
    raw: EvidenceRecord | dict[str, Any],
    *,
    run_id: int | None = None,
    candidate_key: str | None = None,
) -> EvidenceRecord:
    if isinstance(raw, EvidenceRecord):
        return raw
    data = dict(raw)
    entry_ts = _optional_str(data.get("entry_ts") or data.get("window_end_ts") or data.get("window_end"))
    month = _month(entry_ts)
    hour = _hour(entry_ts)
    bucket = str(data.get("session_bucket") or session_bucket(entry_ts))
    return EvidenceRecord(
        run_id=_optional_int(data.get("run_id"), default=run_id),
        candidate_key=_optional_str(data.get("candidate_key"), default=candidate_key),
        pattern_key=_optional_str(data.get("pattern_key")),
        cluster_id=_optional_int(data.get("cluster_id")),
        symbol=_optional_str(data.get("symbol")),
        timeframe=_optional_str(data.get("timeframe")),
        window_size=_optional_int(data.get("window_size")),
        forward_bars=_optional_int(data.get("forward_bars")),
        side=_optional_str(data.get("side")),
        window_start_ts=_optional_str(data.get("window_start_ts") or data.get("window_start")),
        window_end_ts=_optional_str(data.get("window_end_ts") or data.get("window_end")),
        entry_ts=entry_ts,
        exit_ts=_optional_str(data.get("exit_ts") or data.get("forward_end")),
        entry_price=_optional_float(data.get("entry_price")),
        exit_price=_optional_float(data.get("exit_price")),
        forward_return=_optional_float(data.get("forward_return")),
        outcome_r=_optional_float(data.get("outcome_r")),
        split=_optional_str(data.get("split")),
        cost_base_r=_optional_float(data.get("cost_base_r")),
        cost_x2_r=_optional_float(data.get("cost_x2_r")),
        hour_of_day=hour,
        session_bucket=bucket,
        month=_optional_str(data.get("month"), default=month),
        source=_optional_str(data.get("source")),
    )


def summarize_evidence_directory(path: str | Path) -> dict[str, Any]:
    root = Path(path)
    records = list(_iter_records(root))
    fields = tuple(EvidenceRecord.__dataclass_fields__.keys())
    available = sorted(field for field in fields if any(row.get(field) is not None for row in records))
    missing = sorted(field for field in fields if field not in available)
    warnings: list[str] = []
    if not root.exists():
        warnings.append("evidence_dir_missing")
    if not records:
        warnings.append("no_evidence_records")
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_coverage": {
            "record_count": len(records),
            "candidate_count": len({row.get("candidate_key") for row in records if row.get("candidate_key")}),
            "run_count": len({row.get("run_id") for row in records if row.get("run_id") is not None}),
        },
        "symbol_contribution": _group_summary(records, "symbol"),
        "time_of_day_summary": _group_summary(records, "session_bucket"),
        "month_summary": _group_summary(records, "month"),
        "fields_available": available,
        "fields_missing": missing,
        "warnings": warnings,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    coverage = summary.get("evidence_coverage", {})
    lines = [
        "# Intraday Research Evidence",
        "",
        f"- records: `{coverage.get('record_count', 0)}`",
        f"- candidates: `{coverage.get('candidate_count', 0)}`",
        f"- runs: `{coverage.get('run_count', 0)}`",
        "",
        "## Top Symbols",
    ]
    lines.extend(_summary_lines(summary.get("symbol_contribution", [])))
    lines.extend(["", "## Time Of Day"])
    lines.extend(_summary_lines(summary.get("time_of_day_summary", [])))
    lines.extend(["", "## Months"])
    lines.extend(_summary_lines(summary.get("month_summary", [])))
    if summary.get("warnings"):
        lines.extend(["", "## Warnings"])
        lines.extend(f"- `{warning}`" for warning in summary["warnings"])
    return "\n".join(lines) + "\n"


def session_bucket(value: str | None) -> str:
    parsed = _parse_datetime(value)
    if parsed is None:
        return "unknown"
    current = parsed.time()
    if time(9, 30) <= current < time(11, 0):
        return "open"
    if time(11, 0) <= current < time(15, 0):
        return "mid"
    if time(15, 0) <= current <= time(16, 0):
        return "close"
    return "unknown"


def _iter_records(root: Path) -> Iterable[dict[str, Any]]:
    if root.is_file() and root.suffix == ".jsonl":
        paths = [root]
    else:
        paths = sorted(root.glob("run_*/candidate_*.jsonl")) if root.exists() else []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if text:
                    yield json.loads(text)


def _group_summary(records: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        key = row.get(field)
        grouped[str(key if key is not None else "not_available")].append(row)
    output = []
    for key, rows in grouped.items():
        outcomes = [_optional_float(row.get("outcome_r")) for row in rows]
        returns = [_optional_float(row.get("forward_return")) for row in rows]
        output.append(
            {
                field: key,
                "record_count": len(rows),
                "avg_outcome_r": _avg(value for value in outcomes if value is not None),
                "avg_forward_return": _avg(value for value in returns if value is not None),
                "sources": dict(Counter(str(row.get("source") or "not_available") for row in rows)),
            }
        )
    return sorted(output, key=lambda row: int(row["record_count"]), reverse=True)


def _summary_lines(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["- none"]
    lines = []
    for row in rows[:10]:
        key_name = next((key for key in row if key not in {"record_count", "avg_outcome_r", "avg_forward_return", "sources"}), "key")
        lines.append(
            f"- `{row.get(key_name)}` count=`{row.get('record_count')}` "
            f"avg_r=`{row.get('avg_outcome_r')}` avg_ret=`{row.get('avg_forward_return')}`"
        )
    return lines


def _safe_key(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in str(value))[:160] or "unknown"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _month(value: str | None) -> str | None:
    parsed = _parse_datetime(value)
    return None if parsed is None else f"{parsed.year:04d}-{parsed.month:02d}"


def _hour(value: str | None) -> int | None:
    parsed = _parse_datetime(value)
    return None if parsed is None else int(parsed.hour)


def _optional_str(value: Any, default: str | None = None) -> str | None:
    if value is None:
        return default
    text = str(value)
    return text if text else default


def _optional_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(values: Iterable[float]) -> float | None:
    vals = list(values)
    if not vals:
        return None
    return round(sum(vals) / len(vals), 8)
