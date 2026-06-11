# Agent K — Discovery Bit-for-Bit Determinism (Wave4-B, 2026-06-11)

Branch: `feat/wave4-discovery-determinism-20260611`

## Objective

Make discovery/research output reproducible bit-for-bit for identical inputs,
config and seed — or close the scope honestly with a harness plus fixes for
the identified nondeterminism sources.

## Audit findings

| Source | Location | Verdict |
|---|---|---|
| Clustering RNG | `cluster_research_engine.py` `MiniBatchKMeans(random_state=42, n_init=10)` | Already seeded; deterministic in-process for identical input matrices. |
| Null/bootstrap RNG | `cluster_research_engine.py` `_null_seed()` (blake2b of side/rr/sizes), `adversarial_research.py` `_seed_index()`, `quant_validation.py` explicit `rng` params | Already content-addressed/seeded; no wall-clock or global RNG. |
| Sample ordering | `discover()` sorts window sizes; `_cluster_window_size` sorts samples by `end` | Deterministic given unique window-end dates; verified by shuffle test. |
| Engine-core timestamps | `cluster_research_engine.py`, `window_sampler.py`, `adversarial_research.py`, `quant_validation.py` | None present — engine core is wall-clock free. |
| Report JSON ordering | `pattern_discovery_lab_agent._write_report` dumped without `sort_keys` | **Fixed**: report JSON now dumps with `sort_keys=True`. |
| Report identity vs run metadata | Report filename embeds wall-clock `ts`; payload embeds `run_id`, paths, `generated_at` | **Fixed via content hash**: payload now carries `determinism.content_hash` (sha256 over canonical JSON excluding volatile keys), so two runs over identical inputs are comparable by hash regardless of run_id/timestamp/paths. |
| Memory-graph dict ordering | `autonomous_research_director.py` iterated `families.items()` / `regimes.items()` in DB-row insertion order | **Fixed**: iterations sorted; canonical-member tie now breaks on `pattern_key`. |
| Pattern query tie order | `_patterns` ordered by `(score desc, created_at desc)` only | **Fixed**: added `pattern_key asc` tiebreaker so equal-score/timestamp rows enumerate deterministically. |
| Test fixture hash salt | `tests/fixtures.py` `fixture_ohlcv` seeds from `abs(hash(symbol))` (PYTHONHASHSEED-salted) and `pd.Timestamp.now()` index | **Not changed** (out of scope; would silently reshape data under existing tests). New harness builds its own seeded fixtures. Noted as a known cross-process variance in *test fixture data*, not in production discovery. |

## Implemented

1. `backend/tradeo/research/determinism.py` (new):
   - `canonical_payload` / `canonical_json`: sorted stringified keys, volatile
     keys dropped, sets sorted, numpy unwrapped, non-finite floats → `null`.
   - `content_hash` (`sha256_canonical_json_v1`) with
     `DEFAULT_VOLATILE_KEYS` = timestamps (`built_at`, `generated_at`, …),
     `run_id`, durations, and artifact/filesystem path keys.
   - `candidate_content_payload` / `discovery_content_hash` for full
     candidate-list identity (metrics included).
2. `pattern_discovery_lab_agent._write_report`: appends a `determinism` block
   (`algo`, `content_hash`, `excluded_keys`, `generated_at`) computed before
   the block itself is added, and writes the JSON with `sort_keys=True`.
3. `autonomous_research_director.py`: deterministic enumeration (sorted
   families/regimes, pattern_key tiebreakers in query and canonical pick).

No statistics, thresholds or gates were changed; all edits are ordering,
serialization and metadata-identity only.

## Harness

`backend/tradeo/tests/test_discovery_determinism.py` (6 tests):

- Canonical-payload unit contracts: key-order/type insensitivity, volatile-key
  exclusion, non-finite → null.
- **Double-run engine contract**: real `ClusterResearchEngine.discover` runs
  twice over freshly rebuilt seeded synthetic fixtures (two separated vector
  blobs, 48 windows, unique end dates); full candidate payloads compared as
  canonical JSON strings — bit-for-bit equality, plus equal
  `discovery_content_hash`.
- **Input-order independence**: shuffled sample order produces an identical
  content hash.
- **Report artifact identity**: `_write_report` called with different
  `run_id`s yields equal `determinism.content_hash` and byte-identical
  canonical payloads outside the `determinism` block.

Evidence: targeted file 6 passed; image suite 288 passed, 4 skipped; ruff
clean on touched files.

## Honest limits

- The contract is **same machine, same image, same library versions,
  in-process**. sklearn/BLAS may vary float reductions across versions,
  hardware or thread configurations; cross-environment bit-equality is not
  claimed and not tested.
- Full real discovery (`PatternDiscoveryLabAgent.run`) hits live market data,
  DB autoincrement ids and the accumulating global experiment registry; those
  are run-context, excluded from the identity hash, and a full end-to-end
  double-run is intentionally out of scope. The deterministic contract covers
  the engine core (clustering, validation statistics, scoring) and the report
  payload identity.
- Registry hash-chain values depend on prior registry state by design; they
  are deterministic given the same starting state but differ across
  accumulating runs.
- `tests/fixtures.py` `fixture_ohlcv` remains PYTHONHASHSEED-sensitive across
  processes (pre-existing; affects only fixture-generated test data).
