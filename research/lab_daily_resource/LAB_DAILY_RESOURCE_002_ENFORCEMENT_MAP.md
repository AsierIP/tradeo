# T-LAB-DAILY-RESOURCE-002 Enforcement Map

| Consumer | Job Type | Owner | Resource Class | Pre | Regular | Post | Closed | Enforcement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `backend/tradeo/modules/fast_chart_analysis/engine_registry.py` | `daily_watchlist_reeval` | `daily_watchlist` | fast engine | allow | allow | allow/high | allow/high | ENFORCED |
| `backend/tradeo/modules/resource_policy/enforcement.py` | `research_heavy` | `research` | heavy research | block | block | allow | allow/high | ENFORCED |
| `backend/tradeo/modules/resource_policy/enforcement.py` | `lab_paper_probe` | `lab` | Lab probe | allow | allow/high | block | block | ENFORCED |
| `backend/tradeo/modules/daily_swing/setup_watchlist.py` | `daily_watchlist_reeval` | `daily_watchlist` | daily metadata | allow | allow | allow/high | allow/high | GUARD_WRAPPER_ADDED |
| `backend/tradeo/modules/fast_chart_analysis/engine_registry.py` | `fast_engine` | `daily_watchlist` | fast engine | via daily reevaluation | via daily reevaluation | via daily reevaluation | via daily reevaluation | ENFORCED |
| Research heavy runners | `research_heavy` | `research` | CPU/scanner/cache | block | block | allow | allow/high | GUARD_WRAPPER_ADDED |
| Research capacity jobs | `research_heavy` | `research` | CPU/cache | block | block | allow | allow/high | GUARD_WRAPPER_ADDED |
| Intraday wave runners | `research_light` | `research` | light research | low | low | medium | high | DOC_ONLY |
| Daily after-close reevaluation | `daily_watchlist_reeval` | `daily_watchlist` | daily metadata | allow | allow | allow/high | allow/high | GUARD_WRAPPER_ADDED |
| Scheduler/worker wrappers | mixed | mixed | scheduler | policy-dependent | policy-dependent | policy-dependent | policy-dependent | NEEDS_FOLLOWUP |

## Notes

- `UNKNOWN` session fails closed.
- `paper_submit` and `live` are blocked by the enforcement wrapper.
- Lab Paper Probe is not granted submit authority by resource policy; its existing gates remain the only allowed submit path.
