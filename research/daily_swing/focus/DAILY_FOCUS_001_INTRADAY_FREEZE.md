# DAILY FOCUS 001 Intraday Freeze

Status: PASS
Date: 2026-07-07

## Policy

`TRADEO_FOCUS_MODE` now defaults to `daily_only` through `Settings.focus_mode`.
The compatible non-freeze mode is `all`; aliases `daily`, `full`, and
`unrestricted` normalize to the supported values.

Daily-only mode denies intraday heavy research, lab, paper, shadow, scanner, and
capacity work with the exact deny reason:

`INTRADAY_FROZEN_DAILY_FOCUS`

## Frozen Job Types

- `research_heavy`
- `heavy_backtest`
- `large_scanner`
- `lab_execution`
- `lab_readiness`
- `lab_paper_probe`
- `paper_submit`
- `intraday_lab`
- `intraday_shadow`
- `intraday_capacity`

## Allowed During Freeze

- Read-only policy/status checks: `resource_policy.evaluate`, `market_session.status`
- Cache inspection: `local_cache.read`
- Read-only report/artifact output: `report.write`, `artifact.write`
- Maintenance job metadata: `intraday_read_only_report`, `intraday_maintenance_test`, `intraday_cache_inspection`
- Daily/report workflow jobs: `daily_watchlist_reeval`, `daily_watchlist_prep`, `nightly_report`

## Validation

- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_resource_policy_enforcement.py backend/tradeo/tests/test_market_session_resource_policy.py backend/tradeo/tests/test_resource_policy_market_session.py backend/tradeo/tests/test_daily_focus_001_red_team.py backend/tradeo/tests/test_fast_chart_engine_registry.py backend/tradeo/tests/test_lab_daily_resource_004_red_team.py`
  - Result: 57 passed, 1 existing FastAPI/Starlette deprecation warning
- `backend/.venv/bin/python -m ruff check backend/tradeo/core/config.py backend/tradeo/modules/resource_policy backend/tradeo/routers/resource_policy.py backend/tradeo/tests/test_resource_policy_enforcement.py backend/tradeo/tests/test_market_session_resource_policy.py backend/tradeo/tests/test_resource_policy_market_session.py backend/tradeo/tests/test_fast_chart_engine_registry.py backend/tradeo/tests/test_lab_daily_resource_004_red_team.py backend/tradeo/tests/test_daily_focus_001_red_team.py`
  - Result: all checks passed

No live orders, paper orders, `.env` edits, or timer changes were made.
