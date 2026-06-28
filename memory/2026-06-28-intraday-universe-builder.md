## 2026-06-28 - Intraday Universe Builder

- User requested a serious intraday Universe Builder before continuing more pattern-search loops.
- Motivation: 15m/W20/30d produced real windows/clusters but no accepted patterns; dominant blockers were symbol diversity, OOS, cost stress and multiple-testing gates. 30m/W20/60d remained unevaluated until cache exists.
- Research/design notes: IBKR scanners can provide contract candidates but no market data fields, so candidates must be re-scored with OHLCV liquidity/quality metrics; historical-data access must be cache-aware and pacing-safe.
- Implemented `backend/tradeo/services/intraday_universe_builder.py`: scored CSV builder with price, median dollar volume, rows, zero-volume, stale-close, spread/range proxy, event-bar return, event-driven keyword rejection, deterministic rotation and bucket caps.
- Implemented `scripts/build_intraday_universe.py` and `scripts/fetch_ibkr_intraday_candidates.py`.
- Added tests in `backend/tradeo/tests/test_intraday_universe_builder.py` and docs in `docs/intraday_universe_builder.md`.
