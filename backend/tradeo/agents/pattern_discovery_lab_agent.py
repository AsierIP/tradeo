from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread, get_ident
from typing import Any

import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, DiscoveryRun, ResearchAnalyzedWindow
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.autonomous_research_director import (
    ResearchDirector as PersistentResearchDirector,
)
from tradeo.research.determinism import CONTENT_HASH_ALGO, DEFAULT_VOLATILE_KEYS, content_hash
from tradeo.research.global_experiment_registry import GlobalExperimentRegistry
from tradeo.research.intraday_context_filters import normalize_context_filter_spec
from tradeo.research.novel_pattern_registry import NovelPatternRegistry
from tradeo.research.pattern_committee import PatternResearchCommittee
from tradeo.research.quant_validation import (
    benjamini_hochberg,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
)
from tradeo.research.research_director import ResearchDirector as CandidateResearchDirector
from tradeo.research.validation_gate import ValidationGate
from tradeo.research.intraday_vwap_conditions import expected_side_from_vwap_condition
from tradeo.research.window_sampler import WindowSampler
from tradeo.schemas import DiscoveryRunRequest, DiscoveryRunResponse
from tradeo.services.data_provider import (
    MarketDataProvider,
    load_universe,
    pick_symbols,
    universe_file_for_interval,
    universe_scope_for_interval,
)
from tradeo.services.data_quality import assess_ohlcv_quality_from_settings
from tradeo.services.market_regime import MarketRegimeService
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.universe_snapshot import UniverseSnapshotService

_BENCHMARK_CONTEXT_LOCK = Lock()
_BENCHMARK_FRAMES_CACHE: dict[tuple[str, str], dict[str, Any]] = {}
_BENCHMARK_REGIME_CACHE: dict[str, Any] = {}
_BENCHMARK_REPORT_MODE_ENV = "TRADEO_DISCOVERY_BENCHMARK_REPORT_MODE"
_BENCHMARK_JSON_ONLY_REPORT_VALUES = frozenset({"1", "true", "yes", "json", "json_only"})
_CLUSTER_PROFILE_ENV = "TRADEO_DISCOVERY_CLUSTER_PROFILE"
_CLUSTER_PROFILE_INTERVAL_MS_ENV = "TRADEO_DISCOVERY_CLUSTER_PROFILE_INTERVAL_MS"
_CLUSTER_PROFILE_TOP_N_ENV = "TRADEO_DISCOVERY_CLUSTER_PROFILE_TOP_N"
_CLUSTER_PROFILE_ENABLED_VALUES = frozenset({"1", "true", "yes", "on", "sample", "sampling"})
_PHASE_TIMING_VOLATILE_KEYS = frozenset(
    {"phase_timings", "phase_counts", "phase_diagnostics"}
)
_REPORT_ARTIFACT_VOLATILE_KEYS = frozenset({"report_artifacts", "report_artifact_mode"})
_CLUSTER_ENGINE_FILENAME = "cluster_research_engine.py"


class _PhaseTimer:
    __slots__ = ("_elapsed", "counts", "started")

    def __init__(self) -> None:
        self.started = time.perf_counter()
        self._elapsed: dict[str, float] = {}
        self.counts: dict[str, int] = {}

    @staticmethod
    def mark() -> float:
        return time.perf_counter()

    def add(self, phase: str, started_at: float) -> None:
        self._elapsed[phase] = self._elapsed.get(phase, 0.0) + (
            time.perf_counter() - started_at
        )

    def increment(self, name: str, amount: int = 1) -> None:
        self.counts[name] = self.counts.get(name, 0) + int(amount)

    def timings_snapshot(self, total_duration: float) -> dict[str, float]:
        timings = {phase: round(seconds, 6) for phase, seconds in self._elapsed.items()}
        accounted = sum(self._elapsed.values())
        timings["total_run_s"] = round(total_duration, 3)
        timings["unaccounted_s"] = round(max(total_duration - accounted, 0.0), 6)
        return timings

    def counts_snapshot(self) -> dict[str, int]:
        return dict(self.counts)


class _ClusterStackSampler:
    __slots__ = (
        "_details",
        "_frame_counts",
        "_interval_s",
        "_profiled_s",
        "_started_at",
        "_stop",
        "_target_ident",
        "_thread",
        "_top_n",
    )

    def __init__(self, *, interval_s: float, top_n: int) -> None:
        self._interval_s = max(0.001, float(interval_s))
        self._top_n = max(1, int(top_n))
        self._target_ident = get_ident()
        self._stop = Event()
        self._thread: Thread | None = None
        self._frame_counts: Counter[str] = Counter()
        self._details: dict[str, dict[str, object]] = {}
        self._started_at: float | None = None
        self._profiled_s = 0.0

    def __enter__(self) -> "_ClusterStackSampler":
        self._started_at = time.perf_counter()
        self._thread = Thread(
            target=self._run,
            name="tradeo-cluster-stack-sampler",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self._profiled_s = (
            time.perf_counter() - self._started_at if self._started_at is not None else 0.0
        )
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(0.1, self._interval_s * 2.0))

    def _run(self) -> None:
        while not self._stop.wait(self._interval_s):
            frame = sys._current_frames().get(self._target_ident)
            if frame is None:
                continue
            sample = _cluster_stack_sample(frame)
            key = str(sample["key"])
            self._frame_counts[key] += 1
            if key not in self._details:
                self._details[key] = {
                    name: value for name, value in sample.items() if name != "key"
                }

    def snapshot(self) -> dict[str, object]:
        total = sum(self._frame_counts.values())
        top_frames: list[dict[str, object]] = []
        buckets: Counter[str] = Counter()
        top_keys: set[str] = set()
        for key, count in self._frame_counts.most_common(self._top_n):
            top_keys.add(key)
            detail = dict(self._details.get(key, {}))
            bucket = str(detail.get("bucket") or "unknown")
            buckets[bucket] += int(count)
            top_frames.append(
                {
                    **detail,
                    "samples": int(count),
                    "sample_pct": round((float(count) / max(total, 1)) * 100.0, 3),
                }
            )
        for key, count in self._frame_counts.items():
            if key in top_keys:
                continue
            detail = self._details.get(key, {})
            buckets[str(detail.get("bucket") or "unknown")] += int(count)
        return {
            "method": "thread_stack_sampler_v1",
            "enabled": True,
            "interval_ms": round(self._interval_s * 1000.0, 3),
            "profiled_s": round(float(self._profiled_s), 3),
            "samples": int(total),
            "buckets": [
                {
                    "bucket": bucket,
                    "samples": int(count),
                    "sample_pct": round((float(count) / max(total, 1)) * 100.0, 3),
                }
                for bucket, count in buckets.most_common()
            ],
            "top_frames": top_frames,
        }


def _cluster_stack_sampler_from_env() -> _ClusterStackSampler | None:
    enabled = os.getenv(_CLUSTER_PROFILE_ENV, "").strip().lower()
    if enabled not in _CLUSTER_PROFILE_ENABLED_VALUES:
        return None
    return _ClusterStackSampler(
        interval_s=_cluster_profile_interval_s(),
        top_n=_cluster_profile_top_n(),
    )


def _cluster_profile_interval_s() -> float:
    raw = os.getenv(_CLUSTER_PROFILE_INTERVAL_MS_ENV, "25").strip()
    try:
        interval_ms = float(raw)
    except ValueError:
        interval_ms = 25.0
    return max(1.0, interval_ms) / 1000.0


def _cluster_profile_top_n() -> int:
    raw = os.getenv(_CLUSTER_PROFILE_TOP_N_ENV, "12").strip()
    try:
        return max(1, int(raw))
    except ValueError:
        return 12


def _cluster_stack_sample(frame: Any) -> dict[str, object]:
    selected = None
    cursor = frame
    while cursor is not None:
        if cursor.f_code.co_filename.rsplit(os.sep, 1)[-1] == _CLUSTER_ENGINE_FILENAME:
            selected = cursor
            break
        cursor = cursor.f_back

    if selected is None:
        selected = frame
    filename = selected.f_code.co_filename.rsplit(os.sep, 1)[-1]
    function = selected.f_code.co_name
    line = int(selected.f_lineno)
    return {
        "key": f"{filename}:{function}:{line}",
        "filename": filename,
        "function": function,
        "line": line,
        "bucket": _cluster_profile_bucket(function),
    }


