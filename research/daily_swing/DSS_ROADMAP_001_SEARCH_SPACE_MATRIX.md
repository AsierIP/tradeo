# DSS-ROADMAP-001 Search-Space Matrix

Task: T-DAILY-ROADMAP-001
Generated: 2026-07-05
Scope: comparative roadmap only. No backtest, data download, IBKR, signal, preview, paper, or live execution was run.

Scores use 1-5 where higher is better, except leakage risk, data dependency, implementation cost, and future paper difficulty where higher means more risk/cost/difficulty.

| Search-space | Research value | Data dependency | Leakage risk | Implementation cost | Auditability | Infra compatibility | Future paper difficulty | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Earnings / post-earnings drift | 5 | 5 | 5 | 5 | 2 | 3 | 4 | High value, but blocked until a timestamped earnings data decision exists. |
| Gap continuation / gap reversal | 4 | 1 | 3 | 2 | 4 | 5 | 3 | Best next stock-only Daily candidate; uses existing OHLCV and requires no new external data. |
| Sector / relative strength | 4 | 4 | 4 | 4 | 3 | 3 | 3 | Promising, but needs point-in-time sector classification before testing. |
| Market breadth + pullback | 4 | 4 | 4 | 4 | 3 | 3 | 3 | Interesting regime filter, but breadth data/membership timing must be solved first. |
| Daily-to-intraday hybrid entry | 4 | 3 | 4 | 5 | 2 | 2 | 5 | Too complex immediately after Daily closure; defer until a Daily-only edge exists. |
| ETF/macro separate | 3 | 2 | 3 | 3 | 4 | 2 | 3 | Requires a policy decision because it changes the system from stock-only to ETF/macro. |

## Candidate Notes

### Earnings / Post-Earnings Drift

- Hypothesis: stocks with abnormal post-earnings drift continue over several sessions when the market regime is supportive.
- Data required: point-in-time earnings calendar, announcement timestamp, before/after-market flag, symbol mapping, OHLCV.
- Main false positives: timestamp leakage, revised calendars, survivorship, earnings surprise proxy leakage, and event clustering around mega-cap names.
- Minimum acceptance: every signal must prove timestamp availability before entry, survive event-time placebos, OOS/cost stress, concentration limits, and multiple-testing controls.

### Gap Continuation / Gap Reversal

- Hypothesis: large overnight gaps have conditional continuation or reversal behavior when filtered by prior trend, volume, volatility, and market regime.
- Data required: existing Daily OHLCV only for first protocol; optional intraday confirmation is a future phase.
- Main false positives: unrealistic open execution, gap fill assumptions, same-day information leakage, and selection of visually obvious thresholds.
- Minimum acceptance: pre-registered gap definition, entry model, adverse open slippage, OOS/cost stress, plus gap-size and direction placebos.

### Sector / Relative Strength

- Hypothesis: stocks with persistent strength versus sector/market benchmarks keep outperforming over short Daily horizons.
- Data required: stock OHLCV plus point-in-time sector classification or sector ETF benchmark mapping.
- Main false positives: present-day sector mapping leakage, survivorship bias, sector rotation fitted after the fact, and benchmark overlap.
- Minimum acceptance: timestamped classification policy, benchmark-only separation, sector-neutral controls, and concentration caps.

### Market Breadth + Pullback

- Hypothesis: Daily pullbacks work only when market breadth confirms a constructive regime.
- Data required: breadth series or derivation from a declared point-in-time universe.
- Main false positives: breadth unavailable at entry time, membership survivorship, hidden dependence on mega-cap regime, and refitting failed pullback logic.
- Minimum acceptance: no PB rescue, independent breadth definition, adversarial breadth shifts, and explicit rejection if pullback specificity is not improved.

### Daily-to-Intraday Hybrid Entry

- Hypothesis: a Daily condition may be viable only when the intraday entry improves realized execution and risk.
- Data required: Daily signal data plus intraday bars, execution model, and mixed-timeframe clock rules.
- Main false positives: time boundary leakage, cherry-picked intraday entry, and operational complexity hiding weak Daily signal quality.
- Minimum acceptance: Daily signal must first pass standalone research; intraday entry is only execution refinement, never edge rescue.

### ETF/Macro Separate

- Hypothesis: ETF/macro Daily patterns may be more stable than single-stock patterns.
- Data required: ETF/macro universe, product policy, OHLCV, and separate risk treatment.
- Main false positives: changing system objective, regime overfit, product-specific costs, and mixing stock-only conclusions with ETF behavior.
- Minimum acceptance: explicit `etf_macro` policy decision before any testing, with a separate protocol and reporting line.

## Priority Recommendation

Select `Gap continuation / gap reversal` as the next Daily search-space. It is not a rescue of PB/BO/CO/CW, needs no new external data for a first pre-registered protocol, and best fits the clean Daily infrastructure. The protocol must be strict about open-entry realism and must reject the line if continuation/reversal edge disappears under adverse open slippage, next-close entry placebo, or gap threshold perturbations.
