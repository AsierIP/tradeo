# LAB_FOXHUNTER_001 Final Report

## A. Executive Summary

The Lab/FoxHunter promotion framework is defined with a strict Lab to FoxHunter gate and a separate FoxHunter to live gate. This task creates policy, schemas, a pure gate module, a validation CLI, and disabled initial probe proposals. It does not execute paper or live orders.

## B. Real Path Used

`/tmp/tradeo-lab-foxhunter-001`

## C. Branch/Commit/Push

Branch: `feature/lab-foxhunter-gate-001`.

Commit and push are recorded in git history and the task handoff.

## D. New Lab/FoxHunter Taxonomy

- `research_observation`.
- `lab_paper_probe`.
- `foxhunter_candidate`.
- `live_candidate`.

## E. Research to Lab Gate

Implemented in `research_to_lab_gate`. It blocks lookahead, leakage, product policy failures, data quality failures, missing documentation, unclear hypothesis, unbounded operational risk, fatal failure reason, security issues, missing logs, non-reproducibility, live risk, and missing Direccion approval.

## F. Lab to FoxHunter Gate

Implemented in `lab_to_foxhunter_gate`. It requires at least 20 paper trades, at least 12 successes, positive net expectancy, profit factor above 1.15, non-destructive costs/slippage, drawdown inside limit, zero operational and reconciliation errors, no concentration, no degradation, complete logs, no manual overrides, and Direccion approval.

## G. FoxHunter to Live Gate

Implemented in `foxhunter_to_live_gate`. It requires prior FoxHunter eligibility, risk review, tested kill-switch, controlled live arming, max loss/value/trades, paper/live account separation, human review, and explicit Asier/Direccion authorization.

## H. Initial Probes Proposed

- `LAB-GAP-REV-001`, source `GAP003_REVERSAL-SAME-DAY_ABS_3_0_BOTH_ALL`, disabled by default.
- `LAB-GAP-REV-002`, source `GAP003_REVERSAL-SAME-DAY_DESIGN_SPY_LTE_0`, disabled by default.

## I. Telemetry and 20-Trade Metrics

Telemetry and milestone metrics are defined in `LAB_FOXHUNTER_001_GATE_CRITERIA.md` and enforced for lab probe manifests by `validate_lab_paper_probe_manifest`.

## J. Tests/Validation

Validation commands are recorded in the final task response after execution.

## K. Final Decision

`LAB_FOXHUNTER_GATE_READY_NO_EXECUTION`

## L. Safety Confirmation

No live orders, no paper orders, no broker simulated orders, no order previews, no operational signals, no IBKR operational use, no data downloads, no cron trading, no `.env` changes, no main push, no FoxHunter promotion, and no live promotion are authorized or performed by this task.

## M. Recommended Next Task

`T-LAB-PAPER-PROBE-002 - Enable first supervised paper probe batch, paper-only, max 2 probes, no FoxHunter promotion.`
