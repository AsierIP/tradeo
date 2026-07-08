# LAB_AUTOMATION_001_NIGHTLY_REPORT_SPEC

`scripts/build_lab_nightly_report.py` reads `artifacts/runtime/lab_paper_probe/YYYY-MM-DD/`, updates the daily state machine, and writes:

- `research/lab_foxhunter/nightly/LAB_NIGHTLY_REPORT_YYYY-MM-DD.md`
- `research/lab_foxhunter/nightly/LAB_NIGHTLY_DECISION_YYYY-MM-DD.json`

The report consolidates per-probe trades, successes, operational errors, reconciliation errors, slippage/latency placeholders, circuit-breaker state, and 20-trade review eligibility. It never promotes to FoxHunter automatically.
