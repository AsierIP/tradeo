# DSS-GAP-002A Cache Discovery

Decision: CACHE_CANDIDATE_FOUND.

Scope: local-only inspection. No IBKR, no downloads, no backtest, no signals, no preview, no orders.

Best cache candidate:

- Path: `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001/artifacts/runtime/daily_swing/daily_ohlcv_research`
- Format: CSV per symbol.
- CSV files: 152.
- Approx size: 13M.
- Contains SPY: yes.
- Contains QQQ: yes.
- Sample symbols: AAON, AAPL, ABBV, ABNB, ACMR, ADBE, ADI, ADP, AEO, ALGM, AMAT, AMBA.
- Modified at: 2026-07-04T17:02:17+02:00.
- Selected reason: matches the GAP-002 approved `daily_ohlcv_research` input path and contains research-150 plus SPY/QQQ benchmarks.

Other local candidates:

- `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001/artifacts/runtime/daily_swing/daily_ohlcv`: 52 CSV files, 4.2M, SPY/QQQ present, pilot-sized.
- `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001/artifacts/runtime/daily_swing/daily_ohlcv_mini`: 2 CSV files, 172K, SPY/QQQ absent, unsuitable.

Universe selected:

- Path: `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001/artifacts/runtime/daily_swing/dss_003e_research_universe_checked.csv`
- Rows: 152.
- Operational symbols: 150.
- Benchmarks: 2.
- Selected reason: matches the GAP-002 approved universe file and pairs with the selected research cache.

