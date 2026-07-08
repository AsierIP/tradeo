# CAPACITY-002-A Intraday Cache Readiness

Decision: `INTRADAY_CACHE_READY_FOR_PLANNED_WAVE`

Universe:
- selected_count: 117
- total_candidates: 5623
- rejected_count: 5506
- product_policy: `stock_only`
- suspicious_selected_count: 0
- product_class_distribution: `{"adr": 6, "common_stock": 111}`

Timeframe coverage:
- 5m: cached=11/117, hit_rate=0.094017, min_rows=2340, decision=DATA_MISSING
- 15m: cached=11/117, hit_rate=0.094017, min_rows=780, decision=DATA_MISSING
- 30m: cached=117/117, hit_rate=1.0, min_rows=143, decision=READY
- 1h: cached=117/117, hit_rate=1.0, min_rows=83, decision=PARTIAL

Readiness blockers: `["5m_data_missing", "15m_data_missing", "1h_partial"]`

Safety: cache-only; no IBKR; no downloads; no signals; no preview; no orders; no candidate approval.
