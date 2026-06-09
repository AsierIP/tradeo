# Audit Summary For ChatGPT

Generated from the package CSV exports. This is a lab-audit and candidate-ranking aid only.

**Validation stance:** no pattern is approved for operation in this package. Paper/live execution validation is unavailable because `paper_trades.csv` and `ib_fills.csv` have zero rows.

## A. Sample Distribution By Pattern

| metric | value |
|---|---:|
| total patterns | 465 |
| min independent_sample_count | 30 |
| p25 | 70.00 |
| median | 130.00 |
| p75 | 337.00 |
| p90 | 804.20 |
| max | 2289 |
| patterns >= 30 samples | 465 |
| patterns >= 50 samples | 417 |
| patterns >= 100 samples | 283 |
| patterns >= 300 samples | 127 |
| patterns >= 500 samples | 83 |

## B. Top 30 Patterns By Independent Sample Count

| pattern_id | pattern_name | independent_sample_count | event_count | ticker_count | first_seen | last_seen | net_pnl_estimado | profit_factor | max_drawdown | status |
|---|---|---:|---:|---:|---|---|---:|---:|---:|---|
| PATTERN_000398 | DISCOVERED_LONG_W20_C10_23AFD7D8 | 2289 | 2289 | 27 | 2021-11-01T00:00:00+00:00 | 2025-08-05T00:00:00+00:00 | 0 | 1.31738 | 64.95042 | rejected |
| PATTERN_000275 | DISCOVERED_LONG_W20_C06_7A57C575 | 2079 | 2079 | 27 | 2021-07-13T00:00:00+00:00 | 2025-10-13T00:00:00+00:00 | 0 | 1.24157 | 118.48466 | rejected |
| PATTERN_000123 | DISCOVERED_SHORT_W20_C06_A39911C9 | 1982 | 1982 | 20 | 2021-07-26T00:00:00+00:00 | 2025-07-28T00:00:00+00:00 | 0 | 1.0019 | 82.79279 | rejected |
| PATTERN_000374 | DISCOVERED_LONG_W20_C00_659CABD7 | 1967 | 1967 | 27 | 2021-12-06T00:00:00+00:00 | 2025-03-21T00:00:00+00:00 | 0 | 1.25109 | 95.8417 | rejected |
| PATTERN_000216 | DISCOVERED_LONG_W20_C10_BC6A527E | 1933 | 1933 | 24 | 2023-07-11T00:00:00+00:00 | 2025-08-08T00:00:00+00:00 | 0 | 1.23114 | 78.60368 | rejected |
| PATTERN_000023 | DISCOVERED_LONG_W20_C11_A8CF022A | 1839 | 1839 | 27 | 2021-07-21T00:00:00+00:00 | 2025-11-11T00:00:00+00:00 | 0 | 1.27007 | 67.30591 | rejected |
| PATTERN_000377 | DISCOVERED_LONG_W20_C11_08DEA78E | 1615 | 1615 | 27 | 2021-07-13T00:00:00+00:00 | 2026-01-27T00:00:00+00:00 | 0 | 1.28404 | 56.64109 | rejected |
| PATTERN_000273 | DISCOVERED_SHORT_W20_C07_78E7E2B9 | 1607 | 1607 | 27 | 2021-07-13T00:00:00+00:00 | 2024-12-12T00:00:00+00:00 | 0 | 1.18117 | 53.23259 | rejected |
| PATTERN_000403 | DISCOVERED_SHORT_W20_C05_76056E6F | 1524 | 1524 | 27 | 2021-09-20T00:00:00+00:00 | 2024-10-22T00:00:00+00:00 | 0 | 1.16048 | 62.9861 | rejected |
| PATTERN_000036 | DISCOVERED_LONG_W20_C08_85949F07 | 1509 | 1509 | 27 | 2021-12-06T00:00:00+00:00 | 2026-01-30T00:00:00+00:00 | 0 | 1.19554 | 64.89136 | rejected |
| PATTERN_000029 | DISCOVERED_LONG_W20_C08_519EBA3A | 1509 | 1509 | 27 | 2021-12-06T00:00:00+00:00 | 2026-01-30T00:00:00+00:00 | 0 | 1.19554 | 64.89136 | rejected |
| PATTERN_000039 | DISCOVERED_LONG_W20_C08_B8496B30 | 1509 | 1509 | 27 | 2021-12-06T00:00:00+00:00 | 2024-07-29T00:00:00+00:00 | 0 | 0.0 | 0.0 | rejected |
| PATTERN_000408 | DISCOVERED_SHORT_W20_C02_24519BF6 | 1486 | 1486 | 27 | 2023-06-22T00:00:00+00:00 | 2025-12-16T00:00:00+00:00 | 0 | 1.0317 | 38.61455 | rejected |
| PATTERN_000221 | DISCOVERED_SHORT_W20_C07_4C51A243 | 1466 | 1466 | 24 | 2023-09-05T00:00:00+00:00 | 2025-10-08T00:00:00+00:00 | 0 | 1.04664 | 52.0944 | rejected |
| PATTERN_000027 | DISCOVERED_SHORT_W20_C01_326BBE79 | 1441 | 1441 | 27 | 2021-09-28T00:00:00+00:00 | 2025-07-31T00:00:00+00:00 | 0 | 1.14121 | 54.27766 | rejected |
| PATTERN_000407 | DISCOVERED_LONG_W20_C01_3CA3218E | 1427 | 1427 | 27 | 2021-08-24T00:00:00+00:00 | 2026-03-06T00:00:00+00:00 | 0 | 1.20914 | 61.07864 | rejected |
| PATTERN_000269 | DISCOVERED_LONG_W20_C03_70E7C15F | 1413 | 1413 | 27 | 2022-06-21T00:00:00+00:00 | 2024-11-20T00:00:00+00:00 | 0 | 1.39213 | 59.68482 | rejected |
| PATTERN_000117 | DISCOVERED_SHORT_W20_C01_7BDA6ED8 | 1394 | 1394 | 20 | 2023-04-10T00:00:00+00:00 | 2026-04-28T00:00:00+00:00 | 0 | 1.1943 | 61.08213 | rejected |
| PATTERN_000218 | DISCOVERED_LONG_W20_C03_42ABEBEE | 1362 | 1362 | 24 | 2021-07-29T00:00:00+00:00 | 2024-09-05T00:00:00+00:00 | 0 | 1.23451 | 69.99317 | rejected |
| PATTERN_000024 | DISCOVERED_LONG_W20_C04_53B26AF4 | 1357 | 1357 | 27 | 2021-07-29T00:00:00+00:00 | 2025-02-03T00:00:00+00:00 | 0 | 1.33756 | 37.26638 | rejected |
| PATTERN_000037 | DISCOVERED_LONG_W20_C04_92A899D7 | 1357 | 1357 | 27 | 2021-09-01T00:00:00+00:00 | 2025-08-21T00:00:00+00:00 | 0 | 0.0 | 0.0 | rejected |
| PATTERN_000406 | DISCOVERED_LONG_W20_C09_CAF6546E | 1354 | 1354 | 27 | 2021-07-29T00:00:00+00:00 | 2026-04-28T00:00:00+00:00 | 0 | 1.21403 | 64.4129 | rejected |
| PATTERN_000279 | DISCOVERED_LONG_W20_C11_CAAD9849 | 1233 | 1233 | 27 | 2022-02-04T00:00:00+00:00 | 2026-04-07T00:00:00+00:00 | 0 | 1.14099 | 54.58651 | rejected |
| PATTERN_000001 | DISCOVERED_LONG_W20_C05_798BAA44 | 1224 | 1224 | 24 | 2021-07-13T00:00:00+00:00 | 2023-11-15T00:00:00+00:00 | 0 | 1.39154 | 66.06152 | rejected |
| PATTERN_000276 | DISCOVERED_LONG_W20_C01_A2B5CA7A | 1205 | 1205 | 27 | 2021-11-12T00:00:00+00:00 | 2026-01-27T00:00:00+00:00 | 0 | 1.22591 | 71.85983 | rejected |
| PATTERN_000376 | DISCOVERED_SHORT_W20_C07_A7D07551 | 1203 | 1203 | 27 | 2021-08-24T00:00:00+00:00 | 2025-09-17T00:00:00+00:00 | 0 | 1.15056 | 66.12171 | rejected |
| PATTERN_000219 | DISCOVERED_LONG_W20_C04_70DFA8A1 | 1087 | 1087 | 24 | 2021-08-06T00:00:00+00:00 | 2026-04-07T00:00:00+00:00 | 0 | 1.16165 | 60.58271 | rejected |
| PATTERN_000048 | DISCOVERED_LONG_W20_C04_DBC9C574 | 1075 | 1075 | 24 | 2021-07-13T00:00:00+00:00 | 2024-01-26T00:00:00+00:00 | 0 | 1.34551 | 53.64194 | rejected |
| PATTERN_000051 | DISCOVERED_SHORT_W20_C02_76FE4B00 | 1070 | 1070 | 24 | 2021-10-01T00:00:00+00:00 | 2024-09-19T00:00:00+00:00 | 0 | 1.17925 | 35.1384 | rejected |
| PATTERN_000003 | DISCOVERED_LONG_W20_C01_06E08FF8 | 1069 | 1069 | 24 | 2022-10-19T00:00:00+00:00 | 2024-02-16T00:00:00+00:00 | 0 | 1.19737 | 58.25314 | rejected |

