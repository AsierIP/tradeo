# LAB_FOXHUNTER_001 Gate Criteria

## Research To Lab

Allows `lab_paper_probe` only when lookahead, leakage, product policy, data quality, documentation, operational risk, reproducibility, and Direction approval are clean. It blocks fatal failure reasons and live risk.

## Lab To FoxHunter

Minimums:

- `paper_trades_count >= 20`
- `success_count >= 12`
- `expectancy_net > 0`
- `profit_factor > 1.15`
- drawdown within configured limit
- zero operational errors
- zero reconciliation errors
- no symbol/event concentration
- no manual overrides
- complete logs
- Direction approval

The only passing decision is `eligible_for_foxhunter_review`; it is not live approval.

## FoxHunter To Live

Requires FoxHunter review, risk review, kill-switch proof, risk limits, paper/live account separation, human review, and explicit Asier plus Direction authorization. The gate check must not arm live.
