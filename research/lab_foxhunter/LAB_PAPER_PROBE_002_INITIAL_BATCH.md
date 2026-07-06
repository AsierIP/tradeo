# LAB Paper Probe 002 Initial Batch

Task: `T-LAB-PAPER-PROBE-002`.

Purpose: prepare the first supervised Lab paper-probe batch for measuring GAP same-day reversal open slippage and fill realism. This is a Lab measurement batch, not FoxHunter promotion and not live.

## Batch

- Batch ID: `LAB-PAPER-PROBE-002`.
- Max probes: 2.
- Mode: supervised Lab paper probe.
- Global auto-submit: disabled.
- Broker submit from this task: disabled.
- Signals/previews: disabled.
- FoxHunter/live promotion: disabled.

## Selected Probes

1. `LAB-GAP-REV-001`
   - Source: `GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL`.
   - Goal: measure real open slippage and fill realism.
   - Max initial paper trades: 20.
   - Success threshold: 12.
   - Extra requirement: net expectancy after costs positive.

2. `LAB-GAP-REV-002`
   - Source: `GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0`.
   - Goal: measure weak-SPY regime behavior.
   - Max initial paper trades: 20.
   - Success threshold: 12.
   - Extra requirement: net expectancy after costs positive.

## Explicit Non-Promotions

- No GAP source becomes `foxhunter_candidate`.
- No GAP source becomes `live_candidate`.
- PB/BO/CO/CW remain excluded from this batch.
- The only allowed post-batch decisions are `stay_in_lab` or `stop_probe` until a later Lab-to-FoxHunter review task exists.
