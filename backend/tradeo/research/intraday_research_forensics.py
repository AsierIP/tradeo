from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from tradeo.db.models import (
    DiscoveredPattern,
    DiscoveredPatternExample,
    DiscoveredPatternMatch,
    DiscoveredPatternMetric,
    DiscoveryRun,
)
from tradeo.research.determinism import CONTENT_HASH_ALGO, content_hash

NOT_AVAILABLE = "not_available"

PROHIBITED_REPEATS = (
    "30m W20 4,8,13",
    "30m W50 4,8,13",
    "30m W50 8,13,21",
    "1h W20 2,4,6",
    "1h W50 2,4,6",
)


@dataclass(frozen=True, slots=True)
class CandidateForensics:
    pattern_key: str
    name: str
    run_id: int | None
    side: str
    timeframe: str | None
    window_size: int | None
    expectancy_r: float | None
    profit_factor: float | None
    oos_expectancy_r: float | None
    oos_profit_factor: float | None
    symbol_count: int
    sample_count: int
    drawdown_r: float | None
    cost_x2_result: str
    fdr_result: str
    wrc_result: str
    spa_result: str
    market_replay: str
    placebo_adversarial: str
    dominant_failure_class: str
    failure_taxonomy: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    data_granularity: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["failure_taxonomy"] = list(self.failure_taxonomy)
        payload["rejection_reasons"] = list(self.rejection_reasons)
        return payload


def resolve_run_ids(*, wave_manifests: Sequence[str], run_ids: Sequence[str]) -> list[int]:
    resolved: list[int] = []
    for raw in run_ids:
        for item in str(raw).replace(";", ",").split(","):
            text = item.strip()
            if text:
                resolved.append(_positive_int(text, "--run-ids"))
    for manifest in wave_manifests:
        resolved.extend(run_ids_from_wave_manifest(manifest))
    return _dedupe_ints(resolved)


def run_ids_from_wave_manifest(path: str | Path) -> list[int]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = (((payload.get("research_result") or {}).get("details") or {}).get("runs") or [])
    if not isinstance(rows, list):
        raise ValueError(f"{path}: research_result.details.runs is not a list")
    run_ids = [_optional_int(row.get("run_id")) for row in rows if isinstance(row, dict)]
    out = [run_id for run_id in run_ids if run_id is not None and run_id > 0]
    if not out:
        raise ValueError(f"{path}: no run IDs found")
    return out


