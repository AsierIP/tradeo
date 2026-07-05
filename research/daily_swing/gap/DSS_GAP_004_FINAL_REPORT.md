# DSS-GAP-004 Final Report

## A. Executive Summary

GAP-004 completed as a cache-only research dry-run. The GAP-003 matrix was executed over the local GAP-002A ledger, runtime results were generated locally, sanitized summaries were versioned, and no candidate was approved.

Final decision: GAP_DRY_RUN_COMPLETE_NO_CANDIDATE_APPROVAL.

## B. Real Path Used

`/tmp/tradeo-main-004k-clean`

## C. Branch

Branch: `feature/daily-gap-protocol-001`

Commit/push status is recorded in the chat report after validation and push.

## D. Input / Matrix Gate

INPUT_MATRIX_GATE_PASS:
- Ledger runtime exists: `artifacts/runtime/daily_swing/gap/dss_gap_002_event_ledger.csv`.
- Ledger rows: 114304.
- Ledger range: 2023-07-05 through 2026-07-02.
- Matrix rows: 92.
- Candidate rows: 40.
- Baseline rows: 8.
- Placebo rows: 16.
- Security flags are all false.

## E. Dry-run Execution

Executed 92 test_ids across:
- GAP_CONTINUATION_SAME_DAY
- GAP_REVERSAL_SAME_DAY
- GAP_CONTINUATION_NEXT_DAY
- GAP_REVERSAL_NEXT_DAY

Policies:
- ALL_EVENTS_RESEARCH_ONLY
- MAX_2_NEW_TRADES_PER_DAY
- ONE_ACTIVE_PER_SYMBOL

Runtime outputs:
- `artifacts/runtime/daily_swing/gap/dss_gap_004_results_by_test.csv`
- `artifacts/runtime/daily_swing/gap/dss_gap_004_results_by_policy.csv`
- `artifacts/runtime/daily_swing/gap/dss_gap_004_results_by_family.csv`
- `artifacts/runtime/daily_swing/gap/dss_gap_004_dry_run_summary.json`

## F. No-lookahead / Open Realism Audit

GAP_DRY_RUN_NO_LOOKAHEAD_PASS:
- Same-day selection excludes close/high/low/outcome fields.
- Same-day return is open_t to close_t after selection.
- Next-day selection is after close_t with entry at open_t+1.
- Open adverse slippage stress is applied at 10/25/50 bps.

## G. Results Summary

Sanitized outputs:
- `research/daily_swing/gap/dss_gap_004_results_summary_by_family.csv`
- `research/daily_swing/gap/dss_gap_004_results_summary_by_policy.csv`
- `research/daily_swing/gap/dss_gap_004_results_summary_top_observations.csv`

No candidate approval, no best threshold selection, and no paper/shadow/live readiness claim.

## H. Baselines / Placebos

Executed controls include MATCHED_NON_GAP, RANDOM_MATCHED, SIGN_INVERTED_GAP, DELAYED_ENTRY, THRESHOLD_PERTURBATION, and EARNINGS_SENSITIVITY. They are used only for comparison and warnings.

## I. Tests / Validations

Commands:
- `python3 -m py_compile scripts/run_daily_gap_matrix_dry_run.py backend/tradeo/modules/daily_swing/gap_matrix_dry_run.py backend/tradeo/tests/test_daily_gap_matrix_dry_run.py` -> exit 0.
- `python3 scripts/validate_daily_gap_backtest_matrix.py --matrix-json research/daily_swing/gap/dss_gap_003_backtest_matrix.json` -> exit 0.
- `/tmp/tradeo-gap004-venv/bin/python -m pytest backend/tradeo/tests/test_daily_gap_backtest_matrix.py backend/tradeo/tests/test_daily_gap_matrix_dry_run.py` -> 20 passed, exit 0.
- `/tmp/tradeo-gap004-venv/bin/ruff check --no-cache backend/tradeo/modules/daily_swing/__init__.py backend/tradeo/modules/daily_swing/gap_matrix_dry_run.py scripts/run_daily_gap_matrix_dry_run.py backend/tradeo/tests/test_daily_gap_matrix_dry_run.py` -> all checks passed, exit 0.
- `git diff --check` -> exit 0.

## J. Docker Build Status

Space checks before build:
- `df -h` showed `/dev/sda2` at 99% with 2.9G available.
- `docker system df` showed 14.62GB build cache and 5.452GB reclaimable.

Build:
- First context attempt with `docker build -f backend/Dockerfile -t tradeo-backend:gap004 backend` failed because the Dockerfile expects repository-root context.
- Correct repository-root build `docker build -f backend/Dockerfile -t tradeo-backend:gap004 .` completed successfully, exit 0.

## K. Decision

GAP_DRY_RUN_COMPLETE_NO_CANDIDATE_APPROVAL.

## L. Safety Confirmation

Confirmed:
- no orders;
- no paper;
- no live;
- no preview;
- no signals;
- no IBKR;
- no downloads;
- no cron;
- no `.env` real modified;
- no `gh`;
- no main push.

## M. Next Task Recommendation

T-DAILY-GAP-005 - Gap dry-run forensic review and candidate triage, no paper. Do not execute it in this task.
