# DSS-GAP-003 No-Lookahead Matrix Audit

Task: T-DAILY-GAP-003
Decision: MATRIX_NO_LOOKAHEAD_PASS

## Same-Day Families

Same-day continuation and reversal rows decide at `open_t`. Their required known
fields are restricted to symbol/date identity, `open_t`, `prev_close`, gap fields,
ATR/return fields available through t-1, and benchmark return fields available
through t-1.

Forbidden same-day decision fields are explicitly listed in every same-day row:

- `high_t`
- `low_t`
- `close_t`
- `volume_t`
- `gap_fill_ratio`
- `open_to_close_return`
- `close_to_next_open_return`
- `next_open_to_close_return`
- `intraday_gap_fill_flag`

## Next-Day Families

Next-day continuation and reversal rows decide after `close_t` and enter at
`open_t_plus_1`. Completed day-t fields are therefore allowed as required known
fields: `high_t`, `low_t`, `close_t`, and `volume_t`.

## Gap And Prior Fields

- `gap_pct` remains defined as `open_t / prev_close - 1`.
- `abs_gap_pct` and `gap_direction` derive from that open-time gap.
- `atr14_pct_prev`, `gap_vs_atr_prev`, `prior_return_5d`, and `prior_return_20d`
  are prior fields and must not use day-t close/high/low outcomes.
- SPY/QQQ remain benchmark/regime references only.

## Audit Decision

MATRIX_NO_LOOKAHEAD_PASS.
