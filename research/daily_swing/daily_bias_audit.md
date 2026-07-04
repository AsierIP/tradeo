# Daily Bias Audit

- Lookahead: blocked by `last_valid_trading_day`; Monday 2026-07-06 uses Thursday 2026-07-02.
- Holiday: explicit 2026-07-03 observed Independence Day test prevents a fake Friday bar.
- Leakage: preview hashes include signal date, last valid bar date, sizing, entry, stop and target.
- Survivorship: unresolved because the pilot uses current liquid names for preview; live remains blocked and automatic paper submission remains blocked until this is audited.
- Historical evidence: unresolved in this branch; metrics are scaffold placeholders, not backtest output.
- FDR/WRC/SPA: not implemented for Daily in this branch; documented gap, blocks live, does not block paper_probe.
