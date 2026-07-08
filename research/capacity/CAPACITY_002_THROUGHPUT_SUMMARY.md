# CAPACITY-002 Throughput Summary

Metrics:
- RC-002-A: decision=INTRADAY_CACHE_READY_FOR_PLANNED_WAVE, windows=256, clusters=4, elapsed=4.191573
- RC-002-B: decision=MATRIX_PLAN_READY_FOR_SMALL_BATCH, windows=4664015, clusters=189, elapsed=4.191573
- RC-002-C: decision=REJECTED_MINING_READY, windows=50, clusters=23, elapsed=4.191573

Bottlenecks:
`["5m_data_missing", "15m_data_missing", "1h_partial", "matrix_data_missing=63", "matrix_needs_director_approval=54", "matrix_partial=63", "drawdown", "placebo", "fdr", "wrc", "oos"]`

Recommended next batch, still requiring separate Director authorization:
- 30m W20 fast no_filter: READY, estimated_windows=84149
- 30m W20 standard no_filter: READY, estimated_windows=83096
- 30m W20 slow no_filter: READY, estimated_windows=82160
- 30m W50 fast no_filter: READY, estimated_windows=80639
- 30m W50 standard no_filter: READY, estimated_windows=79586
- 30m W50 slow no_filter: READY, estimated_windows=78650

Safety: cache-only plan execution only; no candidates, signals, previews, orders, IBKR, downloads, or gate relaxation.
