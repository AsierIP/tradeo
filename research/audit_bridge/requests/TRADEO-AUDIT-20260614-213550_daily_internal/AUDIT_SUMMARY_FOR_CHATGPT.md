# Audit Summary For ChatGPT

Generated from the package CSV exports. This is a lab-audit and candidate-ranking aid only.

**Validation stance:** no pattern is approved for operation in this package. Paper/live execution validation is unavailable because `paper_trades.csv` and `ib_fills.csv` have zero rows; there are no `closed_lab_trades` from which to rank by regime or entry variant.

## A. Sample Distribution By Pattern

| metric | value |
|---|---:|
| total patterns | 500 |
| min independent_sample_count | 8 |
| p25 | 10.00 |
| median | 11.00 |
| p75 | 11.00 |
| p90 | 11.00 |
| max | 11 |
| patterns >= 30 samples | 0 |
| patterns >= 50 samples | 0 |
| patterns >= 100 samples | 0 |
| patterns >= 300 samples | 0 |
| patterns >= 500 samples | 0 |

## B. Top 30 Patterns By Independent Sample Count

| pattern_id | pattern_name | independent_sample_count | event_count | ticker_count | first_seen | last_seen | net_pnl_estimado | profit_factor | max_drawdown | status |
|---|---|---:|---:|---:|---|---|---:|---:|---:|---|
| PATTERN_000492 | DISCOVERED_SHORT_W50_C01_85A05D85 | 11 | 66 | 14 | 2021-10-06T00:00:00+00:00 | 2025-02-20T00:00:00+00:00 | 0 |  |  | lab_candidate |
| PATTERN_000560 | DISCOVERED_SHORT_W50_C02_18ED21F8 | 11 | 63 | 17 | 2021-09-07T00:00:00+00:00 | 2023-06-13T00:00:00+00:00 | 0 |  |  | lab_candidate |
| PATTERN_000494 | DISCOVERED_SHORT_W50_C10_58F162DA | 11 | 56 | 20 | 2021-12-01T00:00:00+00:00 | 2022-05-20T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000490 | DISCOVERED_SHORT_W50_C03_38E81507 | 11 | 51 | 16 | 2021-10-27T00:00:00+00:00 | 2022-05-25T00:00:00+00:00 | 0 |  |  | lab_candidate |
| PATTERN_000146 | DISCOVERED_SHORT_W50_C03_A8E55DE4 | 11 | 51 | 9 | 2021-10-14T00:00:00+00:00 | 2023-11-03T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000115 | DISCOVERED_LONG_W20_C05_07F5B55F | 11 | 44 | 20 | 2021-09-20T00:00:00+00:00 | 2026-03-03T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000292 | DISCOVERED_LONG_W20_C08_F227A7E4 | 11 | 44 | 8 | 2021-07-26T00:00:00+00:00 | 2026-03-24T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000371 | DISCOVERED_SHORT_W50_C00_E21E3237 | 11 | 35 | 20 | 2021-09-02T00:00:00+00:00 | 2025-04-30T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000090 | DISCOVERED_SHORT_W20_C00_7C7F0CBB | 11 | 28 | 23 | 2022-04-01T00:00:00+00:00 | 2024-09-16T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000366 | DISCOVERED_SHORT_W50_C06_D53F85BD | 11 | 23 | 19 | 2021-12-01T00:00:00+00:00 | 2022-05-20T00:00:00+00:00 | 0 |  |  | paper_candidate |
| PATTERN_000028 | DISCOVERED_SHORT_W50_C04_68EE8AB8 | 11 | 22 | 18 | 2021-08-24T00:00:00+00:00 | 2022-02-17T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000586 | DISCOVERED_SHORT_W20_C00_53B25BBC | 11 | 21 | 23 | 2021-09-10T00:00:00+00:00 | 2025-08-29T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000212 | DISCOVERED_LONG_W20_C11_88DE1FDF | 11 | 20 | 21 | 2022-04-11T00:00:00+00:00 | 2026-04-01T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000002 | DISCOVERED_SHORT_W20_C03_6A9EDC74 | 11 | 19 | 23 | 2021-12-14T00:00:00+00:00 | 2023-08-30T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000364 | DISCOVERED_SHORT_W50_C05_BBCCAF14 | 11 | 18 | 18 | 2021-09-01T00:00:00+00:00 | 2022-06-16T00:00:00+00:00 | 0 |  |  | paper_candidate |
| PATTERN_000544 | DISCOVERED_SHORT_W20_C04_8DEB273D | 11 | 17 | 27 | 2021-09-10T00:00:00+00:00 | 2025-04-30T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000282 | DISCOVERED_LONG_W20_C05_43AA830F | 11 | 16 | 8 | 2021-12-06T00:00:00+00:00 | 2026-02-18T00:00:00+00:00 | 0 |  |  | paper_candidate |
| PATTERN_000415 | DISCOVERED_LONG_W20_C07_1DCBEBD1 | 11 | 13 | 13 | 2021-12-09T00:00:00+00:00 | 2025-03-18T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000524 | DISCOVERED_LONG_W20_C07_943E3CAC | 11 | 13 | 18 | 2021-07-13T00:00:00+00:00 | 2026-04-01T00:00:00+00:00 | 0 |  |  | lab |
| PATTERN_000478 | DISCOVERED_SHORT_W20_C09_3597EC9B | 11 | 12 | 27 | 2021-12-28T00:00:00+00:00 | 2026-03-27T00:00:00+00:00 | 0 |  |  | lab_watchlist |
| PATTERN_000200 | DISCOVERED_SHORT_W50_C10_4142FAF4 | 11 | 11 | 14 | 2021-09-07T00:00:00+00:00 | 2022-11-18T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000466 | DISCOVERED_SHORT_W50_C00_CE8AA7CF | 11 | 11 | 6 | 2021-09-15T00:00:00+00:00 | 2022-11-23T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000617 | DISCOVERED_SHORT_W50_C00_989C652E | 11 | 11 | 11 | 2021-09-15T00:00:00+00:00 | 2022-11-18T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000103 | DISCOVERED_SHORT_W50_C10_CC719DB4 | 11 | 11 | 4 | 2021-09-10T00:00:00+00:00 | 2023-02-13T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000694 | DISCOVERED_SHORT_W50_C09_1305EF64 | 11 | 11 | 23 | 2021-08-23T00:00:00+00:00 | 2022-02-25T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000258 | DISCOVERED_SHORT_W50_C04_DB295C4E | 11 | 11 | 20 | 2021-08-16T00:00:00+00:00 | 2022-02-14T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000237 | DISCOVERED_SHORT_W50_C06_3282E3E4 | 11 | 11 | 10 | 2021-08-20T00:00:00+00:00 | 2024-05-17T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000104 | DISCOVERED_SHORT_W50_C03_910C25FE | 11 | 11 | 18 | 2021-12-14T00:00:00+00:00 | 2022-11-07T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000432 | DISCOVERED_LONG_W20_C03_49116A34 | 11 | 11 | 1 | 2022-04-28T00:00:00+00:00 | 2024-05-17T00:00:00+00:00 | 0 |  |  | rejected |
| PATTERN_000105 | DISCOVERED_SHORT_W50_C11_3DDBA7B3 | 11 | 11 | 15 | 2021-08-16T00:00:00+00:00 | 2022-02-14T00:00:00+00:00 | 0 |  |  | rejected |

