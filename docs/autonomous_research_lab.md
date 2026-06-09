# Autonomous Research Lab

Tradeo Research now adds a deterministic autonomous-science layer to discovery.
It does not train neural networks, install dependencies, migrate the database or
promote patterns to paper/live. All durable state is JSON/Markdown under
`reports/research` and candidate `metrics_json`.

## Flow

1. `PatternDiscoveryLabAgent` samples windows and calls `ClusterResearchEngine`.
2. Each cluster receives:
   - `foundation_teacher`: masked reconstruction, contrastive embedding and future-proxy diagnostics.
   - `market_replay`: latency, late entry, partial fill, fill probability, size cap, spread/slippage and gap penalties.
   - `causal_invariance`: regime/year/symbol/liquidity/sector proxy invariance and expected-fail buckets.
   - `adversarial_challenge`: leakage probe, placebo, shuffled assignment, universe/date/cost/regime/parameter shocks.
3. `ValidationGate` consumes those metrics and can reject fragile candidates.
4. `ResearchDirector` runs at discovery completion before registry persistence.
5. The existing DB director/scheduler can still run separately when enabled.

## Artifacts

The discovery-completion director writes:

- `reports/research/research_memory_graph.json`
- `reports/research/director/run_<id>_director_<ts>.json`
- `reports/research/director/run_<id>_director_<ts>.md`
- `reports/research/papers/run_<id>/<pattern_key>.md`

The memory graph stores families, variants, relations, regimes, decay and
family state. It is intentionally JSON so existing databases stay compatible.

## Lifecycle

Lifecycle states are suggestions only:

- `discovered`
- `challenged`
- `confirmed`
- `decaying`
- `retired`
- `resurrectable`

Every lifecycle payload includes:

- `paper_live_auto_promotion: false`
- `director_gate_required_for_paper_or_live: true`

## Kill Conditions

Generated hypotheses include explicit death conditions such as failed fresh OOS,
negative replay expectancy, adversarial hard failure, causal concentration,
cost-stress failure and parameter decay.

## Tests

Focused tests live in `backend/tradeo/tests/test_autonomous_research_lab.py`.
They cover replay penalties, adversarial gate rejection and director artifacts.
