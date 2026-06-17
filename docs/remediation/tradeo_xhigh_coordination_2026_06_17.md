# Tradeo xHigh Coordination - 2026-06-17

## Scope

Five xHigh agents reviewed Tradeo after commit `3c288d2` with focus on:

- Research pattern discovery.
- Laboratory entry signal scanning.
- Throughput and patterns/signals per second.
- EV validation, leakage, OOS and overfit.
- Recent commits, architecture, tests and roadmap.

The full external handoffs live outside the repo under:

- `/home/vboxuser/.openclaw/workspace/handoffs/tradeo_xhigh_A_research_discovery.md`
- `/home/vboxuser/.openclaw/workspace/handoffs/tradeo_xhigh_B_lab_entry_signals.md`
- `/home/vboxuser/.openclaw/workspace/handoffs/tradeo_xhigh_C_throughput.md`
- `/home/vboxuser/.openclaw/workspace/handoffs/tradeo_xhigh_E_commits_arch_roadmap.md`

Agent D returned its EV validation in chat only.

## Shared Verdict

Tradeo is safer than before for prepaper work, but no current pattern should be
treated as proven EV+.

Current blockers remain:

- Research runs `671`, `672` and `673` accepted `0` Lab patterns.
- Director/audit packages still report `0` `paper_trades` and `0` `ib_fills`.
- `edge_claim` must remain `NO_DEMOSTRADO`.
- Nested discovery replay, full anti-lookahead coverage, dedup/independence and
  paper execution evidence are still promotion blockers.

The right next step is not relaxing gates. It is increasing measured exploration
and shadow/confirmation evidence without contaminating Director paper evidence.

## Changes Implemented In This Pass

### Research Trial Accounting

`GlobalExperimentRegistry` now uses a run-independent canonical experiment id
based on `family_id`, `pattern_key` and `variant_id`.

When the same candidate appears again, the registry increments
`replication_count` and marks the candidate as repeated instead of increasing
`global_trial_count`.

This prevents repeated discovery runs from inflating multiple-testing evidence.

New candidate metrics:

- `global_trial_count_increased`
- `is_repeated_experiment`
- `is_repeated_manifest`
- `replication_count`
- `replication_of_experiment_id`

### Research Window Coverage

`WindowSampler` now allocates the per-symbol window budget across requested
window sizes.

The previous sequential budget could let W20/W50 consume the full symbol budget
before W100/W200 received coverage. The new quota keeps large-window pattern
families visible while preserving the total `max_windows_per_symbol` cap.

New sample feature:

- `sample_window_size_quota`

### Lab/Fox Runtime Throughput

Entry scan status now persists:

- `scan_duration_ms`
- `scan_rates_per_minute`
- `funnel`
- `entry_variants_considered`
- `rejected_by_ambiguity`
- shadow/paper observation counters

The scanner now records scan duration directly. Runtime JSON artifacts are also
chmodded to `0644` after atomic writes so the operating user can inspect current
status without root-only permission failures.

## P0 Still Recommended

- Implement a `confirmation_shadow_candidate` lane for promising rejected
  hypotheses. It must never submit IBKR orders or count as Director paper
  evidence.
- Implement nested discovery replay MVP and make blocked/stale replay visible in
  every candidate digest.
- Add a null-test battery for top candidates: matched random entry, time shift,
  opposite side, neighbor cluster, leave-one-symbol/month/regime and cost stress.
- Run market-open Paper E2E until at least one real IBKR paper order/fill loop is
  Director-countable.
- Freeze or demote promoted legacy patterns without linked fills.

## P1/P2 Recommended

- Create an `ExperimentRunner` that executes active-learning agenda items instead
  of only writing them.
- Add shadow-history ranking with shrinkage, separated from IBKR paper evidence.
- Add matcher rejection counters for threshold, conformal kNN, Mahalanobis, shape,
  regime, prototype-bank missing and ambiguity.
- Benchmark `WindowSampler`, `PatternEmbeddingEngine`, `ClusterResearchEngine`
  and `RewardRiskAnalyzer` with patterns/s metrics.
- Move toward PIT/delisting-aware universes before claiming historical EV.

## Safety Position

These changes improve discovery breadth and observability. They do not promote
any pattern, relax any live/paper gate, or prove EV.

Candidate A criteria remain blocked until net EV is demonstrated with clean OOS,
paper fills, costs/slippage, robustness, replay, null baselines and reproducible
hashes.
