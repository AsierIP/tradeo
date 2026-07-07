# T-LAB-DAILY-RESOURCE-004 Red Team

Decision: `RED_TEAM_PASS`

## Scope

This red-team pass targeted rollout breakage around market-session resource policy enforcement, runner gating, read-only Daily setup surfaces, Lab Paper Probe separation, endpoint/UI write exposure, tracked runtime artifacts, and secret/account-id leakage.

Concurrent implementation work was present in the worktree while this pass ran. I did not revert or edit those implementation files; this report validates the state as observed after that wiring was present.

## Test Evidence

Focal command:

```bash
cd backend && .venv/bin/python -m pytest -q tradeo/tests/test_lab_daily_resource_004_red_team.py
```

Result: `14 passed, 1 warning`.

Extended command:

```bash
cd backend && .venv/bin/python -m pytest -q tradeo/tests/test_lab_daily_resource_004_red_team.py tradeo/tests/test_resource_policy_enforcement.py tradeo/tests/test_market_session_resource_policy.py tradeo/tests/test_intraday_worker_jobs.py tradeo/tests/test_intraday_research_wave_runner.py tradeo/tests/test_daily_resource_api_contract.py tradeo/tests/test_daily_setup_watchlist.py
```

Result: `95 passed, 1 warning`.

The warning is the existing Starlette/httpx deprecation warning from `fastapi.testclient`.

## Cases

| Case | Result | Evidence |
| --- | --- | --- |
| `decide_job("paper_submit")` | PASS | Direct budget policy and enforcement wrapper both block paper submit; `can_submit_orders=false`. |
| Direct heavy research during `REGULAR_MARKET` | PASS | `assert_job_allowed(research_heavy, research)` returns blocked with persisted deny reason. |
| Heavy research during `MARKET_CLOSED` | PASS | Enforcement allows with `HIGH` priority and still `can_submit_orders=false`. |
| Worker attempts heavy during RTH | PASS | Worker wrapper blocks before calling the action when policy denies. |
| Capacity runner respects policy | PASS | Static check finds `decide_with_market_session_policy` and `RESEARCH_HEAVY` in capacity runner. |
| Intraday wave runner respects policy | PASS | Static check finds execute-time resource policy gate and blocked manifest path. |
| Daily/gap runners respect policy or wrapper blocks | PASS | Static check finds resource policy gates in both gap dry-run and confirmatory runners. |
| Missing policy | PASS | Enforcement fails closed with `resource_policy_missing`. |
| Unknown session | PASS | Enforcement fails closed with `session_state_unknown`. |
| Deny reason persisted | PASS | `blocked_job_status()` carries `details.resource_policy.deny_reason`. |
| Daily setup `entry_ready` broker call | PASS | Entry-ready artifact and Lab probe request remain non-submitting. |
| Lab Paper Probe own gate | PASS | Lab probe can receive policy priority but paper readiness remains dry-run-only and non-submitting. |
| Resource Policy grants IBKR write | PASS | Even when budget exposes a write flag, paper submit is blocked and cannot be authorized by policy alone. |
| Mixed Daily+Lab metrics | PASS | Daily setup artifact excludes order submission, broker id, live trade, and intraday metric fields. |
| Endpoint POST/write | PASS | Resource policy and Daily setup routes are GET-only; POST returns 405. |
| Heavy admin API bypass | PASS | `/scan`, `/research/run-discovery`, `/research/match-current`, `/research/director/run`, `/backtests/run`, and `/self-improvement/run` contain route policy guards. |
| UI live/submit/FoxHunter button | PASS | Daily Setup panel has no button or `onClick`; it only renders blocked contract flags. |
| Runtime artifacts tracked | PASS | `git ls-files` shows no tracked `artifacts/runtime` paths. |
| Secret/raw account id | PASS | API payloads scanned by the focal test do not expose default password strings or raw broker account-id patterns. |
| Automation timer collision | PASS | Existing intraday registration still uses `max_instances=1`, `coalesce=true`, and jitter; no timers or one-shots were modified. |

## A Inventory Completeness

Agent A inventory is complete for the original core contract: fail-closed session policy, prohibited order resources, API surface, and core policy tests are documented.

For T-004 rollout, the wrapper inventory artifacts now list the current worker, route, script, capacity, intraday, GAP, and Daily Swing enforcement state. Older T-002 enforcement-map artifacts are historical and were not treated as authoritative for this rollout.
