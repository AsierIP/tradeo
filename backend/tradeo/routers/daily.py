from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException

from tradeo.core.config import Settings
from tradeo.core.security import require_admin
from tradeo.modules.daily_swing import setup_watchlist
from tradeo.modules.daily_swing.setup_watchlist import ARTIFACT_SCHEMA_VERSION
from tradeo.modules.resource_policy import (
    RESOURCE_ARTIFACT_WRITE,
    RESOURCE_IBKR_HISTORICAL_DATA,
    RESOURCE_LAB_BACKTEST,
    RESOURCE_LOCAL_CACHE_READ,
    RESOURCE_LOCAL_CACHE_WRITE,
    RESOURCE_MARKET_DATA_REFRESH,
    RESOURCE_MARKET_SESSION_STATUS,
    RESOURCE_POLICY_EVALUATE,
    RESOURCE_REPORT_WRITE,
    MarketSessionResourcePolicy,
)

router = APIRouter(prefix="/daily", tags=["daily"])

DAILY_SETUP_WATCHLIST_SCHEMA = "tradeo.daily.setup_watchlist.status.v1"
DAILY_SETUP_WATCHLIST_RESOURCES = (
    RESOURCE_POLICY_EVALUATE,
    RESOURCE_MARKET_SESSION_STATUS,
    RESOURCE_LOCAL_CACHE_READ,
    RESOURCE_LOCAL_CACHE_WRITE,
    RESOURCE_ARTIFACT_WRITE,
    RESOURCE_REPORT_WRITE,
    RESOURCE_LAB_BACKTEST,
    RESOURCE_MARKET_DATA_REFRESH,
    RESOURCE_IBKR_HISTORICAL_DATA,
)
SENSITIVE_DAILY_KEY_PARTS = (
    "secret",
    "token",
    "password",
    "api_key",
    "account",
    "acct",
    "username",
)
ACCOUNT_ID_PATTERN = re.compile(r"\b(?:DU|U|F|FA)\d{5,}\b", re.IGNORECASE)


def _daily_settings() -> Settings:
    return setup_watchlist.get_settings()


@router.get("/setup-watchlist")
def daily_setup_watchlist(
    _: str = Depends(require_admin),
    settings: Settings = Depends(_daily_settings),
) -> dict[str, object]:
    return build_daily_setup_watchlist_status(settings)


@router.get("/setup-watchlist/summary")
def daily_setup_watchlist_summary(
    _: str = Depends(require_admin),
    settings: Settings = Depends(_daily_settings),
) -> dict[str, object]:
    payload = build_daily_setup_watchlist_status(settings)
    watchlist = dict(payload.get("watchlist") or {})
    return {
        "schema_version": payload["schema_version"],
        "generated_at": payload["generated_at"],
        "read_only": payload["read_only"],
        "status": payload["status"],
        "active_count": watchlist.get("active_count", 0),
        "count": watchlist.get("count", 0),
        "entry_ready_count": watchlist.get("entry_ready_count", 0),
        "state_counts": watchlist.get("state_counts", {}),
        "contract": payload["contract"],
        "resource_policy": payload["resource_policy"],
    }


@router.get("/setup-watchlist/status")
def daily_setup_watchlist_status(
    _: str = Depends(require_admin),
    settings: Settings = Depends(_daily_settings),
) -> dict[str, object]:
    return build_daily_setup_watchlist_status(settings)


@router.get("/setup-watchlist/contract")
def daily_setup_watchlist_contract(
    _: str = Depends(require_admin),
    settings: Settings = Depends(_daily_settings),
) -> dict[str, object]:
    payload = build_daily_setup_watchlist_status(settings)
    return {
        "schema_version": payload["schema_version"],
        "generated_at": payload["generated_at"],
        "read_only": payload["read_only"],
        "status": payload["status"],
        "contract": payload["contract"],
        "blocked_actions": payload["blocked_actions"],
        "resource_policy": payload["resource_policy"],
    }


@router.get("/setup-watchlist/{setup_id}")
def daily_setup_watchlist_item(
    setup_id: str,
    _: str = Depends(require_admin),
    settings: Settings = Depends(_daily_settings),
) -> dict[str, object]:
    artifact = _load_watchlist_artifact(settings)
    for item in _artifact_items(artifact):
        if str(item.get("setup_id") or "") == setup_id:
            return item
    raise HTTPException(status_code=404, detail="daily setup watchlist item not found")