def build_forensics_report(
    *,
    db: Any,
    wave_manifests: Sequence[str] = (),
    run_ids: Sequence[int] = (),
    top_candidates: int = 25,
) -> dict[str, Any]:
    exact_run_ids = _dedupe_ints(run_ids)
    if not exact_run_ids:
        raise ValueError("Research forensics requires exact --wave-manifest or --run-ids scope")

    runs = list(
        db.query(DiscoveryRun)
        .filter(DiscoveryRun.id.in_(exact_run_ids))
        .order_by(DiscoveryRun.id.desc())
        .all()
    )
    found_run_ids = [int(run.id) for run in runs]
    patterns = []
    if found_run_ids:
        patterns = list(
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.run_id.in_(found_run_ids))
            .order_by(DiscoveredPattern.score.desc())
            .all()
        )
    pattern_ids = [int(pattern.id) for pattern in patterns]
    examples_by_pattern = _counts_by_pattern(db, DiscoveredPatternExample, pattern_ids)
    metrics_by_pattern = _counts_by_pattern(db, DiscoveredPatternMetric, pattern_ids)
    matches_by_pattern = _counts_by_pattern(db, DiscoveredPatternMatch, pattern_ids)

    all_candidates = [
        candidate_forensics(
            pattern,
            example_count=examples_by_pattern.get(int(pattern.id), 0),
            metric_snapshot_count=metrics_by_pattern.get(int(pattern.id), 0),
            match_count=matches_by_pattern.get(int(pattern.id), 0),
        )
        for pattern in patterns
    ]
    candidates = sorted(all_candidates, key=_candidate_rank, reverse=True)[: max(1, int(top_candidates))]
    all_candidate_dicts = [candidate.to_dict() for candidate in candidates]
    blocker_counts = Counter(label for candidate in all_candidates for label in candidate.failure_taxonomy)
    exact_reasons = Counter(reason for pattern in patterns for reason in _reasons(pattern))
    run_totals = {
        "runs": len(runs),
        "completed": sum(1 for run in runs if str(run.status) == "completed"),
        "failed": sum(1 for run in runs if str(run.status) == "failed"),
        "running": sum(1 for run in runs if str(run.status) == "running"),
        "windows": sum(int(run.windows_sampled or 0) for run in runs),
        "clusters": sum(int(run.clusters_evaluated or 0) for run in runs),
        "accepted": sum(int(run.accepted_patterns or 0) for run in runs),
        "rejected": sum(int(run.rejected_patterns or 0) for run in runs),
        "duration_s": round(sum(float(run.duration_seconds or 0.0) for run in runs), 3),
    }
    persisted_candidates = len(patterns)
    manifest_metadata = _manifest_metadata(wave_manifests)
    scope = {
        "exact_scope": True,
        "wave_manifests": list(wave_manifests),
        "requested_run_ids": list(exact_run_ids),
        "run_ids": found_run_ids,
        "missing_run_ids": sorted(set(exact_run_ids) - set(found_run_ids)),
        "universe": manifest_metadata.get("universe_file") or _first_param(runs, "universe_file"),
        "product_policy": (
            manifest_metadata.get("product_policy")
            or _first_param(runs, "universe_policy")
            or _first_param(runs, "product_policy")
        ),
        "manifest_metadata": manifest_metadata,
    }
    wave_summary = {
        **run_totals,
        "persisted_candidates": persisted_candidates,
        "store_rejected_likely_disabled": bool(
            run_totals["clusters"] > 0 and persisted_candidates < max(1, run_totals["rejected"])
        ),
        "top_blockers": dict(blocker_counts.most_common(20)),
        "exact_rejection_reasons": dict(exact_reasons.most_common(20)),
    }
    report = {
        "schema_version": "tradeo.intraday_research_forensics.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": scope,
        "data_granularity": data_granularity_summary(
            patterns=patterns,
            examples_by_pattern=examples_by_pattern,
            metrics_by_pattern=metrics_by_pattern,
            matches_by_pattern=matches_by_pattern,
        ),
        "wave_summary": wave_summary,
        "run_totals": run_totals,
        "candidate_visibility": {
            "persisted_candidates": persisted_candidates,
            "summary_candidates": _summary_candidate_count(runs),
            "report_candidates": 0,
            "store_rejected_likely_disabled": wave_summary["store_rejected_likely_disabled"],
        },
        "top_blockers": wave_summary["top_blockers"],
        "top_exact_rejection_reasons": wave_summary["exact_rejection_reasons"],
        "taxonomy_counts": dict(blocker_counts.most_common()),
        "near_misses": all_candidate_dicts,
        "recommended_actions": next_hypotheses(blocker_counts),
        "diagnostic_flags": _diagnostic_flags(run_totals, persisted_candidates),
        "candidate_forensics": all_candidate_dicts,
        "failure_taxonomy": dict(blocker_counts.most_common()),
        "next_hypotheses": next_hypotheses(blocker_counts),
        "prohibited_repeats": list(PROHIBITED_REPEATS),
        "safety": {
            "live_allowed": False,
            "paper_allowed": False,
            "orders_allowed": False,
            "order_code_allowed": False,
            "gates_allowed": False,
            "read_only": True,
        },
    }
    report["determinism"] = {
        "algo": CONTENT_HASH_ALGO,
        "content_hash": content_hash(report),
    }
    return report


