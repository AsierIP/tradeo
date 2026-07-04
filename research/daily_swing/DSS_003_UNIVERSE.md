# DSS-003 Universe

Built three Daily universes for cache warmup:

- smoke: 10 stocks + SPY/QQQ benchmark-only
- pilot: 50 stocks + SPY/QQQ benchmark-only
- research: 150 stocks + SPY/QQQ benchmark-only

Source priority:
1. Existing repo seed universes under `data/`.
2. Stable fallback liquid stock list, used only to make the pilot/research cache warmup broad enough.

Operational rows are `product_type=STK` and `operational_eligible=true`. SPY and QQQ are present only as regime benchmarks and are not eligible operational symbols.
