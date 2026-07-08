from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tradeo.modules.research_capacity.capacity_metrics import (
    CapacityRunConfig,
    REQUIRED_METRIC_FIELDS,
    ResearchCapacitySafetyError,
    build_experiment_queue,
    enforce_capacity_guards,
    metric_schema,
    research_surface_rows,
    run_capacity_plan,
    run_capacity_microbench,
    write_capacity_docs,
)


def test_capacity_schema_contains_required_fields() -> None:
    schema = metric_schema()

    assert "elapsed_seconds" in schema["required_fields"]
    assert "decision" in schema["required_fields"]
    assert len(schema["required_fields"]) == len(REQUIRED_METRIC_FIELDS)


@pytest.mark.parametrize(
    ("flag", "message"),
    [
        ("cache_only", "cache-only"),
        ("dry_run", "dry-run"),
        ("no_downloads", "downloads"),
        ("no_ibkr", "IBKR"),
        ("no_orders", "order"),
        ("no_signals", "signal"),
        ("no_preview", "preview"),
        ("no_candidate_approval", "candidate approval"),
    ],
)
def test_microbench_blocks_unsafe_flags(tmp_path: Path, flag: str, message: str) -> None:
    config = _config(tmp_path, **{flag: False})

    with pytest.raises(ResearchCapacitySafetyError, match=message):
        enforce_capacity_guards(config)


def test_microbench_respects_max_workload(tmp_path: Path) -> None:
    runtime = tmp_path / "artifacts" / "runtime"
    cache = runtime / "ohlcv_cache"
    cache.mkdir(parents=True)
    for idx in range(3):
        _cache_file(cache / f"AAA{idx}_30m_60d.csv")
    payload = run_capacity_microbench(_config(tmp_path, runtime_root=runtime, max_workload=2))

    assert payload["cache_files_sampled"] == 2
    assert payload["metrics"][1]["clusters_processed"] == 2


def test_microbench_blocks_invalid_max_workload(tmp_path: Path) -> None:
    with pytest.raises(ResearchCapacitySafetyError, match="max workload"):
        run_capacity_microbench(_config(tmp_path, max_workload=1001))


def test_microbench_records_elapsed_seconds(tmp_path: Path) -> None:
    payload = run_capacity_microbench(_config(tmp_path))

    assert payload["elapsed_seconds"] >= 0
    assert all(set(REQUIRED_METRIC_FIELDS) <= set(row) for row in payload["metrics"])


def test_microbench_writes_json_and_csv(tmp_path: Path) -> None:
    payload = run_capacity_microbench(_config(tmp_path))

    assert Path(payload["runtime_paths"]["json"]).exists()
    assert Path(payload["runtime_paths"]["csv"]).exists()
    with Path(payload["runtime_paths"]["csv"]).open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header == REQUIRED_METRIC_FIELDS


def test_experiment_queue_requires_director_for_execution() -> None:
    queue = build_experiment_queue()

    assert queue[0]["experiment_id"] == "RC-002-A"
    assert all("no IBKR" in row["safety_requirements"] for row in queue)
    assert any(row["needs_director_approval"] for row in queue)


def test_research_surface_inventory_classifies_safe_and_blocked_paths() -> None:
    rows = research_surface_rows()

    assert any(row["cache_only_capable"] and row["dry_run_capable"] for row in rows)
    assert any(row["ibkr_required"] for row in rows)
    assert any(row["can_generate_preview_or_orders"] for row in rows)
    assert any(row["blocked_for_capacity_001"] for row in rows)
    assert all(
        row["blocked_for_capacity_001"]
        for row in rows
        if row["ibkr_required"] or row["can_generate_signals"] or row["can_generate_preview_or_orders"]
    )


