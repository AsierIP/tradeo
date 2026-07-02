# Intraday VWAP Research Strategy

## Objective

VWAP becomes a primary research axis for intraday Tradeo work. It is not a
paper/live signal and it does not relax any gate. The first goal is to measure
how patterns behave around session VWAP so future research waves can separate
continuation, rejection, pullback, extension and mean-reversion families.

## VWAP Definition

Default VWAP uses typical price:

```text
typical_price = (high + low + close) / 3
vwap = cumulative_sum(typical_price * volume) / cumulative_sum(volume)
```

Close-based VWAP is supported for sensitivity checks, but typical price is the
default research contract. VWAP resets every regular US equity session in
`America/New_York`, from `09:30` inclusive to `16:00` exclusive.

## No Lookahead

VWAP features must only use the current bar and previously closed bars. Future
outcomes, forward returns and confirmation labels must live in separate outcome
or validation layers. Entry features cannot use future VWAP, future highs/lows,
or future volume.

The feature module marks this contract in metadata with `no_lookahead=true`.

## Session Handling

Bars are converted into `America/New_York`. Naive timestamps are localized to
that timezone and recorded as an assumption in metadata. Timezone-aware bars are
converted to the session timezone. Bars outside `09:30-16:00` are marked
`out_of_session` and do not contribute to session VWAP.

Session buckets:

- `open`: first 60 minutes of the regular session.
- `mid`: regular session after open and before final hour.
- `close`: final 60 minutes before 16:00.
- `out_of_session`: premarket, postmarket or exact 16:00+ bars.
- `unknown`: reserved for future data contracts that cannot infer session state.

## Hypothesis Families

Long continuation:

- Price reclaims VWAP from below.
- The reclaim happens on a closed bar.
- VWAP slope is positive or stable.
- Volume and later pullback behavior confirm acceptance.
- Exit/invalidación if price loses VWAP.

Long mean reversion:

- Price is materially below VWAP.
- Selling extension is extreme.
- Exhaustion or compression appears.
- Partial objective is VWAP.
- Invalidación if downside extension continues.

Short continuation:

- Price loses VWAP from above.
- VWAP slope is negative or stable.
- Rebound rejects VWAP.
- Exit/invalidación if price reclaims VWAP.

Short mean reversion:

- Price is materially above VWAP.
- Buying extension is extreme.
- Exhaustion or failed continuation appears.
- Partial objective is VWAP.
- Invalidación if upside extension continues.

## Candidate Features

The first feature contract emits:

- `vwap`
- `vwap_distance_pct`
- `vwap_distance_bps`
- `vwap_distance_atr`
- `above_vwap`
- `below_vwap`
- `crossed_above_vwap`
- `crossed_below_vwap`
- `bars_since_vwap_cross`
- `vwap_slope_bps`
- `vwap_slope_direction`
- `session_bucket`

The first event contract emits:

- `vwap_reclaim_long`
- `vwap_loss_long_exit`
- `vwap_hold_long`
- `vwap_reject_short`
- `vwap_loss_short`
- `vwap_reclaim_short_exit`
- `vwap_extension_up`
- `vwap_extension_down`
- `vwap_mean_reversion_candidate`

## Executable VWAP Conditions

Research sampling supports an opt-in VWAP conditioning contract. Default is
`vwap_condition=none`, which preserves legacy sampling exactly. Any non-`none`
condition is evaluated only on the closed bar at each window `end_pos`; future
bars are used only for the existing forward outcome labels after the window has
already passed or failed the VWAP filter.

Supported conditions:

- `vwap_reclaim_long`: close is above VWAP after a current/recent reclaim from below, with VWAP slope flat or rising by default.
- `vwap_reject_short`: close is below VWAP and the closed bar confirms a VWAP rejection/loss.
- `vwap_pullback_long`: price remains above VWAP, pulls back near VWAP and holds it.
- `vwap_pullback_short`: price remains below VWAP, tests near VWAP and rejects it.
- `vwap_above_rising`: close is above VWAP and VWAP slope is flat/rising.
- `vwap_below_falling`: close is below VWAP and VWAP slope is flat/falling.
- `vwap_mean_reversion_long`: price is extended below VWAP by the configured distance threshold.
- `vwap_mean_reversion_short`: price is extended above VWAP by the configured distance threshold.

Optional knobs:

- `vwap_side_bias`: `long`, `short` or empty; inferred from the condition when omitted.
- `vwap_max_distance_bps`: caps near-VWAP distance for pullback/regime filters and sets extension distance for mean reversion.
- `vwap_min_slope_bps`: minimum slope for rising/falling conditions.

Conditioned windows record VWAP fields in `WindowSample.features`. Discovery
summaries record `windows_vwap_selected`, `windows_vwap_rejected` and
`vwap_condition_applied`.

## Validation Metrics

VWAP-aware families must still pass normal research validation:

- OOS expectancy and profit factor.
- Cost stress.
- FDR, SPA and WRC controls.
- Drawdown and tail loss.
- Regime splits.
- Placebo and adversarial checks.
- Symbol concentration.
- Session bucket/month split stability.

VWAP cannot be used as a shortcut around statistical controls.

## Paper And Live Status

This work does not authorize paper or live. It creates only research features,
tests and documentation. A future candidate must survive Research, then Shadow
without orders, before any paper discussion.

## Evidence And Planner Integration

Next steps should integrate VWAP fields into Evidence and Planner outputs so
Director can answer:

- Which VWAP family produced the candidate?
- Did outcomes differ by open/mid/close buckets?
- Did VWAP distance or slope explain rejection?
- Was the candidate concentrated in only one symbol or one session regime?
- Did VWAP invalidation/target behavior improve cost-adjusted outcomes?

Future VWAP-aware search families may include:

- `30m_W100_vwap_reclaim_slow`
- `30m_W100_vwap_reject_slow`
- `15m_W50_vwap_pullback_fast`
- `1h_W100_vwap_regime_filter`

They must still be checked against `prohibited_repeats` before execution.

VWAP-conditioned signatures include the executable condition, for example:

- `30m W100 8,13,21 vwap_reclaim_long`
- `30m W100 8,13,21 vwap_reject_short`

A legacy prohibited repeat such as `30m W100 8,13,21` is marked
`legacy_overlap=true` but is not blocked when an explicit VWAP condition is
present, because the conditioned sample universe is a distinct hypothesis.
