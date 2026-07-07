# T-POSTSESSION-IMPROVEMENT-001 Env Safety

## Result

Decision: `ENV_HARDENED`.

The real `/home/vboxuser/tradeo/.env` was checked without printing secrets. The two authorized safety flags were unsafe and were changed only to the approved safe values:

- `TRADEO_IBKR_READONLY`: `false` -> `true`
- `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS`: `true` -> `false`

Backup created:

- `/home/vboxuser/tradeo/.env.backup.20260707T224236.postsession-safety`

No credentials, account identifiers, limits, ports, tokens, or unrelated settings were changed or printed.

## Redacted Diff

```diff
- TRADEO_IBKR_READONLY=false
+ TRADEO_IBKR_READONLY=true
- TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true
+ TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false
```

## Current Check

- `TRADEO_IBKR_READONLY`: `SAFE`
- `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS`: `SAFE`

