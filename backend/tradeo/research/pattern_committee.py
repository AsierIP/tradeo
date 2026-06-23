from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from tradeo.core.config import Settings, get_settings
from tradeo.research.types import ClusterCandidate

COMMITTEE_ROLES = (
    "statistical_falsifier",
    "execution_scientist",
    "overfit_adversary",
    "entry_exit_optimizer",
    "consensus_director",
)

HARD_FAILURES = (
    "validation_failed",
    "fdr_failed",
    "negative_oos_expectancy",
    "cost_stress_failed",
    "overfit_score_failed",
    "insufficient_effective_samples",
    "insufficient_symbol_diversity",
    "insufficient_year_diversity",
)

PRODUCTION_STATES = {
    "approved",
    "live",
    "live_candidate",
    "paper_candidate",
    "paper_limited_candidate",
    "paper_extended_candidate",
    "premium_candidate",
    "production",
    "production_candidate",
}


@dataclass(slots=True)
class PatternResearchCommittee:
    """Deterministic scientific review between Research and Lab.

    The committee is intentionally backend-only and local. It does not call an
    LLM, issue orders, or promote beyond LAB; it only mutates ClusterCandidate
    research metadata before persistence.
    """

    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def review_candidates(
        self,
        candidates: list[ClusterCandidate],
        *,
        run_id: int | str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        reviews = [
            self.review_candidate(candidate, run_id=run_id, params=params)
            for candidate in candidates
        ]
        approved = [review for review in reviews if review["approved"]]
        verdict_counts: dict[str, int] = {}
        for review in reviews:
            verdict = str(review["verdict"])
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        return {
            "schema_version": "tradeo.pattern_research_committee.summary.v1",
            "run_id": run_id,
            "candidate_count": len(candidates),
            "approved_count": len(approved),
            "blocked_count": len(candidates) - len(approved),
            "verdict_counts": verdict_counts,
            "roles": list(COMMITTEE_ROLES),
            "approval_rule": {
                "votes_required": 4,
                "member_count": 5,
                "hard_veto_allowed": False,
                "min_consensus_confidence": 0.60,
                "promotion_ceiling": "lab_candidate",
            },
            "patterns": [
                {
                    "pattern_key": review["pattern_key"],
                    "verdict": review["verdict"],
                    "approved": review["approved"],
                    "votes_positive": review["votes_positive"],
                    "consensus_confidence": review["consensus_confidence"],
                    "lab_destination": review["lab_destination"],
                    "hard_failures": review["hard_failures"],
                }
                for review in reviews
            ],
        }

    def review_candidate(
        self,
        candidate: ClusterCandidate,
        *,
        run_id: int | str | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        hard_failures = self._hard_failures(candidate)
        prior_reasoning = self._prior_reasoning(candidate)
        agents: list[dict[str, Any]] = []
        for role in COMMITTEE_ROLES:
            agents.append(
                self._agent_review(
                    candidate,
                    role=role,
                    previous_agents=agents,
                    hard_failures=hard_failures,
                    prior_reasoning=prior_reasoning,
                )
            )

        votes_positive = sum(1 for agent in agents if agent["vote"] == "approve")
        vetoes = [
            {"agent_id": agent["agent_id"], "role": agent["role"], "reason": agent["veto_reason"]}
            for agent in agents
            if agent["veto"]
        ]
        consensus_confidence = round(
            sum(float(agent["confidence"]) for agent in agents) / max(len(agents), 1),
            5,
        )
        lab_destination = self._lab_destination(candidate.timeframe)
        approved = (
            votes_positive >= 4
            and not vetoes
            and candidate.validation_passed
            and consensus_confidence >= 0.60
        )
        verdict = "approved_for_lab" if approved else self._blocked_verdict(hard_failures)
        payload = {
            "schema_version": "tradeo.pattern_research_committee.v1",
            "run_id": run_id,
            "pattern_key": candidate.pattern_key,
            "name": candidate.name,
            "side": candidate.side,
            "timeframe": candidate.timeframe,
            "window_size": candidate.window_size,
            "cluster_id": candidate.cluster_id,
            "params": self._json_clean(params or {}),
            "prior_reasoning": prior_reasoning,
            "roles": list(COMMITTEE_ROLES),
            "agents": agents,
            "votes_positive": votes_positive,
            "votes_negative": len(agents) - votes_positive,
            "votes_required": 4,
            "vetoes": vetoes,
            "hard_failures": hard_failures,
            "consensus_confidence": consensus_confidence,
            "approved": approved,
            "verdict": verdict,
            "lab_destination": lab_destination if approved else None,
            "next_research_layer": lab_destination if approved else None,
            "promotion_ceiling": "lab_candidate",
            "production_or_live_allowed": False,
        }
        payload = self._json_clean(payload)
        compact = self._compact_payload(payload)
        self._apply_verdict(candidate, payload=payload, compact=compact)
        return payload

    def _agent_review(
        self,
        candidate: ClusterCandidate,
        *,
        role: str,
        previous_agents: list[dict[str, Any]],
        hard_failures: list[str],
        prior_reasoning: dict[str, Any],
    ) -> dict[str, Any]:
        seen = [str(agent["agent_id"]) for agent in previous_agents]
        scoped_failures = self._role_failures(role, hard_failures)
        veto = bool(scoped_failures)
        vote = self._role_vote(candidate, role=role, hard_failures=hard_failures, prior_agents=previous_agents)
        confidence = self._role_confidence(candidate, role=role, hard_failures=hard_failures, vote=vote)
        role_index = COMMITTEE_ROLES.index(role) + 1
        agent_id = f"committee_{role_index}_{role}"
        return {
            "agent_id": agent_id,
            "role": role,
            "focus": self._role_focus(role),
            "seen_prior_agents": seen,
            "critique_of_previous": self._critique_of_previous(role, previous_agents, scoped_failures),
            "supporting_evidence": self._supporting_evidence(candidate, role, prior_reasoning),
            "objections": self._objections(candidate, role, hard_failures),
            "entry_exit_recommendations": self._entry_exit_recommendations(candidate, role),
            "vote": "approve" if vote else "block",
            "confidence": confidence,
            "veto": veto,
            "veto_reason": "; ".join(scoped_failures) if veto else "",
        }

    def _role_vote(
        self,
        candidate: ClusterCandidate,
        *,
        role: str,
        hard_failures: list[str],
        prior_agents: list[dict[str, Any]],
    ) -> bool:
        metrics = candidate.metrics
        if role == "statistical_falsifier":
            return not any(
                failure in hard_failures
                for failure in (
                    "validation_failed",
                    "fdr_failed",
                    "insufficient_effective_samples",
                )
            )
        if role == "execution_scientist":
            return not any(
                failure in hard_failures
                for failure in ("negative_oos_expectancy", "cost_stress_failed")
            )
        if role == "overfit_adversary":
            return not any(
                failure in hard_failures
                for failure in (
                    "overfit_score_failed",
                    "insufficient_symbol_diversity",
                    "insufficient_year_diversity",
                )
            )
        if role == "entry_exit_optimizer":
            required_rr = self._finite_float(metrics.get("required_runtime_rr"), 4.0)
            best_rr = self._finite_float(metrics.get("best_rr"), 0.0)
            best_expectancy = self._finite_float(metrics.get("best_expectancy_r"), 0.0)
            return best_rr >= required_rr and best_expectancy > 0 and "negative_oos_expectancy" not in hard_failures
        if role == "consensus_director":
            prior_votes = sum(1 for agent in prior_agents if agent.get("vote") == "approve")
            return prior_votes >= 3 and not hard_failures and candidate.validation_passed
        return False

    def _hard_failures(self, candidate: ClusterCandidate) -> list[str]:
        s = self.settings
        assert s is not None
        metrics = candidate.metrics
        failures: list[str] = []
        if not candidate.validation_passed or metrics.get("validation_passed") is False:
            failures.append("validation_failed")
        if metrics.get("fdr_failed") is True or metrics.get("fdr_passed") is False:
            failures.append("fdr_failed")
        oos = self._oos_expectancy(metrics)
        if oos is not None and oos <= 0.0:
            failures.append("negative_oos_expectancy")
        if metrics.get("cost_stress_failed") is True or metrics.get("cost_stress_passed") is False:
            failures.append("cost_stress_failed")
        overfit = self._finite_float_or_none(metrics.get("overfit_score"))
        if metrics.get("overfit_score_failed") is True or (
            overfit is not None and overfit > s.discovery_max_overfit_score
        ):
            failures.append("overfit_score_failed")
        effective_samples = self._effective_samples(metrics)
        if metrics.get("insufficient_effective_samples") is True or (
            effective_samples is not None and effective_samples < s.discovery_min_effective_samples
        ):
            failures.append("insufficient_effective_samples")
        if metrics.get("insufficient_symbol_diversity") is True or candidate.symbol_count < s.discovery_min_symbols:
            failures.append("insufficient_symbol_diversity")
        if metrics.get("insufficient_year_diversity") is True or candidate.year_count < s.discovery_min_years:
            failures.append("insufficient_year_diversity")
        return [failure for failure in HARD_FAILURES if failure in set(failures)]

    @staticmethod
    def _oos_expectancy(metrics: dict[str, Any]) -> float | None:
        direct = PatternResearchCommittee._finite_float_or_none(metrics.get("out_of_sample_expectancy_r"))
        if direct is not None:
            return direct
        oos_metrics = metrics.get("out_of_sample_metrics")
        if isinstance(oos_metrics, dict):
            return PatternResearchCommittee._finite_float_or_none(oos_metrics.get("expectancy_r"))
        return None

    @staticmethod
    def _effective_samples(metrics: dict[str, Any]) -> float | None:
        direct = PatternResearchCommittee._finite_float_or_none(metrics.get("effective_sample_count"))
        if direct is not None:
            return direct
        quant = metrics.get("quant_validation")
        if isinstance(quant, dict):
            return PatternResearchCommittee._finite_float_or_none(quant.get("n_eff"))
        return None

    @staticmethod
    def _role_failures(role: str, hard_failures: list[str]) -> list[str]:
        scoped = {
            "statistical_falsifier": {
                "validation_failed",
                "fdr_failed",
                "insufficient_effective_samples",
            },
            "execution_scientist": {"negative_oos_expectancy", "cost_stress_failed"},
            "overfit_adversary": {
                "overfit_score_failed",
                "insufficient_symbol_diversity",
                "insufficient_year_diversity",
            },
            "entry_exit_optimizer": {"negative_oos_expectancy"},
            "consensus_director": set(HARD_FAILURES),
        }
        return [failure for failure in hard_failures if failure in scoped.get(role, set())]

    def _role_confidence(
        self,
        candidate: ClusterCandidate,
        *,
        role: str,
        hard_failures: list[str],
        vote: bool,
    ) -> float:
        metrics = candidate.metrics
        confidence = 0.50
        confidence += 0.10 if candidate.validation_passed else -0.15
        confidence += 0.10 if self._finite_float(metrics.get("best_expectancy_r"), 0.0) > 0 else -0.08
        confidence += 0.10 if self._oos_expectancy(metrics) and self._oos_expectancy(metrics) > 0 else -0.08
        confidence += 0.08 if metrics.get("fdr_passed") is not False else -0.12
        confidence += 0.08 if metrics.get("cost_stress_passed") is not False else -0.12
        confidence += 0.07 if self._finite_float(metrics.get("stability_score"), 0.0) >= 0.45 else -0.04
        confidence -= 0.08 * len(hard_failures)
        confidence += 0.05 if vote else -0.03
        if role == "consensus_director":
            confidence += 0.03
        return round(max(0.05, min(0.95, confidence)), 5)

    @staticmethod
    def _role_focus(role: str) -> str:
        return {
            "statistical_falsifier": "Reject false discoveries, multiple-testing leaks and weak effective samples.",
            "execution_scientist": "Check OOS edge, cost stress and executable fill assumptions.",
            "overfit_adversary": "Challenge overfit score, symbol diversity and year diversity.",
            "entry_exit_optimizer": "Assess whether entry/exit evidence can be handed to Lab safely.",
            "consensus_director": "Aggregate prior reviews under the 4-of-5 and no-veto rule.",
        }[role]

    @staticmethod
    def _critique_of_previous(
        role: str,
        previous_agents: list[dict[str, Any]],
        scoped_failures: list[str],
    ) -> str:
        if not previous_agents:
            return "first review; no prior agents available"
        approvals = sum(1 for agent in previous_agents if agent.get("vote") == "approve")
        blocks = len(previous_agents) - approvals
        if scoped_failures:
            return (
                f"prior agents saw {approvals} approve and {blocks} block; this role adds hard "
                f"objections: {', '.join(scoped_failures)}"
            )
        return (
            f"prior agents saw {approvals} approve and {blocks} block; {role} finds no new "
            "hard veto in its scope"
        )

    @staticmethod
    def _supporting_evidence(
        candidate: ClusterCandidate,
        role: str,
        prior_reasoning: dict[str, Any],
    ) -> list[str]:
        metrics = candidate.metrics
        evidence = [
            f"validation_passed={candidate.validation_passed}",
            f"best_rr={metrics.get('best_rr')}",
            f"best_expectancy_r={metrics.get('best_expectancy_r')}",
            f"out_of_sample_expectancy_r={metrics.get('out_of_sample_expectancy_r')}",
        ]
        if role in {"statistical_falsifier", "consensus_director"}:
            evidence.append(f"fdr_passed={metrics.get('fdr_passed')}")
            evidence.append(f"effective_sample_count={metrics.get('effective_sample_count')}")
        if role in {"execution_scientist", "entry_exit_optimizer"}:
            evidence.append(f"cost_stress_passed={metrics.get('cost_stress_passed')}")
            evidence.append(f"avg_fill_probability={metrics.get('avg_fill_probability')}")
        if role == "overfit_adversary":
            evidence.append(f"overfit_score={metrics.get('overfit_score')}")
            evidence.append(
                f"symbol_count={candidate.symbol_count};year_count={candidate.year_count}"
            )
        hypothesis = prior_reasoning.get("research_hypothesis")
        if isinstance(hypothesis, dict) and hypothesis.get("thesis"):
            evidence.append(f"research_thesis={hypothesis.get('thesis')}")
        return evidence

    @staticmethod
    def _objections(candidate: ClusterCandidate, role: str, hard_failures: list[str]) -> list[str]:
        scoped = PatternResearchCommittee._role_failures(role, hard_failures)
        objections = [f"hard_failure:{failure}" for failure in scoped]
        if role == "entry_exit_optimizer":
            best_rr = PatternResearchCommittee._finite_float(candidate.metrics.get("best_rr"), 0.0)
            required_rr = PatternResearchCommittee._finite_float(
                candidate.metrics.get("required_runtime_rr"), 4.0
            )
            if best_rr < required_rr:
                objections.append(f"best_rr below runtime requirement: {best_rr:g} < {required_rr:g}")
        return objections or ["no hard objection in role scope"]

    @staticmethod
    def _entry_exit_recommendations(candidate: ClusterCandidate, role: str) -> list[str]:
        metrics = candidate.metrics
        rr = PatternResearchCommittee._finite_float(metrics.get("best_rr"), 4.0)
        if role == "entry_exit_optimizer":
            return [
                f"use Lab-only entry validation at {rr:g}R target before any execution promotion",
                "record next-bar eligible entry, stop-first path and timeout outcome in Lab observations",
            ]
        if role == "execution_scientist":
            return [
                "stress test fills, spread, slippage and gap adverse R before paper evidence",
                "keep paper/live promotion blocked until Director gate observes real fills",
            ]
        return [
            "do not promote beyond lab_candidate from research metrics",
            "require falsifiable Lab observations before production review",
        ]

    @staticmethod
    def _prior_reasoning(candidate: ClusterCandidate) -> dict[str, Any]:
        metrics = candidate.metrics
        return PatternResearchCommittee._json_clean(
            {
                "validation_passed": candidate.validation_passed,
                "validation_reasons": candidate.validation_reasons,
                "validation_warnings": metrics.get("validation_warnings", []),
                "validation_rejections": metrics.get("validation_rejections", []),
                "promotion_status_before_committee": metrics.get("promotion_status"),
                "promotion_reason_before_committee": metrics.get("promotion_reason"),
                "research_hypothesis": metrics.get("research_hypothesis", {}),
                "research_hypothesis_package": metrics.get("research_hypothesis_package", {}),
                "pattern_lifecycle": metrics.get("pattern_lifecycle", {}),
                "research_director": metrics.get("research_director", {}),
            }
        )

    @staticmethod
    def _blocked_verdict(hard_failures: list[str]) -> str:
        false_positive_failures = {
            "fdr_failed",
            "negative_oos_expectancy",
            "cost_stress_failed",
            "overfit_score_failed",
        }
        if any(failure in false_positive_failures for failure in hard_failures):
            return "rejected_false_positive"
        return "needs_more_research"

    @staticmethod
    def _lab_destination(timeframe: str) -> str:
        normalized = " ".join(str(timeframe).strip().lower().split()).replace(" ", "")
        if normalized in {"1d", "1day", "daily", "day", "d"}:
            return "lab_daily"
        return "lab_intraday"

    def _apply_verdict(
        self,
        candidate: ClusterCandidate,
        *,
        payload: dict[str, Any],
        compact: dict[str, Any],
    ) -> None:
        metrics = candidate.metrics
        approved = bool(payload["approved"])
        verdict = str(payload["verdict"])
        metrics["research_committee"] = payload
        metrics["research_committee_compact"] = compact

        lifecycle = metrics.get("pattern_lifecycle")
        lifecycle_payload = dict(lifecycle) if isinstance(lifecycle, dict) else {}
        lifecycle_payload["committee_gate"] = payload
        lifecycle_payload["paper_live_auto_promotion"] = False
        lifecycle_payload["director_gate_required_for_paper_or_live"] = True
        metrics["pattern_lifecycle"] = lifecycle_payload

        director = metrics.get("research_director")
        director_payload = dict(director) if isinstance(director, dict) else {}
        director_payload["pattern_committee"] = payload
        director_payload["paper_live_auto_promotion"] = False
        director_payload["director_gate_required_for_paper_or_live"] = True
        metrics["research_director"] = director_payload

        metrics["research_committee_approved"] = approved
        metrics["research_committee_verdict"] = verdict
        if approved:
            destination = str(payload["lab_destination"])
            candidate.validation_passed = True
            metrics["validation_passed"] = True
            metrics["lab_destination"] = destination
            metrics["next_research_layer"] = destination
            metrics["promotion_status"] = "lab_candidate"
            metrics["promotion_reason"] = (
                "approved_for_lab by PatternResearchCommittee consensus: "
                f"{payload['votes_positive']}/5 votes, confidence "
                f"{float(payload['consensus_confidence']):.2f}, destination {destination}; "
                "production/live remains blocked"
            )
        else:
            candidate.validation_passed = False
            metrics["validation_passed"] = False
            metrics["lab_destination"] = None
            metrics["next_research_layer"] = None
            metrics["promotion_status"] = (
                "needs_confirmation" if verdict == "needs_more_research" else "rejected"
            )
            metrics["promotion_reason"] = (
                f"blocked by PatternResearchCommittee: {verdict}; "
                f"{payload['votes_positive']}/5 votes, confidence "
                f"{float(payload['consensus_confidence']):.2f}; hard_failures="
                f"{payload['hard_failures']}"
            )
            marker = f"research_committee:{verdict}"
            if marker not in candidate.validation_reasons:
                candidate.validation_reasons = [*candidate.validation_reasons, marker]
            rejection_reasons = metrics.get("rejection_reasons", [])
            if not isinstance(rejection_reasons, list):
                rejection_reasons = []
            if marker not in rejection_reasons:
                rejection_reasons.append(marker)
            metrics["rejection_reasons"] = rejection_reasons
            if verdict == "needs_more_research":
                metrics["confirmation_recommended"] = True
                metrics["confirmation_status"] = "needs_confirmation"

        if str(metrics.get("promotion_status", "")).lower() in PRODUCTION_STATES:
            metrics["promotion_status"] = "lab_candidate" if approved else "rejected"
            metrics["research_committee_forced_lab_ceiling"] = True

    @staticmethod
    def _compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": "tradeo.pattern_research_committee.compact.v1",
            "pattern_key": payload["pattern_key"],
            "verdict": payload["verdict"],
            "approved": payload["approved"],
            "votes_positive": payload["votes_positive"],
            "votes_required": payload["votes_required"],
            "consensus_confidence": payload["consensus_confidence"],
            "veto_count": len(payload["vetoes"]),
            "hard_failures": payload["hard_failures"],
            "lab_destination": payload["lab_destination"],
            "role_votes": [
                {
                    "role": agent["role"],
                    "vote": agent["vote"],
                    "confidence": agent["confidence"],
                    "veto": agent["veto"],
                }
                for agent in payload["agents"]
            ],
            "production_or_live_allowed": False,
        }

    @staticmethod
    def _finite_float(value: Any, default: float) -> float:
        converted = PatternResearchCommittee._finite_float_or_none(value)
        return default if converted is None else converted

    @staticmethod
    def _finite_float_or_none(value: Any) -> float | None:
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return None
        return converted if math.isfinite(converted) else None

    @staticmethod
    def _json_clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): PatternResearchCommittee._json_clean(child) for key, child in value.items()}
        if isinstance(value, list | tuple | set):
            return [PatternResearchCommittee._json_clean(child) for child in value]
        if hasattr(value, "item") and callable(value.item):
            try:
                return PatternResearchCommittee._json_clean(value.item())
            except (TypeError, ValueError):
                return str(value)
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
