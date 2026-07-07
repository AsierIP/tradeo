# Daily Universe v2 Protocol

Generated: 2026-07-07

## Scope

Daily Universe v2 builds a deterministic, local-only focus universe for daily swing research. It does not fetch market data, scan brokers, call IBKR, place orders, create signals, or promote paper/live candidates.

## Required Buckets

- `mega_large_cap`
- `large_cap_core`
- `liquid_mid_cap`
- `liquid_small_cap`
- `high_beta_growth`
- `defensive_quality`
- `sector_leaders`
- `etf_macro`

ETFs are valid only in `etf_macro`. Common stocks and ADR-like equity rows are valid only in the non-ETF buckets.

## Market-Cap Rule

The repo does not provide a verified point-in-time market-cap source for this builder. Until such a source is supplied, every build must mark:

- `market_cap_source`: `unavailable`
- `market_cap_method` / `market_cap_bucket_method`: `proxy`
- `survivorship_warning`: `true`

The bucket labels are therefore research proxies, not point-in-time investable market-cap claims.

## Outputs

- Runtime CSV: `artifacts/runtime/daily_swing/universe_daily_swing_v2.csv`
- Bucket summary CSV: `research/daily_swing/universe/daily_universe_v2_bucket_summary.csv`
- Bucket summary JSON: `research/daily_swing/universe/daily_universe_v2_bucket_summary.json`

The bucket summary JSON keeps `required_buckets`, `missing_required_buckets`,
selected counts, and `market_cap_point_in_time` under `metadata`.

`artifacts/runtime/` is ignored by git; the runtime CSV is a local artifact only.

## Required Runtime Fields

Rows include bucket-aware metadata for downstream Daily Watchlist/Lab routing:

- `symbol`, `company_name`, `bucket`, `bucket_reason`, `bucket_version`
- `product_class`, `sector`, `market_cap_bucket`, `market_cap_source`
- `market_cap_method`, `market_cap_bucket_method`, `liquidity_bucket`, `avg_dollar_volume_proxy`
- `avg_spread_proxy`, `volatility_bucket`, `beta_proxy`
- `daily_history_rows`, `first_date`, `last_date`
- `eligible_for_daily_swing`, `eligible_for_lab_watchlist`, `eligible_for_research`
- `rejection_reason`, `data_source`, `survivorship_warning`

Low-liquidity `liquid_small_cap` rows are rejected with an explicit warning reason instead of being silently eligible.

## Command

```bash
python scripts/build_daily_swing_universe_v2.py
```

Optional local seed files may be supplied with `--seed-file`. Seed files must include `symbol`; rows should include a valid `bucket`.