def build_daily_setup_watchlist_status(
    settings: Settings,
    *,
    policy: MarketSessionResourcePolicy | None = None,
) -> dict[str, object]:
    resource_policy = policy or MarketSessionResourcePolicy()
    decision = resource_policy.evaluate(DAILY_SETUP_WATCHLIST_RESOURCES)
    status = _daily_setup_status(decision.fail_closed, set(decision.blocked_resources))
    artifact = _load_watchlist_artifact(settings)
    watchlist = _watchlist_payload(artifact)
    return {
        "schema_version": DAILY_SETUP_WATCHLIST_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "status": status,
        "cadence": "daily",
        "timeframe": "1d",
        "runtime": {
            "trading_mode": settings.trading_mode,
            "live_armed": settings.live_armed,
            "kill_switch_enabled": settings.kill_switch_enabled,
            "ibkr_readonly": settings.ibkr_readonly,
        },
        "watchlist": watchlist,
        "contract": {
            "allowed_methods": ["GET"],
            "write_endpoint_available": False,
            "resource_policy_required": True,
            "order_submission_allowed": False,
            "paper_order_submission_allowed": False,
            "live_order_submission_allowed": False,
            "signal_output_allowed": False,
            "fox_hunter_promotion_allowed": False,
            "secret_values_exposed": False,
        },
        "resource_policy": decision.to_dict(),
        "next_actions": [
            "populate_daily_setup_watchlist_artifact",
            "review_resource_policy_status",
        ],
        "blocked_actions": [
            "submit_orders",
            "emit_signals",
            "promote_to_fox_hunter",
            "arm_live",
        ],
    }


def _daily_setup_status(fail_closed: bool, blocked_resources: set[str]) -> str:
    if fail_closed:
        return "resource_policy_fail_closed"
    if {
        RESOURCE_LOCAL_CACHE_WRITE,
        RESOURCE_ARTIFACT_WRITE,
        RESOURCE_REPORT_WRITE,
        RESOURCE_LAB_BACKTEST,
        RESOURCE_MARKET_DATA_REFRESH,
        RESOURCE_IBKR_HISTORICAL_DATA,
    } & blocked_resources:
        return "waiting_for_market_close"
    return "ready_for_offline_setup"


def _load_watchlist_artifact(settings: Settings) -> dict[str, Any] | None:
    for path in _watchlist_artifact_paths(settings):
        if not path.exists() or not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            safe = _redact_sensitive(payload)
            safe["_source_name"] = path.name
            return safe
    return None


def _watchlist_artifact_paths(settings: Settings) -> tuple[Path, ...]:
    artifacts = Path(settings.artifacts_dir)
    return (
        artifacts / "runtime" / "daily_swing" / "setup_watchlist" / "latest.json",
        artifacts / "runtime" / "daily_setup_watchlist" / "latest.json",
        artifacts / "runtime" / "daily_setup_watchlist.json",
        artifacts / "daily_setup_watchlist.json",
        Path("research") / "lab_daily_resource" / "daily_setup_watchlist.json",
    )


def _watchlist_payload(artifact: Mapping[str, Any] | None) -> dict[str, object]:
    if artifact is None:
        return {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "state": "not_populated",
            "source": "contract_placeholder",
            "symbols": [],
            "items": [],
            "count": 0,
            "active_count": 0,
            "entry_ready_count": 0,
            "state_counts": {},
            "reason": "daily_setup_watchlist_artifact_not_loaded",
            "orders_allowed": False,
            "paper_allowed": False,
            "live_allowed": False,
        }
    items = _artifact_items(artifact)
    state_counts = dict(artifact.get("state_counts") or _state_counts(items))
    return {
        "schema_version": artifact.get("schema_version") or ARTIFACT_SCHEMA_VERSION,
        "state": artifact.get("status") or "loaded",
        "source": artifact.get("_source_name") or "artifact",
        "generated_at": artifact.get("generated_at"),
        "symbols": [item["symbol"] for item in items if isinstance(item.get("symbol"), str)],
        "items": items,
        "count": len(items),
        "active_count": sum(
            1
            for item in items
            if str(item.get("state") or item.get("status"))
            not in {"blocked", "expired", "rejected", "invalidated"}
        ),
        "entry_ready_count": int(
            artifact.get("entry_ready_count") or state_counts.get("entry_ready") or 0
        ),
        "state_counts": state_counts,
        "reason": None,
        "orders_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
    }


def _artifact_items(artifact: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if artifact is None:
        return []
    raw_items = artifact.get("items")
    if not isinstance(raw_items, list):
        return []
    return [dict(item) for item in raw_items if isinstance(item, Mapping)]


def _state_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        state = str(item.get("state") or item.get("status") or "unknown")
        counts[state] = counts.get(state, 0) + 1
    return counts


def _redact_sensitive(value: Any) -> Any:
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if any(part in key_text.lower() for part in SENSITIVE_DAILY_KEY_PARTS):
                out[key_text] = "<redacted>"
            else:
                out[key_text] = _redact_sensitive(item)
        return out
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    if isinstance(value, str) and ACCOUNT_ID_PATTERN.search(value):
        return ACCOUNT_ID_PATTERN.sub("<redacted-account>", value)
    return value
