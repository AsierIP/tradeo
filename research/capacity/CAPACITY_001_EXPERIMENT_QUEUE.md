# CAPACITY-001 Experiment Queue

## 1. RC-002-A - Intraday universe/cache expansion readiness
- Priority score: 95
- Priority rationale: Lowest leakage risk and directly removes current universe/cache uncertainty.
- EVI: High
- Data required: Existing intraday cache + universe manifests
- Cache required: 30m/60d cache
- Estimated runtime: short
- Safety requirements: cache-only; dry-run; no downloads; no live; no paper; no IBKR; no signals; no preview; no orders; no candidate approval; order_code_changed=false; gates_relaxed=false
- Gates required: no-lookahead; FDR/WRC/SPA-light where applicable; cost_x2; OOS; drawdown; placebo
- Success metrics: falsifiable OOS metric, cache coverage, elapsed_seconds, blockers
- Blocker conditions: missing cache, leakage risk, insufficient sample, failed safety guard
- Needs Director approval: False

## 2. RC-002-B - Intraday 15m/30m/1h search-space matrix
- Priority score: 88
- Priority rationale: High falsification value once cache coverage is known.
- EVI: High
- Data required: Cached OHLCV by timeframe
- Cache required: 15m,30m,1h cache
- Estimated runtime: medium
- Safety requirements: cache-only; dry-run; no downloads; no live; no paper; no IBKR; no signals; no preview; no orders; no candidate approval; order_code_changed=false; gates_relaxed=false
- Gates required: no-lookahead; FDR/WRC/SPA-light where applicable; cost_x2; OOS; drawdown; placebo
- Success metrics: falsifiable OOS metric, cache coverage, elapsed_seconds, blockers
- Blocker conditions: missing cache, leakage risk, insufficient sample, failed safety guard
- Needs Director approval: True

## 3. RC-002-C - Regime-conditioned intraday search
- Priority score: 76
- Priority rationale: Useful after baseline matrix; adds leakage/regime complexity.
- EVI: Medium
- Data required: Cached intraday features and SPY/QQQ context
- Cache required: intraday + benchmark cache
- Estimated runtime: medium
- Safety requirements: cache-only; dry-run; no downloads; no live; no paper; no IBKR; no signals; no preview; no orders; no candidate approval; order_code_changed=false; gates_relaxed=false
- Gates required: no-lookahead; FDR/WRC/SPA-light where applicable; cost_x2; OOS; drawdown; placebo
- Success metrics: falsifiable OOS metric, cache coverage, elapsed_seconds, blockers
- Blocker conditions: missing cache, leakage risk, insufficient sample, failed safety guard
- Needs Director approval: True

## 4. RC-002-D - Daily new search-space, excluding PB/BO/CO/CW/GAP rescue
- Priority score: 70
- Priority rationale: Separate daily lane without rescuing rejected families.
- EVI: Medium
- Data required: Daily OHLCV cache
- Cache required: 1d cache
- Estimated runtime: medium
- Safety requirements: cache-only; dry-run; no downloads; no live; no paper; no IBKR; no signals; no preview; no orders; no candidate approval; order_code_changed=false; gates_relaxed=false
- Gates required: no-lookahead; FDR/WRC/SPA-light where applicable; cost_x2; OOS; drawdown; placebo
- Success metrics: falsifiable OOS metric, cache coverage, elapsed_seconds, blockers
- Blocker conditions: missing cache, leakage risk, insufficient sample, failed safety guard
- Needs Director approval: True

## 5. RC-002-E - GAP next-day only redesign
- Priority score: 55
- Priority rationale: Low EVI but cheap protocol design; execution remains blocked pending Director.
- EVI: Low
- Data required: Prior GAP ledgers
- Cache required: gap ledger cache
- Estimated runtime: short
- Safety requirements: cache-only; dry-run; no downloads; no live; no paper; no IBKR; no signals; no preview; no orders; no candidate approval; order_code_changed=false; gates_relaxed=false
- Gates required: no-lookahead; FDR/WRC/SPA-light where applicable; cost_x2; OOS; drawdown; placebo
- Success metrics: falsifiable OOS metric, cache coverage, elapsed_seconds, blockers
- Blocker conditions: missing cache, leakage risk, insufficient sample, failed safety guard
- Needs Director approval: True

## 6. RC-002-F - ETF/macro separate etf_macro research lane
- Priority score: 50
- Priority rationale: Medium EVI but intentionally lower priority because it is a separate lane and must not mix with stock_only.
- EVI: Medium
- Data required: ETF/macro cache
- Cache required: separate ETF cache
- Estimated runtime: medium
- Safety requirements: cache-only; dry-run; no downloads; no live; no paper; no IBKR; no signals; no preview; no orders; no candidate approval; order_code_changed=false; gates_relaxed=false
- Gates required: no-lookahead; FDR/WRC/SPA-light where applicable; cost_x2; OOS; drawdown; placebo
- Success metrics: falsifiable OOS metric, cache coverage, elapsed_seconds, blockers
- Blocker conditions: missing cache, leakage risk, insufficient sample, failed safety guard
- Needs Director approval: True
