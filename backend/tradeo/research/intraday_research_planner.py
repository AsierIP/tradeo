from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Literal

PlannerDecision = Literal[
    "data_missing",
    "expand_universe",
    "candidate_for_confirmation",
    "hypothesis_side_mismatch_blocked",
    "change_search_space",
    "continue_matrix",
]

_DEFAULT_UNIVERSE = "/app/artifacts/runtime/universe_intraday_stock_only_v3.csv"
_DEFAULT_POLICY = "stock_only"
_DEFAULT_PERIOD = "60d"
_RESEARCH_VWAP_CONDITIONS = {
    "vwap_reclaim_long",
    "vwap_reject_short",
    "vwap_pullback_long",
    "vwap_pullback_short",
    "vwap_above_rising",
    "vwap_below_falling",
    "vwap_mean_reversion_long",
    "vwap_mean_reversion_short",
}
_VWAP_CONDITION_BY_WAVE_NAME = {
    "30m_W100_vwap_reclaim_slow": "vwap_reclaim_long",
    "30m_W100_vwap_reject_slow": "vwap_reject_short",
    "15m_W50_vwap_pullback_fast": "vwap_pullback_long",
    "1h_W100_vwap_regime_filter": "vwap_above_rising",
}


@dataclass(frozen=True, slots=True)
class ResearchWaveSpec:
    name: str
    timeframe: str
    window_sizes: tuple[int, ...]
    forward_bars: tuple[int, ...]
    max_total_windows: int
    max_windows_per_symbol: int
    hypothesis: str
    priority: int
    requires_cache_warmup: bool = False
    vwap_condition: str | None = None
    session_filter: str = "none"
    cost_filter: str = "none"
    max_execution_cost_r: float | None = None
    legacy_overlap: bool = False

    def env(self, *, universe_file: str, product_policy: str, period: str, store_rejected: bool) -> dict[str, str]:
        env = {
            "TRADEO_INTRADAY_UNIVERSE_FILE": universe_file,
            "TRADEO_INTRADAY_UNIVERSE_POLICY": product_policy,
            "TRADEO_INTRADAY_RESEARCH_REFRESH_MARKET_DATA_ENABLED": "false",
            "TRADEO_DISCOVERY_STORE_REJECTED": str(store_rejected).lower(),
            "TRADEO_INTRADAY_TIMEFRAMES": self.timeframe,
            "TRADEO_INTRADAY_RESEARCH_WINDOW_SIZES": _csv(self.window_sizes),
            "TRADEO_INTRADAY_RESEARCH_FORWARD_BARS": _csv(self.forward_bars),
            "TRADEO_INTRADAY_RESEARCH_PERIOD": period,
            "TRADEO_INTRADAY_RESEARCH_MAX_TOTAL_WINDOWS": str(self.max_total_windows),
            "TRADEO_INTRADAY_RESEARCH_MAX_WINDOWS_PER_SYMBOL": str(self.max_windows_per_symbol),
        }
        if self.vwap_condition:
            env["TRADEO_INTRADAY_RESEARCH_VWAP_CONDITION"] = self.vwap_condition
        if self.session_filter != "none":
            env["TRADEO_INTRADAY_RESEARCH_SESSION_FILTER"] = self.session_filter
        if self.cost_filter != "none":
            env["TRADEO_INTRADAY_RESEARCH_COST_FILTER"] = self.cost_filter
        if self.max_execution_cost_r is not None:
            env["TRADEO_INTRADAY_RESEARCH_MAX_EXECUTION_COST_R"] = str(self.max_execution_cost_r)
        return env

    @property
    def signatures(self) -> tuple[str, ...]:
        suffix_parts = []
        if self.vwap_condition:
            suffix_parts.append(self.vwap_condition)
        if self.session_filter != "none":
            suffix_parts.append(f"session_{self.session_filter}")
        if self.cost_filter != "none":
            cost_suffix = self.cost_filter
            if self.max_execution_cost_r is not None:
                cost_suffix = f"{cost_suffix}_{self.max_execution_cost_r:g}"
            suffix_parts.append(cost_suffix)
        suffix = f" {' '.join(suffix_parts)}" if suffix_parts else ""
        return tuple(
            f"{self.timeframe} W{window_size} {_csv(self.forward_bars)}{suffix}"
            for window_size in self.window_sizes
        )


@dataclass(frozen=True, slots=True)
class BlockedWave:
    name: str
    reason: str
    signature: str
    wave: ResearchWaveSpec


