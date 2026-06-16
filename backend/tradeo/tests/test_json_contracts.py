"""JSON blob contract registry tests (informe §6.1, D-T1)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from tradeo.db import models  # noqa: F401  (register all models on Base.metadata)
from tradeo.db.json_contracts import (
    JSON_CONTRACTS,
    AgentMessagePayloadV1,
    stamp_schema_version,
    validate_payload,
)
from tradeo.db.session import Base


def _persisted_json_columns() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for table in Base.metadata.tables.values():
        for column in table.columns:
            base_type = column.type
            if isinstance(base_type, (JSON, JSONB)) or "JSON" in type(base_type).__name__.upper():
                found.add((table.name, column.name))
    return found


def test_json_contracts_have_version_and_validator() -> None:
    """Every persisted JSON column must declare a versioned, validated contract."""
    persisted = _persisted_json_columns()
    assert persisted, "expected JSON columns on the model metadata"

    registered = set(JSON_CONTRACTS.keys())
    unregistered = persisted - registered
    assert not unregistered, (
        "JSON columns without a registered contract (add them to "
        f"tradeo.db.json_contracts.JSON_CONTRACTS): {sorted(unregistered)}"
    )
    stale = registered - persisted
    assert not stale, f"contracts registered for non-existent columns: {sorted(stale)}"

    for contract in JSON_CONTRACTS.values():
        assert isinstance(contract.schema_version, int) and contract.schema_version >= 1, (
            f"{contract.table}.{contract.column} schema_version must be a positive int"
        )
        assert isinstance(contract.validator, type) and issubclass(contract.validator, BaseModel), (
            f"{contract.table}.{contract.column} validator must be a Pydantic model"
        )


def test_agent_message_payload_contract_is_strict() -> None:
    payload = AgentMessagePayloadV1(kind="parity_check", data={"divergences": 0})
    assert payload.schema_version == 1
    with pytest.raises(ValidationError):
        AgentMessagePayloadV1(kind="x", data={}, unexpected_field=True)
    with pytest.raises(ValidationError):
        validate_payload("agent_messages", "payload_json", {"data": {}})  # kind missing


def test_agent_message_payload_rejects_unknown_schema_version() -> None:
    with pytest.raises(ValidationError, match="schema_version 999"):
        validate_payload(
            "agent_messages",
            "payload_json",
            {"kind": "future_payload", "data": {}, "schema_version": 999},
        )


def test_stamp_schema_version_round_trip() -> None:
    stamped = stamp_schema_version({"foo": 1}, "signals", "metadata_json")
    assert stamped["schema_version"] == JSON_CONTRACTS[("signals", "metadata_json")].schema_version
    assert stamped["foo"] == 1


def test_unregistered_contract_lookup_fails_closed() -> None:
    with pytest.raises(KeyError):
        validate_payload("signals", "not_a_column", {})
