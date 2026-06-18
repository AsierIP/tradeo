# LiveReadinessGate hardening - 2026-06-18

Scope: centralize live eligibility so health, Fox status and IBKR live submit all
answer from one fail-closed gate.

## Changes

- Added `LiveReadinessGate` as the single live-order decision service.
- `/health/deep` now exposes the full readiness packet.
- Fox Hunter status now uses the central gate for `live_orders_allowed`,
  `execution_block_reason`, reconciliation freshness and check details.
- IBKR live submit now rejects when `LiveReadinessGate` blocks, before any broker
  connection or order construction.

## Hard Gates

- Env kill switch off.
- Runtime kill switch off.
- `live_armed=true`.
- `TRADEO_TRADING_MODE=live`.
- `TRADEO_IBKR_READONLY=false`.
- IBKR live port only: 7496 or 4001.
- Explicit `TRADEO_IBKR_ACCOUNT`.
- Non-empty `TRADEO_IBKR_ALLOWED_SYMBOLS`.
- Fresh worker heartbeat.
- Recent clean reconciliation audit: zero divergences, warnings and exit-protection
  errors.
- At least one production pattern with active Director production manifest.

## Why

Before this, readiness was partly duplicated across scanner status and broker
guards. That made false-positive UI readiness possible and made manual submit
depend on a different set of checks than Fox. Live readiness now fails closed
with concrete reason codes and can be monitored from health, scanner state and
submit errors.

## Verification

- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_live_readiness_gate.py -q`
- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_pattern_entry_scanner.py backend/tradeo/tests/test_execution_state_transitions.py -q`