def _cluster_profile_bucket(function: str) -> str:
    if function in {
        "_fit_clusters",
        "_fit_hdbscan_clusters_cached",
        "_fit_hdbscan_clusters",
        "_fit_kmeans_clusters",
        "_assign_density_holdout_labels",
        "_array_cache_digest",
        "_hdbscan_fit_cache_key",
    }:
        return "cluster_fit"
    if function in {
        "_cluster_consensus_ensemble",
        "_consensus_labels",
        "_coassignment_stability",
    }:
        return "consensus_stability"
    if function in {
        "_metrics_for_side",
        "_analyze_reward_risk",
        "_simulate_sample",
        "_simulate_sample_detail",
        "_null_baseline",
        "_stratified_draw",
        "_bootstrap_confidence",
        "_split_metrics",
        "_cost_stress_metrics",
        "_outcome_metrics",
        "_group_expectancy",
        "_sharpe_diagnostics",
        "_edge_decay_metrics",
    }:
        return "reward_risk_metrics"
    if function in {
        "_walk_forward_metrics",
        "_purged_combinatorial_cv",
        "_quant_validation_metrics",
    }:
        return "validation_metrics"
    if function in {
        "_false_match_metrics",
        "_match_tau_similarity",
        "_match_conformal_threshold",
        "_prototype_match_contract",
        "_shape_match_contract",
        "_cluster_signature",
    }:
        return "match_contract"
    if function in {"_regime_profile", "_benchmark_regime_outcomes"}:
        return "regime_diagnostics"
    if function in {"_feature_summary", "_human_rule", "_examples"}:
        return "candidate_output"
    if function == "_apply_novelty_diversity":
        return "novelty_diversity"
    if function in {"discover", "_cluster_window_size"}:
        return "orchestration"
    return "other_cluster_engine"


