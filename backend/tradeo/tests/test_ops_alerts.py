from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import AuditLog
from tradeo.db.session import Base
from tradeo.services.ops_alerts import record_job_failure


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def test_record_job_failure_persists_internal_alert() -> None:
    db = session_factory()

    recorded = record_job_failure(db, job_id="market_scan", exc=RuntimeError("boom"))

    assert recorded is True
    alert = db.query(AuditLog).filter(AuditLog.action == "internal_ops_alert").one()
    assert alert.actor == "ops_alerting"
    assert alert.entity_type == "scheduler_job"
    assert alert.entity_id == "market_scan"
    assert alert.details_json["severity"] == "critical"
    assert alert.details_json["job_id"] == "market_scan"
    assert alert.details_json["exception_type"] == "RuntimeError"
