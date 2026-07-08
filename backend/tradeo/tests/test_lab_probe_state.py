from __future__ import annotations

from datetime import date
from pathlib import Path

from tradeo.modules.lab_foxhunter.probe_state import ProbeStatePaths, acquire_session_lock, director_review_required, initial_state, is_eligible_for_review, load_or_create, update_probe_metrics, write_state


def test_session_lock_blocks_duplicate(tmp_path: Path) -> None:
    paths = ProbeStatePaths(runtime_root=tmp_path, trading_day=date(2026, 7, 6))
    state = load_or_create(paths)

    first, state = acquire_session_lock(paths, state)
    write_state(paths, state)
    second, state = acquire_session_lock(paths, state)

    assert first is True
    assert second is False
    assert state["state"] == "SESSION_BLOCKED"


def test_runtime_final_blocks_session_runner(tmp_path: Path) -> None:
    paths = ProbeStatePaths(runtime_root=tmp_path, trading_day=date(2026, 7, 6))
    paths.day_dir.mkdir(parents=True)
    paths.final_marker.write_text("{}\n", encoding="utf-8")

    acquired, state = acquire_session_lock(paths, initial_state(trading_day=date(2026, 7, 6)))

    assert acquired is False
    assert state["state"] == "SESSION_COMPLETE"


def test_eligible_review_requires_twenty_trades_and_quality() -> None:
    assert is_eligible_for_review(
        {
            "total_trades_toward_20": 20,
            "successes": 12,
            "net_expectancy_after_costs": 0.01,
            "paper_profit_factor": 1.16,
            "operational_errors": 0,
            "reconciliation_errors": 0,
        }
    )


def test_circuit_breaker_marks_director_review() -> None:
    state = update_probe_metrics(initial_state(trading_day=date(2026, 7, 6)), "LAB-GAP-REV-001", {"operational_errors": 1})

    assert state["probes"]["LAB-GAP-REV-001"]["blocked_until_director_review"] is True
    assert director_review_required(state) is True
