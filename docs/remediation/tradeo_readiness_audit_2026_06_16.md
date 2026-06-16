# Tradeo Readiness Audit And Roadmap Validation (2026-06-16)

## Scope

Objective: define honest 7/10 gates for Research, Laboratory and FoxHunter so
Asier can run paper as soon as possible without confusing research signal,
paper evidence and live readiness.

Sources reviewed:

- Latest audit bridge packages through
  `TRADEO-AUDIT-20260615-213559_daily_internal`.
- Runtime API/DB snapshot on 2026-06-16 06:35 UTC.
- Module boundary docs, audit contract, remediation docs and current scanner /
  Director gate code.
- Existing untracked roadmap:
  `docs/remediation/tradeo_7_10_roadmap_2026_06_16.md`.

No live-trading setting was changed.

## Score Semantics

Scores measure readiness, not optimism.

- 0: absent or unknown.
- 1-2: scaffold only, unsafe or misleading if used.
- 3-4: major gate exists, but evidence is missing or blockers are active.
- 5: functional internal workflow, not promotable.
- 6: safe to run in the next lower-risk environment, but key evidence loop is
  still unproven.
- 7: objectively usable for its intended boundary with no hard blockers.
- 8: repeatable with enough evidence diversity and regression coverage.
- 9: production/live pilot ready with tiny sizing and explicit human approval.
- 10: mature, monitored, statistically and operationally robust.

For this project, 7/10 never means "edge proven enough for live" unless the
module is specifically scoring live readiness after Director production gates.

## Current Scores

| Module | Current score | Why |
|---|---:|---|
| Research | 5/10 | The technical pipeline, audit bridge and Director blockers exist, but the latest package is still Director-blocked by missing OOS boundaries, missing hashes, duplicate/independence failures, no nested replay pass and no paper evidence. |
| Laboratory | 6/10 | Runtime is paper-safe and IBKR Paper connects; Lab auto-submit paper is enabled and worker is healthy. It is still below 7 because there are zero Director-countable `ibkr_paper_fill` rows and the last observed status was market closed. |
| FoxHunter | 4/10 | Live is safely blocked and local code has production-manifest gates, but there are zero `production` patterns, zero active manifests, zero production evidence and the deployed container should be rechecked after rebuild for latest readiness fields. |

## Evidence Snapshot

Latest Director gate package:

- `status=blocked`.
- 500 patterns, 5849 events, 2995 experiment rows.
- 0 `paper_trades`, 0 `ib_fills`.
- 3 promoted-status offenders: `PATTERN_000282`, `PATTERN_000364`,
  `PATTERN_000366`.
- Duplicate repeated event share: 432/5849 rows, 7.39%.
- 500 event rows are not verified independent samples.
- 2995 experiments lack explicit `out_of_sample_start/out_of_sample_end`.
- 2953 experiment rows lack `event_ledger_hash`.
- 2965 experiment rows lack `nested_discovery_replay` evidence.
- 2965 experiment rows lack `registry_hash`.
- 2965 experiment rows lack `registry_run_manifest_hash`.

Runtime/DB snapshot:

- Docker: backend, worker, db, redis and frontend are up.
- `/api/health`: `mode=paper`, `live_armed=false`,
  `kill_switch_enabled=false`.
- `/api/health/deep`: watchdog OK, no stale discovery runs.
- `/api/health/ibkr`: IBKR Paper reachable on port `14002`,
  `readonly=false`, `trading_mode=paper`, `live_armed=false`.
- Lab status: `auto_submit_paper_orders=true`,
  `paper_orders_allowed=true`, `paper_order_safety_ok=true`,
  `runtime_kill_switch_enabled=false`, worker OK, market closed.
- DB: 32 Lab-eligible validated patterns plus 3 legacy `paper_candidate`
  patterns that remain runtime-blocked from promotion evidence.
- DB: 135 `paper_approved` signals and 7 `executed` signals, but no normal
  closed `ibkr_paper_fill` trades.
- Trades: 3 open, 6 cancelled; no Director-countable paper fills.
- FoxHunter status: `auto_submit_live_orders=false`,
  `live_orders_allowed=false`, `production_status_patterns=0`,
  `eligible_patterns=0`.

## 7/10 Gates

### Research 7/10

