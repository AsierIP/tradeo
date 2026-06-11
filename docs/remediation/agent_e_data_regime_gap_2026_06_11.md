# Agent E - Data / Universe / Regime / Reproducibility Gap Closure

Date: 2026-06-11
Branch/worktree: `feat/tradeo12-data-regime-gap-20260611` at `/home/vboxuser/tradeo-worktrees/data-regime-gap`
Base: local `main` @ `df418fb` (agents A-D already merged).

## Scope

Single bounded package closing the remaining 3.1 / 3.2 / 3.8 / 7 gaps from the
compliance matrix without touching execution/matcher beyond the minimum
integration point. No live trading paths, no order routing, no secrets.

## Sections Addressed

### 3.8 Market regimes — SPY SMA200 + volatility tercile service (new)

- New `backend/tradeo/services/market_regime.py`:
  - `regime_table(df)`: per-bar benchmark labels. Trend = close vs strict
    SMA200 (full window required; young series report `insufficient_history`
    instead of a fake trend). Volatility = annualized stdev of 20d log
    returns, bucketed into terciles whose boundaries come exclusively from the
    trailing 252 values up to the *previous* bar (shifted), so labels are
    point-in-time and never change when future bars are appended (covered by a
    dedicated stability test).
  - `regime_at(df, as_of)`: snapshot dict with `trend_regime`, `vol_regime`,
    `regime_key` (`benchmark_bull|mid_vol_tercile` style), numeric values,
    tercile bounds, `source_bar_hash` lineage, and honest
    `insufficient_history` labels.
  - `MarketRegimeService`: fetches the benchmark through the (cached) provider
    and degrades to an honest empty regime on provider failure (never blocks a
    scan).
- Minimal matcher integration (`novel_pattern_matcher.py`): one benchmark
  regime snapshot per `match_current` run, attached additively as
  `regime["benchmark_regime"]` on each match and `benchmark_regime` on the run
  result. The per-symbol `regime_key` consumed by throttles/entry scanner is
  untouched, so no behavior change in matching/gating; the SPY regime is
  audit/lineage metadata until calibrated as a gate.
- New settings: `market_regime_benchmark_symbol` (SPY),
  `market_regime_sma_window` (200), `market_regime_vol_window` (20),
  `market_regime_vol_tercile_lookback` (252).

### 3.1 Data layer — true incremental fetch (unblocked within existing signature)

- `CachedMarketDataProvider` now performs an overlap-verified tail merge for
  daily artifacts instead of serving a stale disk cache forever:
  - If the cached last bar is older than `min_gap_days`, it fetches only the
    missing tail (`{gap+overlap}d` period through the *existing*
    `period/interval` provider boundary — no provider signature change needed).
  - The refetched overlap window (default 5 bars) must match cached bars
    (open/close, 1e-4 relative tolerance). Any mismatch — e.g. dividend/split
    re-adjustment of an `ADJUSTED_LAST` feed — forces an honest full refetch
    (`full_refetch_overlap_mismatch`).
  - Gaps beyond `max_gap_days` (45) skip the merge and full-refetch.
  - Metadata now records `incremental_fetch_supported=true` (daily),
    `refresh_mode` (`full_fetch` / `incremental_append` /
    `full_refetch_overlap_mismatch` / `full_refetch_gap_too_large`) and
    `rows_appended`; the data manifest exposes `refresh_mode`,
    `incremental_fetch_supported` and `last_timestamp` per entry.
- New settings: `market_data_incremental_enabled` (true),
  `market_data_incremental_overlap_bars` (5),
  `market_data_incremental_min_gap_days` (1),
  `market_data_incremental_max_gap_days` (45). Knobs are also constructor
  fields so tests/operators can override per instance.

### 3.2 / 7 Universe + reproducibility

- Universe snapshots now carry a deterministic `content_hash` (month, as-of,
  symbols, eligibility rules — excludes `built_at` and absolute paths) so
  bit-for-bit snapshot identity can be asserted across rebuilds.
- Explicit `delisting_data_available` flag (settings-backed, default false)
  in snapshot metadata: PIT/delisting remains **honestly blocked** — there is
  still no licensed delisting/PIT membership source; survivorship flags and
  the `lab_watchlist` cap from Agent A remain the operative mitigation.

## Files Changed

- `backend/tradeo/services/market_regime.py` (new)
- `backend/tradeo/services/data_provider.py`
- `backend/tradeo/services/universe_snapshot.py`
- `backend/tradeo/research/novel_pattern_matcher.py`
- `backend/tradeo/core/config.py`
- `.env.example`
- `backend/tradeo/tests/test_market_regime.py` (new, 11 tests)
- `backend/tradeo/tests/test_data_provider.py` (+5 tests)
- `backend/tradeo/tests/test_pattern_entry_scanner.py` (fetch-count assertion
  updated for the one extra SPY regime fetch per scan)
- `docs/remediation/agent_e_data_regime_gap_2026_06_11.md`
- `docs/remediation/tradeo_12_phase_compliance_matrix_2026_06_10.md` (Agent E rows)

## Tests Run

- `docker run --rm -v "$PWD/backend/tradeo:/app/tradeo:ro" tradeo-backend:latest pytest tradeo/tests -q` → **193 passed** (was 178 before this phase; +15 new, 1 updated).
- `ruff check` on all touched files → passed.
- Host Python lacks pytest/pandas; all verification ran in the
  `tradeo-backend:latest` image with the worktree mounted read-only.

## Remaining Risks / Known Non-Compliance

- **PIT/delisting (3.2): still blocked.** Requires a licensed vendor; flagged
  honestly via `survivorship_biased` + `delisting_data_available=false`.
- The SPY regime snapshot is attached as audit metadata; it is *not* yet a
  hard gate in `_pattern_regime_fit`. Calibrating it as a gate needs labeled
  outcome history per regime bucket (deliberate, to avoid an uncalibrated
  behavior change in match scoring).
- Incremental merge assumes tz-consistent daily indexes (IBKR daily bars are
  date-indexed). Intraday intervals keep the previous cache-forever behavior.
- The regime fetch adds one benchmark request per matcher run (cached
  thereafter); on IBKR outage it degrades to `insufficient_history` rather
  than failing the scan.
- Incremental refresh changes runtime behavior: stale daily caches now
  refresh on first access per process. This is the intended fix (previously a
  disk cache was never refreshed), but operators can disable it via
  `TRADEO_MARKET_DATA_INCREMENTAL_ENABLED=false`.

## Merge Notes

- Conflict surface vs other agents: `core/config.py` (new settings block),
  `.env.example`, `novel_pattern_matcher.py` (3 small additive hunks),
  compliance matrix. No changes to validation gate, risk manager, broker or
  execution paths.
- `test_pattern_entry_scanner.py` change is a single assertion block update;
  if another branch touches the same test, keep both by summing expected
  fetch counts.
- No live-trading defaults changed; provider factory still IBKR-only with
  synthetic data forbidden.
