from __future__ import annotations

import json

import numpy as np
import pytest

from tradeo.core.config import Settings
from tradeo.research.nested_optimization import (
    nested_optimization_report,
    optuna_available,
)
from tradeo.services.self_improvement import SelfImprovementEngine

N_PERIODS = 20
N_VARIANTS = 5
N_FOLDS = 5


def _specialist_overfit_matrix() -> np.ndarray:
    """Each variant j is great everywhere except in outer fold j, where it crashes.

    Inner selection on the complement of fold j always picks variant j (it hides
    its bad fold), and the outer fold then ranks it dead last: the canonical
    selection-overfitting shape that nested evaluation must block.
    """
    perf = np.full((N_PERIODS, N_VARIANTS), 1.0)
    folds = np.array_split(np.arange(N_PERIODS), N_FOLDS)
    for j, rows in enumerate(folds):
        perf[rows, j] = -5.0
    return perf


def _robust_matrix() -> np.ndarray:
    """Variant 0 has a persistent positive edge; the others are flat-to-negative."""
    perf = np.zeros((N_PERIODS, N_VARIANTS))
    for j in range(N_VARIANTS):
        perf[:, j] = -0.1 * j
    perf[:, 0] = 0.5 + 0.01 * np.cos(np.arange(N_PERIODS))
    return perf


def test_overfit_specialists_are_blocked() -> None:
    report = nested_optimization_report(_specialist_overfit_matrix(), n_outer_folds=N_FOLDS)
    assert report["blocked"] is False
    assert report["passed"] is False
    assert report["pbo_outer"] == 1.0
    assert report["pbo_passed"] is False
    assert report["outer_median_selected_score"] < 0.0
    assert all(f["outer_rank"] == 1 for f in report["outer_folds"])
    assert all(f["lambda"] < 0 for f in report["outer_folds"])
    # Every fold picks a different "specialist": maximal selection instability.
    assert report["selection_stability"] == pytest.approx(1.0 / N_FOLDS)


def test_persistent_edge_passes() -> None:
    report = nested_optimization_report(_robust_matrix(), n_outer_folds=N_FOLDS)
    assert report["blocked"] is False
    assert report["passed"] is True
    assert report["pbo_outer"] == 0.0
    assert report["outer_median_selected_score"] > 0.0
    assert report["consensus_variant"] == 0
    assert report["selection_stability"] == 1.0
    assert all(f["selected_variant"] == 0 for f in report["outer_folds"])
    assert all(f["outer_rank"] == N_VARIANTS for f in report["outer_folds"])


def test_consistent_loser_fails_outer_score_gate() -> None:
    perf = _robust_matrix() - 2.0  # stable ranking, but everything loses money
    report = nested_optimization_report(perf, n_outer_folds=N_FOLDS)
    assert report["pbo_passed"] is True
    assert report["outer_score_passed"] is False
    assert report["passed"] is False


def test_insufficient_periods_blocks() -> None:
    report = nested_optimization_report(np.ones((4, 3)), n_outer_folds=N_FOLDS)
    assert report["blocked"] is True
    assert report["passed"] is False
    assert report["reason"] == "insufficient_periods_for_outer_folds"


def test_insufficient_variants_blocks() -> None:
    report = nested_optimization_report(np.ones((20, 1)), n_outer_folds=N_FOLDS)
    assert report["blocked"] is True
    assert report["reason"] == "insufficient_variants_for_nested_search"


def test_non_finite_values_block() -> None:
    perf = _robust_matrix()
    perf[3, 2] = np.nan
    report = nested_optimization_report(perf, n_outer_folds=N_FOLDS)
    assert report["blocked"] is True
    assert report["reason"] == "non_finite_performance_values"


def test_report_is_deterministic() -> None:
    a = nested_optimization_report(_specialist_overfit_matrix(), n_outer_folds=N_FOLDS)
    b = nested_optimization_report(_specialist_overfit_matrix(), n_outer_folds=N_FOLDS)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_fallback_contract_reports_optuna_availability() -> None:
    report = nested_optimization_report(_robust_matrix(), n_outer_folds=N_FOLDS)
    assert report["optuna_available"] is optuna_available()
    if not optuna_available():
        assert report["inner_method"] == "exhaustive_deterministic"


