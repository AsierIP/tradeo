# DSS-004I Allowlist / Blocklist

Generated: 2026-07-04

## Scope

Source branch: `feature/daily-swing-paper-probe-001`.

Clean branch: `feature/daily-research-infra-clean-001`.

Base: `origin/main`.

This inventory was built from `git diff --name-only origin/main...origin/feature/daily-swing-paper-probe-001`. It classifies 374 changed paths before extraction:

- ALLOW_CODE / ALLOW_TEST / ALLOW_DOC_SANITIZED: 159 paths.
- BLOCK_*: 199 paths.
- REVIEW_MANUAL: 16 paths.

The machine-readable inventories are outside the repo:

- `/tmp/tradeo_daily_clean_extraction_allowlist.json`
- `/tmp/tradeo_daily_clean_extraction_blocklist.json`

## Included In Clean Branch

The clean branch includes reusable Daily research infrastructure only:

- `backend/tradeo/modules/daily_swing/` research modules, excluding paper-probe execution code.
- Daily focal tests for DSS-003 through DSS-004G-C, excluding paper-probe tests.
- Daily cache, quality, read-only diagnostics, cache-only backtest, and statistical audit scripts.
- Minimal sanitized DSS-004I documentation and decision artifacts under `research/daily_swing/`.
- `.gitignore` hardening for agent memory, runtime artifacts, env files, caches, logs, and local broker state.

## Excluded From Clean Branch

The clean branch intentionally excludes:

- `MEMORY.md` and `memory/`.
- `artifacts/runtime/` and all heavy generated runtime artifacts.
- OHLCV caches and raw data directories.
- Paper preview artifacts with concrete symbols, quantities, or prices.
- Audit bundles and generated reports outside sanitized research docs.
- Paper-probe scripts/config/module/test surface.
- `gh` output, PR metadata, cron changes, live/paper execution state, and broker account data.

## Manual Review Decisions

Manual-review files were resolved conservatively:

- Read-only IBKR diagnostics and historical probes were included because they do not submit orders and are useful for data readiness.
- `backend/tradeo/modules/daily_swing/paper_probe.py`, paper-probe configs, paper planning scripts, and paper-probe tests were excluded to avoid any paper-ready narrative or executable paper surface in this PR.
- Non-Markdown research CSVs from the contaminated branch were excluded unless re-expressed as sanitized DSS-004I summaries.

## Decision

ALLOWLIST_BLOCKLIST_COMPLETE
