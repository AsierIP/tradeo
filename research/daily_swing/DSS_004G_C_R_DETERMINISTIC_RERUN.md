# DSS-004G-C-R Deterministic Rerun

Decision: `RERUN_EXIT0_MATCHES_CANON`.

Command:

```bash
/tmp/tradeo-dss-004g-c-r-venv/bin/python scripts/backtest_daily_swing_dss_004g_c.py --output-dir /tmp/dss_004g_c_r_rerun_100 --research-dir /tmp/dss_004g_c_r_rerun_100_research --bootstrap-iterations 100
```

Exit code: `0`.

Rerun setup:

- Output directory: `/tmp/dss_004g_c_r_rerun_100`.
- Research report directory: `/tmp/dss_004g_c_r_rerun_100_research`.
- Canonical artifacts were not overwritten.
- Required prior input artifacts were copied into the temporary output directory.
- Research cache remained `artifacts/runtime/daily_swing/daily_ohlcv_research`.
- Bootstrap iterations: 100.

Comparison against canonical artifacts:

| Field | Canonical | Rerun |
| --- | --- | --- |
| Decision | `DSS_CW_001_RESEARCH_FAIL_TIMING_NOT_SPECIFIC` | `DSS_CW_001_RESEARCH_FAIL_TIMING_NOT_SPECIFIC` |
| Artifact integrity | `PASS` | `PASS` |
| FDR decision | `FDR_PLACEBO_DOMINANCE_FAIL` | `FDR_PLACEBO_DOMINANCE_FAIL` |
| WRC/SPA-light decision | `WRC_SPA_PLACEBO_BEST_FAIL` | `WRC_SPA_PLACEBO_BEST_FAIL` |
| Timing decision | `TIMING_PLACEBO_DOMINANCE_FAIL` | `TIMING_PLACEBO_DOMINANCE_FAIL` |
| Best strategy | `DSS_CW_WINDOW_PLACEBO_PLUS_1` | `DSS_CW_WINDOW_PLACEBO_PLUS_1` |
| Base rank | `3` | `3` |

JSON comparison result: canonical and rerun `decision`, `artifact_integrity`, `fdr_summary`, `wrc_spa_light`, and `timing_verdict` matched after ignoring `generated_at`.

Conclusion: the deterministic cache-only rerun completed with exit `0` and matched the canonical DSS-004G-C decision. The prior exit `-1` was not reproduced.
