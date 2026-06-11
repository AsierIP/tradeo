"""Deterministic serialization and content hashing for research artifacts.

The discovery pipeline must be bit-for-bit reproducible for identical inputs,
config and seeds. Wall-clock timestamps, database run ids and filesystem paths
are legitimate run metadata but must never leak into the identity of a result.
This module provides one canonical JSON form and a content hash that excludes
those volatile keys, so two runs over the same inputs can be compared by hash
regardless of when or where they executed.
"""

from __future__ import annotations

import json
import math
from hashlib import sha256
from typing import Any

import numpy as np

from tradeo.research.types import ClusterCandidate

CONTENT_HASH_ALGO = "sha256_canonical_json_v1"

# Run metadata that varies across re-runs of identical inputs. Excluded from
# content hashes only — the artifact itself keeps these fields.
DEFAULT_VOLATILE_KEYS = frozenset(
    {
        "built_at",
        "generated_at",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
        "exported_at",
        "timestamp",
        "run_id",
        "duration_seconds",
        "elapsed_seconds",
        "event_ledger_path",
        "research_paper_report_path",
        "report_path",
        "report_json_path",
        "report_md_path",
        "backup_path",
        "path",
    }
)


def canonical_payload(value: Any, *, exclude_keys: frozenset[str] = DEFAULT_VOLATILE_KEYS) -> Any:
    """Reduce a payload to plain, deterministic JSON-safe types.

    Dict keys are stringified and sorted, volatile keys dropped, sets sorted,
    numpy scalars/arrays unwrapped, and non-finite floats mapped to None so the
    output never depends on insertion order, hash seeds or NaN encodings.
    """
    if isinstance(value, dict):
        return {
            str(key): canonical_payload(item, exclude_keys=exclude_keys)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in exclude_keys
        }
    if isinstance(value, (list, tuple)):
        return [canonical_payload(item, exclude_keys=exclude_keys) for item in value]
    if isinstance(value, (set, frozenset)):
        return [canonical_payload(item, exclude_keys=exclude_keys) for item in sorted(value, key=str)]
    if isinstance(value, np.ndarray):
        return [canonical_payload(item, exclude_keys=exclude_keys) for item in value.tolist()]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def canonical_json(value: Any, *, exclude_keys: frozenset[str] = DEFAULT_VOLATILE_KEYS) -> str:
    return json.dumps(
        canonical_payload(value, exclude_keys=exclude_keys),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def content_hash(value: Any, *, exclude_keys: frozenset[str] = DEFAULT_VOLATILE_KEYS) -> str:
    return sha256(canonical_json(value, exclude_keys=exclude_keys).encode("utf-8")).hexdigest()


def candidate_content_payload(candidate: ClusterCandidate) -> dict[str, Any]:
    """Stable identity payload for one discovery candidate."""
    return {
        "pattern_key": candidate.pattern_key,
        "name": candidate.name,
        "side": candidate.side,
        "timeframe": candidate.timeframe,
        "window_size": candidate.window_size,
        "cluster_id": candidate.cluster_id,
        "centroid": candidate.centroid,
        "sample_count": candidate.sample_count,
        "symbol_count": candidate.symbol_count,
        "year_count": candidate.year_count,
        "score": candidate.score,
        "validation_passed": candidate.validation_passed,
        "validation_reasons": candidate.validation_reasons,
        "metrics": candidate.metrics,
        "feature_summary": candidate.feature_summary,
        "examples": candidate.examples,
    }


def discovery_content_hash(candidates: list[ClusterCandidate]) -> str:
    """Content hash of a full discovery result, in result order."""
    return content_hash([candidate_content_payload(candidate) for candidate in candidates])
