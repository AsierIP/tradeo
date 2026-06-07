# Tradeo Periodic Audit Tasks

## Purpose

This file defines the standing audit cadence for Tradeo. It separates automatic checks, Claw/Codex maintenance, the Internal Daily Auditor, and ChatGPT Director review.

## Always-on checks

| Cadence | Owner | Task | Command / Output | Blocking rule |
|---|---|---|---|---|
| Every audit export | Claw/Codex or worker | Validate package schema | `python research/audit_bridge/validate_audit_package.py research/audit_bridge/requests/<audit_id>` | Invalid packages block review. |
| Every audit export | Internal Daily Auditor | Run Director gate | `python research/audit_bridge/director_gate.py research/audit_bridge/requests/<audit_id>` | Gate BLOCKED means no promotion. |
| Every audit export | Internal Daily Auditor | Write machine-readable result | `director_gate_result.json`, `director_gate_result.md` | Missing result blocks promotion. |

## Daily tasks

| Time UTC | Owner | Task | Expected output |
|---:|---|---|---|
| 21:35 | Internal Daily Auditor | Export latest package and run deterministic audit | `director_audit_run.json`, `internal_auditor_agent_review.md` |
| 21:45 | Claw/Codex | Review P0/P1 blockers from daily run | Task update or fix PR if needed |
| 22:00 | ChatGPT Director | Review daily summary only if P0 or new execution evidence exists | Direction for Claw/Codex |

## Weekly tasks

| Time UTC | Owner | Task | Expected output |
|---:|---|---|---|
| Sunday 22:15 | Internal Daily Auditor | Generate weekly Director packet | weekly audit package / summary |
| Sunday after packet | ChatGPT Director | Perform large audit and decide math/code changes | Director response + tasks + PR review |
| Monday 08:00 | Claw/Codex | Implement Director-ordered fixes | PR or status report |

## ChatGPT Director recurring task

```text
Every Sunday after the weekly audit packet exists:
1. Review the week’s packages, daily summaries, Director gate results and blockers.
2. Decide whether the mathematical model, clustering, scoring, OOS split, cost model, or code must change.
3. Create or review PRs for process improvements.
4. Do not approve paper/live promotion unless the gate passes and paper/fill evidence exists.
```

## Claw/Codex recurring task

```text
Every day after the audit run:
1. Check director_gate_result.json.
2. Fix P0/P1 blockers first.
3. Do not promote patterns when the package is Director-gate-blocked.
4. Keep discovery running only as research/watchlist.
5. Prepare PRs for export, validator, and research-model improvements.
```

## Manual emergency audit triggers

Run a Director audit immediately if any of these happens:

```text
- a pattern appears exceptionally strong
- any pattern is proposed for paper_candidate or stronger
- paper fills are ingested
- detector code changes
- universe file changes
- IBKR provider or execution logic changes
- data errors spike
- duplicate samples spike
- OOS collapses relative to in-sample
```

## Commands

```bash
# Full automated run
python research/audit_bridge/run_director_audit.py --cadence daily

# Weekly Director packet
python research/audit_bridge/run_director_audit.py --cadence weekly

# Gate an existing package
python research/audit_bridge/run_director_audit.py --cadence manual --audit-id <audit_id> --skip-export
```
