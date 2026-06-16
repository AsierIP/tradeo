# Tradeo Module Boundaries

Tradeo is split into three product domains plus shared primitives.

## Intelligence Residency

Tradeo's intelligence is distributed. No single service owns "the brain"; each
layer owns a bounded kind of judgment and hands off evidence to the next layer.

- Scientific cortex: `backend/tradeo/research/` discovers hypotheses,
  validates them statistically, writes memory artifacts and keeps research
  `edge_claim` unproven until separate execution evidence exists.
- Current perception: `NovelPatternMatcher` compares today's market windows
  against persisted pattern centroids and stores auditable match context.
- Operational decision: shared entry scanning, entry gates, opportunity ranking
  and risk checks decide whether a current match may become a Lab/Fox signal.
- Memory and evidence: DB models, JSON contracts, metadata, `audit_logs` and
  `agent_messages` are the durable record. Agent messages transport evidence
  and blockers; they do not promote state.
- Executable learning: Laboratory observations, paper fills and Director gates
  decide whether research hypotheses have operational truth.
- Survival: RiskManager, IBKR broker validation, reconciliation and kill
  switches can veto execution regardless of upstream scores.
- Production: FoxHunter, production manifests and pattern health monitoring
  are the only live-pattern runtime boundary.
- Metabolism: workers and runtime status keep scans, reports and audits moving
  but should not silently invent new decision authority.

Frontend surfaces are trust interfaces, not decision engines. They can mislead a
human if evidence is displayed incorrectly, but they must not become a hidden
source of trading decisions.

When improving this area:

- Qualitative improvements should clarify handoffs, provenance and blocker
  reasons without merging domain responsibilities.
- Performance improvements should cache deterministic perception/research work
  and reduce repeated market-data fetches without caching away fresh evidence,
  risk state, kill switches or reconciliation checks.
- Veracity improvements should strengthen fail-closed evidence boundaries:
  research metrics stay research-only, shadow observations stay non-fill
  evidence, paper/live fills require broker provenance, and promotions remain
  Director/manifest gated.

Changes that move promotion responsibility, consolidate memory stores, create a
new decision layer or alter persisted contracts need orchestrator approval.

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
