# Wave4-A - Director Review Evidence: skip_rate / Non-Trade Accounting

Date: 2026-06-11
Branch: `feat/wave4-director-skip-evidence-20260611`
Scope: gap left open by Agent J ("`skip_rate` not yet surfaced in Director
review evidence"). Evidence/reporting only — no trading behavior change, no
gate relaxed or tightened.

## Problem

Agent J made non-trade accounting real in Research and Backtest aggregates:
`RewardRiskAnalyzer.metrics_for_rr` reports `signal_count`/`skipped_count`/
`skip_rate`/`skip_reason_counts` (persisted per RR level in
`pattern.rr_metrics_json`), and `Backtester` reports `total_signals`/
`skipped_signals`/`skip_rate`. But the Director never saw it: a pattern with
strong traded expectancy could reach `DIRECTOR_REVIEW` (and the
`DirectorProductionGate` packet) while 40% of its research signals were
non-trades — lower deployable capacity, invisible in the evidence.

## Change

`backend/tradeo/services/director_review_gate.py` (additive only):

- `DirectorReviewGate._research_skip_accounting(pattern)` locates stored
  skip accounting, preferring `pattern.rr_metrics_json[best_rr]`, then other
  RR levels, then `pattern.metrics_json.rr_metrics`, then backtest-shaped
  blocks (`metrics_json.backtest` / `lab_backtest` / `backtest_summary`,
  normalizing `total_signals`/`skipped_signals` to `signal_count`/
  `skipped_count`). When nothing is stored it returns
  `{"available": false, "reason": ...}` — it never derives or invents
  numbers for runs that predate non-trade accounting.
- `lab_execution` evidence gains `research_skip_accounting` (with `source`
  provenance), `skip_rate_warning_threshold` (default 0.25),
  `research_skip_rate_warning` and an explanatory note.
- When the warning fires, `director_recommendations` gains a high-priority
  `review_research_skip_rate` entry carrying `skip_rate`/`signal_count`/
  `skipped_count`/`skip_reason_counts`.
- `DirectorProductionGate.evaluate_pattern` report includes the same
  `research_skip_accounting` block for the Director packet.
- Explicitly NOT a blocker anywhere: `promotion_blockers` and production
  `blockers` are unchanged for any input.

## Files Changed

- `backend/tradeo/services/director_review_gate.py`
- `backend/tradeo/tests/test_director_review_gate.py`
- `docs/remediation/tradeo_12_phase_compliance_matrix_2026_06_10.md`
- `docs/remediation/wave4_a_director_skip_evidence_2026_06_11.md`

## Tests Run

- New: `test_director_review_gate_surfaces_high_research_skip_rate_evidence`
  (good expectancy + 0.4 skip_rate: pattern still marked, zero blockers,
  evidence + warning + recommendation visible),
  `test_director_review_gate_reports_missing_skip_accounting_without_inventing_data`,
  `test_director_review_gate_reads_backtest_shape_skip_accounting`,
  `test_director_production_gate_report_includes_research_skip_accounting`.
- `test_director_review_gate.py`: 18 passed. Related suites
  (`test_effective_sample_weights.py`, `test_research_lab_fox_lifecycle.py`):
  7 passed. `ruff check` on touched files: clean.

## Risks

- Warning threshold (0.25) is a reporting default, not calibrated; the
  Director can tune `skip_rate_warning_threshold` per instance. No runtime
  setting added on purpose (evidence-only phase).
- Patterns discovered before Agent J's change report
  `available: false` until rediscovery refreshes `rr_metrics_json`; that is
  honest, not a regression.
- Research `skip_rate` (gap-entry policy at signal level) and lab paper
  skip semantics differ by design (Agent H); the evidence block labels its
  `source` so the Director does not conflate them.

## Next Step Recommended

Once calibrated evidence accumulates, the Director may decide whether a
hard `skip_rate` ceiling belongs in `DirectorProductionGate` — out of scope
here (would tighten the gate; needs Asier's sign-off).
