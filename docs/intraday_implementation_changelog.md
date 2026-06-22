# Intraday Implementation Changelog

## 2026-06-22 - Audit integration remainder

- Extended `scripts/build_intraday_audit_pack.py` to emit schema version 2 with git branch, commit, short commit, dirty flag and status counts without listing local file names.
- Added an executable test manifest to the audit pack:
  - `python3 scripts/build_intraday_audit_pack.py --dry-run`
  - `make test-safety`
  - targeted intraday pytest files discovered from `backend/tradeo/tests/test_intraday*.py` plus `test_ibkr_pacing.py`.
- Added a static AST summary for the intraday package and integration points:
  - candidate building, data sync, Director promotion gates, paper execution, features, EOD flat service, lab observation, reports, risk, universe selection, calendar and API router.
- Hardened the audit pack against secret leakage by documenting excluded runtime sources, avoiding raw status path output, and failing generation if sensitive keys are not redacted or known credential patterns appear in emitted values.

## 2026-06-22 - Intraday data lab

- `0f89995 feat(intraday): add data sync and lab`
- Added closed-bar data validation/manifests and shadow lab observation metrics for intraday evidence.

## 2026-06-22 - Intraday API and paper execution

- `f5445a6 feat(intraday): add safe API surface`
- Added admin-only status, pacing, flat-preview/request endpoints and paper execution eligibility/metrics without broker-backed live execution.

## 2026-06-22 - Intraday session controls

- `99fff45 feat(intraday): add session controls`
- Added session-scoped risk gates, Director promotion thresholds, EOD flat state handling and audit report primitives.

## 2026-06-22 - Intraday candidate runtime

- `2e49e2a feat(intraday): add candidate runtime`
- Added session-aware candidate normalization, expiry, exposure de-duplication and reason-code metadata.

## 2026-06-22 - Intraday safety foundation

- `ea1ee86 feat(intraday): add safety foundation`
- Added default-off intraday settings, no-regression tests, schema support and calendar/pacing safety checks.
