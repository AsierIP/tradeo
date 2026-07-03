# Intraday VWAP Cost/Regime Plan

The current VWAP evidence says VWAP is useful context, but not a standalone edge. The reviewed pure VWAP families all failed before any Paper, Shadow, or Live promotion:

- `vwap_reclaim_long 30m W100`: rejected by OOS, cost, drawdown, statistics, and regime instability.
- `vwap_reject_short 30m W100`: rejected by OOS, cost, drawdown, statistics, regime instability, and side issues.
- `vwap_above_rising 30m W100`: rejected after confirmation gate hardening; the near miss had excessive drawdown and negative market replay.
- `vwap_pullback_long 15m W50`: rejected by cost/OOS/statistics/replay despite clean side integrity.

Next research should add explicit filters before another wave:

1. Low spread/cost or low churn.
2. Session filter, preferably mid-session first.
3. RVOL/gap context when available.
4. SPY/QQQ regime agreement for directional hypotheses.
5. Exact execution contract integrity with no material requested-vs-actual mismatches.

Primary proposal for the next Director-authorized wave:

`30m_W50_vwap_above_rising_long_low_cost_mid_session`

- timeframe: `30m`
- window size: `50`
- forward bars: `4,8,13`
- expected side: `long`
- filters: `low_cost`, `mid_session`, `low_churn`

Secondary proposal:

`1h_W100_vwap_above_rising_long_spy_qqq_positive_regime`

- timeframe: `1h`
- window size: `100`
- forward bars: `2,4,6`
- expected side: `long`
- filters: `SPY_positive_regime`, `QQQ_positive_regime`, `low_churn`

Do not repeat `15m W50 2,3,4 vwap_pullback_long` unless Director explicitly authorizes a repeat.
