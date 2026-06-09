from __future__ import annotations

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

        if candidate.sample_count < s.discovery_min_samples:
            reasons.append(f"muestras insuficientes: {candidate.sample_count} < {s.discovery_min_samples}")
        if train_sample_count < s.discovery_min_samples:
            reasons.append(f"muestras train insuficientes: {train_sample_count} < {s.discovery_min_samples}")
        if candidate.symbol_count < s.discovery_min_symbols:
            reasons.append(f"poca diversidad de símbolos: {candidate.symbol_count} < {s.discovery_min_symbols}")
        if candidate.year_count < s.discovery_min_years:
            reasons.append(f"poca diversidad temporal: {candidate.year_count} < {s.discovery_min_years}")
        if best_expectancy <= 0:
            reasons.append("sin expectancy positiva en ningún R:R evaluado")
        if best_pf <= 1:
            reasons.append("profit factor débil en todos los R:R")
        if best_drawdown > s.discovery_max_drawdown_r:
            reasons.append(f"drawdown excesivo: {best_drawdown:.2f}R > {s.discovery_max_drawdown_r:.2f}R")
        if not minimum or float(minimum.get("expectancy_r", 0.0)) <= 0:
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
            if preferred_passed and oos_positive and float(metrics.get("stability_score", 0.0)) >= s.discovery_min_stability_score:
                promotion_status = "lab_candidate"
            elif preferred_passed or (minimum and float(minimum.get("expectancy_r", 0.0)) > 0):
                promotion_status = "lab_watchlist"
            elif best_expectancy > 0:
                promotion_status = "lab"

        candidate.validation_passed = promotion_status != "rejected"
        candidate.validation_reasons = warnings if candidate.validation_passed else reasons + warnings
        candidate.metrics["validation_warnings"] = warnings
        candidate.metrics["validation_rejections"] = reasons
        candidate.metrics["validation_passed"] = candidate.validation_passed
        candidate.metrics["preferred_rr_passed"] = preferred_passed
        candidate.metrics["premium_rr_passed"] = premium_passed
        candidate.metrics["execution_promotion_blocked"] = premium_passed or promotion_status in {"lab_candidate", "lab_watchlist", "lab"}
        candidate.metrics["promotion_status"] = promotion_status
        candidate.metrics["promotion_reason"] = self._promotion_reason(promotion_status, best_rr, best_expectancy, best_pf, oos_positive)
        candidate.metrics["confirmation_recommended"] = bool(confirmation["recommended"])
        candidate.metrics["confirmation_status"] = "needs_confirmation" if confirmation["recommended"] else ""
        candidate.metrics["confirmation_reason"] = str(confirmation["reason"])
        candidate.metrics["confirmation_priority_score"] = float(confirmation["priority_score"])
        candidate.metrics["confirmation_next_action"] = str(confirmation["next_action"])
        candidate.metrics["rejection_reasons"] = reasons
        return candidate

    def evaluate_many(self, candidates: list[ClusterCandidate]) -> list[ClusterCandidate]:
        return [self.evaluate(candidate) for candidate in candidates]

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
        return max(matches, key=lambda m: float(m.get("expectancy_r", 0.0)))

    @staticmethod
    def _quality_pass(metrics: dict[str, object] | None, min_expectancy: float, min_profit_factor: float) -> bool:
        if not metrics:
            return False
        return float(metrics.get("expectancy_r", 0.0)) >= min_expectancy and float(metrics.get("profit_factor", 0.0)) >= min_profit_factor

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
        stats_ok = adjusted_p is None or float(adjusted_p) <= s.discovery_max_adjusted_p_value
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