@dataclass(frozen=True, slots=True)
class CandidateSignal:
    pattern_key: str
    run_id: int | None = None
    side: str | None = None
    expected_side: str | None = None
    side_matches_hypothesis: bool | None = None
    hypothesis_rejection_reason: str | None = None
    expectancy_r: float = 0.0
    profit_factor: float = 0.0
    oos_expectancy_r: float = 0.0
    oos_profit_factor: float = 0.0
    symbol_count: int = 0
    sample_count: int = 0
    max_drawdown_r: float = 0.0
    market_replay: str | None = None
    cost_x2_result: str | None = None
    fdr_result: str | None = None
    wrc_result: str | None = None
    spa_result: str | None = None
    failure_taxonomy: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()

    @property
    def confirmation_score(self) -> float:
        score = 0.0
        if self.symbol_count >= 6:
            score += 1.0
        if self.oos_expectancy_r > 0:
            score += 1.0
        if self.oos_profit_factor >= 1.2:
            score += 1.0
        if self.profit_factor >= 1.5:
            score += 0.5
        if 0 < self.max_drawdown_r <= 18:
            score += 0.5
        reason_text = " ".join(self.rejection_reasons).lower()
        if "cost" not in reason_text and "coste" not in reason_text:
            score += 1.0
        if not any(token in reason_text for token in ("fdr", "wrc", "spa", "placebo", "adversarial")):
            score += 1.0
        return score


@dataclass(frozen=True, slots=True)
class PlannerInput:
    selected_count: int
    selected_count_source: str = "diagnostic_json"
    selected_count_diagnostic_value: int | None = None
    readiness_ready: bool = True
    readiness_coverage: float = 1.0
    universe_file: str = _DEFAULT_UNIVERSE
    product_policy: str = _DEFAULT_POLICY
    period: str = _DEFAULT_PERIOD
    windows: int = 0
    clusters: int = 0
    accepted: int = 0
    rejected: int = 0
    persisted_candidates: int = 0
    blockers: dict[str, int] = field(default_factory=dict)
    exact_rejection_reasons: dict[str, int] = field(default_factory=dict)
    candidates: tuple[CandidateSignal, ...] = ()
    prohibited_repeats: tuple[str, ...] = ()
    vwap_summary: dict[str, Any] | None = None
    context_filtering: dict[str, Any] = field(default_factory=dict)
    execution_contract_integrity: dict[str, Any] | None = None
    source: str = "manual"


@dataclass(frozen=True, slots=True)
class PlannerOutput:
    generated_at: str
    decision: PlannerDecision
    rationale: tuple[str, ...]
    candidate_for_confirmation: tuple[CandidateSignal, ...]
    candidate_for_shadow_review: tuple[CandidateSignal, ...]
    blocked_candidates: tuple[dict[str, Any], ...]
    confirmation_gate: dict[str, Any]
    waves: tuple[ResearchWaveSpec, ...]
    allowed_waves: tuple[ResearchWaveSpec, ...]
    blocked_waves: tuple[BlockedWave, ...]
    recommended_limit: int
    limit_source: str
    execution_contract_integrity: dict[str, Any]
    vwap_context: dict[str, Any]
    context_filtering: dict[str, Any]
    actions: tuple[str, ...]
    safety: dict[str, Any]
    input_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "decision": self.decision,
            "rationale": list(self.rationale),
            "candidate_for_confirmation": [asdict(candidate) for candidate in self.candidate_for_confirmation],
            "candidate_for_shadow_review": [asdict(candidate) for candidate in self.candidate_for_shadow_review],
            "blocked_candidates": list(self.blocked_candidates),
            "confirmation_gate": self.confirmation_gate,
            "waves": [asdict(wave) for wave in self.waves],
            "allowed_waves": [asdict(wave) for wave in self.allowed_waves],
            "blocked_waves": [
                {
                    "name": blocked.name,
                    "reason": blocked.reason,
                    "signature": blocked.signature,
                    "wave": asdict(blocked.wave),
                }
                for blocked in self.blocked_waves
            ],
            "recommended_limit": self.recommended_limit,
            "limit_source": self.limit_source,
            "execution_contract_integrity": self.execution_contract_integrity,
            "vwap_context": self.vwap_context,
            "context_filtering": self.context_filtering,
            "actions": list(self.actions),
            "safety": self.safety,
            "input_summary": self.input_summary,
        }


