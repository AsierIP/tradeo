from __future__ import annotations

from dataclasses import dataclass

from tradeo.core.config import Settings, get_settings
from tradeo.research.types import ClusterCandidate


@dataclass(slots=True)
class ValidationGate:
    """Hard statistical gate for unknown patterns.

    A discovered pattern can be exciting, but it is never tradable merely because
    the cluster looks good. This gate tries to reject curve-fit artifacts early.
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

        if candidate.sample_count < s.discovery_min_samples:
            reasons.append(f"muestras insuficientes: {candidate.sample_count} < {s.discovery_min_samples}")
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
        oos_positive = float(metrics.get("out_of_sample_expectancy_r", 0.0)) > 0
        if not oos_positive:
            warnings.append("out-of-sample expectancy no positiva")
        if float(metrics.get("out_of_sample_profit_factor", 0.0)) < 1.2:
            warnings.append("out-of-sample profit factor demasiado débil")

        hit_rate = float(metrics.get("hit_4r_rate", 0.0))
        if hit_rate < 0.08:
            warnings.append("tasa de 4R baja; puede requerir filtro posterior de entrada")
        if candidate.symbol_count <= 3:
            warnings.append("posible dependencia de pocos símbolos")
        if candidate.year_count <= 1:
            warnings.append("posible dependencia de un solo régimen temporal")

        promotion_status = "rejected"
        if not reasons:
            if premium_passed and oos_positive and float(metrics.get("stability_score", 0.0)) >= s.discovery_min_stability_score:
                promotion_status = "paper_candidate"
            elif premium_passed:
                promotion_status = "premium_candidate"
            elif preferred_passed:
                promotion_status = "lab_candidate"
            elif minimum and float(minimum.get("expectancy_r", 0.0)) > 0:
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
        candidate.metrics["promotion_status"] = promotion_status
        candidate.metrics["promotion_reason"] = self._promotion_reason(promotion_status, best_rr, best_expectancy, best_pf, oos_positive)
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

    @staticmethod
    def _promotion_reason(status: str, best_rr: float, expectancy: float, profit_factor: float, oos_positive: bool) -> str:
        if status == "rejected":
            return "rechazado por filtros estadísticos duros"
        oos = "OOS positivo" if oos_positive else "OOS pendiente/debil"
        return f"{status}: best_rr={best_rr:g}, expectancy={expectancy:.2f}R, PF={profit_factor:.2f}, {oos}"