@pytest.mark.skipif(not optuna_available(), reason="optuna not installed")
def test_optuna_inner_search_is_seeded_and_deterministic() -> None:
    rng = np.random.default_rng(7)
    perf = rng.normal(0.0, 0.2, size=(20, 96))
    perf[:, 11] += 1.0
    a = nested_optimization_report(perf, n_outer_folds=N_FOLDS, inner_trials=64)
    b = nested_optimization_report(perf, n_outer_folds=N_FOLDS, inner_trials=64)
    assert a["inner_method"] == "optuna_tpe_seeded_no_pruning"
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _engine(tmp_path, **overrides) -> SelfImprovementEngine:
    return SelfImprovementEngine(Settings(reports_dir=str(tmp_path), **overrides))


def _records_from_matrix(perf: np.ndarray) -> list[dict]:
    months = [f"2023-{m:02d}" for m in range(1, 13)] + [f"2024-{m:02d}" for m in range(1, 9)]
    assert len(months) == perf.shape[0]
    records = []
    for j in range(perf.shape[1]):
        trades = [
            {"exit_date": f"{month}-15", "r_multiple": float(perf[t, j])}
            for t, month in enumerate(months)
        ]
        records.append({"config": {"min_depth": 0.10 + 0.01 * j}, "metrics": {"trades": trades}})
    return records


def test_engine_nested_guard_blocks_specialist_overfit(tmp_path) -> None:
    engine = _engine(tmp_path)
    guards, summary = engine._anti_overfit_guards(_records_from_matrix(_specialist_overfit_matrix()))
    nested = summary["nested"]
    assert nested["blocked"] is False
    assert nested["passed"] is False
    assert nested["pbo_outer"] == 1.0
    assert nested["period_kind"] == "monthly_realized_r_buckets"
    assert guards[0]["nested_passed"] is False
    metrics = {
        "total_trades": 50,
        "profit_factor": 2.5,
        "expectancy_r": 0.4,
        "max_drawdown_pct": 5.0,
    }
    guard = {"pbo_passed": True, "plateau_passed": True, "nested_passed": False}
    assert engine._passes_lab_gate(metrics, guard) is False


def test_engine_nested_guard_accepts_persistent_edge_report(tmp_path) -> None:
    engine = _engine(tmp_path)
    guards, summary = engine._anti_overfit_guards(_records_from_matrix(_robust_matrix()))
    assert summary["nested"]["passed"] is True
    diagnostics = summary["selective_inference_diagnostics"]
    assert diagnostics["diagnostic_only"] is True
    assert diagnostics["blocked"] is False
    assert diagnostics["spa"]["method"] == "studentized_stationary_bootstrap_spa_v1"
    assert diagnostics["romano_wolf"]["method"] == "romano_wolf_stepdown_stationary_bootstrap_v1"
    assert guards[0]["nested_passed"] is True


def test_engine_nested_disabled_fails_closed(tmp_path) -> None:
    engine = _engine(tmp_path, self_improvement_nested_enabled=False)
    report = engine._nested_report(_records_from_matrix(_robust_matrix()))
    assert report["blocked"] is True
    assert report["passed"] is False
    assert report["reason"] == "nested_optimization_disabled_fail_closed"


def test_lab_gate_requires_all_three_guards() -> None:
    engine = SelfImprovementEngine(Settings())
    metrics = {
        "total_trades": 50,
        "profit_factor": 2.5,
        "expectancy_r": 0.4,
        "max_drawdown_pct": 5.0,
    }
    full = {"pbo_passed": True, "plateau_passed": True, "nested_passed": True}
    assert engine._passes_lab_gate(metrics, full) is True
    for key in full:
        broken = dict(full)
        broken[key] = False
        assert engine._passes_lab_gate(metrics, broken) is False
