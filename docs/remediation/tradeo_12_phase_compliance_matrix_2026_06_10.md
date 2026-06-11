# Tradeo 12-Phase Compliance Matrix - 2026-06-10

| Section | Agent A fallback status | Evidence |
|---|---|---|
| 3.1 Data layer | Partial implemented | Deterministic OHLCV cache, metadata columns, split heuristic, provider manifest. True incremental fetch remains blocked by current provider signature. |
| 3.2 Universe | Partial implemented | Monthly snapshot service, eligibility filters, hash metadata, explicit survivorship flags, validation cap to `lab_watchlist` when non-PIT. Delisting/PIT vendor data still absent. |
| 3.8 Market regimes | Partial implemented | Candidate regime profile now exposes regime count/share and `regime_specific` metadata; matcher already consumes `preferred_regime_keys`. Full SPY SMA200/vol tercile service remains pending. |
| 7 Reproducibility | Partial implemented | Discovery summaries/candidates attach data manifest and universe snapshot lineage. Full bit-for-bit discovery determinism still depends on broader clustering/research paths. |
| 8 Config | Implemented for this scope | Added env settings for cache, adjusted feed, whatToShow, snapshots, PIT availability, and survivorship cap. |
