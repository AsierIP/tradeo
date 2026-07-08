# Lab Paper Readiness

- status: `READY_FOR_DIRECTOR_PAPER_REVIEW`
- paper_readiness_decision: `READY_FOR_DIRECTOR_PAPER_REVIEW`
- dry_run_only: `True`
- submit_allowed: `False`
- paper_allowed_actual: `False`
- blockers: `[]`
- gaps: `[]`

## Checks

- trading_mode_not_live: `True` (blocker)
- live_trading_disabled: `True` (blocker)
- live_not_armed: `True` (blocker)
- intraday_live_disabled: `True` (blocker)
- intraday_paper_disabled_for_tlab002: `True` (blocker)
- ibkr_readonly: `True` (blocker)
- ibkr_not_live_port: `True` (blocker)
- market_orders_disabled: `True` (blocker)
- lab_auto_submit_paper_disabled: `True` (blocker)
- fox_auto_submit_live_disabled: `True` (blocker)
- reconciliation_auto_repair_paper_exits_disabled: `True` (blocker)
- kill_switch_clear: `True` (gap)
- max_trades_per_day_defined: `True` (gap)
- max_daily_loss_defined: `True` (gap)
- max_position_value_defined: `True` (gap)
- ibkr_max_order_value_defined: `True` (gap)

The bracket preview is dry-run only. This script never imports broker adapters and never sends orders.
