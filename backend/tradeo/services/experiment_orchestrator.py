from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tradeo.services.self_improvement import sample_grid


@dataclass(frozen=True, slots=True)
class ExperimentSpace:
    name: str
    module: str
    parameters: dict[str, list[Any]]
    budget: int
    seed: int
    evaluator: str
    cadence: str = "manual"
    counts_toward_family_n_trials: bool = True


def build_experiment_plan(spaces: list[ExperimentSpace]) -> dict[str, Any]:
    """Build an auditable multi-module experiment plan.

    This is a planning/accounting layer only: evaluators are named but not
    executed here. Every generated trial carries enough metadata for DSR/PBO
    trial accounting and downstream audit packages.
    """
    plan_spaces: list[dict[str, Any]] = []
    trials: list[dict[str, Any]] = []
    global_trial_index = 0
    for space in spaces:
        _validate_space(space)
        sampled, sampling = sample_grid(
            space.parameters,
            budget=space.budget,
            seed=space.seed,
        )
        space_trials: list[dict[str, Any]] = []
        for local_index, params in enumerate(sampled, start=1):
            global_trial_index += 1
            trial = {
                "trial_index": global_trial_index,
                "space_trial_index": local_index,
                "space": space.name,
                "module": space.module,
                "evaluator": space.evaluator,
                "parameters": params,
                "trial_accounting": {
                    "n_trials_this_space": len(sampled),
                    "space_budget": int(space.budget),
                    "full_grid_size": int(sampling["full_grid_size"]),
                    "counts_toward_family_n_trials": bool(
                        space.counts_toward_family_n_trials
                    ),
                },
            }
            trials.append(trial)
            space_trials.append(trial)
        plan_spaces.append(
            {
                "name": space.name,
                "module": space.module,
                "evaluator": space.evaluator,
                "cadence": space.cadence,
                "budget": int(space.budget),
                "sampled_count": len(sampled),
                "sampling": sampling,
            }
        )
    return {
        "method": "experiment_orchestrator_plan_v1",
        "space_count": len(plan_spaces),
        "trial_count": len(trials),
        "spaces": plan_spaces,
        "trials": trials,
    }


def default_precision_spaces(*, seed: int = 20260612) -> list[ExperimentSpace]:
    """Conservative V1 Precision search-space registry.

    Budgets are intentionally small and evaluators are offline/paper-only. Live
    trading remains outside this layer.
    """
    return [
        ExperimentSpace(
            name="cup_detector",
            module="self_improvement",
            evaluator="lab_backtest_with_existing_pbo_plateau_nested_gates",
            cadence="weekly",
            budget=80,
            seed=seed,
            parameters={
                "min_depth": [0.10, 0.12, 0.16],
                "max_depth": [0.34, 0.42],
                "rim_tolerance": [0.08, 0.12],
                "max_handle_depth": [0.12, 0.16, 0.18],
                "min_breakout_volume_ratio": [1.10, 1.20, 1.35],
                "min_composite_score": [0.68, 0.72, 0.76],
            },
        ),
        ExperimentSpace(
            name="matcher",
            module="novel_pattern_matcher",
            evaluator="false_match_harness_fpr_at_recall90",
            cadence="monthly",
            budget=24,
            seed=seed + 1,
            parameters={
                "conformal_alpha": [0.05, 0.10, 0.15],
                "knn_k": [1, 3, 5],
                "temporal_gamma": [0.95, 0.97, 0.99],
                "ambiguity_ratio_threshold": [0.92, 0.95, 0.97],
            },
        ),
        ExperimentSpace(
            name="entry",
            module="laboratory",
            evaluator="shadow_paper_entry_variant_expectancy",
            cadence="weekly",
            budget=18,
            seed=seed + 2,
            parameters={
                "entry_min_quality_score": [0.55, 0.60, 0.65],
                "entry_min_score": [0.50, 0.55, 0.60],
                "ambiguity_entry_score_margin": [0.05, 0.10],
            },
        ),
        ExperimentSpace(
            name="meta_label",
            module="research_lab_bridge",
            evaluator="purged_oos_meta_label_calibration",
            cadence="monthly",
            budget=12,
            seed=seed + 3,
            parameters={
                "top_fraction": [0.10, 0.15],
                "min_top_decile_uplift": [0.06, 0.08, 0.10],
                "ece_max": [0.04, 0.06],
            },
        ),
    ]


def _validate_space(space: ExperimentSpace) -> None:
    if not space.name.strip():
        raise ValueError("experiment space name is required")
    if not space.module.strip():
        raise ValueError(f"experiment space {space.name} requires module")
    if int(space.budget) < 1:
        raise ValueError(f"experiment space {space.name} budget must be positive")
    if not space.parameters:
        raise ValueError(f"experiment space {space.name} parameters are required")
    for key, values in space.parameters.items():
        if not key.strip() or not values:
            raise ValueError(f"experiment space {space.name} has empty axis {key!r}")
