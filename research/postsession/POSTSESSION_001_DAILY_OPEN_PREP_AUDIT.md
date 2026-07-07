# T-POSTSESSION-IMPROVEMENT-001 Daily Open Prep Audit

## Snapshot

- branch/status: `feature/daily-open-prep...origin/main [ahead 1]`
- HEAD: `713e43deb2a9048f13702f1fda6eb1c6c2a00a5c`
- commit confirmed: `713e43d Harden daily paper open prep`
- recent log:
  - `713e43d Harden daily paper open prep`
  - `c7d86a8 Merge Daily focus universe expansion`
  - `1281717 feat: focus daily universe and freeze intraday`
  - `3cc319b Merge Lab Daily resource final report`
  - `91a768f docs: record lab daily resource rollout final report`
- dirty files after `713e43d`: 9 tracked paths, 381 insertions, 42 deletions

## Dirty File Classification

| File | Classification | Probable intent | Safety impact | Order impact | Paper-readiness impact | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| `backend/tradeo/core/config.py` | `ORDER_PATH_RISK` | Add settings for auto-cancelling missing paper orders and a visibility grace period. | Sensitive because default `reconciliation_auto_cancel_missing_paper_orders=True` changes reconciliation behavior. | Can mark DB paper trades cancelled when broker has no order/position. | Potentially improves idempotency but must be reviewed. | Isolate/review before integration. |
| `backend/tradeo/services/reconciliation.py` | `ORDER_PATH_RISK` | Treat stale paper orders missing at broker as no-fill cancellations instead of divergences. | High: changes kill-switch behavior for a class of paper divergence. | Does not submit orders, but changes cancel/reconciliation state. | Could reduce false blockers, but could hide a real broker visibility issue if wrong. | Director review required. |
| `backend/tradeo/modules/shared/entry_scanner.py` | `ORDER_PATH_RISK` | Block same-bar resubmission after reconciliation auto-cancelled a paper order. | Safety-positive intent, but coupled to the sensitive reconciliation change. | Prevents duplicate paper order attempts for same bar after no-fill cancellation. | Good paper-readiness direction if reconciliation premise is approved. | Review with reconciliation patch. |
| `backend/tradeo/tests/test_execution_state_transitions.py` | `TEST_UPDATE` | Cover grace warning and stale missing paper order auto-cancel behavior. | Improves coverage. | Tests changed cancel/no-fill behavior. | Useful if the behavior is accepted. | Keep with reviewed patch only. |
| `backend/tradeo/tests/test_pattern_entry_scanner.py` | `TEST_UPDATE` | Cover duplicate-signal block after reconciliation auto-cancel. | Improves coverage. | Confirms no broker resubmit for same bar. | Useful if the behavior is accepted. | Keep with reviewed patch only. |
| `backend/tradeo/services/module_dashboard.py` | `SAFE_FIX` | Compute P/L from closed execution fills only. | Positive observability hardening. | No submit/cancel path. | Reduces misleading dashboard totals. | Safe to integrate separately. |
| `frontend/app/page.tsx` | `NEEDS_REVIEW` | Remove standalone Daily tab and relabel closed orders as fills. | Mostly UI/observability. | No order path. | Could hide Daily module visibility from dashboard; needs product review. | Isolate/review. |
| `scripts/notify_new_pattern_alerts.py` | `SAFE_FIX` | Resolve `openclaw` binary robustly for notifier. | Low. | External message only; no broker submit. | Operational reliability. | Safe if notification target remains intended. |
| `scripts/notify_tradeo_orders.sh` | `SAFE_FIX` | Resolve `openclaw` binary robustly for order notifier. | Low-to-medium because it is order telemetry notification. | Does not create orders. | Improves visibility. | Safe if target/env defaults are approved. |

## Decision

Partial decision: `DAILY_OPEN_PREP_NEEDS_REVIEW`, isolated.

The dirty tree contained a sensitive reconciliation/order-state change. It is not an immediate live-order blocker because no submit path is added and no orders were launched, but it is a merge blocker until Director review accepts or rejects the paper missing-order auto-cancel behavior.

Resolution applied after Director asked to unblock:

- saved the full dirty diff to `research/postsession/patches/POSTSESSION_001_DAILY_OPEN_PREP_DIRTY_CHANGES.patch`;
- restored the 9 dirty tracked files back to `713e43d`;
- preserved the patch for review/re-application;
- left the feature working tree free of those dirty tracked changes.

Recommended split:

- Patch A: dashboard P/L fill-only calculation and notifier binary lookup (`SAFE_FIX`).
- Patch B: reconciliation auto-cancel plus entry-scanner duplicate block and tests (`ORDER_PATH_RISK`, Director review).
- Patch C: frontend Daily tab removal/relabel (`NEEDS_REVIEW`).
