# DSS-ROADMAP-001 Pre-Registration Draft

Task: T-DAILY-ROADMAP-001
Recommended search-space: Gap continuation / gap reversal
Generated: 2026-07-05
Status: draft only. Do not implement from this document without a new Director task.

## Hypothesis

Large overnight gaps in stock-only Daily symbols may show conditional continuation or reversal over a short holding window when filtered by prior trend, prior volatility, volume confirmation, and market regime. The research question is not whether gaps are visually common; it is whether a pre-declared, executable next-session model survives OOS, costs, adverse open assumptions, and timing/placebo tests.

## Universe

- Stock-only Daily universe from the existing DSS-003/DSS-004 clean infrastructure.
- SPY and QQQ remain benchmark-only and are not tradable symbols.
- No ETF/macro products, no sector/macro expansion, and no rescued PB/BO/CO/CW rules.
- Any symbol with invalid OHLCV, duplicate dates, fake holiday bars, missing opens, or non-stock product type is excluded by the existing quality gate.

## Data Needed

- Existing Daily OHLCV cache only for the first protocol.
- Required columns: `symbol`, `date`, `open`, `high`, `low`, `close`, `volume`.
- No new downloads, IBKR calls, or external event/classification data are part of this draft.
- If fresh data is needed later, it requires a separate authorized task and must remain read-only.

## Preliminary Signal Definition

The implementation phase should pre-register exact thresholds before running any backtest. The following structure is allowed for design:

- Gap size: absolute overnight gap from prior close to current open, bucketed by pre-declared percent or ATR-normalized thresholds.
- Direction: up-gap and down-gap are separate families; continuation and reversal are separate declared variants.
- Filters: prior trend, prior realized volatility, prior volume regime, and market regime may be used only if computed from data available before the entry decision.
- Entry model: default must assume entry no better than current open plus adverse slippage for signals formed from the gap open. A next-close placebo/adversarial entry must also be evaluated.
- Exit model: pre-declared time stop, with optional stop/R only if specified before testing.

## Split And Costs

- Use the existing IS/OOS date split policy from Daily infrastructure unless a new split is explicitly justified before testing.
- Report full, IS, and OOS metrics.
- Apply existing cost stress at x1/x2/x3 bps levels plus a gap-open adverse-slippage stress.
- Reject any candidate whose OOS edge exists only at optimistic open assumptions.

## Adversarial And Placebo Tests

- Gap threshold perturbation: adjacent pre-declared gap thresholds must not dominate the selected threshold by chance.
- Direction placebo: up-gap logic must not be explained by generic market strength alone; down-gap logic must be tested separately.
- Timing placebo: delayed entry and next-close entry variants must not dominate the base.
- Baseline controls: compare against trend-only, volatility-only, and random matched event days.
- Concentration: cap or fail if top symbols, months, or event clusters explain most OOS edge.
- Multiple-testing: use the existing light FDR/WRC/SPA harness pattern, while labeling it as approximate.

## Rejection Criteria

Reject the search-space if any of the following holds:

- It requires intraday data to define a plausible first-pass Daily edge.
- It depends on choosing execution prices unavailable at decision time.
- OOS expectancy/profit factor fails under x2 cost or adverse open slippage.
- Placebo timing, baseline, or threshold perturbation variants match or beat the selected rule.
- Edge is concentrated in too few symbols, months, or gap clusters.
- The best result is a hidden PB/BO/CO/CW rescue rather than a gap-specific rule.

## Research Pass Criteria

A future protocol may mark `research_pass` only if:

- The rule is pre-registered before execution.
- No-lookahead and data quality gates pass.
- OOS sample size and symbol/month effective sample are adequate.
- OOS net results survive x2 costs and adverse open slippage.
- Timing/placebo/baseline tests do not dominate the candidate.
- Concentration and robustness checks pass.
- The final report states explicitly that research pass is not paper authorization.

## What Blocks Paper

Even after a research pass, paper remains blocked until a separate Director approval defines risk limits, kill-switch, position sizing, operational schedule, broker constraints, and a paper-readiness gate. This draft does not authorize shadow, preview, paper, live, signals, orders, IBKR, or cron.

## Suggested Next Task

T-DAILY-GAP-001-PROTOCOL - Pre-register the exact gap continuation/reversal protocol, thresholds, variants, splits, costs, adverse slippage, and rejection gates. Do not run a backtest in that task unless the Director explicitly authorizes protocol plus implementation as separate phases.
