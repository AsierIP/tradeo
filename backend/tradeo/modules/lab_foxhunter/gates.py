from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CandidateDecision(StrEnum):
    STAY_IN_LAB = "stay_in_lab"
    STOP_PROBE = "stop_probe"
    ELIGIBLE_FOR_FOXHUNTER_REVIEW = "eligible_for_foxhunter_review"


class Taxonomy(StrEnum):
    RESEARCH_OBSERVATION = "research_observation"
    LAB_PAPER_PROBE = "lab_paper_probe"
    FOXHUNTER_CANDIDATE = "foxhunter_candidate"
    LIVE_CANDIDATE = "live_candidate"


@dataclass(frozen=True, slots=True)
class GateDecision:
    gate_name: str
    allowed: bool
    decision: str
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    outputs_generated: tuple[str, ...] = ()

    @property
    def no_execution_outputs(self) -> bool:
        return not any(
            output in {"paper_order", "live_order", "order_preview", "signal"}
            for output in self.outputs_generated
        )


@dataclass(frozen=True, slots=True)
class ResearchLabEvidence:
    no_lookahead: bool
    no_leakage: bool
    product_policy_ok: bool
    data_quality_ok: bool
    pattern_documented: bool
    hypothesis_clear: bool
    operational_risk_bounded: bool
    failure_reason_fatal: bool
    security_ok: bool
    director_approved: bool
    logs_available: bool = True
    reproducible: bool = True
    live_risk: bool = False


@dataclass(frozen=True, slots=True)
class LabProbeMetrics:
    paper_trades_count: int
    success_count: int
    expectancy_net: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_limit: float
    avg_slippage_bps: float
    slippage_destructive: bool
    fill_rate: float
    rejected_orders: int
    operational_errors: int
    reconciliation_errors: int
    top_symbols_events_concentrated: bool
    last_n_trades_degraded: bool
    logs_complete: bool
    manual_overrides: int
    director_approved: bool
    avg_win: float | None = None
    avg_loss: float | None = None
    worst_streak: int | None = None


@dataclass(frozen=True, slots=True)
class LiveAuthorization:
    foxhunter_gate_passed: bool
    risk_review_passed: bool
    kill_switch_tested: bool
    live_armed_controlled: bool
    max_daily_loss_configured: bool
    max_position_value_configured: bool
    max_trades_configured: bool
    paper_live_account_separation: bool
    human_review_complete: bool
    explicit_asier_or_director_authorization: bool


@dataclass(frozen=True, slots=True)
class LabPaperProbeManifest:
    probe_id: str
    strategy_source_id: str
    status: str
    rationale: str
    max_initial_paper_trades: int
    success_threshold: int
    disabled_by_default: bool
    extra_requirements: tuple[str, ...] = ()
    taxonomy: str = Taxonomy.LAB_PAPER_PROBE.value
    execution_enabled: bool = False
    generate_signals: bool = False
    generate_previews: bool = False
    live_allowed: bool = False
    allowed_outputs: tuple[str, ...] = field(default_factory=lambda: ("manifest_validation",))


REQUIRED_LAB_PROBE_TELEMETRY = (
    "probe_id",
    "strategy_source_id",
    "symbol",
    "decision_time",
    "intended_side",
    "intended_entry_type",
    "theoretical_open",
    "submitted_paper_order",
    "paper_fill_price",
    "fill_latency_ms",
    "bid",
    "ask",
    "last",
    "spread_bps",
    "slippage_bps",
    "exit_price",
    "pnl_pct",
    "pnl_after_costs",
    "success_flag",
    "reason_success_failure",
    "mfe",
    "mae",
    "ibkr_state",
    "kill_switch_state",
    "risk_limits_state",
    "reconciliation_status",
)

REQUIRED_20_TRADE_METRICS = (
    "paper_trades_count",
    "success_count",
    "winrate",
    "expectancy_net",
    "profit_factor",
    "avg_win",
    "avg_loss",
    "max_drawdown",
    "worst_streak",
    "avg_slippage_bps",
    "fill_rate",
    "rejected_orders",
    "operational_errors",
    "reconciliation_errors",
    "candidate_decision",
)


def research_to_lab_gate(evidence: ResearchLabEvidence) -> GateDecision:
    blockers: list[str] = []
    if not evidence.no_lookahead:
        blockers.append("lookahead")
    if not evidence.no_leakage:
        blockers.append("leakage")
    if not evidence.product_policy_ok:
        blockers.append("product_policy")
    if not evidence.data_quality_ok:
        blockers.append("data_quality")
    if not evidence.pattern_documented:
        blockers.append("pattern_not_documented")
    if not evidence.hypothesis_clear:
        blockers.append("hypothesis_not_clear")
    if not evidence.operational_risk_bounded:
        blockers.append("operational_risk_unbounded")
    if evidence.failure_reason_fatal:
        blockers.append("fatal_failure_reason")
    if not evidence.security_ok:
        blockers.append("security_violation")
    if not evidence.director_approved:
        blockers.append("director_approval_required")
    if not evidence.logs_available:
        blockers.append("missing_logs")
    if not evidence.reproducible:
        blockers.append("not_reproducible")
    if evidence.live_risk:
        blockers.append("live_risk")
    return GateDecision(
        gate_name="research_to_lab_gate",
        allowed=not blockers,
        decision=(
            Taxonomy.LAB_PAPER_PROBE.value
            if not blockers
            else Taxonomy.RESEARCH_OBSERVATION.value
        ),
        blockers=tuple(blockers),
    )


