# DSS-004H Daily Research Terminal Report

Generated: 2026-07-04

## Executive Summary

Daily Swing DSS-001 through DSS-004G-C-R closes as negative operational research with useful infrastructure. No Daily pattern is approved for shadow, paper, live, preview, or operational signals.

The terminal scientific decision is that the current Daily candidates did not survive the project standard: out-of-sample evidence, costs, drawdown sanity, baseline/placebo/adversarial checks, statistical-family checks, symbol independence, and operability.

## Infrastructure Gained

- Daily OHLCV loader and cache workflow.
- Safe resume, quarantine, canary, and batch caps for data ingestion.
- IBKR connectivity diagnostics with live-port blocking and read-only posture.
- Daily quality gate and cache manifests.
- research-150 universe and cache process.
- Backtest engines for PB, BO, CO, and CW families.
- Data ledger and guard checks for false future bars, SPY/QQQ benchmark treatment, and signal t / entry t+1.
- Bias/adversarial tooling: placebos, matched baselines, offset timing, overlap/effective-sample checks.
- FDR/WRC/SPA-light approximation for the terminal CW family.

## Pattern Outcomes

### DSS-PB-001

Pullback in Uptrend Long failed OOS after costs. It is rejected as a spec and was not promoted into later statistical-family testing.

### DSS-BO-001

Volatility Contraction Breakout Long produced attractive headline OOS metrics, but the edge was explained by a simpler CONTRACTION_ONLY matched baseline. It fails as an independent breakout specification.

### DSS-CO-001

Contraction in Uptrend remains research-interesting, especially as a regime phenomenon, but it did not clear timing/effective-sample concerns. It is not operational.

### DSS-CW-001

Contraction Window was the frozen final timing hypothesis. It failed because timing placebos +1 and +2 dominated the base, the base ranked third, and WRC/SPA-light rejected the base as the family winner.

## Research-Interesting Hypothesis

The only surviving idea is not a tradable pattern: contraction/regime behavior may contain information, but the current Daily timing specifications do not isolate a defensible entry edge. Any future work should pre-register a new search space rather than rescue +1/+2 placebos or retrofit the current candidates.

## Remaining Gaps

- Formal SPA/WRC implementation beyond the current light approximation.
- Portfolio-normalized drawdown and exposure accounting.
- Risk/R framework with stops, not only percent-return time stops.
- More historical depth if the data source and survivorship controls allow it.
- Sector, earnings, liquidity, and corporate-action filters where relevant.
- Event-calendar reliability if earnings/post-earnings drift is pursued.

## Strategic Recommendation

Do not paper Daily now. Preserve the infrastructure and negative evidence. Close this branch as research infrastructure only after cleanup, then open a new pre-registered search-space task if Direction wants more Daily work.

Possible future search spaces, design only:

- earnings/post-earnings drift if calendar data is reliable.
- gap plus continuation/reversal.
- sector or relative strength.
- market breadth plus pullback.
- daily-to-intraday hybrid entry.
- ETF/macro work in `etf_macro`, separate from stock Daily.

## Explicit Candidate Status

- shadow_candidate: none
- paper_candidate: none
- live_candidate: none
- operational_signal_candidate: none
