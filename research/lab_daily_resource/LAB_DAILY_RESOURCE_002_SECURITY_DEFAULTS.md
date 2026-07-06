# T-LAB-DAILY-RESOURCE-002 Security Defaults

- status: `PASS`
- generated_at: `2026-07-06T20:30:00Z`
- scope: `.env.example`, `tradeo.core.config.Settings`, versioned examples/config defaults

## Changes

- `TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false` in `.env.example`.
- `Settings.laboratory_auto_submit_paper_orders=False`.
- Existing `TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS=false` remains unchanged.

## Safety Review

- No `.env` file was versioned.
- No live default was enabled.
- No live-armed default was enabled.
- No market-order default was enabled.
- Existing defensive/test/documentation strings mentioning live/paper gates were reviewed as false positives.

## Decision

`SECURITY_DEFAULTS_HARDENED`
