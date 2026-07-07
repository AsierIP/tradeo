from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


def _load_benchmark_module():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "run_intraday_process_pool_benchmark.py"
    spec = importlib.util.spec_from_file_location("run_intraday_process_pool_benchmark", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_diagnose_module():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "diagnose_discovery_benchmark.py"
    spec = importlib.util.spec_from_file_location("diagnose_discovery_benchmark", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_benchmark_summary_marks_zero_window_runs_invalid() -> None:
    benchmark = _load_benchmark_module()

    assert benchmark._invalid_benchmark_reason({"runs": 10, "windows": 0, "clusters": 12}) == (
        "zero_windows"
    )
    assert benchmark._invalid_benchmark_reason({"runs": 10, "windows": 20, "clusters": 0}) == (
        "zero_clusters"
    )
    assert benchmark._invalid_benchmark_reason({"runs": 10, "windows": 20, "clusters": 12}) is None


def test_benchmark_blocks_when_resource_policy_denies(monkeypatch, capsys) -> None:
    benchmark = _load_benchmark_module()
    calls: list[bool] = []
    decision = SimpleNamespace(
        allowed=False,
        deny_reason="resource_policy_denied:regular_market",
        to_dict=lambda: {
            "allowed": False,
            "deny_reason": "resource_policy_denied:research_heavy:regular_market",
            "can_submit_orders": False,
        },
    )

    monkeypatch.setattr(sys, "argv", ["run_intraday_process_pool_benchmark.py"])
    monkeypatch.setattr(benchmark, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(benchmark, "decide_with_market_session_policy", lambda *args, **kwargs: decision)
    monkeypatch.setattr(
        benchmark.worker,
        "_run_intraday_research_process_pool",
        lambda *args, **kwargs: calls.append(True),
    )

    code = benchmark.main()
    payload = json.loads(capsys.readouterr().out)

    assert code == 5
    assert payload["decision"] == "blocked_resource_policy"
    assert payload["resource_policy"]["allowed"] is False
    assert payload["research_result"]["status"] == "skipped"
    assert payload["research_result"]["reason"] == "resource_policy_denied"
    assert (
        payload["research_result"]["details"]["resource_policy"]["deny_reason"]
        == "resource_policy_denied:research_heavy:regular_market"
    )
    assert calls == []


def test_diagnose_auto_recent_groups_consecutive_valid_repeats() -> None:
    diagnose = _load_diagnose_module()
    rows = [
        {
            "id": run_id,
            "windows_sampled": 0 if run_id == 2507 else 50,
            "clusters_evaluated": 0 if run_id == 2507 else 4,
        }
        for run_id in range(2507, 2528)
    ]

    groups = diagnose._auto_recent_groups(
        rows,
        group_size=10,
        max_groups=4,
        existing=[],
    )

    assert [(group.label, group.first_id, group.last_id) for group in groups] == [
        ("repeat1_2508_2517", 2508, 2517),
        ("repeat2_2518_2527", 2518, 2527),
    ]


def test_diagnose_auto_recent_groups_skips_invalid_zero_cluster_rows() -> None:
    diagnose = _load_diagnose_module()
    rows = [
        {"id": run_id, "windows_sampled": 50, "clusters_evaluated": 4}
        for run_id in range(2518, 2528)
    ]
    rows[4] = {"id": 2522, "windows_sampled": 50, "clusters_evaluated": 0}

    groups = diagnose._auto_recent_groups(
        rows,
        group_size=10,
        max_groups=4,
        existing=[],
    )

    assert groups == []
    assert diagnose._is_valid_run(rows[4]) is False
    assert diagnose._invalid_reason(rows[4]) == "zero_clusters"


def test_worker_tail_summary_estimates_queue_critical_path() -> None:
    benchmark = _load_benchmark_module()
    worker_results = [
        {
            "timeframe": "15m",
            "chunk_number": 1,
            "chunk_count": 5,
            "chunk_index": 0,
            "symbols": 4,
            "estimated_cost": 40,
            "elapsed_seconds": 4.0,
            "submitted_order": 0,
        },
        {
            "timeframe": "5m",
            "chunk_number": 1,
            "chunk_count": 5,
            "chunk_index": 0,
            "symbols": 4,
            "estimated_cost": 30,
            "elapsed_seconds": 3.0,
            "submitted_order": 1,
        },
        {
            "timeframe": "15m",
            "chunk_number": 2,
            "chunk_count": 5,
            "chunk_index": 1,
            "symbols": 4,
            "estimated_cost": 20,
            "elapsed_seconds": 2.0,
            "submitted_order": 2,
        },
        {
            "timeframe": "5m",
            "chunk_number": 2,
            "chunk_count": 5,
            "chunk_index": 1,
            "symbols": 4,
            "estimated_cost": 10,
            "elapsed_seconds": 1.0,
            "submitted_order": 3,
        },
        {
            "timeframe": "15m",
            "chunk_number": 3,
            "chunk_count": 5,
            "chunk_index": 2,
            "symbols": 4,
            "estimated_cost": 50,
            "elapsed_seconds": 5.0,
            "submitted_order": 4,
        },
    ]

    summary = benchmark._worker_tail_summary(
        worker_results,
        elapsed_wall_s=10.0,
        process_workers=2,
    )

    assert summary["workers_reported"] == 5
    assert summary["total_worker_s"] == 15.0
    assert summary["max_worker_s"] == 5.0
    assert summary["pool_utilization_pct"] == 75.0
    assert summary["slowest_workers"][0]["chunk"] == "3_of_5"
    assert summary["estimated_queue"]["estimated_makespan_s"] == 10.0
    assert summary["estimated_queue"]["estimated_queue_wait_tail_s"] == 5.0
    assert summary["estimated_queue"]["critical_path"][-1]["chunk"] == "3_of_5"
