# Dashboard observability: EV, cost and closed-trade diagnostics

Date: 2026-06-17
Scope: small read-only observability patch for Laboratory/Fox module dashboard.

## What changed

- Module overview now exposes expected value per signal/trade.
  - Paper-history expectancy is preferred when `opportunity_rank_components.history_count > 0`.
  - Research-pattern expectancy is used as fallback from `signal_snapshot.pattern.expectancy_r` or match metrics.
- Closed execution fills now expose execution-adjusted diagnostics:
  - net expectancy R after slippage and commission
  - mean slippage R
  - mean commission R
  - cost/shortfall coverage and missing rows
- Trade rows now include:
  - expected value source
  - exit reason
  - total slippage R
  - commission USD/R
  - estimated per-share cost
  - net R
  - cost coverage state

## Audit notes

- This dashboard remains an operational read model, not the Director promotion source.
- Shadow and near-miss observations stay excluded from execution-fill PnL/EV.
- Net EV is only trustworthy when cost coverage is high and missing shortfall/commission rows are zero.
- Open trades may show entry-fill diagnostics only; full net R requires a closed broker fill with entry, exit and commission provenance.

## Before live

- Treat any pattern with low cost coverage as not live-ready.
- Require Director/audit export to confirm promotion decisions.
- Use the dashboard to spot missing cost/slippage provenance early, not to override gates.
