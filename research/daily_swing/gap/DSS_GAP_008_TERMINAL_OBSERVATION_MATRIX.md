# DSS GAP-008 Terminal Observation Matrix

Decision: `GAP_TERMINAL_OBSERVATIONS_CLOSED`.

| observation_id | policy | threshold | confirmatory_status | OOS x2 | PF x2 | slippage 50 bps | operability | baseline/placebo | final_class |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL | ALL/ONE_ACTIVE pass; MAX2 fail | abs_gap_pct >= 0.030 | FAIL_OPEN_SLIPPAGE | 0.00356055 all/one-active; -0.00209933 MAX2 | 1.237430 all/one-active; 0.878991 MAX2 | 0.00056055 all/one-active; -0.00509933 MAX2 | MAX2 fail | Not dominated | REJECTED_OPERABILITY |
| GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0 | ALL/ONE_ACTIVE slippage fail; MAX2 fail | abs_gap_pct >= 0.010, SPY <= 0 | FAIL_OPEN_SLIPPAGE | 0.00172545 all/one-active; -0.00211581 MAX2 | 1.145552 all/one-active; 0.846896 MAX2 | -0.00127455 all/one-active; -0.00511581 MAX2 | MAX2 fail | Not dominated | REJECTED_OPEN_SLIPPAGE |

No observation is promoted to any candidate class. GAP same-day reversal is closed for the current protocol.
