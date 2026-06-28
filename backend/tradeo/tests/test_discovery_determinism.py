"""Bit-for-bit determinism contract for the discovery/research path.

Runs the real ClusterResearchEngine twice over identical synthetic fixtures
and asserts the full candidate payload (metrics included) is byte-identical
under canonical JSON. Scope is honest: the contract covers the engine core
(clustering, validation statistics, scoring) and the discovery report
artifact identity; it does not cover live market data fetches or DB state.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.determinism import (
    DEFAULT_VOLATILE_KEYS,
    canonical_json,
    candidate_content_payload,
    content_hash,
    discovery_content_hash,
)
from tradeo.research.types import ForwardOutcome, WindowSample


def _sample(index: int, *, vector: np.ndarray, close: float) -> WindowSample:
    entry = 100.0
    risk = 10.0
    end = date(2024, 1, 1) + timedelta(days=index)
    highs = [max(close, entry) + 1.0]
    lows = [min(close, entry) - 1.0]
    return WindowSample(
        symbol=f"DET{index % 7}",
        timeframe="1d",
        window_size=20,
        start=(end - timedelta(days=20)).isoformat(),
        end=end.isoformat(),
        year=end.year,
        vector=vector.astype(np.float32),
        chart={},
        features={},
        outcome=ForwardOutcome(
            forward_returns={5: close / entry - 1.0},
            entry_price=entry,
            risk_proxy=risk,
            forward_end=(end + timedelta(days=1)).isoformat(),
            long_mfe_r=max((max(highs) - entry) / risk, 0.0),
            long_mae_r=max((entry - min(lows)) / risk, 0.0),
            long_outcome_r=(close - entry) / risk,
            long_hit_4r=False,
            short_mfe_r=max((entry - min(lows)) / risk, 0.0),
            short_mae_r=max((max(highs) - entry) / risk, 0.0),
            short_outcome_r=(entry - close) / risk,
            short_hit_4r=False,
            forward_highs=highs,
            forward_lows=lows,
            forward_closes=[close],
        ),
    )


def _make_samples(seed: int = 7, count: int = 48) -> list[WindowSample]:
    rng = np.random.default_rng(seed)
    samples: list[WindowSample] = []
    for i in range(count):
        blob = i % 2
        base = 0.0 if blob == 0 else 5.0
        vector = base + rng.normal(0.0, 0.05, 2)
        drift = 1.0 if blob == 0 else -1.0
        close = 100.0 + float(rng.normal(drift, 0.5))
        samples.append(_sample(i, vector=vector, close=close))
    return samples


def _engine() -> ClusterResearchEngine:
    return ClusterResearchEngine(
        min_cluster_size=5,
        max_clusters_per_window=2,
        out_of_sample_pct=0.2,
        rr_levels=[2.0],
        min_samples=1,
        quant_bootstrap_draws=100,
    )


def test_canonical_payload_is_order_and_type_insensitive() -> None:
    a = {"b": 1, "a": np.float64(2.5), "tags": {"y", "x"}, "vec": np.asarray([1.0, 2.0])}
    b = {"vec": [1.0, 2.0], "tags": ["x", "y"], "a": 2.5, "b": 1}
    assert content_hash(a) == content_hash(b)


def test_content_hash_excludes_volatile_keys() -> None:
    base = {"score": 1.25, "nested": {"win_rate": 0.5}}
    noisy = {
        **base,
        "generated_at": "2026-06-11T00:00:00Z",
        "run_id": 99,
        "nested": {"win_rate": 0.5, "built_at": "2026-06-11", "path": "/tmp/x.json"},
    }
    assert content_hash(base) == content_hash(noisy)
    assert content_hash(base) != content_hash({**base, "score": 1.26})


def test_canonical_json_maps_non_finite_to_null() -> None:
    payload = canonical_json({"a": float("nan"), "b": float("inf")})
    assert json.loads(payload) == {"a": None, "b": None}


def test_discovery_is_bit_for_bit_deterministic_across_runs() -> None:
    first = _engine().discover(_make_samples())
    second = _engine().discover(_make_samples())
    assert first, "fixture must produce candidates for the contract to be meaningful"
    assert len(first) == len(second)
    first_json = canonical_json([candidate_content_payload(c) for c in first])
    second_json = canonical_json([candidate_content_payload(c) for c in second])
    assert first_json == second_json
    assert discovery_content_hash(first) == discovery_content_hash(second)


def test_discovery_is_independent_of_input_sample_order() -> None:
    baseline = _engine().discover(_make_samples())
    shuffled_samples = _make_samples()
    np.random.default_rng(123).shuffle(shuffled_samples)  # type: ignore[arg-type]
    shuffled = _engine().discover(shuffled_samples)
    assert baseline
    assert discovery_content_hash(baseline) == discovery_content_hash(shuffled)


def test_discovery_report_content_hash_is_stable_across_run_ids(tmp_path: Path) -> None:
    agent = PatternDiscoveryLabAgent(provider=object(), settings=Settings(reports_dir=str(tmp_path)))
    candidates = _engine().discover(_make_samples())
    assert candidates
    params = {"timeframe": "1d", "window_sizes": [20], "seed": 42}
    summary = {
        "windows_sampled": 48,
        "clusters_evaluated": len(candidates),
        "accepted_patterns": len(candidates),
        "rejected_patterns": 0,
    }
    first_path = agent._write_report(1, params, dict(summary), candidates)
    second_path = agent._write_report(2, params, dict(summary), candidates)
    assert first_path is not None and second_path is not None
    first_payload = json.loads(first_path.read_text(encoding="utf-8"))
    second_payload = json.loads(second_path.read_text(encoding="utf-8"))
    assert "\n" not in first_path.read_text(encoding="utf-8")
    assert list(first_path.parent.glob(f".{first_path.name}.*.tmp")) == []
    assert first_payload["determinism"]["algo"] == "sha256_canonical_json_v1"
    assert first_payload["determinism"]["content_hash"] == second_payload["determinism"]["content_hash"]
    report_artifact_keys = frozenset({"report_artifacts", "report_artifact_mode"})
    assert first_payload["determinism"]["excluded_keys"] == sorted(
        DEFAULT_VOLATILE_KEYS | report_artifact_keys
    )
    stripped_first = canonical_json(
        {k: v for k, v in first_payload.items() if k != "determinism"},
        exclude_keys=DEFAULT_VOLATILE_KEYS | report_artifact_keys,
    )
    stripped_second = canonical_json(
        {k: v for k, v in second_payload.items() if k != "determinism"},
        exclude_keys=DEFAULT_VOLATILE_KEYS | report_artifact_keys,
    )
    assert stripped_first == stripped_second


def test_discovery_benchmark_json_only_mode_skips_markdown_without_changing_hash(
    tmp_path: Path,
    monkeypatch,
) -> None:
    agent = PatternDiscoveryLabAgent(provider=object(), settings=Settings(reports_dir=str(tmp_path)))
    candidates = _engine().discover(_make_samples())
    assert candidates
    params = {"timeframe": "1d", "window_sizes": [20], "seed": 42}
    summary = {
        "windows_sampled": 48,
        "clusters_evaluated": len(candidates),
        "accepted_patterns": len(candidates),
        "rejected_patterns": 0,
    }

    full_path = agent._write_report(1, params, dict(summary), candidates)
    monkeypatch.setenv("TRADEO_DISCOVERY_BENCHMARK_REPORT_MODE", "json_only")
    json_only_path = agent._write_report(2, params, dict(summary), candidates)

    assert full_path is not None and json_only_path is not None
    assert full_path.with_suffix(".md").exists()
    assert not json_only_path.with_suffix(".md").exists()

    full_payload = json.loads(full_path.read_text(encoding="utf-8"))
    json_only_payload = json.loads(json_only_path.read_text(encoding="utf-8"))
    assert full_payload["summary"]["report_artifacts"]["markdown_written"] is True
    assert json_only_payload["summary"]["report_artifacts"]["markdown_written"] is False
    assert json_only_payload["summary"]["report_artifacts"]["mode"] == "json_only"
    assert (
        full_payload["determinism"]["content_hash"]
        == json_only_payload["determinism"]["content_hash"]
    )


def test_discovery_report_content_hash_excludes_phase_timings(tmp_path: Path) -> None:
    agent = PatternDiscoveryLabAgent(provider=object(), settings=Settings(reports_dir=str(tmp_path)))
    candidates = _engine().discover(_make_samples())
    assert candidates
    params = {"timeframe": "1d", "window_sizes": [20], "seed": 42}
    summary = {
        "windows_sampled": 48,
        "clusters_evaluated": len(candidates),
        "accepted_patterns": len(candidates),
        "rejected_patterns": 0,
    }

    first_path = agent._write_report(
        1,
        params,
        {
            **summary,
            "phase_timings": {"data_fetch_s": 1.0, "clustering_s": 2.0},
            "phase_counts": {"symbols_fetched": 3},
            "phase_diagnostics": {"clustering_profile": {"samples": 10}},
        },
        candidates,
    )
    second_path = agent._write_report(
        2,
        params,
        {
            **summary,
            "phase_timings": {"data_fetch_s": 9.0, "clustering_s": 8.0},
            "phase_counts": {"symbols_fetched": 7},
            "phase_diagnostics": {"clustering_profile": {"samples": 20}},
        },
        candidates,
    )
    assert first_path is not None and second_path is not None

    first_payload = json.loads(first_path.read_text(encoding="utf-8"))
    second_payload = json.loads(second_path.read_text(encoding="utf-8"))

    assert first_payload["summary"]["phase_timings"] != second_payload["summary"]["phase_timings"]
    assert (
        first_payload["summary"]["phase_diagnostics"]
        != second_payload["summary"]["phase_diagnostics"]
    )
    assert first_payload["determinism"]["content_hash"] == second_payload["determinism"]["content_hash"]
    assert "phase_timings" in first_payload["determinism"]["excluded_keys"]
    assert "phase_counts" in first_payload["determinism"]["excluded_keys"]
    assert "phase_diagnostics" in first_payload["determinism"]["excluded_keys"]
