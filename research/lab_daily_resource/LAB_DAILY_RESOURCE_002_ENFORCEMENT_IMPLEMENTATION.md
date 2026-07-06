# T-LAB-DAILY-RESOURCE-002 Enforcement Implementation

- status: `PASS_WITH_KNOWN_FOLLOWUPS`
- implementation: `backend/tradeo/modules/resource_policy/enforcement.py`

## Implemented

- Added `assert_job_allowed(job_type, owner, session_state, policy)`.
- Added `ResourcePolicyDecision` with machine-readable allow/deny fields.
- `UNKNOWN` fails closed.
- Missing policy fails closed for Daily fast-engine scheduler planning.
- `paper_submit` and `live` are blocked by the enforcement wrapper.
- Fast engine request and Daily watchlist scheduler planning use the shared enforcement wrapper.

## Lab Paper Probe

Resource policy can prioritize or block Lab Paper Probe by market session, but it does not grant order authority. Submit remains governed by existing Lab Paper Probe, paper-mode, kill-switch, live-port and broker gates.

## Follow-Ups

- Wire `assert_job_allowed` into every concrete long-running scheduler/worker call site. The wrapper is now available and tested; not every historical runner was refactored in this hardening pass.
