# P1 Research Matcher Prototypes

## Scope

Persists matcher prototype metadata during Research discovery so Lab can use
the new conformal/kNN/Mahalanobis matcher path on newly discovered patterns.

## External Report Sections Addressed

- §3.1.1: medoid kNN support.
- §3.1.2: diagonal Mahalanobis support.
- §3.1.3: conformal threshold support.

## Files Changed

- `backend/tradeo/research/cluster_research_engine.py`
- `backend/tradeo/tests/test_pattern_discovery_lab.py`

## Behavior

For each cluster candidate, Research now persists:

- `match_conformal` report and `match_conformal_similarity_threshold` when
  calibration has enough members.
- `matcher_medoids_scaled`
- `matcher_diag_variance_scaled`
- `match_knn_similarity_threshold`
- `matcher_prototype_contract`

Existing centroid/tau fields remain unchanged for backward compatibility.

## Tests

- Prototype contract persists medoids, diagonal variance and kNN threshold.
- Conformal threshold report is emitted for sufficiently large calibration
  samples.

## Remaining Risks

- Existing persisted patterns will not have these fields until rediscovery or
  refresh. The matcher falls back to centroid/tau for those legacy patterns.
