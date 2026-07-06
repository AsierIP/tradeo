# LAB_FOXHUNTER_001 Initial Probes

## LAB-GAP-REV-001

- source: `GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL`
- status: `proposed_lab_paper_probe`
- rationale: measure open slippage and fill realism
- max_initial_paper_trades: 20
- success_threshold: 12
- extra requirement: net expectancy positive
- disabled_by_default: true

## LAB-GAP-REV-002

- source: `GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0`
- status: `proposed_lab_paper_probe`
- rationale: measure behavior in weak SPY regime
- max_initial_paper_trades: 20
- success_threshold: 12
- extra requirement: net expectancy positive
- disabled_by_default: true

## Required Telemetry

`probe_id`, `strategy_source_id`, `symbol`, `decision_time`, `intended_side`, `intended_entry_type`, `theoretical_open`, `submitted_paper_order`, `paper_fill_price`, `fill_latency_ms`, `bid`, `ask`, `last`, `spread_bps`, `slippage_bps`, `exit_price`, `pnl_pct`, `pnl_after_costs`, `success_flag`, `reason_success_failure`, `mfe`, `mae`, `ibkr_state`, `kill_switch_state`, `risk_limits_state`, `reconciliation_status`.

## 20-Trade Metrics

`paper_trades_count`, `success_count`, `winrate`, `expectancy_net`, `profit_factor`, `avg_win`, `avg_loss`, `max_drawdown`, `worst_streak`, `avg_slippage_bps`, `fill_rate`, `rejected_orders`, `operational_errors`, `reconciliation_errors`, and `candidate_decision`.
