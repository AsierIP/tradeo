from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, time
import json
from pathlib import Path
import re
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo

from tradeo.db.models import DiscoveredPattern, DiscoveredPatternExample, DiscoveryRun
from tradeo.research.determinism import CONTENT_HASH_ALGO, content_hash
from tradeo.research.intraday_research_forensics import resolve_run_ids as _resolve_run_ids

NOT_AVAILABLE = "not_available"
SCHEMA_VERSION = "tradeo.intraday_research_evidence.v1"
ALLOWED_TERMINAL_RECOMMENDATIONS = frozenset(
    {
        "continue_research",
        "change_search_space",
        "candidate_for_shadow_review",
        "research_closed_no_candidate",
        "insufficient_evidence",
    }
)
_NY_TZ = ZoneInfo("America/New_York")


def resolve_run_ids(*, wave_manifests: Sequence[str], run_ids: Sequence[str]) -> list[int]:
    return _resolve_run_ids(wave_manifests=wave_manifests, run_ids=run_ids)


@dataclass(frozen=True, slots=True)
class EvidenceSample:
    run_id: int | None
    candidate_key: str
    pattern_key: str
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
    split: str
    cost_base_r: float | None
    cost_x2_r: float | None
    hour_of_day: int | None
    session_bucket: str
    month: str | None
    source: str
    rejection_reasons: list[str]
    data_availability: dict[str, str]
    timestamp_timezone_assumption: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_evidence_report(
    *,
    db: Any,
    wave_manifests: Sequence[str] = (),
    run_ids: Sequence[int] = (),
    top_candidates: int = 25,
    max_candidates: int = 25,
    max_samples_per_candidate: int = 500,
    max_total_samples: int = 10_000,
    artifact_root: str | Path | None = None,
) -> dict[str, Any]:
    exact_run_ids = _dedupe_ints(run_ids)
    if not exact_run_ids:
        raise ValueError("Research evidence requires exact --wave-manifest or --run-ids scope")
    limits = _limits(
        top_candidates=top_candidates,
        max_candidates=max_candidates,
        max_samples_per_candidate=max_samples_per_candidate,
        max_total_samples=max_total_samples,
    )
    runs = list(
        db.query(DiscoveryRun)
        .filter(DiscoveryRun.id.in_(exact_run_ids))
        .order_by(DiscoveryRun.id.asc())
        .all()
    )
    found_run_ids = [int(run.id) for run in runs]
    patterns = _load_patterns(db, found_run_ids, limit=limits["candidate_limit"])
    samples_by_candidate: dict[str, list[dict[str, Any]]] = {}
    candidate_manifests: list[dict[str, Any]] = []
    total_samples = 0
    truncated = False

    for pattern in patterns:
        remaining = max(0, limits["max_total_samples"] - total_samples)
        if remaining <= 0:
            truncated = True
            break
        sample_limit = min(limits["max_samples_per_candidate"], remaining)
        examples = _load_examples(db, int(pattern.id), limit=sample_limit + 1)
        candidate_truncated = False
        if len(examples) > sample_limit:
            truncated = True
            candidate_truncated = True
            examples = examples[:sample_limit]
        samples = [sample.to_dict() for sample in evidence_samples_for_pattern(pattern, examples)]
        total_samples += len(samples)
        candidate_key = safe_candidate_key(pattern.pattern_key or pattern.name or str(pattern.id))
        samples_by_candidate[candidate_key] = samples
        candidate_manifests.append(
            _candidate_manifest(
                pattern=pattern,
                candidate_key=candidate_key,
                sample_count=len(samples),
                truncated=candidate_truncated,
            )
        )

    missing_fields_summary = missing_fields(samples_by_candidate.values())
    summary = summarize_evidence(
        runs=runs,
        candidates=candidate_manifests,
        samples_by_candidate=samples_by_candidate,
        missing_fields_summary=missing_fields_summary,
        requested_run_ids=exact_run_ids,
        wave_manifests=wave_manifests,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": {
            "exact_scope": True,
            "wave_manifests": list(wave_manifests),
            "requested_run_ids": exact_run_ids,
            "run_ids": found_run_ids,
            "missing_run_ids": sorted(set(exact_run_ids) - set(found_run_ids)),
        },
        "limits": limits,
        "runs": [_run_manifest(run) for run in runs],
        "candidate_count": len(candidate_manifests),
        "sample_count": total_samples,
        "truncated": truncated,
        "missing_fields_summary": missing_fields_summary,
        "candidate_manifests": candidate_manifests,
        "samples_by_candidate": samples_by_candidate,
        "summary": summary,
        "safety": safety_manifest(),
    }
    report["determinism"] = {"algo": CONTENT_HASH_ALGO, "content_hash": content_hash(report)}
    if artifact_root is not None:
        report["artifacts"] = write_evidence_artifacts(report, artifact_root)
    return report


