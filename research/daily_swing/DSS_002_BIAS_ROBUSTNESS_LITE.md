# DSS-002 Bias & Robustness Lite

BIAS_GATE=WARNING

No performance robustness test can be trusted without the underlying Daily OHLCV event ledger.

Completed checks:
- Lookahead: code path still computes Monday 2026-07-06 from last valid bar 2026-07-02.
- Calendar: 2026-07-03 is excluded as Independence Day observed.
- Leakage: no real backtest was run, so no leakage in generated performance metrics.
- Duplicate samples: not_applicable until an event ledger exists.
- Placebo: not_run because there are zero DSS-PB-001 real events.
- Cost x1/x2/x3: not_run because there are zero DSS-PB-001 real trades.
- Entry sensitivity: not_run because there are zero DSS-PB-001 real trades.

Live gap: FDR/WRC/SPA for Daily still does not exist and remains a hard live blocker.
