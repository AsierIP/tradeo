from __future__ import annotations

from pathlib import Path

from tradeo.core.config import Settings
from tradeo.services.runtime_status import entry_scan_status, write_entry_scan_status


def test_entry_scan_status_accumulates_symbols(tmp_path) -> None:
    settings = Settings(artifacts_dir=str(tmp_path))

    write_entry_scan_status("laboratory", {"symbols_checked": 40}, settings)
    write_entry_scan_status("laboratory", {"symbols_checked": 40}, settings)

    status = entry_scan_status("laboratory", settings)

    assert status["symbols_checked"] == 80
    assert status["last_symbols_checked"] == 40


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


def test_writable_runtime_paths_fallback_when_data_volume_is_read_only(tmp_path, monkeypatch) -> None:
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
