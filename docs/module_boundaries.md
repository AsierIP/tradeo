# Tradeo Module Boundaries

Tradeo is split into three product domains plus shared primitives.

## Research

Purpose: discover and validate pattern hypotheses. Research never submits broker
orders.

Primary package:

- `backend/tradeo/research/`
- `backend/tradeo/modules/research/`

Key responsibilities:

- Window sampling, embeddings and clustering.
- Novel pattern registry and matching contracts.
- Research Director, hypothesis packages and experiment memory.
- Validation gates before any pattern can move toward paper validation.

## Laboratory

Purpose: validate Research patterns through paper execution and shadow
observations.

Primary package:

- `backend/tradeo/modules/laboratory/`

Key responsibilities:

- Laboratory API facade.
- Paper validation scans.
- Paper observation lifecycle.
- Laboratory diagnostics.

Laboratory may submit paper orders only when paper-mode safety gates allow it.
It must not submit live orders.

## FoxHunter

Purpose: monitor production-approved patterns and, only after explicit live
arming, route live execution.

Primary package:

- `backend/tradeo/modules/fox_hunter/`

Key responsibilities:

- FoxHunter API facade.
- Production manifest validation.
- Production-pattern scans.
- Live execution gating.

FoxHunter requires an active production manifest and live safety gates before
any live order path can open.

## Shared

Purpose: host mechanics that must stay identical across Laboratory and
FoxHunter.

Primary package:

- `backend/tradeo/modules/shared/`

Key responsibilities:

- Entry matching orchestration.
- Common signal creation flow.
- Risk/quality gate integration.
- Runtime status updates for entry scans.

Compatibility wrappers remain under `backend/tradeo/services/` so older imports
continue to work, but new code should enter through the domain packages.

