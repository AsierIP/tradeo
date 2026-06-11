# Tradeo 12-Phase Compliance Matrix

Date: 2026-06-10

Each agent appends its own rows without removing other branches' work.

| Section | Agent | Status | Evidence | Remaining gap |
|---|---|---|---|---|
| 3.1 Data layer | A | Partial implemented | Deterministic OHLCV cache, metadata columns, split heuristic, provider manifest. | True incremental fetch remains blocked by current provider signature. |
| 3.2 Universe | A | Partial implemented | Monthly snapshot service, eligibility filters, hash metadata, explicit survivorship flags, validation cap to `lab_watchlist` when non-PIT. | Delisting/PIT vendor data still absent. |
| 3.8 Market regimes | A | Partial implemented | Candidate regime profile exposes regime count/share and `regime_specific` metadata; matcher consumes `preferred_regime_keys`. | Full SPY SMA200/vol tercile service remains pending. |
| 7 Reproducibility (data lineage) | A | Partial implemented | Discovery summaries/candidates attach data manifest and universe snapshot lineage. | Full bit-for-bit discovery determinism still depends on broader clustering/research paths. |
| 8 Config (data scope) | A | Implemented for this scope | Env settings for cache, adjusted feed, whatToShow, snapshots, PIT availability, and survivorship cap. | — |
| 3.3 Representation | B | Partial implemented | Shared `PatternEmbeddingEngine.contract()` persisted from Research and Lab; targeted parity test added. | Matrix Profile/DTW/learned embeddings deferred to avoid heavy unpinned dependencies. |
| 3.4 Clustering | B | Partial implemented | Cluster signature now records medoid, similarity distribution and concentration checks; gate rejects new concentrated clusters when diagnostics exist. | KMeans remains; HDBSCAN/noise labeling deferred. |
| 4.1 Matching parity / no live daily bar | B | Mostly implemented | Prior patch already drops incomplete daily bars; this patch adds explicit feature parity contract to matcher output and match metrics. | Existing historical patterns need rediscovery to carry the contract. |
| 4.2 Matcher threshold / ambiguity | B | Partial implemented | Prior patch uses per-pattern tau; this patch adds `ambiguity_ratio`, similarity margin and second-best pattern metadata. | Ratio is audit-only until calibrated as a hard gate. |
| 7 Audit / reproducibility | B | Partial implemented | New JSON metrics are deterministic and covered by tests; remediation report created. | Coordinator should merge all agents' reports into the final consolidated package. |
| 3.5 Canonical outcomes | C | Partial implemented | `RewardRiskAnalyzer._simulate_sample_detail` and `Backtester._simulate_exit` delegate to `triple_barrier_outcome`; `WindowSampler` persists `forward_opens`. | True non-trade/skipped signal accounting should propagate beyond labels. |
| 3.5 Cost model | C | Partial implemented | `tiered_round_trip_cost_r` added and used by backtester; Research continues to use existing execution cost metrics through canonical net R. | — |
| 3.6 RR/N_trials accounting | C | Partial implemented | Default RR grid reduced to `2.5,4.0`; existing `real_variant_count`/`multiple_testing_trials` counts configured RR levels. | — |
| 5 ImprovementAgent anti-overfitting | C | Partial implemented | Fixed trial budget, mandatory CSCV/PBO guard, PBO threshold, and plateau check added before lab candidate creation. | Guarded but not yet a nested Optuna workflow. |
| 6 Backtester parity | C | Partial implemented | Backtester exit path now uses canonical `triple_barrier_outcome` and shared tiered costs. | ShadowTracker canonical outcome parity remains for Agent D/future work. |
| 8 Config (outcomes scope) | C | Partial implemented | `.env.example` and `Settings` expose RR and self-improvement guard defaults. | — |

