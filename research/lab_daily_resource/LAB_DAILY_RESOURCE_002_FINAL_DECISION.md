# T-LAB-DAILY-RESOURCE-002 Final Decision

Decision: `LAB_DAILY_RESOURCE_PR_READY_WITH_UI_PLACEHOLDER`

## Summary

- Security default blocker closed.
- Shared fail-closed resource enforcement added.
- Fast engine/Daily scheduler planning now requires resource policy.
- Daily Setup Watchlist remains orderless metadata only.
- API remains read-only; UI remains a passive placeholder.

## Known Follow-Up

Full adoption of `assert_job_allowed` across all historical scheduler/worker entrypoints should be done as a follow-up hardening task. This branch now supplies the wrapper and tests the critical Daily/Research/Lab policy behavior.
