"""Versioned contracts for every persisted JSON blob (informe §6.1, D-T1).

The JSON columns in ``tradeo.db.models`` act as de-facto schemas. Without a
version and a validator they drift silently. This module is the single
registry: every JSON/JSONB column must declare

- ``schema_version``: integer, bumped on every shape change;
- ``validator``: a Pydantic model that validates the blob.

Legacy blobs that grew organically are registered with permissive validators
(``extra="allow"``) and ``strict=False`` — that is honest: the contract states
what is guaranteed today, nothing more. New blobs (e.g. ``agent_messages``)
must register strict validators.

``test_json_contracts_have_version_and_validator`` enforces full coverage, so
adding a JSON column without registering a contract fails CI.

Convention for writers: stamp payloads with :func:`stamp_schema_version`
before persisting, so the version travels inside the blob itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class _FreeformDict(BaseModel):
    """Permissive contract for legacy dict blobs: any keys allowed."""

    model_config = ConfigDict(extra="allow")


class _StringList(BaseModel):
    root: list[str] = Field(default_factory=list)


class _FreeformDictList(BaseModel):
    root: list[dict[str, Any]] = Field(default_factory=list)


class _FloatList(BaseModel):
    root: list[float] = Field(default_factory=list)


class AgentMessagePayloadV1(BaseModel):
    """Strict envelope for ``agent_messages.payload_json`` (informe §5).

    ``kind`` identifies the message type within the producing agent;
    ``data`` carries the typed evidence. Extra top-level keys are rejected so
    the envelope cannot drift silently.
    """

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=120)
    data: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = Field(default=1, ge=1)


@dataclass(frozen=True)
class JsonContract:
    table: str
    column: str
    schema_version: int
    validator: type[BaseModel]
    strict: bool = False

    @property
    def key(self) -> tuple[str, str]:
        return (self.table, self.column)


_CONTRACTS: tuple[JsonContract, ...] = (
    JsonContract("signals", "metadata_json", 1, _FreeformDict),
    JsonContract("trades", "metadata_json", 1, _FreeformDict),
    JsonContract("strategy_versions", "params_json", 1, _FreeformDict),
    JsonContract("strategy_versions", "metrics_json", 1, _FreeformDict),
    JsonContract("audit_logs", "details_json", 1, _FreeformDict),
    JsonContract("system_controls", "details_json", 1, _FreeformDict),
    JsonContract("discovery_runs", "params_json", 1, _FreeformDict),
    JsonContract("discovery_runs", "summary_json", 1, _FreeformDict),
    JsonContract("discovered_patterns", "rr_metrics_json", 1, _FreeformDict),
    JsonContract("discovered_patterns", "rejection_reasons_json", 1, _StringList),
    JsonContract("discovered_patterns", "validation_reasons_json", 1, _StringList),
    JsonContract("discovered_patterns", "centroid_json", 1, _FloatList),
    JsonContract("discovered_patterns", "metrics_json", 1, _FreeformDict),
    JsonContract("discovered_patterns", "feature_summary_json", 1, _FreeformDict),
    JsonContract("discovered_pattern_examples", "chart_json", 1, _FreeformDict),
    JsonContract("discovered_pattern_examples", "features_json", 1, _FreeformDict),
    JsonContract("discovered_pattern_metrics", "metrics_json", 1, _FreeformDict),
    JsonContract("discovered_pattern_matches", "chart_json", 1, _FreeformDict),
    JsonContract("discovered_pattern_matches", "metrics_json", 1, _FreeformDict),
    JsonContract("intraday_universe_snapshots", "symbols_json", 1, _StringList),
    JsonContract("intraday_universe_snapshots", "filters_json", 1, _FreeformDict),
    JsonContract("intraday_universe_snapshots", "excluded_json", 1, _FreeformDictList),
    JsonContract("intraday_universe_snapshots", "pacing_budget_json", 1, _FreeformDict),
    JsonContract("intraday_symbol_state", "metadata_json", 1, _FreeformDict),
    JsonContract("intraday_pacing_ledger", "payload_json", 1, _FreeformDict),
    JsonContract("intraday_risk_ledger", "payload_json", 1, _FreeformDict),
    JsonContract("intraday_flatten_attempts", "broker_response_json", 1, _FreeformDict),
    JsonContract("agent_messages", "input_refs", 1, _StringList, strict=True),
    JsonContract("agent_messages", "payload_json", 1, AgentMessagePayloadV1, strict=True),
    JsonContract("agent_messages", "consumed_by", 1, _StringList, strict=True),
)

JSON_CONTRACTS: dict[tuple[str, str], JsonContract] = {c.key: c for c in _CONTRACTS}


def contract_for(table: str, column: str) -> JsonContract:
    try:
        return JSON_CONTRACTS[(table, column)]
    except KeyError as exc:
        raise KeyError(
            f"No JSON contract registered for {table}.{column}; "
            "register it in tradeo.db.json_contracts.JSON_CONTRACTS"
        ) from exc


def validate_payload(table: str, column: str, payload: Any) -> Any:
    """Validate ``payload`` against its registered contract (fail-closed).

    List-shaped contracts (``root`` field) accept a bare list. Raises
    ``pydantic.ValidationError`` on mismatch — callers must not swallow it.
    """
    contract = contract_for(table, column)
    fields = contract.validator.model_fields
    if "root" in fields and isinstance(payload, list):
        return contract.validator(root=payload)
    validated = contract.validator.model_validate(payload)

    if "schema_version" not in fields:
        return validated

    actual_version = getattr(validated, "schema_version")
    if actual_version != contract.schema_version:
        raise ValidationError.from_exception_data(
            f"{contract.table}.{contract.column}",
            [
                {
                    "type": "value_error",
                    "loc": ("schema_version",),
                    "msg": "Value error, schema_version mismatch",
                    "input": actual_version,
                    "ctx": {
                        "error": ValueError(
                            f"schema_version {actual_version} does not match registered "
                            f"contract version {contract.schema_version}"
                        )
                    },
                }
            ],
        )
    return validated


def stamp_schema_version(payload: dict[str, Any], table: str, column: str) -> dict[str, Any]:
    """Return a copy of ``payload`` carrying its contract's schema_version."""
    contract = contract_for(table, column)
    return {**payload, "schema_version": contract.schema_version}
