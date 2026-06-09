from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import DiscoveredPattern, DiscoveredPatternMetric


@dataclass(slots=True)
class ResearchDirector:
    """Autonomous research scientist layer for discovered patterns.

    The director does not promote patterns to paper/live. It turns discovery
    output into durable research knowledge: falsifiable hypotheses, adversarial
    challenges, invariant checks, memory graph updates, active-learning agendas
    and paper-style reports.
    """

    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def run(
        self,
        db: Session,
        *,
        run_id: int | None = None,
        limit: int | None = None,
        store: bool = True,
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        patterns = self._patterns(db, run_id=run_id, limit=limit or settings.research_director_pattern_limit)
        generated_at = datetime.now(timezone.utc).isoformat()
        intelligence_by_key: dict[str, dict[str, Any]] = {}
        for pattern in patterns:
            intelligence = self._pattern_intelligence(pattern, generated_at=generated_at)
            intelligence_by_key[pattern.pattern_key] = intelligence
            if store:
                metrics = dict(pattern.metrics_json or {})
                metrics["research_intelligence"] = intelligence
                metrics["research_hypothesis"] = intelligence["hypothesis"]
                metrics["research_lifecycle"] = intelligence["lifecycle"]
                metrics["research_director_updated_at"] = generated_at
                pattern.metrics_json = self._json_clean(metrics)
                pattern.updated_at = datetime.now(timezone.utc)
                db.add(pattern)
                db.add(
                    DiscoveredPatternMetric(
                        pattern_id=pattern.id,
                        split="research_director",
                        metrics_json=self._json_clean(intelligence),
                    )
                )

        memory_graph = self._memory_graph(patterns, intelligence_by_key)
        agenda = self._active_learning_agenda(patterns, intelligence_by_key, memory_graph)
        summary = {
            "generated_at": generated_at,
            "run_id": run_id,
            "patterns_reviewed": len(patterns),
            "hypotheses_created": len(intelligence_by_key),
            "memory_graph": memory_graph,
            "active_learning_agenda": agenda,
            "director_state": self._director_state(patterns, intelligence_by_key, agenda),
        }
        paths = self._write_artifacts(summary, patterns, intelligence_by_key)
        summary["artifacts"] = paths
        if store:
            db.commit()
        return self._json_clean(summary)

    def _patterns(self, db: Session, *, run_id: int | None, limit: int) -> list[DiscoveredPattern]:
        query = db.query(DiscoveredPattern).order_by(DiscoveredPattern.score.desc(), DiscoveredPattern.created_at.desc())
        if run_id is not None:
            query = query.filter(DiscoveredPattern.run_id == run_id)
        return query.limit(max(1, min(int(limit), 500))).all()

    def _pattern_intelligence(self, pattern: DiscoveredPattern, *, generated_at: str) -> dict[str, Any]:
        metrics = dict(pattern.metrics_json or {})
        hypothesis = self._hypothesis(pattern, metrics)
        replay = self._market_replay(pattern, metrics)
        adversarial = self._adversarial_challenge(pattern, metrics, replay)
        invariance = self._invariance(pattern, metrics)
        foundation = self._foundation_learning_digest(pattern, metrics)
        lifecycle = self._lifecycle(pattern, metrics, adversarial, invariance)
        paper = self._paper_summary(pattern, hypothesis, adversarial, invariance, replay, lifecycle)
        return {
            "generated_at": generated_at,
            "pattern_key": pattern.pattern_key,
            "hypothesis": hypothesis,
            "foundation_learning": foundation,
            "market_replay": replay,
            "adversarial_challenge": adversarial,
            "invariance": invariance,
            "lifecycle": lifecycle,
            "paper": paper,
        }

    def _hypothesis(self, pattern: DiscoveredPattern, metrics: dict[str, Any]) -> dict[str, Any]:
        human_rule = metrics.get("human_rule") if isinstance(metrics.get("human_rule"), dict) else {}
        rule = str(human_rule.get("rule") or self._fallback_rule(pattern, metrics))
        regime = metrics.get("regime_profile") if isinstance(metrics.get("regime_profile"), dict) else {}
        dominant_regime = str(regime.get("dominant_regime", "unknown"))
        mechanism = self._mechanism(pattern, metrics, rule)
        works_when = self._works_when(metrics, human_rule, dominant_regime)
        fails_when = self._fails_when(metrics, dominant_regime)
        evidence = {
            "sample_count": pattern.sample_count,
            "symbol_count": pattern.symbol_count,
            "year_count": pattern.year_count,
            "best_rr": float(pattern.best_rr or metrics.get("best_rr", 0.0) or 0.0),
            "expectancy_r": float(pattern.best_expectancy_r or metrics.get("best_expectancy_r", 0.0) or 0.0),
            "profit_factor": float(pattern.best_profit_factor or metrics.get("best_profit_factor", 0.0) or 0.0),
            "oos_expectancy_r": float(pattern.out_of_sample_expectancy_r or 0.0),
            "purged_cv_positive_rate": float(metrics.get("purged_cv_positive_rate", 0.0) or 0.0),
            "deflated_sharpe_probability": float(metrics.get("deflated_sharpe_probability", 0.0) or 0.0),
        }
        return {
            "thesis": f"{pattern.side} edge candidate: {rule}",
            "mechanism": mechanism,
            "works_when": works_when,
            "should_fail_when": fails_when,
            "kill_criteria": self._kill_criteria(pattern, metrics),
            "evidence": evidence,
            "confidence": self._bounded(
                0.15
                + min(pattern.sample_count / 250.0, 1.0) * 0.18
                + min(pattern.symbol_count / 20.0, 1.0) * 0.16
                + min(pattern.year_count / 5.0, 1.0) * 0.12
                + max(0.0, float(metrics.get("purged_cv_positive_rate", 0.0))) * 0.17
                + max(0.0, float(metrics.get("deflated_sharpe_probability", 0.0))) * 0.12
                + (0.10 if pattern.validation_passed else 0.0)
            ),
            "falsifiable": True,
        }

    @staticmethod
    def _fallback_rule(pattern: DiscoveredPattern, metrics: dict[str, Any]) -> str:
        rule_bits = [
            f"window={pattern.window_size}",
            f"side={pattern.side}",
            f"best_rr={float(metrics.get('best_rr', pattern.best_rr or 0.0)):.2f}",
            f"score={float(pattern.score or 0.0):.3f}",
        ]
        return "centroid similarity with " + ", ".join(rule_bits)

    @staticmethod
    def _mechanism(pattern: DiscoveredPattern, metrics: dict[str, Any], rule: str) -> str:
        side_word = "demand" if pattern.side == "long" else "supply"
        if "compression" in rule or float(metrics.get("range_phase_expansion", 0.0) or 0.0) < 0:
            return f"{side_word} imbalance after compression; edge should appear quickly after range expansion."
        if float(metrics.get("mfe_before_mae_rate", 0.0) or 0.0) >= 0.55:
            return f"{side_word} imbalance appears before adverse excursion; timing quality is part of the edge."
        if float(metrics.get("relative_strength_sector", 0.0) or 0.0) > 0:
            return "sector-relative strength plus local trigger may indicate institutional rotation."
        return "recurrent chart family with forward path asymmetry; causal driver remains provisional."

    @staticmethod
    def _works_when(metrics: dict[str, Any], human_rule: dict[str, Any], dominant_regime: str) -> list[str]:
        conditions = []
        for condition in human_rule.get("conditions", []) if isinstance(human_rule, dict) else []:
            if isinstance(condition, dict) and condition.get("label"):
                conditions.append(
                    f"{condition.get('label')} {condition.get('operator')} {condition.get('threshold')}"
                )
        if dominant_regime != "unknown":
            conditions.append(f"dominant regime matches {dominant_regime}")
        if float(metrics.get("avg_fill_probability", 1.0) or 1.0) >= 0.65:
            conditions.append("estimated fill quality remains high")
        if not conditions:
            conditions.append("centroid similarity remains high and execution costs stay near research assumptions")
        return conditions[:6]

    @staticmethod
    def _fails_when(metrics: dict[str, Any], dominant_regime: str) -> list[str]:
        failures = [
            "out-of-sample expectancy turns negative",
            "purged CV positive fold rate drops below configured minimum",
            "cost stress x2 removes positive expectancy",
        ]
        if dominant_regime != "unknown":
            failures.append(f"market leaves preferred regime {dominant_regime}")
        if float(metrics.get("fast_target_rate", 0.0) or 0.0) > 0.35:
            failures.append("entries are delayed; fast-target edge becomes latency-fragile")
        if float(metrics.get("avg_fill_probability", 1.0) or 1.0) < 0.55:
            failures.append("fill probability deteriorates below tradable threshold")
        return failures[:6]

    @staticmethod
    def _kill_criteria(pattern: DiscoveredPattern, metrics: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "metric": "rolling_oos_expectancy_r",
                "operator": "<=",
                "threshold": 0.0,
                "reason": "edge must stay positive outside discovery sample",
            },
            {
                "metric": "cost_stress_2x_expectancy_r",
                "operator": "<=",
                "threshold": 0.0,
                "reason": "statistical edge without cost edge is not tradable",
            },
            {
                "metric": "symbol_count",
                "operator": "<",
                "threshold": max(4, min(8, int(pattern.symbol_count or 0))),
                "reason": "avoid single-name or tiny-universe artifacts",
            },
            {
                "metric": "edge_decay_parameter_score",
                "operator": ">",
                "threshold": max(0.55, float(metrics.get("edge_decay_parameter_score", 0.55) or 0.55)),
                "reason": "nearby parameter changes should not destroy the edge",
            },
        ]

    @staticmethod
    def _market_replay(pattern: DiscoveredPattern, metrics: dict[str, Any]) -> dict[str, Any]:
        fill = float(metrics.get("avg_fill_probability", 0.0) or 0.0)
        max_size = float(metrics.get("p25_max_size_usd", 0.0) or 0.0)
        cost_r = float(metrics.get("avg_execution_cost_r", 0.0) or 0.0)
        spread = float(metrics.get("avg_spread_proxy_pct", 0.0) or 0.0)
        slippage = float(metrics.get("avg_slippage_proxy_pct", 0.0) or 0.0)
        gap = float(metrics.get("avg_entry_gap_penalty_pct", 0.0) or 0.0)
        fast = float(metrics.get("fast_target_rate", 0.0) or 0.0)
        late_entry_fragility = ResearchDirector._bounded(fast * 0.65 + gap * 8.0 + slippage * 5.0)
        tradability = ResearchDirector._bounded(
            fill * 0.35
            + min(max_size / 25_000.0, 1.0) * 0.20
            + max(0.0, 1.0 - cost_r / 0.35) * 0.25
            + max(0.0, 1.0 - late_entry_fragility) * 0.20
        )
        bottlenecks = []
        if fill < 0.55:
            bottlenecks.append("fill_probability")
        if 0 < max_size < 10_000:
            bottlenecks.append("max_size")
        if cost_r > 0.25:
            bottlenecks.append("execution_cost")
        if late_entry_fragility > 0.55:
            bottlenecks.append("entry_latency")
        return {
            "tradability_score": round(tradability, 5),
            "late_entry_fragility": round(late_entry_fragility, 5),
            "avg_fill_probability": round(fill, 5),
            "p25_max_size_usd": round(max_size, 2),
            "avg_execution_cost_r": round(cost_r, 5),
            "avg_spread_proxy_pct": round(spread, 6),
            "avg_slippage_proxy_pct": round(slippage, 6),
            "avg_entry_gap_penalty_pct": round(gap, 6),
            "bottlenecks": bottlenecks,
            "market_replay_model": "deterministic_latency_fill_cost_proxy_v1",
            "assumption": "No broker microstructure data is used; this is a conservative research replay proxy.",
        }

    @staticmethod
    def _adversarial_challenge(
        pattern: DiscoveredPattern,
        metrics: dict[str, Any],
        replay: dict[str, Any],
    ) -> dict[str, Any]:
        tests = [
            ResearchDirector._challenge_test(
                "leakage_guard",
                bool(metrics.get("train_cutoff")) and bool(metrics.get("holdout_start")),
                "train/holdout timestamps are explicit",
            ),
            ResearchDirector._challenge_test(
                "white_reality_check",
                float(metrics.get("wrc_p_value", 1.0) or 1.0) <= 0.25,
                "multiple-testing corrected reality check should pass",
            ),
            ResearchDirector._challenge_test(
                "spa_test",
                float(metrics.get("spa_p_value", 1.0) or 1.0) <= 0.25,
                "SPA proxy should pass",
            ),
            ResearchDirector._challenge_test(
                "deflated_sharpe",
                float(metrics.get("deflated_sharpe_probability", 0.0) or 0.0) >= 0.50,
                "Sharpe must survive trial deflation",
            ),
            ResearchDirector._challenge_test(
                "cost_shock",
                bool(metrics.get("cost_stress_passed", False)),
                "edge must survive stressed costs",
            ),
            ResearchDirector._challenge_test(
                "parameter_decay",
                bool(metrics.get("edge_decay_passed", False)),
                "nearby R:R variants should keep edge",
            ),
            ResearchDirector._challenge_test(
                "universe_concentration",
                pattern.symbol_count >= 8,
                "edge should not depend on a tiny symbol set",
            ),
            ResearchDirector._challenge_test(
                "time_concentration",
                pattern.year_count >= 2,
                "edge should not depend on a single year",
            ),
            ResearchDirector._challenge_test(
                "market_replay",
                float(replay.get("tradability_score", 0.0)) >= 0.45,
                "execution replay must stay tradable",
            ),
        ]
        fail_count = sum(1 for test in tests if not test["passed"])
        challenge_score = ResearchDirector._bounded(1.0 - fail_count / max(len(tests), 1))
        if challenge_score >= 0.78:
            verdict = "survives_adversarial_review"
        elif challenge_score >= 0.50:
            verdict = "needs_targeted_confirmation"
        else:
            verdict = "fragile_or_overfit"
        return {
            "verdict": verdict,
            "challenge_score": round(challenge_score, 5),
            "tests": tests,
            "warnings": [test["name"] for test in tests if not test["passed"]],
        }

    @staticmethod
    def _challenge_test(name: str, passed: bool, rationale: str) -> dict[str, Any]:
        return {"name": name, "passed": bool(passed), "rationale": rationale}

    @staticmethod
    def _invariance(pattern: DiscoveredPattern, metrics: dict[str, Any]) -> dict[str, Any]:
        by_year = metrics.get("by_year_expectancy") if isinstance(metrics.get("by_year_expectancy"), dict) else {}
        by_symbol = metrics.get("top_symbols_expectancy") if isinstance(metrics.get("top_symbols_expectancy"), dict) else {}
        regime = metrics.get("regime_profile") if isinstance(metrics.get("regime_profile"), dict) else {}
        positive_year_rate = ResearchDirector._positive_value_rate(by_year)
        positive_symbol_rate = ResearchDirector._positive_value_rate(by_symbol)
        purged_rate = float(metrics.get("purged_cv_positive_rate", 0.0) or 0.0)
        stability = float(metrics.get("stability_score", 0.0) or 0.0)
        invariant_score = ResearchDirector._bounded(
            min(pattern.symbol_count / 20.0, 1.0) * 0.20
            + min(pattern.year_count / 5.0, 1.0) * 0.20
            + positive_year_rate * 0.18
            + positive_symbol_rate * 0.14
            + purged_rate * 0.18
            + stability * 0.10
        )
        expected_fail_buckets = []
        if pattern.side == "long":
            expected_fail_buckets.extend(["market_down", "sector_weak"])
        else:
            expected_fail_buckets.extend(["market_up", "sector_strong"])
        if float(metrics.get("avg_fill_probability", 1.0) or 1.0) < 0.65:
            expected_fail_buckets.append("thin_liquidity")
        return {
            "invariant_score": round(invariant_score, 5),
            "positive_year_rate": round(positive_year_rate, 5),
            "positive_symbol_rate": round(positive_symbol_rate, 5),
            "purged_cv_positive_rate": round(purged_rate, 5),
            "dominant_regime": regime.get("dominant_regime", "unknown"),
            "expected_fail_buckets": expected_fail_buckets,
            "evidence": {
                "symbol_count": pattern.symbol_count,
                "year_count": pattern.year_count,
                "by_year_expectancy": by_year,
                "top_symbols_expectancy": by_symbol,
            },
        }

    @staticmethod
    def _foundation_learning_digest(pattern: DiscoveredPattern, metrics: dict[str, Any]) -> dict[str, Any]:
        centroid = np.asarray(pattern.centroid_json or [], dtype=float)
        finite_ratio = float(np.mean(np.isfinite(centroid))) if len(centroid) else 0.0
        norm = float(np.linalg.norm(np.nan_to_num(centroid))) if len(centroid) else 0.0
        feature_summary = pattern.feature_summary_json or {}
        feature_completeness = min(len(feature_summary) / 30.0, 1.0)
        contrastive = 1.0 - float(metrics.get("run_max_family_similarity", metrics.get("registry_similarity", 0.0)) or 0.0)
        path_alignment = ResearchDirector._bounded(
            float(metrics.get("mfe_before_mae_rate", 0.0) or 0.0) * 0.35
            + float(metrics.get("fast_target_rate", 0.0) or 0.0) * 0.25
            + max(0.0, float(metrics.get("expectancy_lift_r", 0.0) or 0.0)) * 0.20
            + max(0.0, float(metrics.get("out_of_sample_expectancy_r", 0.0) or 0.0)) * 0.20
        )
        teacher_score = ResearchDirector._bounded(
            finite_ratio * 0.20
            + feature_completeness * 0.20
            + max(0.0, min(contrastive, 1.0)) * 0.20
            + path_alignment * 0.30
            + min(norm / max(len(centroid), 1), 1.0) * 0.10
        )
        return {
            "method": "self_supervised_proxy_teacher_v1",
            "masked_reconstruction_stability": round(finite_ratio * feature_completeness, 5),
            "contrastive_family_separation": round(max(0.0, min(contrastive, 1.0)), 5),
            "future_proxy_alignment": round(path_alignment, 5),
            "embedding_teacher_score": round(teacher_score, 5),
            "note": "Lightweight local proxy; no neural training or external dependency required.",
        }

    @staticmethod
    def _lifecycle(
        pattern: DiscoveredPattern,
        metrics: dict[str, Any],
        adversarial: dict[str, Any],
        invariance: dict[str, Any],
    ) -> dict[str, Any]:
        challenge = float(adversarial.get("challenge_score", 0.0))
        invariant = float(invariance.get("invariant_score", 0.0))
        status = "discovered"
        if not pattern.validation_passed:
            status = "needs_confirmation" if metrics.get("confirmation_recommended") else "rejected_learning_memory"
        elif str(pattern.drift_status or "") == "degrading":
            status = "decaying"
        elif challenge >= 0.78 and invariant >= 0.60:
            status = "confirmed_lab_hypothesis"
        elif challenge >= 0.50:
            status = "challenged_lab_hypothesis"
        else:
            status = "fragile_lab_hypothesis"
        next_action = {
            "confirmed_lab_hypothesis": "send to Director paper-review queue; still blocked from live execution",
            "challenged_lab_hypothesis": "run targeted confirmation in weak buckets before any paper promotion",
            "fragile_lab_hypothesis": "keep as learning memory; do not allocate paper validation yet",
            "decaying": "monitor for resurrection only in original dominant regime",
            "needs_confirmation": str(metrics.get("confirmation_next_action", "expand sample and rerun")),
            "rejected_learning_memory": "retain as negative research memory and avoid near-duplicate runs",
            "discovered": "continue observation",
        }.get(status, "continue observation")
        return {
            "status": status,
            "next_action": next_action,
            "paper_live_blocked": True,
            "resurrectable_under": invariance.get("dominant_regime", "unknown"),
            "health_score": round(ResearchDirector._bounded(challenge * 0.55 + invariant * 0.45), 5),
        }

    @staticmethod
    def _paper_summary(
        pattern: DiscoveredPattern,
        hypothesis: dict[str, Any],
        adversarial: dict[str, Any],
        invariance: dict[str, Any],
        replay: dict[str, Any],
        lifecycle: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "title": f"{pattern.name} research note",
            "abstract": (
                f"{pattern.side} pattern in {pattern.timeframe}/W{pattern.window_size}: "
                f"{hypothesis['mechanism']} Current lifecycle={lifecycle['status']}."
            ),
            "rule": hypothesis["thesis"],
            "evidence": hypothesis["evidence"],
            "anti_overfit": adversarial,
            "regime": invariance,
            "execution": replay,
            "risks": adversarial["warnings"] + replay["bottlenecks"],
            "death_conditions": hypothesis["kill_criteria"],
            "next_experiment": lifecycle["next_action"],
        }

    def _memory_graph(
        self,
        patterns: list[DiscoveredPattern],
        intelligence_by_key: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        families: dict[str, list[DiscoveredPattern]] = {}
        regimes: dict[str, list[str]] = {}
        for pattern in patterns:
            intelligence = intelligence_by_key.get(pattern.pattern_key, {})
            lifecycle = intelligence.get("lifecycle", {})
            invariance = intelligence.get("invariance", {})
            regime = str(invariance.get("dominant_regime", "unknown"))
            family = pattern.pattern_family_key or pattern.canonical_pattern_key or pattern.pattern_key
            families.setdefault(family, []).append(pattern)
            regimes.setdefault(regime, []).append(pattern.pattern_key)
            nodes.append(
                {
                    "pattern_key": pattern.pattern_key,
                    "name": pattern.name,
                    "family": family,
                    "canonical": pattern.canonical_pattern_key or pattern.pattern_key,
                    "variant_key": pattern.variant_key,
                    "side": pattern.side,
                    "timeframe": pattern.timeframe,
                    "window_size": pattern.window_size,
                    "score": round(float(pattern.score or 0.0), 5),
                    "status": pattern.promotion_status,
                    "lifecycle": lifecycle.get("status", "unknown"),
                    "dominant_regime": regime,
                }
            )
        for family, members in families.items():
            if len(members) <= 1:
                continue
            canonical = sorted(members, key=lambda p: p.score or 0.0, reverse=True)[0]
            for member in members:
                if member.pattern_key == canonical.pattern_key:
                    continue
                edges.append(
                    {
                        "source": member.pattern_key,
                        "target": canonical.pattern_key,
                        "type": "variant_of",
                        "family": family,
                    }
                )
        for regime, pattern_keys in regimes.items():
            if regime == "unknown" or len(pattern_keys) <= 1:
                continue
            hub = f"regime::{regime}"
            nodes.append({"pattern_key": hub, "name": regime, "type": "regime"})
            for pattern_key in pattern_keys[:40]:
                edges.append({"source": pattern_key, "target": hub, "type": "works_in_regime"})
        return {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes[:500],
            "edges": edges[:1000],
            "families": {
                family: {
                    "count": len(members),
                    "best_score": round(max(float(p.score or 0.0) for p in members), 5),
                    "statuses": sorted({p.promotion_status for p in members}),
                }
                for family, members in families.items()
            },
        }

    def _active_learning_agenda(
        self,
        patterns: list[DiscoveredPattern],
        intelligence_by_key: dict[str, dict[str, Any]],
        memory_graph: dict[str, Any],
    ) -> list[dict[str, Any]]:
        agenda: list[dict[str, Any]] = []
        family_counts = {
            family: int(summary.get("count", 0))
            for family, summary in (memory_graph.get("families") or {}).items()
            if isinstance(summary, dict)
        }
        for pattern in patterns:
            intelligence = intelligence_by_key.get(pattern.pattern_key, {})
            lifecycle = intelligence.get("lifecycle", {})
            adversarial = intelligence.get("adversarial_challenge", {})
            foundation = intelligence.get("foundation_learning", {})
            metrics = pattern.metrics_json or {}
            family = pattern.pattern_family_key or pattern.canonical_pattern_key or pattern.pattern_key
            priority = 0.0
            reasons: list[str] = []
            experiment = "observe"
            if metrics.get("confirmation_recommended"):
                priority += 0.35
                reasons.append("underpowered_edge")
                experiment = "expand_universe_same_hypothesis"
            if float(metrics.get("expected_information_gain", 0.0) or 0.0) > 0.05:
                priority += 0.20
                reasons.append("high_information_gain")
                experiment = "sample_similar_regime_more_deeply"
            if adversarial.get("verdict") == "needs_targeted_confirmation":
                priority += 0.18
                reasons.append("adversarial_weakness")
                experiment = "target_failed_adversarial_tests"
            if lifecycle.get("status") == "decaying":
                priority += 0.12
                reasons.append("edge_decay")
                experiment = "run_regime_resurrection_check"
            if family_counts.get(family, 0) >= 4:
                priority -= 0.10
                reasons.append("family_saturated")
            if float(foundation.get("embedding_teacher_score", 0.0) or 0.0) < 0.35:
                priority += 0.08
                reasons.append("weak_embedding_teacher_signal")
            if priority <= 0 and pattern.validation_passed:
                priority = 0.05
                reasons.append("periodic_health_check")
            if priority > 0:
                agenda.append(
                    {
                        "pattern_key": pattern.pattern_key,
                        "name": pattern.name,
                        "priority": round(self._bounded(priority), 5),
                        "experiment": experiment,
                        "reasons": reasons,
                        "blocked_from_execution": True,
                    }
                )
        return sorted(agenda, key=lambda item: float(item["priority"]), reverse=True)[:25]

    @staticmethod
    def _director_state(
        patterns: list[DiscoveredPattern],
        intelligence_by_key: dict[str, dict[str, Any]],
        agenda: list[dict[str, Any]],
    ) -> dict[str, Any]:
        lifecycle_counts: dict[str, int] = {}
        challenge_scores = []
        invariant_scores = []
        for intelligence in intelligence_by_key.values():
            lifecycle = intelligence.get("lifecycle", {})
            status = str(lifecycle.get("status", "unknown"))
            lifecycle_counts[status] = lifecycle_counts.get(status, 0) + 1
            adversarial = intelligence.get("adversarial_challenge", {})
            invariance = intelligence.get("invariance", {})
            challenge_scores.append(float(adversarial.get("challenge_score", 0.0) or 0.0))
            invariant_scores.append(float(invariance.get("invariant_score", 0.0) or 0.0))
        return {
            "pattern_count": len(patterns),
            "lifecycle_counts": lifecycle_counts,
            "avg_challenge_score": round(float(np.mean(challenge_scores)), 5) if challenge_scores else 0.0,
            "avg_invariant_score": round(float(np.mean(invariant_scores)), 5) if invariant_scores else 0.0,
            "agenda_count": len(agenda),
            "top_agenda": agenda[:5],
        }

    def _write_artifacts(
        self,
        summary: dict[str, Any],
        patterns: list[DiscoveredPattern],
        intelligence_by_key: dict[str, dict[str, Any]],
    ) -> dict[str, str]:
        settings = self.settings
        assert settings is not None
        director_dir = settings.reports_path / "research" / "director"
        director_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        payload = {
            "summary": summary,
            "patterns": [
                {
                    "pattern_key": pattern.pattern_key,
                    "name": pattern.name,
                    "intelligence": intelligence_by_key.get(pattern.pattern_key, {}),
                }
                for pattern in patterns
            ],
        }
        json_path = director_dir / f"research_director_{ts}.json"
        md_path = director_dir / f"research_director_{ts}.md"
        graph_path = director_dir / "research_memory_graph.json"
        latest_json = director_dir / "latest_research_director.json"
        latest_md = director_dir / "latest_research_director.md"
        json_text = json.dumps(self._json_clean(payload), indent=2, ensure_ascii=False, default=str)
        json_path.write_text(json_text, encoding="utf-8")
        latest_json.write_text(json_text, encoding="utf-8")
        graph_path.write_text(
            json.dumps(summary["memory_graph"], indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        md_text = self._markdown(summary, patterns, intelligence_by_key)
        md_path.write_text(md_text, encoding="utf-8")
        latest_md.write_text(md_text, encoding="utf-8")
        return {
            "json": str(json_path),
            "markdown": str(md_path),
            "latest_json": str(latest_json),
            "latest_markdown": str(latest_md),
            "memory_graph": str(graph_path),
        }

    @staticmethod
    def _markdown(
        summary: dict[str, Any],
        patterns: list[DiscoveredPattern],
        intelligence_by_key: dict[str, dict[str, Any]],
    ) -> str:
        lines = [
            "# Tradeo Autonomous Research Director",
            "",
            "## Executive State",
            f"- Generated: {summary['generated_at']}",
            f"- Patterns reviewed: {summary['patterns_reviewed']}",
            f"- Hypotheses created: {summary['hypotheses_created']}",
            f"- Memory graph: {summary['memory_graph']['node_count']} nodes / {summary['memory_graph']['edge_count']} edges",
            f"- Agenda items: {len(summary['active_learning_agenda'])}",
            "",
            "## Active Learning Agenda",
        ]
        for item in summary["active_learning_agenda"][:12]:
            lines.append(
                f"- {item['priority']}: {item['name']} -> {item['experiment']} ({', '.join(item['reasons'])})"
            )
        lines.extend(["", "## Research Notes"])
        for pattern in patterns[:20]:
            intelligence = intelligence_by_key.get(pattern.pattern_key, {})
            paper = intelligence.get("paper", {})
            lifecycle = intelligence.get("lifecycle", {})
            adversarial = intelligence.get("adversarial_challenge", {})
            invariance = intelligence.get("invariance", {})
            replay = intelligence.get("market_replay", {})
            lines.extend(
                [
                    "",
                    f"### {pattern.name}",
                    f"- Lifecycle: {lifecycle.get('status')} / health {lifecycle.get('health_score')}",
                    f"- Abstract: {paper.get('abstract')}",
                    f"- Rule: {paper.get('rule')}",
                    f"- Adversarial: {adversarial.get('verdict')} / score {adversarial.get('challenge_score')}",
                    f"- Invariance: {invariance.get('invariant_score')} / regime {invariance.get('dominant_regime')}",
                    f"- Replay: tradability {replay.get('tradability_score')} / bottlenecks {replay.get('bottlenecks')}",
                    f"- Next: {paper.get('next_experiment')}",
                ]
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _positive_value_rate(values: dict[str, Any]) -> float:
        if not values:
            return 0.0
        numeric = []
        for value in values.values():
            try:
                numeric.append(float(value))
            except (TypeError, ValueError):
                continue
        if not numeric:
            return 0.0
        return float(sum(1 for value in numeric if value > 0) / len(numeric))

    @staticmethod
    def _bounded(value: float) -> float:
        return float(max(0.0, min(1.0, value)))

    @staticmethod
    def _json_clean(value: Any) -> Any:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, dict):
            return {str(k): ResearchDirector._json_clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [ResearchDirector._json_clean(v) for v in value]
        if isinstance(value, tuple):
            return [ResearchDirector._json_clean(v) for v in value]
        return value
