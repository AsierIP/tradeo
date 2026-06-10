# Agent A Fallback - Data, Universe, Reproducibility

Date: 2026-06-10
Branch/worktree: `agent-a-data-universe-repro-fallback` at `/home/vboxuser/tradeo-worktrees/agent-a-data-universe-repro-fallback`

## Scope

Implemented bounded remediation for external report sections 3.1, 3.2, 3.8, 7, and related config. No live trading, no order routing, no secrets.

## External Report Sections Addressed

- 3.1 Data layer: added deterministic local OHLCV cache with canonical CSV artifacts, sidecar metadata, `adjusted`, `what_to_show`, `bar_complete`, split-like jump heuristic, and per-run data manifest export.
- 3.2 Universe: added monthly forward snapshot service with eligibility filters, metadata/hash, explicit `point_in_time` and `survivorship_biased` flags.
- 3.8 Regimes: enriched regime profile with `regime_count`, `dominant_share`, and `regime_specific`/`multi_regime_observed` research gate metadata; event ledgers now include data lineage.
- 7 Reproducibility: discovery runs now attach a data manifest summary and universe snapshot metadata to run summaries and candidates.
- 8 Config: added explicit env/config knobs for market-data cache, adjusted feed metadata, universe snapshots, PIT availability, and survivorship cap.

## Files Changed

- `.env.example`
- `backend/tradeo/agents/pattern_discovery_lab_agent.py`
- `backend/tradeo/core/config.py`
- `backend/tradeo/research/cluster_research_engine.py`
- `backend/tradeo/research/types.py`
- `backend/tradeo/research/validation_gate.py`
- `backend/tradeo/research/window_sampler.py`
- `backend/tradeo/services/data_provider.py`
- `backend/tradeo/services/ibkr_data_provider.py`
- `backend/tradeo/services/provider_factory.py`
- `backend/tradeo/services/universe_snapshot.py`
- `backend/tradeo/tests/test_data_provider.py`
- `backend/tradeo/tests/test_quant_validation_integration.py`
- `docs/remediation/agent_a_data_universe_repro_2026_06_10.md`
- `docs/remediation/tradeo_12_phase_compliance_matrix_2026_06_10.md`

## Tests Run

- `python3 -m compileall tradeo/core/config.py tradeo/services/data_provider.py tradeo/services/provider_factory.py tradeo/services/ibkr_data_provider.py tradeo/services/universe_snapshot.py tradeo/research/window_sampler.py tradeo/research/types.py tradeo/research/cluster_research_engine.py tradeo/research/validation_gate.py tradeo/agents/pattern_discovery_lab_agent.py`
- `docker run --rm -v "$PWD/backend/tradeo:/app/tradeo:ro" d407ca6eb516 pytest tradeo/tests/test_data_provider.py tradeo/tests/test_quant_validation_integration.py -q` -> 21 passed
- `docker run --rm -v "$PWD/backend/tradeo:/app/tradeo:ro" d407ca6eb516 ruff check ...touched files...` -> passed

Note: host Python lacked `pytest` and `pandas`. Full Docker build failed only at `COPY data /app/data` because this isolated worktree has no `data/` directory. Tests were run in the successfully built dependency layer with current code mounted read-only.

## Remaining Risks / Known Non-Compliance

- Cache is deterministic and manifest-backed, but not true incremental-by-date because the existing provider boundary accepts only `period`/`interval`; metadata marks `incremental_fetch_supported=false`.
- Artifact format is canonical CSV, not Parquet, to avoid adding heavy unpinned dependencies. The manifest makes the format explicit.
- IBKR `ADJUSTED_LAST` is now configurable/defaulted for research data, but live verification against the gateway was not run.
- Historical point-in-time/delisting coverage is still unavailable. The system now honestly caps `lab_candidate` to `lab_watchlist` when discovery metadata declares `survivorship_biased=true`.
- Regime profile is metadata/gating support, not a full SPY SMA200 tercile service yet.

## Merge Notes

- This branch is isolated from `/home/vboxuser/tradeo` and does not revert other agents' work.
- Safe merge order: after any branches touching the same validation/config/provider files, review conflicts around `ValidationGate`, `PatternDiscoveryLabAgent`, and `.env.example`.
- No live trading settings were enabled; paper-first/read-only defaults remain intact.