class IntradayResearchPlanner:
    """Turn rejected intraday research into the next focused experiments.

    The planner is intentionally read-only. It does not relax gates, touch order
    execution, or run research. Its job is to stop repeating a failed family and
    convert dominant blockers into a compact, auditable next-wave plan.
    """

    def plan(self, data: PlannerInput) -> PlannerOutput:
        promising = tuple(
            sorted(
                (candidate for candidate in data.candidates if candidate.confirmation_score >= 5.0),
                key=lambda candidate: candidate.confirmation_score,
                reverse=True,
            )[:5]
        )
        hard_blockers = tuple(
            blocker
            for candidate in promising
            for blocker in _confirmation_hard_blockers(candidate)
        )
        blocked_keys = {str(blocker["pattern_key"]) for blocker in hard_blockers}
        blocked_candidates = hard_blockers
        confirmation = tuple(candidate for candidate in promising if candidate.pattern_key not in blocked_keys)
        confirmation_gate = {
            "passed": bool(confirmation) and not hard_blockers,
            "hard_blockers": list(hard_blockers),
        }
        decision: PlannerDecision
        rationale: list[str] = []
        waves: list[ResearchWaveSpec] = []
        allowed_waves: tuple[ResearchWaveSpec, ...] = ()
        blocked_waves: tuple[BlockedWave, ...] = ()
        actions: list[str] = []
        contract = _execution_contract_integrity(data.execution_contract_integrity)

        if contract["material_mismatches"]:
            decision = "change_search_space"
            confirmation = ()
            blocked_candidates = tuple(
                {
                    "pattern_key": "execution_contract",
                    "reason": "material_execution_contract_mismatch",
                    "metric": item.get("field"),
                    "value": item.get("actual"),
                    "threshold": item.get("requested"),
                }
                for item in contract["material_mismatches"]
            )
            confirmation_gate = {
                "passed": False,
                "hard_blockers": list(blocked_candidates),
            }
            rationale.append("Execution contract has material requested-vs-actual mismatches; do not confirm or shadow-review.")
            actions.append("Fix the execution spec contract before any new wave authorization.")
        elif not data.readiness_ready or data.readiness_coverage < 0.90:
            decision = "data_missing"
            rationale.append("Readiness is not DATA_READY; research must not run until cache coverage is restored.")
            actions.append("Run warmup only for the selected universe/timeframe that failed readiness.")
        elif data.selected_count < 100:
            decision = "expand_universe"
            rationale.append("Selected stock_only universe is below 100; more symbols are needed before serious matrix search.")
            actions.append("Continue cache/build on the official US listed candidate universe without lowering liquidity filters.")
        elif confirmation:
            decision = "candidate_for_confirmation"
            rationale.append("At least one candidate meets the confirmation preconditions; do not paper yet, isolate and confirm.")
            actions.append("Run a narrow confirmation wave on the candidate family with identical gates and exact-scope diagnosis.")
        elif blocked_candidates:
            if all(item.get("reason") == "side_mismatch" for item in blocked_candidates):
                decision = "hypothesis_side_mismatch_blocked"
                rationale.append(
                    "Promising candidates were blocked because their side contradicts the VWAP side-bias hypothesis."
                )
                actions.append(
                    "Do not confirm the mismatched candidate; change the search space or rerun a side-compatible hypothesis."
                )
            else:
                decision = "change_search_space"
                rationale.append("Promising candidates were rejected by hard confirmation blockers.")
                rationale.extend(self._rationale_from_blockers(data))
                actions.append("Do not confirm or shadow-review hard-blocked candidates.")
                actions.extend(self._actions_from_blockers(data))
        else:
            decision = "change_search_space"
            rationale.extend(self._rationale_from_blockers(data))
            proposed_waves = self._waves_from_blockers(data)
            vwap_waves = _waves_from_vwap_summary(data.vwap_summary)
            if vwap_waves:
                proposed_waves = vwap_waves + proposed_waves
                rationale.append("VWAP summary is available; prioritize permitted VWAP-aware waves first.")
            allowed_waves, blocked_waves = filter_prohibited_waves(proposed_waves, data.prohibited_repeats)
            waves.extend(allowed_waves)
            if blocked_waves:
                rationale.append("Prohibited repeat configurations were removed from the recommended waves.")
            if proposed_waves and not allowed_waves:
                rationale.append("All generated wave candidates were prohibited repeats; Director must approve a new search family.")
            actions.extend(self._actions_from_blockers(data))
            if data.selected_count >= 100:
                actions.append(f"Run future readiness/waves with explicit --limit {data.selected_count}; never rely on defaults.")

        if decision != "change_search_space":
            allowed_waves, blocked_waves = filter_prohibited_waves(waves, data.prohibited_repeats)
            waves = list(allowed_waves)

        return PlannerOutput(
            generated_at=datetime.now(UTC).isoformat(),
            decision=decision,
            rationale=tuple(rationale),
            candidate_for_confirmation=confirmation,
            candidate_for_shadow_review=confirmation,
            blocked_candidates=blocked_candidates,
            confirmation_gate=confirmation_gate,
            waves=tuple(waves),
            allowed_waves=tuple(allowed_waves),
            blocked_waves=tuple(blocked_waves),
            recommended_limit=max(0, int(data.selected_count)),
            limit_source="selected_count_effective",
            execution_contract_integrity=contract,
            vwap_context=_vwap_context(data.vwap_summary, allowed_waves),
            context_filtering=_context_filtering(data.context_filtering),
            actions=tuple(actions),
            safety={
                "paper_allowed": False,
                "live_allowed": False,
                "order_code_allowed": False,
                "relax_gates_allowed": False,
                "requires_store_rejected": True,
                "requires_exact_scope_diagnosis": True,
            },
            input_summary={
                "selected_count": data.selected_count,
                "selected_count_effective": data.selected_count,
                "selected_count_source": data.selected_count_source,
                "selected_count_diagnostic_value": data.selected_count_diagnostic_value,
                "readiness_ready": data.readiness_ready,
                "readiness_coverage": data.readiness_coverage,
                "universe_file": data.universe_file,
                "product_policy": data.product_policy,
                "period": data.period,
                "windows": data.windows,
                "clusters": data.clusters,
                "accepted": data.accepted,
                "rejected": data.rejected,
                "persisted_candidates": data.persisted_candidates,
                "top_blockers": dict(_top_items(data.blockers, limit=12)),
                "top_exact_rejection_reasons": dict(_top_items(data.exact_rejection_reasons, limit=12)),
                "prohibited_repeats": list(data.prohibited_repeats),
                "source": data.source,
            },
        )

    def _rationale_from_blockers(self, data: PlannerInput) -> list[str]:
        blockers = _normalized_counter(data.blockers | data.exact_rejection_reasons)
        out: list[str] = []
        if _has_any(blockers, "cost", "coste", "slippage"):
            out.append("Cost stress dominates; move to higher timeframe/slower exits and require cost-aware follow-up.")
        if _has_any(blockers, "drawdown", "dd"):
            out.append("Drawdown remains excessive; longer windows or regime filters are preferred over repeating W20/W50.")
        if _has_any(blockers, "oos"):
            out.append("OOS weakness dominates; split by regime/time-of-day instead of broad-market repetitions.")
        if _has_any(blockers, "fdr", "wrc", "spa", "p_adj", "significancia"):
            out.append("Multiple-testing failures remain high; run narrower families one at a time with exact-scope diagnosis.")
        if not out:
            out.append("No confirmation candidate found; rotate search space rather than repeating the last family.")
        return out

    def _waves_from_blockers(self, data: PlannerInput) -> list[ResearchWaveSpec]:
        blockers = _normalized_counter(data.blockers | data.exact_rejection_reasons)
        waves: list[ResearchWaveSpec] = []
        if _has_any(blockers, "cost", "coste", "slippage"):
            waves.append(
                ResearchWaveSpec(
                    name="1h_W50_cost_aware",
                    timeframe="1h",
                    window_sizes=(50,),
                    forward_bars=(2, 4, 6),
                    max_total_windows=80_000,
                    max_windows_per_symbol=800,
                    hypothesis="Higher timeframe and wider pattern context reduce cost/slippage dominance.",
                    priority=1,
                    requires_cache_warmup=True,
                )
            )
            waves.append(
                ResearchWaveSpec(
                    name="30m_W100_slow_exit",
                    timeframe="30m",
                    window_sizes=(100,),
                    forward_bars=(8, 13, 21),
                    max_total_windows=120_000,
                    max_windows_per_symbol=1_200,
                    hypothesis="Longer structure plus slower exits can convert small raw edge into cost-surviving edge.",
                    priority=2,
                )
            )
        if _has_any(blockers, "drawdown", "oos", "placebo", "adversarial"):
            waves.append(
                ResearchWaveSpec(
                    name="30m_W100_standard_regime_probe",
                    timeframe="30m",
                    window_sizes=(100,),
                    forward_bars=(4, 8, 13),
                    max_total_windows=120_000,
                    max_windows_per_symbol=1_200,
                    hypothesis="A larger pattern window tests whether W20/W50 failures were local noise.",
                    priority=3,
                )
            )
        if not waves:
            waves.append(
                ResearchWaveSpec(
                    name="15m_W50_ultra_liquid_probe",
                    timeframe="15m",
                    window_sizes=(50,),
                    forward_bars=(4, 8, 13),
                    max_total_windows=100_000,
                    max_windows_per_symbol=900,
                    hypothesis="Probe faster timeframe only after strict liquidity/cost filters; do not use as broad default.",
                    priority=4,
                )
            )
        return _dedupe_waves(waves)[:4]

    def _actions_from_blockers(self, data: PlannerInput) -> list[str]:
        actions = [
            "Do not paper/live; no candidate met confirmation criteria.",
            "Diagnose every new wave by --wave-manifest or --run-ids, never by a broad --hours scope.",
            "Persist rejected candidates for every wave.",
        ]
        blockers = _normalized_counter(data.blockers | data.exact_rejection_reasons)
        if _has_any(blockers, "cost", "coste", "slippage"):
            actions.append("Add a follow-up cost-aware analysis: rank candidates by gross edge minus base and x2 costs.")
        if _has_any(blockers, "oos", "drawdown"):
            actions.append("Plan regime splits: opening hour, final hour, gap days, high RVOL, SPY/QQQ up/down.")
        if data.persisted_candidates == 0 and data.rejected > 0:
            actions.append("Fix store_rejected before more research; rejected candidates must be persisted.")
        return actions


