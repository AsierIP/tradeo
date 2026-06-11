"""Nested optimization with an outer-fold PBO report (Wave4-D).

Closes the ImprovementAgent gap "Nested Optuna + outer-fold PBO report"
without adding a hard dependency on Optuna:

- The candidate variants are already fully enumerated by the ImprovementAgent
  grid, so the inner optimization is a *selection* problem over M variants.
- Inner selection runs on the train periods (complement of each outer fold).
  When Optuna is installed and the variant count exceeds the inner trial
  budget, a seeded ``TPESampler`` searches the categorical variant space with
  pruning disabled (the objective is a cheap deterministic mean, there are no
  intermediate values to prune on). Otherwise a deterministic exhaustive scan
  (argmax with first-index tie-break) is used — strictly better than any
  sampler when the budget covers the space, and bit-for-bit reproducible.
- Each outer fold then evaluates the inner winner out-of-fold: its rank among
  all M variants gives omega = rank/(M+1) and lambda = ln(omega/(1-omega)),
  as in CSCV (Bailey, Borwein, Lopez de Prado, Zhu 2017). The outer-fold PBO
  is the fraction of folds with lambda <= 0.

Honest limitations (do not overclaim):
- Folds are contiguous splits of the aggregated performance periods (monthly
  R buckets upstream); no embargo/purge is applied at this aggregation level.
- Train = complement of the outer fold (CSCV-style), so train may contain
  periods after the outer fold; this measures selection-overfitting, not a
  causal walk-forward forecast.
- This is an additional anti-overfit *blocker* layered on top of the existing
  CSCV PBO and plateau guards. It never relaxes them.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np

METHOD = "nested_outer_fold_pbo_v1"


def optuna_available() -> bool:
    try:
        import optuna  # noqa: F401
    except ImportError:
        return False
    return True


def _blocked(reason: str, **extra: Any) -> dict[str, Any]:
    report: dict[str, Any] = {
        "method": METHOD,
        "passed": False,
        "blocked": True,
        "reason": reason,
        "optuna_available": optuna_available(),
    }
    report.update(extra)
    return report


def _inner_select_exhaustive(inner_means: np.ndarray) -> tuple[int, str]:
    return int(np.argmax(inner_means)), "exhaustive_deterministic"


def _inner_select_optuna(inner_means: np.ndarray, n_trials: int, seed: int) -> tuple[int, str]:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    indices = list(range(inner_means.shape[0]))

    def objective(trial: "optuna.Trial") -> float:
        idx = trial.suggest_categorical("variant_index", indices)
        return float(inner_means[int(idx)])

    study.optimize(objective, n_trials=n_trials)
    return int(study.best_params["variant_index"]), "optuna_tpe_seeded_no_pruning"


def nested_optimization_report(
    perf: np.ndarray,
    *,
    n_outer_folds: int = 5,
    inner_trials: int = 64,
    max_pbo: float = 0.10,
    seed: int = 17,
    min_periods_per_fold: int = 2,
    use_optuna: bool = True,
) -> dict[str, Any]:
    """Nested inner-selection / outer-evaluation report over ``perf`` (T, M).

    ``perf`` rows are time-ordered aggregation periods, columns are strategy
    variants. Returns a report dict with ``passed`` (bool) and ``blocked``
    (bool); blocked or failed reports must block lab-candidate acceptance
    (fail-closed).
    """
    perf = np.asarray(perf, dtype=float)
    if perf.ndim != 2:
        return _blocked("perf_must_be_2d_matrix")
    n_periods, n_variants = perf.shape
    if n_variants < 2:
        return _blocked(
            "insufficient_variants_for_nested_search",
            period_count=int(n_periods),
            variant_count=int(n_variants),
        )
    if n_outer_folds < 4:
        return _blocked("n_outer_folds_must_be_at_least_4", n_outer_folds=int(n_outer_folds))
    if n_periods < n_outer_folds * min_periods_per_fold:
        return _blocked(
            "insufficient_periods_for_outer_folds",
            period_count=int(n_periods),
            required_periods=int(n_outer_folds * min_periods_per_fold),
            n_outer_folds=int(n_outer_folds),
        )
    if not np.isfinite(perf).all():
        return _blocked("non_finite_performance_values")

    has_optuna = optuna_available()
    folds = np.array_split(np.arange(n_periods), n_outer_folds)
    fold_reports: list[dict[str, Any]] = []
    lambdas: list[float] = []
    selected_variants: list[int] = []
    selected_outer_scores: list[float] = []
    inner_method = "exhaustive_deterministic"
    for fold_index, test_rows in enumerate(folds):
        train_rows = np.setdiff1d(np.arange(n_periods), test_rows)
        inner_means = perf[train_rows].mean(axis=0)
        if has_optuna and use_optuna and n_variants > inner_trials:
            selected, inner_method = _inner_select_optuna(
                inner_means, n_trials=inner_trials, seed=seed + fold_index
            )
        else:
            selected, inner_method = _inner_select_exhaustive(inner_means)
        outer_means = perf[test_rows].mean(axis=0)
        rank = float(np.sum(outer_means <= outer_means[selected]))  # 1..M, higher = better
        omega = rank / (n_variants + 1.0)
        lam = math.log(omega / (1.0 - omega))
        lambdas.append(lam)
        selected_variants.append(selected)
        selected_outer_scores.append(float(outer_means[selected]))
        fold_reports.append(
            {
                "fold_index": fold_index,
                "train_period_count": int(train_rows.size),
                "test_period_count": int(test_rows.size),
                "selected_variant": selected,
                "inner_score": round(float(inner_means[selected]), 6),
                "outer_score": round(float(outer_means[selected]), 6),
                "outer_rank": int(rank),
                "lambda": round(lam, 6),
                "oos_degradation": round(float(inner_means[selected] - outer_means[selected]), 6),
            }
        )

    pbo_outer = float(np.mean(np.asarray(lambdas) <= 0.0))
    outer_median_selected_score = float(np.median(selected_outer_scores))
    selection_counts = Counter(selected_variants)
    consensus_variant, consensus_count = selection_counts.most_common(1)[0]
    pbo_passed = pbo_outer < float(max_pbo)
    outer_score_passed = outer_median_selected_score > 0.0
    return {
        "method": METHOD,
        "passed": bool(pbo_passed and outer_score_passed),
        "blocked": False,
        "optuna_available": has_optuna,
        "inner_method": inner_method,
        "inner_trials": int(inner_trials),
        "seed": int(seed),
        "n_outer_folds": int(n_outer_folds),
        "period_count": int(n_periods),
        "variant_count": int(n_variants),
        "pbo_outer": round(pbo_outer, 5),
        "max_pbo": float(max_pbo),
        "pbo_passed": bool(pbo_passed),
        "outer_median_selected_score": round(outer_median_selected_score, 6),
        "outer_score_passed": bool(outer_score_passed),
        "consensus_variant": int(consensus_variant),
        "selection_stability": round(consensus_count / float(n_outer_folds), 5),
        "selection_counts": {str(k): int(v) for k, v in sorted(selection_counts.items())},
        "mean_oos_degradation": round(
            float(np.mean([f["oos_degradation"] for f in fold_reports])), 6
        ),
        "outer_folds": fold_reports,
    }