| 4.3 Microstructure filters | D | Partial implemented | Signal snapshots and entry quality keep liquidity, ATR, volume, extension, regime, and entry-gate rejection reasons auditable. | Richer real-time microstructure feeds where available. |
| 4.4 Sizing | D | Improved | `RiskManager` caps quantity by ADV participation and blocks excess open positions in the same pattern family. | — |
| 4.5 Execution/reconciliation | D | Existing, verified | Reconciliation auto-kill-switch path remains enabled by default and backend suite is green. | Explicit order-state transition tests. |
| 4.6 Shortfall | D | Improved | Director shortfall gate existed; PatternHealthMonitor now also monitors real-fill `slippage_R` CUSUM. | — |
| 4.7 Director sequential gate | D | Improved | Defaults now require 25 effective real paper fills, 8 symbols, and 10 days before Director review eligibility. | Persisted effective-sample weights for paper fills. |
| 4.8 Health monitor | D | Improved | Health monitor tracks realized R decay and shortfall deterioration. | — |
| 7 Audit reproducibility | D | Improved | Audit export separates exported event count from verified independent sample count and tests reconstruction from event rows. | — |

| 3.1 Data layer (incremental fetch) | E | Implemented for daily artifacts | Overlap-verified tail merge inside the existing `period/interval` boundary; `refresh_mode`/`rows_appended` metadata; manifest exposes refresh lineage. Mismatched overlap (re-adjusted feed) forces full refetch. | Intraday intervals keep cache-forever behavior. |
| 3.2 Universe | E | Partial implemented | Snapshot metadata adds deterministic `content_hash` and explicit `delisting_data_available=false`. | Delisting/PIT vendor data still absent (honestly blocked). |
| 3.8 Market regimes | E | Implemented (audit-grade) | `market_regime.py`: SPY strict-SMA200 trend + trailing vol-tercile labels, PIT-stable by construction (test-covered); attached per match as `benchmark_regime` and on matcher run output. | Not yet a hard gate in `_pattern_regime_fit`; needs labeled outcome history per regime bucket to calibrate. |
| 7 Reproducibility (data lineage) | E | Improved | Snapshot `content_hash` excludes timestamps/paths for bit-for-bit identity; regime snapshots carry `source_bar_hash`; manifest entries record `last_timestamp` + refresh mode. | Bit-for-bit determinism of full discovery runs still depends on clustering/research paths. |
| 8 Config (regime/incremental scope) | E | Implemented for this scope | Env knobs for incremental cache refresh (enabled/overlap/min/max gap), regime windows, benchmark symbol, delisting availability. | — |

## Agent E Test Evidence

- Full backend suite in `tradeo-backend:latest` (worktree mounted read-only): 193 passed.
- Ruff on touched files: passed.

## Agent C Test Evidence

- Full backend suite: 165 passed (in Agent C worktree).
- Ruff: passed.

## Cross-Agent Notes

- Agent D did not change live trading enablement.
- Remaining full compliance needs persisted effective-sample weights for paper fills, explicit order-state transition tests, and richer real-time microstructure feeds where available.

## Agent G Consolidation (2026-06-11)

| Section | Agent | Status | Evidence | Remaining gap |
|---|---|---|---|---|
| 7 Audit package consolidation | G | Implemented | Final consolidated report `tradeo_12_phase_final_report_2026_06_11.md` (12-section status, test ledger, merge order, honest-claims review); supersedes the 06-10 final report. | — |
| 7 Docs traceability | G | Implemented | `test_remediation_docs_traceability.py`: Files Changed references must resolve to real files; matrix must keep A–D rows; audit export must keep `event_count`/`independent_sample_count`/`is_independent_sample`. | Validates path existence, not prose accuracy. |

Status updates recorded by Agent G (rows above are wave-1/wave-2 history and were not edited in place):

- 4.5 Execution/reconciliation: "explicit order-state transition tests" gap closed by Agent F (`feat/tradeo12-execution-state-gap-20260611`, 22 tests in `test_execution_state_transitions.py`), pending merge at the time of writing.
- 4.7 Director sequential gate: "persisted effective-sample weights" gap closed by Agent F (`effective_sample.py`, weights persisted in trade metadata and pattern `lab_execution` metrics; `n_eff` now binding), pending merge at the time of writing.
- The Cross-Agent Notes list above predates Agent F; of its three items only "richer real-time microstructure feeds" remains open (no provider available).

