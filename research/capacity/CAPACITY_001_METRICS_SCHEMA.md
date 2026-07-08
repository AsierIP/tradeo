# CAPACITY-001 Metrics Schema

Schema version: `tradeo.research_capacity.capacity_001.v1`

Required fields:
- `experiment_id`
- `runner_name`
- `research_family`
- `universe_policy`
- `symbols_count`
- `timeframe`
- `window`
- `forward_set`
- `cache_mode`
- `started_at`
- `finished_at`
- `elapsed_seconds`
- `windows_processed`
- `clusters_processed`
- `candidates_total`
- `candidates_accepted`
- `candidates_rejected`
- `near_misses`
- `rejected_persisted`
- `store_rejected_enabled`
- `cache_hit_rate`
- `data_missing_count`
- `blocker_counts`
- `fdr_fail_count`
- `wrc_fail_count`
- `spa_fail_count`
- `cost_x2_fail_count`
- `oos_fail_count`
- `drawdown_fail_count`
- `placebo_fail_count`
- `artifact_bytes`
- `cpu_seconds`
- `memory_peak_mb`
- `decision`
- `safety_flags`

Safety invariants: cache-only, no IBKR, no orders, no signals, no preview, no candidate approval, no downloads.
