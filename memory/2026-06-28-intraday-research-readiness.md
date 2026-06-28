## 2026-06-28 - Intraday Research Readiness architecture

- User asked to continue architecture work even while IBKR/TWS is unavailable.
- Added a readiness gate to prevent invalid `0 windows` runs from being interpreted as failed experiments.
- New states: `DATA_MISSING`, `DATA_READY`, then Research evaluation.
- `backend/tradeo/services/intraday_research_readiness.py` checks exact cache coverage for universe/period/timeframe and writes an auditable manifest with hash.
- `scripts/check_intraday_research_readiness.py` provides a manual readiness check.
- `scripts/run_intraday_research_wave.py` blocks process-pool scouting unless readiness passes; with `--execute` it runs the existing process pool and writes a wave manifest.
- This work does not touch live/paper execution or validation gates.
