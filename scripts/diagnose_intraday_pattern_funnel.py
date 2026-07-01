#!/usr/bin/env python3
"""Diagnose why intraday Research is not producing usable patterns.

Run inside the backend container after recent discovery runs. The script reads
`discovery_runs` and, when available, `discovered_patterns`, then ranks blockers
and near-misses. It is intentionally diagnostic only: it does not change gates or
promote patterns.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from typing import Any, Iterable

from tradeo.core.config import get_settings
from tradeo.db.models import DiscoveredPattern, DiscoveryRun
from tradeo.db.session import SessionLocal


@dataclass(frozen=True, slots=True)
class CandidateView:
    source: str
    run_id: int | None
    pattern_key: str
    name: str
    status: str
    side: str
    timeframe: str
    window_size: int
    sample_count: int
    symbol_count: int
    year_count: int
    score: float
    best_rr: float
    best_expectancy_r: float
    best_profit_factor: float
    stability_score: float
    confirmation_priority_score: float
    confirmation_recommended: bool
    rejection_reasons: list[str]
    inferred_blockers: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=72.0, help="Recent horizon to inspect; 0 disables time filtering.")
    parser.add_argument("--limit-runs", type=int, default=80, help="Maximum discovery runs to inspect.")
    parser.add_argument(
        "--run-ids",
        default="",
        help="Comma-separated DiscoveryRun IDs to diagnose exactly; disables --hours filtering.",
    )
    parser.add_argument(
        "--wave-manifest",
        default="",
        help="Path to an intraday_research_wave_*.json manifest; extracts research_result.details.runs[].run_id.",
    )
    parser.add_argument("--top", type=int, default=20, help="Near-miss candidates to include.")
    parser.add_argument("--json-only", action="store_true", help="Only print machine-readable JSON.")
    args = parser.parse_args()

    report = build_report(
        hours=args.hours,
        limit_runs=args.limit_runs,
        top=args.top,
        run_ids_arg=args.run_ids,
        wave_manifest=args.wave_manifest,
    )
    if args.json_only:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    _print_human(report)
    print("\nJSON:")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build_report(
    *,
    hours: float,
    limit_runs: int,
    top: int,
    run_ids_arg: str = "",
    wave_manifest: str = "",
) -> dict[str, Any]:
    settings = get_settings()
    explicit_run_ids = _resolve_explicit_run_ids(run_ids_arg=run_ids_arg, wave_manifest=wave_manifest)
    scope_mode = "recent"
    if run_ids_arg.strip() and wave_manifest.strip():
        scope_mode = "run_ids+wave_manifest"
    elif run_ids_arg.strip():
        scope_mode = "run_ids"
    elif wave_manifest.strip():
        scope_mode = "wave_manifest"

    cutoff = None
    if not explicit_run_ids and hours and hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=float(hours))

    db = SessionLocal()
    try:
        if explicit_run_ids:
            query = (
                db.query(DiscoveryRun)
                .filter(DiscoveryRun.id.in_(explicit_run_ids))
                .order_by(DiscoveryRun.id.desc())
            )
            runs = list(query.all())
        else:
            query = db.query(DiscoveryRun).order_by(DiscoveryRun.id.desc())
            if cutoff is not None:
                query = query.filter(DiscoveryRun.started_at >= cutoff)
            runs = list(query.limit(max(1, int(limit_runs))).all())
        run_ids = [int(run.id) for run in runs]
        persisted = []
        if run_ids:
            persisted = (
                db.query(DiscoveredPattern)
                .filter(DiscoveredPattern.run_id.in_(run_ids))
                .order_by(DiscoveredPattern.score.desc())
                .all()
            )
    finally:
        db.close()

    summary_candidates = [
        candidate
        for run in runs
        for candidate in _summary_candidates(run, settings=settings)
    ]
    persisted_candidates = [_persisted_candidate(pattern, settings=settings) for pattern in persisted]
    all_candidates = _dedupe_candidates(persisted_candidates + summary_candidates)

    run_totals = {
        "runs": len(runs),
        "completed": sum(1 for run in runs if str(run.status) == "completed"),
        "failed": sum(1 for run in runs if str(run.status) == "failed"),
        "running": sum(1 for run in runs if str(run.status) == "running"),
        "windows": sum(int(run.windows_sampled or 0) for run in runs),
        "clusters": sum(int(run.clusters_evaluated or 0) for run in runs),
        "accepted_patterns": sum(int(run.accepted_patterns or 0) for run in runs),
        "rejected_patterns": sum(int(run.rejected_patterns or 0) for run in runs),
        "duration_s": round(sum(float(run.duration_seconds or 0.0) for run in runs), 3),
    }
    status_counts = Counter(candidate.status for candidate in all_candidates)
    blocker_counts = Counter(
        blocker for candidate in all_candidates for blocker in candidate.inferred_blockers
    )
    exact_reasons = Counter(
        reason for candidate in persisted_candidates for reason in candidate.rejection_reasons
    )
    near_misses = sorted(all_candidates, key=_near_miss_rank, reverse=True)[: max(1, int(top))]

    diagnostic_flags = _diagnostic_flags(
        run_totals=run_totals,
        persisted_candidates=persisted_candidates,
        summary_candidates=summary_candidates,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "mode": scope_mode,
            "hours": hours if not explicit_run_ids else None,
            "limit_runs": limit_runs if not explicit_run_ids else None,
            "requested_run_ids": explicit_run_ids,
            "missing_run_ids": sorted(set(explicit_run_ids) - set(run_ids)),
            "wave_manifest": wave_manifest or None,
            "run_ids": run_ids,
        },
        "run_totals": run_totals,
        "candidate_visibility": {
            "persisted_candidates": len(persisted_candidates),
            "summary_candidates": len(summary_candidates),
            "all_candidates_deduped": len(all_candidates),
            "store_rejected_likely_disabled": bool(
                run_totals["clusters"] > 0
                and len(persisted_candidates) < max(1, run_totals["rejected_patterns"])
            ),
        },
        "status_counts": dict(status_counts.most_common()),
        "inferred_blockers": dict(blocker_counts.most_common(20)),
        "exact_rejection_reasons_from_persisted_rows": dict(exact_reasons.most_common(20)),
        "near_misses": [asdict(candidate) for candidate in near_misses],
        "recommended_actions": _recommended_actions(blocker_counts, diagnostic_flags),
        "diagnostic_flags": diagnostic_flags,
    }


def _resolve_explicit_run_ids(*, run_ids_arg: str, wave_manifest: str) -> list[int]:
    run_ids: list[int] = []
    run_ids.extend(_parse_run_ids(run_ids_arg))
    if wave_manifest.strip():
        run_ids.extend(_run_ids_from_wave_manifest(wave_manifest.strip()))
    return _dedupe_ints(run_ids)


def _parse_run_ids(value: str) -> list[int]:
    if not value.strip():
        return []
    run_ids: list[int] = []
    for item in value.replace(";", ",").split(","):
        text = item.strip()
        if not text:
            continue
        try:
            run_id = int(text)
        except ValueError as exc:
            raise SystemExit(f"Invalid --run-ids value {text!r}; expected comma-separated integers.") from exc
        if run_id <= 0:
            raise SystemExit(f"Invalid --run-ids value {text!r}; IDs must be positive integers.")
        run_ids.append(run_id)
    return run_ids


def _run_ids_from_wave_manifest(path: str) -> list[int]:
    try:
        with open(path, encoding="utf-8") as handle:
            manifest = json.load(handle)
    except OSError as exc:
        raise SystemExit(f"Could not read --wave-manifest {path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Could not parse --wave-manifest {path!r} as JSON: {exc}") from exc

    runs = (
        manifest.get("research_result", {})
        .get("details", {})
        .get("runs", [])
    )
    if not isinstance(runs, list):
        raise SystemExit(f"Invalid --wave-manifest {path!r}: research_result.details.runs is not a list.")

    run_ids: list[int] = []
    for row in runs:
        if not isinstance(row, dict):
            continue
        run_id = _to_int(row.get("run_id"))
        if run_id > 0:
            run_ids.append(run_id)
    if not run_ids:
        raise SystemExit(f"Invalid --wave-manifest {path!r}: no run IDs found in research_result.details.runs.")
    return run_ids


def _dedupe_ints(values: Iterable[int]) -> list[int]:
    output: list[int] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _summary_candidates(run: DiscoveryRun, *, settings: Any) -> list[CandidateView]:
    summary = run.summary_json if isinstance(run.summary_json, dict) else {}
    candidates: list[CandidateView] = []
    for section in ("top_patterns", "confirmation_queue"):
        rows = summary.get(section) or []
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                candidates.append(_candidate_from_mapping(row, source=f"summary.{section}", run_id=run.id, settings=settings))
    return candidates


def _persisted_candidate(pattern: DiscoveredPattern, *, settings: Any) -> CandidateView:
    metrics = pattern.metrics_json if isinstance(pattern.metrics_json, dict) else {}
    rejection_reasons = list(pattern.rejection_reasons_json or pattern.validation_reasons_json or [])
    return _candidate_from_mapping(
        {
            **metrics,
            "pattern_key": pattern.pattern_key,
            "name": pattern.name,
            "status": pattern.promotion_status or str(pattern.status.value),
            "side": pattern.side,
            "timeframe": pattern.timeframe,
            "window_size": pattern.window_size,
            "sample_count": pattern.sample_count,
            "symbol_count": pattern.symbol_count,
            "year_count": pattern.year_count,
            "score": pattern.score,
            "best_rr": pattern.best_rr,
            "best_expectancy_r": pattern.best_expectancy_r,
            "best_profit_factor": pattern.best_profit_factor,
            "stability_score": pattern.stability_score,
            "confirmation_priority_score": pattern.confirmation_priority_score,
            "confirmation_recommended": bool(pattern.confirmation_status == "needs_confirmation"),
            "rejection_reasons": rejection_reasons,
        },
        source="persisted.discovered_patterns",
        run_id=pattern.run_id,
        settings=settings,
    )


def _candidate_from_mapping(
    row: dict[str, Any], *, source: str, run_id: int | None, settings: Any
) -> CandidateView:
    rejection_reasons = [str(item) for item in row.get("rejection_reasons") or row.get("validation_rejections") or []]
    candidate = CandidateView(
        source=source,
        run_id=int(run_id) if run_id is not None else None,
        pattern_key=str(row.get("pattern_key") or ""),
        name=str(row.get("name") or ""),
        status=str(row.get("status") or row.get("promotion_status") or "unknown"),
        side=str(row.get("side") or ""),
        timeframe=str(row.get("timeframe") or ""),
        window_size=_to_int(row.get("window_size")),
        sample_count=_to_int(row.get("sample_count")),
        symbol_count=_to_int(row.get("symbol_count")),
        year_count=_to_int(row.get("year_count")),
        score=_to_float(row.get("score") or row.get("lab_priority_score")),
        best_rr=_to_float(row.get("best_rr")),
        best_expectancy_r=_to_float(row.get("best_expectancy_r") or row.get("expectancy_r")),
        best_profit_factor=_to_float(row.get("best_profit_factor") or row.get("profit_factor")),
        stability_score=_to_float(row.get("stability_score")),
        confirmation_priority_score=_to_float(row.get("confirmation_priority_score")),
        confirmation_recommended=bool(row.get("confirmation_recommended")),
        rejection_reasons=rejection_reasons,
        inferred_blockers=[],
    )
    blockers = _infer_blockers(row, candidate, settings=settings)
    return CandidateView(**{**asdict(candidate), "inferred_blockers": blockers})


def _infer_blockers(row: dict[str, Any], candidate: CandidateView, *, settings: Any) -> list[str]:
    blockers: list[str] = []
    is_intraday = candidate.timeframe.strip().lower() not in {"", "1d", "daily", "1day", "1 day"}
    min_samples = settings.intraday_research_min_samples if is_intraday else settings.discovery_min_samples
    min_effective = (
        settings.intraday_research_min_effective_samples
        if is_intraday
        else settings.discovery_min_effective_samples
    )
    min_symbols = settings.intraday_research_min_symbols if is_intraday else settings.discovery_min_symbols
    min_years = settings.intraday_research_min_years if is_intraday else settings.discovery_min_years

    if candidate.status not in {"lab", "lab_watchlist", "lab_candidate", "needs_confirmation"}:
        blockers.append("not_non_rejected")
    if candidate.confirmation_recommended:
        blockers.append("needs_confirmation")
    if candidate.sample_count < min_samples:
        blockers.append("sample_limited")
    effective = _to_float(row.get("effective_sample_count"))
    if effective and effective < float(min_effective):
        blockers.append("effective_sample_limited")
    if candidate.symbol_count < int(min_symbols):
        blockers.append("symbol_diversity_limited")
    if candidate.year_count < int(min_years):
        blockers.append("temporal_diversity_limited")
    if row.get("fdr_passed") is False:
        blockers.append("fdr_failed")
    adjusted_p = _to_optional_float(row.get("adjusted_p_value"))
    if adjusted_p is not None and adjusted_p > float(settings.discovery_max_adjusted_p_value):
        blockers.append("adjusted_p_failed")
    for key, bucket in (("wrc_p_value", "wrc_failed"), ("spa_p_value", "spa_failed")):
        value = _to_optional_float(row.get(key))
        if value is not None and value > float(settings.discovery_max_adjusted_p_value):
            blockers.append(bucket)
    if candidate.best_expectancy_r <= 0:
        blockers.append("no_positive_expectancy")
    if candidate.best_profit_factor <= 1:
        blockers.append("no_positive_profit_factor")
    if candidate.best_expectancy_r < float(settings.discovery_min_expectancy_r):
        blockers.append("expectancy_below_quality_bar")
    if candidate.best_profit_factor < float(settings.discovery_min_profit_factor):
        blockers.append("profit_factor_below_quality_bar")
    if candidate.stability_score < float(settings.discovery_min_stability_score):
        blockers.append("stability_failed")
    if row.get("cost_stress_passed") is False:
        blockers.append("cost_stress_failed")
    if row.get("edge_decay_passed") is False:
        blockers.append("edge_decay_failed")
    if _to_float(row.get("out_of_sample_expectancy_r")) <= 0:
        blockers.append("oos_expectancy_not_positive")
    if _to_float(row.get("out_of_sample_profit_factor")) < 1.2:
        blockers.append("oos_profit_factor_weak")
    if bool(row.get("survivorship_cap_applied")):
        blockers.append("survivorship_cap")
    return _dedupe(blockers)


def _near_miss_rank(candidate: CandidateView) -> tuple[float, float, float, int, int]:
    status_bonus = {
        "lab_candidate": 5.0,
        "lab_watchlist": 4.0,
        "needs_confirmation": 3.5,
        "lab": 3.0,
        "rejected": 0.0,
    }.get(candidate.status, 0.0)
    blocker_penalty = 0.15 * len(candidate.inferred_blockers)
    score = (
        status_bonus
        + max(0.0, candidate.confirmation_priority_score) * 2.0
        + max(0.0, candidate.best_expectancy_r) * 1.5
        + min(max(candidate.best_profit_factor, 0.0), 4.0) * 0.4
        + max(0.0, candidate.stability_score) * 0.6
        + min(candidate.sample_count / 100.0, 2.0) * 0.25
        - blocker_penalty
    )
    return (round(score, 6), candidate.best_expectancy_r, candidate.best_profit_factor, candidate.sample_count, candidate.symbol_count)


def _diagnostic_flags(
    *,
    run_totals: dict[str, Any],
    persisted_candidates: list[CandidateView],
    summary_candidates: list[CandidateView],
) -> list[str]:
    flags: list[str] = []
    if run_totals["runs"] == 0:
        flags.append("no_recent_discovery_runs")
    if run_totals["clusters"] == 0 and run_totals["windows"] > 0:
        flags.append("windows_but_zero_clusters")
    if run_totals["clusters"] > 0 and not persisted_candidates:
        flags.append("clusters_without_persisted_candidates")
    if not persisted_candidates and summary_candidates:
        flags.append("use_summary_candidates_or_run_scouting_store_rejected")
    if run_totals["accepted_patterns"] == 0 and run_totals["clusters"] > 0:
        flags.append("validation_gate_blocking_all_candidates")
    return flags


def _recommended_actions(blockers: Counter[str], flags: list[str]) -> list[str]:
    actions: list[str] = []
    if "clusters_without_persisted_candidates" in flags:
        actions.append(
            "Run one diagnostic scouting pass with rejected persistence enabled so near-misses and exact rejection reasons are visible."
        )
    if blockers["sample_limited"] or blockers["effective_sample_limited"]:
        actions.append(
            "Increase historical period and max windows before relaxing gates; target the same promising pattern keys for confirmation."
        )
    if blockers["symbol_diversity_limited"]:
        actions.append("Expand intraday universe/limit for deep scouting; 25 symbols may be too narrow for robust clusters.")
    if blockers["fdr_failed"] or blockers["adjusted_p_failed"] or blockers["wrc_failed"] or blockers["spa_failed"]:
        actions.append(
            "Do not lower FDR/WRC/SPA. Reduce hypothesis noise by isolating timeframes/window sizes or add more data per family."
        )
    if blockers["cost_stress_failed"] or blockers["edge_decay_failed"]:
        actions.append("Keep the candidate in lab only and search for entry filters that improve cost/decay robustness.")
    if blockers["no_positive_expectancy"] or blockers["no_positive_profit_factor"]:
        actions.append("Change search space: add/alter timeframes, windows, forward bars or universe; more speed alone will not create edge.")
    if not actions:
        actions.append("No dominant blocker found; inspect near_misses and run a store-rejected scouting benchmark.")
    return actions


def _dedupe_candidates(candidates: Iterable[CandidateView]) -> list[CandidateView]:
    seen: set[tuple[str, int | None, str, str]] = set()
    output: list[CandidateView] = []
    for candidate in candidates:
        key = (candidate.pattern_key, candidate.run_id, candidate.status, candidate.source)
        if key in seen:
            continue
        seen.add(key)
        output.append(candidate)
    return output


def _dedupe(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    parsed = _to_optional_float(value)
    return 0.0 if parsed is None else parsed


def _to_optional_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _print_human(report: dict[str, Any]) -> None:
    totals = report["run_totals"]
    print("Intraday pattern funnel")
    print("=======================")
    print(
        f"Runs={totals['runs']} completed={totals['completed']} windows={totals['windows']} "
        f"clusters={totals['clusters']} accepted={totals['accepted_patterns']} rejected={totals['rejected_patterns']}"
    )
    print(f"Candidate visibility: {report['candidate_visibility']}")
    print("\nDominant inferred blockers:")
    for name, count in list(report["inferred_blockers"].items())[:10]:
        print(f"- {name}: {count}")
    print("\nRecommended actions:")
    for action in report["recommended_actions"]:
        print(f"- {action}")
    print("\nTop near-misses:")
    for candidate in report["near_misses"][:10]:
        print(
            f"- run={candidate['run_id']} status={candidate['status']} tf={candidate['timeframe']} "
            f"score={candidate['score']:.3f} exp={candidate['best_expectancy_r']:.3f} "
            f"pf={candidate['best_profit_factor']:.3f} samples={candidate['sample_count']} "
            f"symbols={candidate['symbol_count']} blockers={','.join(candidate['inferred_blockers'][:4])}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