def candidate_forensics(
    pattern: DiscoveredPattern,
    *,
    example_count: int = 0,
    metric_snapshot_count: int = 0,
    match_count: int = 0,
) -> CandidateForensics:
    metrics = pattern.metrics_json if isinstance(pattern.metrics_json, dict) else {}
    reasons = tuple(_reasons(pattern))
    taxonomy = classify_failure(
        rejection_reasons=reasons,
        metrics=metrics,
        sample_count=int(pattern.sample_count or 0),
        symbol_count=int(pattern.symbol_count or 0),
        year_count=int(pattern.year_count or 0),
        oos_expectancy_r=_coalesce_float(
            getattr(pattern, "out_of_sample_expectancy_r", None),
            metrics.get("out_of_sample_expectancy_r"),
            metrics.get("oos_expectancy_r"),
        ),
        oos_profit_factor=_coalesce_float(
            getattr(pattern, "out_of_sample_profit_factor", None),
            metrics.get("out_of_sample_profit_factor"),
            metrics.get("oos_profit_factor"),
        ),
        drawdown_r=_coalesce_float(
            getattr(pattern, "best_max_drawdown_r", None),
            metrics.get("best_max_drawdown_r"),
            metrics.get("max_drawdown_r"),
        ),
    )
    return CandidateForensics(
        pattern_key=str(pattern.pattern_key or ""),
        name=str(pattern.name or ""),
        run_id=_optional_int(pattern.run_id),
        side=str(pattern.side or ""),
        timeframe=str(pattern.timeframe or "") or None,
        window_size=_optional_int(pattern.window_size),
        expectancy_r=_coalesce_float(pattern.best_expectancy_r, pattern.expectancy_r, metrics.get("expectancy_r")),
        profit_factor=_coalesce_float(pattern.best_profit_factor, pattern.profit_factor, metrics.get("profit_factor")),
        oos_expectancy_r=_coalesce_float(
            pattern.out_of_sample_expectancy_r,
            metrics.get("out_of_sample_expectancy_r"),
            metrics.get("oos_expectancy_r"),
        ),
        oos_profit_factor=_coalesce_float(
            pattern.out_of_sample_profit_factor,
            metrics.get("out_of_sample_profit_factor"),
            metrics.get("oos_profit_factor"),
        ),
        symbol_count=int(pattern.symbol_count or 0),
        sample_count=int(pattern.sample_count or 0),
        drawdown_r=_coalesce_float(pattern.best_max_drawdown_r, metrics.get("max_drawdown_r")),
        cost_x2_result=_cost_x2_result(metrics, reasons),
        fdr_result=_boolean_result(metrics.get("fdr_passed"), reasons, ("fdr", "bh-fdr")),
        wrc_result=_pvalue_result(metrics.get("wrc_p_value"), reasons, ("wrc",)),
        spa_result=_pvalue_result(metrics.get("spa_p_value"), reasons, ("spa",)),
        market_replay=_reason_result(reasons, ("market replay",)),
        placebo_adversarial=_reason_result(reasons, ("adversarial", "placebo", "shock")),
        dominant_failure_class=taxonomy[0] if taxonomy else "unclassified",
        failure_taxonomy=tuple(taxonomy),
        rejection_reasons=reasons,
        data_granularity={
            "examples": example_count,
            "metric_snapshots": metric_snapshot_count,
            "matches": match_count,
            "time_of_day_analysis": NOT_AVAILABLE,
            "spy_qqq_regime_analysis": NOT_AVAILABLE,
            "rvol_gap_analysis": NOT_AVAILABLE,
            "per_symbol_examples_available": example_count > 0,
        },
    )


