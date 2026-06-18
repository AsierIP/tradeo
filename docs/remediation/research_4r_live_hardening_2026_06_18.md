# Research 4R Live Hardening - 2026-06-18

## Consensus

Five xhigh review agents inspected Research/Lab/Live readiness from separate
angles: architecture, throughput, EV/R:R, statistical validation, and live
handoff. The shared conclusion was:

- there is no obvious direct Research-to-Live bypass;
- live submit remains protected by production state, manifest, readiness and
  broker preflights;
- the weak point was upstream: Research/Lab could still accept, rank or count
  evidence below the required 1:4 reward:risk standard.

For live preparation, 4R must be an operational invariant, not a premium label.

## Implemented Now

- Raised Research reward:risk defaults to 4R:
  `discovery_min_reward_risk=4.0` and
  `discovery_candidate_reward_risk=4.0`.
- Synced `.env.example` so new environments start with min/preferred 4R.
- Made `RewardRiskAnalyzer.best_rr` selectable only from levels >= 4R. Lower
  R:R metrics remain available for diagnostics, but cannot become the operative
  best R:R.
- Hardened `ValidationGate` so missing or weak 4R runtime evidence is a
  rejection reason, not a warning.
- Hardened `NovelPatternMatcher` so any persisted pattern with `best_rr < 4R`
  is skipped at runtime and counted in `reward_risk_gate_blocked`.
- Hardened `DirectorReviewGate` so paper fills below 4R do not count as
  promotion evidence.
- Added regression tests for sub-4R rejection in Research, matcher, Director
  evidence, and reward:risk selection.

## Why

The previous behavior allowed a pattern with attractive 2.5R/3R metrics to look
good in Research and enter Lab prioritization while not proving the strategy
edge at the user's required 1:4 standard. That contaminates dashboards,
ranking, paper evidence and Director review.

The new contract is:

- sub-4R can be observed;
- sub-4R cannot be selected as the operational best R:R;
- sub-4R cannot pass Research validation;
- sub-4R cannot produce Lab matches;
- sub-4R paper fills cannot count as Director evidence.

## Still Not Live-Ready

The agents agreed that live should remain off until these larger scientific and
execution blockers are handled:

- nested discovery replay is still a production blocker;
- effective sample, OOS, walk-forward and purged-CV absence should become
  fail-closed for any executable state;
- Research should apply OHLCV data-quality gates before window sampling;
- point-in-time/delisting-aware universe bias is still unresolved;
- Lab warnings for liquidity/ATR/execution quality should become observation
  only, not paper evidence;
- RiskManager should sync broker equity, positions, open orders and realized PnL
  before any live sizing.

## Verification

Focused tests were run against the changed Research, matcher, Director and live
preflight surfaces. See the commit message and test output for exact command
coverage.
