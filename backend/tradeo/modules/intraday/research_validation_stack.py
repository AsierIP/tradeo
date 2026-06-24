from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from tradeo.modules.intraday.research import (
    IntradayResearchConfig,
    IntradayResearchEvent,
    IntradayResearchOutcome,
    IntradayResearchReport,
    evaluate_intraday_research,
)
from tradeo.modules.intraday.research_contracts import INTRADAY_RESEARCH_CORE_VERSION
from tradeo.research.quant_validation import average_uniqueness_weights


@dataclass(frozen=True, slots=True)
class IntradayMatchedBaseline:
    events: tuple[IntradayResearchEvent, ...]
    bucket_counts: dict[str, int]
    missing_buckets: tuple[str, ...]
    method: str = "matched_intraday_bucket_round_robin_v2"

    @property
    def complete(self) -> bool:
        return not self.missing_buckets


class IntradayMatchedBaselineFactory:
    """Deterministic baseline sampler matched by intraday bucket."""

    def build(
        self,
        real_events: Iterable[IntradayResearchEvent | Mapping[str, Any]],
        baseline_events: Iterable[IntradayResearchEvent | Mapping[str, Any]],
    ) -> IntradayMatchedBaseline:
        real = tuple(_event(e) for e in real_events)
        pool = tuple(_event(e) for e in baseline_events)
        wanted = Counter(e.bucket_key for e in real)
        by_bucket: dict[str, list[IntradayResearchEvent]] = defaultdict(list)
        for event in pool:
            by_bucket[event.bucket_key].append(event)
        for rows in by_bucket.values():
            rows.sort(key=lambda e: e.resolved_event_id)
        selected: list[IntradayResearchEvent] = []
        counts: Counter[str] = Counter()
        missing: list[str] = []
        for bucket, count in sorted(wanted.items()):
            rows = by_bucket.get(bucket, [])
            if not rows:
                missing.append(bucket)
                continue
            for idx in range(count):
                selected.append(rows[idx % len(rows)])
                counts[bucket] += 1
        return IntradayMatchedBaseline(tuple(selected), dict(sorted(counts.items())), tuple(sorted(missing)))


@dataclass(frozen=True, slots=True)
class IntradayValidationThresholds:
    min_raw_events: int = 50
    min_effective_events: float = 25.0
    min_unique_symbols: int = 5
    min_unique_sessions: int = 5
    min_buckets: int = 2
    min_net_expectancy_r: float = 0.05
    min_edge_vs_baseline_r: float = 0.01
    min_profit_factor: float = 1.20
    max_symbol_concentration: float = 0.35
    max_session_concentration: float = 0.25
    required_cost_multipliers: tuple[float, ...] = (1.0, 2.0, 3.0)
    fail_on_report_reasons: bool = True


@dataclass(frozen=True, slots=True)
class IntradayValidationResult:
    accepted: bool
    reason_codes: tuple[str, ...]
    metrics: dict[str, Any]
    thresholds: IntradayValidationThresholds
    contract_version: str = INTRADAY_RESEARCH_CORE_VERSION


