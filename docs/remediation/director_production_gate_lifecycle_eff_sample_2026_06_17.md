# Director Production Gate Lifecycle + Effective Sample Patch - 2026-06-17

## Summary

Audit focus: Research -> Laboratory -> Fox Hunter lifecycle and live readiness.

Practical blocker found: `DirectorProductionGate` recomputed normal IBKR paper
fills, but did not bind production approval to the lifecycle state or to the
same effective-sample concept already used by Director review. A direct
production-gate call could therefore approve a validated Lab candidate with
sufficient raw fill count and stored scientific-contract metadata, even if the
pattern had not reached `director_review` and the fill evidence was
pseudo-replicated inside a small number of symbol-day clusters.

## Patch

- Production approval now requires the pattern to be in `director_review` or
  already `production` for manifest renewal.
- Production approval now requires `validation_passed=true`.
- Production approval now computes `effective_sample_summary(fills)` and blocks
  when `effective_paper_fills < min_effective_paper_fills` (default 25).
- Production evidence packets now expose `effective_paper_fills`,
  `min_effective_paper_fills` and the auditable `effective_sample` breakdown.
- Fox Hunter production-manifest validation now rejects evidence packets that
  omit or fail the effective-fill threshold, closing the manual-manifest bypass.

## Tests

- Added DirectorProductionGate lifecycle-state coverage.
- Added DirectorProductionGate low effective-paper-fill coverage.
- Added production-manifest effective-paper-fill threshold coverage.
- Updated lifecycle/Fox fixtures so production manifests carry effective-fill
  evidence.

Verification run from `backend/`:

```bash
.venv/bin/pytest -q tradeo/tests/test_director_review_gate.py tradeo/tests/test_research_lab_fox_lifecycle.py tradeo/tests/test_pattern_entry_scanner.py
.venv/bin/pytest -q tradeo/tests/test_effective_sample_weights.py tradeo/tests/test_execution_quality_audit.py
```

Result: 78 passed, then 29 passed.

## Remaining Risk

This does not approve live. It tightens production readiness only. Live still
requires active manifest, explicit live arming, current safety checks,
reconciliation, monitoring and Asier approval.

The default production effective-fill threshold is 25, matching the current
Director effective-sample gate. Raising it to 30 would be a policy decision.
