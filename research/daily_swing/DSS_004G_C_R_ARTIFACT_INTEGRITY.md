# DSS-004G-C-R Artifact Integrity Recheck

Decision: `ARTIFACT_INTEGRITY_PASS`.

Scope: rechecked the canonical DSS-004G-C artifacts written under `artifacts/runtime/daily_swing` and the canonical report under `research/daily_swing`. Inputs were read from repository artifacts only, not from chat summaries.

Artifacts checked:

| Artifact | Result |
| --- | --- |
| `research/daily_swing/DSS_004G_C_FINAL_REPORT.md` | present |
| `artifacts/runtime/daily_swing/dss_004g_c_decision.json` | present, valid JSON |
| `artifacts/runtime/daily_swing/dss_004g_c_test_matrix.csv` | present, 10 rows, closed family |
| `artifacts/runtime/daily_swing/dss_004g_c_artifact_integrity.json` | present, `status=PASS` |
| `artifacts/runtime/daily_swing/dss_004g_c_fdr_results.csv` | present, 9 statistical-family rows |
| `artifacts/runtime/daily_swing/dss_004g_c_fdr_summary.json` | present, valid JSON |
| `artifacts/runtime/daily_swing/dss_004g_c_wrc_spa_light.json` | present, valid JSON |
| `artifacts/runtime/daily_swing/dss_004g_c_timing_verdict.json` | present, valid JSON |

Canonical findings:

- Final decision: `DSS_CW_001_RESEARCH_FAIL_TIMING_NOT_SPECIFIC`.
- Artifact integrity status: `PASS`.
- Test matrix rows: 10, with 9 rows included in the statistical family and `DSS_BO_001_REFERENCE` excluded as reference-only.
- Base strategy: `DSS_CW_001_BASE_MAX2`.
- Base rank: 3.
- Best strategy: `DSS_CW_WINDOW_PLACEBO_PLUS_1`.
- Placebo dominators: `DSS_CW_WINDOW_PLACEBO_PLUS_1`, `DSS_CW_WINDOW_PLACEBO_PLUS_2`.
- FDR partial decision: `FDR_PLACEBO_DOMINANCE_FAIL`.
- WRC/SPA-light partial decision: `WRC_SPA_PLACEBO_BEST_FAIL`.
- Timing partial decision: `TIMING_PLACEBO_DOMINANCE_FAIL`.
- Critical p-values/q-values are present in `dss_004g_c_fdr_results.csv`.
- No critical NaN values were found in decision, summary, or ranking fields.
- Files are readable and not truncated.

Conclusion: the canonical DSS-004G-C artifacts are coherent and support the existing scientific decision. No artifact invalidation is required.
