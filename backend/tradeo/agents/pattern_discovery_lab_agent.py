from __future__ import annotations

import gzip
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, DiscoveryRun
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.autonomous_research_director import ResearchDirector as PersistentResearchDirector
from tradeo.research.determinism import CONTENT_HASH_ALGO, DEFAULT_VOLATILE_KEYS, content_hash
from tradeo.research.global_experiment_registry import GlobalExperimentRegistry
from tradeo.research.novel_pattern_registry import NovelPatternRegistry
from tradeo.research.quant_validation import (
    benjamini_hochberg,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
)
from tradeo.research.research_director import ResearchDirector as CandidateResearchDirector
from tradeo.research.validation_gate import ValidationGate
from tradeo.research.window_sampler import WindowSampler
from tradeo.schemas import DiscoveryRunRequest, DiscoveryRunResponse
from tradeo.services.data_provider import MarketDataProvider, pick_symbols
from tradeo.services.market_regime import MarketRegimeService
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.universe_snapshot import UniverseSnapshotService


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
        started = time.perf_counter()
        warnings: list[str] = []
        params = self._resolve_params(request)
        run = DiscoveryRun(status="running", params_json=params)
        db.add(run)
        db.commit()
        db.refresh(run)
        logger.info("pattern discovery run {} started with params {}", run.id, params)

        try:
            symbols = self._resolve_symbols(request, params)
            universe_snapshot = self._build_universe_snapshot(warnings)
            samples = []
            sampler = WindowSampler(target_r=settings.discovery_min_reward_risk)
            benchmark_frames = self._benchmark_frames(params, warnings)
            benchmark_regime_table = self._benchmark_regime_table(params, warnings)
            for symbol in symbols:
                if len(samples) >= params["max_total_windows"]:
                    break
                try:
                    df = self.provider.fetch_ohlcv(symbol, period=params["period"], interval=params["interval"])
                    symbol_samples = sampler.sample(
                        symbol=symbol,
                        df=df,
                        timeframe=params["interval"],
                        window_sizes=params["window_sizes"],
                        forward_bars=params["forward_bars"],
                        stride=params["stride"],
                        max_windows_per_symbol=params["max_windows_per_symbol"],
                        benchmark_frames=benchmark_frames,
                    )
                    remaining = params["max_total_windows"] - len(samples)
                    samples.extend(symbol_samples[:remaining])
                except Exception as exc:  # noqa: BLE001
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
                min_samples=settings.discovery_min_samples,
                walk_forward_folds=settings.discovery_walk_forward_folds,
                walk_forward_embargo_samples=settings.discovery_walk_forward_embargo_samples,
                cost_stress_multipliers=settings.discovery_cost_stress_multiplier_list,
                required_cost_stress_multiplier=settings.discovery_required_cost_stress_multiplier,
                event_ledger_limit=0,
                match_tau_percentile=settings.discovery_match_tau_percentile,
                benchmark_regime_table=benchmark_regime_table,
                conformal_alpha=settings.discovery_match_conformal_alpha,
                prototype_medoid_count=settings.discovery_match_prototype_medoids,
                prototype_knn_k=settings.discovery_match_knn_k,
            )
            raw_candidates = engine.discover(samples)
            data_manifest = self._data_manifest(run.id, symbols, warnings)
            for candidate in raw_candidates:
                candidate.metrics["data_manifest"] = {
                    "path": data_manifest.get("path"),
                    "manifest_hash": data_manifest.get("manifest_hash"),
                    "entry_count": len((data_manifest.get("entries") or {})),
                    "artifact_format": data_manifest.get("artifact_format"),
                }
                candidate.metrics["universe_snapshot"] = universe_snapshot
                candidate.metrics["universe_point_in_time"] = bool(
                    universe_snapshot.get("point_in_time", settings.universe_point_in_time_available)
                )
                candidate.metrics["survivorship_biased"] = not bool(candidate.metrics["universe_point_in_time"])
            self._apply_run_level_inference(raw_candidates)
            candidates = ValidationGate(settings).evaluate_many(raw_candidates)
            accepted = [c for c in candidates if c.validation_passed]
            rejected = [c for c in candidates if not c.validation_passed]
            ledger_artifacts = self._write_event_ledgers(run.id, candidates)
            global_registry = GlobalExperimentRegistry(
                settings.reports_path / "research" / "global_experiment_registry.json"
            ).register(candidates, run_id=run.id, params=params)
            candidate_director_summary: dict[str, Any] = {}
            if settings.research_director_enabled:
                try:
                    logger.info("Research Director: enriqueciendo candidatos antes del registry")
                    candidate_director_summary = CandidateResearchDirector(settings=settings).run(
                        run_id=run.id,
                        candidates=candidates,
                        samples=samples,
                        params=params,
                    )
                except Exception as exc:  # noqa: BLE001
                    msg = f"CandidateResearchDirector failed: {exc}"
                    logger.exception(msg)
                    warnings.append(msg)
            stored = NovelPatternRegistry().store_candidates(
                db,
                candidates,
                run_id=run.id,
                store_rejected=params["store_rejected"],
            )
            director_result: dict[str, Any] | None = None
            if settings.research_director_enabled:
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
            duration = round(time.perf_counter() - started, 3)
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
            if director_result is not None:
                summary["research_director"]["db_director"] = {
                    "patterns_reviewed": director_result.get("patterns_reviewed", 0),
                    "hypotheses_created": director_result.get("hypotheses_created", 0),
                    "director_state": director_result.get("director_state", {}),
                    "artifacts": director_result.get("artifacts", {}),
                }
            report_path = self._write_report(run.id, params, summary, candidates)
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
                        "event_ledgers": ledger_artifacts,
                        "data_manifest": summary.get("data_manifest", {}),
                        "universe_snapshot": universe_snapshot,
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
                top_patterns=summary["top_patterns"],
                warnings=warnings[:50],
            )
        except Exception as exc:  # noqa: BLE001
            duration = round(time.perf_counter() - started, 3)
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.duration_seconds = duration
            run.summary_json = {"error": str(exc), "warnings": warnings}
            db.add(run)
            db.add(
                AuditLog(
                    actor="PatternDiscoveryLabAgent",
                    action="discovery_run_failed",
                    entity_type="discovery_run",
                    entity_id=str(run.id),
                    details_json={"error": str(exc), "warnings": warnings[:50]},
                )
            )
            db.commit()
            raise

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
            sr = float(quant.get("sharpe_per_trade", candidate.metrics.get("trade_sharpe", 0.0)) or 0.0)
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
        return {
            "limit": request.limit or s.discovery_limit_default,
            "period": request.period or s.discovery_period,
            "interval": request.interval or s.discovery_interval,
            "window_sizes": request.window_sizes or s.discovery_window_size_list,
            "forward_bars": request.forward_bars or s.discovery_forward_bar_list,
            "stride": max(1, request.stride or s.discovery_stride),
            "max_total_windows": max(100, max_total_windows),
            "max_windows_per_symbol": max(50, request.max_windows_per_symbol or s.discovery_max_windows_per_symbol),
            "min_cluster_size": max(20, request.min_cluster_size or s.discovery_min_cluster_size),
            "max_clusters_per_window": max(2, min(request.max_clusters_per_window or s.discovery_max_clusters_per_window, 40)),
            "store_rejected": s.discovery_store_rejected if request.store_rejected is None else request.store_rejected,
            "rr_levels": s.discovery_rr_level_list,
            "min_reward_risk": s.discovery_min_reward_risk,
            "candidate_reward_risk": s.discovery_candidate_reward_risk,
            "premium_reward_risk": s.discovery_premium_reward_risk,
            "max_drawdown_r": s.discovery_max_drawdown_r,
            "walk_forward_folds": s.discovery_walk_forward_folds,
            "walk_forward_embargo_samples": s.discovery_walk_forward_embargo_samples,
            "cost_stress_multipliers": s.discovery_cost_stress_multiplier_list,
            "required_cost_stress_multiplier": s.discovery_required_cost_stress_multiplier,
        }

    @staticmethod
    def _resolve_symbols(request: DiscoveryRunRequest, params: dict[str, Any]) -> list[str]:
        if request.symbols:
            return [s.upper().strip() for s in request.symbols if s.strip()]
        return pick_symbols(limit=params["limit"])

    def _build_universe_snapshot(self, warnings: list[str]) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        if not settings.universe_snapshot_monthly:
            return {
                "enabled": False,
                "point_in_time": settings.universe_point_in_time_available,
                "survivorship_biased": not settings.universe_point_in_time_available,
            }
        try:
            return UniverseSnapshotService(settings).build_monthly_snapshot()
        except Exception as exc:  # noqa: BLE001
            msg = f"UniverseSnapshotService failed: {exc}"
            logger.warning(msg)
            warnings.append(msg)
            return {
                "enabled": True,
                "error": str(exc),
                "point_in_time": settings.universe_point_in_time_available,
                "survivorship_biased": not settings.universe_point_in_time_available,
            }

    def _data_manifest(self, run_id: int, symbols: list[str], warnings: list[str]) -> dict[str, Any]:
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
            payload = provider_manifest(symbols)
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
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        payload = dict(payload)
        payload["path"] = str(path)
        return payload

    def _benchmark_frames(self, params: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
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
        return frames

    def _benchmark_regime_table(self, params: dict[str, Any], warnings: list[str]) -> Any:
        assert self.provider is not None
        try:
            return MarketRegimeService(provider=self.provider, settings=self.settings).history_table(
                period=str(params.get("period") or "")
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"benchmark regime table unavailable: {exc}")
            return None

    def _summary(self, candidates: list[Any], samples: list[Any], warnings: list[str]) -> dict[str, Any]:
        accepted = [c for c in candidates if c.validation_passed]
        confirmation = [c for c in candidates if c.metrics.get("confirmation_recommended")]
        status_counts: dict[str, int] = {}
        for candidate in candidates:
            status = str(candidate.metrics.get("promotion_status", "lab" if candidate.validation_passed else "rejected"))
            status_counts[status] = status_counts.get(status, 0) + 1
        top = sorted(candidates, key=lambda c: c.score, reverse=True)[: self.settings.discovery_report_top_n]  # type: ignore[union-attr]
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
            "status": metrics.get("promotion_status", "lab" if candidate.validation_passed else "rejected"),
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
            "descriptive_all_reward_risk_estimate": metrics.get("descriptive_all_reward_risk_estimate"),
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
            raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
            digest = hashlib.sha256(raw).hexdigest()
            compressed = gzip.compress(raw, compresslevel=9, mtime=0)
            path = ledger_dir / f"{self._safe_artifact_stem(candidate.pattern_key)}.json.gz"
            path.write_bytes(compressed)
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
        payload = {
            "run_id": run_id,
            "params": params,
            "summary": summary,
            "patterns": [self._candidate_digest(c) for c in candidates],
            "top_by_expectancy": sorted(
                [self._candidate_digest(c) for c in candidates],
                key=lambda p: float(p.get("best_expectancy_r") or 0.0),
                reverse=True,
            )[:10],
            "top_by_stability": sorted(
                [self._candidate_digest(c) for c in candidates],
                key=lambda p: float(p.get("stability_score") or 0.0),
                reverse=True,
            )[:10],
        }
        payload["determinism"] = {
            "algo": CONTENT_HASH_ALGO,
            "content_hash": content_hash(payload),
            "excluded_keys": sorted(DEFAULT_VOLATILE_KEYS),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str), encoding="utf-8"
        )
        md_path.write_text(self._markdown_report(run_id, params, summary), encoding="utf-8")
        return json_path

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
            "## Política de tokens",
            "El laboratorio no envía ventanas OHLCV crudas a ningún LLM. Solo exporta este digest compacto para revisión.",
            "",
            "## Research Director",
            "```json",
            json.dumps(summary.get("research_director", {}), indent=2, ensure_ascii=False, default=str),
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
            human_rule_text = (
                human_rule.get("rule")
                if isinstance(human_rule, dict)
                else human_rule
            )
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
