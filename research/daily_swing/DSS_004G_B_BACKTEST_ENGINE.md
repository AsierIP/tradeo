# DSS-004G-B Backtest Engine

DSS-CW-001 was executed as a frozen episode-window rule using EPISODE_GAP_5, a five-session eligible window, first eligible portfolio-filtered decision date, theoretical next-open entry, and ten-session close exit.

| Policy | OOS trades | OOS symbols | OOS exp x2 | OOS PF x2 | Last 12m exp x2 | Cost x3 exp | Max DD | Worst loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL_ELIGIBLE_EPISODES | 843 | 147 | 0.7336 | 1.2516 | 0.9992 | 0.3147 | 568.7978 | 14 |
| ONE_ACTIVE_PER_SYMBOL_EPISODE | 814 | 147 | 0.7380 | 1.2517 | 1.0424 | 0.2966 | 585.2215 | 14 |
| MAX_2_NEW_EPISODES_PER_DAY | 529 | 137 | 0.8739 | 1.3802 | 1.1921 | 0.5898 | 213.3251 | 8 |
