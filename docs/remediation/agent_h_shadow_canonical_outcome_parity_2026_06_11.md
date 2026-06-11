# Agent H - ShadowTracker Canonical-Outcome Parity

Date: 2026-06-11
Branch: `main` (direct, single-phase execution/director task)
Scope: external report section 6 (backtester/shadow parity), gap 6 of the
2026-06-11 final report: "ShadowTracker canonical-outcome parity (6)".

## Problem

The lab shadow-observation lifecycle
(`LabPaperObservationService._evaluate_trade`) closed observations with an
ad-hoc stop/target loop while the backtester (Agent C) and Research RR
simulation already shared the canonical triple-barrier engine
(`triple_barrier_outcome` in `quant_validation.py`). The divergences were
all optimistic for the shadow path:

- a bar that **opened through the stop** was filled at the stop price; the
  canonical rule fills at the OPEN (worse than the stop);
- a bar that **opened through the target** happened to fill at the target,
  but only because stop/target were checked intrabar — the open-gap ordering
  (stop gap before target gap) was not applied;
- intrabar stop+target resolution matched by code-order accident, not by an
  explicit `conservative_both` contract;
- no canonical outcome record was persisted, so a gate decision based on a
  shadow close could not be reproduced against the shared engine.

Because Director review evidence includes shadow/near-miss observations,
optimistic shadow fills inflate apparent R for gapped stops — exactly the
class of bias section 6 flags.

## Change

`_evaluate_trade` now delegates exit math to `triple_barrier_outcome`:

- The shadow position exists from `opened_at` at `trade.entry`, before the
  first future bar. Two synthetic bars pinned at the entry price (signal bar
  + entry bar) precede the future bars, so every real bar is "posterior to
  entry" and the canonical open-gap rules apply to **all** future bars,
  including the first. `max_bars` is passed as `max_holding_bars + 1` to
  account for the synthetic entry-bar slot.
- `entry_price=trade.entry`, `side=±1` from `trade.side`,
  `gap_entry_policy="skip"`, `conservative_both=True`,
  `round_trip_cost_R=0.0` (shadow observations carry zero execution costs by
  design; cost modelling for shadow evidence stays downstream).
- Pending semantics preserved: a `time` outcome is only accepted once
  `len(future) >= max_holding_bars`; otherwise the observation stays open
  and the existing diagnostic path (`awaiting_future_market_bars`) runs.
  Non-`ok` engine statuses (malformed barriers, e.g. entry at/through a
  barrier) also keep the observation pending instead of fabricating an exit.
- `exit_reason` keeps the shadow vocabulary via `CANONICAL_EXIT_REASON_MAP`
  (`stop`/`stop_and_target_conservative` → `stop_hit`, `target` →
  `target_hit`, `time` → `time_stop`); `stop_gap`/`target_gap` pass through
  unchanged because `implementation_shortfall.py` already classifies them
  and renaming would hide that the fill was at the open.
- Closed trades persist a `canonical_outcome` metadata block (engine,
  status, canonical reason, R, mfe_R, mae_R, bars_held, conservative_both,
  gap_entry_policy, round_trip_cost_R) so any gate decision can be
  reproduced from stored rows against the shared engine.

`r_multiple`/`pnl` continue to be computed in `_close_trade` from the exit
price; with zero costs they equal the canonical `R` (asserted in tests).

## Behavior change (intentional tightening)

Shadow observations whose stop is gapped at the open now record the open as
the exit price (e.g. entry 10, stop 9, next open 8.4 → R −1.6, was −1.0),
with `exit_reason="stop_gap"`. Dashboards and gate evidence will show worse
R for gapped shadow stops; this is the parity fix, not a regression.

## Files Changed

- `backend/tradeo/modules/laboratory/paper_observations.py`
- `backend/tradeo/tests/test_shadow_canonical_outcome_parity.py`
- `docs/remediation/agent_h_shadow_canonical_outcome_parity_2026_06_11.md`
- `docs/remediation/tradeo_12_phase_compliance_matrix_2026_06_10.md`

## Tests Run

- `.venv/bin/pytest -q tradeo/tests/test_shadow_canonical_outcome_parity.py tradeo/tests/test_execution_state_transitions.py tradeo/tests/test_pattern_entry_scanner.py` → 68 passed
- `.venv/bin/pytest -q tradeo/tests` (full backend suite) → **270 passed**, 1 warning
- `.venv/bin/ruff check` on both changed Python files → clean

New tests (8) cover: first-bar and later-bar stop gaps fill at the open
(long and short), target gaps fill at the target (not the open), intrabar
stop+target resolves to the stop with the canonical reason recorded,
time-stop waits for the full holding window, the persisted
`canonical_outcome` block, and a direct engine-parity assertion comparing
the persisted exit against `triple_barrier_outcome` on the same arrays.

## Risks

- **Evidence numbers shift down** for any pattern whose shadow history
  contains gapped stops; `effective_lab_trades` is unaffected (counts, not
  R), but health/SQN-style metrics fed by shadow R will be more
  conservative. Intended.
- Malformed observations (entry at or beyond a barrier) now stay pending
  with diagnostics instead of being force-closed at a barrier price. They
  surface via the existing `lab_shadow_observation_pending_bars` audit path.
- MFE/MAE: both the legacy `mfe`/`mae` fields (from observed bars) and the
  canonical `mfe_R`/`mae_R` (which include the zero-excursion synthetic
  entry bar) are persisted; consumers should prefer the canonical block for
  engine-comparable numbers.
- No order routing, broker configuration, gate thresholds or live-trading
  flags were touched; shadow observations remain `no_ibkr_order=true`.

## Next Step Recommended

Gap 3.5 (true non-trade/skipped-signal accounting through aggregate
metrics): the engine's `skipped` statuses (`gapped_through_stop`,
`gapped_past_target`) are now reachable from the shadow path's pending
diagnostics, so wiring them into the aggregate non-trade metrics is the
natural follow-on execution/director phase.
