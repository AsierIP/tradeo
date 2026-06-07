# Task: 2026-06-07_claw_merge_redeploy_director_audit_automation

## From

ChatGPT Director

## To

Claw/Codex Researcher

## Priority

`P0`

## Goal

Resolve conflicts, merge the Director audit automation PR, update the local deployment, and redeploy all services so the new audit loop is available as soon as possible.

## Context

This PR adds the automated Director audit runner, machine-readable Director gate outputs, an internal daily auditor skill, and standing periodic task definitions. The goal is to move from manual audit discipline to repeatable daily/weekly audit operations.

## Actions

1. Fetch the PR branch and check for conflicts:
   ```bash
   git fetch origin
   git checkout main
   git pull --ff-only origin main
   git checkout automation/director-audit-loop
   git rebase main
   ```
2. Resolve conflicts if any.
3. Run validation:
   ```bash
   python research/audit_bridge/run_director_audit.py --cadence manual --audit-id 2026-06-07_ib_paper_patterns --skip-export
   python research/audit_bridge/validate_audit_package.py research/audit_bridge/requests/2026-06-07_ib_paper_patterns
   python research/audit_bridge/director_gate.py research/audit_bridge/requests/2026-06-07_ib_paper_patterns
   ```
   The current package is expected to be Director-gate-blocked, not approved.
4. Merge the PR after checks are acceptable.
5. Update local:
   ```bash
   git checkout main
   git pull --ff-only origin main
   ```
6. Rebuild and redeploy:
   ```bash
   docker compose build --no-cache backend worker frontend
   docker compose up -d --remove-orphans
   docker compose ps
   ```
7. Smoke-test services:
   ```bash
   curl -fsS http://localhost:8000/api/health
   curl -fsS http://localhost:8000/api/health/deep
   curl -fsS http://localhost:8000/api/health/ibkr || true
   ```
8. Run one audit manually after redeploy:
   ```bash
   docker compose exec worker python research/audit_bridge/run_director_audit.py --cadence daily
   ```

## Acceptance criteria

- PR is merged or explicitly blocked with reason.
- Local `main` contains the merged changes.
- Docker services are rebuilt and running.
- Manual Director audit run produces:
  - `director_gate_result.json`
  - `director_gate_result.md`
  - `internal_auditor_agent_review.json`
  - `internal_auditor_agent_review.md`
  - `director_audit_run.json`
  - `director_audit_run.md`
- No live trading configuration is changed.
- No pattern is promoted from a blocked package.

## Response format

- Estado: OK / BLOCKED / NEEDS_HUMAN
- Rama:
- PR:
- Commits:
- Conflictos:
- Validaciones ejecutadas:
- Redeploy:
- Health checks:
- Riesgos:
- Siguiente paso recomendado:
