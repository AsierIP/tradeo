from __future__ import annotations

import json

from tradeo.core.config import Settings
from tradeo.services.self_improvement import (
    MUTATION_GRID,
    SelfImprovementEngine,
    sample_grid,
)


def _engine(**overrides) -> SelfImprovementEngine:
    return SelfImprovementEngine(Settings(**overrides))


def test_mutation_budget_covers_all_axis_values() -> None:
    engine = _engine(self_improvement_max_trials=80)
    out = engine._mutations({"target_r_multiple": 4.0})
    assert len(out) == 80
    for axis, values in MUTATION_GRID.items():
        seen = {cfg[axis] for cfg in out}
        assert seen == set(values), f"axis {axis} not fully covered: {seen}"
    assert engine._last_sampling_metadata is not None
    assert engine._last_sampling_metadata["all_axes_fully_covered"] is True


def test_mutation_budget_respects_max_trials() -> None:
    for budget in (1, 6, 80, 400):
        engine = _engine(self_improvement_max_trials=budget)
        out = engine._mutations({})
        assert len(out) <= budget
        assert len(out) <= 324


def test_mutation_sampling_deterministic_given_seed() -> None:
    base = {"target_r_multiple": 4.0}
    first = _engine(self_improvement_max_trials=80)._mutations(base)
    second = _engine(self_improvement_max_trials=80)._mutations(base)
    assert first == second

    other_seed = _engine(
        self_improvement_max_trials=80,
        self_improvement_sampling_seed=99,
    )._mutations(base)
    assert other_seed != first


def test_grid_truncation_bias_fixed() -> None:
    engine = _engine(self_improvement_max_trials=80)
    out = engine._mutations({})
    assert len({cfg["min_depth"] for cfg in out}) > 1
    keys = tuple(MUTATION_GRID)
    combos = [tuple(cfg[key] for key in keys) for cfg in out]
    assert len(set(combos)) == len(combos)


def test_sample_grid_returns_full_grid_when_budget_allows() -> None:
    sampled, metadata = sample_grid(MUTATION_GRID, budget=1000, seed=20260611)
    assert len(sampled) == 324
    assert metadata["full_grid_size"] == 324
    assert metadata["all_axes_fully_covered"] is True


def test_sample_grid_partial_budget_metadata() -> None:
    sampled, metadata = sample_grid(MUTATION_GRID, budget=2, seed=20260611)
    assert len(sampled) == 2
    assert metadata["sampled_count"] == 2
    assert metadata["all_axes_fully_covered"] is False
    for axis, info in metadata["axis_coverage"].items():
        assert info["covered_count"] == len({selection[axis] for selection in sampled})


def test_report_includes_sampling_metadata(tmp_path) -> None:
    engine = _engine(self_improvement_max_trials=80, reports_dir=str(tmp_path))
    engine._mutations({})
    path = engine._write_report([], [], None, {"passed": False})
    payload = json.loads(path.read_text())
    assert payload["sampling"]["method"] == "stratified_cycle_v1"
    assert payload["sampling"]["seed"] == 20260611
    assert payload["sampling"]["all_axes_fully_covered"] is True
