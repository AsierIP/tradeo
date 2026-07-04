# DSS-004G-A Operability Protocol

## Purpose

This document defines what would be required later for `DSS-CW-001` to approach shadow or paper status. It does not enable shadow, paper, live trading, previews, signals, broker access, or orders.

## Shadow Candidate Requirements

Before `DSS-CW-001` can become `shadow_candidate`, it must have:

- Frozen specification committed before the test.
- Research-only backtest with passing or explicitly accepted warning status.
- Data guard pass.
- Bias/placebo/adversarial audit.
- Concentration audit.
- Bootstrap by symbol and symbol-month.
- FDR/WRC/SPA-light result or documented blocker.
- No live or paper execution path enabled.

## Paper Probe Candidate Requirements

Before `paper_probe_candidate`, it additionally needs:

- Explicit Asier authorization.
- Risk budget approved in writing.
- Paper-only environment check.
- `live_armed=false` hard gate.
- `paper_enabled=true` only after authorization.
- Kill-switch documented and tested.
- Telemetry schema available.
- Manual review of daily generated candidates before any order automation.

## Future Risk Limits

Initial future limits should be conservative:

- Maximum 2 new episodes per day.
- One active position per symbol.
- Maximum open positions: to be approved separately.
- Maximum position value: to be approved separately.
- Maximum daily loss: to be approved separately.
- Hard kill-switch: required.
- Live trading disabled.
- Paper trading disabled until explicit authorization.

## Future Telemetry

If later authorized, telemetry should include:

- `episode_id`.
- `symbol`.
- `first_signal_date`.
- `last_signal_date`.
- `entry_decision_date`.
- Theoretical entry date and price.
- Entry eligibility reason.
- Rejection/no-trade reason.
- Bid, ask, last, spread, and timestamp if paper execution is ever authorized.
- Fill details only for authorized paper mode.
- MFE/MAE.
- Return percentage and R if a risk model is later defined.
- Exit reason.
- Gate state, kill-switch state, and environment state.

## Non-Implementation Statement

DSS-004G-A does not implement execution, broker connectivity, paper orders, live orders, preview generation, or operational signal generation.
