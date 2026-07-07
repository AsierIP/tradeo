from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo
import hashlib
import json
import re

SCHEMA_VERSION = "tradeo.postsession_improvement.v1"
DecisionClass = Literal[
    "AUTO_FIX_ALLOWED",
    "DIRECTOR_REVIEW_REQUIRED",
    "NO_CHANGE",
    "BLOCKER_STOP_NEXT_SESSION",
]
FinalDecision = Literal[
    "POSTSESSION_AUTO_FIXES_APPLIED",
    "POSTSESSION_PROPOSALS_READY_FOR_DIRECTOR",
    "POSTSESSION_NO_CHANGE_REQUIRED",
    "POSTSESSION_BLOCK_NEXT_SESSION",
    "POSTSESSION_VALIDATION_FAIL",
    "POSTSESSION_SECURITY_BLOCKER",
    "POSTSESSION_INCONCLUSIVE",
]

SENSITIVE_AREAS = frozenset(
    {
        "trigger_logic",
        "submit",
        "cancel",
        "reconciliation",
        "risk_limits",
        "watchlist_transitions",
        "scheduler",
        "timers",
        "universe_selection",
        "scoring",
        "thresholds",
        "gates",
        "paper_behavior",
        "live_behavior",
    }
)
PROHIBITED_AUTO_FIX_AREAS = SENSITIVE_AREAS | frozenset(
    {
        "order_path",
        "broker_submit",
        "market_data",
        "env_real",
        "session_timing",
    }
)
BLOCKER_KINDS = frozenset(
    {
        "live_risk",
        "extra_order",
        "reconciliation_error",
        "raw_account_id_leak",
        "auto_submit_unauthorized",
        "kill_switch_failure",
        "runtime_corrupt",
        "duplicate_runner",
        "paper_account_mismatch",
        "unreconciled_position",
        "secret_versioned",
    }
)
SAFE_IMPACT_AREAS = frozenset({"safety", "observability", "docs", "research_quality", "ui"})
SECRET_KEY_PARTS = ("secret", "token", "password", "api_key", "private_key", "account")
ACCOUNT_RE = re.compile(r"\b(?:DU|U)\d{5,}\b")


@dataclass(frozen=True, slots=True)
class PostSessionFinding:
    finding_id: str
    title: str
    evidence: str
    severity: int
    recurrence_count: int
    impact_area: str
    confidence: float
    estimated_change_risk: int
    estimated_benefit: int
    component: str
    touched_areas: tuple[str, ...] = ()
    tests_available: bool = False
    change_size: str = "unknown"
    requires_ibkr: bool = False
    affects_env_real: bool = False
    source: str = "session_artifact"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: dict[str, Any], *, source: str) -> "PostSessionFinding":
        finding_id = str(payload.get("finding_id") or payload.get("id") or _stable_id(payload))
        return cls(
            finding_id=finding_id,
            title=str(payload.get("title") or finding_id),
            evidence=str(payload.get("evidence") or payload.get("reason") or ""),
            severity=_clamp_int(payload.get("severity", 0), 0, 5),
            recurrence_count=max(1, _clamp_int(payload.get("recurrence_count", 1), 1, 999)),
            impact_area=str(payload.get("impact_area") or "observability"),
            confidence=_clamp_float(payload.get("confidence", 0.0), 0.0, 1.0),
            estimated_change_risk=_clamp_int(payload.get("estimated_change_risk", 5), 0, 5),
            estimated_benefit=_clamp_int(payload.get("estimated_benefit", 0), 0, 5),
            component=str(payload.get("component") or "unknown"),
            touched_areas=tuple(str(item) for item in payload.get("touched_areas", []) or []),
            tests_available=bool(payload.get("tests_available", False)),
            change_size=str(payload.get("change_size") or "unknown"),
            requires_ibkr=bool(payload.get("requires_ibkr", False)),
            affects_env_real=bool(payload.get("affects_env_real", False)),
            source=source,
            metadata={k: _redact(v) for k, v in payload.items() if k not in {"secret", "token"}},
        )

    @property
    def recurrence_factor(self) -> float:
        if self.recurrence_count >= 3:
            return 2.0
        if self.recurrence_count == 2:
            return 1.5
        return 1.0

    @property
    def improvement_score(self) -> float:
        return (
            float(self.severity) * self.confidence * self.recurrence_factor
            + float(self.estimated_benefit)
            - float(self.estimated_change_risk)
        )


