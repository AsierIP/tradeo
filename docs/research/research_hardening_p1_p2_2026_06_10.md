# Research Hardening P1/P2 - 2026-06-10

## Invariants

- Full-sample descriptive metrics use the `descriptive_all_*` prefix.
- `descriptive_all_*` metrics are not score inputs for `lab_priority_score`, `promotion_score`, registry-adjusted score, or best-pattern selection.
- Legacy `expectancy_r`, `profit_factor`, `win_rate`, `avg_mfe_r`, and `avg_mae_r` now mirror train/in-sample scope for compatibility.
- Candidate ranking uses `lab_priority_score`, which is scoped to train, OOS, walk-forward, purged CV, bootstrap reality proxy, replay, adversarial, invariance, and teacher evidence.
- WRC/SPA-like values are displayed as `bootstrap_reality_proxy` unless `reality_check_formal_test=true`.

## Hypothesis Package

Research Director emits `research_hypothesis_package` from an immutable `HypothesisPackage` object. The serialized package includes:

- `selection_split`
- `fit_scope`
- `train_metrics`
- `out_of_sample_metrics`
- `walk_forward_metrics`
- `global_trial_count`
- `event_ledger_hash`
- `kill_conditions`
- `family_id`
- `variant_id`
- `edge_claim=NO_DEMOSTRADO`
- `nested_discovery_replay`

## Global Experiment Registry

`reports/research/global_experiment_registry.json` accumulates discovery experiments by `run_id`, `pattern_key`, and `variant_id`. Re-registering the same run/pattern/variant is idempotent and does not inflate `global_trial_count`.

## Nested Discovery Replay

Full nested discovery replay is not implemented yet. Finalists receive a blocking contract:

- `nested_discovery_replay.status=blocked_contract`
- `nested_discovery_replay.blocking=true`
- edge claim remains `NO_DEMOSTRADO`
- paper/live promotion remains blocked until replay is implemented and recorded
