# LAB_DAILY_RESOURCE_001 Context Sync

Date: 2026-07-06
Branch: `feature/lab-daily-resource-001`
Worktree: `/tmp/tradeo-lab-daily-resource-001`
Base: `origin/main` at `f47b769`

## Existing Relevant Modules

- FastAPI app: `backend/tradeo/main.py` includes routers under `/api`.
- Existing operational routers: `laboratory`, `fox_hunter`, `intraday`, `research`, `ibkr`.
- Daily research modules: `backend/tradeo/modules/daily_swing/*`.
- Lab/Fox order-adjacent path: `backend/tradeo/modules/shared/entry_scanner.py` and `backend/tradeo/services/ibkr_broker.py`.
- Intraday queue/scheduler: `backend/tradeo/modules/intraday/work_queue.py`, `backend/tradeo/tasks/worker.py`.
- Frontend: `frontend/app/page.tsx`, proxied via `frontend/app/api/tradeo/[...path]/route.ts`.

## Integration Points

- Resource policy: new `backend/tradeo/modules/resource_policy/`.
- Daily watchlist: new `backend/tradeo/modules/daily_swing/setup_watchlist.py`.
- Fast engine ownership: new `backend/tradeo/modules/fast_chart_analysis/engine_registry.py`.
- Read-only APIs: `backend/tradeo/routers/resource_policy.py`, `backend/tradeo/routers/daily.py`.
- UI: passive Lab Daily watchlist contract panel.

## Dangerous Routes

- `/api/ibkr/*` submit paths.
- `/api/laboratory/scan` and `/api/fox-hunter/scan` because they can pass `execute_orders`.
- Shared entry scanner and `IBKRBroker.submit_signal_bracket`.
- Any status that could be interpreted as `paper_candidate`, `live_candidate`, or FoxHunter promotion.

## Assumptions

- No live/paper orders are authorized by this task.
- Resource policy may write runtime status artifacts but runtime artifacts are ignored by git.
- Daily watchlist is metadata only; Lab Paper Probe must still run its own gates.
- Frontend addition can be a read-only placeholder/contract panel.

## Unknowns

- Full CI environment was not present in the parent shell (`pytest`, `ruff`, pydantic, frontend node_modules missing).
- Existing `.env.example` still contains paper auto-submit defaults inherited from main; this task did not modify operational order defaults.