def load_planner_input(
    path: str | Path,
    *,
    selected_count: int | None = None,
    universe_metadata: str | Path | None = None,
    universe_file: str | Path | None = None,
) -> PlannerInput:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return planner_input_from_payload(
        payload,
        source=str(path),
        selected_count=selected_count,
        universe_metadata=universe_metadata,
        universe_file=universe_file,
    )


def planner_input_from_payload(
    payload: dict[str, Any],
    *,
    source: str = "payload",
    selected_count: int | None = None,
    universe_metadata: str | Path | None = None,
    universe_file: str | Path | None = None,
) -> PlannerInput:
    if "input_summary" in payload:
        summary = payload.get("input_summary") or {}
        resolved = resolve_selected_count(
            explicit_selected_count=selected_count,
            universe_metadata=universe_metadata,
            universe_file=universe_file,
            payload=payload,
        )
        return PlannerInput(
            selected_count=resolved["selected_count_effective"],
            selected_count_source=resolved["selected_count_source"],
            selected_count_diagnostic_value=resolved["selected_count_diagnostic_value"],
            readiness_ready=bool(summary.get("readiness_ready", True)),
            readiness_coverage=float(summary.get("readiness_coverage") or 0.0),
            universe_file=str(summary.get("universe_file") or _DEFAULT_UNIVERSE),
            product_policy=str(summary.get("product_policy") or _DEFAULT_POLICY),
            period=str(summary.get("period") or _DEFAULT_PERIOD),
            windows=int(summary.get("windows") or 0),
            clusters=int(summary.get("clusters") or 0),
            accepted=int(summary.get("accepted") or 0),
            rejected=int(summary.get("rejected") or 0),
            persisted_candidates=int(summary.get("persisted_candidates") or 0),
            blockers=dict(summary.get("top_blockers") or {}),
            exact_rejection_reasons=dict(summary.get("top_exact_rejection_reasons") or {}),
            prohibited_repeats=tuple(str(item) for item in payload.get("prohibited_repeats") or ()),
            context_filtering=_context_filtering(payload.get("context_filtering")),
            execution_contract_integrity=payload.get("execution_contract_integrity"),
            source=source,
        )

    totals = payload.get("run_totals") or payload.get("totals") or {}
    visibility = payload.get("candidate_visibility") or {}
    scope = payload.get("scope") or {}
    blockers = payload.get("top_blockers") or payload.get("blockers") or {}
    exact = payload.get("top_exact_rejection_reasons") or payload.get("exact_rejection_reasons") or {}
    candidates = tuple(_candidate_from_payload(row) for row in payload.get("near_misses", [])[:25])
    resolved = resolve_selected_count(
        explicit_selected_count=selected_count,
        universe_metadata=universe_metadata,
        universe_file=universe_file,
        payload=payload,
    )
    return PlannerInput(
        selected_count=resolved["selected_count_effective"],
        selected_count_source=resolved["selected_count_source"],
        selected_count_diagnostic_value=resolved["selected_count_diagnostic_value"],
        readiness_ready=bool(payload.get("readiness_ready", True)),
        readiness_coverage=float(payload.get("readiness_coverage") or 1.0),
        universe_file=str(payload.get("universe_file") or scope.get("universe_file") or _DEFAULT_UNIVERSE),
        product_policy=str(payload.get("product_policy") or scope.get("product_policy") or _DEFAULT_POLICY),
        period=str(payload.get("period") or scope.get("period") or _DEFAULT_PERIOD),
        windows=int(totals.get("windows") or payload.get("windows") or 0),
        clusters=int(totals.get("clusters") or payload.get("clusters") or 0),
        accepted=int(totals.get("accepted") or payload.get("accepted") or 0),
        rejected=int(totals.get("rejected") or payload.get("rejected") or 0),
        persisted_candidates=int(visibility.get("persisted_candidates") or payload.get("persisted_candidates") or 0),
        blockers=dict(blockers),
        exact_rejection_reasons=dict(exact),
        candidates=candidates,
        prohibited_repeats=tuple(str(item) for item in payload.get("prohibited_repeats") or ()),
        context_filtering=_context_filtering(payload.get("context_filtering")),
        execution_contract_integrity=payload.get("execution_contract_integrity"),
        source=source,
    )


