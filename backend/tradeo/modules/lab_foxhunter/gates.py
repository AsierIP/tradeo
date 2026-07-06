from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ProbeStatus = Literal["proposed_lab_paper_probe", "active_lab_paper_probe", "stopped"]
GateStatus = Literal["PASS", "BLOCK"]
LiveDecision = Literal["HARD_NO", "ELIGIBLE_FOR_HUMAN_REVIEW"]


@dataclass(frozen=True, slots=True)
class GateDecision:
    gate: str
    status: GateStatus
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)
    orders_allowed: bool = False
    paper_orders_generated: bool = False
    live_orders_generated: bool = False
    previews_generated: bool = False
    signals_generated: bool = False

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "status": self.status,
            "passed": self.passed,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "details": self.details,
            "orders_allowed": self.orders_allowed,
            "paper_orders_generated": self.paper_orders_generated,
            "live_orders_generated": self.live_orders_generated,
            "previews_generated": self.previews_generated,
            "signals_generated": self.signals_generated,
        }


@dataclass(frozen=True, slots=True)
class LabPaperProbeManifest:
    probe_id: str
    strategy_source_id: str
    status: ProbeStatus
    rationale: str
    max_initial_paper_trades: int
    success_threshold: int
    disabled_by_default: bool = True
    net_expectancy_required: bool = True
    direction_approved: bool = False
    lookahead_free: bool = True
    leakage_free: bool = True
    product_policy_ok: bool = True
    data_quality_ok: bool = True
    documented_hypothesis: bool = True
    operational_risk_bounded: bool = True
    fatal_failure_reason: bool = False
    live_risk: bool = False
    reproducible: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LabPaperProbeManifest":
        return cls(
            probe_id=str(raw.get("probe_id", "")),
            strategy_source_id=str(raw.get("strategy_source_id", "")),
            status=raw.get("status", ""),
            rationale=str(raw.get("rationale", "")),
            max_initial_paper_trades=int(raw.get("max_initial_paper_trades", 0)),
            success_threshold=int(raw.get("success_threshold", 0)),
            disabled_by_default=bool(raw.get("disabled_by_default", True)),
            net_expectancy_required=bool(raw.get("net_expectancy_required", True)),
            direction_approved=bool(raw.get("direction_approved", False)),
            lookahead_free=bool(raw.get("lookahead_free", True)),
            leakage_free=bool(raw.get("leakage_free", True)),
            product_policy_ok=bool(raw.get("product_policy_ok", True)),
            data_quality_ok=bool(raw.get("data_quality_ok", True)),
            documented_hypothesis=bool(raw.get("documented_hypothesis", True)),
            operational_risk_bounded=bool(raw.get("operational_risk_bounded", True)),
            fatal_failure_reason=bool(raw.get("fatal_failure_reason", False)),
            live_risk=bool(raw.get("live_risk", False)),
            reproducible=bool(raw.get("reproducible", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "strategy_source_id": self.strategy_source_id,
            "status": self.status,
            "rationale": self.rationale,
            "max_initial_paper_trades": self.max_initial_paper_trades,
            "success_threshold": self.success_threshold,
            "disabled_by_default": self.disabled_by_default,
            "net_expectancy_required": self.net_expectancy_required,
            "direction_approved": self.direction_approved,
            "lookahead_free": self.lookahead_free,
            "leakage_free": self.leakage_free,
            "product_policy_ok": self.product_policy_ok,
            "data_quality_ok": self.data_quality_ok,
            "documented_hypothesis": self.documented_hypothesis,
            "operational_risk_bounded": self.operational_risk_bounded,
            "fatal_failure_reason": self.fatal_failure_reason,
            "live_risk": self.live_risk,
            "reproducible": self.reproducible,
        }


def validate_manifest(raw: dict[str, Any]) -> GateDecision:
    blockers: list[str] = []
    manifest = LabPaperProbeManifest.from_dict(raw)
    if not manifest.probe_id:
        blockers.append("probe_id_required")
    if not manifest.strategy_source_id:
        blockers.append("strategy_source_id_required")
    if manifest.status not in {"proposed_lab_paper_probe", "active_lab_paper_probe", "stopped"}:
        blockers.append("status_not_allowed")
    if not manifest.rationale:
        blockers.append("rationale_required")
    if manifest.max_initial_paper_trades <= 0:
        blockers.append("max_initial_paper_trades_required")
    if manifest.success_threshold <= 0:
        blockers.append("success_threshold_required")
    if manifest.success_threshold > manifest.max_initial_paper_trades:
        blockers.append("success_threshold_exceeds_trade_cap")
    if not manifest.disabled_by_default:
        blockers.append("lab_probe_must_be_disabled_by_default")
    return _decision("manifest_schema", blockers, {"manifest": manifest.to_dict()})


def validate_research_to_lab_gate(raw: dict[str, Any]) -> GateDecision:
    manifest = LabPaperProbeManifest.from_dict(raw)
    blockers: list[str] = []
    if validate_manifest(raw).blockers:
        blockers.extend(f"manifest:{name}" for name in validate_manifest(raw).blockers)
    required_true = {
        "lookahead_free": manifest.lookahead_free,
        "leakage_free": manifest.leakage_free,
        "product_policy_ok": manifest.product_policy_ok,
        "data_quality_ok": manifest.data_quality_ok,
        "documented_hypothesis": manifest.documented_hypothesis,
        "operational_risk_bounded": manifest.operational_risk_bounded,
        "reproducible": manifest.reproducible,
        "direction_approved": manifest.direction_approved,
    }
    blockers.extend(name for name, ok in required_true.items() if not ok)
    if manifest.fatal_failure_reason:
        blockers.append("fatal_failure_reason")
    if manifest.live_risk:
        blockers.append("live_risk")
    return _decision(
        "research_to_lab_gate",
        blockers,
        {
            "target_status": "lab_paper_probe",
            "probe_id": manifest.probe_id,
            "execution": "no_order_no_preview_no_signal",
        },
    )


def validate_lab_to_foxhunter_gate(metrics: dict[str, Any]) -> GateDecision:
    blockers: list[str] = []
    if int(metrics.get("paper_trades_count", 0)) < 20:
        blockers.append("min_paper_trades_20_required")
    if int(metrics.get("success_count", 0)) < 12:
        blockers.append("min_successes_12_required")
    if float(metrics.get("expectancy_net", 0.0)) <= 0.0:
        blockers.append("positive_expectancy_required")
    if float(metrics.get("profit_factor", 0.0)) <= 1.15:
        blockers.append("profit_factor_above_1_15_required")
    if float(metrics.get("max_drawdown_pct", 100.0)) > float(
        metrics.get("max_allowed_drawdown_pct", 10.0)
    ):
        blockers.append("max_drawdown_exceeded")
    if int(metrics.get("operational_error_count", 0)) != 0:
        blockers.append("operational_errors_present")
    if int(metrics.get("reconciliation_errors", 0)) != 0:
        blockers.append("reconciliation_errors_present")
    if bool(metrics.get("symbol_or_event_concentration", False)):
        blockers.append("symbol_or_event_concentration")
    if bool(metrics.get("manual_overrides", False)):
        blockers.append("manual_overrides_present")
    if not bool(metrics.get("logs_complete", False)):
        blockers.append("logs_complete_required")
    if not bool(metrics.get("direction_approved", False)):
        blockers.append("direction_approval_required")
    return _decision(
        "lab_to_foxhunter_gate",
        blockers,
        {
            "candidate_decision": (
                "eligible_for_foxhunter_review" if not blockers else "stay_in_lab_or_stop_probe"
            ),
            "metrics": metrics,
        },
    )


def validate_foxhunter_to_live_gate(review: dict[str, Any]) -> GateDecision:
    blockers: list[str] = []
    required_true = {
        "foxhunter_review_passed": bool(review.get("foxhunter_review_passed", False)),
        "risk_review_passed": bool(review.get("risk_review_passed", False)),
        "kill_switch_tested": bool(review.get("kill_switch_tested", False)),
        "max_daily_loss_defined": bool(review.get("max_daily_loss_defined", False)),
        "max_position_value_defined": bool(review.get("max_position_value_defined", False)),
        "max_trades_defined": bool(review.get("max_trades_defined", False)),
        "paper_live_account_separation": bool(
            review.get("paper_live_account_separation", False)
        ),
        "human_review_complete": bool(review.get("human_review_complete", False)),
        "explicit_asier_authorization": bool(
            review.get("explicit_asier_authorization", False)
        ),
        "explicit_direction_authorization": bool(
            review.get("explicit_direction_authorization", False)
        ),
    }
    blockers.extend(name for name, ok in required_true.items() if not ok)
    if bool(review.get("live_armed", False)):
        blockers.append("live_must_not_be_armed_by_gate_check")
    details: dict[str, Any] = {
        "live_decision": "ELIGIBLE_FOR_HUMAN_REVIEW" if not blockers else "HARD_NO",
        "review": review,
    }
    return _decision("foxhunter_to_live_gate", blockers, details)


def _decision(gate: str, blockers: list[str], details: dict[str, Any]) -> GateDecision:
    return GateDecision(
        gate=gate,
        status="BLOCK" if blockers else "PASS",
        blockers=tuple(blockers),
        details=details,
    )
