# MEMORY

## Preferences

- Use Telegram through the Tradeo bot as the dedicated channel for Tradeo-specific conversations. The configured bot username is @TradeoInternalBot; do not store bot tokens in memory.
- When checking whether Daily and intraday Research are running in parallel and continuously searching, send the result to Asier as an audio message in Telegram.
- Asier wants Telegram alerts whenever Tradeo finds a new non-REJECTED pattern. Backend emits `audit_logs.action='new_pattern_discovered'`; cron `tradeo-new-pattern-alerts` consumes those events every minute and stores state in `memory/pattern-alert-audit-state.json`.
- In Chat sessions, warn Asier in Spanish when approaching the context/compaction limit, before compaction happens when possible.

## Tradeo Optimization Notes

- 2026-06-28 loop closeout: Asier explicitly stopped the optimization loops. Final best benchmark reference was DB group `2968-2979`, DB wall `10.235s`, `9,300` windows, `118` clusters, `0` errors/skips; future acceptance threshold for a >=3% improvement is `<=9.928s` in clean explicit groups.
