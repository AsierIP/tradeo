# T-LAB-DAILY-RESOURCE-002 API/UI Hardening

- status: `PASS_WITH_UI_PLACEHOLDER`

## API

- `GET /api/resource-policy/status` remains read-only.
- `GET /api/daily/setup-watchlist` remains read-only.
- `GET /api/daily/setup-watchlist/{setup_id}` remains read-only.
- `GET /api/daily/setup-watchlist/summary` remains read-only.
- POST to Daily setup watchlist returns 405.
- No secrets or raw account identifiers are exposed in contract tests.

## UI

- Frontend panel remains a passive placeholder/contract consumer.
- No live button was added.
- No FoxHunter promotion button was added.
- No order submit UI was added.

## Decision

`UI_PLACEHOLDER_ACCEPTED`
