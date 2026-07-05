# DSS GAP-007 Input Integrity

Decision: `CONFIRMATORY_INPUT_PASS`.

Scope:

- Matrix: `research/daily_swing/gap/dss_gap_006_confirmatory_matrix.json`.
- Criteria: `research/daily_swing/gap/DSS_GAP_006_CONFIRMATION_CRITERIA.json`.
- Ledger: `artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger.csv`.

Findings:

- GAP-007 uses the closed GAP-006 matrix only.
- Matrix rows: 12.
- Allowed observations: `GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL` and `GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0`.
- Confirmation targets: 6.
- Baseline rows: 2.
- Placebo rows: 4.
- Required policies present: `ONE_ACTIVE_PER_SYMBOL`, `MAX_2_NEW_TRADES_PER_DAY`.
- Slippage stresses present: `10bps`, `25bps`, `50bps`, `75bps`.
- Security flags are false for execution, paper, live, preview and signal output.
- Ledger rows: 114304, date range 2023-07-05 to 2026-07-02.
- No fake 2026-07-03 event was used.
- SPY/QQQ remain benchmark/regime inputs only; stock-only execution universe is enforced by `product_class` and `is_stock_operational`.
- Runtime outputs remain under ignored `artifacts/runtime`.

Safety:

No orders, no paper, no live, no preview, no signals, no IBKR, no downloads, no cron, no `.env` changes, no main push.
