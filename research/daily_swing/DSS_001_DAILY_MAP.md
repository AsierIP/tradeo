# DSS-001 Daily Map

Daily-specific production code was not present as a standalone module before this branch. The repo is primarily intraday/research oriented, with reusable broker, backtester, indicator and safety components.

Key decision: add `backend/tradeo/modules/daily_swing/` as the bounded Daily Swing paper-probe surface. It is preview-only by default and treats IBKR execution as blocked until paper safety flags and kill-switch pass.

Generated preview spec hash: `d67278d4ba55b02b6cb9532995ed12973b8bba8e1ed322ea14ebf68d1fa3f823`.
