# Audit Summary For ChatGPT

Generated from the package CSV exports. This is a lab-audit and candidate-ranking aid only.

**Validation stance:** no pattern is approved for operation in this package. Paper/live execution validation is unavailable because `paper_trades.csv` and `ib_fills.csv` have zero rows.

## A. Sample Distribution By Pattern

| metric | value |
|---|---:|
| total patterns | 500 |
| min independent_sample_count | 30 |
| p25 | 73.75 |
| median | 132.00 |
| p75 | 414.25 |
| p90 | 998.60 |
| max | 3151 |
| patterns >= 30 samples | 500 |
| patterns >= 50 samples | 452 |
| patterns >= 100 samples | 313 |
| patterns >= 300 samples | 149 |
| patterns >= 500 samples | 111 |

## B. Top 30 Patterns By Independent Sample Count

| pattern_id | pattern_name | independent_sample_count | event_count | ticker_count | first_seen | last_seen | net_pnl_estimado | profit_factor | max_drawdown | status |
|---|---|---:|---:|---:|---|---|---:|---:|---:|---|
| PATTERN_000479 | DISCOVERED_LONG_W20_C03_54495ACA | 3151 | 3151 | 27 | 2021-09-28T00:00:00+00:00 | 2026-04-01T00:00:00+00:00 | 0 | 1.34598 | 90.34896 | rejected |
| PATTERN_000502 | DISCOVERED_SHORT_W20_C09_92CAE690 | 2433 | 2433 | 26 | 2022-07-18T00:00:00+00:00 | 2026-01-08T00:00:00+00:00 | 0 | 1.06281 | 143.26209 | rejected |
| PATTERN_000398 | DISCOVERED_LONG_W20_C10_23AFD7D8 | 2289 | 2289 | 27 | 2021-11-01T00:00:00+00:00 | 2025-08-05T00:00:00+00:00 | 0 | 1.31738 | 64.95042 | rejected |
| PATTERN_000569 | DISCOVERED_LONG_W20_C04_B46F2FCA | 2271 | 2271 | 27 | 2021-07-16T00:00:00+00:00 | 2026-01-05T00:00:00+00:00 | 0 | 1.22633 | 98.31722 | rejected |
| PATTERN_000551 | DISCOVERED_LONG_W20_C08_5C360351 | 2257 | 2257 | 27 | 2021-08-11T00:00:00+00:00 | 2025-08-08T00:00:00+00:00 | 0 | 1.22026 | 88.33245 | rejected |
| PATTERN_000275 | DISCOVERED_LONG_W20_C06_7A57C575 | 2079 | 2079 | 27 | 2021-07-13T00:00:00+00:00 | 2025-10-13T00:00:00+00:00 | 0 | 1.24157 | 118.48466 | rejected |
| PATTERN_000592 | DISCOVERED_LONG_W20_C02_5E60C311 | 2067 | 2067 | 27 | 2023-07-06T00:00:00+00:00 | 2026-01-15T00:00:00+00:00 | 0 | 1.34028 | 48.60727 | rejected |
| PATTERN_000549 | DISCOVERED_LONG_W20_C00_2A3EEBA9 | 2064 | 2064 | 26 | 2021-11-17T00:00:00+00:00 | 2025-09-12T00:00:00+00:00 | 0 | 1.27403 | 74.37113 | rejected |
| PATTERN_000374 | DISCOVERED_LONG_W20_C00_659CABD7 | 1967 | 1967 | 27 | 2021-12-06T00:00:00+00:00 | 2025-03-21T00:00:00+00:00 | 0 | 1.25109 | 95.8417 | rejected |
| PATTERN_000531 | DISCOVERED_LONG_W20_C05_F37A7C6C | 1936 | 1936 | 27 | 2022-06-21T00:00:00+00:00 | 2026-01-27T00:00:00+00:00 | 0 | 1.21408 | 75.67488 | rejected |
| PATTERN_000216 | DISCOVERED_LONG_W20_C10_BC6A527E | 1933 | 1933 | 24 | 2023-07-11T00:00:00+00:00 | 2025-08-08T00:00:00+00:00 | 0 | 1.23114 | 78.60368 | rejected |
| PATTERN_000596 | DISCOVERED_SHORT_W20_C05_1FE2A639 | 1880 | 1880 | 27 | 2021-11-12T00:00:00+00:00 | 2025-11-03T00:00:00+00:00 | 0 | 1.15494 | 82.13365 | rejected |
| PATTERN_000023 | DISCOVERED_LONG_W20_C11_A8CF022A | 1839 | 1839 | 27 | 2021-07-21T00:00:00+00:00 | 2025-11-11T00:00:00+00:00 | 0 | 1.27007 | 67.30591 | rejected |
| PATTERN_000523 | DISCOVERED_LONG_W20_C09_1414C751 | 1801 | 1801 | 27 | 2021-07-13T00:00:00+00:00 | 2026-01-05T00:00:00+00:00 | 0 | 1.35263 | 96.18084 | rejected |
| PATTERN_000377 | DISCOVERED_LONG_W20_C11_08DEA78E | 1615 | 1615 | 27 | 2021-07-13T00:00:00+00:00 | 2026-01-27T00:00:00+00:00 | 0 | 1.28404 | 56.64109 | rejected |
| PATTERN_000273 | DISCOVERED_SHORT_W20_C07_78E7E2B9 | 1607 | 1607 | 27 | 2021-07-13T00:00:00+00:00 | 2024-12-12T00:00:00+00:00 | 0 | 1.18117 | 53.23259 | rejected |
| PATTERN_000594 | DISCOVERED_LONG_W20_C10_9929DB96 | 1600 | 1600 | 27 | 2021-12-09T00:00:00+00:00 | 2026-04-28T00:00:00+00:00 | 0 | 1.20463 | 80.13186 | rejected |
| PATTERN_000487 | DISCOVERED_LONG_W20_C05_BECF1229 | 1527 | 1527 | 27 | 2021-10-01T00:00:00+00:00 | 2025-07-23T00:00:00+00:00 | 0 | 1.07178 | 108.50693 | rejected |
| PATTERN_000403 | DISCOVERED_SHORT_W20_C05_76056E6F | 1524 | 1524 | 27 | 2021-09-20T00:00:00+00:00 | 2024-10-22T00:00:00+00:00 | 0 | 1.16048 | 62.9861 | rejected |
| PATTERN_000036 | DISCOVERED_LONG_W20_C08_85949F07 | 1509 | 1509 | 27 | 2021-12-06T00:00:00+00:00 | 2026-01-30T00:00:00+00:00 | 0 | 1.19554 | 64.89136 | rejected |
| PATTERN_000029 | DISCOVERED_LONG_W20_C08_519EBA3A | 1509 | 1509 | 27 | 2021-12-06T00:00:00+00:00 | 2026-01-30T00:00:00+00:00 | 0 | 1.19554 | 64.89136 | rejected |
| PATTERN_000027 | DISCOVERED_SHORT_W20_C01_326BBE79 | 1441 | 1441 | 27 | 2021-09-28T00:00:00+00:00 | 2025-07-31T00:00:00+00:00 | 0 | 1.14121 | 54.27766 | rejected |
| PATTERN_000407 | DISCOVERED_LONG_W20_C01_3CA3218E | 1427 | 1427 | 27 | 2021-08-24T00:00:00+00:00 | 2026-03-06T00:00:00+00:00 | 0 | 1.20914 | 61.07864 | rejected |
| PATTERN_000269 | DISCOVERED_LONG_W20_C03_70E7C15F | 1413 | 1413 | 27 | 2022-06-21T00:00:00+00:00 | 2024-11-20T00:00:00+00:00 | 0 | 1.39213 | 59.68482 | rejected |
| PATTERN_000117 | DISCOVERED_SHORT_W20_C01_7BDA6ED8 | 1394 | 1394 | 20 | 2023-04-10T00:00:00+00:00 | 2026-04-28T00:00:00+00:00 | 0 | 1.1943 | 61.08213 | rejected |
| PATTERN_000532 | DISCOVERED_LONG_W20_C06_FDB0C003 | 1377 | 1377 | 27 | 2021-12-09T00:00:00+00:00 | 2025-07-31T00:00:00+00:00 | 0 | 1.25029 | 94.07625 | rejected |
| PATTERN_000218 | DISCOVERED_LONG_W20_C03_42ABEBEE | 1362 | 1362 | 24 | 2021-07-29T00:00:00+00:00 | 2024-09-05T00:00:00+00:00 | 0 | 1.23451 | 69.99317 | rejected |
| PATTERN_000506 | DISCOVERED_LONG_W20_C00_32BAAB9F | 1359 | 1359 | 27 | 2021-08-19T00:00:00+00:00 | 2026-03-27T00:00:00+00:00 | 0 | 1.14773 | 67.87049 | rejected |
| PATTERN_000024 | DISCOVERED_LONG_W20_C04_53B26AF4 | 1357 | 1357 | 27 | 2021-07-29T00:00:00+00:00 | 2025-02-03T00:00:00+00:00 | 0 | 1.33756 | 37.26638 | rejected |
| PATTERN_000037 | DISCOVERED_LONG_W20_C04_92A899D7 | 1357 | 1357 | 27 | 2021-09-01T00:00:00+00:00 | 2025-08-21T00:00:00+00:00 | 0 | 0.0 | 0.0 | rejected |

