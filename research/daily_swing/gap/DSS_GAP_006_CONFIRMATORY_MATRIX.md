# DSS GAP-006 Confirmatory Matrix

Generated: 2026-07-05T16:30:00Z

## Purpose

This document pre-registers the closed GAP-007 matrix. It does not execute GAP-007 and does not promote any candidate.

## Scope

- Family: `GAP_REVERSAL_SAME_DAY` only.
- Observations: exactly the two GAP-005 observations.
- Direction: `both_signed` only.
- Total test rows: 12.
- Execution, signals, preview, paper, and live flags: all false.

## Matrix Design

Rows 1-6 preserve the two observations under reference and operable policies:

- `ALL_EVENTS_RESEARCH_ONLY` is retained only as a reference.
- `ONE_ACTIVE_PER_SYMBOL` is mandatory.
- `MAX_2_NEW_TRADES_PER_DAY` is mandatory.

Rows 7-12 define direct controls:

- `MATCHED_NON_GAP`
- `RANDOM_MATCHED`
- `SIGN_INVERTED_GAP`
- `DELAYED_ENTRY`
- `THRESHOLD_PERTURBATION`
- `EARNINGS_SENSITIVITY`

Every row carries `10bps|25bps|50bps|75bps` slippage stress and `cost_x2|cost_x3`. The 75 bps stress is terminal/descriptive; 50 bps cannot be ignored if negative.

Canonical machine-readable files:

- `dss_gap_006_confirmatory_matrix.csv`
- `dss_gap_006_confirmatory_matrix.json`
