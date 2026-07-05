# DSS GAP-007 Statistical / Baseline / Placebo Verdict

Decision: `STAT_BASELINE_WARNING`.

Baseline and placebo controls:

- MATCHED_NON_GAP: expectancy x2 -0.00203712, PF x2 0.724939.
- RANDOM_MATCHED: expectancy x2 -0.00174909, PF x2 0.815529.
- SIGN_INVERTED_GAP: expectancy x2 -0.00371776, PF x2 0.730386.
- DELAYED_ENTRY: expectancy x2 -0.00122391, PF x2 0.891117.
- THRESHOLD_PERTURBATION: expectancy x2 -0.00043096, PF x2 0.963158.

Stat-light verdict:

- Best target: `GAP006_OBS1_REFERENCE_ALL`, expectancy x2 0.00356055.
- Best control: `GAP006_PLACEBO_THRESHOLD_PERTURBATION_PAIR`, expectancy x2 -0.00043096.
- Baseline/placebo dominance: false.
- Bootstrap p05 negative: false for the best target in the lightweight check.
- WRC/SPA-light status: PASS.

Interpretation:

The statistical controls do not explain away the best all-events observation. However, this does not rescue GAP-007 because operability constraints and open slippage fail before candidate approval can be considered.
