# P1 kNN/Mahalanobis Matcher Support

## Scope

Adds optional matcher support for medoid kNN similarity and diagonal
Mahalanobis distance when Research persists prototype metadata.

## External Report Sections Addressed

- §3.1.1: distance to k nearest medoids instead of only centroid distance.
- §3.1.2: diagonal Mahalanobis as a second shape gate.

## Files Changed

- `backend/tradeo/core/config.py`
- `backend/tradeo/research/novel_pattern_matcher.py`
- `backend/tradeo/tests/test_pattern_entry_scanner.py`

## Behavior

- New settings:
  - `discovery_match_knn_enabled`
  - `discovery_match_knn_k`
- If a pattern has `matcher_medoids_scaled` or `medoid_vectors_scaled`, the
  matcher computes average distance to the k nearest medoids and requires
  `match_knn_similarity_threshold` when present.
- If a pattern has `matcher_diag_variance_scaled`, the matcher also computes a
  diagonal Mahalanobis distance and honors `match_mahalanobis_max_distance`
  when present.
- Patterns without medoid metadata keep the existing centroid/tau path.

## Tests

- Optional kNN medoid diagnostics pass with nearby medoids.
- A far medoid set blocks when the kNN threshold is not met.

## Remaining Risks

- Research still needs to persist real medoid vectors and diagonal variances
  during discovery. Until then this support is dormant and backward compatible.
