"""Bridge-agent message bus tests (informe §5): fail-closed + idempotent."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import AgentMessage, AgentMessageSeverity
from tradeo.db.session import Base
from tradeo.services.agent_messages import (
    AgentMessageContractError,
    build_idempotency_key,
    mark_consumed,
    pending_agent_messages,
    publish_agent_message,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _payload(**data):
    return {"kind": "parity_check", "data": {"divergences": 0, **data}, "schema_version": 1}


def test_agent_messages_idempotent() -> None:
    """Publishing the same idempotency_key twice persists exactly one row."""
    db = _session()
    key = build_idempotency_key("parity_bridge", "parity_check", "2026-06-12")

    first = publish_agent_message(
        db,
        agent="parity_bridge",
        payload=_payload(),
        severity="info",
        input_refs=["sha256:abc"],
        idempotency_key=key,
    )
    second = publish_agent_message(
        db,
        agent="parity_bridge",
        payload=_payload(),
        severity="info",
        input_refs=["sha256:abc"],
        idempotency_key=key,
    )

    assert first.id == second.id
    assert db.query(AgentMessage).count() == 1
    assert second.idempotency_key == key
    assert second.schema_version == 1
    assert second.payload_json["kind"] == "parity_check"


def test_same_key_different_content_fails_closed() -> None:
    db = _session()
    key = build_idempotency_key("parity_bridge", "parity_check", "x")
    publish_agent_message(db, agent="parity_bridge", payload=_payload(), idempotency_key=key)
    with pytest.raises(AgentMessageContractError):
        publish_agent_message(
            db, agent="parity_bridge", payload=_payload(divergences=3), idempotency_key=key
        )
    with pytest.raises(AgentMessageContractError):
        publish_agent_message(db, agent="other_agent", payload=_payload(), idempotency_key=key)


def test_invalid_payload_is_rejected_before_persisting() -> None:
    db = _session()
    with pytest.raises(Exception):  # pydantic.ValidationError
        publish_agent_message(
            db, agent="parity_bridge", payload={"data": {}, "extra": True}  # no kind, extra key
        )
    assert db.query(AgentMessage).count() == 0
    with pytest.raises(AgentMessageContractError):
        publish_agent_message(db, agent="  ", payload=_payload())


def test_pending_and_mark_consumed_are_per_consumer_and_idempotent() -> None:
    db = _session()
    message = publish_agent_message(
        db,
        agent="drift_sentinel",
        payload={"kind": "drift_alert", "data": {"psi": 0.4}},
        severity=AgentMessageSeverity.BLOCKING,
    )

    pending_director = pending_agent_messages(db, consumer="director")
    assert [m.id for m in pending_director] == [message.id]

    mark_consumed(db, message, consumer="director")
    mark_consumed(db, message, consumer="director")  # idempotent ack
    assert message.consumed_by == ["director"]

    assert pending_agent_messages(db, consumer="director") == []
    assert [m.id for m in pending_agent_messages(db, consumer="worker")] == [message.id]


def test_auto_idempotency_key_derives_from_content() -> None:
    db = _session()
    first = publish_agent_message(db, agent="a", payload=_payload())
    second = publish_agent_message(db, agent="a", payload=_payload())
    third = publish_agent_message(db, agent="a", payload=_payload(divergences=1))
    assert first.id == second.id
    assert third.id != first.id
    assert db.query(AgentMessage).count() == 2
