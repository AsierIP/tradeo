# DSS-004C Return Decomposition

Partial decision: `TIMING_PASS`

## Average Components

| Segment | Mean return |
| --- | ---: |
| Signal close to next open | 0.3072% |
| Next open to close day 1 | 0.0615% |
| Day 1 to day 3 | 0.1896% |
| Day 3 to day 5 | 0.5657% |
| Day 5 to day 10 | 0.8829% |
| MAE | -7.3738% |
| MFE | 9.2478% |
| Net x2 trade return | 1.3829% |

## Interpretation

The edge is not only an untradable overnight gap. Most average return appears after entry, especially from day 3 through day 10. This supports the timing-window interpretation: the signal opens a multi-day window rather than a single-day execution edge.

MAE is material, so any future paper preview needs risk sizing and kill-switch logic. This task did not define stops or R.
