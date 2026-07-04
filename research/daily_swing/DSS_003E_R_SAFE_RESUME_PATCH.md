# DSS-003E-R Safe Resume Patch

Decision: PATCH_APPLIED_AND_TESTED

Files changed:
- `backend/tradeo/modules/daily_swing/dss_003.py`
- `backend/tradeo/services/ibkr_data_provider.py`
- `scripts/cache_daily_ohlcv.py`
- `scripts/probe_ibkr_historical_readonly.py`
- `backend/tradeo/tests/test_daily_swing_dss_003.py`

New loader controls:
- `--max-new-fetches`
- `--max-consecutive-timeouts`
- `--request-timeout`
- `--retry-count`
- `--retry-backoff-seconds`
- `--quarantine-failures`
- `--continue-on-symbol-timeout`
- `--stop-on-global-timeout`

The patch keeps read-only enforcement intact and does not alter DSS-CO-001, gates, signals, paper execution, or live execution.

Validation:
- `python -m py_compile scripts/cache_daily_ohlcv.py scripts/probe_ibkr_historical_readonly.py backend/tradeo/modules/daily_swing/dss_003.py`
- `pytest -q backend/tradeo/tests/test_daily_swing_dss_003.py`: 16 passed.
- `ruff check scripts/cache_daily_ohlcv.py scripts/probe_ibkr_historical_readonly.py backend/tradeo/modules/daily_swing/dss_003.py backend/tradeo/tests/test_daily_swing_dss_003.py`: passed.