def classify_failure(
    *,
    rejection_reasons: Sequence[str],
    metrics: dict[str, Any] | None = None,
    sample_count: int = 0,
    symbol_count: int = 0,
    year_count: int = 0,
    oos_expectancy_r: float | None = None,
    oos_profit_factor: float | None = None,
    drawdown_r: float | None = None,
) -> list[str]:
    metrics = metrics or {}
    text = " | ".join(str(reason).lower() for reason in rejection_reasons)
    out: list[str] = []
    if "cost" in text or "coste" in text or metrics.get("cost_stress_passed") is False:
        out.append("cost_dominated")
    if (
        "oos" in text
        or "out-of-sample" in text
        or "market replay" in text
        or (oos_expectancy_r is not None and oos_expectancy_r <= 0)
        or (oos_profit_factor is not None and oos_profit_factor < 1.2)
    ):
        out.append("oos_unstable")
    if any(token in text for token in ("fdr", "wrc", "spa", "p_adj", "significancia", "bootstrap reality")):
        out.append("statistical_datamined")
    if "drawdown" in text or (drawdown_r is not None and drawdown_r > 12.0):
        out.append("drawdown_excessive")
    if any(token in text for token in ("date_shock", "universe_shock", "walk-forward", "regime", "replay")):
        out.append("regime_sensitive_candidate")
    if "concentracion" in text or "concentration" in text or "symbol_concentration" in text:
        out.append("concentration_risk")
    if "fill" in text or "operational" in text:
        out.append("operationally_unavailable")
    if sample_count < 50 or symbol_count < 6 or year_count < 1:
        out.append("insufficient_data")
    return _dedupe_strings(out)


