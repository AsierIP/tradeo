# Post-Audit Remediation Report - 2026-06-10

Source: post-implementation audit dated 2026-06-10.

Verdict after remediation: live/production remains blocked by design until
real IBKR paper fills are reconciled and a Director audit package passes. The
code now blocks the false-positive paths identified by the audit instead of
treating closed internal trades, shadow observations or dashboard summaries as
proof of edge.

## Corrections Applied

| Audit item | Exact correction | Main files |
|---|---|---|
| R1 - `ibkr_paper_fill` inferred from closed status | Removed closed-status promotion as proof of fill. `ibkr_paper_order` becomes `ibkr_paper_fill` only with real fill provenance: `broker_execution` or `broker_statement_import`, fill/execution id or hash, broker timestamp and commission. Simulated and shadow closes never count as strong fills. | `backend/tradeo/services/evidence.py`; `research/audit_bridge/export_audit_package.py`; `backend/tradeo/services/director_review_gate.py`; `backend/tradeo/services/module_dashboard.py` |
| R1 - reconstructed audit fills | `paper_trades.csv` and `ib_fills.csv` export only broker-provenance fills. The exporter no longer reconstructs IBKR fills from a closed paper trade record. Fill rows now derive hashes from broker fill/execution metadata and mark the provenance source. | `research/audit_bridge/export_audit_package.py`; `backend/tradeo/tests/test_audit_hardening.py` |
| R2 - incomplete production gate | `DirectorProductionGate` now requires scientific contracts in addition to 30 fills: nested discovery replay implemented/passed, Director audit passed, no active blockers, event ledger hash, evidence packet reference/hash, reconciled cost/slippage/fill provenance, non-degrading drift, `edge_claim=NO_DEMOSTRADO`, and registry hash-chain metadata. | `backend/tradeo/services/director_review_gate.py`; `backend/tradeo/tests/test_director_review_gate.py`; `backend/tradeo/tests/test_research_lab_fox_lifecycle.py` |
| R3 - evidence stored only in JSON | Added typed `Trade.evidence_type` and `Trade.evidence_quality` columns plus init-time backfill from `metadata_json`. Runtime helpers merge typed columns with legacy metadata for compatibility. | `backend/tradeo/db/models.py`; `backend/tradeo/db/init_db.py`; write paths in `ibkr_broker.py`, `paper_broker.py`, `lab_paper_observations.py` |
| R4 - validator/gate semantics | Validator output now separates `schema_valid` / `package_valid`, `director_gate_status`, and `promotion_allowed`. A schema-valid package can be explicitly blocked for promotion. Anti-lookahead columns and scientific experiment columns are part of the expected export contract. | `research/audit_bridge/validate_audit_package.py`; `research/audit_bridge/director_gate.py`; `research/audit_bridge/export_audit_package.py` |
| R5 - global experiment registry too soft | Registry writes are now temp+rename atomic, existing registries are backed up, each write stores a canonical registry hash, previous hash and run manifest hash, and candidates receive registry hash-chain metadata. | `backend/tradeo/research/global_experiment_registry.py`; `backend/tradeo/tests/test_pattern_discovery_lab.py` |
| R6 - dashboard partial scope unclear | Dashboard overview now exposes `data_scope`, `query_limit`, `summary_limit`, `pnl_basis`, `director_source=false`, and a scope note. Frontend shows the limited scope beside fill KPIs. | `backend/tradeo/services/module_dashboard.py`; `frontend/app/page.tsx`; `backend/tradeo/tests/test_module_dashboard.py` |

## Problems Found While Fixing

| Problem | Resolution |
|---|---|
| The backend evidence helper was fixed by agents, but the audit exporter still had its own closed-status to fill inference. | Aligned `export_audit_package.py` with the stricter provenance contract. |
| `active_blockers=[]` could become the literal CSV text `[]` and be interpreted as a blocker. | Export now writes an empty string when there are no blockers; Director gate ignores empty list sentinels. |
| Legacy tests encoded the old assumption that closed paper trades were fills. | Updated tests to require broker provenance and added a regression test rejecting closed paper trades without broker fill metadata. |
| Dashboard fill counts could still look like full-history evidence. | Dashboard now labels the scope as latest-query summary and declares it is not a Director source. |

## Remaining Blockers

- Real edge is still `NO_DEMOSTRADO`.
- Production remains blocked until real IBKR paper executions are reconciled into trade metadata or imported broker statements with fill IDs/hashes, broker timestamps, commissions, slippage/cost provenance and audit package hashes.
- A process still needs to persist the real Director audit result and evidence packet metadata into `pattern.metrics_json` before `DirectorProductionGate.approve_pattern()` can ever pass.
- Existing audit packages may remain schema-valid but promotion-blocked until they include the new scientific contract fields, anti-lookahead values and broker-provenance fills.

## Verification

- Focused backend remediation tests passed for audit hardening, Director gates and dashboard scope.
- Ruff passed on the modified audit/evidence/gate files before final full verification.
- Full-suite verification is recorded in the commit summary for this branch.