## C. Top 30 Patterns By Estimated Net PnL

No available `net_pnl` values. Current package has zero paper trades/fills, so PnL ranking is not actionable.

## D. Concentration

| check | count | notes |
|---|---:|---|
| patterns whose PnL depends on best trade | 0 | Requires non-empty PnL fields. |
| patterns whose PnL depends on top 5 trades | 0 | Requires non-empty PnL fields. |
| patterns concentrated in fewer than 5 tickers | 137 | Based on `metrics_by_pattern.ticker_count`. |
| patterns concentrated in fewer than 5 days | 0 | Based on unique event dates in `pattern_events.csv`. |
| patterns concentrated in one market regime | 474 | Current export mostly uses `not_persisted`; regime audit is limited. |
| regime performance buckets available | 0 | See `metrics_by_regime.csv`; empty rows include `empty_reason`. |
| entry variant performance buckets available | 0 | See `metrics_by_entry_variant.csv`; empty rows include `empty_reason`. |

## E. Automatically Detected Risks

| risk | count | notes |
|---|---:|---|
| possible duplicated event rows | 248 | Counted from repeated `duplicate_group_id`. |
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
| candidates_for_audit | 0 | Review first for lab quality and statistical robustness; do not approve for operation. |
| needs_more_samples | 500 | Gather more independent samples before statistical claims. |
| likely_duplicates | 248 | Deduplicate or explain before ranking. |
| freeze_until_more_data | 500 | No paper trades yet; execution validation unavailable. |
| discard_candidates | 500 | Low sample or low ticker diversity; keep rejected unless new evidence appears. |
| no_closed_lab_trades_bucket_gap | 1 | Fill `paper_trades.csv` with closed lab trades carrying regime and entry_variant metadata before bucket ranking. |

### First Candidates For Audit

| pattern_id | pattern_name | independent_sample_count | ticker_count | status |
|---|---|---:|---:|---|

### Regime Bucket Snapshot

no_closed_lab_trades: missing closed_lab_trades with signal.metadata_json.regime.regime_key; paper_trades.csv has no matching closed trades.

### Entry Variant Bucket Snapshot

no_closed_lab_trades: missing closed_lab_trades with signal.metadata_json.entry_variant_id; paper_trades.csv has no matching closed trades.

### Bottom-Line Instruction

Do not approve any pattern from this package. Use it to audit the research lab, detect data/logic issues, and rank candidates for future paper validation.