def next_hypotheses(failures: Counter[str]) -> list[dict[str, str]]:
    ranked: list[dict[str, str]] = []
    if failures["cost_dominated"]:
        ranked.append(
            {
                "hypothesis": "cost/spread filter required",
                "reason": "Cost stress or cost-shock appears in dominant failures.",
            }
        )
        ranked.append(
            {
                "hypothesis": "ultra-liquid-only universe",
                "reason": "Cost failures should be isolated before broader pattern search repeats.",
            }
        )
    if failures["regime_sensitive_candidate"]:
        ranked.extend(
            [
                {"hypothesis": "time-of-day split", "reason": "Replay/date/walk-forward instability suggests regime sensitivity."},
                {"hypothesis": "RVOL/gap split", "reason": "Use only if event-level data becomes available; otherwise report not_available."},
                {"hypothesis": "SPY/QQQ regime split", "reason": "Broad-market state may explain OOS instability."},
            ]
        )
    if failures["statistical_datamined"] or failures["oos_unstable"]:
        ranked.append(
            {
                "hypothesis": "reject family entirely",
                "reason": "Repeated OOS and multiple-testing failures are broad, not isolated.",
            }
        )
    if not ranked:
        ranked.append({"hypothesis": "W100 structural search", "reason": "Only consider with explicit new authorization."})
    return ranked


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Intraday Research Forensics",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Scope",
        f"- exact_scope: `{report['scope']['exact_scope']}`",
        f"- wave_manifests: `{', '.join(report['scope']['wave_manifests']) or NOT_AVAILABLE}`",
        f"- run_ids: `{', '.join(str(item) for item in report['scope']['run_ids'])}`",
        f"- universe: `{report['scope'].get('universe') or NOT_AVAILABLE}`",
        f"- product_policy: `{report['scope'].get('product_policy') or NOT_AVAILABLE}`",
        "",
        "## Wave Summary",
    ]
    for key, value in report["wave_summary"].items():
        if isinstance(value, dict):
            lines.append(f"- {key}:")
            for subkey, subvalue in list(value.items())[:12]:
                lines.append(f"  - {subkey}: `{subvalue}`")
        else:
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Data Granularity"])
    for key, value in report["data_granularity"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Candidate Forensics"])
    for candidate in report["candidate_forensics"]:
        lines.extend(
            [
                f"### {candidate['name'] or candidate['pattern_key']}",
                f"- pattern_key: `{candidate['pattern_key']}`",
                f"- run_id: `{candidate['run_id']}` side: `{candidate['side']}` timeframe: `{candidate['timeframe']}` W{candidate['window_size']}",
                f"- expectancy/PF: `{candidate['expectancy_r']}` / `{candidate['profit_factor']}`",
                f"- OOS expectancy/PF: `{candidate['oos_expectancy_r']}` / `{candidate['oos_profit_factor']}`",
                f"- samples/symbols: `{candidate['sample_count']}` / `{candidate['symbol_count']}`",
                f"- drawdown_r: `{candidate['drawdown_r']}` cost_x2: `{candidate['cost_x2_result']}`",
                f"- FDR/WRC/SPA: `{candidate['fdr_result']}` / `{candidate['wrc_result']}` / `{candidate['spa_result']}`",
                f"- market_replay: `{candidate['market_replay']}` placebo_adversarial: `{candidate['placebo_adversarial']}`",
                f"- dominant_failure_class: `{candidate['dominant_failure_class']}`",
                f"- failure_taxonomy: `{', '.join(candidate['failure_taxonomy'])}`",
                "",
            ]
        )
    lines.extend(["## Next Hypotheses"])
    for item in report["next_hypotheses"]:
        lines.append(f"- {item['hypothesis']}: {item['reason']}")
    lines.extend(["", "## Prohibited Repeats"])
    lines.extend(f"- {item}" for item in report["prohibited_repeats"])
    lines.extend(["", "## Safety"])
    for key, value in report["safety"].items():
        lines.append(f"- {key}: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def data_granularity_summary(
    *,
    patterns: Sequence[DiscoveredPattern],
    examples_by_pattern: dict[int, int],
    metrics_by_pattern: dict[int, int],
    matches_by_pattern: dict[int, int],
) -> dict[str, Any]:
    return {
        "candidate_level_metrics": bool(patterns),
        "rejection_reasons": any(_reasons(pattern) for pattern in patterns),
        "run_ids": bool(patterns),
        "symbol_count": any(int(pattern.symbol_count or 0) > 0 for pattern in patterns),
        "sample_count": any(int(pattern.sample_count or 0) > 0 for pattern in patterns),
        "oos_metrics": any(
            _coalesce_float(pattern.out_of_sample_expectancy_r, pattern.out_of_sample_profit_factor) is not None
            for pattern in patterns
        ),
        "cost_stress": _available_by_reason_or_metric(patterns, ("cost", "coste"), "cost_stress_passed"),
        "drawdown": any(_coalesce_float(pattern.best_max_drawdown_r) is not None for pattern in patterns),
        "market_replay": _available_by_reason_or_metric(patterns, ("market replay",), None),
        "placebo_adversarial": _available_by_reason_or_metric(patterns, ("adversarial", "placebo", "shock"), None),
        "per_symbol_examples": sum(examples_by_pattern.values()) or NOT_AVAILABLE,
        "metric_snapshots": sum(metrics_by_pattern.values()) or NOT_AVAILABLE,
        "matches": sum(matches_by_pattern.values()) or NOT_AVAILABLE,
        "timestamp_symbol_events": sum(examples_by_pattern.values()) or NOT_AVAILABLE,
        "symbol_month_contributions": NOT_AVAILABLE,
        "time_of_day_regime_analysis": NOT_AVAILABLE,
        "spy_qqq_regime_inputs": NOT_AVAILABLE,
        "rvol_gap_inputs": NOT_AVAILABLE,
    }


def _counts_by_pattern(db: Any, model: Any, pattern_ids: Sequence[int]) -> dict[int, int]:
    if not pattern_ids:
        return {}
    rows = db.query(model.pattern_id).filter(model.pattern_id.in_(pattern_ids)).all()
    return dict(Counter(int(row[0]) for row in rows))


def _summary_candidate_count(runs: Sequence[DiscoveryRun]) -> int:
    total = 0
    for run in runs:
        summary = run.summary_json if isinstance(run.summary_json, dict) else {}
        for key in ("top_patterns", "confirmation_queue"):
            rows = summary.get(key) or []
            if isinstance(rows, list):
                total += len(rows)
    return total


def _diagnostic_flags(run_totals: dict[str, Any], persisted_candidates: int) -> list[str]:
    flags: list[str] = []
    if run_totals["runs"] == 0:
        flags.append("no_discovery_runs")
    if run_totals["windows"] > 0 and run_totals["clusters"] == 0:
        flags.append("windows_but_zero_clusters")
    if run_totals["clusters"] > 0 and persisted_candidates == 0:
        flags.append("clusters_without_persisted_candidates")
    if run_totals["accepted"] == 0 and run_totals["clusters"] > 0:
        flags.append("validation_gate_blocking_all_candidates")
    return flags


def _reasons(pattern: DiscoveredPattern) -> list[str]:
    reasons = pattern.rejection_reasons_json or pattern.validation_reasons_json or []
    return [str(reason) for reason in reasons if str(reason)]


def _candidate_rank(candidate: CandidateForensics) -> tuple[float, float, int, int]:
    expectancy = candidate.expectancy_r or 0.0
    profit_factor = candidate.profit_factor or 0.0
    penalty = 0.2 * len(candidate.failure_taxonomy)
    score = max(expectancy, 0.0) * 2.0 + min(max(profit_factor, 0.0), 4.0) * 0.5 - penalty
    return (round(score, 6), expectancy, candidate.sample_count, candidate.symbol_count)


def _available_by_reason_or_metric(
    patterns: Sequence[DiscoveredPattern], reason_tokens: Sequence[str], metric_key: str | None
) -> bool:
    for pattern in patterns:
        metrics = pattern.metrics_json if isinstance(pattern.metrics_json, dict) else {}
        if metric_key and metric_key in metrics:
            return True
        text = " | ".join(_reasons(pattern)).lower()
        if any(token in text for token in reason_tokens):
            return True
    return False


def _first_param(runs: Sequence[DiscoveryRun], key: str) -> Any:
    for run in runs:
        params = run.params_json if isinstance(run.params_json, dict) else {}
        if params.get(key):
            return params.get(key)
    return None


def _manifest_metadata(paths: Sequence[str]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "timeframes": [],
        "window_sizes": [],
        "forward_bars": [],
    }
    for path in paths:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        readiness = payload.get("readiness") or {}
        spec = readiness.get("spec") or {}
        if spec.get("universe_file") and not out.get("universe_file"):
            out["universe_file"] = spec.get("universe_file")
        policy = spec.get("product_policy") or spec.get("universe_policy")
        if policy and not out.get("product_policy"):
            out["product_policy"] = policy
        for key in ("timeframes", "window_sizes", "forward_bars"):
            values = spec.get(key) or []
            if not isinstance(values, list):
                values = [values]
            out[key].extend(str(value) for value in values if str(value))
    for key in ("timeframes", "window_sizes", "forward_bars"):
        out[key] = _dedupe_strings(out[key])
    return out


def _cost_x2_result(metrics: dict[str, Any], reasons: Sequence[str]) -> str:
    text = " | ".join(reason.lower() for reason in reasons)
    if "edge no sobrevive coste x2" in text or "cost_shock" in text:
        return "failed"
    if metrics.get("cost_stress_passed") is False:
        return "failed"
    if metrics.get("cost_stress_passed") is True:
        return "passed"
    return NOT_AVAILABLE


def _boolean_result(value: Any, reasons: Sequence[str], tokens: Sequence[str]) -> str:
    if value is True:
        return "passed"
    if value is False:
        return "failed"
    return _reason_result(reasons, tokens)


def _pvalue_result(value: Any, reasons: Sequence[str], tokens: Sequence[str]) -> str:
    parsed = _optional_float(value)
    if parsed is not None:
        return "passed" if parsed <= 0.25 else "failed"
    return _reason_result(reasons, tokens)


def _reason_result(reasons: Sequence[str], tokens: Sequence[str]) -> str:
    text = " | ".join(reason.lower() for reason in reasons)
    return "failed" if any(token in text for token in tokens) else NOT_AVAILABLE


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


def _positive_int(value: Any, label: str) -> int:
    parsed = _optional_int(value)
    if parsed is None or parsed <= 0:
        raise ValueError(f"{label} expects positive integer values, got {value!r}")
    return parsed


def _dedupe_ints(values: Iterable[int]) -> list[int]:
    output: list[int] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output


def _dedupe_strings(values: Iterable[str]) -> list[str]:
    output: list[str] = []
    for value in values:
        if value not in output:
            output.append(value)
    return output
