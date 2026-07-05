# DSS-GAP-001 Preregistered Spec

Task: T-DAILY-GAP-001
Pattern id: DSS-GAP-001
Status: protocol-only

## Hypothesis

Overnight gaps may contain conditional information about same-day or next-day continuation/reversal. Any edge must survive stock-only universe controls, conservative costs, adverse open slippage, delayed-entry tests, sign-inversion tests, matched non-gap baselines, concentration checks, and OOS validation.

This protocol separates four families before any backtest:

1. `GAP_CONTINUATION_SAME_DAY`
2. `GAP_REVERSAL_SAME_DAY`
3. `GAP_CONTINUATION_NEXT_DAY`
4. `GAP_REVERSAL_NEXT_DAY`

No family is approved for execution in this task.

## Universe

- `stock_only`.
- US common stocks only when product metadata allows it.
- Exclude ETFs, ETPs, funds, inverse products, leveraged products, and non-stock instruments.
- SPY/QQQ may be used only as benchmark/regime references, not as tradable symbols.
- Minimum liquidity thresholds must be fixed before any event-ledger or backtest run.

## Required Data

Minimum fields:

- `close_t_minus_1`
- `open_t`
- `high_t`
- `low_t`
- `close_t`
- `volume_t`
- prior adjusted OHLCV history for ATR/volatility and prior returns
- SPY/QQQ benchmark history for regime context

Future optional blockers:

- timestamp-safe earnings calendar;
- point-in-time sector map;
- audited breadth data.

## Variables

Pre-registered variables:

- `gap_pct = open_t / close_t_minus_1 - 1`
- `abs_gap_pct`
- `gap_direction`
- `atr14_pct_t_minus_1`
- `gap_vs_atr = gap_pct / atr14_pct_t_minus_1`
- `prior_return_5d`
- `prior_return_20d`
- `benchmark_return_20d`
- `open_to_close_return = close_t / open_t - 1`
- `next_open_to_close_return`, if next-day holding is evaluated later

`gap_fill_ratio` may be computed for analysis after the bar closes, but it must not be used as an open-time signal input.

## Same-Day Families

Same-day families assume the decision is known at `open_t`.

Allowed open-time signal inputs:

- `close_t_minus_1`
- `open_t`
- historical volume through `t-1`
- `atr14_pct_t_minus_1`
- `prior_return_5d_t_minus_1`
- `prior_return_20d_t_minus_1`
- `benchmark_return_20d_t_minus_1`

Forbidden signal inputs:

- `high_t`
- `low_t`
- `close_t`
- `volume_t`
- `gap_fill_ratio_t`

Entry model:

- `open_t_with_adverse_slippage`

Target families:

- continuation: `open_t -> close_t` in gap direction;
- reversal: `open_t -> close_t` against gap direction.

## Next-Day Families

Next-day families assume the decision is calculated after `close_t` and can enter at `open_t_plus_1`.

Allowed inputs include completed day `t` OHLCV because the decision occurs after the close:

- `close_t_minus_1`
- `open_t`
- `high_t`
- `low_t`
- `close_t`
- `volume_t`
- prior volatility and returns
- benchmark context through close `t`

Entry model:

- `open_t_plus_1_with_adverse_slippage`

Target families:

- continuation after close `t`;
- reversal after close `t`.

## Pre-Registered Rejection Criteria

Reject if any of the following dominate:

- OOS expectancy net x2 <= 0.
- OOS PF < 1.
- Edge disappears under x2 costs or is severely unstable under x3 costs.
- Matched non-gap baseline explains the result.
- Sign-inverted gap placebo dominates.
- Delayed-entry placebo dominates.
- A few trades or symbols explain the result.
- Earnings gaps explain the result and no timestamp-safe earnings calendar exists.
- Same-day logic uses any post-open unknown input.
- Open slippage makes the result non-operable.
- FDR/WRC/SPA-light family checks fail materially.

## Future Minimum Research-Pass Criteria

Future `research_pass` requires, at minimum:

- OOS expectancy net x2 > 0.
- Prefer OOS PF x2 > 1.2.
- Effective sample is sufficient.
- At least 20 OOS symbols for research-150 style tests.
- Top 3 symbols and top 5 trades do not explain most of the result.
- Last 12 months are not negative.
- Cost x3 does not destroy the candidate in an extreme way.
- Placebo/adversarial tests do not dominate.
- No calendar, adjustment, product-policy, or lookahead failure.
- Drawdown is portfolio-normalized and reasonable once portfolio constraints exist.

These are necessary conditions, not paper approval.