def render_markdown(plan: PlannerOutput) -> str:
    lines = [
        "# Intraday Research Next Plan",
        "",
        f"Generated: {plan.generated_at}",
        f"Decision: `{plan.decision}`",
        "",
        "## Rationale",
    ]
    lines.extend(f"- {item}" for item in plan.rationale)
    lines.append("")
    lines.append("## Safety")
    for key, value in plan.safety.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    lines.append("## Scope Controls")
    lines.append(f"- selected_count_effective: `{plan.input_summary['selected_count_effective']}`")
    lines.append(f"- selected_count_source: `{plan.input_summary['selected_count_source']}`")
    lines.append(f"- recommended_limit: `{plan.recommended_limit}`")
    lines.append("- Do not run readiness or waves without explicit `--limit "
                 f"{plan.recommended_limit}`.")
    lines.append("")
    lines.append("## Recommended waves")
    if not plan.waves:
        lines.append("No new waves recommended before the listed actions are completed.")
    for wave in plan.waves:
        lines.extend(
            [
                f"### {wave.priority}. {wave.name}",
                f"- timeframe: `{wave.timeframe}`",
                f"- window_sizes: `{_csv(wave.window_sizes)}`",
                f"- forward_bars: `{_csv(wave.forward_bars)}`",
                f"- max_total_windows: `{wave.max_total_windows}`",
                f"- max_windows_per_symbol: `{wave.max_windows_per_symbol}`",
                f"- requires_cache_warmup: `{wave.requires_cache_warmup}`",
                f"- signatures: `{', '.join(wave.signatures)}`",
                f"- recommended_limit: `{plan.recommended_limit}`",
                f"- hypothesis: {wave.hypothesis}",
                "",
            ]
        )
    if plan.blocked_waves:
        lines.append("## Blocked waves")
        for blocked in plan.blocked_waves:
            lines.append(f"- {blocked.name}: `{blocked.reason}` `{blocked.signature}`")
        lines.append("")
    if plan.blocked_candidates:
        lines.append("## Blocked candidates")
        for candidate in plan.blocked_candidates:
            lines.append(
                f"- {candidate.get('pattern_key')}: `{candidate.get('reason')}` "
                f"`{candidate.get('metric')}`={candidate.get('value')!r} threshold={candidate.get('threshold')!r}"
            )
        lines.append("")
    lines.append("## Confirmation gate")
    lines.append(f"- passed: `{plan.confirmation_gate.get('passed')}`")
    lines.append(f"- hard_blockers: `{len(plan.confirmation_gate.get('hard_blockers') or [])}`")
    lines.append("")
    contract = plan.execution_contract_integrity
    if contract.get("available"):
        lines.append("## Execution Contract Integrity")
        lines.append(f"- passed: `{contract.get('passed')}`")
        lines.append(f"- material_mismatches: `{len(contract.get('material_mismatches') or [])}`")
        lines.append(f"- non_material_mismatches: `{len(contract.get('non_material_mismatches') or [])}`")
        lines.append("")
    if plan.vwap_context.get("available"):
        lines.append("## VWAP context")
        lines.append(f"- symbols_analyzed: `{plan.vwap_context.get('symbols_analyzed')}`")
        lines.append(f"- bars_analyzed: `{plan.vwap_context.get('bars_analyzed')}`")
        lines.append(f"- recommended_waves: `{', '.join(plan.vwap_context.get('recommended_waves') or [])}`")
        lines.append("")
    if plan.context_filtering:
        lines.append("## Context filtering")
        for key in ("session_filter", "cost_filter", "max_execution_cost_r"):
            lines.append(f"- {key}: `{plan.context_filtering.get(key)}`")
        lines.append("")
    lines.append("## Actions")
    lines.extend(f"- {item}" for item in plan.actions)
    return "\n".join(lines).rstrip() + "\n"


