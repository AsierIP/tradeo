# DSS-004J PR Handoff

Task: T-DAILY-SWING-004J

Compare URL:
https://github.com/AsierIP/tradeo/compare/main...feature/daily-research-infra-clean-001

Suggested PR title:

```text
Daily research infrastructure and terminal negative findings
```

Suggested PR body:

```markdown
## Summary

Adds Daily research infrastructure only.

This PR introduces reusable Daily research tooling:
- Daily OHLCV cache/readiness/quality tooling.
- Safe IBKR read-only diagnostics and cache resume/quarantine/caps.
- Daily research/backtest infrastructure.
- No-lookahead ledger guards.
- Bias, placebo, baseline, episode, effective-sample and FDR/WRC/SPA-light research tooling.
- Sanitized terminal Daily research documentation.

## Terminal research result

Daily Swing research did not produce an approved trading candidate.

Final candidate status:
- DSS-PB-001: rejected, OOS/cost failure.
- DSS-BO-001: rejected as independent pattern, baseline explained.
- DSS-CO-001: research warning, timing/window issue.
- DSS-CW-001: rejected as current operational specification, timing not specific.

No Daily pattern is approved as:
- shadow_candidate
- paper_candidate
- live_candidate

## Trading safety

This PR does not enable:
- paper trading
- live trading
- cron trading
- operational signals
- order submission
- order preview execution

Runtime artifacts, OHLCV caches, memory files, paper previews, audit bundles and sensitive/generated data are intentionally excluded.

## Validation

- Security/data/artifact audit: passed
- py_compile: passed
- pytest Daily focal: passed
- ruff: passed
- git diff --check: passed
- docker build backend: passed

## Residual risks

- Daily has no approved operational candidate.
- WRC/SPA remains light/approximate, not formal.
- No Daily candidate currently has stop/R and portfolio-normalized drawdown.
- Future paper requires a new approved research line and explicit Direction approval.
```

Validation checklist:
- Security/data/artifact audit: PASS.
- py_compile: PASS.
- Daily focal pytest: PASS, 113 tests.
- ruff branch Python files: PASS.
- git diff checks: PASS.
- Docker backend build: PASS.

Safety checklist:
- No orders.
- No paper orders.
- No live orders.
- No IBKR operation.
- No operational signals.
- No order preview execution.
- No cron change.
- No data download.
- No merge to main.
- No `gh`.

Decision: DSS_004J_PR_HANDOFF_READY
