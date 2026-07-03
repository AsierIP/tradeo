# Lab VWAP Shadow Continuous

T-LAB-002B adds a bounded loop wrapper for the read-only VWAP Shadow batch
runner. It is designed for manual or scheduled Shadow capture without Paper,
Live, broker submit, or worker auto-submit.

## Safe Defaults

- `--max-iterations` defaults to `1`.
- `--interval-seconds` defaults to `0`.
- `--conditions` defaults to `vwap_reclaim_long:long,vwap_reject_short:short`.
- Output is written under `artifacts/runtime/lab_shadow/` unless explicit paths
  are provided.
- Every summary keeps `orders_allowed=false`, `paper_allowed=false`,
  `live_allowed=false`, and `submit_order_called=false`.

## Manual Smoke

```bash
python3 scripts/run_vwap_shadow_loop.py \
  --universe-file /home/vboxuser/tradeo/artifacts/runtime/universe_intraday_stock_only_v3.csv \
  --limit 10 \
  --timeframe 1m \
  --max-iterations 1 \
  --conditions vwap_reclaim_long:long,vwap_reject_short:short \
  --jsonl-out artifacts/runtime/lab_shadow/shadow_events_continuous_loop.jsonl \
  --summary-json artifacts/runtime/lab_shadow/shadow_continuous_loop_summary.json \
  --summary-md artifacts/runtime/lab_shadow/shadow_continuous_loop_summary.md
```

Acceptable decisions are `shadow_recorded`, `market_closed`,
`quote_unavailable`, and `blocked_safety`.

Forbidden outcomes are `order_submitted`, `paper_order_submitted`,
`live_order_submitted`, or `submit_order_called=true`.

## Scheduling Recommendation

For T-LAB-002B, run the command manually or through a short-lived scheduler with
an explicit `--max-iterations`. Do not leave an indefinite process running. A
future T-LAB-002C can add a cron or systemd timer after Director reviews the
first continuous smoke artifacts.

## T-LAB-002C Scheduled Wrapper

`scripts/run_lab_shadow_scheduled_once.sh` is a one-shot wrapper for cron or a
systemd timer. It checks the real runtime flags fail-closed before running,
sources `/home/vboxuser/tradeo/.env`, and writes artifacts to
`artifacts/runtime/lab_shadow/` under the code root by default. Override
`TRADEO_SHADOW_OUTPUT_DIR` if a different writable artifact directory is
required.

Recommended cron command:

```bash
flock -n /tmp/tradeo_lab_shadow.lock timeout 120s \
  /home/vboxuser/tradeo-worktrees/director-control-loop-operability/scripts/run_lab_shadow_scheduled_once.sh \
  >> /home/vboxuser/tradeo-worktrees/director-control-loop-operability/artifacts/runtime/lab_shadow/scheduled_shadow_cron.log 2>&1
```

The job must remain one-shot. Keep `TRADEO_SHADOW_MAX_ITERATIONS=1` unless a
future Director task explicitly authorizes longer bounded runs.
