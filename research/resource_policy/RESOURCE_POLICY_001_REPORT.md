# RESOURCE_POLICY_001 Report

Implemented a central market-session resource policy with New York session classification, injected holiday provider support, budget fields, deny reasons and read-only endpoint status.

The policy prioritizes Lab during regular market, Research during closed sessions, Daily watchlist after close, and fails closed for UNKNOWN sessions. It writes runtime status only under ignored `artifacts/runtime/resource_policy/latest.json`.

No broker submit paths were changed.
