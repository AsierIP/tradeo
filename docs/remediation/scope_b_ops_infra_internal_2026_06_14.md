# Scope B Ops/Infra Internal Remediation (2026-06-14)

Branch: `codex-scope-b-infra-20260614`

## Implemented

- Internal ops alerting:
  - Scheduler job failures and APScheduler missed/error events persist
    `audit_logs.action = internal_ops_alert`.
  - Watchdog stale-run repairs still mark runs failed, and now also emit an
    internal warning alert in the same DB transaction.
  - No webhook, email, public post, vendor API or live-trading side effect was
    added.
- PostgreSQL-aware backup:
  - `ops/scripts/backup_tradeo.sh` still produces the file/archive backup.
  - When `pg_dump` and `TRADEO_DATABASE_URL` are available, it adds a custom
    PostgreSQL dump to the archive.
  - `TRADEO_BACKUP_POSTGRES=required` fails closed if the database dump cannot
    be produced.
- FastAPI IBKR route hardening:
  - `/api/ibkr/*` endpoints are now `async` and explicitly offload blocking
    IBKR work via `run_in_threadpool`.
  - DB-backed signal preview/submit helpers create and close their SQLAlchemy
    session inside the worker thread to avoid sharing a session across threads.
  - Safety gates keep returning HTTP 409; broker/API failures keep returning
    HTTP 502.
- IBKR exception boundary:
  - Data-provider connection failures are wrapped as
    `IBKRDataConnectionError`.
  - Broker connection failures are wrapped as `IBKROperationalError`.
  - The remaining broad catches are constrained to the ib-insync boundary,
    where the library raises heterogeneous runtime exceptions.
- False-match/drift metrics job and CLI:
  - `tradeo-false-match-metrics` summarizes persisted
    `fpr_at_recall90`, temporal harness metrics and drift status from the
    local DB.
  - Worker schedules a nightly `false_match_drift_metrics` job, which writes
    `false_match_drift_metrics_report` and raises an internal alert if high
    FPR or drift thresholds are exceeded.
- Daily cache freshness hardening:
  - Incremental daily refresh now counts completed business days rather than
    calendar days, so a Friday cache is not treated as stale on Sunday when no
    completed daily bar exists.

## External Dependencies Not Implemented

- PIT/delisting universe data still requires a licensed data source.
- Richer real-time microstructure feed remains blocked on an available feed.
- Live IBKR verification was not run and no live-trading flag was changed.

## Verification

- `ruff check .`
- Targeted pytest:
  - `tradeo/tests/test_watchdog.py`
  - `tradeo/tests/test_ops_alerts.py`
  - `tradeo/tests/test_false_match_metrics_cli.py`
  - `tradeo/tests/test_ibkr_router_threadpool.py`
  - `tradeo/tests/test_backup_script.py`
- Full backend suite: `373 passed, 1 skipped`.
