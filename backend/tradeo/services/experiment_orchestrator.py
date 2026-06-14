from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any

from tradeo.services.self_improvement import sample_grid

SAFE_EXPERIMENT_MODES = {"shadow", "paper"}
LIVE_EXECUTION_MODES = {"live", "production"}


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


@dataclass(frozen=True, slots=True)
class StrategyConfigArm:
    """Versioned config identity for paper/shadow experiments."""

    arm_id: str
    config: dict[str, Any]
    config_version: str
    role: str = "challenger"


@dataclass(frozen=True, slots=True)
class EntryVariantArm:
    """Observed paper/shadow evidence for Thompson Sampling allocation."""

    variant_id: str
    successes: float = 0.0
    failures: float = 0.0
    prior_alpha: float = 1.0
    prior_beta: float = 1.0
    is_default: bool = False


def stable_config_hash(config: dict[str, Any]) -> str:
    """Deterministic config hash for audit manifests."""
    payload = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_champion_challenger_manifest(
    *,
    champion: StrategyConfigArm,
    challengers: list[StrategyConfigArm],
    experiment_mode: str,
    experiment_id: str,
) -> dict[str, Any]:
    """Describe a champion/challenger experiment that is not live-routable."""
    mode = _normal_mode(experiment_mode)
    if mode not in SAFE_EXPERIMENT_MODES:
        raise ValueError("champion/challenger experiments are shadow_or_paper_only")
    if champion.role != "champion":
        raise ValueError("champion arm must have role='champion'")
    if not challengers:
        raise ValueError("at least one challenger arm is required")

    champion_record = _arm_record(champion, allowed_execution_modes=[mode])
    challenger_records = []
    for challenger in challengers:
        if challenger.role == "champion":
            raise ValueError("challenger arms must not use role='champion'")
        challenger_records.append(_arm_record(challenger, allowed_execution_modes=[mode]))
    return {
        "method": "champion_challenger_manifest_v1",
        "experiment_id": str(experiment_id),
        "experiment_mode": mode,
        "live_guardrail": "challenger_never_live",
        "promotion_policy": "paper_shadow_evidence_only_human_director_gate_required",
        "champion": champion_record,
        "challengers": challenger_records,
        "config_hashes": {
            champion.arm_id: champion_record["config_hash"],
            **{row["arm_id"]: row["config_hash"] for row in challenger_records},
        },
    }


def select_champion_challenger_arm(
    manifest: dict[str, Any],
    *,
    execution_mode: str,
    subject_key: str,
    challenger_fraction: float = 0.10,
) -> dict[str, Any]:
    """Deterministically assign paper/shadow traffic; live always gets champion."""
    mode = _normal_mode(execution_mode)
    champion = dict(manifest.get("champion") or {})
    challengers = list(manifest.get("challengers") or [])
    if mode in LIVE_EXECUTION_MODES:
        return {
            "selected_arm_id": champion.get("arm_id"),
            "role": "champion",
            "config_version": champion.get("config_version"),
            "config_hash": champion.get("config_hash"),
            "execution_mode": mode,
            "guardrail": "live_execution_forces_champion",
            "challenger_allowed": False,
        }
    if mode not in SAFE_EXPERIMENT_MODES:
        raise ValueError("execution_mode must be shadow, paper or live")
    if not challengers:
        return {
            "selected_arm_id": champion.get("arm_id"),
            "role": "champion",
            "execution_mode": mode,
            "challenger_allowed": False,
            "reason": "no_challengers_in_manifest",
        }

    fraction = min(max(float(challenger_fraction), 0.0), 1.0)
    bucket = int(stable_config_hash({"subject_key": subject_key, "experiment_id": manifest.get("experiment_id")})[:8], 16)
    unit = bucket / 0xFFFFFFFF
    if unit >= fraction:
        return {
            "selected_arm_id": champion.get("arm_id"),
            "role": "champion",
            "config_version": champion.get("config_version"),
            "config_hash": champion.get("config_hash"),
            "execution_mode": mode,
            "challenger_allowed": False,
            "challenger_fraction": fraction,
        }
    challenger = challengers[bucket % len(challengers)]
    return {
        "selected_arm_id": challenger.get("arm_id"),
        "role": "challenger",
        "config_version": challenger.get("config_version"),
        "config_hash": challenger.get("config_hash"),
        "execution_mode": mode,
        "challenger_allowed": True,
        "challenger_fraction": fraction,
        "guardrail": "paper_shadow_only",
    }


