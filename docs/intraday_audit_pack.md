# Intraday Audit Pack

The intraday audit pack is a redacted, reproducible manifest for a session or dry run. It must include:

- effective intraday config keys without secret values;
- schema and code hashes;
- test command results;
- session status, pacing metrics, risk ledger summary, flat status, and reason codes when available;
- explicit labels for `shadow`, `paper`, and `live`.

It must not include `.env`, account numbers, tokens, passwords, broker credentials, raw logs with secrets, DB dumps, or runtime caches.

Generate dry-run:

```bash
python3 scripts/build_intraday_audit_pack.py --dry-run
```