class IntradayValidationStack:
    def __init__(self, thresholds: IntradayValidationThresholds | None = None) -> None:
        self.thresholds = thresholds or IntradayValidationThresholds()

    def evaluate_report(self, report: IntradayResearchReport) -> IntradayValidationResult:
        thresholds = self.thresholds
        rows = tuple(report.evidence_outcomes)
        metrics = _evidence_metrics(rows)
        reasons = list(report.reason_codes) if thresholds.fail_on_report_reasons else []
        if len(rows) < thresholds.min_raw_events:
            reasons.append("insufficient_raw_intraday_events")
        if metrics["effective_events"] < thresholds.min_effective_events:
            reasons.append("insufficient_effective_intraday_events")
        if metrics["unique_symbols"] < thresholds.min_unique_symbols:
            reasons.append("insufficient_intraday_symbols")
        if metrics["unique_sessions"] < thresholds.min_unique_sessions:
            reasons.append("insufficient_intraday_sessions")
        if metrics["unique_buckets"] < thresholds.min_buckets:
            reasons.append("insufficient_intraday_buckets")
        if metrics["max_symbol_concentration"] > thresholds.max_symbol_concentration:
            reasons.append("symbol_concentration_too_high")
        if metrics["max_session_concentration"] > thresholds.max_session_concentration:
            reasons.append("session_concentration_too_high")
        for multiplier in thresholds.required_cost_multipliers:
            stress = report.cost_stress.get(float(multiplier))
            suffix = f"{int(multiplier)}x" if float(multiplier).is_integer() else f"{multiplier:g}x"
            if stress is None:
                reasons.append(f"missing_cost_stress_{suffix}")
                continue
            if stress.expectancy_r < thresholds.min_net_expectancy_r:
                reasons.append(f"net_ev_below_threshold_{suffix}")
            if stress.edge_vs_null_r is None or stress.edge_vs_null_r < thresholds.min_edge_vs_baseline_r:
                reasons.append(f"baseline_edge_below_threshold_{suffix}")
            if multiplier == 1.0 and stress.profit_factor < thresholds.min_profit_factor:
                reasons.append("profit_factor_below_threshold_1x")
        metrics |= {
            "report_accepted": report.accepted,
            "net_expectancy_r": report.net_expectancy_r,
            "math_backend": "grouped_n_eff_vectorized",
        }
        return IntradayValidationResult(
            accepted=not reasons,
            reason_codes=tuple(dict.fromkeys(reasons)),
            metrics=metrics,
            thresholds=thresholds,
        )

    def evaluate(
        self,
        events: Iterable[IntradayResearchEvent | Mapping[str, Any]],
        bars_by_symbol_session: Mapping[Any, Any],
        *,
        baseline_events: Iterable[IntradayResearchEvent | Mapping[str, Any]] | None = None,
        research_config: IntradayResearchConfig | None = None,
    ) -> tuple[IntradayResearchReport, IntradayValidationResult]:
        report = evaluate_intraday_research(
            events,
            bars_by_symbol_session,
            null_events=baseline_events,
            config=research_config,
        )
        return report, self.evaluate_report(report)


def _evidence_metrics(rows: Sequence[IntradayResearchOutcome]) -> dict[str, Any]:
    if not rows:
        return {
            "raw_events": 0,
            "effective_events": 0.0,
            "unique_symbols": 0,
            "unique_sessions": 0,
            "unique_buckets": 0,
            "max_symbol_concentration": 0.0,
            "max_session_concentration": 0.0,
        }
    by_session: dict[str, list[IntradayResearchOutcome]] = defaultdict(list)
    for row in rows:
        by_session[row.event.session_id].append(row)
    effective = 0.0
    for grouped in by_session.values():
        _, session_eff = average_uniqueness_weights(
            [r.span_start for r in grouped],
            [r.span_end for r in grouped],
        )
        effective += session_eff
    symbols = Counter(r.event.symbol for r in rows)
    sessions = Counter(r.event.session_id for r in rows)
    buckets = Counter(r.bucket_key for r in rows)
    n_rows = len(rows)
    return {
        "raw_events": n_rows,
        "effective_events": round(float(effective), 6),
        "unique_symbols": len(symbols),
        "unique_sessions": len(sessions),
        "unique_buckets": len(buckets),
        "max_symbol_concentration": max(symbols.values()) / n_rows,
        "max_session_concentration": max(sessions.values()) / n_rows,
        "bucket_counts": dict(sorted(buckets.items())),
    }


def _event(raw: IntradayResearchEvent | Mapping[str, Any]) -> IntradayResearchEvent:
    return raw if isinstance(raw, IntradayResearchEvent) else IntradayResearchEvent.from_mapping(raw)
