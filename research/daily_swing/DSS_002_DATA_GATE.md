# DSS-002 Data Gate

DATA_GATE=BLOCKED

Validated local seed universe files and searched for reusable Daily OHLCV cache files. The repo currently exposes seed universe CSVs with `symbol,name,cap_segment,note`, but not enough OHLCV history to run DSS-PB-001.

- Symbols total: 40
- Stock-only seed universe: True
- OHLCV columns confirmed: False
- 2026-07-03 false USA bar present: False
- Last valid bar for 2026-07-06 signals: 2026-07-02

Daily data candidates inspected:
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/config_snapshot/data_config.json` (209 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/config_snapshot/detector_config.json` (1100 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/config_snapshot/execution_config.json` (213 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/config_snapshot/ib_paper_config.redacted.json` (231 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/config_snapshot/risk_config.json` (265 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/config_snapshot/universe_config.json` (596 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/director_audit_run.json` (566252 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/director_gate_result.json` (688558 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/experiment_registry.csv` (1959610 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/ib_fills.csv` (174 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/internal_auditor_agent_review.json` (1606 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/manifest.json` (4613 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/metrics_by_entry_variant.csv` (428 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/metrics_by_pattern.csv` (138025 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/metrics_by_period.csv` (978002 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/metrics_by_regime.csv` (426 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/metrics_by_ticker.csv` (468863 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/paper_trades.csv` (510 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/pattern_catalog.csv` (886231 bytes)
- `research/audit_bridge/requests/TRADEO-AUDIT-20260611-213558_daily_internal/pattern_events.csv` (7737380 bytes)

Blocking reason: no local historical Daily OHLCV cache with open/high/low/close/volume, adjusted dates and enough lookback was available for the requested real backtest.