def evidence_samples_for_pattern(
    pattern: DiscoveredPattern, examples: Iterable[DiscoveredPatternExample]
) -> list[EvidenceSample]:
    return [_sample_from_example(pattern, example) for example in examples]


def summarize_evidence(
    *,
    runs: Sequence[DiscoveryRun],
    candidates: Sequence[dict[str, Any]],
    samples_by_candidate: dict[str, list[dict[str, Any]]],
    missing_fields_summary: dict[str, int],
    requested_run_ids: Sequence[int],
    wave_manifests: Sequence[str],
) -> dict[str, Any]:
    samples = [sample for rows in samples_by_candidate.values() for sample in rows]
    outcome_samples = [sample for sample in samples if sample.get("outcome_r") is not None]
    result = {
        "runs_included": [int(run.id) for run in runs],
        "requested_run_ids": list(requested_run_ids),
        "wave_manifests": list(wave_manifests),
        "candidates_included": len(candidates),
        "samples_included": len(samples),
        "missing_fields": missing_fields_summary,
        "by_symbol": _group_stats(samples, "symbol"),
        "by_session": _group_stats(samples, "session_bucket"),
        "by_month": _group_stats(samples, "month"),
        "by_split": _group_stats(samples, "split"),
        "top_concentration": _top_concentration(outcome_samples),
        "candidate_quality_flags": candidate_quality_flags(candidates, samples, missing_fields_summary),
        "terminal_research_recommendation": terminal_research_recommendation(
            runs=runs,
            candidates=candidates,
            samples=samples,
            missing_fields_summary=missing_fields_summary,
        ),
    }
    result["terminal_research_recommendation_allowed"] = (
        result["terminal_research_recommendation"] in ALLOWED_TERMINAL_RECOMMENDATIONS
    )
    return result