def _candidate_from_payload(row: dict[str, Any]) -> CandidateSignal:
    return CandidateSignal(
        pattern_key=str(row.get("pattern_key") or row.get("name") or "unknown"),
        run_id=_optional_int(row.get("run_id")),
        side=str(row.get("side") or "") or None,
        expected_side=str(row.get("expected_side") or "") or None,
        side_matches_hypothesis=_optional_bool(row.get("side_matches_hypothesis")),
        hypothesis_rejection_reason=str(row.get("hypothesis_rejection_reason") or "") or None,
        expectancy_r=float(row.get("expectancy_r") or row.get("best_expectancy_r") or 0.0),
        profit_factor=float(row.get("profit_factor") or row.get("best_profit_factor") or 0.0),
        oos_expectancy_r=float(row.get("oos_expectancy_r") or row.get("out_of_sample_expectancy_r") or 0.0),
        oos_profit_factor=float(row.get("oos_profit_factor") or row.get("out_of_sample_profit_factor") or 0.0),
        symbol_count=int(row.get("symbol_count") or row.get("symbols") or 0),
        sample_count=int(row.get("sample_count") or row.get("samples") or 0),
        max_drawdown_r=float(row.get("max_drawdown_r") or row.get("drawdown_r") or 0.0),
        market_replay=str(row.get("market_replay") or "") or None,
        cost_x2_result=str(row.get("cost_x2_result") or "") or None,
        fdr_result=str(row.get("fdr_result") or "") or None,
        wrc_result=str(row.get("wrc_result") or "") or None,
        spa_result=str(row.get("spa_result") or "") or None,
        failure_taxonomy=tuple(str(item) for item in row.get("failure_taxonomy") or ()),
        rejection_reasons=tuple(str(item) for item in row.get("rejection_reasons") or row.get("reasons") or ()),
    )


def _execution_contract_integrity(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "available": False,
            "passed": True,
            "material_mismatches": [],
            "non_material_mismatches": [],
            "requested_vs_actual_mismatches": [],
        }
    material = list(payload.get("material_mismatches") or [])
    non_material = list(payload.get("non_material_mismatches") or [])
    return {
        **payload,
        "available": True,
        "passed": bool(payload.get("passed", not material)),
        "material_mismatches": material,
        "non_material_mismatches": non_material,
        "requested_vs_actual_mismatches": list(payload.get("requested_vs_actual_mismatches") or [*material, *non_material]),
    }


