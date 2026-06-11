# Wave4-D — Nested Optimization + Outer-Fold PBO Report (2026-06-11)

## Scope

Closes the section-5 ImprovementAgent gap "Nested Optuna workflow + outer-fold
PBO report" from `tradeo_12_phase_final_report_2026_06_11.md`. This is a pure
anti-overfit hardening: it adds a third mandatory blocker to the lab-candidate
gate. It does not relax any existing threshold and cannot improve any claim.

## What Was Built

`backend/tradeo/research/nested_optimization.py` implements
`nested_optimization_report(perf)` over the same (T periods x M variants)
performance matrix the ImprovementAgent already builds from monthly realized
backtest R buckets:

- **Outer folds.** Periods are split into `n_outer_folds` (default 5)
  contiguous folds.
- **Inner optimization.** For each outer fold, the inner search selects the
  best variant on the complement (train) periods. The ImprovementAgent's
  candidate space is fully enumerated by its grid, so inner optimization is a
  selection problem over M variants.
- **Outer evaluation + PBO.** The inner winner is ranked out-of-fold among all
  M variants: omega = rank/(M+1), lambda = ln(omega/(1-omega)) (CSCV
  convention, Bailey/Borwein/Lopez de Prado/Zhu 2017). `pbo_outer` is the
  fraction of outer folds with lambda <= 0.
- **Pass criteria (both required).** `pbo_outer < max_pbo` (default 0.10,
  same ceiling as the existing CSCV guard) **and** median out-of-fold score of
  the selected variants > 0. A stable-but-losing family cannot pass.
- **Report.** Per-fold detail (selected variant, inner/outer score, rank,
  lambda, OOS degradation), `consensus_variant`, `selection_stability`,
  `selection_counts`, `mean_oos_degradation`. Persisted via the existing
  self-improvement report JSON (`anti_overfit.nested`), per-candidate
  `metrics_json.anti_overfit.nested`, and the lab-cycle audit log.

## Optuna Decision (honest)

Optuna is **not installed** in the backend venv and was **not added** as a
dependency. Rationale:

- The inner search space is a fully enumerated categorical set (grid
  mutations). A deterministic exhaustive scan (argmax, first-index tie-break)
  is strictly better than any sampler whenever the trial budget covers the
  space, and is bit-for-bit reproducible — which Wave4-B made a contract.
- Adding a heavy optimizer dependency to "look more rigorous" without a
  larger-than-budget search space would be cargo cult, not hardening.

The Optuna interface ships behind the same contract anyway: if `optuna` is
importable, `self_improvement_nested_use_optuna=true`, and the variant count
exceeds `self_improvement_nested_inner_trials`, inner selection uses a seeded
`TPESampler` (per-fold derived seed) with **pruning off** — the objective is a
cheap deterministic mean with no intermediate values, so pruning could only
add nondeterminism for zero compute savings. Reports always carry
`optuna_available` and `inner_method` (`exhaustive_deterministic` or
`optuna_tpe_seeded_no_pruning`), so evidence never overstates what ran.
If Optuna is installed later it must be version-pinned in
`backend/pyproject.toml` and the skipped seeded-determinism test
(`test_optuna_inner_search_is_seeded_and_deterministic`) becomes active.

## Gate Wiring

- `SelfImprovementEngine._anti_overfit_guards` now computes the nested report
  once per cycle and attaches `nested` / `nested_passed` to every candidate
  guard; the guard summary embeds it under `nested`.
- `_passes_lab_gate` now requires `nested_passed` **in addition to** the
  existing CSCV `pbo_passed` and `plateau_passed`. Nothing was removed or
  loosened.
- Fail-closed: a blocked report (insufficient periods/variants, non-finite
  values) or `self_improvement_nested_enabled=false` yields
  `nested_passed=false` and blocks lab-candidate acceptance. Disabling the
  knob disables candidate creation, not the guard.

## Config Knobs (defaults)

| Knob | Default | Meaning |
|---|---|---|
| `self_improvement_nested_enabled` | `true` | Fail-closed master switch (off = block acceptance). |
| `self_improvement_nested_outer_folds` | `5` | Contiguous outer folds (engine floors at 4). |
| `self_improvement_nested_inner_trials` | `64` | Inner budget; exhaustive scan when it covers M. |
| `self_improvement_nested_max_pbo` | `0.10` | Outer-fold PBO ceiling (same as CSCV guard). |
| `self_improvement_nested_seed` | `17` | Base seed for the optional Optuna sampler. |
| `self_improvement_nested_use_optuna` | `true` | Use Optuna only if importable and M > budget. |

## Honest Limitations

- Folds are contiguous splits of monthly aggregated R buckets; no
  embargo/purge at this aggregation level (trade-level purging lives in
  `purged_walk_forward`).
- Train is the complement of the outer fold (CSCV-style), so train can
  contain periods after the fold: this measures selection overfitting, not a
  causal walk-forward forecast, and is documented as such in the module.
- PBO is still computed from monthly realized R buckets of the lab backtest;
  no production claim of any kind follows from a pass.

## Tests

`backend/tradeo/tests/test_nested_optimization.py` (13 tests, 1 skipped
without Optuna):

- Synthetic "specialist" overfit matrix — each variant is best in-sample for
  exactly the fold where it crashes — yields `pbo_outer = 1.0`, worst outer
  rank in every fold, and is blocked.
- Persistent-edge matrix passes with `pbo_outer = 0.0`, full selection
  stability, consensus variant 0.
- Stable-but-losing matrix fails the outer-median-score criterion despite
  `pbo_passed`.
- Insufficient periods/variants and non-finite values block (fail-closed).
- Byte-identical reports on repeated runs (determinism contract).
- Engine integration: monthly trade records reproducing the specialist matrix
  block the gate; `_passes_lab_gate` requires all three guards; disabled knob
  fails closed; seeded Optuna determinism test guarded by `importorskip`.

Full backend suite after this change: 315 passed, 1 skipped. Before the
matrix append the suite carried 1 pre-existing failure
(`test_remediation_docs_traceability`) inherited from Wave4-C shipping
`agent_l_rediscovery_readiness_2026_06_11.md` without a compliance-matrix
record; the Wave4-D matrix append records that trace, restoring green.

## Files Changed

- `backend/tradeo/research/nested_optimization.py`
- `backend/tradeo/services/self_improvement.py`
- `backend/tradeo/core/config.py`
- `backend/tradeo/tests/test_nested_optimization.py`
- `docs/remediation/wave4_d_nested_optuna_pbo_2026_06_11.md`
- `docs/remediation/tradeo_12_phase_compliance_matrix_2026_06_10.md`
