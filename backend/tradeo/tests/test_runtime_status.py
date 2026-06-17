from __future__ import annotations

from pathlib import Path

from tradeo.core.config import Settings
from tradeo.services import runtime_status
from tradeo.services.runtime_status import entry_scan_status, write_entry_scan_status


def test_entry_scan_status_accumulates_symbols(tmp_path) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))

    write_entry_scan_status("laboratory", {"symbols_checked": 40}, settings)
    write_entry_scan_status("laboratory", {"symbols_checked": 40}, settings)

    status = entry_scan_status("laboratory", settings)

    assert status["symbols_checked"] == 80
    assert status["last_symbols_checked"] == 40


def test_entry_scan_status_records_throughput_and_funnel(tmp_path) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))

    write_entry_scan_status(
        "laboratory",
        {
            "symbols_checked": 20,
            "patterns_checked": 80,
            "entry_variants_considered": 12,
            "matches_found": 6,
            "signals_created": 3,
            "orders_submitted": 1,
            "rejected_by_entry_gate": 2,
            "rejected_by_ambiguity": 1,
            "shadow_no_order_observations_opened": 2,
            "scan_duration_ms": 30000,
        },
        settings,
    )

    status = entry_scan_status("laboratory", settings)

    assert status["scan_duration_ms"] == 30000
    assert status["scan_rates_per_minute"]["patterns_per_min"] == 160
    assert status["scan_rates_per_minute"]["signals_per_min"] == 6
    assert status["funnel"]["entry_variants_considered"] == 12
    assert status["funnel"]["rejected_by_ambiguity"] == 1
    assert status["shadow_no_order_observations_opened"] == 2


def test_entry_scan_status_keeps_market_closed_reason(tmp_path) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))

    write_entry_scan_status(
        "laboratory",
        {
            "symbols_checked": 0,
            "skipped_reason": "market_closed",
            "market_session": {"state": "market_closed", "regular_session_open": False},
        },
        settings,
    )

    status = entry_scan_status("laboratory", settings)

    assert status["symbols_checked"] == 0
    assert status["skipped_reason"] == "market_closed"
    assert status["market_session"]["state"] == "market_closed"


def test_entry_scan_status_alerts_after_repeated_zero_order_scans(tmp_path) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))
    result = {
        "symbols_checked": 40,
        "patterns_checked": 25,
        "matches_found": 8,
        "signals_created": 0,
        "orders_submitted": 0,
        "skipped_duplicates": 8,
        "rejected_by_entry_gate": 0,
        "rejected_by_risk": 0,
        "rejected_by_entry_quality": 0,
        "order_errors": [],
    }

    write_entry_scan_status("laboratory", result, settings)
    write_entry_scan_status("laboratory", result, settings)
    write_entry_scan_status("laboratory", result, settings)

    status = entry_scan_status("laboratory", settings)

    assert status["zero_order_scan_streak"] == 3
    assert status["zero_order_alert"] is True
    assert status["zero_order_block_reason"] == "duplicates"
    assert status["skipped_duplicates"] == 8


def test_entry_scan_status_prefers_explicit_order_skip_reason(tmp_path) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))
    result = {
        "symbols_checked": 40,
        "matches_found": 8,
        "orders_submitted": 0,
        "skipped_duplicates": 8,
        "order_skip_reason_counts": {"runtime_kill_switch_enabled": 8},
        "order_errors": [],
    }

    write_entry_scan_status("laboratory", result, settings)

    status = entry_scan_status("laboratory", settings)

    assert status["order_skip_reason_counts"] == {"runtime_kill_switch_enabled": 8}
    assert status["zero_order_block_reason"] == "runtime_kill_switch_enabled"


def test_entry_scan_status_resets_zero_order_streak_when_order_submits(tmp_path) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))

    write_entry_scan_status(
        "laboratory",
        {"symbols_checked": 40, "matches_found": 8, "orders_submitted": 0},
        settings,
    )
    write_entry_scan_status(
        "laboratory",
        {"symbols_checked": 40, "matches_found": 8, "orders_submitted": 1},
        settings,
    )

    status = entry_scan_status("laboratory", settings)

    assert status["zero_order_scan_streak"] == 0
    assert status["zero_order_alert"] is False
    assert status["zero_order_block_reason"] is None


def test_entry_scan_status_does_not_alert_when_execution_is_disabled(tmp_path) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))
    result = {
        "symbols_checked": 40,
        "matches_found": 8,
        "execute_orders": False,
        "orders_submitted": 0,
    }

    write_entry_scan_status("laboratory", result, settings)
    write_entry_scan_status("laboratory", result, settings)
    write_entry_scan_status("laboratory", result, settings)

    status = entry_scan_status("laboratory", settings)

    assert status["execute_orders"] is False
    assert status["zero_order_scan_streak"] == 0
    assert status["zero_order_alert"] is False


def test_entry_scan_status_writes_with_atomic_replace(tmp_path, monkeypatch) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))
    original_replace = runtime_status.os.replace
    calls: list[tuple[str, str]] = []

    def tracked_replace(src, dst) -> None:
        calls.append((Path(src).name, Path(dst).name))
        original_replace(src, dst)

    monkeypatch.setattr(runtime_status.os, "replace", tracked_replace)

    write_entry_scan_status("laboratory", {"symbols_checked": 7}, settings)

    assert calls
    assert calls[-1][1] == runtime_status.ENTRY_SCAN_STATUS
    assert calls[-1][0].startswith(f".{runtime_status.ENTRY_SCAN_STATUS}.")
    assert entry_scan_status("laboratory", settings)["symbols_checked"] == 7
    assert (tmp_path / runtime_status.ENTRY_SCAN_STATUS).stat().st_mode & 0o777 == 0o644


def test_writable_runtime_paths_fallback_when_data_volume_is_read_only(
    tmp_path, monkeypatch
) -> None:
    original_mkdir = Path.mkdir
    blocked = tmp_path / "readonly" / "ohlcv_cache"

    def fake_mkdir(self, *args, **kwargs):
        if self == blocked:
            raise OSError("read-only file system")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    settings = Settings(
        market_data_cache_dir=str(blocked),
        artifacts_dir=str(tmp_path / "artifacts"),
    )

    assert settings.market_data_cache_path == tmp_path / "artifacts" / "runtime" / "ohlcv_cache"
    assert settings.market_data_cache_path.exists()
