# Intraday Research Next Plan

Generated: 2026-07-03T14:38:51.868717+00:00
Decision: `change_search_space`

## Rationale
- Promising candidates were rejected by hard confirmation blockers.
- Cost stress dominates; move to higher timeframe/slower exits and require cost-aware follow-up.
- Drawdown remains excessive; longer windows or regime filters are preferred over repeating W20/W50.
- OOS weakness dominates; split by regime/time-of-day instead of broad-market repetitions.
- Multiple-testing failures remain high; run narrower families one at a time with exact-scope diagnosis.

## Safety
- paper_allowed: `False`
- live_allowed: `False`
- order_code_allowed: `False`
- relax_gates_allowed: `False`
- requires_store_rejected: `True`
- requires_exact_scope_diagnosis: `True`

## Scope Controls
- selected_count_effective: `117`
- selected_count_source: `universe_metadata`
- recommended_limit: `117`
- Do not run readiness or waves without explicit `--limit 117`.

## Recommended waves
No new waves recommended before the listed actions are completed.
## Blocked candidates
- novel_long_w100_93323dcacfe3e42aeef2: `drawdown_excessive_for_confirmation` `max_drawdown_r`=102.82831 threshold=12
- novel_long_w100_93323dcacfe3e42aeef2: `market_replay_failed` `market_replay`='failed' threshold='passed'
- novel_long_w100_93323dcacfe3e42aeef2: `market_replay_negative_expectancy` `market_replay_expectancy_r`='market replay sin expectancy positiva: -0.02R' threshold=0

## Confirmation gate
- passed: `False`
- hard_blockers: `3`

## VWAP context
- symbols_analyzed: `117`
- bars_analyzed: `89297`
- recommended_waves: ``

## Actions
- Do not confirm or shadow-review hard-blocked candidates.
- Do not paper/live; no candidate met confirmation criteria.
- Diagnose every new wave by --wave-manifest or --run-ids, never by a broad --hours scope.
- Persist rejected candidates for every wave.
- Add a follow-up cost-aware analysis: rank candidates by gross edge minus base and x2 costs.
- Plan regime splits: opening hour, final hour, gap days, high RVOL, SPY/QQQ up/down.
