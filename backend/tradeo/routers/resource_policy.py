from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from tradeo.core.config import Settings, get_settings
from tradeo.core.security import require_admin
from tradeo.modules.resource_policy import (
    DEFAULT_CLOSED_SESSION_ALLOWLIST,
    DEFAULT_OPEN_SESSION_ALLOWLIST,
    DAILY_FOCUS_FROZEN_RESOURCES,
    DAILY_FOCUS_RESOURCE_ALLOWLIST,
    PROHIBITED_RESOURCES,
    RESOURCE_ARTIFACT_WRITE,
    RESOURCE_IBKR_HISTORICAL_DATA,
    RESOURCE_LAB_BACKTEST,
    RESOURCE_LIVE_ORDER,
    RESOURCE_LOCAL_CACHE_READ,
    RESOURCE_LOCAL_CACHE_WRITE,
    RESOURCE_MARKET_DATA_REFRESH,
    RESOURCE_MARKET_SESSION_STATUS,
    RESOURCE_ORDER_PREVIEW,
    RESOURCE_PAPER_ORDER,
    RESOURCE_POLICY_EVALUATE,
    RESOURCE_REALTIME_MARKET_DATA,
    RESOURCE_REPORT_WRITE,
    RESOURCE_SIGNAL_OUTPUT,
    MarketSessionResourcePolicy,
)
from tradeo.modules.resource_policy.market_session_resource_policy import (
    MarketSessionResourcePolicy as MarketSessionBudgetPolicy,
)
from tradeo.services.ibkr_pacing import IbkrPacingBudget

router = APIRouter(prefix="/resource-policy", tags=["resource-policy"])

RESOURCE_POLICY_STATUS_SCHEMA = "tradeo.resource_policy.status.v1"
RESOURCE_POLICY_STATUS_RESOURCES = (
    RESOURCE_POLICY_EVALUATE,
    RESOURCE_MARKET_SESSION_STATUS,
    RESOURCE_LOCAL_CACHE_READ,
    RESOURCE_LOCAL_CACHE_WRITE,
    RESOURCE_ARTIFACT_WRITE,
    RESOURCE_REPORT_WRITE,
    RESOURCE_LAB_BACKTEST,
    RESOURCE_MARKET_DATA_REFRESH,
    RESOURCE_IBKR_HISTORICAL_DATA,
    RESOURCE_REALTIME_MARKET_DATA,
    RESOURCE_ORDER_PREVIEW,
    RESOURCE_PAPER_ORDER,
    RESOURCE_LIVE_ORDER,
    RESOURCE_SIGNAL_OUTPUT,
)


@router.get("/status")
def resource_policy_status(
    _: str = Depends(require_admin),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return build_resource_policy_status(settings)


def build_resource_policy_status(
    settings: Settings,
    *,
    policy: MarketSessionResourcePolicy | None = None,
) -> dict[str, object]:
    resource_policy = policy or MarketSessionResourcePolicy(settings=settings)
    decision = resource_policy.evaluate(RESOURCE_POLICY_STATUS_RESOURCES)
    budget = _resource_budget_status(settings)
    return {
        "schema_version": RESOURCE_POLICY_STATUS_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        **budget,
        "runtime": {
            "trading_mode": settings.trading_mode,
            "live_armed": settings.live_armed,
            "kill_switch_enabled": settings.kill_switch_enabled,
            "ibkr_readonly": settings.ibkr_readonly,
            "market_data_provider": settings.market_data_provider,
        },
        "policy": decision.to_dict(),
        "resources": {
            "evaluated": list(RESOURCE_POLICY_STATUS_RESOURCES),
            "open_session_allowlist": sorted(DEFAULT_OPEN_SESSION_ALLOWLIST),
            "closed_session_allowlist": sorted(DEFAULT_CLOSED_SESSION_ALLOWLIST),
            "daily_focus_allowlist": sorted(DAILY_FOCUS_RESOURCE_ALLOWLIST),
            "daily_focus_frozen": sorted(DAILY_FOCUS_FROZEN_RESOURCES),
            "always_prohibited": sorted(PROHIBITED_RESOURCES),
        },
        "pacing": _pacing_snapshot(),
        "safety": {
            "write_endpoints_exposed": False,
            "order_resources_prohibited": True,
            "paper_order_submission_allowed": False,
            "live_order_submission_allowed": False,
            "signal_output_allowed": False,
            "fox_hunter_promotion_allowed": False,
            "secret_values_exposed": False,
        },
    }


def _pacing_snapshot() -> dict[str, object]:
    metrics = IbkrPacingBudget().metrics()
    request_types: dict[str, object] = {}
    for request_type, payload in dict(metrics.get("request_types") or {}).items():
        windows = []
        for window in list(dict(payload).get("windows") or []):
            data = dict(window)
            capacity = int(data.get("capacity") or 0)
            daily_reserved = int(data.get("daily_reserved") or 0)
            windows.append(
                {
                    "window_seconds": data.get("window_seconds"),
                    "capacity": capacity,
                    "used": data.get("used"),
                    "remaining": data.get("remaining"),
                    "daily_reserved": daily_reserved,
                    "intraday_capacity": max(0, capacity - daily_reserved),
                }
            )
        request_types[str(request_type)] = {"windows": windows}
    return {
        "generated_at": metrics.get("generated_at"),
        "request_types": request_types,
    }


def _resource_budget_status(settings: Settings) -> dict[str, object]:
    policy = MarketSessionBudgetPolicy(settings=settings)
    current = policy._coerce_now(None)
    state = policy.forced_session_state or policy.classify_session(current)
    return policy._budget_for_state(state, current).public_status()


def resource_names_by_access(payload: dict[str, Any]) -> dict[str, list[str]]:
    policy = dict(payload.get("policy") or {})
    return {
        "allowed": list(policy.get("allowed_resources") or []),
        "blocked": list(policy.get("blocked_resources") or []),
    }
