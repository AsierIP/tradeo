# CAPACITY-002-B Intraday Matrix Plan

Decision: `MATRIX_PLAN_READY_FOR_SMALL_BATCH`

Combination count: 189
Classification counts: `{"DATA_MISSING": 63, "NEEDS_DIRECTOR_APPROVAL": 54, "PARTIAL": 63, "READY": 9}`
Microbench rows/sec baseline: `597392.572`

The planned matrix covers 15m/30m/1h, W20/W50/W100, fast/standard/slow forward sets, and seven regimes. It was classified from cache coverage and estimated windows only; no wave was executed.

Safety: cache-only; no IBKR; no downloads; no signals; no preview; no orders; no candidate approval.
