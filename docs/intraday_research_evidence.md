# Intraday Research Evidence

`scripts/summarize_intraday_research_evidence.py` is a read-only post-run evidence
capture tool for completed intraday research waves. It does not start waves, read
IBKR, submit paper/live orders, change gates, or modify scoring.

## Scope

The tool is fail-closed on scope. Provide at least one exact selector:

```bash
python3 scripts/summarize_intraday_research_evidence.py \
  --wave-manifest artifacts/runtime/intraday_research_wave_xxx.json \
  --json-out artifacts/runtime/research_evidence/_summary.json \
  --md-out artifacts/runtime/research_evidence/_summary.md
```

or:

```bash
python3 scripts/summarize_intraday_research_evidence.py \
  --run-ids 123,124 \
  --top-candidates 25 \
  --json-only
```

Implicit "latest" or recency scopes are intentionally unsupported.

## Artifacts

Default output root:

```text
artifacts/runtime/research_evidence/
```

Generated files:

```text
artifacts/runtime/research_evidence/_summary.json
artifacts/runtime/research_evidence/_summary.md
artifacts/runtime/research_evidence/run_<run_id>/manifest.json
artifacts/runtime/research_evidence/run_<run_id>/candidate_<safe_candidate_key>.jsonl
```

Size controls:

- `--max-candidates`, default `25`
- `--max-samples-per-candidate`, default `500`
- `--max-total-samples`, default `10000`

## Evidence Fields

Each JSONL row attempts to include:

```text
run_id, candidate_key, pattern_key, cluster_id, symbol, timeframe,
window_size, forward_bars, side, window_start_ts, window_end_ts, entry_ts,
exit_ts, entry_price, exit_price, forward_return, outcome_r, split,
cost_base_r, cost_x2_r, hour_of_day, session_bucket, month, source,
rejection_reasons, data_availability
```

Fields absent from the current schema are emitted as `null` or `not_available`
and counted in `missing_fields_summary`.

`hour_of_day`, `month`, and `session_bucket` are derived from `entry_ts` or
`window_end_ts`. Timezone-aware timestamps are converted to `America/New_York`.
Naive timestamps are treated as `America/New_York` and marked with
`timestamp_timezone_assumption`.

Session buckets:

- `open`: 09:30-10:30 New York time
- `mid`: 10:30-15:00 New York time
- `close`: 15:00-16:00 New York time
- `unknown`: missing or outside regular session

## Summary

The summary includes:

- runs, candidates, samples, truncation, missing fields
- stats by symbol, session bucket, month, and split
- top symbol concentration when `outcome_r` is available
- candidate quality flags
- terminal research recommendation
- deterministic content hash
- read-only safety manifest

Allowed terminal recommendations are deliberately narrow:

- `continue_research`
- `change_search_space`
- `candidate_for_shadow_review`
- `research_closed_no_candidate`
- `insufficient_evidence`

The tool never recommends direct paper or live execution.

## Safety

The module reports:

```text
live_allowed=false
paper_allowed=false
orders_allowed=false
broker_allowed=false
gates_allowed=false
scoring_changes_allowed=false
read_only=true
```

It only reads `discovery_runs`, `discovered_patterns`, and
`discovered_pattern_examples`, then writes evidence artifacts under the selected
artifact root.