## Agent H Update (2026-06-11)

| Section | Agent | Status | Evidence | Remaining gap |
|---|---|---|---|---|
| 6 Backtester/Shadow parity | H | Implemented | Shadow observation exits delegate to canonical `triple_barrier_outcome` (open-gap stop fills at the OPEN, target gaps at the TARGET, conservative intrabar both-hit); closed trades persist a `canonical_outcome` block. 8 parity tests in `test_shadow_canonical_outcome_parity.py`; full suite 270 passed. See `agent_h_shadow_canonical_outcome_parity_2026_06_11.md`. | Shadow costs remain 0R by design (observation-only); 3.5 non-trade accounting still open. |

Status update recorded by Agent H (earlier rows unedited): the section-6 row's
"ShadowTracker canonical outcome parity remains for Agent D/future work" gap is
now closed on `main`.

## Agent E2 Update (2026-06-11, recorded by audit/traceability agent)

Agent E2's intraday incremental cache work merged to `main` as `b83c71a`
without appending its matrix rows; this section records them after the fact so
the matrix matches the code on `main`. Earlier rows are unedited.

| Section | Agent | Status | Evidence | Remaining gap |
|---|---|---|---|---|
| 3.1 Data layer (intraday incremental fetch) | E2 | Implemented | Intraday intervals (`1m/5m/15m/30m/1h`) now use the same overlap-verified tail append as daily, with bar-relative min-gap and wall-clock max-gap thresholds, master switch `market_data_incremental_intraday_enabled`, honest in-progress-bar exclusion in `_bar_complete_mask`, and complete-bars-only persistence (also fixes the latent daily partial-bar cementing defect). 5 new tests in `test_data_provider.py`; image suite 258 passed. See `agent_e2_intraday_incremental_cache_2026_06_11.md`. | RTH session boundaries not modeled (overnight gap math is wall-clock, harmless no-op); unknown intervals keep the permissive all-complete mask. |

Status updates recorded by the audit/traceability agent (earlier rows unedited):

- 3.1 Data layer (incremental fetch): the E row's remaining gap "Intraday
  intervals keep cache-forever behavior" is now closed on `main` (`b83c71a`).
- Agent F merge status: the Agent G notes above describe F's work as "pending
  merge at the time of writing"; F is now merged on `main` (`12f2157`, via
  merge `646b995`), so both F items (order-state transition tests, persisted
  effective-sample weights) are live.

## Agent I Update (2026-06-11)

| Section | Agent | Status | Evidence | Remaining gap |
|---|---|---|---|---|
| 3.8 Market regimes (outcome calibration) | I | Implemented (gate ships disabled) | Research persists `regime_profile.benchmark_regime_outcomes`: per-PIT-benchmark-bucket sample_count/expectancy_r/win_rate/profit_factor from canonical triple-barrier simulation at the pattern's side/best RR. `_pattern_regime_fit` uses the calibrated bucket when it has ≥ `market_regime_outcome_min_samples` (default 12) labeled outcomes, attaching the evidence as `regime_fit.calibration`; calibrated-negative buckets are droppable via `market_regime_hard_gate_enabled` (default OFF), with `regime_gate_blocked` counts on matcher output. 11 tests in `test_regime_outcome_calibration.py`; image suite 278 passed. See `agent_i_regime_outcome_calibration_2026_06_11.md`. | Existing DB patterns lack calibration until rediscovery; real-fill per-regime attribution and the enable-gate decision remain Director follow-ups. |

