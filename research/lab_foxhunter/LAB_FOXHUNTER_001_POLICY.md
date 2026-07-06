# LAB_FOXHUNTER_001 Policy

Decision: paper can be used as a Lab validator, but paper results are not live approval.

## Taxonomy

- `research_observation`: hypothesis or interesting rejected/near-miss result. It does not trade.
- `lab_paper_probe`: may trade in paper in a later authorized phase with small size, full telemetry, and no live implication.
- `foxhunter_candidate`: has passed Lab paper evidence and minimum research gates; ready for strict review only.
- `live_candidate`: requires FoxHunter, risk review, kill-switch proof, and explicit Asier/Direction authorization.

## Safety Policy

This task only defines gates and manifests. It does not send paper orders, live orders, previews, or operational signals. Probes are `disabled_by_default=true` until a later task explicitly enables a supervised paper-only batch.
