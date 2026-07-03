# VWAP Cost/Regime Search Plan

Generated: `2026-07-03T17:11:55Z`

Decision: request Director authorization for a new cost/regime-filtered family. Do not repeat a pure VWAP family.

## Prior Results

- `T-004R vwap_reclaim_long 30m W100`: rejected, `0/48` accepted. Dominant blockers were OOS, statistics, regime sensitivity, cost, and drawdown.
- `T-008R vwap_reject_short 30m W100`: rejected, `0/45` accepted. Dominant blockers were OOS, statistics, regime sensitivity, cost, drawdown, and side problems.
- `T-012 vwap_above_rising 30m W100`: rejected, `0/8` accepted. The near miss failed hardened drawdown and market replay gates.
- `T-014 vwap_pullback_long 15m W50`: rejected, `0/8` accepted. Side integrity was clean, but every candidate failed cost/OOS/statistical/replay checks.

## Blocker Matrix

- `cost_dominated`: present across all reviewed families. Mitigation: low spread/cost filters, slower forward sets, and low churn.
- `oos_unstable`: present across all reviewed families. Mitigation: session and broad-market regime splits.
- `regime_sensitive_candidate`: present across all reviewed families. Mitigation: SPY/QQQ regime gates.
- `drawdown_excessive`: present in the 30m families. Mitigation: avoid confirmation unless replay and drawdown are both clean.
- `side_mismatch`: present in T-012. Mitigation: keep expected side explicit and material in execution contract integrity.

## Recommended Primary

`30m_W50_vwap_above_rising_long_low_cost_mid_session`

- timeframe: `30m`
- window_size: `50`
- forward_bars: `4,8,13`
- expected_side: `long`
- filters: `low_cost`, `mid_session`, `low_churn`
- reason: best first response to repeated cost/OOS failures without shrinking the sample as much as 1h.

## Recommended Secondary

`1h_W100_vwap_above_rising_long_spy_qqq_positive_regime`

- timeframe: `1h`
- window_size: `100`
- forward_bars: `2,4,6`
- expected_side: `long`
- filters: `SPY_positive_regime`, `QQQ_positive_regime`, `low_churn`
- reason: stronger regime gate if Director wants fewer but cleaner samples.

## Rejected Options

- Do not repeat `15m W50 2,3,4 vwap_pullback_long` without explicit repeat authorization.
- Do not run broad VWAP without cost or regime filters.
- Do not move any T-014 candidate to confirmation, Shadow, Paper, or Live.

## Acceptance Criteria

- OOS expectancy `> 0`
- OOS PF `> 1.2`
- cost x2 `passed`
- max drawdown `<= 12R`
- FDR/WRC/SPA not failed
- market replay not failed and not negative
- side matches hypothesis
- symbol count `>= 6`
- no severe concentration
- execution contract integrity has no material mismatches

## Safety

- wave_executed: `false`
- cache_executed: `false`
- paper_allowed: `false`
- live_allowed: `false`
- orders_allowed: `false`
- ibkr_used: `false`
- shadow_scheduler_unchanged: `true`
