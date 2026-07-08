from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import IntradayWorkItem
from tradeo.db.session import Base
from tradeo.modules.intraday.work_ids import IntradayWorkDescriptor, params_hash
from tradeo.modules.intraday.work_queue import (
    IntradayDistributedWorkQueue,
    WORK_STATUS_COMPLETED,
    WORK_STATUS_LEASED,
    WORK_STATUS_PENDING,
)


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _descriptor(**overrides) -> IntradayWorkDescriptor:
    values = {
        "scope": "research",
        "lane": "intraday_research",
        "symbol": "SOUN",
        "session_id": "2026-06-22",
        "timeframe": "5m",
        "window_start": "2026-06-22T13:30:00Z",
        "window_end": "2026-06-22T14:00:00Z",
        "window_size": 6,
        "forward_bars": 3,
        "miner_id": "cluster_v1",
        "params_hash": params_hash({"window": 6, "rr": 4.0}),
        "data_manifest_hash": "data-hash",
        "split_id": "purged-fold-0",
    }
    values.update(overrides)
    return IntradayWorkDescriptor(**values)


def test_intraday_work_fingerprint_is_stable_and_chart_specific() -> None:
    first = _descriptor().fingerprint()
    assert first == _descriptor().fingerprint()
    assert first != _descriptor(window_end="2026-06-22T14:05:00Z").fingerprint()
    assert len(first) == 64


def test_intraday_work_queue_dedupes_and_claims_with_lease() -> None:
    db = _db_session()
    queue = IntradayDistributedWorkQueue()
    descriptor = _descriptor()

    created = queue.enqueue(db, descriptor, priority=10.0)
    duplicate = queue.enqueue(db, descriptor, priority=10.0)
    db.commit()

    assert created.created is True
    assert duplicate.created is False
    assert db.query(IntradayWorkItem).count() == 1

    claimed = queue.claim_batch(
        db,
        scope="research",
        lane="intraday_research",
        worker_id="research-01",
        limit=1,
        lease_seconds=30,
        now=datetime(2026, 6, 22, 14, 1, tzinfo=timezone.utc),
    )
    assert len(claimed) == 1
    assert claimed[0].status == WORK_STATUS_LEASED
    assert claimed[0].lease_owner == "research-01"

    other = queue.claim_batch(
        db,
        scope="research",
        lane="intraday_research",
        worker_id="research-02",
        limit=1,
        now=datetime(2026, 6, 22, 14, 1, tzinfo=timezone.utc),
    )
    assert other == []


def test_intraday_work_queue_reaps_expired_leases_and_completes() -> None:
    db = _db_session()
    queue = IntradayDistributedWorkQueue()
    queue.enqueue(db, _descriptor(), priority=1.0, max_attempts=2)
    item = queue.claim_batch(
        db,
        scope="research",
        worker_id="research-01",
        lease_seconds=1,
        now=datetime(2026, 6, 22, 14, 0, tzinfo=timezone.utc),
    )[0]

    reaped = queue.reap_expired_leases(
        db,
        now=datetime(2026, 6, 22, 14, 0, 2, tzinfo=timezone.utc),
    )
    assert reaped == 1
    assert item.status == WORK_STATUS_PENDING

    item = queue.claim_batch(db, scope="research", worker_id="research-02", limit=1)[0]
    queue.complete(db, item, result={"patterns": 1}, reason_codes=["accepted"])
    assert item.status == WORK_STATUS_COMPLETED
    assert item.result_json == {"patterns": 1}
    assert item.reason_codes_json == ["accepted"]


def test_intraday_lab_work_expires_before_claim() -> None:
    db = _db_session()
    queue = IntradayDistributedWorkQueue()
    queue.enqueue(
        db,
        _descriptor(scope="lab", lane="intraday_lab", pattern_key="p1", entry_variant_id="breakout"),
        expires_at=datetime(2026, 6, 22, 14, 0, tzinfo=timezone.utc),
    )

    claimed = queue.claim_batch(
        db,
        scope="lab",
        lane="intraday_lab",
        worker_id="lab-01",
        now=datetime(2026, 6, 22, 14, 0, 1, tzinfo=timezone.utc),
    )

    assert claimed == []
    assert queue.metrics(db).by_status == {"expired": 1}


def test_intraday_worker_heartbeat_and_metrics() -> None:
    db = _db_session()
    queue = IntradayDistributedWorkQueue()
    queue.enqueue(db, _descriptor(scope="research", lane="intraday_research"))
    queue.enqueue(db, _descriptor(scope="lab", lane="intraday_lab", pattern_key="p1"))
    heartbeat = queue.heartbeat(db, worker_id="lab-01", scope="lab", lane="intraday_lab", capacity=4)
    metrics = queue.metrics(db)

    assert heartbeat.capacity == 4
    assert metrics.total == 2
    assert metrics.by_scope == {"lab": 1, "research": 1}
