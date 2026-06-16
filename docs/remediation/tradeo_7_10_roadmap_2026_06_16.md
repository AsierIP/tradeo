# Tradeo 7/10 Readiness Roadmap (2026-06-16)

## Goal

Raise Tradeo to at least 7/10 in Research, Laboratory, and FoxHunter readiness
without relaxing the safety model or pretending unproven edge is production
edge.

This roadmap optimizes for fastest honest path to return:

1. Keep Lab running in IBKR Paper and collecting real execution evidence.
2. Convert paper orders/fills into Director-countable evidence.
3. Close Research audit blockers that prevent scientific confidence.
4. Promote to FoxHunter only after paper evidence passes objective gates.
5. Keep Live blocked until Asier explicitly approves after the gates pass.

## Current Baseline

Recorded after reconciliation cleanup on 2026-06-16.

| Area | Score | State |
|---|---:|---|
| Research technical | 7/10 | Pipeline, Director, audit bridge, validation helpers exist. |
| Research evidence | 4/10 | Audit still blocks: missing OOS fields, replay/hash evidence gaps, duplicate/independence issues, no paper fills. |
| Laboratory | 5/10 | Scanner and paper mode exist; `auto_submit_paper_orders=true`, safety OK, but real fill loop is not producing Director-countable evidence yet. |
| FoxHunter | 2/10 | Correctly closed: no production patterns, no live approval, no production evidence. |

## Non-Negotiable Safety Gates

- `TRADEO_TRADING_MODE=paper` until final approval.
- `TRADEO_LIVE_TRADING_ENABLED=false` until final approval.
- `live_armed=false` until final approval.
- FoxHunter may be improved, but not armed.
- No pattern is production-approved from Research-only metrics.
- Paper evidence must be normal IBKR paper fills, not shadow observations or stale orders.

## 7/10 Definition

### Research 7/10

Required:

- Every exported experiment has explicit `out_of_sample_start` and
  `out_of_sample_end`, or a documented `NO_VERIFICADO` blocker.
- `event_ledger_hash`, `registry_hash`, and `registry_run_manifest_hash` are
  present for new runs.
- Nested discovery replay evidence is present or the row is capped below
  promotion.
- Duplicate event rows are below the Director gate threshold or explicitly
  explained.
- Independent sample labels are populated for new candidate rows.
- Discovery cannot create `paper_candidate`/production status without Director
  paper evidence.

Fast score target: 7/10 after new clean discovery/audit package validates these
contracts, even if no edge is proven yet.

### Laboratory 7/10

Required:

- Lab status reports:
  - `auto_submit_paper_orders=true`
  - `paper_orders_allowed=true`
  - `paper_order_safety_ok=true`
  - `runtime_kill_switch_enabled=false`
- Market-open scan with `execute_orders=true` when a valid opportunity appears.
- Paper orders are submitted only in paper mode and never via live ports.
- Filled paper trades persist as Director-countable `ibkr_paper_fill` evidence.
- Closed paper trades include entry variant, regime, commission/slippage or an
  explicit unavailable marker.
- Director review can compute by-regime and by-entry-variant buckets once enough
  fills exist.

Fast score target: 7/10 once the first market-open cycle proves real paper
orders/fills flow into the audit package correctly.

### FoxHunter 7/10

Required:

- FoxHunter remains disabled for live execution until gate pass.
- Production manifest rejects patterns without:
  - Director production approval.
  - Minimum effective paper fills.
  - Regime and entry-variant performance evidence.
  - Slippage/cost evidence.
  - Recent reconciliation-clean state.
- Dashboard/status clearly distinguishes:
  - production-ready pattern count,
  - blocked pattern count,
  - block reasons,
  - live safety state.
- Tests prove FoxHunter cannot submit live orders unless all live gates are true.

Fast score target: 7/10 as a safe production gate, not as a live-trading system.

## Execution Plan

### P0-A: Keep Lab Paper Ready

Owner: main coordinator + Lab agent.

- Done: reconciled stale AAPL DB trade.
- Done: runtime kill switch deactivated after clean reconciliation.
- Done: `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true`.
- Next: verify during regular US market hours that Lab scan uses
  `execute_orders=true`.
- Next: ensure broker submission failures surface actionable reasons, not silent
  retries.

Success metric:

- At least one clean market-open Lab scan logs `execute_orders=true`.
- No runtime kill switch.
- No live gate enabled.

### P0-B: Paper Fill Evidence

Owner: IBKR evidence agent.

- Reconcile paper positions/orders with DB before each scan cycle.
- Persist fills as `evidence_type=ibkr_paper_fill` when IBKR confirms actual
  fill, not just order submission.
- Capture fill price, commission, timestamp, order id/perm id, slippage, and
  entry signal metadata.
- Exclude shadow, near-miss, stale, or fallback rows from production evidence.

Success metric:

- Audit package has non-empty `paper_trades.csv` and `ib_fills.csv`.
- Director gate sees paper fills instead of `0`.

### P0-C: Research Audit Contract

Owner: Research evidence agent.

- Add explicit OOS/walk-forward fields to new experiment rows.
- Ensure hashes are generated for event ledger, registry, and run manifest.
- Populate independence labels and duplicate explanations.
- Keep `edge_claim=NO_DEMOSTRADO` until paper evidence exists.

Success metric:

- New audit package no longer blocks on missing OOS/hash/independence fields.
- Remaining blocks are evidence-count blocks only.

### P1-D: Lab Ranking and Closure

Owner: Lab agent.

- Ensure closed paper fills carry `entry_variant_id` and `regime_key`.
- Surface history by pattern, variant, and regime.
- Keep non-actionable opportunities as watch/shadow only.

Success metric:

- `metrics_by_entry_variant.csv` and `metrics_by_regime.csv` become populated
  once closed paper fills exist.

### P1-E: FoxHunter Gate Hardening

Owner: FoxHunter agent.

- Improve production manifest diagnostics.
- Add tests for live blocking.
- Add status clarity for why eligible pattern count is zero.

Success metric:

- FoxHunter scores 7/10 as a safe gate while still having zero live orders.

## Promotion Rules

### Research to Lab

Allowed when:

- Research contract is complete.
- Pattern is capped at Lab status.
- No lookahead/leakage blocker.

### Lab to Director Review

Allowed when:

- At least 10 normal IBKR paper fills for review trigger.
- Effective sample threshold and symbol/day diversity are progressing.
- No severe reconciliation or fill-quality issue.

### Director to Production Candidate

Allowed when:

- At least 25 effective normal paper fills.
- At least 8 symbols and 10 trading days.
- Positive paper expectancy over baseline.
- PF >= configured gate.
- Slippage/commission acceptable.
- Regime and entry-variant buckets not empty.

### Production to Live

Requires Asier approval after:

- Production gate passes.
- Reconciliation clean.
- Live safety checklist reviewed.
- Initial position size is deliberately tiny.

## Active Agent Workstreams

- Research evidence/OOS/hash blockers.
- Lab paper execution readiness.
- IBKR paper fill ingestion and reconciliation.
- FoxHunter production gate/readiness.
- Readiness scoring rubric and final audit.

## Near-Term Operating Decision

Tradeo should run in Lab Paper now, but the only valid return objective for the
next phase is information return: produce reliable paper fill evidence quickly.
Financial return from Live is not approved until the production gate passes.

