# DSS-004E Final Report

## A. Executive Summary

DSS-004E repeated frozen `DSS-CO-001` on the validated research-150 cache, cache-only and without tuning. Data guard passed, the edge remains positive in research-150, and concentration improves materially versus pilot-50. The decision is still not PASS because placebo shifts +1, +2, +5, and +10 beat or match the base OOS result.

Decision: `DSS_CO_001_RESEARCH_WARNING_RESEARCH150`.
Bias decision: `BIAS_FAIL`.

## B. Real Path Used

Repository path: `/home/vboxuser/tradeo-worktrees/daily-swing-paper-probe-001`.

## C. Branch / Commit / Push

Branch: `feature/daily-swing-paper-probe-001`.
Commit/push: pending at report generation.

## D. Data Used

Cache: `artifacts/runtime/daily_swing/daily_ohlcv_research`.
Universe: `artifacts/runtime/daily_swing/dss_003e_research_universe_checked.csv`.
Operational symbols: 150.
Benchmarks: SPY/QQQ, benchmark-only.
Last valid bar: `2026-07-02`.
False `2026-07-03` bar present: `false`.

## E. DSS-CO-001 Definition

The DSS-CO-001 definition is unchanged: SPY/QQQ regime positive, symbol trend positive, `ATR14_pct(t-1)` at or below its rolling 120-session p40 through `t-1`, signal at close `t`, entry at next open `t+1`, exit after 10 sessions at close or truncated at sample end, costs x1/x2/x3 = 10/20/30 bps round-trip.

## F-H. Policy Metrics

| Policy | Trades | OOS trades | OOS symbols | OOS exp x2 | OOS PF x2 | Last 12m exp x2 | Cost x3 exp | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL_EVENTS | 15096 | 9465 | 147 | 0.9806006282639054 | 1.3707189848878556 | 0.5920184968728122 | 0.6662202048839561 | 4059.083925845 |
| ONE_ACTIVE_PER_SYMBOL | 2114 | 1311 | 147 | 0.9723070300262958 | 1.352405621507822 | 0.7438159504841553 | 0.5050791382271806 | 556.5950396045869 |
| MAX_2_NEW_TRADES_PER_DAY_SIM | 897 | 576 | 116 | 0.4572207791281914 | 1.1929943203637217 | 0.5655175598583358 | 0.19136260467711005 | 225.92636420414965 |

## I. Pilot-50 Comparison

ONE_ACTIVE pilot OOS exp/PF/symbols: `1.7851437283468126` / `1.503132671531211` / `49`.
ONE_ACTIVE research OOS exp/PF/symbols: `0.9723070300262958` / `1.352405621507822` / `147`.
MAX2 pilot OOS exp/PF/symbols: `1.3861419565310171` / `1.4034079691261219` / `48`.
MAX2 research OOS exp/PF/symbols: `0.4572207791281914` / `1.1929943203637217` / `116`.
Concentration improved: ONE_ACTIVE top3 contribution fell from `0.3075629619326353` to `0.14444896768327475`, and top5 trades from `0.11917629770167239` to `0.05496015933305685`.

## J-K. Bias / Placebo / Adversarial

Base ONE_ACTIVE OOS exp/PF: `0.9723070300262958` / `1.352405621507822`.
Placebo +1: `1.1364196507327922` / `1.4128683615252415`.
Placebo +2: `1.1444662236351169` / `1.4356144342408645`.
Placebo +5: `1.0648203620531367` / `1.4082855480988434`.
Placebo +10: `0.9814471745080653` / `1.3530586319556106`.
TREND_ONLY: `0.5067122347756157` / `1.1618177550278237`.
RANDOM_MATCHED: `0.7047437379180985` / `1.2339202873402906`.
VOL_HIGH_ONLY: `-0.15512121462200928` / `0.95795845506022`.
Next close: `0.9875810400369631` / `1.3674402349062993`.
Adverse +10 bps: `0.8723070300262957` / `1.3108190436091407`.
FDR/WRC/SPA remains `NOT_IMPLEMENTED_GAP_FOR_LIVE_OR_PAPER_APPROVAL`.

## L-M. Operability / Safety

ONE_ACTIVE OOS and MAX2 OOS are positive. MAX2 OOS PF is `1.1929943203637217`, slightly above the 1.15 preference, but materially weaker than pilot-50. No orders, no paper execution, no live execution, no cron, no operational preview, no operational signals, no merge, and no `.env` real modification.

## N-O. Decision / Next Phase

Final decision: `DSS_CO_001_RESEARCH_WARNING_RESEARCH150`.

Recommended next step: Director review. The most useful continuation is robustness/statistical work around timing specificity and FDR/WRC/SPA before any DSS-005 preview design. Do not generate preview or paper-probe execution from this result.
