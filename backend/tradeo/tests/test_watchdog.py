from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import DiscoveryRun
from tradeo.db.session import Base
from tradeo.services.watchdog import SystemWatchdog


def test_watchdog_closes_stale_running_discovery_run() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, future=True)()
    stale = DiscoveryRun(
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        status="running",
    )
    fresh = DiscoveryRun(
        started_at=datetime.now(timezone.utc),
        status="running",
    )
    session.add_all([stale, fresh])
    session.commit()

    result = SystemWatchdog().repair(session)

    session.refresh(stale)
    session.refresh(fresh)
    assert stale.status == "failed"
    assert stale.finished_at is not None
    assert fresh.status == "running"
    assert result["repaired"] == [{"type": "discovery_run", "id": stale.id, "action": "marked_failed"}]
