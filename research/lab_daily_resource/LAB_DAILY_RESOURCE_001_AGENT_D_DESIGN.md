# Agent D Design - Fast Engine / Scheduler Integration

## Objective

Create a registry/scaffold so Lab, Research and Daily watchlist can request the fast chart engine through Resource Policy.

## Files

- `backend/tradeo/modules/fast_chart_analysis/engine_registry.py`
- fast engine registry tests.

## Contracts

- Input: owner, job type, heavy flag, optional engine id and resource snapshot.
- Output: allowed/blocked decision, priority, budget, deny reason, `can_submit_orders=false`.

## Risks

- Simultaneous HIGH priority owners.
- UNKNOWN session fail-open.
- Registry becoming a hidden order path.

## Tests

- Lab priority in REGULAR_MARKET.
- Research priority in MARKET_CLOSED.
- Research heavy blocked in REGULAR_MARKET.
- Daily priority POST_MARKET.
- UNKNOWN fails closed.

## Fail-Safe

Unknown owner, missing policy, disabled engine, and UNKNOWN session return blocked with deny reason.
