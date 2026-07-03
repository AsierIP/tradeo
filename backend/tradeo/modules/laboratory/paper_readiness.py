from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
import json
import math
import os

from tradeo.modules.laboratory.vwap_shadow_recorder import redact_shadow_record

ReadinessStatus = Literal["READY_FOR_DIRECTOR_PAPER_REVIEW", "BLOCKED", "NOT_READY"]


@dataclass(frozen=True, slots=True)
class PaperReadinessInput:
    symbol: str = "AAPL"
    side: Literal["long", "short"] = "long"
    entry: float = 100.0
    stop: float = 98.5
    target: float = 106.0
    quantity: int = 1


def build_paper_readiness_report(
    *,
    settings: Any | None = None,
    sample: PaperReadinessInput | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    settings = settings or _default_settings()
    sample = sample or PaperReadinessInput()
    generated_at = now or datetime.now(timezone.utc)
    checks = _readiness_checks(settings)
    blockers = [check["name"] for check in checks if check["severity"] == "blocker" and not check["passed"]]
    gaps = [check["name"] for check in checks if check["severity"] == "gap" and not check["passed"]]
    status: ReadinessStatus
    if blockers:
        status = "BLOCKED"
    elif gaps:
        status = "NOT_READY"
    else:
        status = "READY_FOR_DIRECTOR_PAPER_REVIEW"
    report = {
        "schema_version": "tradeo.lab_paper_readiness.v1",
        "generated_at": generated_at.isoformat(),
        "status": status,
        "paper_readiness_decision": status,
        "blockers": blockers,
        "gaps": gaps,
        "checks": checks,
        "dry_run_only": True,
        "submit_allowed": False,
        "orders_allowed": False,
        "paper_orders_sent": False,
        "live_orders_sent": False,
        "submit_order_called": False,
        "ibkr_used": False,
        "wave_executed": False,
        "paper_allowed_actual": bool(_setting(settings, "intraday_paper_enabled", False)),
        "live_allowed": False,
        "bracket_order_preview": _build_bracket_preview(sample),
        "redacted": True,
    }
    return redact_shadow_record(report)


def write_paper_readiness_artifacts(report: dict[str, Any], *, json_out: str | Path, md_out: str | Path) -> None:
    json_path = Path(json_out)
    md_path = Path(md_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    md_path.write_text(render_paper_readiness_markdown(report), encoding="utf-8")


def render_paper_readiness_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Lab Paper Readiness",
        "",
        f"- status: `{report.get('status')}`",
        f"- paper_readiness_decision: `{report.get('paper_readiness_decision')}`",
        f"- dry_run_only: `{report.get('dry_run_only')}`",
        f"- submit_allowed: `{report.get('submit_allowed')}`",
        f"- paper_allowed_actual: `{report.get('paper_allowed_actual')}`",
        f"- blockers: `{report.get('blockers')}`",
        f"- gaps: `{report.get('gaps')}`",
        "",
        "## Checks",
        "",
    ]
    for check in report.get("checks", []):
        lines.append(f"- {check['name']}: `{check['passed']}` ({check['severity']})")
    lines.extend(
        [
            "",
            "The bracket preview is dry-run only. This script never imports broker adapters and never sends orders.",
            "",
        ]
    )
    return "\n".join(lines)


def settings_from_env_file(path: str | Path | None = None) -> dict[str, Any]:
    values = _settings_defaults()
    if path is not None:
        values.update(_parse_env_file(Path(path)))
    elif Path(".env").exists():
        values.update(_parse_env_file(Path(".env")))
    values.update({key: value for key, value in os.environ.items() if key.startswith("TRADEO_")})
    return {_field_name(key): _coerce_value(value) for key, value in values.items()}


def _readiness_checks(settings: Any) -> list[dict[str, Any]]:
    trading_mode = str(_setting(settings, "trading_mode", "paper")).lower()
    live_trading_enabled = bool(_setting(settings, "live_trading_enabled", False))
    kill_switch_enabled = bool(_setting(settings, "kill_switch_enabled", False))
    live_armed = (
        trading_mode == "live"
        and live_trading_enabled
        and str(_setting(settings, "live_trading_confirmation_value", ""))
        == str(_setting(settings, "live_trading_confirmation_phrase", "I_ACCEPT_LIVE_MARKET_RISK"))
        and not kill_switch_enabled
    )
    return [
        _check("trading_mode_not_live", trading_mode != "live", "blocker", trading_mode),
        _check("live_trading_disabled", not live_trading_enabled, "blocker", live_trading_enabled),
        _check("live_not_armed", not live_armed, "blocker", live_armed),
        _check(
            "intraday_live_disabled",
            not bool(_setting(settings, "intraday_live_enabled", False)),
            "blocker",
            _setting(settings, "intraday_live_enabled", False),
        ),
        _check(
            "intraday_paper_disabled_for_tlab002",
            not bool(_setting(settings, "intraday_paper_enabled", False)),
            "blocker",
            _setting(settings, "intraday_paper_enabled", False),
        ),
        _check("ibkr_readonly", bool(_setting(settings, "ibkr_readonly", True)), "blocker", _setting(settings, "ibkr_readonly", True)),
        _check(
            "ibkr_not_live_port",
            int(_setting(settings, "ibkr_port", 7497) or 0) not in {4001, 7496},
            "blocker",
            _setting(settings, "ibkr_port", 7497),
        ),
        _check(
            "market_orders_disabled",
            not bool(_setting(settings, "ibkr_allow_market_orders", False)),
            "blocker",
            _setting(settings, "ibkr_allow_market_orders", False),
        ),
        _check(
            "lab_auto_submit_paper_disabled",
            not bool(_setting(settings, "laboratory_auto_submit_paper_orders", True)),
            "blocker",
            _setting(settings, "laboratory_auto_submit_paper_orders", True),
        ),
        _check(
            "fox_auto_submit_live_disabled",
            not bool(_setting(settings, "fox_hunter_auto_submit_live_orders", False)),
            "blocker",
            _setting(settings, "fox_hunter_auto_submit_live_orders", False),
        ),
        _check(
            "reconciliation_auto_repair_paper_exits_disabled",
            not bool(_setting(settings, "reconciliation_auto_repair_paper_exits", False)),
            "blocker",
            _setting(settings, "reconciliation_auto_repair_paper_exits", False),
        ),
        _check("kill_switch_clear", not kill_switch_enabled, "gap", kill_switch_enabled),
        _check(
            "max_trades_per_day_defined",
            int(_setting(settings, "intraday_max_trades_per_day", 0) or 0) > 0,
            "gap",
            _setting(settings, "intraday_max_trades_per_day", 0),
        ),
        _check(
            "max_daily_loss_defined",
            _positive(_setting(settings, "intraday_daily_loss_limit_pct", 0.0)),
            "gap",
            _setting(settings, "intraday_daily_loss_limit_pct", 0.0),
        ),
        _check(
            "max_position_value_defined",
            _positive(_setting(settings, "max_position_value_pct", 0.0)),
            "gap",
            _setting(settings, "max_position_value_pct", 0.0),
        ),
        _check(
            "ibkr_max_order_value_defined",
            _positive(_setting(settings, "ibkr_max_order_value_usd", 0.0)),
            "gap",
            _setting(settings, "ibkr_max_order_value_usd", 0.0),
        ),
    ]


def _build_bracket_preview(sample: PaperReadinessInput) -> dict[str, Any]:
    return {
        "symbol": sample.symbol.upper(),
        "side": sample.side,
        "quantity": sample.quantity,
        "entry": sample.entry,
        "stop": sample.stop,
        "target": sample.target,
        "order_type": "limit_bracket_preview",
        "dry_run_only": True,
        "submit_allowed": False,
        "what_if_enabled": False,
    }


def _check(name: str, passed: bool, severity: Literal["blocker", "gap"], observed: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "severity": severity, "observed": observed}


def _positive(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0


def _default_settings() -> Any:
    try:
        from tradeo.core.config import get_settings
    except ImportError:
        return settings_from_env_file()
    return get_settings()


def _setting(settings: Any, name: str, default: Any) -> Any:
    if isinstance(settings, dict):
        return settings.get(name, default)
    return getattr(settings, name, default)


def _settings_defaults() -> dict[str, str]:
    return {
        "TRADEO_TRADING_MODE": "paper",
        "TRADEO_LIVE_TRADING_ENABLED": "false",
        "TRADEO_LIVE_TRADING_CONFIRMATION_PHRASE": "I_ACCEPT_LIVE_MARKET_RISK",
        "TRADEO_LIVE_TRADING_CONFIRMATION_VALUE": "",
        "TRADEO_KILL_SWITCH_ENABLED": "false",
        "TRADEO_INTRADAY_LIVE_ENABLED": "false",
        "TRADEO_INTRADAY_PAPER_ENABLED": "false",
        "TRADEO_IBKR_PORT": "7497",
        "TRADEO_INTRADAY_MAX_TRADES_PER_DAY": "0",
        "TRADEO_INTRADAY_DAILY_LOSS_LIMIT_PCT": "0.005",
        "TRADEO_MAX_POSITION_VALUE_PCT": "0.45",
        "TRADEO_IBKR_READONLY": "true",
        "TRADEO_IBKR_MAX_ORDER_VALUE_USD": "1500",
        "TRADEO_IBKR_ALLOW_MARKET_ORDERS": "false",
        "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS": "true",
        "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS": "false",
        "TRADEO_RECONCILIATION_AUTO_REPAIR_PAPER_EXITS": "false",
    }


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("TRADEO_"):
            values[key] = value.strip().strip("'\"")
    return values


def _field_name(env_key: str) -> str:
    return env_key.removeprefix("TRADEO_").lower()


def _coerce_value(value: Any) -> Any:
    text = str(value).strip()
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text