@dataclass(slots=True)
class PatternDiscoveryLabAgent:
    """Autonomous laboratory agent for unknown technical pattern discovery.

    This agent is intentionally unable to create orders. Its output is a compact,
    token-efficient digest: the LLM supervisor receives only accepted/rejected
    cluster statistics and representative examples, never millions of raw bars.
    """

    provider: MarketDataProvider | None = None
    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.provider = self.provider or get_market_data_provider()

    def run(self, request: DiscoveryRunRequest, db: Session) -> DiscoveryRunResponse:
        settings = self.settings
        assert settings is not None
        timer = _PhaseTimer()
        started = timer.started
        warnings: list[str] = []
        clustering_diagnostics: dict[str, object] | None = None
        phase_started = timer.mark()
        params = self._resolve_params(request)
        timer.add("resolve_params_s", phase_started)
        run = DiscoveryRun(status="running", params_json=params)
        phase_started = timer.mark()
        db.add(run)
        db.commit()
        db.refresh(run)
        timer.add("db_run_create_s", phase_started)
        logger.info("pattern discovery run {} started with params {}", run.id, params)

        try:
            phase_started = timer.mark()
            symbols = self._resolve_symbols(request, params)
            timer.add("resolve_symbols_s", phase_started)
            timer.increment("symbols_resolved", len(symbols))
            phase_started = timer.mark()
            universe_snapshot = self._build_universe_snapshot(
                warnings,
                universe_file=params["universe_file"],
            )
            timer.add("universe_snapshot_s", phase_started)
            samples = []
            sampler = WindowSampler(target_r=settings.discovery_min_reward_risk)
            frame_cache_key = (str(params.get("period") or ""), str(params.get("interval") or ""))
            frame_cache_hit = frame_cache_key in _BENCHMARK_FRAMES_CACHE
            phase_started = timer.mark()
            benchmark_frames = self._benchmark_frames(params, warnings)
            timer.add("benchmark_frames_s", phase_started)
            timer.increment(
                "benchmark_frames_cache_hits" if frame_cache_hit else "benchmark_frames_cache_misses"
            )
            timer.increment("benchmark_frames_returned", len(benchmark_frames))
            regime_cache_key = str(params.get("period") or "")
            regime_cache_hit = regime_cache_key in _BENCHMARK_REGIME_CACHE
            phase_started = timer.mark()
            benchmark_regime_table = self._benchmark_regime_table(params, warnings)
            timer.add("benchmark_regime_s", phase_started)
            timer.increment(
                "benchmark_regime_cache_hits"
                if regime_cache_hit
                else "benchmark_regime_cache_misses"
            )
            if benchmark_regime_table is not None:
                timer.increment("benchmark_regime_tables_returned")
            for symbol in symbols:
                if len(samples) >= params["max_total_windows"]:
                    break
                try:
                    timer.increment("symbols_attempted")
                    phase_started = timer.mark()
                    try:
                        df = self.provider.fetch_ohlcv(
                            symbol, period=params["period"], interval=params["interval"]
                        )
                    finally:
                        timer.add("data_fetch_s", phase_started)
                    timer.increment("symbols_fetched")
                    if settings.data_quality_filter_enabled:
                        phase_started = timer.mark()
                        quality = assess_ohlcv_quality_from_settings(
                            df,
                            symbol,
                            params["interval"],
                            settings,
                        )
                        timer.add("data_quality_s", phase_started)
                        if not quality.research_grade:
                            timer.increment("symbols_quality_rejected")
                            msg = f"{symbol}: OHLCV not research grade ({','.join(quality.issues)})"
                            logger.warning("discovery data quality reject: {}", msg)
                            warnings.append(msg)
                            phase_started = timer.mark()
                            db.add(
                                AuditLog(
                                    actor="PatternDiscoveryLabAgent",
                                    action="market_data_quality_reject",
                                    entity_type="symbol",
                                    entity_id=symbol,
                                    details_json=quality.to_dict(),
                                )
                            )
                            db.commit()
                            timer.add("data_quality_audit_commit_s", phase_started)
                            continue
                    phase_started = timer.mark()
                    try:
                        seen_window_keys = self._seen_window_keys(
                            db,
                            symbol=symbol,
                            timeframe=params["interval"],
                            universe_key=params["universe_key"],
                        )
                        timer.increment("windows_seen_ledger_loaded", len(seen_window_keys))
                        symbol_samples = sampler.sample(
                            symbol=symbol,
                            df=df,
                            timeframe=params["interval"],
                            window_sizes=params["window_sizes"],
                            forward_bars=params["forward_bars"],
                            stride=params["stride"],
                            max_windows_per_symbol=params["max_windows_per_symbol"],
                            benchmark_frames=benchmark_frames,
                            vwap_condition=params["vwap_condition"],
                            vwap_side_bias=params["vwap_side_bias"],
                            vwap_max_distance_bps=params["vwap_max_distance_bps"],
                            vwap_min_slope_bps=params["vwap_min_slope_bps"],
                            session_filter=params["session_filter"],
                            cost_filter=params["cost_filter"],
                            max_execution_cost_r=params["max_execution_cost_r"],
                            skip_window_keys=seen_window_keys,
                        )
                    finally:
                        timer.add("sampling_embedding_s", phase_started)
                    diagnostics = sampler.last_diagnostics
                    timer.increment(
                        "windows_vwap_rejected",
                        int(diagnostics.get("windows_vwap_rejected", 0)),
                    )
                    timer.increment(
                        "windows_vwap_selected",
                        int(diagnostics.get("windows_vwap_selected", 0)),
                    )
                    if bool(diagnostics.get("vwap_condition_applied")):
                        timer.increment("vwap_condition_applied")
                    timer.increment(
                        "windows_session_rejected",
                        int(diagnostics.get("windows_session_rejected", 0)),
                    )
                    timer.increment(
                        "windows_cost_rejected",
                        int(diagnostics.get("windows_cost_rejected", 0)),
                    )
                    timer.increment(
                        "windows_duplicate_skipped",
                        int(diagnostics.get("windows_duplicate_skipped", 0)),
                    )
                    timer.increment(
                        "windows_selected",
                        int(diagnostics.get("windows_selected", 0)),
                    )
                    remaining = params["max_total_windows"] - len(samples)
                    selected_samples = symbol_samples[:remaining]
                    if selected_samples:
                        recorded = self._record_analyzed_windows(
                            db,
                            selected_samples,
                            run_id=run.id,
                            params=params,
                        )
                        timer.increment("windows_seen_ledger_recorded", recorded)
                    samples.extend(selected_samples)
                    timer.increment("windows_sampled", len(selected_samples))
                except Exception as exc:  # noqa: BLE001
                    timer.increment("symbol_failures")
                    msg = f"{symbol}: {exc}"
                    logger.warning("discovery symbol failed: {}", msg)
                    warnings.append(msg)
                    continue

            engine = ClusterResearchEngine(
                min_cluster_size=params["min_cluster_size"],
                max_clusters_per_window=params["max_clusters_per_window"],
                target_r=settings.discovery_min_reward_risk,
                out_of_sample_pct=settings.discovery_out_of_sample_pct,
                rr_levels=params["rr_levels"],
                min_samples=self._min_samples_for_params(params),
                walk_forward_folds=settings.discovery_walk_forward_folds,
                walk_forward_embargo_samples=settings.discovery_walk_forward_embargo_samples,
                cost_stress_multipliers=settings.discovery_cost_stress_multiplier_list,
                required_cost_stress_multiplier=settings.discovery_required_cost_stress_multiplier,
                event_ledger_limit=0,
                match_tau_percentile=settings.discovery_match_tau_percentile,
                clusterer_method=settings.discovery_clusterer_method,
                clusterer_min_samples=(
                    settings.discovery_clusterer_min_samples
                    if settings.discovery_clusterer_min_samples > 0
                    else None
                ),
                consensus_repeats=settings.discovery_cluster_consensus_repeats,
                consensus_subsample_pct=settings.discovery_cluster_consensus_subsample_pct,
                shape_dtw_band_pct=settings.discovery_match_shape_dtw_band_pct,
                shape_dtw_threshold_quantile=settings.discovery_match_shape_dtw_threshold_quantile,
                shape_dtw_method=settings.discovery_match_shape_dtw_method,
                shape_soft_dtw_gamma=settings.discovery_match_shape_soft_dtw_gamma,
                benchmark_regime_table=benchmark_regime_table,
                conformal_alpha=settings.discovery_match_conformal_alpha,
                prototype_medoid_count=settings.discovery_match_prototype_medoids,
                prototype_knn_k=settings.discovery_match_knn_k,
            )
            phase_started = timer.mark()
            clustering_sampler = _cluster_stack_sampler_from_env()
            try:
                if clustering_sampler is None:
                    raw_candidates = engine.discover(samples)
                else:
                    with clustering_sampler:
                        raw_candidates = engine.discover(samples)
            finally:
                timer.add("clustering_s", phase_started)
                if clustering_sampler is not None:
                    clustering_diagnostics = clustering_sampler.snapshot()
            timer.increment("raw_candidates", len(raw_candidates))
            phase_started = timer.mark()
            try:
                data_manifest = self._data_manifest(run.id, symbols, warnings, params=params)
            finally:
                timer.add("data_manifest_s", phase_started)
            phase_started = timer.mark()
            try:
                enriched_windows = self._enrich_analyzed_windows(
                    db,
                    run_id=run.id,
                    params=params,
                    data_manifest=data_manifest,
                )
                timer.increment("windows_seen_ledger_enriched", enriched_windows)
            finally:
                timer.add("window_history_enrich_s", phase_started)
            for candidate in raw_candidates:
                candidate.metrics["data_manifest"] = {
                    "path": data_manifest.get("path"),
                    "manifest_hash": data_manifest.get("manifest_hash"),
                    "entry_count": len((data_manifest.get("entries") or {})),
                    "artifact_format": data_manifest.get("artifact_format"),
                }
                candidate.metrics["universe_snapshot"] = universe_snapshot
                candidate.metrics["universe_point_in_time"] = bool(
                    universe_snapshot.get(
                        "point_in_time", settings.universe_point_in_time_available
                    )
                )
                candidate.metrics["survivorship_biased"] = not bool(
                    candidate.metrics["universe_point_in_time"]
                )
            phase_started = timer.mark()
            try:
                self._apply_run_level_inference(raw_candidates)
            finally:
                timer.add("run_level_inference_s", phase_started)
            phase_started = timer.mark()
            try:
                candidates = ValidationGate(settings).evaluate_many(raw_candidates)
            finally:
                timer.add("validation_s", phase_started)
            timer.increment("validated_candidates", len(candidates))
            accepted = [c for c in candidates if c.validation_passed]
            rejected = [c for c in candidates if not c.validation_passed]
            timer.increment("accepted_candidates", len(accepted))
            timer.increment("rejected_candidates", len(rejected))
            phase_started = timer.mark()
            try:
                ledger_artifacts = self._write_event_ledgers(run.id, candidates)
            finally:
                timer.add("event_ledgers_s", phase_started)
            timer.increment("event_ledgers_written", ledger_artifacts)
            phase_started = timer.mark()
            try:
                global_registry = self._register_global_experiments(
                    candidates,
                    accepted=accepted,
                    run_id=run.id,
                    params=params,
                )
            finally:
                timer.add("global_registry_s", phase_started)
            candidate_director_summary: dict[str, Any] = {}
            if settings.research_director_enabled and accepted:
                phase_started = timer.mark()
                try:
                    logger.info(
                        "Research Director: enriqueciendo candidatos aceptados antes del registry"
                    )
                    candidate_director_summary = CandidateResearchDirector(settings=settings).run(
                        run_id=run.id,
                        candidates=accepted,
                        samples=samples,
                        params=params,
                    )
                except Exception as exc:  # noqa: BLE001
                    msg = f"CandidateResearchDirector failed: {exc}"
                    logger.exception(msg)
                    warnings.append(msg)
                finally:
                    timer.add("candidate_director_s", phase_started)
            committee_summary: dict[str, Any] = {}
            if settings.research_committee_enabled and accepted:
                phase_started = timer.mark()
                try:
                    logger.info(
                        "PatternResearchCommittee: revisando candidatos aceptados antes del registry"
                    )
                    committee_summary = PatternResearchCommittee(
                        settings=settings
                    ).review_candidates(
                        accepted,
                        run_id=run.id,
                        params=params,
                    )
                finally:
                    timer.add("research_committee_s", phase_started)
            phase_started = timer.mark()
            try:
                stored = NovelPatternRegistry().store_candidates(
                    db,
                    candidates,
                    run_id=run.id,
                    store_rejected=params["store_rejected"],
                )
            finally:
                timer.add("novel_registry_s", phase_started)
            timer.increment("stored_patterns", len(stored))
            director_result: dict[str, Any] | None = None
            if settings.research_director_enabled and accepted:
                phase_started = timer.mark()
                try:
                    director_result = PersistentResearchDirector(settings).run(
                        db,
                        run_id=run.id,
                        limit=settings.research_director_pattern_limit,
                    )
                except Exception as exc:  # noqa: BLE001
                    msg = f"ResearchDirector failed: {exc}"
                    logger.exception(msg)
                    warnings.append(msg)
                finally:
                    timer.add("db_director_s", phase_started)
            phase_started = timer.mark()
            summary = self._summary(candidates, samples, warnings)
            summary["data_manifest"] = {
                "path": data_manifest.get("path"),
                "manifest_hash": data_manifest.get("manifest_hash"),
                "entry_count": len((data_manifest.get("entries") or {})),
                "artifact_format": data_manifest.get("artifact_format"),
            }
            summary["universe_snapshot"] = universe_snapshot
            summary["global_experiment_registry"] = global_registry
            summary["research_director"] = {
                "candidate_completion": candidate_director_summary,
            }
            summary["research_committee"] = committee_summary
            summary["vwap_conditioning"] = {
                "vwap_condition": params["vwap_condition"],
                "vwap_side_bias": params["vwap_side_bias"],
                "vwap_expected_side": params["vwap_expected_side"],
                "vwap_max_distance_bps": params["vwap_max_distance_bps"],
                "vwap_min_slope_bps": params["vwap_min_slope_bps"],
                "applied": params["vwap_condition"] != "none",
                "windows_vwap_rejected": timer.counts.get("windows_vwap_rejected", 0),
                "windows_vwap_selected": timer.counts.get("windows_vwap_selected", 0),
            }
            summary["context_filtering"] = {
                "vwap_condition": params["vwap_condition"],
                "session_filter": params["session_filter"],
                "cost_filter": params["cost_filter"],
                "max_execution_cost_r": params["max_execution_cost_r"],
                "windows_vwap_rejected": timer.counts.get("windows_vwap_rejected", 0),
                "windows_session_rejected": timer.counts.get("windows_session_rejected", 0),
                "windows_cost_rejected": timer.counts.get("windows_cost_rejected", 0),
                "windows_duplicate_skipped": timer.counts.get(
                    "windows_duplicate_skipped", 0
                ),
                "windows_selected": timer.counts.get("windows_selected", 0),
            }
            if clustering_diagnostics is not None:
                summary["phase_diagnostics"] = {
                    "clustering_profile": clustering_diagnostics,
                }
            if director_result is not None:
                summary["research_director"]["db_director"] = {
                    "patterns_reviewed": director_result.get("patterns_reviewed", 0),
                    "hypotheses_created": director_result.get("hypotheses_created", 0),
                    "director_state": director_result.get("director_state", {}),
                    "artifacts": director_result.get("artifacts", {}),
                }
            timer.add("summary_build_s", phase_started)
            duration = round(time.perf_counter() - started, 3)
            summary["phase_timings"] = timer.timings_snapshot(duration)
            summary["phase_counts"] = timer.counts_snapshot()
            phase_started = timer.mark()
            try:
                report_path = self._write_report(run.id, params, summary, candidates)
            finally:
                timer.add("report_write_s", phase_started)
            duration = round(time.perf_counter() - started, 3)
            summary["phase_timings"] = timer.timings_snapshot(duration)
            summary["phase_counts"] = timer.counts_snapshot()
            run.status = "completed"
            run.finished_at = datetime.now(timezone.utc)
            run.symbols_scanned = len(symbols)
            run.windows_sampled = len(samples)
            run.clusters_evaluated = len(candidates)
            run.accepted_patterns = len(accepted)
            run.rejected_patterns = len(rejected)
            run.duration_seconds = duration
            run.summary_json = summary
            run.report_path = str(report_path) if report_path else None
            db.add(
                AuditLog(
                    actor="PatternDiscoveryLabAgent",
                    action="discovery_run_completed",
                    entity_type="discovery_run",
                    entity_id=str(run.id),
                    details_json={
                        "symbols": len(symbols),
                        "windows": len(samples),
                        "clusters": len(candidates),
                        "accepted": len(accepted),
                        "rejected": len(rejected),
                        "stored": len(stored),
                        "research_director": summary.get("research_director", {}),
                        "research_committee": summary.get("research_committee", {}),
                        "event_ledgers": ledger_artifacts,
                        "data_manifest": summary.get("data_manifest", {}),
                        "universe_snapshot": universe_snapshot,
                        "phase_timings": summary.get("phase_timings", {}),
                        "phase_counts": summary.get("phase_counts", {}),
                        "report_path": str(report_path) if report_path else None,
                    },
                )
            )
            db.commit()
            return DiscoveryRunResponse(
                run_id=run.id,
                status="completed",
                symbols_scanned=len(symbols),
                windows_sampled=len(samples),
                clusters_evaluated=len(candidates),
                accepted_patterns=len(accepted),
                rejected_patterns=len(rejected),
                stored_patterns=len(stored),
                duration_seconds=duration,
                report_path=str(report_path) if report_path else None,
                actual_resolved_params=params,
                top_patterns=summary["top_patterns"],
                warnings=warnings[:50],
            )
        except Exception as exc:  # noqa: BLE001
            duration = round(time.perf_counter() - started, 3)
            failure_summary = {
                "error": str(exc),
                "warnings": warnings,
                "phase_timings": timer.timings_snapshot(duration),
                "phase_counts": timer.counts_snapshot(),
            }
            if clustering_diagnostics is not None:
                failure_summary["phase_diagnostics"] = {
                    "clustering_profile": clustering_diagnostics,
                }
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.duration_seconds = duration
            run.summary_json = failure_summary
            db.add(run)
            db.add(
                AuditLog(
                    actor="PatternDiscoveryLabAgent",
                    action="discovery_run_failed",
                    entity_type="discovery_run",
                    entity_id=str(run.id),
                    details_json={
                        "error": str(exc),
                        "warnings": warnings[:50],
                        "phase_timings": failure_summary["phase_timings"],
                        "phase_counts": failure_summary["phase_counts"],
                    },
                )
            )
            db.commit()
            raise

    @staticmethod
    def _window_key(sample: Any) -> tuple[str, str, str, str, int]:
        return (
            str(getattr(sample, "symbol", "")).upper(),
            str(getattr(sample, "timeframe", "")),
            str(getattr(sample, "start", "")),
            str(getattr(sample, "end", "")),
            int(getattr(sample, "window_size", 0) or 0),
        )

    @staticmethod
    def _window_fingerprint(
        *,
        universe_key: str,
        symbol: str,
        timeframe: str,
        window_start: str,
        window_end: str,
        window_size: int,
        source_kind: str = "sampler",
    ) -> str:
        payload = "|".join(
            (
                "research-window-v2",
                universe_key,
                symbol.upper(),
                timeframe,
                window_start,
                window_end,
                str(int(window_size)),
                source_kind,
            )
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _seen_window_keys(
        self,
        db: Session,
        *,
        symbol: str,
        timeframe: str,
        universe_key: str,
    ) -> set[tuple[str, str, str, str, int]]:
        rows = (
            db.query(
                ResearchAnalyzedWindow.symbol,
                ResearchAnalyzedWindow.timeframe,
                ResearchAnalyzedWindow.window_start,
                ResearchAnalyzedWindow.window_end,
                ResearchAnalyzedWindow.window_size,
            )
            .filter(ResearchAnalyzedWindow.symbol == symbol.upper())
            .filter(ResearchAnalyzedWindow.timeframe == timeframe)
            .filter(ResearchAnalyzedWindow.universe_key == universe_key)
            .all()
        )
        return {
            (row.symbol, row.timeframe, row.window_start, row.window_end, int(row.window_size))
            for row in rows
        }

    def _record_analyzed_windows(
        self,
        db: Session,
        samples: list[Any],
        *,
        run_id: int,
        params: dict[str, Any],
        source_kind: str = "sampler",
        source_artifact_path: str = "",
    ) -> int:
        records: list[ResearchAnalyzedWindow] = []
        fingerprints: list[str] = []
        universe_key = str(params.get("universe_key") or "")
        for sample in samples:
            symbol, timeframe, window_start, window_end, window_size = self._window_key(sample)
            fingerprint = self._window_fingerprint(
                universe_key=universe_key,
                symbol=symbol,
                timeframe=timeframe,
                window_start=window_start,
                window_end=window_end,
                window_size=window_size,
                source_kind=source_kind,
            )
            fingerprints.append(fingerprint)
            records.append(
                ResearchAnalyzedWindow(
                    fingerprint=fingerprint,
                    run_id=run_id,
                    cadence=str(params.get("cadence") or ""),
                    universe_key=universe_key,
                    universe_scope=str(params.get("universe_scope") or ""),
                    universe_file=str(params.get("universe_file") or ""),
                    universe_hash=str(params.get("universe_hash") or ""),
                    symbol=symbol,
                    timeframe=timeframe,
                    window_start=window_start,
                    window_end=window_end,
                    window_size=window_size,
                    forward_end=str(getattr(getattr(sample, "outcome", None), "forward_end", "") or ""),
                    data_period=str(params.get("period") or ""),
                    source_kind=source_kind,
                    source_artifact_path=source_artifact_path,
                    metadata_json={
                        "year": getattr(sample, "year", None),
                        "features": self._window_history_feature_subset(
                            getattr(sample, "features", {}) or {}
                        ),
                    },
                )
            )
        if not records:
            return 0
        existing = {
            row[0]
            for row in db.query(ResearchAnalyzedWindow.fingerprint)
            .filter(ResearchAnalyzedWindow.fingerprint.in_(fingerprints))
            .all()
        }
        new_records = [record for record in records if record.fingerprint not in existing]
        if not new_records:
            return 0
        db.add_all(new_records)
        db.flush()
        return len(new_records)

    def _enrich_analyzed_windows(
        self,
        db: Session,
        *,
        run_id: int,
        params: dict[str, Any],
        data_manifest: dict[str, Any],
    ) -> int:
        entries = data_manifest.get("entries")
        if not isinstance(entries, dict):
            return 0
        by_symbol = {
            str(entry.get("symbol") or "").upper(): entry
            for entry in entries.values()
            if isinstance(entry, dict)
        }
        rows = (
            db.query(ResearchAnalyzedWindow)
            .filter(ResearchAnalyzedWindow.run_id == run_id)
            .filter(ResearchAnalyzedWindow.data_manifest_hash == "")
            .all()
        )
        updated = 0
        manifest_hash = str(data_manifest.get("manifest_hash") or "")
        for row in rows:
            entry = by_symbol.get(row.symbol.upper())
            row.data_manifest_hash = manifest_hash
            row.data_period = str(params.get("period") or row.data_period or "")
            if entry:
                row.data_artifact_path = str(entry.get("path") or "")
                row.data_artifact_sha256 = str(entry.get("sha256") or "")
                row.data_rows = int(entry.get("rows") or 0)
            updated += 1
        if updated:
            db.flush()
        return updated

    @staticmethod
    def _window_history_feature_subset(features: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "adjusted",
            "what_to_show",
            "bar_complete",
            "session_bucket",
            "liquidity_bucket",
            "rvol_bucket",
            "gap_bucket",
            "regime_bucket",
            "timestamp_timezone_assumption",
        )
        return {key: features[key] for key in keys if key in features}

    def _min_samples_for_params(self, params: dict[str, Any]) -> int:
        settings = self.settings
        assert settings is not None
        if str(params.get("cadence") or "").lower() == "intraday":
            return int(params.get("min_samples") or settings.intraday_research_min_samples)
        return int(settings.discovery_min_samples)

    def _register_global_experiments(
        self,
        candidates: list[Any],
        *,
        accepted: list[Any],
        run_id: int,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        path = settings.reports_path / "research" / "global_experiment_registry.json"
        registry_candidates = candidates if bool(params.get("store_rejected", True)) else accepted
        skipped_rejected = max(0, len(candidates) - len(registry_candidates))
        if not registry_candidates:
            return {
                "path": str(path),
                "new_experiments": 0,
                "repeated_experiments": 0,
                "experiment_count": 0,
                "global_trial_count": 0,
                "skipped_rejected_experiments": skipped_rejected,
                "store_rejected": bool(params.get("store_rejected", True)),
            }
        result = GlobalExperimentRegistry(path).register(
            registry_candidates,
            run_id=run_id,
            params=params,
        )
        if skipped_rejected:
            result["skipped_rejected_experiments"] = skipped_rejected
            result["store_rejected"] = False
        return result

    def _apply_run_level_inference(self, candidates: list[Any]) -> None:
        """Run-level selective inference: BH-FDR + family-deflated Sharpe.

        Per-candidate p-values already exist (stratified permutation vs null
        baselines), but each one ignores how many sibling hypotheses this run
        tested. Benjamini-Hochberg is applied over every cluster evaluated in
        the run — accepted and rejected alike — and the DSR is deflated with the
        N_trials accumulated in the global experiment registry, so the bar for
        lab_candidate rises automatically as more mining happens.
        """
        settings = self.settings
        assert settings is not None
        if not candidates:
            return
        pvals: list[float] = []
        indexed: list[Any] = []
        for candidate in candidates:
            p = candidate.metrics.get("null_p_value")
            try:
                p = float(p)
            except (TypeError, ValueError):
                p = float("nan")
            if np.isfinite(p):
                pvals.append(min(max(p, 0.0), 1.0))
                indexed.append(candidate)
        if pvals:
            passed_mask, cutoff = benjamini_hochberg(pvals, q=settings.discovery_fdr_q)
            for candidate, passed in zip(indexed, passed_mask, strict=True):
                candidate.metrics["fdr_q"] = settings.discovery_fdr_q
                candidate.metrics["fdr_passed"] = bool(passed)
                candidate.metrics["fdr_cutoff_p"] = float(cutoff) if np.isfinite(cutoff) else None
                candidate.metrics["fdr_test_count"] = len(pvals)

        registry_payload = GlobalExperimentRegistry(
            settings.reports_path / "research" / "global_experiment_registry.json"
        ).load()
        prior_trials = int(registry_payload.get("global_trial_count", 0) or 0)
        trials_by_window: dict[int, int] = {}
        for candidate in candidates:
            window = int(getattr(candidate, "window_size", 0))
            count = int(candidate.metrics.get("real_variant_count", 1) or 1)
            trials_by_window[window] = max(trials_by_window.get(window, 0), count)
        run_trials = sum(trials_by_window.values())
        n_trials_total = max(1, prior_trials + run_trials)

        sharpes = np.asarray(
            [float(c.metrics.get("trade_sharpe", 0.0) or 0.0) for c in candidates], dtype=float
        )
        sharpes = sharpes[np.isfinite(sharpes)]
        sr_std = float(np.std(sharpes, ddof=1)) if sharpes.size >= 3 else 0.0

        for candidate in candidates:
            quant = candidate.metrics.get("quant_validation", {})
            if not isinstance(quant, dict):
                quant = {}
            n_eff = float(quant.get("n_eff", 0.0) or 0.0)
            sr = float(
                quant.get("sharpe_per_trade", candidate.metrics.get("trade_sharpe", 0.0)) or 0.0
            )
            skew = float(quant.get("skew", 0.0) or 0.0)
            kurt = float(quant.get("kurtosis", 3.0) or 3.0)
            if n_eff > 1 and sr_std > 0 and n_trials_total > 1:
                dsr, sr_star = deflated_sharpe_ratio(sr, n_eff, skew, kurt, n_trials_total, sr_std)
            elif n_eff > 1:
                dsr = probabilistic_sharpe_ratio(sr, 0.0, n_eff, skew, kurt)
                sr_star = 0.0
            else:
                dsr, sr_star = float("nan"), 0.0
            candidate.metrics["dsr_family"] = round(float(dsr), 5) if np.isfinite(dsr) else None
            candidate.metrics["dsr_family_sr_star"] = round(float(sr_star), 5)
            candidate.metrics["dsr_family_n_trials"] = n_trials_total
            candidate.metrics["dsr_family_sr_std"] = round(sr_std, 5)
            candidate.metrics["dsr_family_prior_registry_trials"] = prior_trials
            candidate.metrics["dsr_family_run_trials"] = run_trials

    def _resolve_params(self, request: DiscoveryRunRequest) -> dict[str, Any]:
        s = self.settings
        assert s is not None
        max_total_windows = min(request.max_total_windows or s.discovery_max_total_windows, 80_000)
        universe_scope = universe_scope_for_interval(request.interval or s.discovery_interval)
        universe_file = universe_file_for_interval(
            s,
            request.interval or s.discovery_interval,
        )
        is_intraday = universe_scope != "daily_midcap"
        context_spec = normalize_context_filter_spec(
            session_filter=request.session_filter,
            cost_filter=request.cost_filter,
            max_execution_cost_r=request.max_execution_cost_r,
        )
        return {
            "limit": request.limit or s.discovery_limit_default,
            "period": request.period or s.discovery_period,
            "interval": request.interval or s.discovery_interval,
            "cadence": "intraday" if is_intraday else "daily",
            "universe_scope": universe_scope,
            "universe_file": universe_file,
            "universe_hash": self._file_sha256(universe_file),
            "universe_key": self._universe_key(
                scope=universe_scope,
                universe_file=universe_file,
            ),
            "symbols": [symbol.upper().strip() for symbol in request.symbols if symbol.strip()]
            if request.symbols
            else None,
            "window_sizes": request.window_sizes or s.discovery_window_size_list,
            "forward_bars": request.forward_bars or s.discovery_forward_bar_list,
            "stride": max(1, request.stride or s.discovery_stride),
            "max_total_windows": max(100, max_total_windows),
            "max_windows_per_symbol": max(
                50, request.max_windows_per_symbol or s.discovery_max_windows_per_symbol
            ),
            "min_cluster_size": max(20, request.min_cluster_size or s.discovery_min_cluster_size),
            "max_clusters_per_window": max(
                2, min(request.max_clusters_per_window or s.discovery_max_clusters_per_window, 40)
            ),
            "store_rejected": s.discovery_store_rejected
            if request.store_rejected is None
            else request.store_rejected,
            "vwap_condition": (request.vwap_condition or "none").strip().lower() or "none",
            "vwap_side_bias": (request.vwap_side_bias or "").strip().lower() or None,
            "vwap_expected_side": expected_side_from_vwap_condition(request.vwap_condition, request.vwap_side_bias),
            "vwap_max_distance_bps": request.vwap_max_distance_bps,
            "vwap_min_slope_bps": request.vwap_min_slope_bps,
            "session_filter": context_spec.session_filter,
            "cost_filter": context_spec.cost_filter,
            "max_execution_cost_r": context_spec.max_execution_cost_r,
            "rr_levels": s.discovery_rr_level_list,
            "min_reward_risk": s.discovery_min_reward_risk,
            "candidate_reward_risk": s.discovery_candidate_reward_risk,
            "premium_reward_risk": s.discovery_premium_reward_risk,
            "max_drawdown_r": s.discovery_max_drawdown_r,
            "walk_forward_folds": s.discovery_walk_forward_folds,
            "walk_forward_embargo_samples": s.discovery_walk_forward_embargo_samples,
            "cost_stress_multipliers": s.discovery_cost_stress_multiplier_list,
            "required_cost_stress_multiplier": s.discovery_required_cost_stress_multiplier,
            "min_samples": s.intraday_research_min_samples
            if is_intraday
            else s.discovery_min_samples,
            "min_effective_samples": (
                s.intraday_research_min_effective_samples
                if is_intraday
                else s.discovery_min_effective_samples
            ),
            "min_symbols": s.intraday_research_min_symbols
            if is_intraday
            else s.discovery_min_symbols,
            "min_years": s.intraday_research_min_years if is_intraday else s.discovery_min_years,
        }

    @staticmethod
    def _file_sha256(path: str | os.PathLike[str]) -> str:
        try:
            with open(path, "rb") as handle:
                digest = hashlib.sha256()
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
                return digest.hexdigest()
        except OSError:
            return ""

    @classmethod
    def _universe_key(cls, *, scope: str, universe_file: str) -> str:
        payload = {
            "scope": scope,
            "file": str(universe_file),
            "sha256": cls._file_sha256(universe_file),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()[:24]
        return f"{scope}:{digest}"

    def _resolve_symbols(self, request: DiscoveryRunRequest, params: dict[str, Any]) -> list[str]:
        if request.symbols:
            return [s.upper().strip() for s in request.symbols if s.strip()]
        return pick_symbols(
            limit=params["limit"],
            interval=params["interval"],
            universe_file=params["universe_file"],
        )

    def _build_universe_snapshot(
        self, warnings: list[str], *, universe_file: str
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        if not settings.universe_snapshot_monthly:
            return {
                "enabled": False,
                "source_universe_file": universe_file,
                "point_in_time": settings.universe_point_in_time_available,
                "survivorship_biased": not settings.universe_point_in_time_available,
            }
        try:
            return UniverseSnapshotService(settings).build_monthly_snapshot(
                universe=load_universe(universe_file),
                source_universe_file=universe_file,
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"UniverseSnapshotService failed: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return {
                "enabled": True,
                "error": str(exc),
                "source_universe_file": universe_file,
                "point_in_time": settings.universe_point_in_time_available,
                "survivorship_biased": not settings.universe_point_in_time_available,
            }

    def _data_manifest(
        self,
        run_id: int,
        symbols: list[str],
        warnings: list[str],
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        provider_manifest = getattr(self.provider, "data_manifest", None)
        if not callable(provider_manifest):
            return self._write_data_manifest(
                run_id,
                {
                    "schema_version": 1,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "entries": {},
                    "manifest_hash": "",
                    "artifact_format": "unavailable",
                    "reason": "provider_does_not_expose_data_manifest",
                },
            )
        try:
            payload = provider_manifest(
                symbols,
                period=(params or {}).get("period"),
                interval=(params or {}).get("interval"),
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"data_manifest failed: {exc}")
            payload = {
                "schema_version": 1,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "entries": {},
                "manifest_hash": "",
                "artifact_format": "unavailable",
                "reason": str(exc),
            }
        return self._write_data_manifest(run_id, payload)

    def _write_data_manifest(self, run_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        manifest_dir = settings.reports_path / "research" / "data_manifests"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        path = manifest_dir / f"discovery_run_{run_id}_data_manifest.json"
        self._atomic_write_bytes(path, self._json_bytes(payload, sort_keys=True))
        payload = dict(payload)
        payload["path"] = str(path)
        return payload

    def _benchmark_frames(self, params: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
        key = (str(params.get("period") or ""), str(params.get("interval") or ""))
        with _BENCHMARK_CONTEXT_LOCK:
            cached = _BENCHMARK_FRAMES_CACHE.get(key)
            if cached is not None:
                return {symbol: frame.copy() for symbol, frame in cached.items()}

            frames: dict[str, Any] = {}
            assert self.provider is not None
            for symbol in ("SPY", "QQQ"):
                try:
                    frames[symbol] = self.provider.fetch_ohlcv(
                        symbol,
                        period=params["period"],
                        interval=params["interval"],
                    )
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"{symbol} benchmark unavailable: {exc}")
            _BENCHMARK_FRAMES_CACHE[key] = {
                symbol: frame.copy() for symbol, frame in frames.items()
            }
            return frames

    def _benchmark_regime_table(self, params: dict[str, Any], warnings: list[str]) -> Any:
        key = str(params.get("period") or "")
        with _BENCHMARK_CONTEXT_LOCK:
            cached = _BENCHMARK_REGIME_CACHE.get(key)
            if cached is not None:
                return cached.copy() if hasattr(cached, "copy") else cached

            assert self.provider is not None
            try:
                table = MarketRegimeService(
                    provider=self.provider, settings=self.settings
                ).history_table(period=str(params.get("period") or ""))
                _BENCHMARK_REGIME_CACHE[key] = table.copy() if hasattr(table, "copy") else table
                return table
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"benchmark regime table unavailable: {exc}")
                return None

    def _summary(
        self, candidates: list[Any], samples: list[Any], warnings: list[str]
    ) -> dict[str, Any]:
        accepted = [c for c in candidates if c.validation_passed]
        confirmation = [c for c in candidates if c.metrics.get("confirmation_recommended")]
        status_counts: dict[str, int] = {}
        for candidate in candidates:
            status = str(
                candidate.metrics.get(
                    "promotion_status", "lab" if candidate.validation_passed else "rejected"
                )
            )
            status_counts[status] = status_counts.get(status, 0) + 1
        top = sorted(candidates, key=lambda c: c.score, reverse=True)[
            : self.settings.discovery_report_top_n
        ]  # type: ignore[union-attr]
        confirmation_top = sorted(
            confirmation,
            key=lambda c: float(c.metrics.get("confirmation_priority_score", 0.0)),
            reverse=True,
        )[: self.settings.discovery_report_top_n]  # type: ignore[union-attr]
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "windows_sampled": len(samples),
            "clusters_evaluated": len(candidates),
            "accepted_patterns": len(accepted),
            "rejected_patterns": len(candidates) - len(accepted),
            "confirmation_candidates": len(confirmation),
            "status_counts": status_counts,
            "rr_levels": self.settings.discovery_rr_level_list,  # type: ignore[union-attr]
            "safety": {
                "live_trading_enabled": self.settings.live_trading_enabled,  # type: ignore[union-attr]
                "trading_mode": self.settings.trading_mode,  # type: ignore[union-attr]
                "ibkr_readonly": self.settings.ibkr_readonly,  # type: ignore[union-attr]
            },
            "token_policy": {
                "raw_windows_sent_to_llm": 0,
                "llm_review_input": "compact_digest_only",
                "reason": "Discovery is local/vectorized; API supervisor only needs top cluster metrics and examples.",
            },
            "top_patterns": [self._candidate_digest(c) for c in top],
            "confirmation_queue": [self._candidate_digest(c) for c in confirmation_top],
            "warnings": warnings[:50],
        }

    @staticmethod
    def _candidate_digest(candidate: Any) -> dict[str, Any]:
        metrics = candidate.metrics
        return {
            "name": candidate.name,
            "pattern_key": candidate.pattern_key,
            "status": metrics.get(
                "promotion_status", "lab" if candidate.validation_passed else "rejected"
            ),
            "side": candidate.side,
            "window_size": candidate.window_size,
            "sample_count": candidate.sample_count,
            "symbol_count": candidate.symbol_count,
            "year_count": candidate.year_count,
            "score": candidate.score,
            "lab_priority_score": metrics.get("lab_priority_score", candidate.score),
            "promotion_score": metrics.get("promotion_score"),
            "score_input_scope": metrics.get("score_input_scope", {}),
            "selection_split": metrics.get("selection_split", {}),
            "fit_scope": metrics.get("fit_scope", {}),
            "train_metrics": metrics.get("train_metrics", {}),
            "out_of_sample_metrics": metrics.get("out_of_sample_metrics", {}),
            "walk_forward_metrics": metrics.get("walk_forward_metrics", {}),
            "descriptive_metric_policy": metrics.get("descriptive_metric_policy", {}),
            "descriptive_all_expectancy_r": metrics.get("descriptive_all_expectancy_r"),
            "descriptive_all_profit_factor": metrics.get("descriptive_all_profit_factor"),
            "descriptive_all_win_rate": metrics.get("descriptive_all_win_rate"),
            "descriptive_all_reward_risk_estimate": metrics.get(
                "descriptive_all_reward_risk_estimate"
            ),
            "expectancy_r": metrics.get("expectancy_r"),
            "profit_factor": metrics.get("profit_factor"),
            "win_rate": metrics.get("win_rate"),
            "best_rr": metrics.get("best_rr"),
            "best_expectancy_r": metrics.get("best_expectancy_r"),
            "best_profit_factor": metrics.get("best_profit_factor"),
            "best_win_rate": metrics.get("best_win_rate"),
            "best_max_drawdown_r": metrics.get("best_max_drawdown_r"),
            "avg_execution_cost_r": metrics.get("avg_execution_cost_r"),
            "avg_bars_to_target": metrics.get("avg_bars_to_target"),
            "avg_bars_to_stop": metrics.get("avg_bars_to_stop"),
            "triple_barrier_labels": metrics.get("triple_barrier_labels", {}),
            "mfe_before_mae_rate": metrics.get("mfe_before_mae_rate"),
            "avg_gap_adverse_r": metrics.get("avg_gap_adverse_r"),
            "strong_close_without_target_rate": metrics.get("strong_close_without_target_rate"),
            "speed_label_counts": metrics.get("speed_label_counts", {}),
            "fast_target_rate": metrics.get("fast_target_rate"),
            "slow_target_rate": metrics.get("slow_target_rate"),
            "timeout_rate": metrics.get("timeout_rate"),
            "avg_fill_probability": metrics.get("avg_fill_probability"),
            "p25_max_size_usd": metrics.get("p25_max_size_usd"),
            "median_max_size_usd": metrics.get("median_max_size_usd"),
            "avg_spread_proxy_pct": metrics.get("avg_spread_proxy_pct"),
            "avg_slippage_proxy_pct": metrics.get("avg_slippage_proxy_pct"),
            "avg_entry_gap_penalty_pct": metrics.get("avg_entry_gap_penalty_pct"),
            "avg_short_borrow_proxy_pct": metrics.get("avg_short_borrow_proxy_pct"),
            "preferred_rr_passed": metrics.get("preferred_rr_passed"),
            "premium_rr_passed": metrics.get("premium_rr_passed"),
            "promotion_reason": metrics.get("promotion_reason"),
            "rr_metrics": metrics.get("rr_metrics"),
            "hit_4r_rate": metrics.get("hit_4r_rate"),
            "reward_risk_estimate": metrics.get("reward_risk_estimate"),
            "stability_score": metrics.get("stability_score"),
            "null_expectancy_r": metrics.get("null_expectancy_r"),
            "expectancy_lift_r": metrics.get("expectancy_lift_r"),
            "null_p_value": metrics.get("null_p_value"),
            "adjusted_p_value": metrics.get("adjusted_p_value"),
            "wrc_p_value": metrics.get("wrc_p_value"),
            "spa_p_value": metrics.get("spa_p_value"),
            "reality_check_method": metrics.get("reality_check_method"),
            "reality_check_formal_test": metrics.get("reality_check_formal_test", False),
            "bootstrap_reality_proxy": metrics.get("bootstrap_reality_proxy", {}),
            "probabilistic_sharpe": metrics.get("probabilistic_sharpe"),
            "deflated_sharpe": metrics.get("deflated_sharpe"),
            "deflated_sharpe_probability": metrics.get("deflated_sharpe_probability"),
            "edge_decay_parameter_score": metrics.get("edge_decay_parameter_score"),
            "edge_decay_passed": metrics.get("edge_decay_passed"),
            "purged_cv_fold_count": metrics.get("purged_cv_fold_count", 0),
            "purged_cv_positive_rate": metrics.get("purged_cv_positive_rate", 0.0),
            "purged_cv_avg_expectancy_r": metrics.get("purged_cv_avg_expectancy_r", 0.0),
            "purged_cv_min_expectancy_r": metrics.get("purged_cv_min_expectancy_r", 0.0),
            "multiple_testing_trials": metrics.get("multiple_testing_trials"),
            "quant_validation": metrics.get("quant_validation", {}),
            "effective_sample_count": metrics.get("effective_sample_count"),
            "unique_event_count": metrics.get("unique_event_count"),
            "fdr_q": metrics.get("fdr_q"),
            "fdr_passed": metrics.get("fdr_passed"),
            "fdr_cutoff_p": metrics.get("fdr_cutoff_p"),
            "fdr_test_count": metrics.get("fdr_test_count"),
            "dsr_family": metrics.get("dsr_family"),
            "dsr_family_n_trials": metrics.get("dsr_family_n_trials"),
            "dsr_family_sr_star": metrics.get("dsr_family_sr_star"),
            "match_tau_similarity": metrics.get("match_tau_similarity"),
            "match_tau_percentile": metrics.get("match_tau_percentile"),
            "statistical_edge_passed": metrics.get("statistical_edge_passed"),
            "null_method": metrics.get("null_method"),
            "null_strata_count": metrics.get("null_strata_count"),
            "expectancy_ci_low": metrics.get("expectancy_ci_low"),
            "expectancy_ci_high": metrics.get("expectancy_ci_high"),
            "profit_factor_ci_low": metrics.get("profit_factor_ci_low"),
            "overfit_score": metrics.get("overfit_score"),
            "cost_stress": metrics.get("cost_stress", {}),
            "cost_stress_passed": metrics.get("cost_stress_passed"),
            "confirmation_recommended": metrics.get("confirmation_recommended", False),
            "confirmation_status": metrics.get("confirmation_status", ""),
            "confirmation_priority_score": metrics.get("confirmation_priority_score", 0.0),
            "confirmation_reason": metrics.get("confirmation_reason", ""),
            "confirmation_next_action": metrics.get("confirmation_next_action", ""),
            "registry_deduped": metrics.get("registry_deduped", False),
            "registry_similarity": metrics.get("registry_similarity", 0.0),
            "registry_canonical_pattern_key": metrics.get("registry_canonical_pattern_key"),
            "pattern_family_key": metrics.get("pattern_family_key"),
            "canonical_pattern_key": metrics.get("canonical_pattern_key"),
            "variant_key": metrics.get("variant_key"),
            "variant_count": metrics.get("variant_count"),
            "drift_status": metrics.get("drift_status"),
            "drift_score": metrics.get("drift_score"),
            "novelty_score": metrics.get("novelty_score"),
            "diversity_bucket": metrics.get("diversity_bucket"),
            "diversity_quota_rank": metrics.get("diversity_quota_rank"),
            "expected_information_gain": metrics.get("expected_information_gain"),
            "registry_novelty_score": metrics.get("registry_novelty_score"),
            "registry_expected_information_gain": metrics.get("registry_expected_information_gain"),
            "human_rule": metrics.get("human_rule", {}),
            "regime_profile": metrics.get("regime_profile", {}),
            "operational_trigger": metrics.get("operational_trigger", {}),
            "event_ledger_count": metrics.get("event_ledger_count", 0),
            "event_ledger_path": metrics.get("event_ledger_path"),
            "event_ledger_sha256": metrics.get("event_ledger_sha256"),
            "event_ledger_compressed_bytes": metrics.get("event_ledger_compressed_bytes"),
            "event_ledger_uncompressed_bytes": metrics.get("event_ledger_uncompressed_bytes"),
            "foundation_teacher": metrics.get("foundation_teacher", {}),
            "market_replay": metrics.get("market_replay", {}),
            "causal_invariance": metrics.get("causal_invariance", {}),
            "adversarial_challenge": metrics.get("adversarial_challenge", {}),
            "research_hypothesis": metrics.get("research_hypothesis", {}),
            "research_hypothesis_package": metrics.get("research_hypothesis_package", {}),
            "nested_discovery_replay": metrics.get("nested_discovery_replay", {}),
            "global_experiment_registry": metrics.get("global_experiment_registry", {}),
            "research_memory": metrics.get("research_memory", {}),
            "active_learning": metrics.get("active_learning", {}),
            "pattern_lifecycle": metrics.get("pattern_lifecycle", {}),
            "research_director": metrics.get("research_director", {}),
            "research_committee": metrics.get("research_committee_compact", {}),
            "research_paper_report_path": metrics.get("research_paper_report_path"),
            "walk_forward_fold_count": metrics.get("walk_forward_fold_count", 0),
            "walk_forward_positive_fold_rate": metrics.get("walk_forward_positive_fold_rate", 0.0),
            "walk_forward_avg_expectancy_r": metrics.get("walk_forward_avg_expectancy_r", 0.0),
            "walk_forward_min_expectancy_r": metrics.get("walk_forward_min_expectancy_r", 0.0),
            "walk_forward_folds": metrics.get("walk_forward_folds", []),
            "out_of_sample_expectancy_r": metrics.get("out_of_sample_expectancy_r"),
            "out_of_sample_profit_factor": metrics.get("out_of_sample_profit_factor"),
            "out_of_sample_win_rate": metrics.get("out_of_sample_win_rate"),
            "out_of_sample_max_drawdown_r": metrics.get("out_of_sample_max_drawdown_r"),
            "validation_reasons": candidate.validation_reasons,
            "representative_examples": [
                {
                    "symbol": e.get("symbol"),
                    "window_end": e.get("window_end"),
                    "kind": e.get("kind"),
                    "outcome_r": e.get("outcome_r"),
                    "mfe_r": e.get("mfe_r"),
                    "mae_r": e.get("mae_r"),
                    "triple_barrier_label": e.get("triple_barrier_label"),
                    "speed_label": e.get("speed_label"),
                    "time_to_target": e.get("time_to_target"),
                    "time_to_stop": e.get("time_to_stop"),
                }
                for e in candidate.examples[:5]
            ],
        }

    def _write_event_ledgers(self, run_id: int, candidates: list[Any]) -> int:
        settings = self.settings
        assert settings is not None
        ledger_dir = settings.reports_path / "research" / "event_ledgers" / f"run_{run_id}"
        written = 0
        for candidate in candidates:
            ledger = candidate.metrics.get("event_ledger")
            if not isinstance(ledger, list):
                continue
            if written == 0:
                ledger_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "run_id": run_id,
                "pattern_key": candidate.pattern_key,
                "name": candidate.name,
                "side": candidate.side,
                "timeframe": candidate.timeframe,
                "window_size": candidate.window_size,
                "cluster_id": candidate.cluster_id,
                "event_count": len(ledger),
                "events": ledger,
            }
            raw = self._json_bytes(payload, sort_keys=True)
            digest = hashlib.sha256(raw).hexdigest()
            compressed = gzip.compress(raw, compresslevel=1, mtime=0)
            path = ledger_dir / f"{self._safe_artifact_stem(candidate.pattern_key)}.json.gz"
            self._atomic_write_bytes(path, compressed)
            candidate.metrics["event_ledger_path"] = str(path)
            candidate.metrics["event_ledger_sha256"] = digest
            candidate.metrics["event_ledger_count"] = len(ledger)
            candidate.metrics["event_ledger_compressed_bytes"] = len(compressed)
            candidate.metrics["event_ledger_uncompressed_bytes"] = len(raw)
            candidate.metrics["event_ledger_persisted"] = True
            candidate.metrics["event_ledger_preview"] = ledger[:5]
            candidate.metrics.pop("event_ledger", None)
            written += 1
        return written

    @staticmethod
    def _safe_artifact_stem(value: object) -> str:
        stem = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in str(value))
        return stem.strip("._")[:120] or "pattern"

    def _write_report(
        self,
        run_id: int,
        params: dict[str, Any],
        summary: dict[str, Any],
        candidates: list[Any],
    ) -> Path | None:
        settings = self.settings
        assert settings is not None
        reports_dir = settings.reports_path / "research"
        reports_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_path = reports_dir / f"discovery_run_{run_id}_{ts}.json"
        md_path = reports_dir / f"discovery_run_{run_id}_{ts}.md"
        report_artifact_mode = self._report_artifact_mode()
        write_markdown = report_artifact_mode != "json_only"
        summary["report_artifacts"] = {
            "mode": report_artifact_mode,
            "json_path": str(json_path),
            "markdown_path": str(md_path) if write_markdown else None,
            "markdown_written": write_markdown,
        }
        patterns = [self._candidate_digest(c) for c in candidates]
        payload = {
            "run_id": run_id,
            "params": params,
            "summary": summary,
            "patterns": patterns,
            "top_by_expectancy": sorted(
                patterns,
                key=lambda p: float(p.get("best_expectancy_r") or 0.0),
                reverse=True,
            )[:10],
            "top_by_stability": sorted(
                patterns,
                key=lambda p: float(p.get("stability_score") or 0.0),
                reverse=True,
            )[:10],
        }
        volatile_keys = DEFAULT_VOLATILE_KEYS
        if isinstance(summary.get("phase_timings"), dict) or isinstance(
            summary.get("phase_counts"), dict
        ):
            volatile_keys = DEFAULT_VOLATILE_KEYS | _PHASE_TIMING_VOLATILE_KEYS
        volatile_keys = volatile_keys | _REPORT_ARTIFACT_VOLATILE_KEYS
        payload["determinism"] = {
            "algo": CONTENT_HASH_ALGO,
            "content_hash": content_hash(payload, exclude_keys=volatile_keys),
            "excluded_keys": sorted(volatile_keys),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._atomic_write_bytes(json_path, self._json_bytes(payload, sort_keys=True))
        if write_markdown:
            self._atomic_write_text(md_path, self._markdown_report(run_id, params, summary))
        return json_path

    @staticmethod
    def _report_artifact_mode() -> str:
        value = os.getenv(_BENCHMARK_REPORT_MODE_ENV, "").strip().lower().replace("-", "_")
        if value in _BENCHMARK_JSON_ONLY_REPORT_VALUES:
            return "json_only"
        return "full"

    @staticmethod
    def _json_bytes(payload: Any, *, sort_keys: bool = False) -> bytes:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=sort_keys,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")

    @staticmethod
    def _atomic_write_text(path: Path, text: str) -> None:
        PatternDiscoveryLabAgent._atomic_write_bytes(path, text.encode("utf-8"))

    @staticmethod
    def _atomic_write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
        try:
            temp_path.write_bytes(data)
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def _markdown_report(run_id: int, params: dict[str, Any], summary: dict[str, Any]) -> str:
        lines = [
            f"# Tradeo Research Lab · Discovery Run {run_id}",
            "",
            "## Resumen",
            f"- Ventanas analizadas: {summary['windows_sampled']}",
            f"- Clusters evaluados: {summary['clusters_evaluated']}",
            f"- Patrones LAB aceptados: {summary['accepted_patterns']}",
            f"- Patrones rechazados: {summary['rejected_patterns']}",
            f"- Candidatos para confirmación: {summary.get('confirmation_candidates', 0)}",
            f"- Estados: {summary.get('status_counts', {})}",
            f"- R:R evaluados: {summary.get('rr_levels', [])}",
            f"- Seguridad: {summary.get('safety', {})}",
            "",
            "## Timings",
            "```json",
            json.dumps(
                {
                    "phase_timings": summary.get("phase_timings", {}),
                    "phase_counts": summary.get("phase_counts", {}),
                    "phase_diagnostics": summary.get("phase_diagnostics", {}),
                },
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            "```",
            "",
            "## Política de tokens",
            "El laboratorio no envía ventanas OHLCV crudas a ningún LLM. Solo exporta este digest compacto para revisión.",
            "",
            "## Research Director",
            "```json",
            json.dumps(
                summary.get("research_director", {}), indent=2, ensure_ascii=False, default=str
            ),
            "```",
            "",
            "## Parámetros",
            "```json",
            json.dumps(params, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Top patrones",
        ]
        for pattern in summary.get("top_patterns", []):
            human_rule = pattern.get("human_rule")
            human_rule_text = human_rule.get("rule") if isinstance(human_rule, dict) else human_rule
            lines.extend(
                [
                    f"### {pattern['name']}",
                    f"- Estado: {pattern['status']}",
                    f"- Lado: {pattern['side']} · ventana: {pattern['window_size']}",
                    (
                        "- Muestras/símbolos/años: "
                        f"{pattern['sample_count']} / {pattern['symbol_count']} / {pattern['year_count']}"
                    ),
                    f"- Score: {pattern['score']}",
                    (
                        f"- Best R:R: {pattern.get('best_rr')} · "
                        f"Expectancy: {pattern.get('best_expectancy_r')}R · "
                        f"PF: {pattern.get('best_profit_factor')} · "
                        f"Win rate: {pattern.get('best_win_rate')}"
                    ),
                    (
                        f"- Labels: {pattern.get('triple_barrier_labels')} · "
                        f"target bars {pattern.get('avg_bars_to_target')} · "
                        f"stop bars {pattern.get('avg_bars_to_stop')} · "
                        f"MFE antes MAE {pattern.get('mfe_before_mae_rate')}"
                    ),
                    (
                        f"- Coste/fill: coste {pattern.get('avg_execution_cost_r')}R · "
                        f"fill {pattern.get('avg_fill_probability')} · "
                        f"p25 max size ${pattern.get('p25_max_size_usd')} · "
                        f"spread {pattern.get('avg_spread_proxy_pct')} · "
                        f"slippage {pattern.get('avg_slippage_proxy_pct')}"
                    ),
                    f"- Trigger operativo: {pattern.get('operational_trigger')}",
                    (
                        "- Walk-forward: "
                        f"{pattern.get('walk_forward_positive_fold_rate')} positive fold rate · "
                        f"avg {pattern.get('walk_forward_avg_expectancy_r')}R · "
                        f"min {pattern.get('walk_forward_min_expectancy_r')}R"
                    ),
                    (
                        f"- Purged CV: {pattern.get('purged_cv_positive_rate')} positive · "
                        f"avg {pattern.get('purged_cv_avg_expectancy_r')}R · "
                        f"min {pattern.get('purged_cv_min_expectancy_r')}R"
                    ),
                    (
                        f"- Null/CI: {pattern.get('null_method')} · "
                        f"p_adj {pattern.get('adjusted_p_value')} · "
                        "bootstrap_reality_proxy "
                        f"wrc_like {pattern.get('wrc_p_value')} · spa_like {pattern.get('spa_p_value')} · "
                        f"CI {pattern.get('expectancy_ci_low')}..{pattern.get('expectancy_ci_high')}R · "
                        f"overfit {pattern.get('overfit_score')}"
                    ),
                    (
                        f"- Sharpe/decay: PSR {pattern.get('probabilistic_sharpe')} · "
                        f"DSR {pattern.get('deflated_sharpe_probability')} · "
                        f"edge decay {pattern.get('edge_decay_parameter_score')}"
                    ),
                    (
                        f"- Novelty: score {pattern.get('novelty_score')} · "
                        f"EIG {pattern.get('expected_information_gain')} · "
                        f"bucket {pattern.get('diversity_bucket')} · "
                        f"rank {pattern.get('diversity_quota_rank')}"
                    ),
                    f"- Regla humana: {human_rule_text}",
                    f"- Hipótesis: {(pattern.get('research_hypothesis') or {}).get('thesis') if isinstance(pattern.get('research_hypothesis'), dict) else None}",
                    f"- Edge claim: {(pattern.get('research_hypothesis') or {}).get('edge_claim') if isinstance(pattern.get('research_hypothesis'), dict) else 'NO_DEMOSTRADO'}",
                    f"- Nested replay: {pattern.get('nested_discovery_replay')}",
                    f"- Registry global: {pattern.get('global_experiment_registry')}",
                    f"- Market replay: {pattern.get('market_replay')}",
                    f"- Adversarial challenge: {pattern.get('adversarial_challenge')}",
                    f"- Invariancia causal: {pattern.get('causal_invariance')}",
                    f"- Lifecycle: {pattern.get('pattern_lifecycle')}",
                    f"- Active learning: {pattern.get('active_learning')}",
                    f"- Paper report: {pattern.get('research_paper_report_path')}",
                    f"- Cost stress passed: {pattern.get('cost_stress_passed')} · {pattern.get('cost_stress')}",
                    (
                        f"- Ledger: {pattern.get('event_ledger_count')} eventos · "
                        f"{pattern.get('event_ledger_path')} · sha256 {pattern.get('event_ledger_sha256')}"
                    ),
                    (
                        f"- R:R estimado: {pattern['reward_risk_estimate']} · "
                        f"Hit 4R: {pattern['hit_4r_rate']} · "
                        f"DD: {pattern.get('best_max_drawdown_r')}R"
                    ),
                    (
                        f"- OOS expectancy: {pattern['out_of_sample_expectancy_r']}R · "
                        f"estabilidad: {pattern['stability_score']}"
                    ),
                    f"- Razones/avisos: {', '.join(pattern.get('validation_reasons') or ['sin incidencias'])}",
                    "",
                ]
            )
        if summary.get("confirmation_queue"):
            lines.extend(["", "## Cola de confirmación"])
            for pattern in summary.get("confirmation_queue", []):
                lines.extend(
                    [
                        f"### {pattern['name']}",
                        f"- Prioridad: {pattern.get('confirmation_priority_score')}",
                        f"- Motivo: {pattern.get('confirmation_reason')}",
                        f"- Siguiente acción: {pattern.get('confirmation_next_action')}",
                        f"- Best R:R: {pattern.get('best_rr')} · Expectancy: {pattern.get('best_expectancy_r')}R · PF: {pattern.get('best_profit_factor')}",
                        "",
                    ]
                )
        return "\n".join(lines)
