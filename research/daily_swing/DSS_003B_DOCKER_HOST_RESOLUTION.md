# DSS-003B Docker Host Resolution

Generated: 2026-07-04 09:41 UTC.

## Checks

- Host shell: `getent hosts host.docker.internal` returned no address.
- Host Python DNS probe: `host.docker.internal:7497` returned `DNS_FAIL`.
- Compose backend check could not run from this worktree because `.env` is absent, and DSS-003B must not modify real `.env`.
- Temporary Docker check with `--add-host=host.docker.internal:host-gateway` resolved `host.docker.internal` to `172.17.0.1`.

## Repository State

The current `docker-compose.yml` already contains:

- `backend.extra_hosts: ["host.docker.internal:host-gateway"]`
- `worker.extra_hosts: ["host.docker.internal:host-gateway"]`

For explicit local runs, DSS-003B also adds the safe, inactive example file:

- `docker-compose.ibkr-local.override.example.yml`

## How To Use The Example

If Asier needs to run with a compose file that lacks this mapping, use:

```bash
docker compose -f docker-compose.yml -f docker-compose.ibkr-local.override.example.yml up -d backend
```

No active compose configuration was changed by this task.
