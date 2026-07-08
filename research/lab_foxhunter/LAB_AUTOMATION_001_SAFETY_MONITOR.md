# LAB_AUTOMATION_001_SAFETY_MONITOR

- Automation mode is `LAB_AUTOMATION_ONLY`.
- Systemd services set `TRADEO_NO_LIVE=1`.
- Daily runner uses per-day runtime under `artifacts/runtime/lab_paper_probe/YYYY-MM-DD/`.
- Duplicate launch is blocked by `backend/tradeo/modules/lab_foxhunter/probe_state.py`.
- Final runtime presence blocks a second session runner for the same day.
- Live orders, real money orders, FoxHunter auto-promotion, live_candidate and paper_candidate clasico are explicitly disabled.
- Circuit-breaker evidence moves the state to `NEEDS_DIRECTOR_REVIEW`.