## C. Top 30 Patterns By Estimated Net PnL

No available `net_pnl` values. Current package has zero paper trades/fills, so PnL ranking is not actionable.

## D. Concentration

| check | count | notes |
|---|---:|---|
| patterns whose PnL depends on best trade | 0 | Requires non-empty PnL fields. |
| patterns whose PnL depends on top 5 trades | 0 | Requires non-empty PnL fields. |
| patterns concentrated in fewer than 5 tickers | 142 | Based on `metrics_by_pattern.ticker_count`. |
| patterns concentrated in fewer than 5 days | 0 | Based on unique event dates in `pattern_events.csv`. |
| patterns concentrated in one market regime | 500 | Current export mostly uses `not_persisted`; regime audit is limited. |

## E. Automatically Detected Risks

| risk | count | notes |
|---|---:|---|
| possible duplicated event rows | 400 | Counted from repeated `duplicate_group_id`. |
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
| needs_more_samples | 187 | Gather more independent samples before statistical claims. |
| likely_duplicates | 400 | Deduplicate or explain before ranking. |
| freeze_until_more_data | 500 | No paper trades yet; execution validation unavailable. |
| discard_candidates | 142 | Low sample or low ticker diversity; keep rejected unless new evidence appears. |

### First Candidates For Audit

| pattern_id | pattern_name | independent_sample_count | ticker_count | status |
|---|---|---:|---:|---|
| PATTERN_000479 | DISCOVERED_LONG_W20_C03_54495ACA | 3151 | 27 | rejected |
| PATTERN_000502 | DISCOVERED_SHORT_W20_C09_92CAE690 | 2433 | 26 | rejected |
| PATTERN_000398 | DISCOVERED_LONG_W20_C10_23AFD7D8 | 2289 | 27 | rejected |
| PATTERN_000569 | DISCOVERED_LONG_W20_C04_B46F2FCA | 2271 | 27 | rejected |
| PATTERN_000551 | DISCOVERED_LONG_W20_C08_5C360351 | 2257 | 27 | rejected |
| PATTERN_000275 | DISCOVERED_LONG_W20_C06_7A57C575 | 2079 | 27 | rejected |
| PATTERN_000592 | DISCOVERED_LONG_W20_C02_5E60C311 | 2067 | 27 | rejected |
| PATTERN_000549 | DISCOVERED_LONG_W20_C00_2A3EEBA9 | 2064 | 26 | rejected |
| PATTERN_000374 | DISCOVERED_LONG_W20_C00_659CABD7 | 1967 | 27 | rejected |
| PATTERN_000531 | DISCOVERED_LONG_W20_C05_F37A7C6C | 1936 | 27 | rejected |
| PATTERN_000216 | DISCOVERED_LONG_W20_C10_BC6A527E | 1933 | 24 | rejected |
| PATTERN_000596 | DISCOVERED_SHORT_W20_C05_1FE2A639 | 1880 | 27 | rejected |
| PATTERN_000023 | DISCOVERED_LONG_W20_C11_A8CF022A | 1839 | 27 | rejected |
| PATTERN_000523 | DISCOVERED_LONG_W20_C09_1414C751 | 1801 | 27 | rejected |
| PATTERN_000377 | DISCOVERED_LONG_W20_C11_08DEA78E | 1615 | 27 | rejected |
| PATTERN_000273 | DISCOVERED_SHORT_W20_C07_78E7E2B9 | 1607 | 27 | rejected |
| PATTERN_000594 | DISCOVERED_LONG_W20_C10_9929DB96 | 1600 | 27 | rejected |
| PATTERN_000487 | DISCOVERED_LONG_W20_C05_BECF1229 | 1527 | 27 | rejected |
| PATTERN_000403 | DISCOVERED_SHORT_W20_C05_76056E6F | 1524 | 27 | rejected |
| PATTERN_000036 | DISCOVERED_LONG_W20_C08_85949F07 | 1509 | 27 | rejected |
| PATTERN_000029 | DISCOVERED_LONG_W20_C08_519EBA3A | 1509 | 27 | rejected |
| PATTERN_000027 | DISCOVERED_SHORT_W20_C01_326BBE79 | 1441 | 27 | rejected |
| PATTERN_000407 | DISCOVERED_LONG_W20_C01_3CA3218E | 1427 | 27 | rejected |
| PATTERN_000269 | DISCOVERED_LONG_W20_C03_70E7C15F | 1413 | 27 | rejected |
| PATTERN_000117 | DISCOVERED_SHORT_W20_C01_7BDA6ED8 | 1394 | 20 | rejected |
| PATTERN_000532 | DISCOVERED_LONG_W20_C06_FDB0C003 | 1377 | 27 | rejected |
| PATTERN_000218 | DISCOVERED_LONG_W20_C03_42ABEBEE | 1362 | 24 | rejected |
| PATTERN_000506 | DISCOVERED_LONG_W20_C00_32BAAB9F | 1359 | 27 | rejected |
| PATTERN_000024 | DISCOVERED_LONG_W20_C04_53B26AF4 | 1357 | 27 | rejected |
| PATTERN_000037 | DISCOVERED_LONG_W20_C04_92A899D7 | 1357 | 27 | rejected |

### Bottom-Line Instruction

Do not approve any pattern from this package. Use it to audit the research lab, detect data/logic issues, and rank candidates for future paper validation.
