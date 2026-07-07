# DAILY_FOCUS_001 Red-Team Report

Task: `T-DAILY-FOCUS-UNIVERSE-001`
Agent: E - Red-team / Integrator support
Date: 2026-07-07

## Decision

`PASS_AFTER_FIXES`

The red-team blockers found in the first pass were fixed:

- `liquid_small_cap` now rejects low-liquidity proxy rows with
  `low_liquidity_smallcap_requires_warning`.
- Legacy Lab/Daily red-team expectations were aligned with the new
  `focus_mode=daily_only` default.

## Attack Matrix

| Required attack | Result | Evidence |
| --- | --- | --- |
| Intraday heavy during `daily_only` | PASS | Intraday heavy Research, heavy backtest, scanner/capacity and Lab/Paper jobs return `INTRADAY_FROZEN_DAILY_FOCUS`. |
| Intraday Lab Paper / paper submit | PASS | `LAB_PAPER_PROBE`, intraday shadow/lab/capacity and `PAPER_SUBMIT` are frozen in daily-only; `can_submit_orders=false`. |
| Global aggregate approval | PASS | Daily Research bucket rows set `global_aggregate_allowed=false`; only `DRBM_V2_SUMMARY_ONLY` allows summary-only aggregation. |
| `entry_ready` direct order | PASS | Daily setup and Lab Probe metadata keep `orders_allowed=false`, `paper_allowed=false`, `live_allowed=false`, `submit_order_called=false`. |
| ETF mixed with stock | PASS | Daily Universe v2 only selects ETFs in `etf_macro`; stock rows in `etf_macro` and ETF rows in stock buckets are rejected. |
| Market-cap proxy treated as real | PASS | Universe v2 records absent PIT market cap as `market_cap_source=unavailable`, `market_cap_bucket_method=proxy`, `survivorship_warning=true`. |
| Low-liquidity smallcap eligible no warning | PASS | `liquid_small_cap` rows below the proxy liquidity threshold are rejected with an explicit warning reason. |
| Missing bucket | PASS | Research matrix validation fails missing buckets; Universe v2 reports `missing_required_buckets`. |
| Daily/Lab/FoxHunter metrics mixed | PASS | Daily records contain Lab route metadata only and no FoxHunter/intraday metric surface in attacked payloads. |
| Live/paper submit appears | PASS | No live/paper order fields, candidate approval, or submit flags are enabled in Daily Focus payloads. |
| Runtime artifact tracked | PASS | `git ls-files` shows no tracked `artifacts/runtime` paths. |

## Tests Run

- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_daily_swing_universe_v2.py backend/tradeo/tests/test_daily_research_bucket_matrix.py backend/tradeo/tests/test_daily_focus_001_red_team.py backend/tradeo/tests/test_lab_daily_resource_004_red_team.py -q` -> passed.

## Residual Risk

The universe is still proxy-based because no verified point-in-time market-cap source is wired. That is disclosed in Universe v2 artifacts and blocks treating bucket labels as historical market-cap truth.
