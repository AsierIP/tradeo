# Agent J - True Non-Trade / Skipped-Signal Accounting in Aggregate Metrics

Date: 2026-06-11
Branch: `feat/non-trade-accounting-aggregates`
Scope: gap 3.5 remainder from Agent C ("True non-trade/skipped signal
accounting should propagate beyond labels"), flagged again by Agent H as
"3.5 non-trade accounting still open".

## Problem

The canonical triple-barrier engine (`triple_barrier_outcome`, gap-entry
policy `skip`) already labeled gap-skipped signals, but the skip never
propagated past the label:

- `RewardRiskAnalyzer.metrics_for_rr` appended `0.0R` to the results array
  for every skipped signal (via `_tuple_from_detail`). That phantom `0R`
  diluted `win_rate`/`loss_rate`/`expectancy_r`/`median_result_r`, inflated
  `sample_count` (the `min_samples` candidate gate counted non-trades as
  evidence), shrank `timeout_rate`/`target_hit_rate`/`stop_hit_rate`
  denominators, and pushed the per-sample MFE/MAE/cost/fill arrays and a
  phantom `timeout` speed label for signals that never traded.
- Non-`ok` statuses other than `skipped` (`invalid`, `no_data`) carry
  `R=NaN`; had one ever occurred it would have poisoned every aggregate.
  The backtester had the same latent NaN path (`_simulate_exit` only
  filtered `skipped`).
- `Backtester.run` silently dropped skipped signals: `BacktestMetrics` had
  no record of how many detected signals never became trades, so backtest
  expectancy could not be reconciled against signal frequency.

## Change

`backend/tradeo/research/reward_risk_analyzer.py`:

- `metrics_for_rr` treats any non-(`ok`/`fallback`) status as a true
  non-trade: it increments `triple_barrier_labels["skipped"]` and a new
  per-reason counter, then skips the sample before any traded array is
  touched. Traded aggregates now cover executed trades only.
- New aggregate keys (additive; all consumers read defensively via
  `.get`): `signal_count` (all evaluated samples), `skipped_count`,
  `skip_rate`, `skip_reason_counts` (e.g. `gapped_past_target`,
  `gapped_to_stop_zone`). `sample_count` now counts traded samples only,
  which makes the `min_samples` candidate gate and downstream
  `validation_gate`/`active_learning` sample thresholds conservative
  (non-trades no longer count as evidence).

`backend/tradeo/services/backtester.py`:

- `_run_symbol` returns `(trades, signals, skipped)`; a detected candidate
  that fails the entry-gap pre-filter or the canonical gap-entry skip is
  counted instead of vanishing.
- `_simulate_exit` filters on `status != "ok"` (was `== "skipped"`),
  closing the latent `invalid`/`no_data` NaN path.
- `run` aggregates `total_signals`/`skipped_signals`/`skip_rate` into
  `BacktestMetrics`.

`backend/tradeo/schemas.py`:

- `BacktestMetrics` gains `total_signals: int = 0`,
  `skipped_signals: int = 0`, `skip_rate: float = 0.0` (defaulted, so
  persisted/serialized payloads remain compatible).

## Behavior change (intentional tightening)

Patterns whose edge previously leaned on phantom `0R` fills will now show
honest (usually wider) win/loss rates and an explicit `skip_rate`;
`sample_count` drops by the number of skipped signals, so clusters near the
`min_samples` boundary may stop qualifying. That is the point of gap 3.5:
non-trades are not evidence.

## Files Changed

- `backend/tradeo/research/reward_risk_analyzer.py`
- `backend/tradeo/services/backtester.py`
- `backend/tradeo/schemas.py`
- `backend/tradeo/tests/test_reward_risk_analyzer.py`
- `backend/tradeo/tests/test_backtester_non_trade_accounting.py`
- `docs/remediation/tradeo_12_phase_compliance_matrix_2026_06_10.md`
- `docs/remediation/agent_j_non_trade_accounting_2026_06_11.md`

## Tests Run

- New: `test_skipped_signals_do_not_dilute_traded_aggregates`,
  `test_all_skipped_signals_yield_zero_sample_count` (analyzer);
  `test_gap_prefiltered_signal_counts_as_skipped_not_trade`,
  `test_executed_signal_counts_as_trade_with_zero_skips` (backtester, stub
  provider/detector).
- Full backend suite: 286 passed (includes Agent I's regime calibration
  work merged to `main` during this task). `ruff check`: clean.

## Risks

- `sample_count` semantics changed from "signals evaluated" to "trades
  simulated". Reviewed consumers (`validation_gate`, `active_learning`,
  `cluster_research_engine`) treat it as a minimum-evidence gate, so the
  change only tightens; nothing computes derived rates from it.
- Shadow/paper observation path is untouched (its skip semantics differ by
  design: malformed barriers only, per Agent H).

## Next Step Recommended

Surface `skip_rate` in Director review evidence: a pattern with strong
traded expectancy but high gap-skip frequency has lower deployable
capacity, and the Director gate currently does not see it.
