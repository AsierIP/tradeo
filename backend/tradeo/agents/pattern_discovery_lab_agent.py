from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, DiscoveryRun
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.novel_pattern_registry import NovelPatternRegistry
from tradeo.research.validation_gate import ValidationGate
from tradeo.research.window_sampler import WindowSampler
from tradeo.schemas import DiscoveryRunRequest, DiscoveryRunResponse
from tradeo.services.data_provider import MarketDataProvider, pick_symbols
from tradeo.services.provider_factory import get_market_data_provider


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
            samples = []
            sampler = WindowSampler(target_r=settings.discovery_min_reward_risk)
            benchmark_frames = self._benchmark_frames(params, warnings)
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
            )
            raw_candidates = engine.discover(samples)
            candidates = ValidationGate(settings).evaluate_many(raw_candidates)
            accepted = [c for c in candidates if c.validation_passed]
            rejected = [c for c in candidates if not c.validation_passed]
            stored = NovelPatternRegistry().store_candidates(
                db,
                candidates,
                run_id=run.id,
                store_rejected=params["store_rejected"],
            )
            duration = round(time.perf_counter() - started, 3)
            summary = self._summary(candidates, samples, warnings)
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
            "expectancy_r": metrics.get("expectancy_r"),
            "profit_factor": metrics.get("profit_factor"),
            "win_rate": metrics.get("win_rate"),
            "best_rr": metrics.get("best_rr"),
            "best_expectancy_r": metrics.get("best_expectancy_r"),
            "best_profit_factor": metrics.get("best_profit_factor"),
            "best_win_rate": metrics.get("best_win_rate"),
            "best_max_drawdown_r": metrics.get("best_max_drawdown_r"),
            "avg_execution_cost_r": metrics.get("avg_execution_cost_r"),
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
            "multiple_testing_trials": metrics.get("multiple_testing_trials"),
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
            "operational_trigger": metrics.get("operational_trigger", {}),
            "event_ledger_count": metrics.get("event_ledger_count", 0),
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
                }
                for e in candidate.examples[:5]
            ],
        }

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
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
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
            "## Parámetros",
            "```json",
            json.dumps(params, indent=2, ensure_ascii=False),
            "```",
            "",
            "## Top patrones",
        ]
        for pattern in summary.get("top_patterns", []):
            lines.extend(
                [
                    f"### {pattern['name']}",
                    f"- Estado: {pattern['status']}",
                    f"- Lado: {pattern['side']} · ventana: {pattern['window_size']}",
                    f"- Muestras/símbolos/años: {pattern['sample_count']} / {pattern['symbol_count']} / {pattern['year_count']}",
                    f"- Score: {pattern['score']}",
                    f"- Best R:R: {pattern.get('best_rr')} · Expectancy: {pattern.get('best_expectancy_r')}R · PF: {pattern.get('best_profit_factor')} · Win rate: {pattern.get('best_win_rate')}",
                    f"- Coste medio: {pattern.get('avg_execution_cost_r')}R · trigger operativo: {pattern.get('operational_trigger')}",
                    f"- Walk-forward: {pattern.get('walk_forward_positive_fold_rate')} positive fold rate · avg {pattern.get('walk_forward_avg_expectancy_r')}R · min {pattern.get('walk_forward_min_expectancy_r')}R",
                    f"- Null/CI: {pattern.get('null_method')} · p_adj {pattern.get('adjusted_p_value')} · CI {pattern.get('expectancy_ci_low')}..{pattern.get('expectancy_ci_high')}R · overfit {pattern.get('overfit_score')}",
                    f"- Cost stress passed: {pattern.get('cost_stress_passed')} · {pattern.get('cost_stress')}",
                    f"- R:R estimado: {pattern['reward_risk_estimate']} · Hit 4R: {pattern['hit_4r_rate']} · DD: {pattern.get('best_max_drawdown_r')}R",
                    f"- OOS expectancy: {pattern['out_of_sample_expectancy_r']}R · estabilidad: {pattern['stability_score']}",
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
