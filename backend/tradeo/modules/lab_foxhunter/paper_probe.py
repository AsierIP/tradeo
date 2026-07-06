from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from tradeo.modules.lab_foxhunter.gates import (
    REQUIRED_20_TRADE_METRICS,
    REQUIRED_LAB_PROBE_TELEMETRY,
    validate_lab_paper_probe_manifest,
)


ALLOWED_INITIAL_PROBE_IDS = ("LAB-GAP-REV-001", "LAB-GAP-REV-002")
ALLOWED_INITIAL_SOURCES = (
    "GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL",
    "GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0",
)
FORBIDDEN_OPERATIONAL_FAMILIES = ("DSS-PB", "DSS-BO", "DSS-CO", "DSS-CW")


@dataclass(frozen=True, slots=True)
class LabPaperProbeEnvironment:
    explicit_paper_probe_mode: bool
    director_approved: bool
    ibkr_readonly: bool = True
    laboratory_auto_submit_paper_orders: bool = False
    foxhunter_auto_submit_live_orders: bool = False
    live_trading_enabled: bool = False
    live_armed: bool = False
    kill_switch_available: bool = True
    risk_limits_available: bool = True
    broker_submit_enabled: bool = False
    cron_trading_enabled: bool = False
    order_preview_enabled: bool = False
    signal_generation_enabled: bool = False
    max_batch_probes: int = 2
    max_initial_paper_trades_per_probe: int = 20


@dataclass(frozen=True, slots=True)
class LabPaperProbeBatchRequest:
    batch_id: str
    probes: tuple[dict[str, Any], ...]
    requested_by: str = "director"
    phase: str = "supervised_lab_paper_probe"


def build_lab_gap_probe_manifests() -> tuple[dict[str, Any], ...]:
    return (
        _probe_manifest(
            probe_id="LAB-GAP-REV-001",
            source="GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL",
            rationale="Measure real open slippage and fill realism for rejected GAP reversal.",
        ),
        _probe_manifest(
            probe_id="LAB-GAP-REV-002",
            source="GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0",
            rationale="Measure weak-SPY regime behavior for rejected GAP reversal.",
        ),
    )


