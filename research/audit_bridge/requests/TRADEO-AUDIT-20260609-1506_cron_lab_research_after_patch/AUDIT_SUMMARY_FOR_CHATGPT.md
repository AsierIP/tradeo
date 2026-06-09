# Audit Summary For ChatGPT

Generated from the package CSV exports. This is a lab-audit and candidate-ranking aid only.

**Validation stance:** no pattern is approved for operation in this package. Paper/live execution validation is unavailable because `paper_trades.csv` and `ib_fills.csv` have zero rows.

## A. Sample Distribution By Pattern

| metric | value |
|---|---:|
| total patterns | 120 |
| min independent_sample_count | 30 |
| p25 | 53.75 |
| median | 75.00 |
| p75 | 101.00 |
| p90 | 125.40 |
| max | 1060 |
| patterns >= 30 samples | 120 |
| patterns >= 50 samples | 96 |
| patterns >= 100 samples | 33 |
| patterns >= 300 samples | 3 |
| patterns >= 500 samples | 2 |

## B. Top 30 Patterns By Independent Sample Count

| pattern_id | pattern_name | independent_sample_count | event_count | ticker_count | first_seen | last_seen | net_pnl_estimado | profit_factor | max_drawdown | status |
|---|---|---:|---:|---:|---|---|---:|---:|---:|---|
| PATTERN_000047 | DISCOVERED_LONG_W20_C01_AF0AFDF9 | 1060 | 1060 | 24 | 2021-07-13T00:00:00+00:00 | 2024-01-31T00:00:00+00:00 | 0 | 1.46724 | 38.55611 | rejected |
| PATTERN_000284 | DISCOVERED_LONG_W20_C03_BEBBB87A | 644 | 644 | 8 | 2021-07-13T00:00:00+00:00 | 2025-11-19T00:00:00+00:00 | 0 | 1.79167 | 26.85386 | rejected |
| PATTERN_000413 | DISCOVERED_LONG_W20_C03_27E7715B | 438 | 438 | 13 | 2021-12-28T00:00:00+00:00 | 2026-04-23T00:00:00+00:00 | 0 | 1.4395 | 38.46605 | rejected |
| PATTERN_000128 | DISCOVERED_LONG_W20_C08_2A34E2D6 | 212 | 212 | 4 | 2021-11-04T00:00:00+00:00 | 2026-04-07T00:00:00+00:00 | 0 | 2.23841 | 14.68703 | rejected |
| PATTERN_000453 | DISCOVERED_LONG_W20_C02_A1FABD04 | 206 | 206 | 3 | 2021-07-02T00:00:00+00:00 | 2025-12-16T00:00:00+00:00 | 0 | 1.54125 | 26.18528 | rejected |
| PATTERN_000059 | DISCOVERED_LONG_W20_C11_484F3A29 | 184 | 184 | 3 | 2021-11-04T00:00:00+00:00 | 2024-05-06T00:00:00+00:00 | 0 | 1.86508 | 18.97468 | rejected |
| PATTERN_000262 | DISCOVERED_SHORT_W50_C02_DA0B95F5 | 182 | 182 | 19 | 2021-08-16T00:00:00+00:00 | 2022-01-19T00:00:00+00:00 | 0 | 1.63644 | 24.70485 | rejected |
| PATTERN_000316 | DISCOVERED_LONG_W20_C02_F2E76BEA | 172 | 172 | 1 | 2022-03-09T00:00:00+00:00 | 2026-04-02T00:00:00+00:00 | 0 | 1.7329 | 17.14719 | rejected |
| PATTERN_000016 | DISCOVERED_SHORT_W50_C06_6C7C8BB7 | 150 | 150 | 20 | 2021-09-10T00:00:00+00:00 | 2021-12-06T00:00:00+00:00 | 0 | 1.65893 | 14.84792 | rejected |
| PATTERN_000332 | DISCOVERED_SHORT_W20_C05_2A303029 | 149 | 149 | 1 | 2021-07-08T00:00:00+00:00 | 2026-01-16T00:00:00+00:00 | 0 | 1.40842 | 40.44963 | rejected |
| PATTERN_000433 | DISCOVERED_LONG_W20_C01_4A2C6E6F | 144 | 144 | 1 | 2021-07-02T00:00:00+00:00 | 2024-06-24T00:00:00+00:00 | 0 | 2.37747 | 8.0 | rejected |
| PATTERN_000177 | DISCOVERED_SHORT_W20_C05_4A0EE5FC | 129 | 129 | 2 | 2021-07-13T00:00:00+00:00 | 2026-04-15T00:00:00+00:00 | 0 | 1.47208 | 20.83405 | rejected |
| PATTERN_000183 | DISCOVERED_SHORT_W50_C01_2F677116 | 125 | 125 | 9 | 2021-08-16T00:00:00+00:00 | 2022-02-17T00:00:00+00:00 | 0 | 1.58421 | 16.52072 | rejected |
| PATTERN_000492 | DISCOVERED_SHORT_W50_C01_85A05D85 | 124 | 124 | 14 | 2021-10-06T00:00:00+00:00 | 2025-02-20T00:00:00+00:00 | 0 | 2.93063 | 6.0 | lab_candidate |
| PATTERN_000225 | DISCOVERED_LONG_W20_C04_04EF2C14 | 124 | 124 | 4 | 2022-01-10T00:00:00+00:00 | 2025-05-21T00:00:00+00:00 | 0 | 1.65606 | 13.73647 | rejected |
| PATTERN_000201 | DISCOVERED_SHORT_W50_C02_B1AF15AF | 122 | 122 | 21 | 2021-08-19T00:00:00+00:00 | 2021-12-28T00:00:00+00:00 | 0 | 2.357 | 14.877 | rejected |
| PATTERN_000620 | DISCOVERED_SHORT_W50_C04_9BE87280 | 121 | 121 | 21 | 2021-08-19T00:00:00+00:00 | 2022-01-05T00:00:00+00:00 | 0 | 2.06279 | 11.81198 | lab_candidate |
| PATTERN_000583 | DISCOVERED_SHORT_W50_C11_B3A70DDE | 119 | 119 | 16 | 2021-09-20T00:00:00+00:00 | 2023-06-13T00:00:00+00:00 | 0 | 2.12048 | 14.78548 | rejected |
| PATTERN_000494 | DISCOVERED_SHORT_W50_C10_58F162DA | 117 | 117 | 20 | 2021-12-01T00:00:00+00:00 | 2022-05-20T00:00:00+00:00 | 0 | 2.42208 | 11.47113 | lab_watchlist |
| PATTERN_000282 | DISCOVERED_LONG_W20_C05_43AA830F | 114 | 114 | 8 | 2021-12-06T00:00:00+00:00 | 2026-02-18T00:00:00+00:00 | 0 | 2.09731 | 7.70257 | paper_candidate |
| PATTERN_000061 | DISCOVERED_LONG_W20_C02_897C0469 | 113 | 113 | 4 | 2021-07-16T00:00:00+00:00 | 2023-11-20T00:00:00+00:00 | 0 | 1.62103 | 12.56676 | rejected |
| PATTERN_000364 | DISCOVERED_SHORT_W50_C05_BBCCAF14 | 111 | 111 | 18 | 2021-09-01T00:00:00+00:00 | 2022-06-16T00:00:00+00:00 | 0 | 2.18494 | 7.50897 | paper_candidate |
| PATTERN_000469 | DISCOVERED_SHORT_W50_C05_B3502794 | 110 | 110 | 14 | 2021-09-10T00:00:00+00:00 | 2022-02-28T00:00:00+00:00 | 0 | 1.88384 | 10.0 | lab_watchlist |
| PATTERN_000205 | DISCOVERED_LONG_W20_C02_141038FE | 108 | 108 | 14 | 2021-11-23T00:00:00+00:00 | 2026-02-23T00:00:00+00:00 | 0 | 1.45958 | 18.49763 | rejected |
| PATTERN_000366 | DISCOVERED_SHORT_W50_C06_D53F85BD | 106 | 106 | 19 | 2021-12-01T00:00:00+00:00 | 2022-05-20T00:00:00+00:00 | 0 | 2.57718 | 11.0 | paper_candidate |
| PATTERN_000175 | DISCOVERED_LONG_W20_C02_FEF1E222 | 105 | 105 | 2 | 2021-07-02T00:00:00+00:00 | 2025-11-24T00:00:00+00:00 | 0 | 2.15735 | 7.0 | rejected |
| PATTERN_000060 | DISCOVERED_LONG_W20_C04_A58C27FA | 105 | 105 | 4 | 2021-07-02T00:00:00+00:00 | 2024-06-05T00:00:00+00:00 | 0 | 1.96344 | 10.3457 | rejected |
| PATTERN_000490 | DISCOVERED_SHORT_W50_C03_38E81507 | 103 | 103 | 16 | 2021-10-27T00:00:00+00:00 | 2022-05-25T00:00:00+00:00 | 0 | 3.71659 | 4.89649 | lab_candidate |
| PATTERN_000470 | DISCOVERED_SHORT_W50_C06_7AE97930 | 102 | 102 | 15 | 2021-08-19T00:00:00+00:00 | 2021-12-06T00:00:00+00:00 | 0 | 1.44329 | 18.41089 | rejected |
| PATTERN_000068 | DISCOVERED_LONG_W50_C01_4C05BFF3 | 101 | 101 | 3 | 2021-08-19T00:00:00+00:00 | 2023-05-23T00:00:00+00:00 | 0 | 2.22188 | 13.82797 | rejected |

