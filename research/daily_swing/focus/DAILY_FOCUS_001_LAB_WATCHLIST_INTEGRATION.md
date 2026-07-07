# DAILY_FOCUS_001 Lab Watchlist Integration

Task: `T-DAILY-FOCUS-UNIVERSE-001 Agent D`

Date: 2026-07-07

## Scope

Integrated Daily Setup Watchlist records with Daily Focus Universe / Lab Paper Probe metadata. The change is metadata-only and keeps the Daily watchlist read-only.

Touched backend surface:

- `backend/tradeo/modules/daily_swing/setup_watchlist.py`
- `backend/tradeo/tests/test_daily_setup_watchlist.py`

## Metadata Contract

Daily setup records and Lab Paper Probe request metadata now validate and expose:

- `universe_bucket`
- `bucket_reason`
- `bucket_version`
- `pattern_family`
- `lab_probe_allowed`
- `lab_probe_id` when the metadata route is applicable
- `route_to_lab_reason`
- `bucket_specific_gate_status`

`bucket_specific_gate_status` is constrained to `pass`, `pending`, `blocked`, or `unknown`. Bucket, version, family, and probe identifiers are normalized to compact safe tokens. Invalid gate statuses fail validation.

## Routing Behavior

`entry_ready` records can carry a Lab Paper Probe metadata route only when:

- the setup status is `entry_ready`;
- `daily_setup_route_entry_ready_to_lab` is enabled;
- the bucket-specific gate status is `pass`.

When those conditions pass, `lab_probe_allowed=true` and a deterministic `lab_probe_id` is attached. This is not paper approval and does not authorize submit. If the route is disabled or the bucket gate does not pass, the record keeps `lab_probe_allowed=false` and `lab_probe_id=null` with a denial reason.

## Safety

Confirmed unchanged safety posture:

- no orders;
- no paper orders;
- no live orders;
- no broker submit;
- no FoxHunter auto-promotion;
- no timers, cron, or scheduler changes;
- `entry_ready` remains watchlist metadata only;
- Lab Paper Probe request payloads still set `submits_order=false`, `orders_allowed=false`, `paper_allowed=false`, and `live_allowed=false`.

## Validation

- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_daily_setup_watchlist.py` -> 20 passed, 1 existing Starlette/httpx deprecation warning.
- `backend/.venv/bin/ruff check backend/tradeo/modules/daily_swing/setup_watchlist.py backend/tradeo/tests/test_daily_setup_watchlist.py` -> passed.
- `backend/.venv/bin/python -m pytest backend/tradeo/tests/test_lab_daily_resource_004_red_team.py backend/tradeo/tests/test_daily_resource_api_contract.py` -> 18 passed, 1 existing Starlette/httpx deprecation warning.

Initial host attempts using `python` and `python3 -m pytest` failed because the host shim/module was unavailable; validation was rerun successfully through `backend/.venv`.

## Blockers

None.
