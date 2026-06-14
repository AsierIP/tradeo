# V1 Precision P2 — Research, Matching, Evidence and Cost Guards (2026-06-14)

Implements a conservative slice of the `INFORME_MEJORA_TRADEO_V1_PRECISION`
items that were still open after P0/P1 preparation. The implementation keeps
live execution guarded: new matching/evidence features are diagnostic or
paper/shadow-only unless a persisted Research contract and explicit flags exist.

## Research and Matching

- Discovery now supports `discovery_clusterer_method=auto`: sklearn HDBSCAN is
  used when available and produces density/noise metadata; deterministic
  MiniBatchKMeans remains the fallback.
- Research persists clusterer metadata, noise counts/rates, and coassignment
  consensus stability so Director/audit packets can distinguish dense clusters
  from fallback partitions.
- Research persists a bounded shape-verifier contract over `close_norm` and
  `volume_rel` using DTW or soft-DTW.
- Lab matcher can compute DTW diagnostics behind
  `discovery_match_shape_dtw_enabled`; hard blocking is off by default and only
  applies when `discovery_match_shape_dtw_hard_gate_enabled=true` and the
  pattern carries a valid Research threshold.

## Automejora and Director Evidence

- Champion/challenger manifests identify champion and paper/shadow challenger
  config versions with deterministic hashes. Live/production selection always
  resolves to the champion.
- Entry-variant Thompson sampling is available as a bounded paper/shadow helper;
  live/production mode forces the default variant.
- Director sequential evidence now includes mSPRT and alpha-spending diagnostics
  alongside the existing posterior/SPRT/KS packet.
- Quant validation adds SPA, Romano-Wolf stepdown, and CPCV multipath helpers.
  SPA/Romano-Wolf are currently wired into self-improvement reports as
  diagnostics, not hard promotion gates.

## Real-Fill Cost Recalibration

- Execution quality now builds advisory tiered-cost recalibration reports from
  real broker fills grouped by ADV bucket.
- Reports can be published to `agent_messages` and `audit_logs` as suggestions.
  They never mutate live risk, strategy config, or backtest cost settings.

## Verification

- Targeted integrated suite:
  `141 passed, 1 skipped`.
- Full backend suite:
  `393 passed, 1 skipped, 1 warning`.
- `ruff check` on touched files: passed.
- `git diff --check`: passed.

## Remaining Limits

- HDBSCAN holdout labels are conservative: sklearn HDBSCAN has no native
  predict path, so holdout assignment uses recorded nearest-centroid/member
  radius metadata.
- DTW hard gating remains disabled by default until fresh Research contracts are
  created and validated.
- SPA/Romano-Wolf/CPCV are implemented as tested helpers/diagnostics; turning
  them into production promotion gates should be a separate Director-approved
  change.
- Cost recalibration requires enough real fills per ADV bucket before suggested
  parameters are meaningful.