## C. Top 30 Patterns By Estimated Net PnL

No available `net_pnl` values. Current package has zero paper trades/fills, so PnL ranking is not actionable.

## D. Concentration

| check | count | notes |
|---|---:|---|
| patterns whose PnL depends on best trade | 0 | Requires non-empty PnL fields. |
| patterns whose PnL depends on top 5 trades | 0 | Requires non-empty PnL fields. |
| patterns concentrated in fewer than 5 tickers | 45 | Based on `metrics_by_pattern.ticker_count`. |
| patterns concentrated in fewer than 5 days | 0 | Based on unique event dates in `pattern_events.csv`. |
| patterns concentrated in one market regime | 111 | Current export mostly uses `not_persisted`; regime audit is limited. |

## E. Automatically Detected Risks

| risk | count | notes |
|---|---:|---|
| possible duplicated event rows | 166 | Counted from repeated `duplicate_group_id`. |
| signals not marked independent | 202 | Any `is_independent_sample` value other than `true`. |
| timestamps without timezone | 0 | Checked exported timestamp-like fields. |
| features with possible leakage keywords | 0 | Keywords: future, forward, outcome, target, label, mfe, mae. Review manually. |
| patterns with uses_future_data = true | 0 | Must be zero unless explicitly justified. |
| duplicated or nearly duplicated variants | 0 | Exact duplicate `(pattern_id, parameters_json)` pairs. |
| patterns without clear exit rule | 0 | Empty `exit_rule_plaintext`. |
| patterns without clear entry rule | 0 | Empty `entry_rule_plaintext`. |

