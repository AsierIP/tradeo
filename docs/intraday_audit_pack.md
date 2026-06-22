# Intraday Audit Pack

The intraday audit pack is a redacted, reproducible manifest for a session or dry run. It must include:

- effective intraday config keys without secret values;
- git branch/commit provenance without local path disclosure;
- schema and code hashes;
- executable test commands and targeted intraday test files;
- static summaries of intraday modules and integration points;
- session status, pacing metrics, risk ledger summary, flat status, and reason codes when available;
- explicit labels for `shadow`, `paper`, and `live`.

It must not include `.env`, account numbers, tokens, passwords, broker credentials, raw logs with secrets, DB dumps, or runtime caches.
Generation fails if emitted values match common credential patterns or sensitive keys are not redacted.

Generate dry-run:

```bash
python3 scripts/build_intraday_audit_pack.py --dry-run
```
