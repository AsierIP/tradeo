# DSS-004H Repo Hygiene / Artifact / Security Audit

Generated: 2026-07-04

## Decision

REPO_HYGIENE_BLOCKED_SECRET_OR_DATA

The branch is not ready to open a PR as-is. No confirmed real `.env`, API token, or full live account ID was found, and no live-order activation was found in the inspected Daily surface. However, the branch contains data/privacy and operational-artifact blockers that must be cleaned before PR:

- tracked paper preview artifacts from an earlier Daily paper-probe scaffold:
  - artifacts/runtime/daily_swing/paper_operability_check.json
  - artifacts/runtime/daily_swing/paper_orders_preview_2026-07-06.csv
  - artifacts/runtime/daily_swing/paper_orders_preview_2026-07-06.json
- tracked OpenClaw memory files (`MEMORY.md` and `memory/2026-06-24.md` through `memory/2026-06-28*.md`) containing personal/ops context. They should not live in the app repo.
- ignored generated content is already tracked: `git ls-files -c -i --exclude-standard` found 206 ignored-but-tracked files under ignored artifact/report/data-style paths.
- paper-probe planning/config/code still present in the branch:
  - configs/daily_swing_paper_probe.yaml has `paper_enabled: true`, while `allow_live_orders: false` and `live_armed: false`.
  - scripts/run_daily_swing_paper.py contains an `--execute` flag but the adapter remains intentionally blocked.
  - backend/tradeo/modules/daily_swing/paper_probe.py generates preview artifacts and contains guarded paper-probe language.
- large tracked generated artifacts exist, including audit bridge bundles around 6.6-7.8 MB each, artifacts/runtime/daily_swing/dss_004e_dss_co_001_trades_all_events.csv at about 3.85 MB, reports/TRADEO_FABLE_MAX_AUDIT_PACK.md at about 1.83 MB, and DSS-004F offset timing CSVs at about 1.55 MB each.

These are not proof of unsafe execution. They do mean the branch should not be described as paper-ready and should not open a PR until generated operational artifacts and private memory files are removed or quarantined from git.

## Git State Inputs

- `git status --short --branch`: clean, on `feature/daily-swing-paper-probe-001...origin/feature/daily-swing-paper-probe-001` before DSS-004H files.
- `git diff --name-only main...HEAD`: 382 changed files; 197 are under ignored `artifacts/runtime/`.
- `git ls-files` audit found no tracked `.env`, venv, `__pycache__`, or `.pyc` paths in the Daily-focused match.
- `git ls-files -c -i --exclude-standard`: 206 ignored-but-tracked files.

## Security / Safety Findings

- No real `.env` was tracked in the inspected diff; only `.env.example` and safe example configs appear.
- No confirmed real API token or full account ID was found; matches were placeholders/examples or synthetic IDs.
- No live activation was found in Daily config: `live_armed: false` and `allow_live_orders: false`.
- Safe env example uses `TRADEO_IBKR_READONLY=true` and a simulated `DU_SIMULATED` account placeholder.
- Live IBKR ports are documented as blocked in diagnostics.
- Audit bridge IB fill CSVs are header-only; redacted config files include host/port/client metadata and should be reviewed before merge.
- No PR should claim readiness for live, paper execution, shadow, preview, or signals.

## Artifact Findings

Artifacts useful as small summaries:

- DSS decision JSON files.
- DSS matrix/statistical summary CSV/JSON files.
- DSS-004H terminal matrix and decision artifacts.

Artifacts needing explicit PR policy:

- paper preview artifacts listed above.
- large all-events and offset-timing CSVs.
- runtime artifacts generally, because the branch has historically force-added research outputs.

## Cleanup Required Before PR

1. Untrack generated/ignored content before PR: `artifacts/`, `reports/`, `data/`, `MEMORY.md`, and `memory/`, unless a specific sanitized fixture is intentionally moved to a fixture path.
2. Remove `paper_orders_preview_2026-07-06.*` and `paper_operability_check.json` from git; regenerate locally only when needed.
3. Remove or sanitize audit request bundles under `research/audit_bridge/requests/**`; keep schema fixtures only.
4. Add `MEMORY.md` and `memory/` to `.gitignore` if this repo should never carry agent memory.
5. Decide whether paper-probe scaffold files belong in the PR at all. If this PR is infra-only/negative-findings, either remove paper preview artifacts from the branch or clearly quarantine them outside merge scope.
6. Keep only small sanitized summary artifacts needed to reproduce the terminal reasoning.
7. Ensure the PR title and body state: no paper candidate, no live candidate, no shadow candidate, no operational signal candidate.

## Safety Confirmation

No orders, no paper orders, no live orders, no paper execution, no preview generated in DSS-004H, no operational signals, no IBKR use, no downloads, no cron, no `.env` real modification, no merge, and no `gh`.