## C. Top 30 Patterns By Estimated Net PnL

No available `net_pnl` values. Current package has zero paper trades/fills, so PnL ranking is not actionable.

## D. Concentration

| check | count | notes |
|---|---:|---|
| patterns whose PnL depends on best trade | 0 | Requires non-empty PnL fields. |
| patterns whose PnL depends on top 5 trades | 0 | Requires non-empty PnL fields. |
| patterns concentrated in fewer than 5 tickers | 177 | Based on `metrics_by_pattern.ticker_count`. |
| patterns concentrated in fewer than 5 days | 0 | Based on unique event dates in `pattern_events.csv`. |
| patterns concentrated in one market regime | 465 | Current export mostly uses `not_persisted`; regime audit is limited. |

## E. Automatically Detected Risks

| risk | count | notes |
|---|---:|---|
| possible duplicated event rows | 213 | Counted from repeated `duplicate_group_id`. |
| signals not marked independent | 500 | Any `is_independent_sample` value other than `true`. |
| timestamps without timezone | 0 | Checked exported timestamp-like fields. |
| features with possible leakage keywords | 0 | Keywords: future, forward, outcome, target, label, mfe, mae. Review manually. |
| patterns with uses_future_data = true | 0 | Must be zero unless explicitly justified. |
| duplicated or nearly duplicated variants | 0 | Exact duplicate `(pattern_id, parameters_json)` pairs. |
| patterns without clear exit rule | 0 | Empty `exit_rule_plaintext`. |
| patterns without clear entry rule | 0 | Empty `entry_rule_plaintext`. |

