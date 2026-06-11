# Agent F - Execution State-Machine Tests & Effective-Sample Weights

Date: 2026-06-11
Branch: `feat/tradeo12-execution-state-gap-20260611`
Worktree: `/home/vboxuser/tradeo-worktrees/execution-state-gap`
Base: local `main` at `df418fb` (phases A-D already merged)

## Scope

Close the two remaining Execution/Director gaps from the 12-phase compliance
matrix (`tradeo_12_phase_compliance_matrix_2026_06_10.md`):

- 4.5 Execution/reconciliation: the auto kill switch existed but had no
  explicit order-state transition tests.
- 4.7 Director sequential gate: `effective_lab_trades` was a raw-count proxy
  ("until per-trade uniqueness weights are persisted"); weights are now
  computed and persisted.

4.3 (richer real-time microstructure feeds) remains *future* — no provider is
available; nothing in this phase touches it. No data/research code was
modified. No live trading paths were loosened.

## External Report Sections Addressed

### 4.5 — Explicit order-state transition tests

New test module `backend/tradeo/tests/test_execution_state_transitions.py`
(22 tests) covering the full trade state machine:

- **Paper broker**: `PAPER_APPROVED/LIVE_APPROVED` signal → `OPEN` trade +
  signal `EXECUTED`; every non-executable signal status is rejected without
  creating a trade; zero quantity is rejected.
- **Lab shadow observations**: `OPEN → CLOSED` on target hit, stop hit;
  stays `OPEN` (with `awaiting_future_market_bars` lifecycle metadata) when no
  future bars exist; stays `OPEN` with `market_data_unavailable` diagnostics
  when the provider fails; `open_observation` is idempotent per signal (no
  duplicate `OPEN` rows). Shadow closes keep `shadow_no_order` evidence and
  `shadow_close` provenance — they never masquerade as broker fills.
- **Evidence promotion transitions**: `ibkr_paper_order → ibkr_paper_fill`
  happens only on `CLOSED` status with real broker provenance
  (`broker_execution` / `broker_statement_import`); `OPEN` and `CANCELLED`
  never promote; `simulated_close` provenance never promotes;
  `live_order → live_fill` follows the same rule.
- **Reconciliation**: clean DB↔broker state leaves the kill switch off (open
  orders count as consistent); `db_open_trade_missing_at_broker` and
  `broker_position_not_in_db` divergences both activate the runtime kill
  switch and audit it; zero-quantity broker positions are ignored; non-IBKR
  open trades (paper / lab shadow) are excluded from divergence checks;
  broker-unreachable is audited but **never** trips the kill switch;
  `reconciliation_auto_kill_switch=false` records the divergence without
  activation; a pre-existing kill switch is reported via
  `kill_switch_already_active`.
- **Kill switch state machine**: an active runtime kill switch blocks
  `IBKRBroker.submit_signal_bracket` before any broker connection;
  activation is idempotent and audited (with `already_active` flag);
  deactivation requires an explicit actor and is audited.

### 4.7 — Persisted effective-sample weights for paper fills

New service `backend/tradeo/services/effective_sample.py`
(method id `inverse_symbol_day_cluster_size_v1`):

- Each closed normal IBKR paper fill belongs to a `(symbol, trading day)`
  cluster (day from `closed_at`, falling back to `opened_at`).
- Each fill weighs `1 / cluster_size`, so a correlated same-symbol same-day
  burst contributes exactly one effective sample.
- `n_eff = Σ weights = number of distinct clusters` is the binding number;
  Kish ESS is reported as a secondary diagnostic of weight inequality only.
- Weights are **persisted twice** for auditability:
  - per trade in `trade.metadata_json.effective_sample` (method, cluster key,
    cluster size, weight, computed_at), idempotent across refreshes;
  - per pattern in `metrics_json.lab_execution.effective_sample` (full
    per-trade breakdown + cluster sizes), so any gate decision can be
    reproduced from stored rows alone.

`DirectorReviewGate` changes (`director_review_gate.py`):

- `effective_lab_trades` is now the weighted `n_eff` (was raw fill count) and
  the `effective_lab_trades_below_{min}` blocker compares `n_eff` against
  `director_min_eff_trades` (default 25, unchanged).
- The old "conservative lower-bound proxy" note was replaced by the weighted
  definition; `closed_lab_trades` / `paper_fill_trades` remain raw counts.
- `_promotion_blockers` takes `effective_trades` (defaults to the raw count
  when not supplied, preserving behavior for any external caller).

This is intentionally stricter: 25 fills concentrated on one symbol-day now
count as 1 effective sample and stay blocked, which is the failure mode the
matrix gap described. `DirectorProductionGate` thresholds were not touched.

## Files Changed

- `backend/tradeo/services/effective_sample.py` (new)
- `backend/tradeo/services/director_review_gate.py`
- `backend/tradeo/tests/test_execution_state_transitions.py` (new, 22 tests)
- `backend/tradeo/tests/test_effective_sample_weights.py` (new, 6 tests)
- `backend/tradeo/tests/test_research_lab_fox_lifecycle.py` (fixture only:
  trades now carry `opened_at`/`closed_at` consistent with their declared
  per-day `broker_execution_time`; previously all 10 fills defaulted to the
  same day and the new weighting correctly blocked them as 1 effective sample)
- `docs/remediation/agent_f_execution_state_gap_2026_06_11.md` (this file)

## Tests Run

- `pytest tradeo/tests/test_execution_state_transitions.py tradeo/tests/test_effective_sample_weights.py` → 33 passed
- `pytest tradeo/tests` (full backend suite) → **210 passed**, 1 warning
- `ruff check` on all changed files → clean

(venv: `/home/vboxuser/tradeo/backend/.venv`, package resolved from this
worktree via cwd/PYTHONPATH.)

## Risks

- **Semantic tightening**: any pattern whose paper evidence is concentrated by
  symbol-day will now report a lower `effective_lab_trades` and may regain the
  `effective_lab_trades_below_25` blocker. This is the intended fix, but
  operators reviewing dashboards should expect the number to drop for
  concentrated patterns.
- The gate now writes `effective_sample` into closed trades' `metadata_json`
  during `refresh()`. Writes are idempotent (skipped when method/cluster/
  weight are unchanged) and only touch fills of patterns under review, but it
  is a new write path on evidence rows; the original evidence fields are never
  modified.
- Weights depend on cluster composition at evaluation time: adding a fill to
  an existing cluster re-weights its siblings on the next refresh. The
  persisted `computed_at`/`method` fields make each snapshot traceable.
- Kish ESS is informational only; if someone later wires it into a gate they
  should note it does not capture clustering (equal weights → raw n).

## Merge Notes

- Single-commit branch over `df418fb`; touches only Execution/Director
  service + tests + this doc, so conflicts with other phase branches are
  unlikely unless they also edit `director_review_gate.py`
  (`_store_lab_execution_metrics` / `_promotion_blockers`) or the lifecycle
  test fixture.
- Compliance matrix follow-up after merge: 4.5 gap "explicit order-state
  transition tests" → closed; 4.7 gap "persisted effective-sample weights for
  paper fills" → closed; 4.3 richer real-time feeds remains *future* (no
  provider).
- No config/env changes; `director_min_eff_trades=25`, `director_min_symbols=8`,
  `director_min_days=10`, `reconciliation_auto_kill_switch=true` defaults
  untouched.
