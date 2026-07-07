# Daily Universe v2 Audit

Generated: 2026-07-07

## Result

Status: `LOCAL_PROXY_BUILD_READY`

The v2 builder is deterministic and local-only. It uses either a provided local seed CSV or the module's built-in proxy seed. No network refresh, provider call, broker scan, paper/live path, order path, or scheduler path is used.

## Bucket Coverage

The default build covers all required buckets:

- `mega_large_cap`
- `large_cap_core`
- `liquid_mid_cap`
- `liquid_small_cap`
- `high_beta_growth`
- `defensive_quality`
- `sector_leaders`
- `etf_macro`

ETF enforcement is explicit: ETF rows outside `etf_macro` are rejected, and stock rows inside `etf_macro` are rejected.

Low-liquidity enforcement is explicit for `liquid_small_cap`: proxy rows below the bucket liquidity threshold are rejected with `low_liquidity_smallcap_requires_warning`.

The bucket summary JSON records `required_buckets`, `missing_required_buckets`,
selected-by-bucket counts, and the point-in-time/proxy warning contract under
`metadata`; each bucket summary row carries the proxy source, method, and
survivorship warning.

## Point-In-Time Market Cap

No point-in-time market-cap source is available in the repo for this task. The builder and reports therefore mark:

- source: `unavailable`
- method: `proxy`
- market-cap bucket method: `proxy`
- survivorship warning: `true`

This is intentional and required until a verified PIT source is supplied.

## Runtime Hygiene

Runtime output path: `artifacts/runtime/daily_swing/universe_daily_swing_v2.csv`

The repository already ignores `artifacts/` and `artifacts/runtime/`, so the runtime CSV remains local and untracked.

## Residual Risk

The universe is a proxy research universe, not a point-in-time reconstructed investable universe. It is suitable for deterministic plumbing, bucket routing, and audit validation, but it should not be used as evidence that historical constituents or market-cap tiers were available at a past date.
