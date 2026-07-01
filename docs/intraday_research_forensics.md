# Intraday Research Forensics

`analyze_intraday_research_forensics.py` is a read-only analyzer for completed
intraday Research waves. It does not run Discovery, place orders, alter gates,
promote candidates, or touch paper/live execution.

## Purpose

The analyzer explains why near-misses failed after repeated `stock_only`
intraday waves. It uses exact manifests or explicit DiscoveryRun IDs and reports
where the evidence breaks down: cost stress, OOS stability, multiple-testing
checks, drawdown, market replay, adversarial robustness, concentration, and data
availability.

## Usage

```bash
python3 scripts/analyze_intraday_research_forensics.py \
  --wave-manifest artifacts/runtime/intraday_research_wave_bb92b1aafc6b.json \
  --wave-manifest artifacts/runtime/intraday_research_wave_ffe8578057ee.json \
  --wave-manifest artifacts/runtime/intraday_research_wave_7c40c7dcf3cc.json \
  --wave-manifest artifacts/runtime/intraday_research_wave_addf848edbf5.json \
  --wave-manifest artifacts/runtime/intraday_research_wave_94ce92fa9c6a.json \
  --top-candidates 25 \
  --json-out artifacts/runtime/research_forensics/_forensics.json \
  --md-out artifacts/runtime/research_forensics/_forensics.md
```

`--run-ids` is also supported and can be repeated or passed as CSV. The analyzer
intentionally has no `--hours` mode; exact scope is required.

## Output

The JSON/Markdown report includes:

- `scope`: manifests, run IDs, inferred universe/product policy, and
  `exact_scope=true`.
- `wave_summary`: windows, clusters, accepted/rejected counts, persisted
  candidate count, store-rejected visibility, top blockers, and exact rejection
  reasons.
- `candidate_forensics`: top near-misses with metrics, OOS, drawdown, cost x2,
  FDR/WRC/SPA, market replay, adversarial/placebo evidence, and a dominant
  failure class.
- `failure_taxonomy`: aggregated classes such as `cost_dominated`,
  `oos_unstable`, `statistical_datamined`, `drawdown_excessive`,
  `regime_sensitive_candidate`, `concentration_risk`,
  `operationally_unavailable`, and `insufficient_data`.
- `next_hypotheses`: read-only scientific recommendations, not automatic waves.
- `prohibited_repeats`: completed configurations that should not be repeated
  immediately.
- `safety`: all live/paper/order/gate permissions remain false.

## Granularity Limits

The current persisted schema exposes candidate-level metrics, rejection reasons,
run IDs, symbol/sample counts, OOS metrics, drawdown, cost stress evidence,
market replay reasons, adversarial/placebo reasons, and representative examples
when available. It does not consistently expose enough structured event data for
time-of-day, RVOL/gap, SPY/QQQ regime, or month/symbol contribution analysis.
Those fields are reported as `not_available` unless present in the database.
