# Agent C Design - API / Frontend Contract

## Objective

Expose read-only status surfaces for resource policy and Daily watchlist, plus a passive frontend contract panel.

## Files

- `backend/tradeo/routers/resource_policy.py`
- `backend/tradeo/routers/daily.py`
- `backend/tradeo/main.py`
- `frontend/app/page.tsx`
- API contract tests.

## Contracts

- `GET /api/resource-policy/status`
- `GET /api/daily/setup-watchlist`
- `GET /api/daily/setup-watchlist/{setup_id}`
- `GET /api/daily/setup-watchlist/summary`
- optional `GET /api/daily/setup-watchlist/status` and `/contract` aliases.

## Risks

- Accidental POST/write endpoint.
- UI implying execution.
- Secrets in runtime artifacts.

## Tests

- GET endpoints require admin, are read-only, and block order resources.
- POST `/api/daily/setup-watchlist` returns 405.
- Frontend has no action button for watchlist rows.

## Fail-Safe

Endpoint contract declares allowed methods `GET` only and all order/promotion permissions false.
