from __future__ import annotations

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.session import Base
from tradeo.services.reports import ReportService
from tradeo.services.runtime_status import write_entry_scan_status, write_worker_heartbeat
from tradeo.services.system_controls import activate_runtime_kill_switch


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def test_review_pack_includes_runtime_and_runtime_kill_switch(tmp_path) -> None:
    settings = Settings(
        reports_dir=str(tmp_path / "reports"),
        artifacts_dir=str(tmp_path / "artifacts"),
    )
    db = session_factory()
    write_worker_heartbeat(settings)
    write_entry_scan_status("laboratory", {"symbols_checked": 4}, settings)
    activate_runtime_kill_switch(
        db,
        reason="test divergence",
        actor="pytest",
        details={"source": "unit_test"},
    )

    pack = ReportService(settings).generate_review_pack(db)

    assert pack["kill_switch_enabled"] is False
    assert pack["runtime_kill_switch_enabled"] is True
    assert pack["runtime_kill_switch"]["reason"] == "test divergence"
    assert pack["runtime_status"]["worker"]["ok"] is True
    assert pack["runtime_status"]["entry_scans"]["laboratory"]["symbols_checked"] == 4
    assert pack["report_metadata"]["schema_version"] == 1
    assert pack["report_metadata"]["row_limits"]["signals"] == 50
    assert pack["paths"]["json"].endswith(".json")
    assert pack["paths"]["markdown"].endswith(".md")


def test_latest_report_skips_invalid_json_with_read_metadata(tmp_path) -> None:
    settings = Settings(reports_dir=str(tmp_path / "reports"))
    reports_path = settings.reports_path
    valid = reports_path / "tradeo_review_20260615_010000.json"
    invalid = reports_path / "tradeo_review_20260615_020000.json"
    valid.write_text(json.dumps({"generated_at_utc": "older"}), encoding="utf-8")
    invalid.write_text("{", encoding="utf-8")

    report = ReportService(settings).latest_report()

    assert report is not None
    assert report["generated_at_utc"] == "older"
    assert report["_latest_report_read"]["path"] == str(valid)
    assert report["_latest_report_read"]["skipped_invalid_count"] == 1
    assert report["_latest_report_read"]["skipped_invalid_reports"][0]["path"] == str(invalid)