def resolve_selected_count(
    *,
    explicit_selected_count: int | None = None,
    universe_metadata: str | Path | None = None,
    universe_file: str | Path | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    diagnostic_value = _diagnostic_selected_count(payload)
    if explicit_selected_count is not None:
        return _selected_count_result(explicit_selected_count, "explicit", diagnostic_value)
    if universe_metadata:
        metadata_count = _selected_count_from_universe_metadata(universe_metadata)
        if metadata_count is not None:
            return _selected_count_result(metadata_count, "universe_metadata", diagnostic_value)
    if universe_file:
        file_count = _selected_count_from_universe_file(universe_file)
        if file_count is not None:
            return _selected_count_result(file_count, "universe_file", diagnostic_value)
    if diagnostic_value is not None:
        return _selected_count_result(diagnostic_value, "diagnostic_json", diagnostic_value)
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    scope_value = _optional_int(scope.get("selected_count"))
    if scope_value is not None:
        return _selected_count_result(scope_value, "diagnostic_scope", diagnostic_value)
    return _selected_count_result(0, "not_available", diagnostic_value)


def filter_prohibited_waves(
    waves: Iterable[ResearchWaveSpec], prohibited_repeats: Iterable[str]
) -> tuple[tuple[ResearchWaveSpec, ...], tuple[BlockedWave, ...]]:
    prohibited = {normalize_wave_signature(item) for item in prohibited_repeats if str(item).strip()}
    allowed: list[ResearchWaveSpec] = []
    blocked: list[BlockedWave] = []
    for wave in waves:
        blocked_signature = next(
            (signature for signature in wave.signatures if normalize_wave_signature(signature) in prohibited),
            None,
        )
        if blocked_signature is None:
            legacy_overlap = bool(
                wave.vwap_condition
                and any(
                    normalize_wave_signature(signature) in prohibited
                    for signature in _legacy_wave_signatures(wave)
                )
            )
            allowed.append(replace(wave, legacy_overlap=legacy_overlap) if legacy_overlap else wave)
        else:
            blocked.append(
                BlockedWave(
                    name=wave.name,
                    reason="prohibited_repeat",
                    signature=blocked_signature,
                    wave=wave,
                )
            )
    return tuple(allowed), tuple(blocked)


def _confirmation_hard_blockers(candidate: CandidateSignal) -> tuple[dict[str, Any], ...]:
    blockers: list[dict[str, Any]] = []

    def add(reason: str, metric: str, value: Any, threshold: Any) -> None:
        blockers.append(
            {
                "pattern_key": candidate.pattern_key,
                "reason": reason,
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "run_id": candidate.run_id,
                "side": candidate.side,
                "expected_side": candidate.expected_side,
                "side_matches_hypothesis": candidate.side_matches_hypothesis,
            }
        )

    if candidate.max_drawdown_r > 12:
        add("drawdown_excessive_for_confirmation", "max_drawdown_r", candidate.max_drawdown_r, 12)
    replay = (candidate.market_replay or "").strip().lower()
    if replay == "failed":
        add("market_replay_failed", "market_replay", candidate.market_replay, "passed")
    elif replay == "not_available":
        add("market_replay_not_available", "market_replay", candidate.market_replay, "available_positive")
    if _has_negative_market_replay(candidate.rejection_reasons):
        add("market_replay_negative_expectancy", "market_replay_expectancy_r", _market_replay_reason(candidate), 0)
    if candidate.side_matches_hypothesis is False:
        add("side_mismatch", "side_matches_hypothesis", False, True)
    if candidate.oos_profit_factor <= 1.2:
        add("oos_profit_factor_too_low", "out_of_sample_profit_factor", candidate.oos_profit_factor, "> 1.2")
    if candidate.oos_expectancy_r <= 0:
        add("oos_expectancy_not_positive", "out_of_sample_expectancy_r", candidate.oos_expectancy_r, "> 0")
    if _is_failed(candidate.cost_x2_result):
        add("cost_x2_failed", "cost_x2_result", candidate.cost_x2_result, "passed")
    for metric, value in (
        ("fdr_result", candidate.fdr_result),
        ("wrc_result", candidate.wrc_result),
        ("spa_result", candidate.spa_result),
    ):
        if _is_failed(value):
            add(f"{metric.removesuffix('_result')}_failed", metric, value, "passed")
    if _has_severe_concentration_risk(candidate):
        add("concentration_risk_severe", "concentration_risk", "severe", "not_severe")
    return tuple(blockers)


def _is_failed(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"failed", "fail", "false", "rejected"}


def _has_negative_market_replay(reasons: Iterable[str]) -> bool:
    return any("market replay" in item.lower() and "-" in item for item in reasons)


def _market_replay_reason(candidate: CandidateSignal) -> str | None:
    return next((item for item in candidate.rejection_reasons if "market replay" in item.lower()), None)


def _has_severe_concentration_risk(candidate: CandidateSignal) -> bool:
    text = " ".join((*candidate.failure_taxonomy, *candidate.rejection_reasons)).lower()
    return "concentration" in text and "severe" in text


def _legacy_wave_signatures(wave: ResearchWaveSpec) -> tuple[str, ...]:
    if wave.session_filter != "none" or wave.cost_filter != "none":
        return ()
    return tuple(
        f"{wave.timeframe} W{window_size} {_csv(wave.forward_bars)}"
        for window_size in wave.window_sizes
    )


def normalize_wave_signature(value: str) -> str:
    return " ".join(str(value).replace(",", ",").split()).lower()


def load_vwap_summary(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != "tradeo.intraday_vwap_research.v1":
        return None
    if payload.get("status") != "OK":
        return None
    return payload


def _waves_from_vwap_summary(summary: dict[str, Any] | None) -> list[ResearchWaveSpec]:
    if not summary:
        return []
    waves: list[ResearchWaveSpec] = []
    for index, row in enumerate(summary.get("recommended_next_waves") or (), start=1):
        try:
            timeframe = str(row["timeframe"])
            window_size = int(row["window_size"])
            forward_bars = tuple(int(item) for item in row["forward_bars"])
            name = str(row["name"])
        except (KeyError, TypeError, ValueError):
            continue
        waves.append(
            ResearchWaveSpec(
                name=name,
                timeframe=timeframe,
                window_sizes=(window_size,),
                forward_bars=forward_bars,
                max_total_windows=120_000 if timeframe != "1h" else 80_000,
                max_windows_per_symbol=1_200 if timeframe != "1h" else 800,
                hypothesis=str(row.get("reason") or row.get("vwap_condition") or "VWAP-aware search-space proposal."),
                priority=index,
                requires_cache_warmup=timeframe != "30m",
                vwap_condition=_vwap_condition_from_summary_row(row),
                session_filter=str(row.get("session_filter") or "none"),
                cost_filter=str(row.get("cost_filter") or "none"),
                max_execution_cost_r=_optional_float(row.get("max_execution_cost_r")),
                legacy_overlap=bool(row.get("legacy_overlap")),
            )
        )
    return waves


def _vwap_condition_from_summary_row(row: dict[str, Any]) -> str | None:
    explicit = str(row.get("research_vwap_condition") or "").strip()
    if explicit:
        return explicit
    raw = str(row.get("vwap_condition") or "").strip()
    if raw in _RESEARCH_VWAP_CONDITIONS:
        return raw
    return _VWAP_CONDITION_BY_WAVE_NAME.get(str(row.get("name") or ""))


def _vwap_context(summary: dict[str, Any] | None, allowed_waves: Iterable[ResearchWaveSpec]) -> dict[str, Any]:
    if not summary:
        return {"available": False, "symbols_analyzed": 0, "bars_analyzed": 0, "recommended_waves": []}
    universe = summary.get("universe") or {}
    vwap_summary = summary.get("vwap_summary") or {}
    vwap_names = {str(row.get("name")) for row in summary.get("recommended_next_waves") or []}
    recommended = [wave.name for wave in allowed_waves if wave.name in vwap_names]
    return {
        "available": True,
        "symbols_analyzed": int(universe.get("symbols_analyzed") or 0),
        "bars_analyzed": int(vwap_summary.get("bars_analyzed") or 0),
        "recommended_waves": recommended,
    }


def _context_filtering(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    return {
        "session_filter": str(payload.get("session_filter") or "none").strip().lower() or "none",
        "cost_filter": str(payload.get("cost_filter") or "none").strip().lower() or "none",
        "max_execution_cost_r": _optional_float(payload.get("max_execution_cost_r")),
    }


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _optional_float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _csv(values: Iterable[int]) -> str:
    return ",".join(str(value) for value in values)


def _diagnostic_selected_count(payload: dict[str, Any]) -> int | None:
    if "input_summary" in payload and isinstance(payload.get("input_summary"), dict):
        parsed = _optional_int(payload["input_summary"].get("selected_count"))
        if parsed is not None:
            return parsed
    parsed = _optional_int(payload.get("selected_count"))
    if parsed is not None:
        return parsed
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    return _optional_int(scope.get("selected_count"))


def _selected_count_result(value: int, source: str, diagnostic_value: int | None) -> dict[str, Any]:
    return {
        "selected_count_effective": max(0, int(value)),
        "selected_count_source": source,
        "selected_count_diagnostic_value": diagnostic_value,
    }


def _selected_count_from_universe_metadata(path: str | Path) -> int | None:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return _optional_int(payload.get("selected_count"))


def _selected_count_from_universe_file(path: str | Path) -> int | None:
    try:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return None
    if not rows:
        return 0
    columns = rows[0].keys()
    if "selected" in columns:
        return sum(1 for row in rows if str(row.get("selected", "")).strip().lower() in {"true", "1", "yes", "y"})
    if "status" in columns:
        return sum(1 for row in rows if str(row.get("status", "")).strip().lower() == "selected")
    return len(rows)


def _top_items(values: dict[str, int], *, limit: int) -> list[tuple[str, int]]:
    return sorted(((str(key), int(value)) for key, value in values.items()), key=lambda item: (-item[1], item[0]))[:limit]


def _normalized_counter(values: dict[str, int]) -> dict[str, int]:
    return {str(key).lower(): int(value) for key, value in values.items()}


def _has_any(values: dict[str, int], *needles: str) -> bool:
    return any(any(needle in key for needle in needles) and count > 0 for key, count in values.items())


def _dedupe_waves(waves: list[ResearchWaveSpec]) -> list[ResearchWaveSpec]:
    seen: set[tuple[str, tuple[int, ...], tuple[int, ...]]] = set()
    out: list[ResearchWaveSpec] = []
    for wave in sorted(waves, key=lambda item: item.priority):
        key = (wave.timeframe, wave.window_sizes, wave.forward_bars)
        if key in seen:
            continue
        seen.add(key)
        out.append(wave)
    return out
