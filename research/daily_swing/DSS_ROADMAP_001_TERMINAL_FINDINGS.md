# DSS-ROADMAP-001 Terminal Findings

Task: T-DAILY-ROADMAP-001
Generated: 2026-07-05
Scope: documentation-only roadmap selection. No backtests, downloads, IBKR, signals, previews, paper, live, cron, `gh`, merge, or main push were used.

## Executive Summary

The PB/BO/CO/CW Daily family is closed. It produced useful reusable Daily research infrastructure, but no shadow, paper, or live candidate. The next Daily line should not rescue those patterns or create DSS-005; it should begin as a new pre-registered search-space with explicit data, leakage, adversarial, and rejection criteria before any implementation.

## Terminal Candidate Summary

| Candidate | What it tested | Terminal finding | Why it does not advance |
| --- | --- | --- | --- |
| DSS-PB-001 | Daily pullback behavior on stock-only universe with market benchmark context | Research fail after OOS/cost review | Evidence did not survive the required OOS/cost review strongly enough to justify shadow or paper. |
| DSS-BO-001 | Trend/contraction/breakout behavior with next-session execution model | Baseline explained fail | The apparent edge was explainable by simpler contraction/regime behavior and did not prove specific breakout value. |
| DSS-CO-001 | Contraction-only continuation family and episode/timing checks | Timing and effective-sample warning | Signal quality remained too dependent on timing/window assumptions and sample adequacy was not strong enough. |
| DSS-CW-001 | Contraction-window episode rule with MAX2 policy and stat-light checks | Timing not specific fail | Declared timing placebos dominated; FDR/WRC/SPA-light did not support a specific timing edge. |

## Tools Gained

- Daily OHLCV universe and cache tooling with read-only guardrails, resume, caps, timeout handling, and quarantine support.
- Daily cache quality gates that reject malformed OHLCV, fake holiday bars, missing symbols, non-stock operational rows, and insufficient ready symbols.
- Stock-only universe validation with SPY/QQQ benchmark-only separation.
- Cache-only Daily backtest runners for PB/BO/CO/CW families.
- No-lookahead guards around signal date, next-session entry, prior-high/ATR features, and holiday bars.
- Cost stress at multiple bps levels and OOS/IS split reporting.
- Baseline, placebo, matched-random, timing-window, concentration, effective-sample, and light FDR/WRC/SPA audits.
- Read-only IBKR connectivity and historical-data diagnostics, preserved as diagnostics only and not used in this task.
- Focal Daily test surface covering the preserved research modules and scripts.

## Methodological Gaps To Preserve

- WRC/SPA remains light/approximate and must not be treated as formal multiple-testing control.
- The current Daily families did not establish stop/R, position sizing, or portfolio-normalized drawdown suitable for operation.
- Generated/runtime artifacts and cached OHLCV are intentionally excluded from clean tracking; future research must regenerate or declare inputs explicitly.
- Any data source with earnings timestamps, sector classifications, breadth series, or macro/ETF membership needs a separate timestamp and survivorship audit before testing.
- Daily-to-intraday hybrids add execution complexity and must be pre-registered as mixed-timeframe research, not as a quiet extension of the closed Daily family.

## Decision Implication

PB/BO/CO/CW remain terminal and should not be rescued. The next task should select one new search-space and produce a protocol before any code or backtest implementation.
