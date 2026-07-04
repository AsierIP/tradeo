# DSS-004F-R Metric Diff / Root Cause

Root cause: `Reporte A` used EPISODE_GAP_5 as calendar-day gaps <= 5 and 100 bootstrap iterations. The committed DSS-004F code in `948410e` uses trading-session `signal_idx` gaps <= 5 and default 20 bootstrap iterations.

This is enough to explain the main discrepancy:

| Metric | Reporte A | Reporte B / rerun | Cause |
|---|---:|---:|---|
| episodes_total | 1597 | 1394 | calendar-day grouping split more episodes |
| episodes_OOS | 979 | 847 | calendar-day grouping split more episodes |
| raw signals / episode mean | 9.4671 | 10.8458 | stricter calendar grouping |
| p95 raw signals / episode | 37 | 40.0000 | stricter calendar grouping |
| bootstrap iterations | 100 | 20 | noncanonical override or stale run |
| symbol bootstrap p05 | positive | -0.0316 | different sample + iteration count |

No data download, IBKR call, parameter tuning, or strategy redesign was used. No method bug requiring code fix was found for the committed DSS-004F path; the stale/noncanonical Reporte A metrics are superseded.
