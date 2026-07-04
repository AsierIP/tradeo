# DSS-004G-C-R Exit Root Cause

Decision: `UNKNOWN_NON_REPRODUCIBLE`.

Observed issue from Director context: one long DSS-004G-C cache-only process reportedly returned exit `-1` after writing artifacts. The canonical JSON/CSV/report artifacts were present and coherent after that run.

Checks performed:

- Reviewed `scripts/backtest_daily_swing_dss_004g_c.py`.
- Reviewed `backend/tradeo/modules/daily_swing/dss_004g_c.py`.
- Reviewed the final write path for CSV, JSON, and Markdown artifacts.
- Searched available workspace and OpenClaw logs for DSS-004G-C stderr/stdout, timeout, kill, filesystem-full, and exit `-1` evidence.
- Checked filesystem space before rerun: `/` had 18G available; `/tmp` had 9.8G available.

Root-cause classification:

- `WRAPPER_TIMEOUT`: not proven. No original wrapper log was found.
- `DOCKER_KILL_OR_RESOURCE`: not proven. No kill/OOM evidence was found.
- `FILESYSTEM_FULL`: not reproduced. Current disk state has available space.
- `POST_WRITE_EXCEPTION`: not reproduced. The script completed cleanly after final writes.
- `RUNNER_EXIT_CODE_BUG`: not found. The CLI returns `0` after `run_dss_004g_c` completes and prints the decision.
- `TEST_ENVIRONMENT_ISSUE`: possible but not proven; direct host Python lacked pandas, so validation used a temporary `/tmp` venv.
- `UNKNOWN_NON_REPRODUCIBLE`: selected.

Important implementation detail: `scripts/backtest_daily_swing_dss_004g_c.py` has no special nonzero exit branch after successful `run_dss_004g_c`; it returns `0`. If the previous exit `-1` happened after artifact writes, the most likely unresolved causes are an external wrapper/session termination or a transient environment/resource event outside the runner.

No patch was applied because the issue did not reproduce and no code-level exit bug was identified.
