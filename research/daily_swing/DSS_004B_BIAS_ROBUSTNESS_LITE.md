# DSS-004B Bias and Robustness Lite

Decision: `BIAS_WARNING`

Passed audits:

- Lookahead: `PASS_SIGNAL_T_ENTRY_T_PLUS_1`
- Leakage: `PASS_CACHE_ONLY_NO_FUTURE_SIGNAL_FIELDS`
- Duplicate trades: `PASS`
- Holiday bar: `PASS_NO_2026_07_03_BAR`

Sensitivity:

- Base next open net x2 expectancy / PF: 1.3829% / 1.3917
- Next close net x2 expectancy / PF: 1.3398% / 1.3922
- Next open adverse +10 bps expectancy / PF: 1.2829% / 1.3588
- Placebo +1 expectancy / PF: 1.3340% / 1.3879
- Placebo +2 expectancy / PF: 1.1069% / 1.3155
- Placebo +5 expectancy / PF: 1.3717% / 1.4042

The placebo variants remaining positive is a warning: the result may reflect broad momentum or breakout timing rather than a highly specific contraction signal.

