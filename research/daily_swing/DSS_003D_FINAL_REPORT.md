# DSS-003D Final Report

Final decision: `PILOT_CACHE_READY_FOR_BACKTEST`

## Summary

DSS-003D expanded the Daily OHLCV cache from smoke to pilot. IB Gateway Paper 4002 stayed reachable from host and Docker, the pilot universe passed product-policy checks, the cache completed with zero failed symbols, and the pilot quality gate passed.

## Execution

- Path: `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`
- Branch: `feature/daily-swing-paper-probe-001`
- Effective IBKR path: `127.0.0.1:4002`
- Port classification: `IB_GATEWAY_PAPER`
- Read-only: `true`
- Host TCP: `TCP_OK`
- Docker TCP: `TCP_OK`

## Universe

- Operational stocks: 50
- Benchmarks: 2 (`SPY`, `QQQ`)
- SPY/QQQ: benchmark-only, not operational
- Operational ETF/ETP/fund rows: 0
- Duplicate symbols: 0

## Cache

- Status: `CACHE_WRITTEN`
- Fetched: 28
- Skipped existing: 24
- Failed: 0
- Duration: 3Y
- End date: 2026-07-06

## Quality Gate

- Data gate pilot: `PASS`
- Operational ready: 50
- Benchmark ready: 2
- Last valid bar date: 2026-07-02
- False 2026-07-03 bar present: false

## Safety

Confirmed no orders, no paper execution, no live trading, no backtest, no signals, no cron changes, no `.env` changes, no gate relaxation, no merge, and no PR.

## Artifacts

- `artifacts/runtime/daily_swing/dss_003d_preflight.json`
- `artifacts/runtime/daily_swing/dss_003d_pilot_universe_checked.csv`
- `artifacts/runtime/daily_swing/dss_003d_pilot_universe_summary.json`
- `artifacts/runtime/daily_swing/dss_003d_pilot_cache_manifest.json`
- `artifacts/runtime/daily_swing/dss_003d_pilot_quality_report.csv`
- `artifacts/runtime/daily_swing/dss_003d_pilot_quality_summary.json`
- `artifacts/runtime/daily_swing/dss_003d_decision.json`

## Next Phase

Recommended next phase: DSS-004 backtest DSS-PB-001, pending explicit Director authorization. Do not execute DSS-004 from this report alone.
