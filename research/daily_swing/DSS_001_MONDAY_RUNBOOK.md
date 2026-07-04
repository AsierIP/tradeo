# DSS-001 Monday Runbook

1. Confirm TWS/IB Gateway is paper only.
2. Run `python scripts/check_daily_swing_paper_operability.py --json-output artifacts/runtime/daily_swing/paper_operability_check.json`.
3. Run `python scripts/plan_daily_swing_paper_orders.py`.
4. Confirm `last_valid_bar_date=2026-07-02` and no row uses 2026-07-03.
5. If operability is BLOCKED, do not submit orders.
6. If no valid signals, record `NO_TRADE_VALID_SIGNAL`.
7. If approved after open, execution window is 09:35-10:00 ET, paper-only, limit orders only.
8. Stop immediately on broker/API errors, hash mismatch, kill-switch failure or live account suspicion.
