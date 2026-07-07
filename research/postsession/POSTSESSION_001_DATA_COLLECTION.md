# Agent A - Session Data Collector

For T-POSTSESSION-IMPROVEMENT-001 the collector design was implemented in `backend/tradeo/modules/postsession/improvement_agent.py`.

Responsibilities covered:

- Collect permitted session artifacts from Lab, Daily, Research, reconciliation, runtime, and validation outputs.
- Redact account identifiers and sensitive keys.
- Reject `.env`, memory files, secrets, tokens, private keys, and unapproved raw runtime inputs.
- Normalize injected or artifact-provided findings into a scored finding schema.
- Roll up trades, fills, cancels, rejects, missing logs, and runtime completeness.

Initial bootstrap run is intentionally not executed against live broker or market data.