def lab_to_foxhunter_gate(metrics: LabProbeMetrics) -> GateDecision:
    blockers: list[str] = []
    warnings: list[str] = []
    if metrics.paper_trades_count < 20:
        blockers.append("min_paper_trades_20_required")
    if metrics.success_count < 12:
        blockers.append("min_successes_12_required")
    if metrics.expectancy_net <= 0:
        blockers.append("positive_net_expectancy_required")
    if metrics.profit_factor <= 1.15:
        blockers.append("profit_factor_above_1_15_required")
    elif metrics.profit_factor < 1.2:
        warnings.append("profit_factor_below_preferred_1_2")
    if metrics.slippage_destructive:
        blockers.append("cost_slippage_destructive")
    if metrics.max_drawdown > metrics.max_drawdown_limit:
        blockers.append("max_drawdown_limit_exceeded")
    if metrics.operational_errors != 0:
        blockers.append("operational_errors")
    if metrics.reconciliation_errors != 0:
        blockers.append("reconciliation_errors")
    if metrics.top_symbols_events_concentrated:
        blockers.append("symbol_event_concentration")
    if metrics.last_n_trades_degraded:
        blockers.append("last_n_trades_degraded")
    if not metrics.logs_complete:
        blockers.append("logs_incomplete")
    if metrics.manual_overrides != 0:
        blockers.append("manual_overrides")
    if not metrics.director_approved:
        blockers.append("director_approval_required")
    return GateDecision(
        gate_name="lab_to_foxhunter_gate",
        allowed=not blockers,
        decision=(
            CandidateDecision.ELIGIBLE_FOR_FOXHUNTER_REVIEW.value
            if not blockers
            else CandidateDecision.STAY_IN_LAB.value
        ),
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )


def foxhunter_to_live_gate(authorization: LiveAuthorization) -> GateDecision:
    blockers: list[str] = []
    checks = {
        "foxhunter_gate_passed": authorization.foxhunter_gate_passed,
        "risk_review_passed": authorization.risk_review_passed,
        "kill_switch_tested": authorization.kill_switch_tested,
        "live_armed_controlled": authorization.live_armed_controlled,
        "max_daily_loss_configured": authorization.max_daily_loss_configured,
        "max_position_value_configured": authorization.max_position_value_configured,
        "max_trades_configured": authorization.max_trades_configured,
        "paper_live_account_separation": authorization.paper_live_account_separation,
        "human_review_complete": authorization.human_review_complete,
        "explicit_asier_or_director_authorization": (
            authorization.explicit_asier_or_director_authorization
        ),
    }
    blockers.extend(key for key, ok in checks.items() if not ok)
    return GateDecision(
        gate_name="foxhunter_to_live_gate",
        allowed=not blockers,
        decision=(
            Taxonomy.LIVE_CANDIDATE.value
            if not blockers
            else Taxonomy.FOXHUNTER_CANDIDATE.value
        ),
        blockers=tuple(blockers),
    )


def validate_lab_paper_probe_manifest(manifest: dict[str, Any]) -> GateDecision:
    blockers: list[str] = []
    required = {
        "schema",
        "taxonomy",
        "probe_id",
        "strategy_source_id",
        "status",
        "rationale",
        "max_initial_paper_trades",
        "success_threshold",
        "disabled_by_default",
        "execution_enabled",
        "generate_signals",
        "generate_previews",
        "live_allowed",
        "allowed_outputs",
        "telemetry_required",
        "milestone_metrics_required",
    }
    missing = sorted(required - set(manifest))
    blockers.extend(f"missing_{field}" for field in missing)
    if manifest.get("taxonomy") != Taxonomy.LAB_PAPER_PROBE.value:
        blockers.append("taxonomy_must_be_lab_paper_probe")
    if manifest.get("status") not in {"proposed_lab_paper_probe", "disabled_lab_paper_probe"}:
        blockers.append("status_not_lab_probe")
    if manifest.get("disabled_by_default") is not True:
        blockers.append("disabled_by_default_required")
    if manifest.get("execution_enabled") is not False:
        blockers.append("execution_must_be_disabled")
    if manifest.get("generate_signals") is not False:
        blockers.append("signals_must_be_disabled")
    if manifest.get("generate_previews") is not False:
        blockers.append("previews_must_be_disabled")
    if manifest.get("live_allowed") is not False:
        blockers.append("live_must_be_disabled")
    if int(manifest.get("max_initial_paper_trades") or 0) > 20:
        blockers.append("max_initial_paper_trades_capped_at_20")
    if int(manifest.get("success_threshold") or 0) < 12:
        blockers.append("success_threshold_min_12")
    allowed_outputs = set(manifest.get("allowed_outputs") or ())
    forbidden_outputs = allowed_outputs & {"paper_order", "live_order", "order_preview", "signal"}
    blockers.extend(f"forbidden_output_{item}" for item in sorted(forbidden_outputs))
    telemetry = set(manifest.get("telemetry_required") or ())
    missing_telemetry = sorted(set(REQUIRED_LAB_PROBE_TELEMETRY) - telemetry)
    blockers.extend(f"missing_telemetry_{item}" for item in missing_telemetry)
    metrics = set(manifest.get("milestone_metrics_required") or ())
    missing_metrics = sorted(set(REQUIRED_20_TRADE_METRICS) - metrics)
    blockers.extend(f"missing_metric_{item}" for item in missing_metrics)
    return GateDecision(
        gate_name="lab_paper_probe_manifest_schema",
        allowed=not blockers,
        decision=Taxonomy.LAB_PAPER_PROBE.value if not blockers else "invalid_manifest",
        blockers=tuple(blockers),
    )
