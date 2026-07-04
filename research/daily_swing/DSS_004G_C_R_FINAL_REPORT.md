# DSS-004G-C-R Final Report

Decision: `DSS_004G_C_CANONICAL_EXIT0_VALIDATED`.

## Executive Summary

DSS-004G-C-R reconciled the reported exit `-1` risk. Canonical DSS-004G-C artifacts are complete and coherent, a deterministic cache-only rerun in a temporary output directory exited `0`, and the rerun matched the canonical decision after ignoring timestamps. The original exit `-1` remains `UNKNOWN_NON_REPRODUCIBLE`, most likely outside the runner because no post-write exception or runner exit-code bug was found.

The scientific decision is unchanged: `DSS_CW_001_RESEARCH_FAIL_TIMING_NOT_SPECIFIC`.

## Results

- Artifact integrity: `ARTIFACT_INTEGRITY_PASS`.
- Exit root cause: `UNKNOWN_NON_REPRODUCIBLE`.
- Deterministic rerun: `RERUN_EXIT0_MATCHES_CANON`.
- Patch applied: none.
- Final DSS-004G-C-R decision: `DSS_004G_C_CANONICAL_EXIT0_VALIDATED`.

## Validation

- `python3 -m venv /tmp/tradeo-dss-004g-c-r-venv && /tmp/tradeo-dss-004g-c-r-venv/bin/python -m pip install -q -e 'backend[dev]'` => exit `0`.
- `python3 scripts/backtest_daily_swing_dss_004g_c.py --output-dir /tmp/dss_004g_c_r_rerun_100 --research-dir /tmp/dss_004g_c_r_rerun_100_research --bootstrap-iterations 100` with the temporary venv Python => exit `0`.
- JSON canonical-vs-rerun comparison ignoring `generated_at` => match.
- Patch not applied, so runner-specific new tests were not added.

## Safety Confirmation

No orders, no paper orders, no live orders, no paper execution, no operational preview, no operational signals, no IBKR, no downloads, no cron, no `.env` real changes, no merge, and no PR were performed.

## Recommended Next Phase

Proceed to Director decision for DSS-004H terminal closure and merge hygiene if desired. Do not open DSS-005, paper, preview, or signals from DSS-CW-001.
