# LAB_FOXHUNTER_001 Gate Criteria

## Research to Lab Gate

Allows `lab_paper_probe` only when all of the following are true:

- No lookahead.
- No leakage.
- Product policy OK.
- Data quality OK.
- Pattern documented.
- Hypothesis clear.
- Operational risk bounded.
- Failure reason is not fatal.
- No safety violation.
- Logs available.
- Pattern reproducible.
- Direccion approved.

Blocks on:

- Lookahead.
- Leakage.
- False data.
- Disallowed product.
- Live risk.
- Missing logs.
- Non-reproducible pattern.
- Security violation.

## Lab to FoxHunter Gate

Minimum criteria:

- `paper_trades_count >= 20`.
- `success_count >= 12`.
- `expectancy_net > 0`.
- `profit_factor > 1.15`, with `> 1.2` preferred.
- Real cost/slippage not destructive.
- Max drawdown within limit.
- `operational_errors = 0`.
- `reconciliation_errors = 0`.
- Top symbols/events not concentrated.
- Last N trades not clearly degraded.
- Logs complete.
- No manual overrides.
- Direccion approved.

Possible candidate decisions:

- `stay_in_lab`.
- `stop_probe`.
- `eligible_for_foxhunter_review`.

## FoxHunter to Live Gate

Minimum criteria:

- Lab to FoxHunter gate passed.
- Risk review passed.
- Kill-switch tested.
- `live_armed` controlled.
- Max daily loss configured.
- Max position value configured.
- Max trades configured.
- Paper/live account separation confirmed.
- Human review complete.
- Explicit Asier/Direccion authorization.

## Required Lab Probe Telemetry

- `probe_id`.
- `strategy_source_id`.
- `symbol`.
- `decision_time`.
- `intended_side`.
- `intended_entry_type`.
- `theoretical_open`.
- `submitted_paper_order`, reserved for future phases.
- `paper_fill_price`.
- `fill_latency_ms`.
- `bid`.
- `ask`.
- `last`.
- `spread_bps`.
- `slippage_bps`.
- `exit_price`.
- `pnl_pct`.
- `pnl_after_costs`.
- `success_flag`.
- `reason_success_failure`.
- `mfe`.
- `mae`.
- `ibkr_state`.
- `kill_switch_state`.
- `risk_limits_state`.
- `reconciliation_status`.

## Required 20-Trade Metrics

- `paper_trades_count`.
- `success_count`.
- `winrate`.
- `expectancy_net`.
- `profit_factor`.
- `avg_win`.
- `avg_loss`.
- `max_drawdown`.
- `worst_streak`.
- `avg_slippage_bps`.
- `fill_rate`.
- `rejected_orders`.
- `operational_errors`.
- `reconciliation_errors`.
- `candidate_decision`.
