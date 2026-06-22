# Security Notes

Do not distribute `.env` or runtime artifacts. Use `.env.example` for documented keys and inject real secrets through the deployment environment.

If a package containing `.env`, account identifiers, tokens, passwords, API keys, or broker credentials was shared outside the trusted machine, rotate those secrets before enabling paper/live execution.

Codex bundles should be produced with:

```bash
bash scripts/make_codex_bundle.sh --dry-run
```

Validate bundles with:

```bash
python3 scripts/check_bundle_no_secrets.py dist/tradeo_codex_bundle.zip
```
