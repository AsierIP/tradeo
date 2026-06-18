# Audit Front D - statistical efficacy / overfitting

Date: 2026-06-17
Scope: `reward_risk_analyzer`, `validation_gate`, `cluster_research_engine`,
`data_quality`, audit/director gates, OOS/regime/multiple-testing/concentration
logic.

## Summary

No P0 live-bypass found: production approval is blocked behind real paper fills,
effective sample, nested replay evidence, Director audit gate, execution
provenance and `edge_claim=NO_DEMOSTRADO`.

Main statistical risk is earlier in Research/Lab: several safeguards are
diagnostic or warnings, not hard gates. The discovery pipeline can still create
lab/watchlist/candidate evidence while full nested replay is explicitly missing,
while data quality is not applied in discovery, and regime/OOS weakness can pass
as non-production state.

## Findings

### P1 - Discovery samples unvetted OHLCV quality

`PatternDiscoveryLabAgent.run()` fetches each symbol and sends it directly to
`WindowSampler.sample()` without `assess_ohlcv_quality_from_settings`, while the
classic scanner rejects non-research-grade data first.

Impact: frozen closes, zero-volume runs, calendar holes or suspected
split/bad-tick bars can enter clustering, inflate apparent recurrence, and
survive into lab evidence. This directly affects pattern efficacy and
overfitting risk.

Evidence:
- `backend/tradeo/agents/pattern_discovery_lab_agent.py:77`
- `backend/tradeo/agents/pattern_discovery_lab_agent.py:78`
- `backend/tradeo/services/scanner.py:51`
- `backend/tradeo/services/data_quality.py:82`

### P1 - Discovery accepts research states while full nested replay is absent

`ClusterResearchEngine` writes `nested_discovery_replay` as
`implemented=False` and says full nested replay must refit scaler, clustering,
side selection and R:R selection before any edge upgrade. `ValidationGate`
does not block lab/watchlist/candidate on this missing replay; the production
gate does block it later.

Impact: not a live bypass, but lab ranking and research persistence can be
driven by a non-nested discovery result. This leaves optimizer/cluster-selection
overfit unmeasured until much later.

Evidence:
- `backend/tradeo/research/cluster_research_engine.py:422`
- `backend/tradeo/research/cluster_research_engine.py:424`
- `backend/tradeo/research/cluster_research_engine.py:426`
- `backend/tradeo/research/validation_gate.py:248`
- `backend/tradeo/research/validation_gate.py:266`
- `backend/tradeo/services/director_review_gate.py:981`
- `backend/tradeo/services/director_review_gate.py:991`

### P1 - Multiple-testing accounting undercounts the full research surface

Run-level BH-FDR is applied only to candidates with finite `null_p_value`;
`real_variant_count` is just clusters x sides x R:R for the discovered clusters,
and the global registry only increments `global_trial_count` for new canonical
experiments. Repeated reruns, discovery parameter changes, failed/no-cluster
searches, universe/period choices and manual mining loops are not clearly
charged as trials.

Impact: p-hacking remains possible by rerunning/changing search space until a
candidate appears, especially because discovery thresholds are permissive
(`p_adj <= 0.25`) for lab-stage filtering.

Evidence:
- `backend/tradeo/research/cluster_research_engine.py:180`
- `backend/tradeo/research/cluster_research_engine.py:181`
- `backend/tradeo/agents/pattern_discovery_lab_agent.py:280`
- `backend/tradeo/agents/pattern_discovery_lab_agent.py:292`
- `backend/tradeo/agents/pattern_discovery_lab_agent.py:303`
- `backend/tradeo/research/global_experiment_registry.py:76`
- `backend/tradeo/research/global_experiment_registry.py:78`
- `backend/tradeo/research/global_experiment_registry.py:123`
- `backend/tradeo/core/config.py:162`

### P1 - OOS/purged CV weakness can pass as lab evidence

OOS expectancy <= 0 and OOS PF < 1.2 are warnings, not rejection reasons.
Missing walk-forward folds are also a warning. Purged CV only blocks when folds
exist; no folds means no hard reason. Lab-candidate requires positive OOS, but
lab/lab_watchlist can still be `validation_passed`.

Impact: weak or absent OOS can still persist patterns into the lab funnel and
influence ranking/active learning, even if production is later blocked.

Evidence:
- `backend/tradeo/research/validation_gate.py:206`
- `backend/tradeo/research/validation_gate.py:213`
- `backend/tradeo/research/validation_gate.py:215`
- `backend/tradeo/research/validation_gate.py:218`
- `backend/tradeo/research/validation_gate.py:249`
- `backend/tradeo/research/validation_gate.py:259`
- `backend/tradeo/research/validation_gate.py:314`

### P2 - Regime calibration is mostly advisory by default

