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
