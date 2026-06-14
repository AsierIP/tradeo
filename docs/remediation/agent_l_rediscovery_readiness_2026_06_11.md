# Agent L — Rediscovery/Backfill Readiness (Wave4-C, 2026-06-11)

Branch: `feat/wave4-rediscovery-readiness-20260611`

## Objective

Legacy `DiscoveredPattern` rows predate the Wave4 metadata contracts and lack
the embedding contract, cluster signature/concentration metadata and
benchmark-regime calibration buckets. Deliver a safe path to identify them,
mark them and verify a real rediscovery repopulated them — without running a
heavy unbounded job in this phase and without pretending production rows were
populated.

## Remediation matrix

| Gap | Where it lives | Remediation delivered | Populated in prod? |
|---|---|---|---|
| Legacy patterns lack `feature_parity_contract` (embedding contract) | `metrics_json` on `discovered_patterns` rows written before Wave4 | Audit check `embedding_contract`: missing if no `contract_id`; **stale** if `contract_id != PatternEmbeddingEngine.CONTRACT_ID` (v2 legacy-prefix-stable) | No — readiness only; runbook §3 populates |
| Legacy patterns lack `cluster_signature` / `concentration_checks` / `medoid` | same | Audit check `cluster_signature`: requires dict signature with `medoid` dict and `concentration_checks.passed` present | No — readiness only |
| Legacy patterns lack `regime_profile.benchmark_regime_outcomes` (calibration buckets) | same | Audit check `regime_calibration_buckets`: requires outcomes dict with `available` key | No — readiness only |
| No way to mark laggards | n/a | `--apply-flags` writes `metrics_json.rediscovery_readiness` block (`needs_rediscovery`, `missing`, `stale`, `checker_version`, `flagged_at`); JSONB-extensible, no schema migration, flips honestly to `false` once real metadata arrives | Flag only — never fakes metadata |
| No rediscovery plan/manifest | n/a | `run_readiness()` emits manifest: per-pattern reasons, per-field counts, `metadata_complete_before == metadata_complete_after` by construction (tool populates nothing), truncation reported, `determinism.content_hash` (Wave4-B algo) | Manifest is dry-run honest |
| Unbounded scan risk | n/a | `DEFAULT_AUDIT_LIMIT = 2000` hard cap + explicit `truncated` flag in manifest and CLI warning | n/a |
| No execution/verification procedure | n/a | `docs/research/wave4_rediscovery_runbook.md`: bounded discovery commands, re-audit verification, success criteria, non-reemerging-pattern disposition rule | Pending operator run |

## Implemented

1. `backend/tradeo/research/rediscovery_readiness.py` (new):
   - `evaluate_pattern_metrics` — pure per-blob check returning
     (`missing`, `stale`) against the three Wave4 contracts.
   - `audit_patterns` — deterministic scan (ordered by `pattern_key`),
     bounded by `limit`, reports truncation.
   - `apply_rediscovery_flags` — opt-in flagging into `metrics_json`;
     clears to `needs_rediscovery: false` when metadata is later present.
   - `build_manifest` / `run_readiness` — honest manifest with before/after
     counts, content hash, and rediscovery plan pointer; optional JSON dump.
   - CLI: `python -m tradeo.research.rediscovery_readiness
     [--apply-flags] [--limit N] [--manifest-out PATH]` — dry-run by default.
2. `backend/tradeo/tests/test_rediscovery_readiness.py` (new, 7 tests):
   legacy-pattern flagged with all three fields missing; modern pattern
   clean; stale v1 embedding contract detected; dry-run mutates nothing and
   `after == before`; `--apply-flags` marks but re-audit still flags
   (flag ≠ metadata); flag flips to false after real metadata upsert;
   manifest written to disk and truncation honest at `limit`.
3. `docs/research/wave4_rediscovery_runbook.md` (new): operator runbook.

## Explicitly NOT done in this phase

- No discovery/rediscovery job was executed; production rows remain
  unpopulated until an operator follows runbook §3.
- No `--apply-flags` run against the production DB (operator decision).
- No schema migration (JSONB block chosen deliberately; no Alembic in repo).
- No live/paper order paths touched.

## Tests run

```
backend/.venv pytest tradeo/tests/test_rediscovery_readiness.py  -> 7 passed
pytest tradeo/tests/test_novel_pattern_registry.py tradeo/tests/test_discovery_determinism.py -> 10 passed
ruff check + format on new files -> clean
```

## Risks / assumptions

- Assumes rediscovery re-emerges the same clusters so upserts refresh legacy
  rows; patterns that never re-emerge stay flagged and need an explicit
  retire/accept disposition (runbook §3 caveat).
- Stale-contract detection keys off exact `CONTRACT_ID` equality; a future
  contract bump automatically marks all rows stale (intended behavior).
- Audit reads whole rows; at current pattern counts (≪2000) this is trivial.

## 2026-06-14 Addendum — deterministic/idempotent flags

Follow-up branch `solaris/internal-remediation-20260614` hardens the same
readiness tooling without changing scope: it still audits/flags only and never
populates metadata.

### What changed

- `run_readiness(..., generated_at=...)` and CLI `--generated-at` allow
  bit-for-bit reproducible manifests when an operator or CI pins the clock.
- Re-running `--apply-flags` against unchanged laggards is idempotent:
  existing `flagged_at` values are preserved, unchanged JSONB blocks are not
  rewritten, and `flagged_this_run` counts only newly flagged laggards.
- Clearing a flag after real rediscovery metadata arrives preserves the
  original `flagged_at` and records a stable `cleared_at`.
- Full-suite verification exposed a daily-cache refresh bug on weekends:
  a Friday daily bar was treated as stale on Sunday because the gap used
  calendar days. `CachedMarketDataProvider` now counts complete business
  dates before today's incomplete daily bar.

### Files Changed

- `backend/tradeo/research/rediscovery_readiness.py`
- `backend/tradeo/services/data_provider.py`
- `backend/tradeo/tests/test_data_provider.py`
- `backend/tradeo/tests/test_rediscovery_readiness.py`
- `docs/remediation/agent_l_rediscovery_readiness_2026_06_11.md`
- `docs/research/wave4_rediscovery_runbook.md`

### Tests

Added coverage that two fixed-clock manifests are byte-identical and that a
second unchanged `--apply-flags` pass does not rewrite `metrics_json`. Added
coverage that a Friday daily cache does not refresh on Sunday without a new
complete business-day bar.

### Remaining external gaps

No PIT/delisting feed, broker/live validation or external market-data provider
was added. Real metadata backfill still requires a bounded rediscovery run over
available internal cached/provider data, followed by this audit.
