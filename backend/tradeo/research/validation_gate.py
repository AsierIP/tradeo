from __future__ import annotations

import math
from dataclasses import dataclass

from tradeo.core.config import Settings, get_settings
from tradeo.research.types import ClusterCandidate


@dataclass(slots=True)
class ValidationGate:
    """Hard statistical gate for unknown patterns.

    A discovered pattern can be exciting, but it is never tradable merely because
    the cluster looks good. This gate rejects curve-fit artifacts early and keeps
    every discovery-stage result below any paper/live promotion state. Paper
    promotion belongs to the Director gate after auditable paper trades, fills,
    costs and clean out-of-sample evidence exist.
    """

    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def evaluate(self, candidate: ClusterCandidate) -> ClusterCandidate:
        s = self.settings
        metrics = candidate.metrics
        reasons: list[str] = []
        warnings: list[str] = []
        self._sanitize_numeric_metrics(candidate, metrics, reasons)
        rr_metrics = metrics.get("rr_metrics", {})
        best_rr = float(metrics.get("best_rr", 0.0))
        best_expectancy = float(metrics.get("best_expectancy_r", metrics.get("expectancy_r", 0.0)))
        best_pf = float(metrics.get("best_profit_factor", metrics.get("profit_factor", 0.0)))
        best_drawdown = float(metrics.get("best_max_drawdown_r", metrics.get("max_drawdown_r", 0.0)))
        preferred = self._metrics_at_or_above(rr_metrics, s.discovery_candidate_reward_risk)
        premium = self._metrics_at_or_above(rr_metrics, s.discovery_premium_reward_risk)
        minimum = self._metrics_at_or_above(rr_metrics, s.discovery_min_reward_risk)
        preferred_passed = self._quality_pass(preferred, s.discovery_min_expectancy_r, s.discovery_min_profit_factor)
        premium_passed = self._quality_pass(premium, s.discovery_min_expectancy_r, s.discovery_min_profit_factor)
        train_sample_count = int(metrics.get("train_sample_count", candidate.sample_count))

        quant = metrics.get("quant_validation", {})
        if not isinstance(quant, dict):
            quant = {}
        effective_samples = metrics.get("effective_sample_count")
        if candidate.sample_count < s.discovery_min_samples:
            reasons.append(f"muestras insuficientes: {candidate.sample_count} < {s.discovery_min_samples}")
        if effective_samples is not None and float(effective_samples) < s.discovery_min_effective_samples:
            reasons.append(
                "muestras efectivas insuficientes (solapamiento/pseudo-replicacion): "
                f"n_eff={float(effective_samples):.1f} < {s.discovery_min_effective_samples:g}"
            )
        if metrics.get("fdr_passed") is False:
            reasons.append(
                f"no supera BH-FDR del run (q={float(metrics.get('fdr_q', s.discovery_fdr_q)):g}, "
                f"p={float(metrics.get('null_p_value', 1.0)):.4f}, "
                f"tests={int(metrics.get('fdr_test_count', 0) or 0)})"
            )
        if train_sample_count < s.discovery_min_samples:
            reasons.append(f"muestras train insuficientes: {train_sample_count} < {s.discovery_min_samples}")
        if candidate.symbol_count < s.discovery_min_symbols:
            reasons.append(f"poca diversidad de símbolos: {candidate.symbol_count} < {s.discovery_min_symbols}")
        if candidate.year_count < s.discovery_min_years:
            reasons.append(f"poca diversidad temporal: {candidate.year_count} < {s.discovery_min_years}")
        concentration = metrics.get("concentration_checks")
        if isinstance(concentration, dict) and concentration.get("passed") is False:
            reasons.append(
                "concentracion excesiva del cluster: "
                + ", ".join(str(reason) for reason in concentration.get("reasons", [])[:3])
            )
        if best_expectancy <= 0:
            reasons.append("sin expectancy positiva en ningún R:R evaluado")
        if best_pf <= 1:
            reasons.append("profit factor débil en todos los R:R")
        if best_drawdown > s.discovery_max_drawdown_r:
            reasons.append(f"drawdown excesivo: {best_drawdown:.2f}R > {s.discovery_max_drawdown_r:.2f}R")
        if not minimum or self._finite_float(minimum.get("expectancy_r", 0.0), 0.0) <= 0:
            warnings.append(f"no demuestra edge positivo en {s.discovery_min_reward_risk:g}R")
        if float(metrics.get("profit_factor", best_pf)) < s.discovery_min_profit_factor and not preferred_passed:
            warnings.append(
                f"profit factor insuficiente: {best_pf:.2f} < {s.discovery_min_profit_factor:.2f}"
            )
        if float(metrics.get("expectancy_r", best_expectancy)) < s.discovery_min_expectancy_r and not preferred_passed:
            warnings.append(
                f"expectancy insuficiente: {best_expectancy:.2f}R < {s.discovery_min_expectancy_r:.2f}R"
            )
        if float(metrics.get("stability_score", 0.0)) < s.discovery_min_stability_score:
            reasons.append(
                f"estabilidad insuficiente: {float(metrics.get('stability_score', 0.0)):.2f} < {s.discovery_min_stability_score:.2f}"
            )
        adjusted_p = metrics.get("adjusted_p_value")
        if adjusted_p is not None and float(adjusted_p) > s.discovery_max_adjusted_p_value:
            reasons.append(
                f"significancia insuficiente: p_adj={float(adjusted_p):.2f} > {s.discovery_max_adjusted_p_value:.2f}"
            )
        wrc_p = metrics.get("wrc_p_value")
        if wrc_p is not None and float(wrc_p) > s.discovery_max_adjusted_p_value:
            wrc_label = (
                "White Reality Check"
                if bool(metrics.get("reality_check_formal_test", False))
                else "bootstrap reality proxy WRC-like"
            )
            reasons.append(
                f"{wrc_label} insuficiente: p={float(wrc_p):.2f} > {s.discovery_max_adjusted_p_value:.2f}"
            )
        spa_p = metrics.get("spa_p_value")
        if spa_p is not None and float(spa_p) > s.discovery_max_adjusted_p_value:
            spa_label = (
                "SPA formal"
                if bool(metrics.get("reality_check_formal_test", False))
                else "bootstrap reality proxy SPA-like"
            )
            reasons.append(f"{spa_label} insuficiente: p={float(spa_p):.2f} > {s.discovery_max_adjusted_p_value:.2f}")
        if metrics.get("statistical_edge_passed") is False:
            lift = float(metrics.get("expectancy_lift_r", 0.0))
            warnings.append(f"edge vs baseline débil: lift={lift:.2f}R")
        expectancy_ci_low = metrics.get("expectancy_ci_low")
        if expectancy_ci_low is not None and float(expectancy_ci_low) < s.discovery_min_expectancy_ci_low:
            reasons.append(
                f"intervalo bootstrap débil: ci_low={float(expectancy_ci_low):.2f}R < {s.discovery_min_expectancy_ci_low:.2f}R"
            )
        overfit_score = metrics.get("overfit_score")
        if overfit_score is not None and float(overfit_score) > s.discovery_max_overfit_score:
            reasons.append(f"riesgo de overfit alto: {float(overfit_score):.2f} > {s.discovery_max_overfit_score:.2f}")
        purged_fold_count = int(metrics.get("purged_cv_fold_count", 0))
        if purged_fold_count:
            purged_rate = float(metrics.get("purged_cv_positive_rate", 0.0))
            if purged_rate < s.discovery_min_walk_forward_positive_rate:
                reasons.append(
                    "purged combinatorial CV inestable: "
                    f"{purged_rate:.2f} < {s.discovery_min_walk_forward_positive_rate:.2f}"
                )
        deflated_psr = metrics.get("deflated_sharpe_probability")
        if deflated_psr is not None and float(deflated_psr) < 0.50:
            reasons.append(f"Deflated Sharpe débil: prob={float(deflated_psr):.2f} < 0.50")
        probabilistic_sharpe = metrics.get("probabilistic_sharpe")
        if probabilistic_sharpe is not None and float(probabilistic_sharpe) < 0.55:
            warnings.append(f"Probabilistic Sharpe bajo: {float(probabilistic_sharpe):.2f}")
        if metrics.get("edge_decay_passed") is False:
            reasons.append("edge decae demasiado ante cambios cercanos de R:R")
        if metrics.get("cost_stress_passed") is False:
            reasons.append(f"edge no sobrevive coste x{s.discovery_required_cost_stress_multiplier:g}")
        replay = metrics.get("market_replay", {})
        if isinstance(replay, dict) and replay:
            replay_expectancy = float(replay.get("expected_expectancy_r", 0.0))
            replay_fill_ratio = float(replay.get("avg_fill_ratio", 0.0))
            if replay_expectancy <= 0:
                reasons.append(f"market replay sin expectancy positiva: {replay_expectancy:.2f}R")
            if replay_fill_ratio < 0.25:
                reasons.append(f"market replay fill ratio demasiado bajo: {replay_fill_ratio:.2f}")
            elif replay_fill_ratio < 0.45:
                warnings.append(f"market replay fill ratio debil: {replay_fill_ratio:.2f}")
            for warning in replay.get("warnings", [])[:3]:
                warnings.append(str(warning))
        causal = metrics.get("causal_invariance", {})
        if isinstance(causal, dict) and causal:
            invariance_score = float(causal.get("invariance_score", 0.0))
            symbol_dependency = causal.get("symbol_dependency", {})
            no_three_symbols = (
                bool(symbol_dependency.get("no_three_symbol_dependency", False))
                if isinstance(symbol_dependency, dict)
                else True
            )
            if not no_three_symbols:
                reasons.append("dependencia de <=3 simbolos/eventos en invariancia causal")
            if invariance_score < 0.25:
                reasons.append(f"invariancia causal muy debil: {invariance_score:.2f}")
            elif invariance_score < 0.45:
                warnings.append(f"invariancia causal debil: {invariance_score:.2f}")
            expected_fail_count = len(causal.get("expected_fail_buckets", []))
            if expected_fail_count:
                warnings.append(f"{expected_fail_count} buckets expected-fail detectados")
        adversarial = metrics.get("adversarial_challenge", {})
        if isinstance(adversarial, dict) and adversarial:
            challenge_score = float(adversarial.get("challenge_score", 0.0))
            for reason in adversarial.get("rejection_reasons", [])[:5]:
                reasons.append(f"adversarial rejection: {reason}")
            if challenge_score < 0.45:
                reasons.append(f"challenge score bajo: {challenge_score:.2f} < 0.45")
            elif challenge_score < 0.55:
                warnings.append(f"challenge score liminal: {challenge_score:.2f} < 0.55")
            for warning in adversarial.get("warnings", [])[:5]:
                warnings.append(str(warning))
        teacher = metrics.get("foundation_teacher", {})
        if isinstance(teacher, dict):
            digest = teacher.get("pretraining_digest", {})
            teacher_score = (
                float(digest.get("embedding_quality_score", 0.0))
                if isinstance(digest, dict)
                else 0.0
            )
            if teacher_score and teacher_score < 0.30:
                warnings.append(f"teacher embedding quality debil: {teacher_score:.2f}")
        if "avg_fill_probability" in metrics and float(metrics.get("avg_fill_probability", 1.0)) < 0.35:
            reasons.append(
                "baja probabilidad de fill estimada: "
                f"{float(metrics.get('avg_fill_probability', 0.0)):.2f}"
            )
        if (
            "p25_max_size_usd" in metrics
            and 0.0 < float(metrics.get("p25_max_size_usd", 0.0)) < s.account_risk_usd * 5
        ):
            warnings.append("tamano operable bajo para el patron; limitar size o exigir mas liquidez")
        fold_count = int(metrics.get("walk_forward_fold_count", 0))
        if fold_count:
            fold_rate = float(metrics.get("walk_forward_positive_fold_rate", 0.0))
            if fold_rate < s.discovery_min_walk_forward_positive_rate:
                reasons.append(
                    f"walk-forward inestable: {fold_rate:.2f} < {s.discovery_min_walk_forward_positive_rate:.2f}"
                )
        else:
            warnings.append("walk-forward sin folds suficientes")
        oos_positive = float(metrics.get("out_of_sample_expectancy_r", 0.0)) > 0
        if not oos_positive:
            warnings.append("out-of-sample expectancy no positiva")
        if float(metrics.get("out_of_sample_profit_factor", 0.0)) < 1.2:
            warnings.append("out-of-sample profit factor demasiado débil")

        hit_rate = float(metrics.get("hit_4r_rate", 0.0))
        if hit_rate < 0.08:
            warnings.append("tasa de 4R baja; puede requerir filtro posterior de entrada")
        operational = metrics.get("operational_trigger", {})
        trigger_rate = float(operational.get("trigger_rate", 0.0)) if isinstance(operational, dict) else 0.0
        if trigger_rate < 0.25:
            warnings.append("baja tasa de trigger operativo; requiere filtro de entrada estricto")
        if candidate.symbol_count <= 3:
            warnings.append("posible dependencia de pocos símbolos")
        if candidate.year_count <= 1:
            warnings.append("posible dependencia de un solo régimen temporal")
        if premium_passed:
            warnings.append(
                "premium/paper promotion bloqueada en discovery: requiere Director gate con trades, fills, costes y OOS limpio"
            )
        confirmation = self._confirmation_candidate(
            candidate=candidate,
            hard_reasons=reasons,
            best_expectancy=best_expectancy,
            best_pf=best_pf,
            best_drawdown=best_drawdown,
            oos_positive=oos_positive,
            train_sample_count=train_sample_count,
        )
        if confirmation["recommended"]:
            warnings.append(str(confirmation["reason"]))

        promotion_status = "rejected"
        if not reasons:
            # Discovery can only create lab-stage states. It must never promote to
            # paper/live from simulated research R metrics, even when those metrics
            # look strong. The Director gate owns all execution-stage promotion.
            if (
                preferred_passed
                and oos_positive
                and float(metrics.get("stability_score", 0.0)) >= s.discovery_min_stability_score
            ):
                promotion_status = "lab_candidate"
            elif preferred_passed or (
                minimum and self._finite_float(minimum.get("expectancy_r", 0.0), 0.0) > 0
            ):
                promotion_status = "lab_watchlist"
            elif best_expectancy > 0:
                promotion_status = "lab"

        if promotion_status == "lab_candidate":
            # lab_candidate is the highest discovery state, so it additionally
            # requires the family-deflated Sharpe and a strictly positive
            # stationary-bootstrap CI on the deduplicated, uniqueness-weighted
            # expectancy. Failures downgrade instead of rejecting: the evidence
            # is weak, not contradicted.
            dsr_family = metrics.get("dsr_family")
            dsr_family_value = self._finite_float_or_none(dsr_family)
            if dsr_family_value is None:
                promotion_status = "lab_watchlist"
                warnings.append(
                    "lab_candidate bloqueado: DSR de familia no calculable (faltan trials o sr_std del ledger)"
                )
            elif dsr_family_value < s.discovery_min_dsr:
                promotion_status = "lab_watchlist"
                warnings.append(
                    f"lab_candidate bloqueado: DSR familia {dsr_family_value:.3f} < {s.discovery_min_dsr:g} "
                    f"(N_trials={int(metrics.get('dsr_family_n_trials', 0) or 0)})"
                )
            stationary_ci_low = quant.get("expectancy_ci95_low")
            stationary_ci_low_value = self._finite_float_or_none(stationary_ci_low)
            if stationary_ci_low is not None and (
                stationary_ci_low_value is None or stationary_ci_low_value <= 0.0
            ):
                promotion_status = "lab_watchlist"
                low_label = "no finito" if stationary_ci_low_value is None else f"{stationary_ci_low_value:.3f}R"
                warnings.append(
                    "lab_candidate bloqueado: IC95 stationary-bootstrap del expectancy ponderado "
                    f"no positivo (low={low_label})"
                )

        survivorship_biased = metrics.get("survivorship_biased")
        universe_pit = metrics.get("universe_point_in_time")
        if promotion_status == "lab_candidate" and (
            survivorship_biased is True or universe_pit is False
        ):
            cap_state = str(s.survivorship_cap_state or "lab_watchlist")
            if cap_state not in {"lab", "lab_watchlist", "rejected"}:
                cap_state = "lab_watchlist"
            promotion_status = cap_state
            metrics["survivorship_cap_applied"] = True
            warnings.append(
                "lab_candidate bloqueado: universo historico no point-in-time; "
                f"cap aplicado a {promotion_status}"
            )
        else:
            metrics["survivorship_cap_applied"] = False

        candidate.validation_passed = promotion_status != "rejected"
        candidate.validation_reasons = warnings if candidate.validation_passed else reasons + warnings
        candidate.metrics["validation_warnings"] = warnings
        candidate.metrics["validation_rejections"] = reasons
        candidate.metrics["validation_passed"] = candidate.validation_passed
        candidate.metrics["preferred_rr_passed"] = preferred_passed
        candidate.metrics["premium_rr_passed"] = premium_passed
        candidate.metrics["execution_promotion_blocked"] = (
            premium_passed or promotion_status in {"lab_candidate", "lab_watchlist", "lab"}
        )
        candidate.metrics["promotion_status"] = promotion_status
        candidate.metrics["promotion_reason"] = self._promotion_reason(
            promotion_status,
            best_rr,
            best_expectancy,
            best_pf,
            oos_positive,
        )
        candidate.metrics["confirmation_recommended"] = bool(confirmation["recommended"])
        candidate.metrics["confirmation_status"] = "needs_confirmation" if confirmation["recommended"] else ""
        candidate.metrics["confirmation_reason"] = str(confirmation["reason"])
        candidate.metrics["confirmation_priority_score"] = float(confirmation["priority_score"])
        candidate.metrics["confirmation_next_action"] = str(confirmation["next_action"])
        candidate.metrics["rejection_reasons"] = reasons
        return candidate

    def evaluate_many(self, candidates: list[ClusterCandidate]) -> list[ClusterCandidate]:
        return [self.evaluate(candidate) for candidate in candidates]

    def _sanitize_numeric_metrics(
        self,
        candidate: ClusterCandidate,
        metrics: dict[str, object],
        reasons: list[str],
    ) -> None:
        s = self.settings
        assert s is not None
        defaults = {
            "train_sample_count": 0.0,
            "effective_sample_count": 0.0,
            "best_rr": 0.0,
            "best_expectancy_r": 0.0,
            "expectancy_r": 0.0,
            "best_profit_factor": 0.0,
            "profit_factor": 0.0,
            "best_max_drawdown_r": float(s.discovery_max_drawdown_r) + 1.0,
            "max_drawdown_r": float(s.discovery_max_drawdown_r) + 1.0,
            "stability_score": 0.0,
            "null_p_value": 1.0,
            "adjusted_p_value": 1.0,
            "wrc_p_value": 1.0,
            "spa_p_value": 1.0,
            "expectancy_lift_r": 0.0,
            "expectancy_ci_low": float(s.discovery_min_expectancy_ci_low) - 1.0,
            "overfit_score": float(s.discovery_max_overfit_score) + 1.0,
            "purged_cv_fold_count": 0.0,
            "purged_cv_positive_rate": 0.0,
            "deflated_sharpe_probability": 0.0,
            "probabilistic_sharpe": 0.0,
            "avg_fill_probability": 0.0,
            "p25_max_size_usd": 0.0,
            "walk_forward_fold_count": 0.0,
            "walk_forward_positive_fold_rate": 0.0,
            "out_of_sample_expectancy_r": 0.0,
            "out_of_sample_profit_factor": 0.0,
            "hit_4r_rate": 0.0,
            "dsr_family_n_trials": 0.0,
        }
        for key, default in defaults.items():
            if key not in metrics:
                continue
            value = self._finite_float_or_none(metrics.get(key))
            if value is None:
                metrics[key] = default
                reasons.append(f"metrica no finita en validation gate: {key}")
        if self._finite_float_or_none(candidate.sample_count) is None:
            reasons.append("sample_count no finito en validation gate")

    @staticmethod
    def _metrics_at_or_above(rr_metrics: object, rr: float) -> dict[str, object] | None:
        if not isinstance(rr_metrics, dict):
            return None
        matches = []
        for key, value in rr_metrics.items():
            try:
                level = float(key)
            except (TypeError, ValueError):
                continue
            if level >= rr and isinstance(value, dict):
                matches.append(value)
        if not matches:
            return None
        return max(matches, key=lambda m: ValidationGate._finite_float(m.get("expectancy_r", 0.0), 0.0))

    @staticmethod
    def _quality_pass(metrics: dict[str, object] | None, min_expectancy: float, min_profit_factor: float) -> bool:
        if not metrics:
            return False
        expectancy = ValidationGate._finite_float(metrics.get("expectancy_r", 0.0), 0.0)
        profit_factor = ValidationGate._finite_float(metrics.get("profit_factor", 0.0), 0.0)
        return expectancy >= min_expectancy and profit_factor >= min_profit_factor

    @staticmethod
    def _finite_float(value: object, default: float) -> float:
        converted = ValidationGate._finite_float_or_none(value)
        return default if converted is None else converted

    @staticmethod
    def _finite_float_or_none(value: object) -> float | None:
        try:
            converted = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        return converted if math.isfinite(converted) else None

    def _confirmation_candidate(
        self,
        *,
        candidate: ClusterCandidate,
        hard_reasons: list[str],
        best_expectancy: float,
        best_pf: float,
        best_drawdown: float,
        oos_positive: bool,
        train_sample_count: int,
    ) -> dict[str, object]:
        s = self.settings
        assert s is not None
        sample_limited = any(reason.startswith("muestras") for reason in hard_reasons)
        if not sample_limited:
            return self._no_confirmation()
        adjusted_p = candidate.metrics.get("adjusted_p_value")
        adjusted_p_value = self._finite_float(adjusted_p, 1.0) if adjusted_p is not None else None
        stats_ok = adjusted_p_value is None or adjusted_p_value <= s.discovery_max_adjusted_p_value
        enough_seed_samples = candidate.sample_count >= s.discovery_confirmation_min_samples
        enough_train_samples = train_sample_count >= max(20, s.discovery_confirmation_min_samples // 2)
        quality_ok = (
            best_expectancy >= s.discovery_confirmation_min_expectancy_r
            and best_pf >= s.discovery_confirmation_min_profit_factor
            and best_drawdown <= s.discovery_max_drawdown_r
            and oos_positive
            and stats_ok
        )
        if not (enough_seed_samples and enough_train_samples and quality_ok):
            return self._no_confirmation()
        priority = (
            max(0.0, best_expectancy) * 0.45
            + min(best_pf / 4.0, 1.0) * 0.25
            + max(0.0, float(candidate.metrics.get("expectancy_lift_r", 0.0))) * 0.20
            + min(candidate.sample_count / max(s.discovery_min_samples, 1), 1.0) * 0.10
        )
        return {
            "recommended": True,
            "reason": (
                "requiere confirmación ampliada: edge fuerte pero muestra train/total insuficiente "
                f"({train_sample_count}/{candidate.sample_count})"
            ),
            "priority_score": round(float(priority), 5),
            "next_action": "rerun con universo/periodo ampliado y mismos window_size/side antes de promocionar",
        }

    @staticmethod
    def _no_confirmation() -> dict[str, object]:
        return {
            "recommended": False,
            "reason": "",
            "priority_score": 0.0,
            "next_action": "",
        }

    @staticmethod
    def _promotion_reason(status: str, best_rr: float, expectancy: float, profit_factor: float, oos_positive: bool) -> str:
        if status == "rejected":
            return "rechazado por filtros estadísticos duros"
        oos = "OOS positivo" if oos_positive else "OOS pendiente/debil"
        return f"{status}: best_rr={best_rr:g}, expectancy={expectancy:.2f}R, PF={profit_factor:.2f}, {oos}; paper/live requiere Director gate"
