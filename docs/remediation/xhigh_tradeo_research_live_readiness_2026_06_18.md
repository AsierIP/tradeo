# xHigh Tradeo Research/live readiness coordination - 2026-06-18

Scope: five xHigh audit fronts plus Solaris integration on Research, pattern search,
post-trade EV, statistical efficacy and live readiness.

## Agent fronts

- Front A, architecture/logical flow: no clear live bypass through Research -> Lab -> Fox,
  but current Director audit evidence remains blocked for live and skip accounting was
  inconsistent in OOS/quant paths.
- Front B, speed/search: largest safe wins are matcher DB batching, compound indexes,
  precompiled pattern artifacts and outcome caching. These are next wave because they
  change hot paths and need golden/perf tests.
- Front C, EV/post-trade: highest remaining risk is partial-fill accounting by requested
  quantity instead of executed quantity. This needs reconciliation/export work as a
  separate focused patch. The lower-risk ranking issue was fixed here.
- Front D, statistics/overfitting: no P0 live bypass found; key risks are data-quality
  fail-closed, nested replay, stronger OOS gates, trial accounting and false-match gates.
- Front E, live readiness: manual IBKR live submit could bypass Fox production manifest
  checks. This was fixed here as a hard safety gate.

## Changes integrated

1. Director bucket metrics now rank entry variants and regimes by execution-adjusted net R
   when real cost coverage is present. Gross expectancy is still reported separately.
   Reason: post-trade learning should not prefer a variant that looks profitable before
   commission but loses after executable costs.

2. Research split/quant validation now excludes skipped gap-entry non-trades from traded
   EV arrays instead of counting them as `0R`. It also reports `signal_count`,
   `skipped_count` and `skip_rate`.
   Reason: a non-trade is coverage information, not a flat trade. Counting it as zero
   distorts expectancy, win rate, effective sample and walk-forward/quant evidence.

3. IBKR live submit now requires:
   - `live_approved` signal status;
   - explicit `TRADEO_IBKR_ACCOUNT`;
   - non-empty `TRADEO_IBKR_ALLOWED_SYMBOLS`;
   - Fox Hunter production signal metadata;
   - existing discovered pattern with `production` status;
   - active production manifest.
   Reason: manual live submission must not route Lab, legacy scanner or paper-approved
   signals around DirectorProductionGate/Fox manifest controls.

## Remaining blockers before real live

- Partial fill accounting must be normalized around executed quantity and fill-atomic
  evidence before live EV can be trusted.
- A central `LiveReadinessGate` should combine manifest, account, allowlist, readonly,
  kill switch, worker freshness and reconciliation freshness.
- Research acceptance should move data quality, nested replay, OOS/purged-CV, trial
  accounting and false-match FPR from advisory diagnostics toward hard gates by state.
- Matcher/storage speed work should be done with golden output and query-count tests.

## Verification

- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_execution_state_transitions.py backend/tradeo/tests/test_reward_risk_analyzer.py backend/tradeo/tests/test_director_review_gate.py backend/tradeo/tests/test_execution_quality_audit.py -q`
  -> 115 passed.

