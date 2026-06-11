# Agent I - Calibrated Benchmark-Regime Outcome History (3.8)

Date: 2026-06-11
Branch: `feat/tradeo12-regime-outcome-calibration-20260611`
Scope: external report section 3.8 (market regimes), the Agent E remaining
gap: "Not yet a hard gate in `_pattern_regime_fit`; needs labeled outcome
history per regime bucket to calibrate."

## Problem

Agent E shipped the PIT SPY SMA200/vol-tercile regime service and attached
`benchmark_regime` to every match, but `_pattern_regime_fit` could only use
presence heuristics (was this regime *seen* during research?) because no
outcome history existed per benchmark-regime bucket. A pattern that was
merely *observed* in `benchmark_bear|high_vol_tercile` scored 0.85 even if
every such sample lost money, and there was no data to ever justify a hard
gate.

## Change

Research now persists labeled outcome history per benchmark-regime bucket,
and the matcher consumes it as a calibrated fit with an optional hard gate.

1. **`services/market_regime.py`**
   - `regime_keys_for_dates(table, dates)`: PIT regime_key at the last
     benchmark bar on or before each date; dates before benchmark history
     return an explicit `insufficient_history|insufficient_history` key
     (`unlabeled_regime_key()`) instead of guessing.
   - `MarketRegimeService.history_table(period)`: full PIT regime table
     covering the research period plus the labeling warmup
     (`required_benchmark_bars`), with the regime config recorded in
     `DataFrame.attrs`. `period_to_months` converts provider period strings.
2. **`research/cluster_research_engine.py`**
   - New optional field `benchmark_regime_table`.
   - `_benchmark_regime_outcomes(samples, side, rr)`: labels each cluster
     sample's window end with the PIT benchmark regime and simulates it with
     the canonical triple-barrier path (`RewardRiskAnalyzer._simulate_sample`,
     same engine as backtester/shadow) at the pattern's side and best RR.
     Per-bucket `sample_count`/`expectancy_r`/`win_rate`/`profit_factor` are
     persisted inside `regime_profile.benchmark_regime_outcomes`, with honest
     `labeled_sample_count`/`unlabeled_sample_count` and an `available:false`
     record when the benchmark table is missing.
3. **`agents/pattern_discovery_lab_agent.py`**: builds the regime table via
   `MarketRegimeService.history_table(params["period"])` and passes it to the
   engine; failure degrades to a run warning, never a failed discovery run.
4. **`research/novel_pattern_matcher.py`**
   - `_pattern_regime_fit(pattern, regime, settings)` now tries
     `_calibrated_regime_fit` first: when the CURRENT `benchmark_regime`
     bucket has at least `market_regime_outcome_min_samples` labeled
     outcomes, the fit is calibrated — positive expectancy →
     `calibrated_regime_positive` (score 0.75–1.0, scaled by expectancy),
     non-positive → `calibrated_regime_negative` (score 0.2,
     `hard_gate_blocked: true`). The full bucket evidence is attached as
     `regime_fit.calibration` for audit.
   - Insufficient bucket samples, unlabeled benchmark regime, or missing
     calibration data fall back to the existing presence heuristics
     unchanged (legacy patterns keep their previous behavior bit-for-bit).
   - `match_current` drops calibrated-negative matches before variant
     creation only when `market_regime_hard_gate_enabled` is on (default
     OFF), logging each block; run output now reports
     `regime_hard_gate_enabled` and `regime_gate_blocked` counts.
5. **Config**: `market_regime_outcome_min_samples` (default 12) and
   `market_regime_hard_gate_enabled` (default false) in `Settings` and
   `.env.example`.

## Honest limits

- The calibration data only exists for patterns (re)discovered after this
  change; existing DB patterns carry no `benchmark_regime_outcomes` and keep
  heuristic scoring. No backfill is fabricated.
- Buckets are calibrated from research sample simulations (canonical
  triple-barrier at next-bar open, zero-cost variant via best-RR), not from
  real fills; real-fill regime attribution stays future work once enough
  labeled paper fills exist per bucket.
- The hard gate ships disabled. Enabling it is a Director-level decision
  once rediscovered patterns populate calibrated buckets.

## Files Changed

- `backend/tradeo/services/market_regime.py`
- `backend/tradeo/research/cluster_research_engine.py`
- `backend/tradeo/agents/pattern_discovery_lab_agent.py`
- `backend/tradeo/research/novel_pattern_matcher.py`
- `backend/tradeo/core/config.py`
- `.env.example`
- `backend/tradeo/tests/test_regime_outcome_calibration.py`
- `docs/remediation/agent_i_regime_outcome_calibration_2026_06_11.md`
- `docs/remediation/tradeo_12_phase_compliance_matrix_2026_06_10.md`

## Tests Run

- `pytest /app/tradeo/tests/test_regime_outcome_calibration.py -q` in
  `tradeo-backend:latest` (worktree mounted read-only) → **11 passed**
- Full backend suite in the same image → **278 passed, 4 skipped**
- `ruff check /app/tradeo` → clean

New tests (11) cover: PIT date→regime_key mapping including the
before-history unlabeled key, empty/missing-table degradation,
period-string parsing, warmup-inclusive `history_table` fetch with config
attrs, per-bucket outcome aggregation (sign + win rate + labeled/unlabeled
counts), `available:false` without a table, calibrated positive/negative
fits with calibration evidence, fallback when the bucket is too small, when
the benchmark regime is unlabeled, and when no settings are passed (legacy
call shape).

## Risks

- Match scores can change for newly discovered patterns once their buckets
  reach `min_samples`: a calibrated-positive bucket scores ≥0.75 where the
  heuristic gave 0.85 for mere presence; a calibrated-negative bucket drops
  to 0.2. Regime fit is 8% of the final match score, so drift is bounded;
  the hard filter itself stays off by default.
- `history_table` adds one daily benchmark fetch per discovery run, served
  by the existing OHLCV cache (incremental tail refresh on the daily feed).
- No execution-path, sizing, gate-threshold, or live-trading flags touched.

## Next Step Recommended

Once rediscovered patterns populate calibrated buckets, attribute real
paper-fill outcomes (`benchmark_regime` is already on every stored match)
into the same bucket schema and let the Director compare research-simulated
vs realized per-regime expectancy before enabling the hard gate.
