"""Publish/consume API for the bridge-agent message bus (informe §5).

Contract shared by every bridge agent:

- **Fail-closed**: an invalid payload raises — nothing half-validated is ever
  persisted. Callers must let the error propagate (block/alert), not assume.
- **Idempotent**: ``idempotency_key`` is unique. Re-publishing the same key
  returns the existing row untouched, so retried agents cannot duplicate
  evidence. A same-key publish with *different* content raises — silently
  swallowing a content mismatch would hide a producer bug.
- **Evidence only**: agents publish evidence and blocks. Promotion state is
  never written through this bus.

Consumers poll with :func:`pending_agent_messages` and acknowledge with
:func:`mark_consumed`; ``consumed_by`` is append-only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tradeo.db.json_contracts import AgentMessagePayloadV1, validate_payload
from tradeo.db.models import AgentMessage, AgentMessageSeverity


class AgentMessageContractError(RuntimeError):
    """Raised when a publish violates the fail-closed message contract."""


def build_idempotency_key(agent: str, kind: str, *parts: Any) -> str:
    """Stable key from the producing agent, message kind and identity parts."""
    raw = "|".join([str(agent), str(kind), *[str(p) for p in parts]])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


def publish_agent_message(
    db: Session,
    *,
    agent: str,
    payload: dict[str, Any] | AgentMessagePayloadV1,
    severity: AgentMessageSeverity | str = AgentMessageSeverity.INFO,
    input_refs: list[str] | None = None,
    idempotency_key: str | None = None,
) -> AgentMessage:
    """Validate and persist one agent message; idempotent on the key."""
    if not str(agent or "").strip():
        raise AgentMessageContractError("agent is required")
    if isinstance(payload, AgentMessagePayloadV1):
        validated = payload
    else:
        validated = validate_payload("agent_messages", "payload_json", payload)
    severity = AgentMessageSeverity(severity)
    refs = [str(r) for r in (input_refs or [])]
    validate_payload("agent_messages", "input_refs", refs)
    payload_dict = validated.model_dump(mode="json")
    key = idempotency_key or build_idempotency_key(
        agent, validated.kind, json.dumps(payload_dict, sort_keys=True)
    )

    existing = db.execute(
        select(AgentMessage).where(AgentMessage.idempotency_key == key)
    ).scalar_one_or_none()
    if existing is not None:
        return _verify_existing(existing, agent=agent, payload_dict=payload_dict, key=key)

    message = AgentMessage(
        agent=agent,
        schema_version=validated.schema_version,
        input_refs=refs,
        payload_json=payload_dict,
        severity=severity,
        consumed_by=[],
        idempotency_key=key,
    )
    db.add(message)
    try:
        db.commit()
    except IntegrityError:
        # Concurrent publisher won the unique-key race: return its row.
        db.rollback()
        existing = db.execute(
            select(AgentMessage).where(AgentMessage.idempotency_key == key)
        ).scalar_one()
        return _verify_existing(existing, agent=agent, payload_dict=payload_dict, key=key)
    db.refresh(message)
    return message


def _verify_existing(
    existing: AgentMessage, *, agent: str, payload_dict: dict[str, Any], key: str
) -> AgentMessage:
    if existing.agent != agent or existing.payload_json != payload_dict:
        raise AgentMessageContractError(
            f"idempotency_key collision with different content: {key} "
            f"(existing agent={existing.agent!r}, new agent={agent!r})"
        )
    return existing


def pending_agent_messages(
    db: Session,
    *,
    consumer: str,
    agent: str | None = None,
    severity: AgentMessageSeverity | str | None = None,
    limit: int = 100,
) -> list[AgentMessage]:
    """Messages this consumer has not acknowledged yet, oldest first."""
    stmt = select(AgentMessage).order_by(AgentMessage.produced_at_utc.asc(), AgentMessage.id.asc())
    if agent:
        stmt = stmt.where(AgentMessage.agent == agent)
    if severity is not None:
        stmt = stmt.where(AgentMessage.severity == AgentMessageSeverity(severity))
    rows = db.execute(stmt.limit(max(1, int(limit)) * 4)).scalars().all()
    return [row for row in rows if consumer not in (row.consumed_by or [])][: max(1, int(limit))]


def mark_consumed(db: Session, message: AgentMessage, *, consumer: str) -> AgentMessage:
    """Append-only acknowledgement; idempotent per consumer."""
    if not str(consumer or "").strip():
        raise AgentMessageContractError("consumer is required")
    consumed = list(message.consumed_by or [])
    if consumer not in consumed:
        message.consumed_by = [*consumed, consumer]
        db.add(message)
        db.commit()
        db.refresh(message)
    return message
