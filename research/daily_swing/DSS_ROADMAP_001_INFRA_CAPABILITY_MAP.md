# DSS-ROADMAP-001 Infrastructure Capability Map

Task: T-DAILY-ROADMAP-001
Generated: 2026-07-05
Scope: map existing `main` capability only. No research execution was performed.

## Available Daily Surface

| Area | Present capability | Relevant files |
| --- | --- | --- |
| Universe and cache | Stock universe builder, benchmark-only SPY/QQQ separation, Daily OHLCV cache writer, resume/dry-run/timeout/quarantine controls | `backend/tradeo/modules/daily_swing/dss_003.py`, `scripts/cache_daily_ohlcv.py` |
| Data quality | Required OHLCV columns, fake holiday bar rejection, duplicate/date/NaN/OHLC validation, min operational-ready gate | `backend/tradeo/modules/daily_swing/dss_003.py`, `scripts/check_daily_ohlcv_quality.py` |
| Shared helpers | Repository root resolution, last valid trading day helper, CSV writer | `backend/tradeo/modules/daily_swing/common.py` |
| PB backtest | Pullback rule generation, stock-only universe loading, benchmark validation, OOS/IS metrics, cost stress | `backend/tradeo/modules/daily_swing/dss_004.py`, `scripts/backtest_daily_swing_dss_pb_001.py` |
| BO backtest | Trend/contraction/breakout rule, next-open/next-close entry model support, OOS/IS metrics | `backend/tradeo/modules/daily_swing/dss_004b.py`, `scripts/backtest_daily_swing_dss_bo_001.py` |
| BO autopsy | Placebo shifts, simple baseline comparison, matched-random controls, stability/timing decisions | `backend/tradeo/modules/daily_swing/dss_004c.py`, `dss_004c_a.py`, `dss_004c_r.py`, related scripts |
| CO/CW research | Contraction-only, episode/window rules, MAX2 policy, episode selection and timing checks | `backend/tradeo/modules/daily_swing/dss_004d.py`, `dss_004f.py`, `dss_004g_b.py`, related scripts |
| Stat-light audit | FDR-light, WRC/SPA-light, timing placebo dominance checks over declared families | `backend/tradeo/modules/daily_swing/dss_004g_c.py`, `scripts/backtest_daily_swing_dss_004g_c.py` |
| Diagnostics | Read-only IBKR connectivity and historical-data probes with live-port blockers | `scripts/probe_ibkr_api_session_readonly.py`, `scripts/probe_ibkr_historical_readonly.py`, `scripts/diagnose_ibkr_connectivity.py` |
| Tests | Focal tests for Daily modules/scripts and safety behavior | `backend/tradeo/tests/test_daily_swing_*.py` |

## Fit By Candidate Search-Space

| Search-space | What current infra can reuse | Missing before implementation |
| --- | --- | --- |
| Earnings / post-earnings drift | Daily cache, OOS/IS metrics, cost stress, no-lookahead checks, placebo/baseline harness patterns | Reliable earnings calendar with announcement timestamps, before/after-market flags, revision handling, symbol survivorship, and data license/provenance. |
| Gap continuation / gap reversal | Daily OHLCV already includes open/close/high/low; next-open modeling can be audited; fake holiday and OHLC gates apply | Explicit entry feasibility model for gap days, spread/slippage assumptions, open auction handling, and optional later intraday confirmation protocol. |
| Sector / relative strength | Stock-only universe, benchmark separation, Daily returns, OOS metrics, concentration checks | Point-in-time sector taxonomy, sector benchmark mapping, delisting/survivorship policy, and benchmark classification audit. |
| Market breadth + pullback | Existing pullback/regime framework, Daily cache quality, OOS/cost tooling | Point-in-time breadth series or universe-derived breadth definition, breadth timestamp policy, membership/survivorship controls, and external-data decision. |
| Daily-to-intraday hybrid entry | Daily signal discipline and existing intraday infrastructure outside this roadmap | Mixed-timeframe protocol, intraday data availability, execution model, latency assumptions, and clear boundary from Intradia context. |
| ETF/macro separate | Daily OHLCV and cost/OOS scaffolding can be adapted if policy changes to `etf_macro` | Separate universe/product policy, ETF/macro risk model, non-stock validation rules, and explicit Director decision to change system nature. |

## Capability Constraint

The clean Daily infra is strongest for stock-only, Daily-bar, cache-only research where all inputs are already point-in-time and auditable. It is weakest where the edge depends on externally timestamped event data, changing classifications, breadth membership, or intraday execution.
