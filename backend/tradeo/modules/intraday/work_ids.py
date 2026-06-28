from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping

WORK_FINGERPRINT_VERSION = "intraday-work-fingerprint-v1"


@dataclass(frozen=True, slots=True)
class IntradayWorkDescriptor:
    """Canonical identity of a Research/Lab unit of work."""

    scope: str
    lane: str
    symbol: str
    session_id: str
    timeframe: str
    window_start: str = ""
    window_end: str = ""
    window_size: int = 0
    forward_bars: int = 0
    pattern_key: str = ""
    entry_variant_id: str = ""
    miner_id: str = ""
    params_hash: str = ""
    data_manifest_hash: str = ""
    split_id: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)

    def fingerprint(self) -> str:
        return stable_work_fingerprint(
            "work",
            self.scope,
            self.lane,
            self.symbol.upper(),
            self.session_id,
            self.timeframe,
            self.window_start,
            self.window_end,
            int(self.window_size or 0),
            int(self.forward_bars or 0),
            self.pattern_key,
            self.entry_variant_id,
            self.miner_id,
            self.params_hash,
            self.data_manifest_hash,
            self.split_id,
        )

    def lab_fingerprint(self) -> str:
        return stable_work_fingerprint(
            "lab",
            self.symbol.upper(),
            self.session_id,
            self.timeframe,
            self.pattern_key,
            self.entry_variant_id,
            self.window_end,
            self.data_manifest_hash,
        )

    def committee_fingerprint(self, *, evidence_snapshot_hash: str = "") -> str:
        return stable_work_fingerprint(
            "committee",
            self.pattern_key,
            self.symbol.upper(),
            self.timeframe,
            self.miner_id,
            self.params_hash,
            self.data_manifest_hash,
            evidence_snapshot_hash,
        )


def stable_work_fingerprint(*parts: Any) -> str:
    payload = "\x1f".join(_normalize(part) for part in (WORK_FINGERPRINT_VERSION, *parts))
    return sha256(payload.encode("utf-8")).hexdigest()


def params_hash(params: Mapping[str, Any]) -> str:
    rows = _flatten_mapping(params)
    return stable_work_fingerprint(*[f"{key}={value}" for key, value in rows])


def _flatten_mapping(value: Mapping[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for key in sorted(value):
        joined = f"{prefix}.{key}" if prefix else str(key)
        item = value[key]
        if isinstance(item, Mapping):
            rows.extend(_flatten_mapping(item, joined))
        elif isinstance(item, (list, tuple)):
            rows.append((joined, ",".join(_normalize(part) for part in item)))
        else:
            rows.append((joined, _normalize(item)))
    return rows


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
