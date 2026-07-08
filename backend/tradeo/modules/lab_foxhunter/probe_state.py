from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any, Literal

DailyState = Literal[
    "PREMARKET_READY",
    "SESSION_ARMED",
    "SESSION_RUNNING",
    "SESSION_BLOCKED",
    "SESSION_COMPLETE",
    "POST_CLOSE_ANALYZED",
    "NEEDS_DIRECTOR_REVIEW",
]

ALLOWED_STATES: set[str] = {
    "PREMARKET_READY",
    "SESSION_ARMED",
    "SESSION_RUNNING",
    "SESSION_BLOCKED",
    "SESSION_COMPLETE",
    "POST_CLOSE_ANALYZED",
    "NEEDS_DIRECTOR_REVIEW",
}
INITIAL_STATE: DailyState = "PREMARKET_READY"
ELIGIBLE_DECISION = "ELIGIBLE_FOR_LAB_TO_FOXHUNTER_REVIEW"


@dataclass(frozen=True, slots=True)
class ProbeStatePaths:
    runtime_root: Path
    trading_day: date

    @property
    def day_dir(self) -> Path:
        return self.runtime_root / self.trading_day.isoformat()

    @property
    def state_file(self) -> Path:
        return self.day_dir / "probe_state.json"

    @property
    def session_lock(self) -> Path:
        return self.day_dir / "session_runner.lock"

    @property
    def final_marker(self) -> Path:
        return self.day_dir / "session_final.json"


def initial_state(*, trading_day: date, generated_at: datetime | None = None) -> dict[str, Any]:
    now = generated_at or datetime.now(timezone.utc)
    return {
        "schema": "tradeo.lab_foxhunter.probe_state.v1",
        "trading_day": trading_day.isoformat(),
        "state": INITIAL_STATE,
        "generated_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "session_runner_locked": False,
        "session_runner_lock_path": None,
        "runtime_final_exists": False,
        "blocked_probes": [],
        "probes": {
            "LAB-GAP-REV-001": empty_probe_metrics(),
            "LAB-GAP-REV-002": empty_probe_metrics(),
        },
        "decisions": [],
        "redacted": True,
    }


def empty_probe_metrics() -> dict[str, Any]:
    return {
        "trades_today": 0,
        "total_trades_toward_20": 0,
        "successes": 0,
        "net_expectancy_after_costs": None,
        "paper_profit_factor": None,
        "slippage_avg": None,
        "slippage_max": None,
        "latency_ms_avg": None,
        "operational_errors": 0,
        "reconciliation_errors": 0,
        "eligible_for_lab_to_foxhunter_review": False,
        "blocked_until_director_review": False,
    }


def load_or_create(paths: ProbeStatePaths, *, generated_at: datetime | None = None) -> dict[str, Any]:
    if paths.state_file.exists():
        return json.loads(paths.state_file.read_text(encoding="utf-8"))
    state = initial_state(trading_day=paths.trading_day, generated_at=generated_at)
    write_state(paths, state)
    return state


def write_state(paths: ProbeStatePaths, state: dict[str, Any]) -> None:
    paths.day_dir.mkdir(parents=True, exist_ok=True)
    paths.state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def transition(
    state: dict[str, Any],
    next_state: DailyState,
    *,
    reason: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    if next_state not in ALLOWED_STATES:
        raise ValueError(f"unsupported lab probe state: {next_state}")
    updated = dict(state)
    updated["state"] = next_state
    updated["updated_at"] = (now or datetime.now(timezone.utc)).isoformat()
    updated.setdefault("decisions", []).append({"state": next_state, "reason": reason, "at": updated["updated_at"]})
    return updated


def acquire_session_lock(paths: ProbeStatePaths, state: dict[str, Any], *, now: datetime | None = None) -> tuple[bool, dict[str, Any]]:
    updated = dict(state)
    updated["runtime_final_exists"] = paths.final_marker.exists()
    if paths.final_marker.exists():
        updated = transition(updated, "SESSION_COMPLETE", reason="runtime_final_exists", now=now)
        return False, updated
    if paths.session_lock.exists():
        updated["session_runner_locked"] = True
        updated["session_runner_lock_path"] = str(paths.session_lock)
        updated = transition(updated, "SESSION_BLOCKED", reason="duplicate_session_runner_lock", now=now)
        return False, updated
    paths.day_dir.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    paths.session_lock.write_text(json.dumps({"created_at": stamp, "trading_day": paths.trading_day.isoformat()}) + "\n", encoding="utf-8")
    updated["session_runner_locked"] = True
    updated["session_runner_lock_path"] = str(paths.session_lock)
    updated = transition(updated, "SESSION_RUNNING", reason="session_lock_acquired", now=now)
    return True, updated


def update_probe_metrics(state: dict[str, Any], probe_id: str, metrics: dict[str, Any]) -> dict[str, Any]:
    updated = dict(state)
    probes = dict(updated.setdefault("probes", {}))
    current = dict(probes.get(probe_id, empty_probe_metrics()))
    current.update(metrics)
    current["eligible_for_lab_to_foxhunter_review"] = is_eligible_for_review(current)
    if has_circuit_breaker(current):
        current["blocked_until_director_review"] = True
        blocked = set(updated.get("blocked_probes", []))
        blocked.add(probe_id)
        updated["blocked_probes"] = sorted(blocked)
    probes[probe_id] = current
    updated["probes"] = probes
    return updated


def is_eligible_for_review(metrics: dict[str, Any]) -> bool:
    return (
        int(metrics.get("total_trades_toward_20") or 0) >= 20
        and int(metrics.get("successes") or 0) >= 12
        and _positive(metrics.get("net_expectancy_after_costs"))
        and float(metrics.get("paper_profit_factor") or 0) > 1.15
        and int(metrics.get("operational_errors") or 0) == 0
        and int(metrics.get("reconciliation_errors") or 0) == 0
    )


def has_circuit_breaker(metrics: dict[str, Any]) -> bool:
    return int(metrics.get("operational_errors") or 0) > 0 or int(metrics.get("reconciliation_errors") or 0) > 0


def director_review_required(state: dict[str, Any]) -> bool:
    if state.get("blocked_probes"):
        return True
    probes = state.get("probes", {})
    return any(probe.get("eligible_for_lab_to_foxhunter_review") for probe in probes.values())


def final_daily_state(state: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    next_state: DailyState = "NEEDS_DIRECTOR_REVIEW" if director_review_required(state) else "POST_CLOSE_ANALYZED"
    return transition(state, next_state, reason="nightly_report_built", now=now)


def _positive(value: Any) -> bool:
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False
