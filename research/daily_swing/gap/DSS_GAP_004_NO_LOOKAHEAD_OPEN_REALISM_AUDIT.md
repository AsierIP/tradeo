# DSS-GAP-004 No-lookahead / Open Realism Audit

Decision: GAP_DRY_RUN_NO_LOOKAHEAD_PASS

Assertions:
- Same-day selection uses only matrix `required_known_fields`, which exclude close, high, low, volume, open-to-close return, next-day returns, gap fill flag, and gap fill ratio.
- Same-day outcome is computed after selection from open_t to close_t.
- Next-day selection is after close_t and may use after-close fields while still forbidding t+1 outcome fields.
- Delayed-entry rows remain placebo rows and are not promoted to strategy rows.
- Baseline/placebo rows preserve `candidate_approval=false`.
- Open adverse slippage stress is applied in the dry-run sensitivity metrics at 10, 25, and 50 bps.
- SPY/QQQ fields are used only as benchmark/regime fields and not as operational symbols.

Result:
- No signal list, preview list, order list, paper candidate, shadow candidate, or live candidate was produced.