Status update recorded by Agent I (earlier rows unedited): the E row's
section-3.8 remaining gap ("Not yet a hard gate in `_pattern_regime_fit`;
needs labeled outcome history per regime bucket to calibrate") now has the
labeled outcome history and a config-gated hard gate on this branch; the
gate default stays off pending calibrated real-fill evidence.

## Agent J Update (2026-06-11)

| Section | Agent | Status | Evidence | Remaining gap |
|---|---|---|---|---|
| 3.5 Canonical outcomes (non-trade accounting) | J | Implemented | Skipped/invalid/no-data signals no longer enter Research RR aggregates as phantom `0R`: `metrics_for_rr` excludes them from all traded arrays and reports `signal_count`/`skipped_count`/`skip_rate`/`skip_reason_counts`, with `sample_count` now traded-only (conservative for `min_samples` and validation-gate thresholds). `Backtester` counts detected-vs-skipped signals and `BacktestMetrics` exposes `total_signals`/`skipped_signals`/`skip_rate`; `_simulate_exit` filters every non-`ok` status, closing the latent `invalid`/`no_data` NaN path. 4 new tests; full suite 286 passed. See `agent_j_non_trade_accounting_2026_06_11.md`. | `skip_rate` not yet surfaced in Director review evidence; shadow path intentionally untouched. |

Status update recorded by Agent J (earlier rows unedited): the C row's
section-3.5 remaining gap ("True non-trade/skipped signal accounting should
propagate beyond labels") and the H row's note ("3.5 non-trade accounting
still open") are closed on this branch.

## Wave4-A Update (2026-06-11)

| Section | Agent | Status | Evidence | Remaining gap |
|---|---|---|---|---|
| 3.5 Canonical outcomes (Director skip-rate evidence) | Wave4-A | Implemented (evidence only) | `DirectorReviewGate` now surfaces stored non-trade accounting as Director evidence: `lab_execution.research_skip_accounting` (with `source` provenance from `pattern.rr_metrics_json[best_rr]`, other RR levels, `metrics_json.rr_metrics`, or backtest-shaped `total_signals`/`skipped_signals` blocks), `research_skip_rate_warning` at threshold 0.25, and a high-priority `review_research_skip_rate` director recommendation carrying `skip_rate`/`signal_count`/`skipped_count`/`skip_reason_counts`. `DirectorProductionGate.evaluate_pattern` includes the same block in its packet. Never a blocker; returns `available: false` (no invented numbers) when the research run predates non-trade accounting. 4 new tests; gate suite 18 passed. See `wave4_a_director_skip_evidence_2026_06_11.md`. | Whether a hard `skip_rate` ceiling belongs in `DirectorProductionGate` is a Director/Asier decision once calibrated evidence accumulates. |

Status update recorded by Wave4-A (earlier rows unedited): the J row's
remaining gap ("`skip_rate` not yet surfaced in Director review evidence")
is closed on this branch.

## Agent K Update (2026-06-11, Wave4-B)

| Section | Agent | Status | Evidence | Remaining gap |
|---|---|---|---|---|
| 3.4 Clustering / reproducibility (discovery determinism) | K | Implemented (in-process contract) | Discovery output is bit-for-bit reproducible for identical inputs/config/seed on the same image: new `research/determinism.py` provides canonical JSON + `sha256_canonical_json_v1` content hash excluding volatile run metadata (timestamps, `run_id`, artifact paths); discovery report JSON now dumps `sort_keys=True` and carries a `determinism.content_hash` block; `autonomous_research_director` memory-graph enumeration and pattern query get deterministic sort/tiebreakers. Harness `test_discovery_determinism.py` runs the real engine twice over seeded synthetic fixtures and asserts byte-identical canonical payloads, input-order independence, and run_id-stable report hashes. 6 new tests; image suite 288 passed, 4 skipped. See `agent_k_discovery_determinism_2026_06_11.md`. | Cross-environment (sklearn/BLAS/hardware) bit-equality not claimed; full live-data end-to-end double-run out of scope (run-context excluded from identity hash); `tests/fixtures.py` `fixture_ohlcv` stays PYTHONHASHSEED-sensitive (pre-existing, test-data only). |
