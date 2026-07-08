from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tradeo.db.models import IntradayWorkItem, IntradayWorkerHeartbeat
from tradeo.modules.intraday.work_ids import IntradayWorkDescriptor

WORK_STATUS_PENDING = "pending"
WORK_STATUS_LEASED = "leased"
WORK_STATUS_COMPLETED = "completed"
WORK_STATUS_FAILED = "failed"
WORK_STATUS_EXPIRED = "expired"
WORK_STATUS_SKIPPED = "skipped"
FINAL_WORK_STATUSES = {WORK_STATUS_COMPLETED, WORK_STATUS_FAILED, WORK_STATUS_EXPIRED, WORK_STATUS_SKIPPED}


@dataclass(frozen=True, slots=True)
class IntradayEnqueueResult:
    item: IntradayWorkItem
    created: bool
    reason: str


@dataclass(frozen=True, slots=True)
class IntradayQueueMetrics:
    total: int
    by_status: dict[str, int]
    by_scope: dict[str, int]
    by_lane: dict[str, int]


class IntradayDistributedWorkQueue:
    """Auditable Postgres-first work queue for Research and Lab workers.

    PostgreSQL deployments use row locks with SKIP LOCKED for concurrent claims.
    SQLite/testing falls back to status transitions, which keeps unit tests fast
    and dependency-free while preserving the same public contract.
    """

    def enqueue(
        self,
        db: Session,
        descriptor: IntradayWorkDescriptor,
        *,
        priority: float = 0.0,
        expires_at: datetime | None = None,
        payload: Mapping[str, Any] | None = None,
        max_attempts: int = 3,
    ) -> IntradayEnqueueResult:
        fingerprint = descriptor.fingerprint()
        existing = db.query(IntradayWorkItem).filter(IntradayWorkItem.work_fingerprint == fingerprint).one_or_none()
        if existing is not None:
            return IntradayEnqueueResult(existing, False, "duplicate_fingerprint")
        item = IntradayWorkItem(
            scope=descriptor.scope,
            lane=descriptor.lane,
            symbol=descriptor.symbol.upper().strip(),
            session_id=descriptor.session_id,
            timeframe=descriptor.timeframe,
            pattern_key=descriptor.pattern_key,
            entry_variant_id=descriptor.entry_variant_id,
            window_start=descriptor.window_start,
            window_end=descriptor.window_end,
            work_fingerprint=fingerprint,
            data_manifest_hash=descriptor.data_manifest_hash,
            params_hash=descriptor.params_hash,
            split_id=descriptor.split_id,
            priority=float(priority),
            status=WORK_STATUS_PENDING,
            expires_at=_as_utc_or_none(expires_at),
            max_attempts=max(1, int(max_attempts)),
            payload_json={**dict(descriptor.payload), **dict(payload or {})},
        )
        db.add(item)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            existing = db.query(IntradayWorkItem).filter(IntradayWorkItem.work_fingerprint == fingerprint).one()
            return IntradayEnqueueResult(existing, False, "duplicate_fingerprint")
        return IntradayEnqueueResult(item, True, "created")

    def claim_batch(
        self,
        db: Session,
        *,
        scope: str,
        worker_id: str,
        lane: str | None = None,
        limit: int = 10,
        lease_seconds: int = 300,
        now: datetime | None = None,
    ) -> list[IntradayWorkItem]:
        current = _as_utc(now)
        self.expire_due_items(db, now=current)
        self.reap_expired_leases(db, now=current)
        query = db.query(IntradayWorkItem).filter(
            IntradayWorkItem.scope == scope,
            IntradayWorkItem.status == WORK_STATUS_PENDING,
            IntradayWorkItem.attempt_count < IntradayWorkItem.max_attempts,
            or_(IntradayWorkItem.expires_at.is_(None), IntradayWorkItem.expires_at > current),
        )
        if lane:
            query = query.filter(IntradayWorkItem.lane == lane)
        if db.bind is not None and db.bind.dialect.name != "sqlite":
            query = query.with_for_update(skip_locked=True)
        rows = (
            query.order_by(
                IntradayWorkItem.priority.desc(),
                IntradayWorkItem.created_at.asc(),
                IntradayWorkItem.id.asc(),
            )
            .limit(max(1, int(limit)))
            .all()
        )
        lease_until = current + timedelta(seconds=max(1, int(lease_seconds)))
        for row in rows:
            row.status = WORK_STATUS_LEASED
            row.lease_owner = worker_id
            row.lease_until = lease_until
            row.started_at = row.started_at or current
            row.updated_at = current
            row.attempt_count += 1
        db.flush()
        return rows

    def complete(
        self,
        db: Session,
        item: IntradayWorkItem,
        *,
        result: Mapping[str, Any] | None = None,
        reason_codes: Iterable[str] = (),
        now: datetime | None = None,
    ) -> IntradayWorkItem:
        current = _as_utc(now)
        item.status = WORK_STATUS_COMPLETED
        item.result_json = dict(result or {})
        item.reason_codes_json = [str(code) for code in reason_codes]
        item.finished_at = current
        item.updated_at = current
        item.lease_until = None
        db.flush()
        return item

    def fail(
        self,
        db: Session,
        item: IntradayWorkItem,
        *,
        reason: str,
        retry: bool = True,
        now: datetime | None = None,
    ) -> IntradayWorkItem:
        current = _as_utc(now)
        if retry and item.attempt_count < item.max_attempts:
            item.status = WORK_STATUS_PENDING
        else:
            item.status = WORK_STATUS_FAILED
            item.finished_at = current
        item.reason_codes_json = [reason]
        item.updated_at = current
        item.lease_until = None
        db.flush()
        return item

    def expire_due_items(self, db: Session, *, now: datetime | None = None) -> int:
        current = _as_utc(now)
        rows = (
            db.query(IntradayWorkItem)
            .filter(
                IntradayWorkItem.status.in_([WORK_STATUS_PENDING, WORK_STATUS_LEASED]),
                IntradayWorkItem.expires_at.is_not(None),
                IntradayWorkItem.expires_at <= current,
            )
            .all()
        )
        for row in rows:
            row.status = WORK_STATUS_EXPIRED
            row.reason_codes_json = ["opportunity_expired"]
            row.finished_at = current
            row.updated_at = current
            row.lease_until = None
        db.flush()
        return len(rows)

    def reap_expired_leases(self, db: Session, *, now: datetime | None = None) -> int:
        current = _as_utc(now)
        rows = (
            db.query(IntradayWorkItem)
            .filter(
                IntradayWorkItem.status == WORK_STATUS_LEASED,
                IntradayWorkItem.lease_until.is_not(None),
                IntradayWorkItem.lease_until <= current,
            )
            .all()
        )
        for row in rows:
            if row.attempt_count >= row.max_attempts:
                row.status = WORK_STATUS_FAILED
                row.reason_codes_json = ["lease_expired_max_attempts"]
                row.finished_at = current
            else:
                row.status = WORK_STATUS_PENDING
                row.reason_codes_json = ["lease_expired_requeued"]
            row.lease_owner = ""
            row.lease_until = None
            row.updated_at = current
        db.flush()
        return len(rows)

    def heartbeat(
        self,
        db: Session,
        *,
        worker_id: str,
        scope: str,
        lane: str,
        capacity: int = 1,
        metadata: Mapping[str, Any] | None = None,
        now: datetime | None = None,
    ) -> IntradayWorkerHeartbeat:
        current = _as_utc(now)
        row = db.query(IntradayWorkerHeartbeat).filter(IntradayWorkerHeartbeat.worker_id == worker_id).one_or_none()
        if row is None:
            row = IntradayWorkerHeartbeat(worker_id=worker_id, first_seen_at=current)
            db.add(row)
        row.scope = scope
        row.lane = lane
        row.capacity = max(1, int(capacity))
        row.last_seen_at = current
        row.status = "online"
        row.metadata_json = dict(metadata or {})
        db.flush()
        return row

    def metrics(self, db: Session) -> IntradayQueueMetrics:
        rows = db.query(IntradayWorkItem).all()
        return IntradayQueueMetrics(
            total=len(rows),
            by_status=dict(sorted(Counter(row.status for row in rows).items())),
            by_scope=dict(sorted(Counter(row.scope for row in rows).items())),
            by_lane=dict(sorted(Counter(row.lane for row in rows).items())),
        )


def _as_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _as_utc_or_none(value: datetime | None) -> datetime | None:
    return _as_utc(value) if value is not None else None
