from __future__ import annotations

import pytest

from tradeo.services.experiment_orchestrator import (
    EntryVariantArm,
    ExperimentSpace,
    StrategyConfigArm,
    build_experiment_plan,
    build_champion_challenger_manifest,
    default_precision_spaces,
    select_champion_challenger_arm,
    stable_config_hash,
    thompson_sample_entry_variant,
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


def test_champion_challenger_manifest_hashes_configs_and_blocks_live_mode() -> None:
    champion = StrategyConfigArm(
        arm_id="cup_v1",
        role="champion",
        config_version="2026.06.14+champion",
        config={"entry_min_score": 0.55, "target_r_multiple": 4.0},
    )
    challenger = StrategyConfigArm(
        arm_id="cup_v1_retest",
        role="challenger",
        config_version="2026.06.14+retest",
        config={"entry_min_score": 0.60, "target_r_multiple": 4.0},
    )

    manifest = build_champion_challenger_manifest(
        champion=champion,
        challengers=[challenger],
        experiment_mode="paper",
        experiment_id="entry-20260614",
    )

    assert manifest["method"] == "champion_challenger_manifest_v1"
    assert manifest["live_guardrail"] == "challenger_never_live"
    assert manifest["champion"]["config_hash"] == stable_config_hash(champion.config)
    assert manifest["challengers"][0]["config_version"] == "2026.06.14+retest"
    assert manifest["challengers"][0]["live_allowed"] is False

    with pytest.raises(ValueError, match="shadow_or_paper_only"):
        build_champion_challenger_manifest(
            champion=champion,
            challengers=[challenger],
            experiment_mode="live",
            experiment_id="bad-live",
        )


def test_champion_challenger_live_selection_forces_champion() -> None:
    manifest = build_champion_challenger_manifest(
        champion=StrategyConfigArm(
            arm_id="champ",
            role="champion",
            config_version="v1",
            config={"a": 1},
        ),
        challengers=[
            StrategyConfigArm(
                arm_id="challenger",
                role="challenger",
                config_version="v2",
                config={"a": 2},
            )
        ],
        experiment_mode="shadow",
        experiment_id="guardrail",
    )

    assignment = select_champion_challenger_arm(
        manifest,
        execution_mode="live",
        subject_key="AAPL:2026-06-14",
        challenger_fraction=1.0,
    )

    assert assignment["selected_arm_id"] == "champ"
    assert assignment["role"] == "champion"
    assert assignment["challenger_allowed"] is False
    assert assignment["guardrail"] == "live_execution_forces_champion"


def test_thompson_sampling_is_deterministic_and_probability_bounded() -> None:
    arms = [
        EntryVariantArm("default", successes=20, failures=10, is_default=True),
        EntryVariantArm("retest", successes=8, failures=4),
        EntryVariantArm("late_breakout", successes=1, failures=9),
    ]

    first = thompson_sample_entry_variant(
        arms,
        execution_mode="paper",
        seed=17,
        min_probability=0.05,
        max_probability=0.80,
    )
    second = thompson_sample_entry_variant(
        arms,
        execution_mode="paper",
        seed=17,
        min_probability=0.05,
        max_probability=0.80,
    )

    assert first == second
    assert first["applied"] is True
    assert abs(sum(first["allocation"].values()) - 1.0) < 1e-8
    assert all(0.05 <= p <= 0.80 for p in first["allocation"].values())
    assert first["selected_variant_id"] in {arm.variant_id for arm in arms}


def test_thompson_sampling_live_mode_uses_default_variant_only() -> None:
    arms = [
        EntryVariantArm("default", successes=1, failures=1, is_default=True),
        EntryVariantArm("challenger", successes=100, failures=1),
    ]

    result = thompson_sample_entry_variant(arms, execution_mode="production", seed=99)

    assert result["applied"] is False
    assert result["selected_variant_id"] == "default"
    assert result["allocation"] == {"default": 1.0}
    assert result["guardrail"] == "entry_variant_sampling_shadow_paper_only"

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
