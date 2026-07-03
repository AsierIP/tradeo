# Lab Paper Readiness

T-LAB-002 adds dry-run Paper readiness checks. It does not activate Paper, does
not submit orders, and does not import broker adapters.

## Shadow Batch

```bash
python3 scripts/run_vwap_shadow_batch.py \
  --symbols AAPL,MSFT,NVDA \
  --vwap-condition vwap_reclaim_long \
  --side long \
  --timeframe 1m \
  --jsonl-out artifacts/runtime/lab_shadow/shadow_events.jsonl \
  --summary-json artifacts/runtime/lab_shadow/shadow_batch_summary.json \
  --summary-md artifacts/runtime/lab_shadow/shadow_batch_summary.md
```

The batch runner appends JSONL records and writes a JSON/Markdown summary. It
uses the T-LAB-001 recorder and keeps `orders_allowed=false`,
`paper_allowed=false`, `live_allowed=false`, and `submit_order_called=false`.

## Paper Readiness

```bash
python3 scripts/check_lab_paper_readiness.py \
  --json-out artifacts/runtime/lab_shadow/paper_readiness.json \
  --md-out artifacts/runtime/lab_shadow/paper_readiness.md
```

Possible outcomes:

- `READY_FOR_DIRECTOR_PAPER_REVIEW`
- `BLOCKED`
- `NOT_READY`

The check blocks live mode, live flags, market orders, Paper auto-submit, Fox
Hunter live auto-submit, and `TRADEO_IBKR_READONLY=false`. It reports configured
limits and emits a bracket preview with `dry_run_only=true` and
`submit_allowed=false`.

T-LAB-002 can only recommend Director review for T-LAB-003. It cannot activate
Paper or send Paper orders.
