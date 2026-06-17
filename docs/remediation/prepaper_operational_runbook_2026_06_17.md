# PrePaper Operational Readiness Runbook (2026-06-17)

## Decision

Live remains blocked. The next operating mode is measured Lab/IBKR Paper only.

This runbook turns the 2026-06-17 preLive audit into a release checklist for
the next seven calendar days. It must not be used to claim live readiness,
profitability, or production approval. Its purpose is to gather reproducible
paper evidence and keep every blocker visible.

## Baseline Evidence Package

Canonical package:

```text
research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal
```

Manifest facts:

- `created_at=2026-06-16T23:36:43+02:00`.
- `repo_commit=3c4ba8ed46c32899f5caf1021f56cd2813b5af72`.
- `data_source=Interactive Brokers Paper`.
- `patterns_detected=500`.
- `total_pattern_events=5619`.
- `total_experiment_variants=2995`.
- `total_paper_trades=0`.
- `total_ib_fills=0`.
- `duplicate_repeated_rows=125`.
- `file_hashes.sha256` hash:
  `b897d400b32697740c1de4311d367812cb9228e577399aeb401d4f0b73327711`.

Validation status recorded on 2026-06-17:

- Package schema: OK.
- Package file hashes: OK.
- Director gate: `blocked`.
- Promotion allowed: `false`.

Known Director blockers from the package:

- `paper_trades.csv` has zero rows.
- `ib_fills.csv` has zero rows.
- Promoted-status offenders without linked paper trades:
  `PATTERN_000282`, `PATTERN_000364`, `PATTERN_000366`.
- 271 event rows have blank anti-lookahead contract values.
- 125/5619 event rows repeat `duplicate_group_id`.
- 2995 experiment rows have nested discovery replay not implemented/passed.
- Experiment rows still report active blockers.

## Reproducibility Commands

Use these commands from the repository root. They verify the package without
creating fills, trades, or live-readiness claims.

```bash
python3 research/audit_bridge/validate_audit_package.py \
  research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal
```

Expected current result:

```text
AUDIT PACKAGE OK
director_gate_status=blocked
promotion_allowed=false
paper_trades=0
fills=0
```

```bash
python3 research/audit_bridge/director_gate.py \
  research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal \
  --allow-blocked-exit-zero
```

Expected current result: `DIRECTOR GATE BLOCKED`.

```bash
cd research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal
sha256sum -c file_hashes.sha256
```

Expected current result: all listed files report `OK`.

If `make` is available:

```bash
make prepaper-verify \
  AUDIT_PACKAGE=research/audit_bridge/requests/TRADEO-AUDIT-20260616-213627_daily_internal
```

## Runtime Safety Snapshot

Before every Lab/Paper operating window, verify:

```bash
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/health/deep
curl -s http://localhost:8000/api/health/ibkr
```

Required state:

- `TRADEO_TRADING_MODE=paper`.
- `TRADEO_LIVE_TRADING_ENABLED=false`.
- `live_armed=false`.
- Runtime kill switch false.
- IBKR port is paper (`7497` for TWS paper or `4002` for IB Gateway paper, or
  the local mapped paper port used by the deployment).
- Backend/frontend are reachable only through localhost/VPN/firewall.
- Lab paper order safety is OK.
- Fox live submission remains disabled.

Stop the run if any live gate is true, any live port is configured, or the
runtime kill switch is active for an unresolved reason.

## Seven-Day Runbook

### Day 0: Release Prep

- Confirm this runbook, the preLive report, and the audit package are in the
  release branch.
- Run `make prepaper-verify` or the three direct commands above.
- Confirm the 20260616 package remains blocked and does not claim promotion.
- Confirm no live mode variables are enabled.
- Confirm IBKR Paper is connected and not readonly only if paper order
  submission is intentionally being tested.

### Day 1: Safety And Offender Freeze

- Freeze or demote `PATTERN_000282`, `PATTERN_000364`, and `PATTERN_000366`
  until they have linked paper fills.
- Record the freeze/demotion in an audit log or remediation note.
- Run Lab only during regular US market hours.
- Save order submission failures with exact reasons.

### Days 2-3: Paper Execution Loop

- Run Lab scans with paper mode and `execute_orders=true` only when market and
  risk gates permit.
- Track the funnel: opportunities, rejected opportunities, order attempts,
  submitted orders, cancelled orders, fills, closed trades.
- Reconcile DB orders/trades against IBKR Paper after every market session.
- Do not count submitted orders as fills.

### Days 4-5: Evidence Quality

- Confirm each real paper fill has fill hash, broker timestamp, commission,
  entry variant, regime key, slippage/cost metadata, and signal metadata.
- Keep shadow, near-miss, stale, cancelled, and fallback rows out of Director
  fill evidence.
- Export a new audit package if any real paper fill closes.

### Day 6: Research Cleanup

- Remove or explain duplicate event rows.
- Fill anti-lookahead contract fields.
- Make nested discovery replay either passed or an explicit blocker that caps
  the row below promotion.
- Keep `edge_claim=NO_DEMOSTRADO` until paper evidence exists.

### Day 7: Director Recheck

- Regenerate the audit package.
- Run validator, Director gate, and hash checks.
- If the package is still blocked, continue Lab/Paper and do not discuss Live.
- If a package passes a review threshold, prepare a Director review packet, but
  do not arm Live.

## Daily Checklist

Pre-market:

- Confirm paper mode, live unarmed, kill switch healthy.
- Confirm IBKR Paper connection and paper port.
- Confirm backend/frontend exposure is localhost/VPN/firewall only.
- Confirm no production manifest was created from Research-only evidence.

Market hours:

- Run Lab only through paper-safe gates.
- Record every non-fill reason.
- Capture order IDs only in redacted/hash form.
- Stop if the system starts using live configuration.

Post-market:

- Reconcile DB against IBKR Paper.
- Export or update audit evidence only from observed rows.
- Run package validator after any export.
- Update the daily decision log with blockers, fills, and next action.

## Promotion Rules

- Research may feed Lab/watchlist only.
- Lab may request Director review after enough normal closed paper fills exist.
- Director production requires stronger paper evidence and clean scientific
  contracts.
- FoxHunter may remain a blocked production gate.
- Live requires explicit Asier approval after production gates pass. Nothing in
  this runbook grants that approval.

## Files Changed

- `docs/remediation/prepaper_operational_runbook_2026_06_17.md`
- `reports/Auditoria_Tradeo_V_0_9_preLive.md`
- `README.md`
- `Makefile`
- `backend/tradeo/tests/test_prepaper_release_readiness.py`