def prepare_lab_paper_probe_batch(
    request: LabPaperProbeBatchRequest,
    environment: LabPaperProbeEnvironment,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    checked_at = now or datetime.now(timezone.utc)
    blockers: list[str] = []
    warnings: list[str] = []

    blockers.extend(_environment_blockers(environment))
    if len(request.probes) > environment.max_batch_probes:
        blockers.append("max_two_probes_per_batch")
    if request.phase != "supervised_lab_paper_probe":
        blockers.append("invalid_probe_phase")
    for index, manifest in enumerate(request.probes):
        manifest_decision = validate_lab_paper_probe_manifest(manifest)
        blockers.extend(f"probe_{index}_{item}" for item in manifest_decision.blockers)
        probe_id = str(manifest.get("probe_id") or "")
        source = str(manifest.get("strategy_source_id") or "")
        if probe_id not in ALLOWED_INITIAL_PROBE_IDS:
            blockers.append(f"probe_{index}_not_in_initial_allowlist")
        if source not in ALLOWED_INITIAL_SOURCES:
            blockers.append(f"probe_{index}_source_not_allowed")
        if any(source.startswith(prefix) for prefix in FORBIDDEN_OPERATIONAL_FAMILIES):
            blockers.append(f"probe_{index}_forbidden_daily_family")
        if int(manifest.get("max_initial_paper_trades") or 0) > 20:
            blockers.append(f"probe_{index}_trade_cap_above_20")
        if manifest.get("disabled_by_default") is not True:
            blockers.append(f"probe_{index}_must_remain_disabled_by_default")
    if len({str(item.get("probe_id") or "") for item in request.probes}) != len(request.probes):
        blockers.append("duplicate_probe_id")
    if environment.ibkr_readonly:
        warnings.append("ibkr_readonly_blocks_broker_submission")

    ready = not blockers
    return {
        "schema": "tradeo.lab_paper_probe_batch.v1",
        "batch_id": request.batch_id,
        "checked_at": checked_at.isoformat(),
        "phase": request.phase,
        "status": "READY_FOR_SUPERVISED_PAPER_PROBE" if ready else "BLOCKED",
        "ready": ready,
        "blockers": blockers,
        "warnings": warnings,
        "probe_ids": [item["probe_id"] for item in request.probes],
        "max_batch_probes": environment.max_batch_probes,
        "max_initial_paper_trades_per_probe": environment.max_initial_paper_trades_per_probe,
        "paper_only": True,
        "supervised_only": True,
        "auto_submit_allowed": False,
        "broker_submit_enabled": False,
        "paper_orders_sent": False,
        "live_orders_sent": False,
        "order_previews_generated": False,
        "signals_generated": False,
        "ibkr_operational_use": False,
        "foxhunter_candidates_created": 0,
        "live_candidates_created": 0,
        "candidate_decision_allowed": ("stay_in_lab", "stop_probe"),
        "foxhunter_promotion_allowed": False,
        "live_promotion_allowed": False,
        "telemetry_required": list(REQUIRED_LAB_PROBE_TELEMETRY),
        "milestone_metrics_required": list(REQUIRED_20_TRADE_METRICS),
    }


def render_lab_paper_probe_batch_markdown(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# LAB Paper Probe 002 Batch",
            "",
            f"- batch_id: `{report['batch_id']}`",
            f"- status: `{report['status']}`",
            f"- ready: `{report['ready']}`",
            f"- probe_ids: `{report['probe_ids']}`",
            f"- paper_orders_sent: `{report['paper_orders_sent']}`",
            f"- live_orders_sent: `{report['live_orders_sent']}`",
            f"- order_previews_generated: `{report['order_previews_generated']}`",
            f"- signals_generated: `{report['signals_generated']}`",
            f"- foxhunter_promotion_allowed: `{report['foxhunter_promotion_allowed']}`",
            f"- blockers: `{report['blockers']}`",
            f"- warnings: `{report['warnings']}`",
            "",
            "This artifact is a supervised Lab paper-probe batch contract. It does not submit",
            "broker orders, does not generate operational signals, and does not promote to",
            "FoxHunter or live.",
            "",
        ]
    )


def _environment_blockers(environment: LabPaperProbeEnvironment) -> list[str]:
    blockers: list[str] = []
    if not environment.explicit_paper_probe_mode:
        blockers.append("explicit_paper_probe_mode_required")
    if not environment.director_approved:
        blockers.append("director_approval_required")
    if environment.laboratory_auto_submit_paper_orders:
        blockers.append("global_lab_auto_submit_must_remain_disabled")
    if environment.foxhunter_auto_submit_live_orders:
        blockers.append("foxhunter_live_auto_submit_must_be_disabled")
    if environment.live_trading_enabled:
        blockers.append("live_trading_enabled")
    if environment.live_armed:
        blockers.append("live_armed")
    if not environment.kill_switch_available:
        blockers.append("kill_switch_required")
    if not environment.risk_limits_available:
        blockers.append("risk_limits_required")
    if environment.broker_submit_enabled:
        blockers.append("broker_submit_not_enabled_by_batch_preparation")
    if environment.cron_trading_enabled:
        blockers.append("cron_trading_enabled")
    if environment.order_preview_enabled:
        blockers.append("order_preview_enabled")
    if environment.signal_generation_enabled:
        blockers.append("signal_generation_enabled")
    return blockers


def _probe_manifest(*, probe_id: str, source: str, rationale: str) -> dict[str, Any]:
    return {
        "schema": "tradeo.lab_paper_probe_manifest.v1",
        "taxonomy": "lab_paper_probe",
        "probe_id": probe_id,
        "strategy_source_id": source,
        "status": "proposed_lab_paper_probe",
        "rationale": rationale,
        "max_initial_paper_trades": 20,
        "success_threshold": 12,
        "extra_requirements": ["net_expectancy_after_costs_positive"],
        "disabled_by_default": True,
        "execution_enabled": False,
        "generate_signals": False,
        "generate_previews": False,
        "live_allowed": False,
        "allowed_outputs": ["manifest_validation", "gate_report"],
        "telemetry_required": list(REQUIRED_LAB_PROBE_TELEMETRY),
        "milestone_metrics_required": list(REQUIRED_20_TRADE_METRICS),
    }
