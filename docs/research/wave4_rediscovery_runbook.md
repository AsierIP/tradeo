# Wave4-C Rediscovery Runbook (2026-06-11)

How to repopulate Wave4 metadata on legacy discovered patterns: embedding
contract (`feature_parity_contract`), cluster signature + concentration
metadata (`cluster_signature` / `concentration_checks`), and benchmark-regime
calibration buckets (`regime_profile.benchmark_regime_outcomes`).

**Honesty contract:** the readiness tool below only *audits and flags*. It
never populates metadata. Patterns only become complete after a real
discovery run re-upserts them via `NovelPatternRegistry.upsert_candidate`,
which overwrites `metrics_json` with engine-fresh metrics.

## 0. Preconditions

- Backend stack up (`make up`) and DB reachable.
- No live/paper trading dependency: discovery is research-only, but avoid
  running it while a director cycle is mid-flight to keep run accounting clean.
- Recent market data cache present (discovery re-downloads otherwise).

## 1. Audit (dry-run, safe, read-only)

```bash
docker compose run --rm backend \
  python -m tradeo.research.rediscovery_readiness \
  --manifest-out /app/artifacts/rediscovery_manifest_$(date +%Y%m%d).json
```

- Default `--limit 2000`; if the manifest reports `"truncated": true`, rerun
  with a higher `--limit`.
- The manifest lists every `pattern_key` needing rediscovery, with per-field
  `missing`/`stale` reasons and a `determinism.content_hash` for comparison
  across runs.
- For byte-identical audit artifacts in CI, pass a fixed ISO timestamp with
  `--generated-at`, for example `--generated-at 2026-06-14T00:00:00+00:00`.

## 2. Flag laggards (optional, writes `metrics_json.rediscovery_readiness`)

```bash
docker compose run --rm backend \
  python -m tradeo.research.rediscovery_readiness --apply-flags \
  --manifest-out /app/artifacts/rediscovery_manifest_flagged.json
```

- Adds a `rediscovery_readiness` block (`needs_rediscovery`, `missing`,
  `stale`, `checker_version`, `flagged_at`) inside each laggard's
  `metrics_json`. No schema migration needed (JSONB is extensible).
- Re-running the same flagging pass is idempotent for unchanged laggards:
  existing `flagged_at` values are preserved and unchanged blocks are not
  rewritten.
- Re-flagging after metadata arrives flips the block to
  `needs_rediscovery: false` with `cleared_at`; it is never deleted,
  preserving audit trail.

## 3. Execute real rediscovery (the only step that populates metadata)

Discovery upserts by `pattern_key` family/centroid similarity, so re-running
discovery over the same universe/timeframes refreshes legacy rows in place
with the new metadata.

Bounded run (recommended first):

```bash
curl -s -X POST http://localhost:8000/api/research/run-discovery \
  -H 'Content-Type: application/json' \
  -d '{"limit": 40, "max_total_windows": 4000}' | jq .
# or: make discover-patterns
```

For full coverage use the existing loop with explicit bounds
(`scripts/research_forever.sh` honors `DISCOVERY_LIMIT`, `MAX_TOTAL_WINDOWS`,
`MAX_WINDOWS_PER_SYMBOL`). Do **not** launch unbounded loops as part of this
runbook; run discrete bounded passes and re-audit between them.

Caveat: a legacy pattern whose cluster no longer re-emerges from current data
will *not* be refreshed by rediscovery. Decide per pattern: retire it
(status/promotion demotion) or accept it stays flagged. Do not hand-edit its
metadata to look populated.

## 4. Verify success

```bash
docker compose run --rm backend \
  python -m tradeo.research.rediscovery_readiness \
  --manifest-out /app/artifacts/rediscovery_manifest_after.json
```

Success criteria:

1. `counts.needs_rediscovery` drops to 0 (or only to patterns explicitly
   accepted as retired/non-reemerging, each with a written disposition).
2. `counts.missing_by_field` and `counts.stale_by_field` are all 0 for
   non-retired patterns.
3. Embedding contract on refreshed rows equals
   `PatternEmbeddingEngine.CONTRACT_ID`
   (`tradeo.pattern_embedding.v2.legacy_prefix_stable`).
4. Discovery report carries a `determinism.content_hash` block (Wave4-B) and
   targeted tests stay green:

```bash
docker compose run --rm backend pytest \
  tradeo/tests/test_rediscovery_readiness.py \
  tradeo/tests/test_novel_pattern_registry.py \
  tradeo/tests/test_discovery_determinism.py -q
```

## 5. Rollback / safety

- The readiness tool itself only writes the `rediscovery_readiness` JSON
  block; nothing else. Worst case it can be ignored by all consumers.
- Discovery upserts are the standard production path (same as the director
  loop) — no special rollback beyond normal DB backups.
- Never run this against live trading sessions' hot path; it is DB-only.
