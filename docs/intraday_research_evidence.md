# Intraday Research Evidence Capture

Research Evidence Capture is a read-only artifact layer for intraday research diagnostics. It stores bounded JSONL evidence per run and candidate so later forensics can explain failures by symbol, timestamp, month, session bucket, and sample outcome.

## Scope

- No waves are launched by this module.
- No IBKR, paper, live, orders, order code, gates, or scoring changes are touched.
- The writer is disabled unless explicitly constructed with `enabled=True`.
- Missing fields are recorded as `null` or `unknown`; data is never invented.

## Files

- `backend/tradeo/research/intraday_research_evidence.py`
- `scripts/summarize_intraday_research_evidence.py`
- `backend/tradeo/tests/test_intraday_research_evidence.py`

## Output

When enabled, records are written under:

```text
artifacts/runtime/research_evidence/run_<run_id>/candidate_<candidate_key>.jsonl
artifacts/runtime/research_evidence/run_<run_id>/manifest.json
```

Limits default to 50 candidates per run and 300 samples per candidate.

## Integration Point

The safest integration point is after `ClusterResearchEngine._cluster_window_size` builds each `ClusterCandidate`, while `cluster_samples`, `cluster_train_samples`, `cluster_holdout_samples`, selected `side`, `best_rr`, `window_size`, and `cluster_id` are all still in memory. That location has symbol, window start/end, forward returns, forward path, and split information before registry persistence.

Registry persistence lives in `NovelPatternRegistry.store_candidates`; it is useful for accepted/rejected candidate persistence, but it only stores compact examples and metrics, not full sample evidence.

## CLI

```bash
python3 scripts/summarize_intraday_research_evidence.py \
  --evidence-dir artifacts/runtime/research_evidence \
  --json-out artifacts/runtime/research_evidence/_summary.json \
  --md-out artifacts/runtime/research_evidence/_summary.md
```

The summarizer works on fake JSONL evidence and does not require a database.
