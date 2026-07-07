# Agent C - Improvement Proposer

The proposer applies the materiality formula:

`improvement_score = severity * confidence * recurrence_factor + estimated_benefit - estimated_change_risk`

Recurrence factor:

- `1.0` for one session;
- `1.5` for two sessions;
- `2.0` for three or more sessions.

Classifications:

- `AUTO_FIX_ALLOWED` only for small, local, reversible changes that avoid submit/live/paper gates, scoring, thresholds, strategy, session timing, `.env` real, IBKR, market data, order paths, and sensitive areas, with tests available and score >= 4.
- `DIRECTOR_REVIEW_REQUIRED` for sensitive areas, risk > 2 with material score, or uncertain impact.
- `NO_CHANGE` for score < 3, insufficient evidence, low impact, or cooldown.
- `BLOCKER_STOP_NEXT_SESSION` for explicit safety blockers.

Cooldowns and caps:

- same component max once per day;
- same runner not two nights in a row except blockers;
- max 3 auto-fixes per night.