class PostSessionImprovementAgent:
    def __init__(
        self,
        *,
        repo_root: str | Path = ".",
        input_roots: list[str | Path] | None = None,
        runtime_root: str | Path | None = None,
        research_root: str | Path | None = None,
        now: datetime | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runtime_root = Path(runtime_root or self.repo_root / "artifacts/runtime/postsession")
        self.research_root = Path(research_root or self.repo_root / "research/postsession")
        self.input_roots = [
            Path(root)
            for root in (
                input_roots
                or [
                    self.repo_root / "artifacts/runtime",
                    self.repo_root / "research/lab_daily_resource",
                    self.repo_root / "research/daily_swing",
                    self.repo_root / "research/reports",
                ]
            )
        ]
        self.now = now or datetime.now(timezone.utc)

    def run(
        self,
        *,
        session_date: date | None = None,
        findings: list[dict[str, Any]] | None = None,
        require_session_runtime: bool = True,
        allow_rth: bool = False,
        apply_auto_fixes: bool = True,
    ) -> dict[str, Any]:
        session_date = session_date or self.now.date()
        day = session_date.isoformat()
        runtime_day = self.runtime_root / day
        lock_path = runtime_day / "postsession_agent.lock"
        final_path = runtime_day / "postsession_final.json"
        try:
            runtime_day.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return self._write_validation_fail(day, f"runtime_root_unwritable:{type(exc).__name__}")

        if final_path.exists():
            return self._write_inconclusive(day, "duplicate_daily_run_blocked", final_path)
        if lock_path.exists():
            return self._write_inconclusive(day, "duplicate_runner_lock_exists", final_path)
        if not allow_rth and _is_regular_trading_hours(self.now):
            return self._write_inconclusive(day, "regular_trading_hours_block", final_path)
        if require_session_runtime and not self._session_runtime_exists(session_date):
            return self._write_inconclusive(
                day,
                "session_runtime_missing",
                final_path,
                write_final_marker=False,
            )

        lock_path.write_text(self.now.isoformat() + "\n", encoding="utf-8")
        try:
            collected = self._agent_a_collect(session_date, injected_findings=findings)
            failure_analysis = self._agent_b_analyze_failures(collected)
            proposals = self._agent_c_propose(failure_analysis)
            red_team = self._agent_d_red_team(proposals)
            decision = self._agent_e_integrate(
                day,
                collected,
                failure_analysis,
                proposals,
                red_team,
                apply_auto_fixes=apply_auto_fixes,
            )
            self._write_outputs(day, collected, failure_analysis, proposals, red_team, decision)
            return decision
        finally:
            if lock_path.exists():
                lock_path.unlink()

    def _agent_a_collect(
        self,
        session_date: date,
        *,
        injected_findings: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        artifacts = self._collect_artifacts(session_date)
        findings: list[PostSessionFinding] = []
        for item in injected_findings or []:
            findings.append(PostSessionFinding.from_mapping(item, source="injected"))
        for artifact in artifacts:
            findings.extend(self._findings_from_artifact(artifact))

        return {
            "agent": "A_SESSION_DATA_COLLECTOR",
            "session_date": session_date.isoformat(),
            "artifacts_scanned": artifacts,
            "findings": [_finding_to_dict(finding) for finding in findings],
            "runtime_completeness": "present" if artifacts or injected_findings else "missing",
            "trades_fills_cancels_rejects": _rollup_events(artifacts),
            "missing_logs": [] if artifacts or injected_findings else ["no_permitted_session_runtime"],
        }

    def _agent_b_analyze_failures(self, collected: dict[str, Any]) -> dict[str, Any]:
        findings = [
            PostSessionFinding.from_mapping(item, source=str(item.get("source") or "collector"))
            for item in collected.get("findings", [])
        ]
        failure_modes = []
        stop_candidates = []
        for finding in findings:
            mode = {
                "finding_id": finding.finding_id,
                "title": finding.title,
                "severity": finding.severity,
                "recurrence_count": finding.recurrence_count,
                "suspected_root_cause": finding.metadata.get("suspected_root_cause", "insufficient_context"),
                "component": finding.component,
            }
            failure_modes.append(mode)
            if _is_blocker(finding):
                stop_candidates.append(mode)
        return {
            "agent": "B_FAILURE_MODE_ANALYST",
            "top_failure_modes": sorted(
                failure_modes,
                key=lambda item: (item["severity"], item["recurrence_count"]),
                reverse=True,
            ),
            "stop_next_session_candidates": stop_candidates,
            "findings": [_finding_to_dict(finding) for finding in findings],
        }

    def _agent_c_propose(self, failure_analysis: dict[str, Any]) -> dict[str, Any]:
        findings = [
            PostSessionFinding.from_mapping(item, source=str(item.get("source") or "failure_analysis"))
            for item in failure_analysis.get("findings", [])
        ]
        proposed_changes = []
        cooldown = self._load_cooldown()
        for finding in findings:
            classification, reasons = classify_finding(finding)
            if classification == "AUTO_FIX_ALLOWED":
                cooldown_reason = self._cooldown_reason(finding, cooldown)
                if cooldown_reason:
                    classification = "NO_CHANGE"
                    reasons.append(cooldown_reason)
            proposed_changes.append(
                {
                    "finding": _finding_to_dict(finding),
                    "classification": classification,
                    "improvement_score": round(finding.improvement_score, 3),
                    "risk": finding.estimated_change_risk,
                    "tests_required": _tests_required(finding),
                    "rationale": reasons,
                }
            )
        return {
            "agent": "C_IMPROVEMENT_PROPOSER",
            "proposed_changes": proposed_changes,
        }

    def _agent_d_red_team(self, proposals: dict[str, Any]) -> dict[str, Any]:
        reviews = []
        for proposal in proposals.get("proposed_changes", []):
            finding = PostSessionFinding.from_mapping(
                proposal.get("finding", {}),
                source=str(proposal.get("finding", {}).get("source") or "proposal"),
            )
            violations = _red_team_violations(finding)
            classification = proposal.get("classification")
            approved = not violations or classification in {
                "DIRECTOR_REVIEW_REQUIRED",
                "BLOCKER_STOP_NEXT_SESSION",
                "NO_CHANGE",
            }
            reviews.append(
                {
                    "finding_id": finding.finding_id,
                    "approved": bool(approved),
                    "violations": violations,
                    "review_decision": "PASS" if approved else "REJECT_AUTO_FIX",
                }
            )
        return {"agent": "D_RED_TEAM_SAFETY_REVIEWER", "reviews": reviews}

    def _agent_e_integrate(
        self,
        day: str,
        collected: dict[str, Any],
        failure_analysis: dict[str, Any],
        proposals: dict[str, Any],
        red_team: dict[str, Any],
        *,
        apply_auto_fixes: bool,
    ) -> dict[str, Any]:
        reviews = {item["finding_id"]: item for item in red_team.get("reviews", [])}
        accepted_auto: list[dict[str, Any]] = []
        director: list[dict[str, Any]] = []
        no_change: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []

        for proposal in proposals.get("proposed_changes", []):
            finding_id = str(proposal.get("finding", {}).get("finding_id"))
            review = reviews.get(finding_id, {})
            classification = str(proposal.get("classification"))
            if classification == "AUTO_FIX_ALLOWED" and not review.get("approved", False):
                classification = "DIRECTOR_REVIEW_REQUIRED"
                proposal = {**proposal, "classification": classification}
            if classification == "AUTO_FIX_ALLOWED":
                accepted_auto.append(proposal)
            elif classification == "DIRECTOR_REVIEW_REQUIRED":
                director.append(proposal)
            elif classification == "BLOCKER_STOP_NEXT_SESSION":
                blockers.append(proposal)
            else:
                no_change.append(proposal)

        auto_applied = accepted_auto[:3] if apply_auto_fixes else []
        if blockers:
            final: FinalDecision = "POSTSESSION_BLOCK_NEXT_SESSION"
            self._write_block_marker(day, blockers)
        elif auto_applied:
            final = "POSTSESSION_AUTO_FIXES_APPLIED"
        elif director:
            final = "POSTSESSION_PROPOSALS_READY_FOR_DIRECTOR"
        elif not collected.get("findings") and collected.get("runtime_completeness") == "missing":
            final = "POSTSESSION_INCONCLUSIVE"
        else:
            final = "POSTSESSION_NO_CHANGE_REQUIRED"

        if auto_applied:
            self._record_cooldowns(day, auto_applied)
        return {
            "schema_version": SCHEMA_VERSION,
            "agent": "E_INTEGRATOR_PATCH_EXECUTOR",
            "session_date": day,
            "generated_at": self.now.isoformat(),
            "final_decision": final,
            "auto_fix_cap": 3,
            "auto_fixes_applied": auto_applied,
            "auto_fixes_deferred_by_cap": accepted_auto[3:],
            "director_review_required": director,
            "no_change": no_change,
            "blockers": blockers,
            "counts": {
                "findings": len(collected.get("findings", [])),
                "auto_fixes_applied": len(auto_applied),
                "director_review_required": len(director),
                "no_change": len(no_change),
                "blockers": len(blockers),
            },
            "safety": {
                "ibkr_used": False,
                "orders_allowed": False,
                "paper_orders_sent": False,
                "live_orders_sent": False,
                "submit_paths_created": False,
                "market_data_used": False,
                "env_real_touched": False,
            },
        }

    def _write_outputs(
        self,
        day: str,
        collected: dict[str, Any],
        failure_analysis: dict[str, Any],
        proposals: dict[str, Any],
        red_team: dict[str, Any],
        decision: dict[str, Any],
    ) -> None:
        reports_dir = self.research_root / "reports"
        proposals_dir = self.research_root / "proposals"
        runtime_day = self.runtime_root / day
        reports_dir.mkdir(parents=True, exist_ok=True)
        proposals_dir.mkdir(parents=True, exist_ok=True)
        runtime_day.mkdir(parents=True, exist_ok=True)

        _write_json(reports_dir / f"POSTSESSION_DECISION_{day}.json", decision)
        _write_json(proposals_dir / f"POSTSESSION_PROPOSALS_{day}.json", proposals)
        _write_json(runtime_day / f"postsession_{day}.json", decision)
        _write_json(runtime_day / "postsession_final.json", decision)
        (reports_dir / f"POSTSESSION_REPORT_{day}.md").write_text(
            render_postsession_report(collected, failure_analysis, proposals, red_team, decision),
            encoding="utf-8",
        )

    def _write_inconclusive(
        self,
        day: str,
        reason: str,
        final_path: Path,
        *,
        write_final_marker: bool = True,
    ) -> dict[str, Any]:
        decision = {
            "schema_version": SCHEMA_VERSION,
            "session_date": day,
            "generated_at": self.now.isoformat(),
            "final_decision": "POSTSESSION_INCONCLUSIVE",
            "reason": reason,
            "safety": {
                "ibkr_used": False,
                "orders_allowed": False,
                "paper_orders_sent": False,
                "live_orders_sent": False,
                "submit_paths_created": False,
                "market_data_used": False,
                "env_real_touched": False,
            },
        }
        if write_final_marker:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(final_path, decision)
        return decision

    def _write_validation_fail(self, day: str, reason: str) -> dict[str, Any]:
        decision = {
            "schema_version": SCHEMA_VERSION,
            "session_date": day,
            "generated_at": self.now.isoformat(),
            "final_decision": "POSTSESSION_VALIDATION_FAIL",
            "reason": reason,
            "safety": {
                "ibkr_used": False,
                "orders_allowed": False,
                "paper_orders_sent": False,
                "live_orders_sent": False,
                "submit_paths_created": False,
                "market_data_used": False,
                "env_real_touched": False,
            },
        }
        reports_dir = self.research_root / "reports"
        try:
            _write_json(reports_dir / f"POSTSESSION_DECISION_{day}.json", decision)
            (reports_dir / f"POSTSESSION_REPORT_{day}.md").write_text(
                "\n".join(
                    [
                        "# Post-Session Improvement Report",
                        "",
                        f"- final_decision: `{decision['final_decision']}`",
                        f"- reason: `{reason}`",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
        except OSError:
            pass
        return decision

    def _session_runtime_exists(self, session_date: date) -> bool:
        day = session_date.isoformat()
        for root in self.input_roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if day in path.name and path.is_file() and _permitted_input(path):
                    return True
        return False

    def _collect_artifacts(self, session_date: date) -> list[dict[str, Any]]:
        day = session_date.isoformat()
        artifacts: list[dict[str, Any]] = []
        for root in self.input_roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if len(artifacts) >= 200:
                    break
                if not path.is_file() or day not in path.name or not _permitted_input(path):
                    continue
                payload = _read_artifact(path)
                if payload is not None:
                    artifacts.append(payload)
        return artifacts

    def _findings_from_artifact(self, artifact: dict[str, Any]) -> list[PostSessionFinding]:
        source = str(artifact.get("path") or "artifact")
        payload = artifact.get("payload")
        findings: list[PostSessionFinding] = []
        if isinstance(payload, dict):
            for key in ("findings", "proposed_findings", "issues"):
                values = payload.get(key)
                if isinstance(values, list):
                    findings.extend(
                        PostSessionFinding.from_mapping(item, source=source)
                        for item in values
                        if isinstance(item, dict)
                    )
            text = json.dumps(payload, sort_keys=True, default=str)
        else:
            text = str(payload or "")
        findings.extend(_text_findings(text, source=source))
        return findings

    def _load_cooldown(self) -> dict[str, Any]:
        path = self.runtime_root / "cooldowns.json"
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _cooldown_reason(self, finding: PostSessionFinding, cooldown: dict[str, Any]) -> str | None:
        today = self.now.date().isoformat()
        yesterday = (self.now.date().toordinal() - 1)
        component_state = cooldown.get("components", {}).get(finding.component, {})
        if component_state.get("last_changed_date") == today:
            return "cooldown_same_component_once_per_day"
        if "runner" in finding.component.lower():
            last = component_state.get("last_changed_date")
            if last:
                try:
                    if date.fromisoformat(last).toordinal() == yesterday:
                        return "cooldown_same_runner_two_nights"
                except ValueError:
                    return "cooldown_state_invalid"
        return None

    def _record_cooldowns(self, day: str, auto_applied: list[dict[str, Any]]) -> None:
        cooldown = self._load_cooldown()
        components = dict(cooldown.get("components") or {})
        for item in auto_applied:
            component = str(item.get("finding", {}).get("component") or "unknown")
            components[component] = {"last_changed_date": day}
        cooldown["components"] = components
        _write_json(self.runtime_root / "cooldowns.json", cooldown)

    def _write_block_marker(self, day: str, blockers: list[dict[str, Any]]) -> None:
        _write_json(
            self.runtime_root / day / "BLOCK_NEXT_SESSION.json",
            {
                "schema_version": SCHEMA_VERSION,
                "decision": "POSTSESSION_BLOCK_NEXT_SESSION",
                "session_date": day,
                "blockers": blockers,
            },
        )


def classify_finding(finding: PostSessionFinding) -> tuple[DecisionClass, list[str]]:
    reasons: list[str] = []
    score = finding.improvement_score
    touched = set(finding.touched_areas)
    if _is_blocker(finding):
        return "BLOCKER_STOP_NEXT_SESSION", ["blocker_stop_condition_matched"]
    if touched & SENSITIVE_AREAS:
        reasons.append("sensitive_area_requires_director")
        return "DIRECTOR_REVIEW_REQUIRED", reasons
    if score < 3:
        return "NO_CHANGE", ["improvement_score_below_3_or_insufficient_evidence"]
    if score >= 3 and finding.estimated_change_risk > 2:
        return "DIRECTOR_REVIEW_REQUIRED", ["material_score_but_change_risk_above_2"]
    if _auto_fix_allowed(finding):
        return "AUTO_FIX_ALLOWED", ["auto_fix_criteria_met"]
    return "DIRECTOR_REVIEW_REQUIRED", ["material_score_but_auto_fix_criteria_not_met"]


def render_postsession_report(
    collected: dict[str, Any],
    failure_analysis: dict[str, Any],
    proposals: dict[str, Any],
    red_team: dict[str, Any],
    decision: dict[str, Any],
) -> str:
    lines = [
        "# Post-Session Improvement Report",
        "",
        f"- schema_version: `{SCHEMA_VERSION}`",
        f"- session_date: `{decision.get('session_date')}`",
        f"- final_decision: `{decision.get('final_decision')}`",
        f"- findings: `{decision.get('counts', {}).get('findings', 0)}`",
        f"- auto_fixes_applied: `{decision.get('counts', {}).get('auto_fixes_applied', 0)}`",
        f"- director_review_required: `{decision.get('counts', {}).get('director_review_required', 0)}`",
        f"- blockers: `{decision.get('counts', {}).get('blockers', 0)}`",
        "",
        "## Safety",
        "",
    ]
    for key, value in decision.get("safety", {}).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Agent A - Data Collection", ""])
    lines.append(f"- artifacts_scanned: `{len(collected.get('artifacts_scanned', []))}`")
    lines.append(f"- runtime_completeness: `{collected.get('runtime_completeness')}`")
    lines.extend(["", "## Agent B - Failure Modes", ""])
    for item in failure_analysis.get("top_failure_modes", [])[:10]:
        lines.append(f"- {item.get('finding_id')}: severity `{item.get('severity')}` component `{item.get('component')}`")
    if not failure_analysis.get("top_failure_modes"):
        lines.append("- none")
    lines.extend(["", "## Agent C/D - Proposals And Red-Team", ""])
    reviews = {item.get("finding_id"): item for item in red_team.get("reviews", [])}
    for item in proposals.get("proposed_changes", []):
        finding = item.get("finding", {})
        review = reviews.get(finding.get("finding_id"), {})
        lines.append(
            "- "
            f"{finding.get('finding_id')}: `{item.get('classification')}` "
            f"score `{item.get('improvement_score')}` red_team `{review.get('review_decision', 'NA')}`"
        )
    if not proposals.get("proposed_changes"):
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _auto_fix_allowed(finding: PostSessionFinding) -> bool:
    return (
        finding.improvement_score >= 4
        and finding.estimated_change_risk <= 2
        and finding.change_size in {"small", "tiny", "local"}
        and not (set(finding.touched_areas) & PROHIBITED_AUTO_FIX_AREAS)
        and finding.impact_area in SAFE_IMPACT_AREAS
        and finding.tests_available
        and not finding.requires_ibkr
        and not finding.affects_env_real
    )


def _is_blocker(finding: PostSessionFinding) -> bool:
    kind = str(finding.metadata.get("kind") or finding.finding_id)
    if kind in BLOCKER_KINDS:
        return True
    if finding.finding_id in BLOCKER_KINDS:
        return True
    text = f"{finding.title} {finding.evidence}".lower()
    return any(
        needle in text
        for needle in (
            "raw account id leak",
            "auto-submit unauthorized",
            "kill-switch failure",
            "unreconciled position",
            "secret versioned",
        )
    )


def _red_team_violations(finding: PostSessionFinding) -> list[str]:
    violations: list[str] = []
    touched = set(finding.touched_areas)
    if "live_behavior" in touched or "live" in finding.component.lower():
        violations.append("touches_live")
    if {"submit", "broker_submit", "order_path"} & touched:
        violations.append("touches_submit_or_order_path")
    if {"gates", "thresholds", "scoring"} & touched:
        violations.append("could_relax_gate_scoring_or_threshold")
    if "reconciliation" in touched and finding.impact_area != "safety":
        violations.append("could_silence_or_change_reconciliation")
    if finding.affects_env_real:
        violations.append("affects_real_env")
    return violations


def _tests_required(finding: PostSessionFinding) -> list[str]:
    tests = ["py_compile", "json_validation", "security_scan"]
    if finding.tests_available:
        tests.append(f"pytest::{finding.component}")
    if set(finding.touched_areas) & {"reconciliation", "submit", "cancel"}:
        tests.append("pytest::paper_readiness")
    return tests


def _collect_json_findings(payload: Any, source: str) -> list[PostSessionFinding]:
    if not isinstance(payload, dict):
        return []
    values = payload.get("findings")
    if not isinstance(values, list):
        return []
    return [
        PostSessionFinding.from_mapping(item, source=source)
        for item in values
        if isinstance(item, dict)
    ]


def _text_findings(text: str, *, source: str) -> list[PostSessionFinding]:
    findings: list[PostSessionFinding] = []
    lowered = text.lower()
    if ACCOUNT_RE.search(text):
        findings.append(
            PostSessionFinding(
                finding_id="raw_account_id_leak",
                title="Raw account id leak",
                evidence="Artifact text matched an account-id pattern.",
                severity=5,
                recurrence_count=1,
                impact_area="safety",
                confidence=0.95,
                estimated_change_risk=1,
                estimated_benefit=5,
                component="redaction",
                touched_areas=("observability",),
                tests_available=True,
                change_size="small",
                source=source,
                metadata={"kind": "raw_account_id_leak"},
            )
        )
    if "reconciliation_error" in lowered or "unreconciled position" in lowered:
        findings.append(
            PostSessionFinding(
                finding_id="reconciliation_error",
                title="Reconciliation error",
                evidence="Artifact reported reconciliation_error or unreconciled position.",
                severity=5,
                recurrence_count=1,
                impact_area="reconciliation",
                confidence=0.9,
                estimated_change_risk=3,
                estimated_benefit=5,
                component="reconciliation",
                touched_areas=("reconciliation",),
                tests_available=True,
                source=source,
                metadata={"kind": "reconciliation_error"},
            )
        )
    return findings


def _rollup_events(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    rollup = {"trades": 0, "fills": 0, "cancels": 0, "rejects": 0}
    for artifact in artifacts:
        text = json.dumps(artifact.get("payload"), default=str).lower()
        for key in rollup:
            rollup[key] += text.count(key[:-1] if key.endswith("s") else key)
    return rollup


def _permitted_input(path: Path) -> bool:
    parts = set(path.parts)
    if ".env" in path.name or "memory" in parts or "MEMORY.md" in path.name:
        return False
    if path.suffix.lower() not in {".json", ".md", ".txt", ".log"}:
        return False
    sensitive_name = path.name.lower()
    return not any(part in sensitive_name for part in ("secret", "token", "private_key", "password"))


def _read_artifact(path: Path) -> dict[str, Any] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000]
    except OSError:
        return None
    if ACCOUNT_RE.search(text):
        payload: Any = "<redacted_artifact_contains_account_id_pattern>"
    elif path.suffix.lower() == ".json":
        try:
            payload = _redact(json.loads(text))
        except json.JSONDecodeError:
            payload = _redact_text(text)
    else:
        payload = _redact_text(text)
    return {"path": str(path), "payload": payload}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(part in key_text.lower() for part in SECRET_KEY_PARTS):
                out[key_text] = "<redacted>"
            else:
                out[key_text] = _redact(item)
        return out
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(text: str) -> str:
    return ACCOUNT_RE.sub("<redacted_account_id>", text)


def _is_regular_trading_hours(now: datetime) -> bool:
    ny_now = now.astimezone(ZoneInfo("America/New_York"))
    if ny_now.weekday() >= 5:
        return False
    return time(9, 30) <= ny_now.time() <= time(16, 0)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _finding_to_dict(finding: PostSessionFinding) -> dict[str, Any]:
    return {
        "finding_id": finding.finding_id,
        "title": finding.title,
        "evidence": _redact_text(finding.evidence),
        "severity": finding.severity,
        "recurrence_count": finding.recurrence_count,
        "recurrence_factor": finding.recurrence_factor,
        "impact_area": finding.impact_area,
        "confidence": finding.confidence,
        "estimated_change_risk": finding.estimated_change_risk,
        "estimated_benefit": finding.estimated_benefit,
        "improvement_score": round(finding.improvement_score, 3),
        "component": finding.component,
        "touched_areas": list(finding.touched_areas),
        "tests_available": finding.tests_available,
        "change_size": finding.change_size,
        "requires_ibkr": finding.requires_ibkr,
        "affects_env_real": finding.affects_env_real,
        "source": finding.source,
        "metadata": _redact(finding.metadata),
    }


def _stable_id(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return f"finding_{digest[:12]}"


def _clamp_int(value: Any, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, number))


def _clamp_float(value: Any, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    return max(low, min(high, number))