Research records regime profiles and benchmark-regime outcomes, but the matcher
only hard-blocks calibrated-negative regimes if
`market_regime_hard_gate_enabled=True`; default is false. If a calibrated bucket
has too few samples, matching falls back to preferred-regime heuristics.

Impact: regime blindness is mitigated but not eliminated. A pattern can be
matched in a known bad or under-sampled regime unless operators enable the hard
gate and enough regime-labeled samples exist.

Evidence:
- `backend/tradeo/core/config.py:92`
- `backend/tradeo/core/config.py:93`
- `backend/tradeo/research/cluster_research_engine.py:2050`
- `backend/tradeo/research/cluster_research_engine.py:2057`
- `backend/tradeo/research/novel_pattern_matcher.py:237`
- `backend/tradeo/research/novel_pattern_matcher.py:238`
- `backend/tradeo/research/novel_pattern_matcher.py:539`
- `backend/tradeo/research/novel_pattern_matcher.py:540`

### P2 - Concentration controls miss multi-month/event clustering

Cluster concentration hard-checks only max symbol share >40% and max month share
>50%. It reports HHI but does not gate on HHI, sector, event week, calendar
quarter, or overlapping macro episodes.

Impact: a pattern can pass while concentrated in a few related symbols or one
market episode spread across adjacent months.

Evidence:
- `backend/tradeo/research/cluster_research_engine.py:2287`
- `backend/tradeo/research/cluster_research_engine.py:2290`
- `backend/tradeo/research/cluster_research_engine.py:2292`
- `backend/tradeo/research/cluster_research_engine.py:2317`
- `backend/tradeo/research/validation_gate.py:67`

### P2 - False-match/FPR harness is not a discovery acceptance gate

The engine computes `fpr_at_recall90`, but `ValidationGate` does not reject or
downgrade on high or missing false-match FPR. The setting
`false_match_metrics_high_fpr_threshold` feeds ops reporting, not discovery
promotion.

Impact: a statistically profitable cluster with poor matcher separability can
still enter lab states, increasing false live/paper signal load.

Evidence:
- `backend/tradeo/research/cluster_research_engine.py:325`
- `backend/tradeo/research/cluster_research_engine.py:337`
- `backend/tradeo/research/false_match_harness.py:52`
- `backend/tradeo/core/config.py:342`

## Prioritized Methodology Improvements

1. Make discovery data-quality fail-closed. Apply
   `assess_ohlcv_quality_from_settings` in `PatternDiscoveryLabAgent.run()` and
   persist skip counts in run summary. Why: prevents bad bars from becoming
   statistical "edge".

2. Add a finalist nested replay gate before `lab_candidate`. Refit scaler,
   clusterer, side and R:R inside outer folds; require positive median OOS,
   low PBO, and no fold worse than configured loss. Why: closes the main
   selection-overfit gap.

3. Expand trial accounting. Charge trials for window sizes, forward horizons,
   R:R grid, sides, clusterer method/min_samples, universe/period/stride, failed
   searches and repeated reruns. Why: FDR/DSR should reflect the actual mining
   surface.

4. Harden OOS gates by state. Keep `lab` permissive if desired, but require
   positive holdout, enough folds, purged CV p10 > 0 or bounded downside, and
   OOS PF floor for `lab_watchlist`/`lab_candidate`. Why: prevents weak OOS from
   consuming paper-validation budget.

5. Enable calibrated regime hard gate for execution-stage matching once bucket
   counts are adequate; otherwise cap to observation-only. Why: prevents
   matching in regimes where research-labeled outcomes are negative or unknown.

6. Replace simple concentration thresholds with effective diversity gates:
   symbol HHI, sector HHI, month/quarter HHI, event-week clusters, and
   max correlated-symbol group share. Why: one macro episode should not look
   like independent evidence.

7. Turn false-match FPR into a lab-state gate. Require negative banks and
   `fpr_at_recall90` below a threshold, or downgrade to watchlist. Why:
   tradable efficacy needs both edge and recognizability.

## Recommended Tests / Fixtures

- Discovery fixture with stale closes / zero volume / split jump proves
  `PatternDiscoveryLabAgent` skips and audits bad symbols before sampling.
- Synthetic p-hacking run: many repeated parameter/universe runs with one lucky
  cluster; assert global trial count and DSR/FDR block it.
- Nested replay fixture where fixed-cluster validation passes but refit-inside
  folds fails; assert no `lab_candidate`.
- OOS-negative but train-positive candidate; assert only `lab` or rejected,
  never `lab_watchlist`/`lab_candidate` under hardened policy.
- Regime-negative bucket with enough PIT samples; with hard gate enabled,
  matcher must reject; with insufficient bucket size, it must mark
  observation-only, not preferred.
- Concentration fixture spread over adjacent months but one event episode;
  assert HHI/event-week blocker.
- High false-match FPR fixture with profitable outcomes; assert discovery
  downgrade/rejects until matcher separability improves.
