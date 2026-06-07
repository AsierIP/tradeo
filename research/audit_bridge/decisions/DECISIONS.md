# Tradeo Director Decisions

## 2026-06-07 — 2026-06-07_ib_paper_patterns

- Verdict: `NEEDS_PROCESS_IMPROVEMENT`
- Director score: `30 / 100`
- Confidence: `medium`
- Promotion decision: `repeat_with_fixes`
- Pattern approval: none
- Main reason: the package is useful for process audit but has zero paper trades, zero IB fills, no observed costs/slippage/spread, no explicit OOS/walk-forward proof, and no persisted market regime/sector.
- Required next action: run the new Director gate and fix the audit/export process before ranking or promoting any pattern.
- Related files:
  - `research/audit_bridge/director_gate.py`
  - `research/audit_bridge/responses/2026-06-07_ib_paper_patterns_RESPONSE.md`
  - `research/audit_bridge/responses/2026-06-07_ib_paper_patterns_RESPONSE.json`
  - `research/audit_bridge/task_queue/pending/2026-06-07_ib_paper_patterns_director_gate_and_research_fixes.md`

### Decision notes

The package may remain as a historical audit artifact, but it must not be interpreted as pattern approval. Research R-metrics are not net realized PnL. Future packages must distinguish base schema validity from Director promotion eligibility.