def write_evidence_artifacts(report: dict[str, Any], artifact_root: str | Path) -> dict[str, Any]:
    root = Path(artifact_root)
    root.mkdir(parents=True, exist_ok=True)
    written: dict[str, Any] = {"runs": {}, "summary_json": str(root / "_summary.json"), "summary_md": str(root / "_summary.md")}
    summary_payload = {key: value for key, value in report.items() if key != "samples_by_candidate"}
    (root / "_summary.json").write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    (root / "_summary.md").write_text(render_markdown(summary_payload), encoding="utf-8")
    candidate_lookup = {item["candidate_key"]: item for item in report["candidate_manifests"]}
    for candidate_key, samples in report["samples_by_candidate"].items():
        candidate = candidate_lookup[candidate_key]
        run_id = candidate.get("run_id") or "unknown"
        run_dir = root / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = run_dir / "manifest.json"
        jsonl_path = run_dir / f"candidate_{candidate_key}.jsonl"
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": report["generated_at"],
            "run_id": candidate.get("run_id"),
            "candidate_count": 1,
            "sample_count": len(samples),
            "truncated": report["truncated"] or candidate.get("truncated", False),
            "missing_fields_summary": missing_fields([samples]),
            "safety": safety_manifest(),
            "determinism": {"algo": CONTENT_HASH_ALGO, "content_hash": content_hash(samples)},
            "candidate": candidate,
            "jsonl_path": str(jsonl_path),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for sample in samples:
                handle.write(json.dumps(sample, sort_keys=True, default=str) + "\n")
        written["runs"].setdefault(str(run_id), []).append(
            {"manifest": str(manifest_path), "jsonl": str(jsonl_path), "sample_count": len(samples)}
        )
    return written


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Intraday Research Evidence",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Scope",
        f"- exact_scope: `{report['scope']['exact_scope']}`",
        f"- run_ids: `{', '.join(str(item) for item in report['scope']['run_ids'])}`",
        f"- wave_manifests: `{', '.join(report['scope']['wave_manifests']) or NOT_AVAILABLE}`",
        "",
        "## Counts",
        f"- candidates: `{report['candidate_count']}`",
        f"- samples: `{report['sample_count']}`",
        f"- truncated: `{report['truncated']}`",
        "",
        "## Terminal Recommendation",
        f"- `{summary['terminal_research_recommendation']}`",
        "",
        "## Candidate Quality Flags",
    ]
    lines.extend(f"- {item}" for item in summary["candidate_quality_flags"])
    lines.extend(["", "## Group Stats"])
    for key in ("by_symbol", "by_session", "by_month", "by_split"):
        lines.append(f"### {key}")
        for label, stats in list(summary[key].items())[:12]:
            lines.append(
                f"- {label}: n=`{stats['n']}` outcome_mean_r=`{stats['outcome_mean_r']}` "
                f"positive_rate=`{stats['positive_rate']}`"
            )
    lines.extend(["", "## Safety"])
    for key, value in report["safety"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def safe_candidate_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return (text or "candidate")[:120]


def derive_time_features(raw_ts: Any) -> dict[str, Any]:
    parsed = _parse_datetime(raw_ts)
    if parsed is None:
        return {
            "hour_of_day": None,
            "session_bucket": "unknown",
            "month": None,
            "timestamp_timezone_assumption": None,
        }
    assumption = None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_NY_TZ)
        assumption = "naive_timestamp_assumed_america_new_york"
    local = parsed.astimezone(_NY_TZ)
    return {
        "hour_of_day": local.hour,
        "session_bucket": session_bucket(local.timetz().replace(tzinfo=None)),
        "month": f"{local.year:04d}-{local.month:02d}",
        "timestamp_timezone_assumption": assumption,
    }


def session_bucket(value: time) -> str:
    if time(9, 30) <= value < time(10, 30):
        return "open"
    if time(10, 30) <= value < time(15, 0):
        return "mid"
    if time(15, 0) <= value <= time(16, 0):
        return "close"
    return "unknown"


def candidate_quality_flags(
    candidates: Sequence[dict[str, Any]], samples: Sequence[dict[str, Any]], missing: dict[str, int]
) -> list[str]:
    flags: list[str] = []
    if not candidates:
        flags.append("no_candidates")
    if not samples:
        flags.append("no_event_level_samples")
    if missing:
        flags.append("missing_event_fields")
    if any(candidate.get("sample_count", 0) < 100 for candidate in candidates):
        flags.append("candidate_sample_count_below_100")
    if any(candidate.get("validation_passed") for candidate in candidates):
        flags.append("validation_passed_candidate_present")
    if not flags:
        flags.append("evidence_complete_for_available_schema")
    return flags


def terminal_research_recommendation(
    *,
    runs: Sequence[DiscoveryRun],
    candidates: Sequence[dict[str, Any]],
    samples: Sequence[dict[str, Any]],
    missing_fields_summary: dict[str, int],
) -> str:
    if not runs:
        return "insufficient_evidence"
    if not candidates:
        completed = all(str(run.status) == "completed" for run in runs)
        clusters = sum(int(run.clusters_evaluated or 0) for run in runs)
        return "research_closed_no_candidate" if completed and clusters > 0 else "insufficient_evidence"
    if any(candidate.get("validation_passed") and int(candidate.get("sample_count") or 0) >= 100 for candidate in candidates):
        return "candidate_for_shadow_review"
    if not samples or missing_fields_summary.get("outcome_r", 0) == len(samples):
        return "insufficient_evidence"
    if any(candidate.get("rejection_reasons") for candidate in candidates):
        return "change_search_space"
    return "continue_research"


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