## F. Preliminary Claw Recommendation

| bucket | count | recommendation |
|---|---:|---|
| candidates_for_audit | 18 | Review first for lab quality and statistical robustness; do not approve for operation. |
| needs_more_samples | 87 | Gather more independent samples before statistical claims. |
| likely_duplicates | 166 | Deduplicate or explain before ranking. |
| freeze_until_more_data | 120 | No paper trades yet; execution validation unavailable. |
| discard_candidates | 45 | Low sample or low ticker diversity; keep rejected unless new evidence appears. |

### First Candidates For Audit

| pattern_id | pattern_name | independent_sample_count | ticker_count | status |
|---|---|---:|---:|---|
| PATTERN_000047 | DISCOVERED_LONG_W20_C01_AF0AFDF9 | 1060 | 24 | rejected |
| PATTERN_000284 | DISCOVERED_LONG_W20_C03_BEBBB87A | 644 | 8 | rejected |
| PATTERN_000413 | DISCOVERED_LONG_W20_C03_27E7715B | 438 | 13 | rejected |
| PATTERN_000262 | DISCOVERED_SHORT_W50_C02_DA0B95F5 | 182 | 19 | rejected |
| PATTERN_000016 | DISCOVERED_SHORT_W50_C06_6C7C8BB7 | 150 | 20 | rejected |
| PATTERN_000183 | DISCOVERED_SHORT_W50_C01_2F677116 | 125 | 9 | rejected |
| PATTERN_000492 | DISCOVERED_SHORT_W50_C01_85A05D85 | 124 | 14 | lab_candidate |
| PATTERN_000201 | DISCOVERED_SHORT_W50_C02_B1AF15AF | 122 | 21 | rejected |
| PATTERN_000620 | DISCOVERED_SHORT_W50_C04_9BE87280 | 121 | 21 | lab_candidate |
| PATTERN_000583 | DISCOVERED_SHORT_W50_C11_B3A70DDE | 119 | 16 | rejected |
| PATTERN_000494 | DISCOVERED_SHORT_W50_C10_58F162DA | 117 | 20 | lab_watchlist |
| PATTERN_000282 | DISCOVERED_LONG_W20_C05_43AA830F | 114 | 8 | paper_candidate |
| PATTERN_000364 | DISCOVERED_SHORT_W50_C05_BBCCAF14 | 111 | 18 | paper_candidate |
| PATTERN_000469 | DISCOVERED_SHORT_W50_C05_B3502794 | 110 | 14 | lab_watchlist |
| PATTERN_000205 | DISCOVERED_LONG_W20_C02_141038FE | 108 | 14 | rejected |
| PATTERN_000366 | DISCOVERED_SHORT_W50_C06_D53F85BD | 106 | 19 | paper_candidate |
| PATTERN_000490 | DISCOVERED_SHORT_W50_C03_38E81507 | 103 | 16 | lab_candidate |
| PATTERN_000470 | DISCOVERED_SHORT_W50_C06_7AE97930 | 102 | 15 | rejected |

### Bottom-Line Instruction

Do not approve any pattern from this package. Use it to audit the research lab, detect data/logic issues, and rank candidates for future paper validation.