def thompson_sample_entry_variant(
    arms: list[EntryVariantArm],
    *,
    execution_mode: str,
    seed: int | None = None,
    min_probability: float = 0.02,
    max_probability: float = 0.70,
) -> dict[str, Any]:
    """Pick an entry variant for paper/shadow using bounded Thompson Sampling."""
    if not arms:
        raise ValueError("at least one entry variant arm is required")
    mode = _normal_mode(execution_mode)
    default = next((arm for arm in arms if arm.is_default), arms[0])
    if mode in LIVE_EXECUTION_MODES:
        return {
            "method": "thompson_sampling_entry_variant_v1",
            "applied": False,
            "execution_mode": mode,
            "selected_variant_id": default.variant_id,
            "selection_reason": "live_execution_forces_default_variant",
            "allocation": {default.variant_id: 1.0},
            "guardrail": "entry_variant_sampling_shadow_paper_only",
        }
    if mode not in SAFE_EXPERIMENT_MODES:
        raise ValueError("execution_mode must be shadow, paper or live")

    rng = random.Random(seed)
    draws: list[float] = []
    for arm in arms:
        alpha = max(float(arm.prior_alpha) + float(arm.successes), 1e-9)
        beta = max(float(arm.prior_beta) + float(arm.failures), 1e-9)
        draws.append(float(rng.betavariate(alpha, beta)))
    probs = _bounded_probability_vector(draws, min_probability, max_probability)
    pick = rng.random()
    cumulative = 0.0
    selected = arms[-1]
    for arm, probability in zip(arms, probs, strict=True):
        cumulative += probability
        if pick <= cumulative:
            selected = arm
            break
    return {
        "method": "thompson_sampling_entry_variant_v1",
        "applied": True,
        "execution_mode": mode,
        "seed": seed,
        "selected_variant_id": selected.variant_id,
        "selection_reason": "bounded_beta_thompson_sample",
        "min_probability": float(min_probability),
        "max_probability": float(max_probability),
        "allocation": {
            arm.variant_id: round(float(probability), 8)
            for arm, probability in zip(arms, probs, strict=True)
        },
        "draws": {
            arm.variant_id: round(float(draw), 8)
            for arm, draw in zip(arms, draws, strict=True)
        },
        "guardrail": "entry_variant_sampling_shadow_paper_only",
    }


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


def _normal_mode(mode: str) -> str:
    return str(mode or "").strip().lower()


def _arm_record(arm: StrategyConfigArm, *, allowed_execution_modes: list[str]) -> dict[str, Any]:
    config_hash = stable_config_hash(arm.config)
    return {
        "arm_id": arm.arm_id,
        "role": arm.role,
        "config": arm.config,
        "config_version": arm.config_version,
        "config_hash": config_hash,
        "config_hash_algorithm": "sha256_canonical_json",
        "allowed_execution_modes": allowed_execution_modes,
        "live_allowed": False,
    }


def _bounded_probability_vector(
    scores: list[float],
    min_probability: float,
    max_probability: float,
) -> list[float]:
    n = len(scores)
    if n == 0:
        raise ValueError("scores are required")
    floor = max(0.0, float(min_probability))
    cap = min(1.0, float(max_probability))
    if cap < floor:
        raise ValueError("max_probability must be >= min_probability")
    if floor * n > 1.0 + 1e-12:
        raise ValueError("min_probability is infeasible for arm count")
    if cap * n < 1.0 - 1e-12:
        raise ValueError("max_probability is infeasible for arm count")
    clean = [score if score > 0 and score == score else 0.0 for score in scores]
    if sum(clean) <= 0.0:
        clean = [1.0 for _ in scores]

    probabilities = [floor for _ in scores]
    remaining = set(range(n))
    remaining_mass = 1.0 - floor * n
    extra_cap = cap - floor
    while remaining:
        total_score = sum(clean[i] for i in remaining)
        proposed = {
            i: remaining_mass / len(remaining)
            if total_score <= 0.0
            else remaining_mass * clean[i] / total_score
            for i in remaining
        }
        capped = [i for i, extra in proposed.items() if extra > extra_cap + 1e-12]
        if not capped:
            for i, extra in proposed.items():
                probabilities[i] = floor + extra
            break
        for i in capped:
            probabilities[i] = cap
            remaining_mass -= extra_cap
            remaining.remove(i)
    total = sum(probabilities)
    if total > 0:
        probabilities = [p / total for p in probabilities]
    return probabilities
