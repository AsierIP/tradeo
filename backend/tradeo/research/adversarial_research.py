from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Any

import numpy as np

from tradeo.research.reward_risk_analyzer import RewardRiskAnalyzer
from tradeo.research.types import Side, WindowSample


@dataclass(slots=True)
class AdversarialResearchEngine:
    """Challenge discovered patterns with deterministic negative controls."""

    min_score_for_pass: float = 0.55

    def analyze(
        self,
        samples: list[WindowSample],
        *,
        baseline_samples: list[WindowSample],
        side: Side,
        rr: float,
        metrics: dict[str, Any],
        causal_invariance: dict[str, Any] | None = None,
        market_replay: dict[str, Any] | None = None,
        observed_outcomes: np.ndarray | None = None,
        baseline_outcomes: np.ndarray | None = None,
    ) -> dict[str, Any]:
        if not samples:
            return self._empty()
        if observed_outcomes is None or len(observed_outcomes) != len(samples):
            observed = np.asarray(
                [RewardRiskAnalyzer._simulate_sample(sample, side, rr)[0] for sample in samples],
                dtype=float,
            )
        else:
            observed = np.asarray(observed_outcomes, dtype=float)
        observed_expectancy = float(np.mean(observed)) if len(observed) else 0.0
        tests = {
            "leakage_probe": self._leakage_probe(samples, observed),
            "opposite_side_placebo": self._opposite_side_placebo(metrics, observed_expectancy),
            "shuffled_assignment_placebo": self._shuffled_assignment_placebo(
                baseline_samples,
                side,
                rr,
                len(samples),
                observed_expectancy,
                baseline_outcomes=baseline_outcomes,
            ),
            "universe_shock": self._universe_shock(samples, observed),
            "date_shock": self._date_shock(samples, observed),
            "cost_shock": self._cost_shock(metrics, market_replay),
            "regime_mismatch": self._regime_mismatch(causal_invariance),
            "parameter_perturbation": self._parameter_perturbation(metrics),
        }
        component_scores = [float(row["score"]) for row in tests.values()]
        challenge_score = float(np.mean(component_scores)) if component_scores else 0.0
        warnings = [
            str(row["warning"])
            for row in tests.values()
            if row.get("warning")
        ]
        rejection_reasons = [
            str(row["name"])
            for row in tests.values()
            if bool(row.get("hard_fail"))
        ]
        return {
            "method": "deterministic_adversarial_research_v1",
            "observed_expectancy_r": round(observed_expectancy, 5),
            "challenge_score": round(float(max(0.0, min(1.0, challenge_score))), 5),
            "challenge_passed": bool(challenge_score >= self.min_score_for_pass and not rejection_reasons),
            "rejection_recommended": bool(rejection_reasons),
            "rejection_reasons": rejection_reasons,
            "warnings": warnings,
            "tests": tests,
        }

    def _leakage_probe(
        self,
        samples: list[WindowSample],
        outcomes: np.ndarray,
    ) -> dict[str, Any]:
        matrix = self._matrix(samples)
        if matrix.size == 0 or len(outcomes) < 8:
            return self._test("leakage_probe", 0.65, warning="leakage probe underpowered")
        dims = min(matrix.shape[1], 96)
        correlations = [abs(self._corr(matrix[:, idx], outcomes)) for idx in range(dims)]
        max_corr = max(correlations) if correlations else 0.0
        score = 1.0 - max(0.0, min(1.0, (max_corr - 0.55) / 0.40))
        hard_fail = bool(max_corr >= 0.92 and len(outcomes) >= 20)
        warning = "posible leakage: dimension de embedding predice futuro demasiado bien" if max_corr >= 0.85 else ""
        return self._test(
            "leakage_probe",
            score,
            hard_fail=hard_fail,
            warning=warning,
            details={"max_abs_corr": round(float(max_corr), 5), "dims_checked": dims},
        )

    @staticmethod
    def _opposite_side_placebo(metrics: dict[str, Any], observed_expectancy: float) -> dict[str, Any]:
        opposite = metrics.get("opposite_side", {})
        if not isinstance(opposite, dict):
            return AdversarialResearchEngine._test(
                "opposite_side_placebo",
                0.60,
                warning="opposite side placebo unavailable",
            )
        opposite_expectancy = float(opposite.get("best_expectancy_r", opposite.get("expectancy_r", 0.0)))
        ratio = opposite_expectancy / max(abs(observed_expectancy), 0.10)
        score = 1.0 - max(0.0, min(1.0, ratio))
        warning = "placebo direccional: el lado contrario tambien parece fuerte" if ratio >= 0.65 else ""
        return AdversarialResearchEngine._test(
            "opposite_side_placebo",
            score,
            hard_fail=bool(ratio >= 1.0 and opposite_expectancy > 0),
            warning=warning,
            details={
                "opposite_expectancy_r": round(float(opposite_expectancy), 5),
                "placebo_ratio": round(float(ratio), 5),
            },
        )

    def _shuffled_assignment_placebo(
        self,
        baseline_samples: list[WindowSample],
        side: Side,
        rr: float,
        size: int,
        observed_expectancy: float,
        *,
        baseline_outcomes: np.ndarray | None = None,
    ) -> dict[str, Any]:
        if not baseline_samples or size <= 0:
            return self._test("shuffled_assignment_placebo", 0.55, warning="placebo baseline unavailable")
        if baseline_outcomes is None or len(baseline_outcomes) != len(baseline_samples):
            outcomes = np.asarray(
                [RewardRiskAnalyzer._simulate_sample(sample, side, rr)[0] for sample in baseline_samples],
                dtype=float,
            )
        else:
            outcomes = np.asarray(baseline_outcomes, dtype=float)
        if len(outcomes) == 0:
            return self._test("shuffled_assignment_placebo", 0.55, warning="placebo outcomes unavailable")
        start = self._seed_index(side, rr, size, len(outcomes))
        ordered = np.roll(outcomes, start)
        draw = ordered[: min(size, len(ordered))]
        placebo_expectancy = float(np.mean(draw)) if len(draw) else 0.0
        lift = observed_expectancy - placebo_expectancy
        score = max(0.0, min(1.0, lift / max(abs(observed_expectancy), 0.25)))
        warning = "shuffled/placebo assignment conserva demasiado edge" if lift <= 0.03 else ""
        return self._test(
            "shuffled_assignment_placebo",
            score,
            hard_fail=bool(lift <= 0 and observed_expectancy > 0),
            warning=warning,
            details={
                "placebo_expectancy_r": round(placebo_expectancy, 5),
                "observed_minus_placebo_r": round(lift, 5),
                "placebo_sample_count": int(len(draw)),
            },
        )

    @staticmethod
    def _universe_shock(samples: list[WindowSample], outcomes: np.ndarray) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for sample in samples:
            counts[sample.symbol] = counts.get(sample.symbol, 0) + 1
        if len(counts) <= 1:
            return AdversarialResearchEngine._test(
                "universe_shock",
                0.0,
                hard_fail=True,
                warning="patron depende de un solo simbolo",
            )
        top_symbol = max(counts.items(), key=lambda item: item[1])[0]
        keep = np.asarray([sample.symbol != top_symbol for sample in samples], dtype=bool)
        if int(np.sum(keep)) < 3:
            return AdversarialResearchEngine._test(
                "universe_shock",
                0.10,
                hard_fail=True,
                warning="sin soporte despues de remover simbolo dominante",
            )
        shocked_expectancy = float(np.mean(outcomes[keep]))
        observed = float(np.mean(outcomes)) if len(outcomes) else 0.0
        score = 1.0 if shocked_expectancy > 0 else max(0.0, 1.0 + shocked_expectancy / 0.50)
        warning = "universe shock negativo al remover simbolo dominante" if shocked_expectancy <= 0 else ""
        return AdversarialResearchEngine._test(
            "universe_shock",
            score,
            hard_fail=bool(shocked_expectancy <= 0 and observed > 0),
            warning=warning,
            details={
                "removed_symbol": top_symbol,
                "remaining_sample_count": int(np.sum(keep)),
                "shocked_expectancy_r": round(shocked_expectancy, 5),
            },
        )

    @staticmethod
    def _date_shock(samples: list[WindowSample], outcomes: np.ndarray) -> dict[str, Any]:
        if len(samples) < 8:
            return AdversarialResearchEngine._test("date_shock", 0.55, warning="date shock underpowered")
        order = np.argsort([sample.end for sample in samples])
        sorted_outcomes = outcomes[order]
        halves = np.array_split(sorted_outcomes, 2)
        first = float(np.mean(halves[0])) if len(halves[0]) else 0.0
        second = float(np.mean(halves[1])) if len(halves[1]) else 0.0
        worst = min(first, second)
        gap = abs(first - second)
        score = (1.0 if worst > 0 else max(0.0, 1.0 + worst / 0.50)) * (1.0 - min(0.5, gap / 2.0))
        warning = "date shock muestra regimen temporal fragil" if worst <= 0 else ""
        return AdversarialResearchEngine._test(
            "date_shock",
            score,
            hard_fail=bool(worst <= -0.10),
            warning=warning,
            details={"first_half_expectancy_r": round(first, 5), "second_half_expectancy_r": round(second, 5)},
        )

    @staticmethod
    def _cost_shock(
        metrics: dict[str, Any],
        market_replay: dict[str, Any] | None,
    ) -> dict[str, Any]:
        cost_passed = metrics.get("cost_stress_passed")
        replay_expectancy = (
            float(market_replay.get("expected_expectancy_r", 0.0))
            if isinstance(market_replay, dict)
            else 0.0
        )
        replay_passed = bool(market_replay.get("passed", False)) if isinstance(market_replay, dict) else True
        score = 0.5 * (1.0 if cost_passed is not False else 0.0) + 0.5 * (
            1.0 if replay_passed and replay_expectancy > 0 else 0.0
        )
        warning = "cost/market replay shock rompe el edge" if score < 0.5 else ""
        return AdversarialResearchEngine._test(
            "cost_shock",
            score,
            hard_fail=bool(score <= 0.0),
            warning=warning,
            details={"cost_stress_passed": cost_passed, "replay_expectancy_r": round(replay_expectancy, 5)},
        )

    @staticmethod
    def _regime_mismatch(causal_invariance: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(causal_invariance, dict):
            return AdversarialResearchEngine._test(
                "regime_mismatch",
                0.55,
                warning="causal invariance unavailable",
            )
        score = float(causal_invariance.get("invariance_score", 0.0))
        warning = "regime mismatch: invariancia insuficiente" if score < 0.45 else ""
        return AdversarialResearchEngine._test(
            "regime_mismatch",
            score,
            hard_fail=bool(score < 0.25),
            warning=warning,
            details={
                "invariance_score": round(score, 5),
                "expected_fail_bucket_count": len(causal_invariance.get("expected_fail_buckets", [])),
            },
        )

    @staticmethod
    def _parameter_perturbation(metrics: dict[str, Any]) -> dict[str, Any]:
        decay_passed = metrics.get("edge_decay_passed")
        decay_score = float(metrics.get("edge_decay_parameter_score", 0.0))
        score = 1.0 - max(0.0, min(1.0, decay_score))
        warning = "parameter perturbation: edge muy sensible a R:R" if decay_passed is False else ""
        return AdversarialResearchEngine._test(
            "parameter_perturbation",
            score,
            hard_fail=bool(decay_passed is False and decay_score >= 0.75),
            warning=warning,
            details={"edge_decay_parameter_score": round(decay_score, 5), "edge_decay_passed": decay_passed},
        )

    @staticmethod
    def _matrix(samples: list[WindowSample]) -> np.ndarray:
        if not samples:
            return np.empty((0, 0), dtype=float)
        lengths = [len(sample.vector) for sample in samples]
        if not lengths:
            return np.empty((0, 0), dtype=float)
        common = max(set(lengths), key=lengths.count)
        vectors = [np.asarray(sample.vector, dtype=float) for sample in samples if len(sample.vector) == common]
        if not vectors:
            return np.empty((0, 0), dtype=float)
        return np.nan_to_num(np.vstack(vectors), nan=0.0, posinf=0.0, neginf=0.0)

    @staticmethod
    def _corr(left: np.ndarray, right: np.ndarray) -> float:
        if len(left) != len(right) or len(left) < 3:
            return 0.0
        left_std = float(np.std(left))
        right_std = float(np.std(right))
        if left_std <= 1e-12 or right_std <= 1e-12:
            return 0.0
        return float(np.corrcoef(left, right)[0, 1])

    @staticmethod
    def _seed_index(side: Side, rr: float, size: int, population: int) -> int:
        digest = blake2b(digest_size=4)
        digest.update(f"{side}|{rr:g}|{size}|{population}".encode())
        return int.from_bytes(digest.digest(), "big", signed=False) % max(1, population)

    @staticmethod
    def _test(
        name: str,
        score: float,
        *,
        hard_fail: bool = False,
        warning: str = "",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "score": round(float(max(0.0, min(1.0, score))), 5),
            "passed": bool(score >= 0.50 and not hard_fail),
            "hard_fail": bool(hard_fail),
            "warning": warning,
            "details": details or {},
        }

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "method": "deterministic_adversarial_research_v1",
            "observed_expectancy_r": 0.0,
            "challenge_score": 0.0,
            "challenge_passed": False,
            "rejection_recommended": True,
            "rejection_reasons": ["no_samples"],
            "warnings": ["sin muestras para adversarial research"],
            "tests": {},
        }
