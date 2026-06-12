from __future__ import annotations

import pytest

from tradeo.services.experiment_orchestrator import (
    ExperimentSpace,
    build_experiment_plan,
    default_precision_spaces,
)


def test_default_precision_spaces_cover_multiple_modules() -> None:
    plan = build_experiment_plan(default_precision_spaces(seed=123))

    assert plan["method"] == "experiment_orchestrator_plan_v1"
    assert plan["space_count"] == 4
    assert {space["module"] for space in plan["spaces"]} == {
        "self_improvement",
        "novel_pattern_matcher",
        "laboratory",
        "research_lab_bridge",
    }
    assert plan["trial_count"] == sum(space["sampled_count"] for space in plan["spaces"])
    matcher = next(space for space in plan["spaces"] if space["name"] == "matcher")
    assert matcher["sampling"]["all_axes_fully_covered"] is True


def test_experiment_plan_is_deterministic_and_trials_are_accounted() -> None:
    spaces = [
        ExperimentSpace(
            name="tiny",
            module="matcher",
            evaluator="offline",
            parameters={"alpha": [0.05, 0.10], "k": [1, 3, 5]},
            budget=4,
            seed=7,
        )
    ]

    first = build_experiment_plan(spaces)
    second = build_experiment_plan(spaces)

    assert first == second
    assert first["trial_count"] == 4
    assert [trial["trial_index"] for trial in first["trials"]] == [1, 2, 3, 4]
    for trial in first["trials"]:
        accounting = trial["trial_accounting"]
        assert accounting["n_trials_this_space"] == 4
        assert accounting["space_budget"] == 4
        assert accounting["full_grid_size"] == 6
        assert accounting["counts_toward_family_n_trials"] is True


def test_experiment_plan_changes_with_seed() -> None:
    base = ExperimentSpace(
        name="tiny",
        module="matcher",
        evaluator="offline",
        parameters={"alpha": [0.05, 0.10, 0.15], "k": [1, 3, 5]},
        budget=4,
        seed=7,
    )
    other = ExperimentSpace(
        name="tiny",
        module="matcher",
        evaluator="offline",
        parameters=base.parameters,
        budget=4,
        seed=8,
    )

    assert build_experiment_plan([base])["trials"] != build_experiment_plan([other])["trials"]


def test_experiment_space_validation() -> None:
    with pytest.raises(ValueError, match="budget"):
        build_experiment_plan(
            [
                ExperimentSpace(
                    name="bad",
                    module="matcher",
                    evaluator="offline",
                    parameters={"alpha": [0.1]},
                    budget=0,
                    seed=1,
                )
            ]
        )

    with pytest.raises(ValueError, match="empty axis"):
        build_experiment_plan(
            [
                ExperimentSpace(
                    name="bad",
                    module="matcher",
                    evaluator="offline",
                    parameters={"alpha": []},
                    budget=1,
                    seed=1,
                )
            ]
        )
