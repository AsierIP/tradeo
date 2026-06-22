from __future__ import annotations

import ast
from pathlib import Path

from tradeo.core.config import Settings


def _worker_job_ids() -> set[str]:
    worker_path = Path(__file__).resolve().parents[1] / "tasks" / "worker.py"
    tree = ast.parse(worker_path.read_text(encoding="utf-8"))
    job_ids: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "add_job":
            continue
        for keyword in node.keywords:
            if keyword.arg == "id" and isinstance(keyword.value, ast.Constant):
                job_ids.add(str(keyword.value.value))
    return job_ids


def test_intraday_disabled_is_noop_for_runtime_defaults() -> None:
    settings = Settings()

    assert settings.intraday_enabled is False
    assert settings.intraday_shadow_enabled is False
    assert settings.intraday_paper_enabled is False
    assert settings.intraday_live_enabled is False
    assert settings.intraday_live_armed is False


def test_worker_has_no_intraday_jobs_registered_by_default() -> None:
    job_ids = _worker_job_ids()

    assert job_ids
    assert not [job_id for job_id in job_ids if job_id.startswith("intraday_")]


def test_daily_contract_snapshot_omits_intraday_when_disabled() -> None:
    settings = Settings(ibkr_readonly=True)
    snapshot = {
        "trading_mode": settings.trading_mode,
        "scan_interval": settings.scan_interval,
        "discovery_interval": settings.discovery_interval,
        "live_trading_enabled": settings.live_trading_enabled,
        "ibkr_readonly": settings.ibkr_readonly,
        "intraday_enabled": settings.intraday_enabled,
    }

    assert snapshot == {
        "trading_mode": "paper",
        "scan_interval": "1d",
        "discovery_interval": "1d",
        "live_trading_enabled": False,
        "ibkr_readonly": True,
        "intraday_enabled": False,
    }
