# LAB_AUTOMATION_001_SCHEDULER

- Scope: daily Lab Paper Probe automation only.
- Scheduler: systemd user timers, not permanent cron.
- Times: premarket 09:00 ET, session runner 09:35 ET, mid collector 09:45 ET, close collector 16:05 ET, nightly Director report 16:20 ET.
- Unit renderer: `scripts/install_lab_daily_systemd.py --write`.
- Session launcher: `scripts/run_lab_daily_session.sh`.
- Live, FoxHunter auto-promotion, live_candidate, paper_candidate clasico, gh and main push remain disabled.
