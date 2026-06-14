from __future__ import annotations

import json
from copy import deepcopy

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import DiscoveredPattern
from tradeo.db.session import Base
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.research.rediscovery_readiness import (
    CLUSTER_SIGNATURE,
    EMBEDDING_CONTRACT,
    READINESS_KEY,
    REGIME_CALIBRATION,
    audit_patterns,
    run_readiness,
)


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def modern_metrics() -> dict:
    return {
        "feature_parity_contract": {
            "contract_id": PatternEmbeddingEngine.CONTRACT_ID,
            "vector_length": 64,
        },
        "cluster_signature": {
            "medoid": {"symbol": "AAPL", "timeframe": "1d"},
            "concentration_checks": {"passed": True, "max_symbol_share": 0.2},
        },
        "regime_profile": {
            "dominant_regime": "benchmark_bull|low_vol_tercile",
            "benchmark_regime_outcomes": {"available": True, "buckets": {}},
        },
    }


def add_pattern(db, key: str, metrics: dict) -> DiscoveredPattern:
    pattern = DiscoveredPattern(pattern_key=key, name=key.upper(), metrics_json=metrics)
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


def test_legacy_pattern_without_fields_is_flagged():
    db = session_factory()
    add_pattern(db, "legacy_cup", {"expectancy_r": 0.4, "win_rate": 0.55})

    results, truncated = audit_patterns(db)

    assert not truncated
    assert len(results) == 1
    result = results[0]
    assert result.needs_rediscovery
    assert result.missing == [EMBEDDING_CONTRACT, CLUSTER_SIGNATURE, REGIME_CALIBRATION]
    assert result.stale == []


def test_modern_pattern_with_all_fields_is_ok():
    db = session_factory()
    add_pattern(db, "modern_flag", modern_metrics())

    results, _ = audit_patterns(db)

    assert len(results) == 1
    assert not results[0].needs_rediscovery
    assert results[0].missing == []
    assert results[0].stale == []


def test_outdated_embedding_contract_is_flagged_as_stale():
    db = session_factory()
    metrics = modern_metrics()
    metrics["feature_parity_contract"]["contract_id"] = "tradeo.pattern_embedding.v1"
    add_pattern(db, "stale_contract", metrics)

    results, _ = audit_patterns(db)

    assert results[0].needs_rediscovery
    assert results[0].stale == [EMBEDDING_CONTRACT]
    assert results[0].missing == []


def test_dry_run_manifest_is_honest_and_mutates_nothing():
    db = session_factory()
    legacy = add_pattern(db, "legacy_cup", {"expectancy_r": 0.4})
    add_pattern(db, "modern_flag", modern_metrics())

    manifest = run_readiness(db, apply_flags=False)

    counts = manifest["counts"]
    assert manifest["dry_run"] is True
    assert counts["patterns_audited"] == 2
    assert counts["needs_rediscovery"] == 1
    assert counts["flagged_this_run"] == 0
    # Honest accounting: a dry-run (and even flagging) populates nothing.
    assert counts["metadata_complete_after"] == counts["metadata_complete_before"] == 1
    assert counts["missing_by_field"][EMBEDDING_CONTRACT] == 1
    db.refresh(legacy)
    assert READINESS_KEY not in (legacy.metrics_json or {})
    assert manifest["determinism"]["content_hash"]


def test_apply_flags_marks_legacy_but_does_not_fake_metadata():
    db = session_factory()
    legacy = add_pattern(db, "legacy_cup", {"expectancy_r": 0.4})

    manifest = run_readiness(db, apply_flags=True)

    assert manifest["counts"]["flagged_this_run"] == 1
    db.refresh(legacy)
    block = legacy.metrics_json[READINESS_KEY]
    assert block["needs_rediscovery"] is True
    assert block["missing"] == [EMBEDDING_CONTRACT, CLUSTER_SIGNATURE, REGIME_CALIBRATION]
    # Flagging must not make the pattern look populated on re-audit.
    results, _ = audit_patterns(db)
    assert results[0].needs_rediscovery
    assert manifest["counts"]["metadata_complete_after"] == 0


def test_readiness_manifest_is_bit_for_bit_with_fixed_clock():
    db = session_factory()
    add_pattern(db, "legacy_cup", {"expectancy_r": 0.4})
    add_pattern(db, "modern_flag", modern_metrics())

    first = run_readiness(db, apply_flags=False, generated_at="2026-06-14T00:00:00+00:00")
    second = run_readiness(db, apply_flags=False, generated_at="2026-06-14T00:00:00+00:00")

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["determinism"]["content_hash"] == second["determinism"]["content_hash"]


def test_apply_flags_is_idempotent_for_unchanged_laggards():
    db = session_factory()
    legacy = add_pattern(db, "legacy_cup", {"expectancy_r": 0.4})

    first = run_readiness(db, apply_flags=True, generated_at="2026-06-14T00:00:00+00:00")
    db.refresh(legacy)
    first_metrics = deepcopy(legacy.metrics_json)
    second = run_readiness(db, apply_flags=True, generated_at="2026-06-15T00:00:00+00:00")
    db.refresh(legacy)

    assert first["counts"]["flagged_this_run"] == 1
    assert second["counts"]["flagged_this_run"] == 0
    assert legacy.metrics_json == first_metrics
    assert legacy.metrics_json[READINESS_KEY]["flagged_at"] == "2026-06-14T00:00:00+00:00"


def test_flag_cleared_after_real_metadata_arrives():
    db = session_factory()
    legacy = add_pattern(db, "legacy_cup", {"expectancy_r": 0.4})
    run_readiness(db, apply_flags=True, generated_at="2026-06-14T00:00:00+00:00")

    # Simulate a real rediscovery upsert refreshing metrics_json.
    db.refresh(legacy)
    refreshed = {**legacy.metrics_json, **modern_metrics()}
    legacy.metrics_json = refreshed
    db.commit()

    manifest = run_readiness(db, apply_flags=True, generated_at="2026-06-15T00:00:00+00:00")

    assert manifest["counts"]["needs_rediscovery"] == 0
    assert manifest["counts"]["flagged_this_run"] == 0
    db.refresh(legacy)
    assert legacy.metrics_json[READINESS_KEY]["needs_rediscovery"] is False
    assert legacy.metrics_json[READINESS_KEY]["flagged_at"] == "2026-06-14T00:00:00+00:00"
    assert legacy.metrics_json[READINESS_KEY]["cleared_at"] == "2026-06-15T00:00:00+00:00"


def test_manifest_written_to_disk_and_truncation_reported(tmp_path):
    db = session_factory()
    for idx in range(3):
        add_pattern(db, f"legacy_{idx}", {})
    out = tmp_path / "manifest.json"

    manifest = run_readiness(db, apply_flags=False, limit=2, manifest_path=out)

    assert manifest["truncated"] is True
    assert manifest["counts"]["patterns_audited"] == 2
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk["counts"] == manifest["counts"]
