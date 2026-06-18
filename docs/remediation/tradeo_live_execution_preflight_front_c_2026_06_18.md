# Tradeo Live Execution Preflight Front C - 2026-06-18

Scope: regression-test matrix for the live execution preflight immediately before
IBKR bracket order construction/placement. This front covers market quote
freshness, executable spread/depth, WhatIf margin/commission safety and evidence
persistence. No live config or production manifest was changed.

## Decision

Live order submission must fail closed unless all execution-time facts are fresh,
bounded and persisted:

- market is in the regular US equity session;
- quote snapshot has usable, non-crossed bid/ask and is within max age;
- spread, entry quote slippage, bid size, ask size and top-of-book notional clear
  configured thresholds;
- IBKR WhatIf returns no warning/rejected status, complete positive margin fields
  and commission within USD/R thresholds;
- accepted evidence is copied to trade metadata, signal execution observation and
  the submit audit log.

## Regression Matrix

| Area | Blocker / Evidence | Expected behavior | Test coverage |
| --- | --- | --- | --- |
| Session | Regular market closed | Reject before quote, WhatIf, bracket or placeOrder | `test_live_execution_preflight_rejects_closed_market_before_order_placement` |
| Quote presence | Missing bid/ask | Reject after one snapshot request, before order construction | `test_live_execution_preflight_rejects_missing_bid_ask_before_order_placement` |
| Quote freshness | Stale quote timestamp | Reject before WhatIf/bracket/placeOrder | `test_live_execution_preflight_rejects_stale_quote_before_order_placement` |
| Spread | Spread pct above threshold | Reject as wide spread before WhatIf/bracket/placeOrder | `test_live_execution_preflight_rejects_wide_spread_before_order_placement` |
| Spread | Spread cost R above threshold | Reject as wide spread before WhatIf/bracket/placeOrder | `test_live_execution_preflight_rejects_wide_spread_cost_r_before_order_placement` |
| Quote slippage | Entry quote slippage above threshold | Reject before WhatIf/bracket/placeOrder | `test_live_execution_preflight_rejects_entry_quote_slippage_before_order_placement` |
| Liquidity | Bid size below threshold | Reject before WhatIf/bracket/placeOrder | `test_live_execution_preflight_rejects_low_bid_ask_size_before_order_placement` |
| Liquidity | Ask size below threshold | Reject before WhatIf/bracket/placeOrder | `test_live_execution_preflight_rejects_low_bid_ask_size_before_order_placement` |
| Liquidity | Top-of-book notional below threshold | Reject before WhatIf/bracket/placeOrder | `test_live_execution_preflight_rejects_low_top_of_book_notional_when_mid_is_low`, `test_live_execution_preflight_rejects_top_of_book_notional_just_below_threshold` |
| WhatIf | IBKR WhatIf API failure | Reject before bracket/placeOrder | `test_live_execution_preflight_rejects_whatif_api_error_before_order_placement` |
| WhatIf | Warning text present | Reject before bracket/placeOrder | `test_live_execution_preflight_rejects_whatif_warning_before_order_placement` |
| WhatIf | Missing/invalid margin fields | Reject before bracket/placeOrder | `test_live_execution_preflight_rejects_missing_whatif_commission_or_margin_before_order_placement`, `test_live_execution_preflight_rejects_invalid_whatif_fields_before_order_placement` |
| WhatIf | Missing/invalid commission | Reject before bracket/placeOrder | `test_live_execution_preflight_rejects_missing_whatif_commission_or_margin_before_order_placement`, `test_live_execution_preflight_rejects_invalid_whatif_fields_before_order_placement` |
| WhatIf | Commission above USD/R threshold | Reject before bracket/placeOrder | `test_live_execution_preflight_rejects_high_whatif_commission_before_order_placement` |
| Persistence | Accepted quote and WhatIf evidence | Persist on trade metadata, signal observation and audit details | `test_live_execution_preflight_persists_fresh_quote_snapshot` |
| Scope boundary | Paper submit | Skips live execution preflight and persists `execution_preflight=None` | `test_paper_submit_skips_live_execution_quote_thresholds` |

## Current Gaps

- The tests cover representative over-threshold failures and one just-below
  top-of-book-notional case. Exact-threshold acceptance tests would be useful if
  thresholds are tuned frequently.
- Crossed bid/ask is implemented but not called out in this Front C matrix because
  the requested gap list focused on wide spread, stale quote, liquidity and
  WhatIf blockers.
- WhatIf tests use a local fake IBKR state. A later adapter-level contract test
  against recorded ib_insync `OrderState` examples would reduce drift risk.

## Verification

Run focused:

```bash
backend/.venv/bin/python -m pytest backend/tradeo/tests/test_execution_state_transitions.py -q
backend/.venv/bin/python -m pytest backend/tradeo/tests/test_ibkr_broker_preflight.py -q
```