Research reaches 7/10 when a new audit package is scientifically clean enough
to feed Lab/watchlist without promotion language.

Required evidence:

- Audit package validates and Director gate has no methodology blockers.
- All new experiment rows include explicit OOS boundaries, event ledger hash,
  registry hash and registry run manifest hash.
- Nested discovery replay is present and passed, or failing rows are explicitly
  capped below promotion.
- `edge_claim=NO_DEMOSTRADO` is present until broker paper fills prove an edge.
- Anti-lookahead contract fields are non-blank.
- Exported event rows are deduplicated or have Director-accepted duplicate
  grouping; current deterministic gate defaults to zero repeated
  `duplicate_group_id` rows.
- Independent sample labels are populated and reconstructable from exported
  events.
- Research states cannot imply paper/live readiness without linked paper/fill
  evidence.

Allowed after Research 7/10:

- Feed candidates into Lab as `lab`, `lab_watchlist` or `lab_candidate`.
- Rank hypotheses for paper observation.
- Keep edge language explicitly unproven.

Still blocked:

- `paper_candidate`, `production`, FoxHunter and live.

Fastest unblockers:

- Regenerate a clean discovery/audit package with OOS/hash/replay/independence
  fields filled.
- Demote or freeze the 3 promoted-status offenders until paper evidence exists.
- Keep duplicate rows at gate-compliant zero, or change the gate only through a
  documented Director decision.

### Laboratory 7/10

Lab reaches 7/10 when it proves the paper execution loop produces
Director-countable evidence.

Required evidence:

- Market-open scan runs with `execute_orders=true`.
- Runtime safety remains: `trading_mode=paper`, `live_armed=false`, no env or
  runtime kill switch, no live IBKR port.
- IBKR Paper bracket submissions create order records with actionable failure
  reasons if they fail.
- Actual broker fills are ingested as closed normal `ibkr_paper_fill` evidence,
  not shadow, near-miss or stale-order rows.
- Each fill carries fill id/hash, broker execution timestamp, commission/fees,
  entry variant, regime key, signal metadata and slippage/cost data or explicit
  unavailable markers.
- Audit export populates non-empty `paper_trades.csv` and `ib_fills.csv` when
  fills exist.
- Director can compute by-regime and by-entry-variant buckets after enough
  closed normal fills.

Allowed after Lab 7/10:

- Continue IBKR Paper operation to gather evidence.
- Trigger Director review once at least 10 closed normal paper fills exist for a
  pattern.

Still blocked:

- Production and live. DirectorProductionGate still requires stronger evidence:
  30 paper fills, symbol/day diversity, scientific contracts, execution
  provenance and positive net paper performance.

Fastest unblockers:

- Run Lab during regular US market hours and verify `orders_submitted > 0` or
  precise order failure reasons.
- Add/fix reconciliation that converts accepted IBKR paper executions into
  strong fill evidence with commission and execution timestamps.
- Export a new audit package immediately after the first real paper fill closes.

### FoxHunter 7/10

FoxHunter reaches 7/10 as a safe production gate, not as permission to trade
live.

Required evidence:

- FoxHunter scans only `production` patterns.
- Every `production` pattern requires an active canonical production manifest.
- Manifest must include Director approval, canonical hash, unexpired version and
  evidence packet reference/hash.
- DirectorProductionGate must pass before any manifest is considered valid.
- Status/API clearly reports production patterns, eligible manifests, blocked
  manifests and block reasons.
- Tests prove FoxHunter cannot create live orders unless live gates are true.
- Runtime image must expose the same readiness fields as local code/tests after
  rebuild/redeploy.

Allowed after FoxHunter 7/10:

- Keep FoxHunter running in blocked/monitoring mode.
- Prepare production-manifest review packets for Asier.

Still blocked:

- Live execution unless all production gates pass and Asier explicitly approves
  live arming and tiny initial sizing.

Fastest unblockers:

- Run targeted FoxHunter gate tests after the current dirty test/code changes
  settle.
- Rebuild/redeploy and recheck `/api/fox-hunter/status`.
- Do not create any production manifest until Lab paper evidence passes
  DirectorProductionGate.

## Paper Vs Live Decision Rules

Paper is allowed now for Lab if the market is open and current safety snapshot
stays true:

- `TRADEO_TRADING_MODE=paper`.
- `TRADEO_LIVE_TRADING_ENABLED=false`.
- `live_armed=false`.
- `kill_switch_enabled=false`.
- runtime kill switch false.
- IBKR port is paper, not 7496/4001.
- Lab scanner enabled and worker fresh.

Paper is still not allowed to support promotion unless the fills become strong
Director evidence.

Live remains blocked until all of these are true:

- Pattern has passed DirectorProductionGate.
- Production manifest is active and hash-verified.
- Reconciliation is clean immediately before arming.
- Live safety checklist is reviewed.
- Asier explicitly approves `live_armed`, live mode and tiny initial sizing.
- Monitoring, kill switch and post-trade reconciliation are active.

## Measuring Return Without Fooling Ourselves

Use two separate returns.

Information return:

- Did a paper cycle reduce uncertainty about a pattern, variant or regime?
- Count every generated opportunity, rejected opportunity, shadow observation,
  submitted order, cancelled order, fill and non-fill.
- Track denominator leakage: fills alone are not the sample; all eligible
  signals are the funnel.

Financial return:

- Only use closed normal broker paper fills for paper PnL claims.
- Compute net R after commission, spread/slippage and other fees.
- Report expectancy, median R, PF, drawdown, win rate, payoff ratio and
  confidence/sequential evidence.
- Segment by pattern, entry variant, regime, symbol and trading day.
- Compare against baseline: no-trade, default variant and random/holdout entry
  where available.
- Do not annualize or promote from small N.
- Exclude shadow/near-miss/stale/cancelled orders from fill PnL, but keep them
  in funnel diagnostics.
- Pre-register thresholds before looking at the next batch.

Minimum honest batch report:

- all opportunities seen;
- orders attempted;
- order failures by reason;
- submitted paper orders;
- filled paper orders;
- closed normal paper fills;
- net R distribution;
- cost/slippage distribution;
- bucket performance by entry variant and regime;
- decisions made before the next batch.

## Roadmap Validation

The existing 7/10 roadmap has the right direction:

- run Lab Paper now;
- convert paper orders/fills into Director-countable evidence;
- keep live blocked;
- treat Research metrics as hypothesis evidence only.

Corrections:

- Research should not be called 7/10 overall while the latest Director gate has
  active scientific blockers. Split it into technical capability (~7) and
  current evidence readiness (~4); overall current readiness is 5.
- Lab is closer than Research to its practical next step, but no
  Director-countable fills means it is not yet 7.
- FoxHunter can be scored as a safety gate, not as a trading system. With zero
  production patterns and zero manifests, current trading readiness remains 4.
- The deployed runtime should be checked after rebuild because local code/tests
  include extra Fox readiness fields that were not all visible in the runtime
  JSON captured during this audit.

## Roadmap Gaps

P0:

- Close Research scientific blockers in the next audit export.
- Demote/freeze promoted-status offenders until paper fills exist.
- Run Lab during market hours and verify paper order submission/failure path.
- Ingest actual IBKR Paper fills as strong `ibkr_paper_fill` evidence.
- Re-export audit package after the first real paper fill closes.

P1:

- Make fill funnel reporting first-class: opportunities -> attempts -> orders
  -> fills -> closed trades.
- Rebuild/redeploy and confirm status API matches local readiness fields.
- Run targeted FoxHunter/Director/entry-scanner test subset.
- Add a compact daily readiness report generated from API/DB and latest audit
  package.

P2:

- Add PIT/delisting data source before claiming robust small-cap universe
  validity.
- Add richer real-time microstructure feed if available.
- Calibrate hard regime/DTW/SPA gates only after enough paper evidence exists.

## Final Rubric

| Module | 0-10 current | 7/10 pass condition | Current blocker |
|---|---:|---|---|
| Research | 5 | Clean Director package with OOS/hash/replay/independence/anti-lookahead complete and no promotion language without fills. | Latest package is scientifically blocked. |
| Laboratory | 6 | Market-open paper loop produces strong broker fill evidence that appears in audit exports. | No Director-countable paper fills yet. |
| FoxHunter | 4 | Production-only scanner plus manifest/live gates tested and visible in deployed status; still no live without approval. | Zero production patterns/manifests; live intentionally blocked. |
