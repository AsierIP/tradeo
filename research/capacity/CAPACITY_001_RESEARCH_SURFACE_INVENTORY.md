# CAPACITY-001 Research Surface Inventory

## Summary
- Daily modules: 18
- Intraday modules: 18
- Research docs: 79
- GAP reports: 44
- Cache files: 1477
- Classified surfaces: 28

## Classified Surfaces
### GAP dry-run matrix
- Path: `scripts/run_daily_gap_matrix_dry_run.py`
- Family: `gap`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: False
- Notes: Safe parser/matrix baseline for capacity microbench.

### GAP confirmatory matrix
- Path: `scripts/run_daily_gap_confirmatory_matrix.py`
- Family: `gap`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: True
- Notes: Research matrix only; candidate approval remains outside CAPACITY-001.

### GAP backtest matrix module
- Path: `backend/tradeo/modules/daily_swing/gap_backtest_matrix.py`
- Family: `gap`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: True
- Notes: Backtest matrix implementation; must keep no-lookahead/cost gates.

### GAP matrix validation
- Path: `scripts/validate_daily_gap_backtest_matrix.py`
- Family: `gap`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: False
- Notes: Validation-only surface.

### Daily PB research runner
- Path: `scripts/backtest_daily_swing_dss_pb_001.py`
- Family: `daily`
- Flags: research-only, cache-only
- Candidate-producing: True
- Notes: Historical rejected family; not a rescue lane for CAPACITY-001.

### Daily BO research runner
- Path: `scripts/backtest_daily_swing_dss_bo_001.py`
- Family: `daily`
- Flags: research-only, cache-only
- Candidate-producing: True
- Notes: Historical rejected family; not a rescue lane for CAPACITY-001.

### Daily CO research runner
- Path: `scripts/backtest_daily_swing_dss_co_001.py`
- Family: `daily`
- Flags: research-only, cache-only
- Candidate-producing: True
- Notes: Historical rejected family; not a rescue lane for CAPACITY-001.

### Daily CW research runner
- Path: `scripts/backtest_daily_swing_dss_cw_001.py`
- Family: `daily`
- Flags: research-only, cache-only
- Candidate-producing: True
- Notes: Historical rejected family; not a rescue lane for CAPACITY-001.

### Intraday wave runner
- Path: `scripts/run_intraday_research_wave.py`
- Family: `intraday`
- Flags: research-only, cache-only
- Candidate-producing: True
- Notes: Heavy research runner; blocked from productive execution in CAPACITY-001.

### Intraday planner
- Path: `scripts/plan_intraday_research_next.py`
- Family: `intraday`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: False
- Notes: Planning-only surface for experiment queue design.

### Intraday readiness
- Path: `scripts/check_intraday_research_readiness.py`
- Family: `intraday`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: False
- Notes: Readiness check; safe for baseline diagnostics.

### Intraday funnel diagnostics
- Path: `scripts/diagnose_intraday_pattern_funnel.py`
- Family: `intraday`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: False
- Notes: Rejected/blocker diagnostics.

### Intraday forensics
- Path: `scripts/analyze_intraday_research_forensics.py`
- Family: `intraday`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: False
- Notes: Rejected/near-miss mining input.

### Intraday validation stack
- Path: `backend/tradeo/modules/intraday/research_validation_stack.py`
- Family: `intraday`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: False
- Notes: FDR/WRC/SPA-light, OOS, cost and blocker validation surface.

### VWAP shadow once
- Path: `scripts/run_vwap_shadow_once.py`
- Family: `laboratory`
- Flags: can-generate-signals
- Candidate-producing: False
- Notes: Explicitly excluded from CAPACITY-001.

### Scheduled lab shadow
- Path: `scripts/run_lab_shadow_scheduled_once.sh`
- Family: `laboratory`
- Flags: can-generate-signals
- Candidate-producing: False
- Notes: Explicitly excluded from CAPACITY-001.

### IBKR candidate fetch
- Path: `scripts/fetch_ibkr_intraday_candidates.py`
- Family: `data`
- Flags: IBKR-required
- Candidate-producing: True
- Notes: IBKR path; blocked for CAPACITY-001.

### Order notification
- Path: `scripts/notify_tradeo_orders.sh`
- Family: `execution`
- Flags: can-generate-preview-or-orders
- Candidate-producing: False
- Notes: Execution-adjacent; blocked for CAPACITY-001.

### Research API/core
- Path: `backend/tradeo/routers/research.py`
- Family: `research_api`
- Flags: research-only
- Candidate-producing: True
- Notes: Broker-safe but may write DB/artifacts; not used by CAPACITY-001 microbench.

### Intraday background research worker
- Path: `backend/tradeo/tasks/worker.py`
- Family: `intraday`
- Flags: research-only
- Candidate-producing: True
- Notes: Background DB write path; excluded from CAPACITY-001.

### Quant validation FDR/WRC/SPA gates
- Path: `backend/tradeo/research/quant_validation.py`
- Family: `validation`
- Flags: research-only, dry-run, cache-only
- Candidate-producing: False
- Notes: Validation gates used by research scoring.

### Rejected/near-miss persistence
- Path: `backend/tradeo/research/novel_pattern_registry.py`
- Family: `forensics`
- Flags: research-only, cache-only
- Candidate-producing: True
- Notes: DB persistence surface; CAPACITY-001 reads artifacts only.

### Intraday cache warming
- Path: `scripts/warm_intraday_cache_resilient.py`
- Family: `data`
- Flags: IBKR-required
- Candidate-producing: False
- Notes: Read-only market data path but requires IBKR/downloads; blocked for CAPACITY-001.

### Daily cache fill
- Path: `scripts/cache_daily_ohlcv.py`
- Family: `data`
- Flags: IBKR-required
- Candidate-producing: False
- Notes: Read-only market data path but requires IBKR/downloads; blocked for CAPACITY-001.

### Backtest API
- Path: `backend/tradeo/routers/backtests.py`
- Family: `backtest_api`
- Flags: research-only
- Candidate-producing: True
- Notes: Provider may refresh data; excluded from CAPACITY-001 microbench.

### Laboratory scanner API
- Path: `backend/tradeo/routers/laboratory.py`
- Family: `laboratory`
- Flags: can-generate-signals, can-generate-preview-or-orders
- Candidate-producing: False
- Notes: Execution perimeter; blocked for CAPACITY-001.

### Signals API
- Path: `backend/tradeo/routers/signals.py`
- Family: `execution`
- Flags: IBKR-required, can-generate-signals, can-generate-preview-or-orders
- Candidate-producing: False
- Notes: Execution perimeter; blocked for CAPACITY-001.

### IBKR API
- Path: `backend/tradeo/routers/ibkr.py`
- Family: `execution`
- Flags: IBKR-required, can-generate-signals, can-generate-preview-or-orders
- Candidate-producing: False
- Notes: Broker/API perimeter; blocked for CAPACITY-001.