def missing_fields(sample_groups: Iterable[Sequence[dict[str, Any]]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for samples in sample_groups:
        for sample in samples:
            for key, value in sample.items():
                if key in {"data_availability", "timestamp_timezone_assumption"}:
                    continue
                if value is None or value == NOT_AVAILABLE:
                    counts[key] += 1
    return dict(sorted(counts.items()))


def _sample_from_example(pattern: DiscoveredPattern, example: DiscoveredPatternExample) -> EvidenceSample:
    features = example.features_json if isinstance(example.features_json, dict) else {}
    chart = example.chart_json if isinstance(example.chart_json, dict) else {}
    metrics = pattern.metrics_json if isinstance(pattern.metrics_json, dict) else {}
    window_end = _first_present(example.window_end, features.get("window_end_ts"), features.get("window_end"))
    entry_ts = _first_present(features.get("entry_ts"), window_end)
    exit_ts = _first_present(features.get("exit_ts"), example.forward_end, features.get("forward_end"))
    time_features = derive_time_features(entry_ts or window_end)
    exit_price = _optional_float(_first_present(features.get("exit_price"), chart.get("exit_price")))
    forward_return = _coalesce_float(
        features.get("forward_return"),
        chart.get("forward_return"),
        _return_from_prices(example.entry_price, exit_price),
    )
    forward_bars = _optional_int(_first_present(features.get("forward_bars"), metrics.get("forward_bars")))
    split = str(_first_present(features.get("split"), chart.get("split"), NOT_AVAILABLE) or NOT_AVAILABLE)
    source = str(_first_present(features.get("source"), chart.get("source"), "discovered_pattern_examples"))
    values = {
        "symbol": example.symbol or None,
        "window_start_ts": example.window_start or None,
        "window_end_ts": window_end or None,
        "entry_ts": entry_ts or None,
        "exit_ts": exit_ts or None,
        "exit_price": exit_price,
        "forward_return": forward_return,
        "forward_bars": forward_bars,
        "split": None if split == NOT_AVAILABLE else split,
    }
    return EvidenceSample(
        run_id=_optional_int(pattern.run_id),
        candidate_key=safe_candidate_key(pattern.pattern_key or pattern.name or pattern.id),
        pattern_key=str(pattern.pattern_key or ""),
        cluster_id=_optional_int(pattern.cluster_id),
        symbol=str(example.symbol or "").upper() or None,
        timeframe=str(example.timeframe or pattern.timeframe or "") or None,
        window_size=_optional_int(pattern.window_size),
        forward_bars=forward_bars,
        side=str(pattern.side or "") or None,
        window_start_ts=example.window_start or None,
        window_end_ts=str(window_end) if window_end else None,
        entry_ts=str(entry_ts) if entry_ts else None,
        exit_ts=str(exit_ts) if exit_ts else None,
        entry_price=_optional_float(example.entry_price),
        exit_price=exit_price,
        forward_return=forward_return,
        outcome_r=_optional_float(example.outcome_r),
        split=split,
        cost_base_r=_coalesce_float(features.get("cost_base_r"), metrics.get("cost_base_r")),
        cost_x2_r=_coalesce_float(features.get("cost_x2_r"), metrics.get("cost_x2_r")),
        hour_of_day=time_features["hour_of_day"],
        session_bucket=time_features["session_bucket"],
        month=time_features["month"],
        source=source,
        rejection_reasons=_reasons(pattern),
        data_availability={key: _availability(value) for key, value in values.items()},
        timestamp_timezone_assumption=time_features["timestamp_timezone_assumption"],
    )


def _load_patterns(db: Any, run_ids: Sequence[int], *, limit: int) -> list[DiscoveredPattern]:
    if not run_ids:
        return []
    return list(
        db.query(DiscoveredPattern)
        .filter(DiscoveredPattern.run_id.in_(run_ids))
        .order_by(DiscoveredPattern.score.desc(), DiscoveredPattern.id.asc())
        .limit(max(1, int(limit)))
        .all()
    )


def _load_examples(db: Any, pattern_id: int, *, limit: int) -> list[DiscoveredPatternExample]:
    return list(
        db.query(DiscoveredPatternExample)
        .filter(DiscoveredPatternExample.pattern_id == pattern_id)
        .order_by(DiscoveredPatternExample.id.asc())
        .limit(max(1, int(limit)))
        .all()
    )


def _candidate_manifest(
    *, pattern: DiscoveredPattern, candidate_key: str, sample_count: int, truncated: bool
) -> dict[str, Any]:
    return {
        "candidate_key": candidate_key,
        "pattern_key": str(pattern.pattern_key or ""),
        "run_id": _optional_int(pattern.run_id),
        "status": str(getattr(pattern.status, "value", pattern.status)),
        "cluster_id": _optional_int(pattern.cluster_id),
        "side": str(pattern.side or "") or None,
        "timeframe": str(pattern.timeframe or "") or None,
        "window_size": _optional_int(pattern.window_size),
        "score": _optional_float(pattern.score),
        "expectancy_r": _optional_float(pattern.expectancy_r),
        "profit_factor": _optional_float(pattern.profit_factor),
        "sample_count": int(pattern.sample_count or sample_count or 0),
        "symbol_count": int(pattern.symbol_count or 0),
        "validation_passed": bool(pattern.validation_passed),
        "rejection_reasons": _reasons(pattern),
        "exported_sample_count": sample_count,
        "truncated": truncated,
    }


def _run_manifest(run: DiscoveryRun) -> dict[str, Any]:
    return {
        "run_id": int(run.id),
        "status": str(run.status),
        "started_at": _iso(run.started_at),
        "finished_at": _iso(run.finished_at),
        "symbols_scanned": int(run.symbols_scanned or 0),
        "windows_sampled": int(run.windows_sampled or 0),
        "clusters_evaluated": int(run.clusters_evaluated or 0),
        "accepted_patterns": int(run.accepted_patterns or 0),
        "rejected_patterns": int(run.rejected_patterns or 0),
    }


def _group_stats(samples: Sequence[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in samples:
        grouped[str(sample.get(key) or NOT_AVAILABLE)].append(sample)
    return {label: _stats(rows) for label, rows in sorted(grouped.items())}


def _stats(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    outcomes = [_optional_float(sample.get("outcome_r")) for sample in samples]
    outcomes = [value for value in outcomes if value is not None]
    return {
        "n": len(samples),
        "outcome_n": len(outcomes),
        "outcome_mean_r": round(sum(outcomes) / len(outcomes), 6) if outcomes else None,
        "positive_rate": round(sum(1 for value in outcomes if value > 0) / len(outcomes), 6) if outcomes else None,
    }


def _top_concentration(samples: Sequence[dict[str, Any]]) -> dict[str, Any]:
    total = len(samples)
    if not total:
        return {"total_outcome_samples": 0, "by_symbol": {}}
    counts = Counter(str(sample.get("symbol") or NOT_AVAILABLE) for sample in samples)
    return {
        "total_outcome_samples": total,
        "by_symbol": {
            symbol: {"n": count, "pct": round(count / total, 6)} for symbol, count in counts.most_common(10)
        },
    }


def _limits(
    *, top_candidates: int, max_candidates: int, max_samples_per_candidate: int, max_total_samples: int
) -> dict[str, int]:
    return {
        "top_candidates": max(1, int(top_candidates)),
        "max_candidates": max(1, int(max_candidates)),
        "candidate_limit": min(max(1, int(top_candidates)), max(1, int(max_candidates))),
        "max_samples_per_candidate": max(1, int(max_samples_per_candidate)),
        "max_total_samples": max(1, int(max_total_samples)),
    }


def _reasons(pattern: DiscoveredPattern) -> list[str]:
    reasons = pattern.rejection_reasons_json or pattern.validation_reasons_json or []
    return [str(reason) for reason in reasons if str(reason)]


def _availability(value: Any) -> str:
    return "available" if value is not None and value != "" else NOT_AVAILABLE


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if value is None or value == "":
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _return_from_prices(entry_price: Any, exit_price: Any) -> float | None:
    entry = _optional_float(entry_price)
    exit_value = _optional_float(exit_price)
    if entry is None or exit_value is None or entry == 0:
        return None
    return round((exit_value - entry) / entry, 10)


def _coalesce_float(*values: Any) -> float | None:
    for value in values:
        parsed = _optional_float(value)
        if parsed is not None:
            return parsed
    return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _dedupe_ints(values: Iterable[int]) -> list[int]:
    output: list[int] = []
    for raw in values:
        value = int(raw)
        if value not in output:
            output.append(value)
    return output
