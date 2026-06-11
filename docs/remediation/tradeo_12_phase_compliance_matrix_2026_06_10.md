# Tradeo 12-Phase Compliance Matrix

Date: 2026-06-10

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
