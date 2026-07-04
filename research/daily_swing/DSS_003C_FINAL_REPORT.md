# DSS-003C Final Report

Generated: 2026-07-04 10:25 UTC.

## Executive Summary

DSS-003C unblocked the previous local connectivity issue through IB Gateway Paper on port `4002`. TWS Paper port `7497` still refused TCP, but `127.0.0.1:4002` and Docker `host.docker.internal:4002` returned `TCP_OK`. A read-only SPY historical probe succeeded and the Daily smoke cache for 10 stocks plus SPY/QQQ completed with smoke quality `PASS`.

No orders, no paper execution, no live operation, no backtest, no signals, no cron, no real `.env` edits, no gate relaxation, no merge, and no PR were performed.

## Path And Branch

- Path used: `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`.
- Branch: `feature/daily-swing-paper-probe-001`.
- Base commit before DSS-003C: `1340fc7 feat(daily): add DSS-003B IBKR connectivity diagnostics`.

## TCP Results

- Host `127.0.0.1:7497`: `TCP_REFUSED`, classified `TWS_PAPER`.
- Host `127.0.0.1:4002`: `TCP_OK`, classified `IB_GATEWAY_PAPER`.
- Docker `host.docker.internal:7497`: `TCP_REFUSED`, resolved to `172.17.0.1`.
- Docker `host.docker.internal:4002`: `TCP_OK`, resolved to `172.17.0.1`.

Effective endpoint for this run: `127.0.0.1:4002`, `IB_GATEWAY_PAPER`, read-only.

## Historical Probe

- Script: `scripts/probe_ibkr_historical_readonly.py`.
- Symbol: `SPY`.
- Period: `5D`.
- Connected: `true`.
- Historical data OK: `true`.
- Bars count: `5`.
- Orders used: `false`.
- Live used: `false`.

## Smoke Cache

- Script: `scripts/cache_daily_ohlcv.py`.
- Universe: `artifacts/runtime/daily_swing/dss_003_universe_smoke.csv`.
- Scope: 10 stocks + SPY/QQQ.
- Duration: `3Y`.
- End date: `2026-07-06`; last valid bar date checked by quality gate: `2026-07-02`.
- Status: `CACHE_WRITTEN`.
- Fetched: `12`.
- Skipped: `0`.
- Failed: `0`.

## Smoke Quality Gate

- Script: `scripts/check_daily_ohlcv_quality.py`.
- Report: `artifacts/runtime/daily_swing/dss_003c_smoke_quality_report.csv`.
- Summary: `artifacts/runtime/daily_swing/dss_003c_smoke_quality_summary.json`.
- DATA_GATE smoke: `PASS`.
- Operational ready: `10`.
- Benchmark ready: `2`.
- False 2026-07-03 holiday bar present: `false`.

This is a smoke gate only; it does not declare the global research `DATA_GATE=PASS`.

## Artifacts

- `artifacts/runtime/daily_swing/dss_003c_tcp_probe.json`.
- `artifacts/runtime/daily_swing/dss_003c_tcp_probe_127001_7497.json`.
- `artifacts/runtime/daily_swing/dss_003c_tcp_probe_127001_4002.json`.
- `artifacts/runtime/daily_swing/dss_003c_historical_probe.json`.
- `artifacts/runtime/daily_swing/dss_003c_smoke_quality_report.csv`.
- `artifacts/runtime/daily_swing/dss_003c_smoke_quality_summary.json`.
- `artifacts/runtime/daily_swing/dss_003c_decision.json`.

## Decision

`SMOKE_CACHE_OK_READY_FOR_PILOT`.

Recommended next phase: DSS-003D cache pilot, 50 stocks plus SPY/QQQ, still read-only, with no paper execution, no live, no backtest, and no signals until explicitly authorized.
