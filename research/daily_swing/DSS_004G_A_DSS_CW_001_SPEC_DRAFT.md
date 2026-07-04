# DSS-004G-A DSS-CW-001 Spec Draft

## Candidate Name

`DSS-CW-001 Contraction Window`

## Design Intent

`DSS-CW-001` treats contraction in an uptrend as an episode and window phenomenon. It is not a re-test of `DSS-CO-001` with the best delayed offset, and it is not an optimized entry chosen after looking at OOS.

## Frozen Base Specification For Future Research Test

### Universe

- Use research-150 operational equities from the validated Daily OHLCV cache.
- Exclude ETFs, ETPs, funds, and non-operational rows from trades.
- Use `SPY` and `QQQ` only for benchmark/regime support; never as operational trade symbols.

### Regime

- Primary regime: `SPY close > SMA200` or `SPY return20d > 0`.
- `QQQ` may be a documented fallback only if `SPY` data is unavailable in a future research-only run.

### Symbol Trend

- `close > SMA50`, and either `close > SMA200` or `SMA50 > SMA200`.

### Contraction

- `ATR14_pct = ATR14 / close`.
- Use `ATR14_pct(t-1)`, never `t`.
- Signal condition: `ATR14_pct(t-1) <= rolling 120-session p40 through t-1`.
- If the 120-session rank is unavailable, no signal.

### Episode Definition

- Episode grouping: `EPISODE_GAP_5` by trading-session signal index, matching the canonical DSS-004F-R code path.
- A new episode begins when the next qualifying signal for the same symbol is more than 5 trading sessions after the previous qualifying signal.
- Episode fields should include `episode_id`, `symbol`, `first_signal_date`, `last_signal_date`, `signal_count`, and contraction rank summary.

### Window Eligibility

- Window starts at `first_signal_date`.
- Window ends at the earlier of:
  - `first_signal_date + 5 trading sessions`, or
  - `last_signal_date` for the episode.
- A future entry may occur only on an eligible session in this pre-registered window.

### Entry Rule

- For research testing, entry is the first eligible session that passes all portfolio filters and has an executable next-open theoretical entry.
- This rule deliberately avoids choosing offset +1, +2, or +5 because those looked good in `DSS-004F-R`.
- Tie-break priority for same-day candidates:
  1. Lower `ATR14_pct_rank` from `t-1`.
  2. Earlier `first_signal_date`.
  3. Stable symbol sort.

### Exit Rule

- Exit at close after 10 trading sessions from entry.
- If the sample ends first, use the last available close and mark `truncated=true`.
- No ATR stop, take-profit, discretionary exit, or intraday execution model in this research phase.

### Solape And Portfolio Policy

- One active episode per symbol.
- At most two new episodes per day.
- Do not add a second trade for the same symbol while an episode position is active.
- Do not trade multiple entries inside one episode.

### Costs

- x1: 10 bps round-trip.
- x2: 20 bps round-trip, primary decision cost.
- x3: 30 bps round-trip stress cost.

### Metrics

- OOS net expectancy x2 and x3.
- OOS profit factor x2 and x3.
- MAX2 portfolio-like performance.
- Symbols OOS, episode count OOS, and episode concentration.
- Top3 contribution and top5 trade share.
- Last 12 months expectancy.
- Bootstrap by symbol and symbol-month.
- Placebo/adversarial comparisons.

## Allowed Variants

Allowed variants are only research hypotheses and must be evaluated with correction for multiple testing:

- Episode gap: 3, 5, or 10 trading sessions.
- Window length: 3, 5, or 10 trading sessions.
- Priority rule: lower ATR rank, lower realized volatility rank, or stable random seed priority.
- Portfolio cap: one or two new episodes per day.

No allowed variant may be selected after inspecting OOS without labeling the result as exploratory.

## Prohibited Variants

- Choosing offset +1, +2, +5, or +10 as a strategy because it outperformed in `DSS-004F-R`.
- Changing the contraction percentile after seeing OOS.
- Changing the exit horizon after seeing OOS.
- Adding stops, take-profit, or intraday filters in the same research test.
- Using live, paper, preview, or broker data.

## Draft Status

This is a design draft ready for Director review. It is not an executed strategy and does not authorize `DSS-004G-B`.