## F. Preliminary Claw Recommendation

| bucket | count | recommendation |
|---|---:|---|
| candidates_for_audit | 30 | Review first for lab quality and statistical robustness; do not approve for operation. |
| needs_more_samples | 182 | Gather more independent samples before statistical claims. |
| likely_duplicates | 213 | Deduplicate or explain before ranking. |
| freeze_until_more_data | 465 | No paper trades yet; execution validation unavailable. |
| discard_candidates | 177 | Low sample or low ticker diversity; keep rejected unless new evidence appears. |

### First Candidates For Audit

| pattern_id | pattern_name | independent_sample_count | ticker_count | status |
|---|---|---:|---:|---|
| PATTERN_000398 | DISCOVERED_LONG_W20_C10_23AFD7D8 | 2289 | 27 | rejected |
| PATTERN_000275 | DISCOVERED_LONG_W20_C06_7A57C575 | 2079 | 27 | rejected |
| PATTERN_000123 | DISCOVERED_SHORT_W20_C06_A39911C9 | 1982 | 20 | rejected |
| PATTERN_000374 | DISCOVERED_LONG_W20_C00_659CABD7 | 1967 | 27 | rejected |
| PATTERN_000216 | DISCOVERED_LONG_W20_C10_BC6A527E | 1933 | 24 | rejected |
| PATTERN_000023 | DISCOVERED_LONG_W20_C11_A8CF022A | 1839 | 27 | rejected |
| PATTERN_000377 | DISCOVERED_LONG_W20_C11_08DEA78E | 1615 | 27 | rejected |
| PATTERN_000273 | DISCOVERED_SHORT_W20_C07_78E7E2B9 | 1607 | 27 | rejected |
| PATTERN_000403 | DISCOVERED_SHORT_W20_C05_76056E6F | 1524 | 27 | rejected |
| PATTERN_000036 | DISCOVERED_LONG_W20_C08_85949F07 | 1509 | 27 | rejected |
| PATTERN_000029 | DISCOVERED_LONG_W20_C08_519EBA3A | 1509 | 27 | rejected |
| PATTERN_000039 | DISCOVERED_LONG_W20_C08_B8496B30 | 1509 | 27 | rejected |
| PATTERN_000408 | DISCOVERED_SHORT_W20_C02_24519BF6 | 1486 | 27 | rejected |
| PATTERN_000221 | DISCOVERED_SHORT_W20_C07_4C51A243 | 1466 | 24 | rejected |
| PATTERN_000027 | DISCOVERED_SHORT_W20_C01_326BBE79 | 1441 | 27 | rejected |
| PATTERN_000407 | DISCOVERED_LONG_W20_C01_3CA3218E | 1427 | 27 | rejected |
| PATTERN_000269 | DISCOVERED_LONG_W20_C03_70E7C15F | 1413 | 27 | rejected |
| PATTERN_000117 | DISCOVERED_SHORT_W20_C01_7BDA6ED8 | 1394 | 20 | rejected |
| PATTERN_000218 | DISCOVERED_LONG_W20_C03_42ABEBEE | 1362 | 24 | rejected |
| PATTERN_000024 | DISCOVERED_LONG_W20_C04_53B26AF4 | 1357 | 27 | rejected |
| PATTERN_000037 | DISCOVERED_LONG_W20_C04_92A899D7 | 1357 | 27 | rejected |
| PATTERN_000406 | DISCOVERED_LONG_W20_C09_CAF6546E | 1354 | 27 | rejected |
| PATTERN_000279 | DISCOVERED_LONG_W20_C11_CAAD9849 | 1233 | 27 | rejected |
| PATTERN_000001 | DISCOVERED_LONG_W20_C05_798BAA44 | 1224 | 24 | rejected |
| PATTERN_000276 | DISCOVERED_LONG_W20_C01_A2B5CA7A | 1205 | 27 | rejected |
| PATTERN_000376 | DISCOVERED_SHORT_W20_C07_A7D07551 | 1203 | 27 | rejected |
| PATTERN_000219 | DISCOVERED_LONG_W20_C04_70DFA8A1 | 1087 | 24 | rejected |
| PATTERN_000048 | DISCOVERED_LONG_W20_C04_DBC9C574 | 1075 | 24 | rejected |
| PATTERN_000051 | DISCOVERED_SHORT_W20_C02_76FE4B00 | 1070 | 24 | rejected |
| PATTERN_000003 | DISCOVERED_LONG_W20_C01_06E08FF8 | 1069 | 24 | rejected |

### Bottom-Line Instruction

Do not approve any pattern from this package. Use it to audit the research lab, detect data/logic issues, and rank candidates for future paper validation.