def test_write_capacity_docs_outputs_valid_json(tmp_path: Path) -> None:
    payload = run_capacity_microbench(_config(tmp_path))
    paths = write_capacity_docs(tmp_path, payload)

    decision = json.loads(Path(paths["decision_json"]).read_text(encoding="utf-8"))
    queue = json.loads(Path(paths["queue_json"]).read_text(encoding="utf-8"))
    inventory = json.loads(Path(paths["inventory_json"]).read_text(encoding="utf-8"))
    assert decision["task_id"] == "T-RESEARCH-CAPACITY-001"
    assert queue
    assert inventory
    assert Path(paths["inventory_md"]).exists()
    assert Path(paths["inventory_csv"]).exists()


def test_capacity_002_plan_writes_expected_reports(tmp_path: Path) -> None:
    runtime = tmp_path / "artifacts" / "runtime"
    cache = runtime / "ohlcv_cache"
    cache.mkdir(parents=True)
    _cache_file(cache / "AAA_30m_60d.csv")
    _cache_file(cache / "AAA_15m_60d.csv")
    _cache_file(cache / "AAA_1h_60d.csv")
    (runtime / "universe_intraday_stock_only_v3.metadata.json").write_text(
        json.dumps(
            {
                "selected_count": 1,
                "selected_symbols": ["AAA"],
                "total_candidates": 1,
                "rejected_count": 0,
                "product_policy": "stock_only",
            }
        ),
        encoding="utf-8",
    )
    (runtime / "universe_intraday_stock_only_v3.csv").write_text(
        "symbol,selected,product_class,product_flags,product_rejection_reason\nAAA,True,common_stock,,\n",
        encoding="utf-8",
    )
    evidence = runtime / "research_evidence"
    evidence.mkdir()
    (evidence / "_summary.json").write_text(
        json.dumps(
            {
                "candidate_manifests": [
                    {
                        "status": "rejected",
                        "timeframe": "30m",
                        "window_size": 100,
                        "rejection_reasons": ["drawdown excesivo", "edge no sobrevive coste x2"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    payload = run_capacity_plan(_config(tmp_path, runtime_root=runtime))

    assert payload["task_id"] == "T-RESEARCH-CAPACITY-002"
    assert payload["rc_002_c"]["decision"] == "REJECTED_MINING_READY"
    assert Path(payload["versioned_docs"]["decision_json"]).exists()


def test_capacity_002_plan_blocks_unsafe_flags(tmp_path: Path) -> None:
    with pytest.raises(ResearchCapacitySafetyError, match="IBKR"):
        run_capacity_plan(_config(tmp_path, no_ibkr=False))


def test_capacity_002_plan_handles_empty_cache_and_rejected_rows(tmp_path: Path) -> None:
    payload = run_capacity_plan(_config(tmp_path))

    assert payload["decision"] == "RESEARCH_CAPACITY_BLOCKED_BY_DATA"
    assert Path(payload["versioned_docs"]["c_csv"]).exists()


def _config(
    tmp_path: Path,
    *,
    runtime_root: Path | None = None,
    max_workload: int = 250,
    cache_only: bool = True,
    dry_run: bool = True,
    no_downloads: bool = True,
    no_ibkr: bool = True,
    no_orders: bool = True,
    no_signals: bool = True,
    no_preview: bool = True,
    no_candidate_approval: bool = True,
) -> CapacityRunConfig:
    return CapacityRunConfig(
        repo_root=tmp_path,
        runtime_root=runtime_root or tmp_path / "artifacts" / "runtime",
        output_dir=tmp_path / "artifacts" / "runtime" / "research_capacity",
        research_dir=tmp_path / "research" / "capacity",
        max_workload=max_workload,
        cache_only=cache_only,
        dry_run=dry_run,
        no_downloads=no_downloads,
        no_ibkr=no_ibkr,
        no_orders=no_orders,
        no_signals=no_signals,
        no_preview=no_preview,
        no_candidate_approval=no_candidate_approval,
    )


def _cache_file(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "open", "high", "low", "close", "volume"])
        writer.writerow(["2026-07-01 10:00:00", "1", "2", "1", "2", "100"])
