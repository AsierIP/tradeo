from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Literal

from sqlalchemy.orm import Session, joinedload

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, DiscoveredPattern, Signal, SignalStatus, Trade, TradeStatus
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.schemas import PatternCandidate
from tradeo.services.evidence import (
    EvidenceQuality,
    EvidenceType,
    evidence_metadata_with_stored_columns,
    is_director_review_paper_fill_evidence,
)
from tradeo.services.ibkr_broker import IBKRBroker
from tradeo.services.market_quotes import QuoteSnapshotProvider, capture_signal_spread_snapshot
from tradeo.modules.laboratory.paper_observations import LAB_SHADOW_EXECUTION_MODE, LabPaperObservationService
from tradeo.services.market_session import market_session_status
from tradeo.services.order_outcomes import mark_signal_order_failure
from tradeo.services.opportunity_ranking import rank_entry_matches
from tradeo.modules.fox_hunter.production_manifest import production_manifest_status
from tradeo.services.risk_manager import RiskManager
from tradeo.services.signal_quality import build_entry_quality, build_signal_snapshot

EntryModule = Literal["laboratory", "fox_hunter"]
LAB_NEAR_MISS_VOLUME_REASONS = {"insufficient_volume", "weak_volume_confirmation"}
LAB_NEAR_MISS_HARD_REASONS = {
    "weak_trigger",
    "weak_entry_score",
    "no_operational_trigger",
    "insufficient_history",
    "regime_not_aligned",
    "regime_filter_failed",
    "excessive_extension",
    "overextended",
    "excessive_volatility",
    "volatility_filter_failed",
    "atr_filter_failed",
    "liquidity_filter_failed",
    "thin_liquidity",
    "trigger_not_confirmed",
}
LAB_NEAR_MISS_TOP_RANK_LIMIT = 3
LAB_NEAR_MISS_MIN_ENTRY_SCORE = 0.50
LAB_NEAR_MISS_MIN_RANK_SCORE = 0.45
LAB_NEAR_MISS_HIGH_RANK_SCORE = 0.60


class PatternEntryScannerSafetyError(RuntimeError):
    """Raised when a scanner tries to cross its allowed execution boundary."""


@dataclass(slots=True)
class PatternEntryScanner:
    """Operational scanner for validated Research patterns.

    Research discovers patterns. Laboratory validates them with IB paper fills.
    Fox Hunter only watches production patterns and can route live orders only
    after the existing live_armed gate is explicitly enabled.
    """

    settings: Settings | None = None
    matcher: NovelPatternMatcher | None = None
    quote_provider: QuoteSnapshotProvider | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.matcher = self.matcher or NovelPatternMatcher(settings=self.settings)

    def scan(
        self,
        db: Session,
        *,
        module: EntryModule,
        symbols: list[str] | None = None,
        limit: int | None = None,
        max_patterns: int | None = None,
        max_results: int | None = None,
        similarity_threshold: float | None = None,
        store_signals: bool | None = None,
        execute_orders: bool | None = None,
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        self._validate_module_execution(module, execute_orders=execute_orders)
        resolved = self._resolved_options(
            module,
            limit=limit,
            max_patterns=max_patterns,
            max_results=max_results,
            similarity_threshold=similarity_threshold,
            store_signals=store_signals,
            execute_orders=execute_orders,
        )
        requested_execute_orders = bool(resolved["execute_orders"])
        execution_degrade_reason: str | None = None
        if module == "laboratory" and resolved["execute_orders"]:
            from tradeo.services.system_controls import runtime_kill_switch_active

            if runtime_kill_switch_active(db):
                resolved["execute_orders"] = False
                execution_degrade_reason = "runtime_kill_switch_enabled"
        observation_lifecycle = self._close_lab_observations(db, module)
        session = market_session_status()
        if self._requires_market_hours(module) and not bool(session["regular_session_open"]):
            result = self._market_closed_result(module, resolved, session)
            result.update(
                self._scan_execution_metadata(
                    module,
                    requested_execute_orders=requested_execute_orders,
                    execute_orders=bool(resolved["execute_orders"]),
                    execution_degrade_reason=execution_degrade_reason,
                )
            )
            result["paper_observations_opened"] = 0
            result["paper_observations_closed"] = observation_lifecycle["closed_observations"]
            result["paper_observation_trade_ids"] = []
            result["shadow_no_order_observations_opened"] = 0
            result["shadow_no_order_trade_ids"] = []
            result["paper_observation_lifecycle"] = observation_lifecycle
            from tradeo.services.runtime_status import write_entry_scan_status

            write_entry_scan_status(module, result, settings)
            return result
        assert self.matcher is not None
        match_result = self.matcher.match_current(
            db,
            symbols=symbols,
            limit=resolved["limit"],
            max_patterns=resolved["max_patterns"],
            max_results=resolved["max_results"],
            similarity_threshold=resolved["similarity_threshold"],
            module=module,
            store=True,
        )
        signals_created = 0
        orders_submitted = 0
        skipped_duplicates = 0
        skipped_cooldown = 0
        rejected_by_entry_gate = 0
        rejected_by_entry_quality = 0
        rejected_by_ambiguity = 0
        rejected_by_risk = 0
        rejected_by_production_manifest = 0
        production_manifest_rejection_reason_counts: dict[str, int] = {}
        production_manifest_status_cache: dict[int, dict[str, Any]] = {}
        production_manifest_checked_at = datetime.now(timezone.utc)
        near_miss_shadow_observations_opened = 0
        order_errors: list[dict[str, Any]] = []
        order_skip_reason_counts: dict[str, int] = {}
        signal_ids: list[int] = []
        near_miss_signal_ids: list[int] = []
        trade_ids: list[int] = []
        paper_observation_trade_ids: list[int] = []
        near_miss_trade_ids: list[int] = []
        paper_observations_opened = 0
        shadow_no_order_observations_opened = 0
        shadow_no_order_trade_ids: list[int] = []
        broker_blocked_symbols: set[str] = set()

        all_ranked_matches = rank_entry_matches(
            match_result["matches"],
            settings=settings,
            execution_history=self._execution_history(db, module),
        )
        ranked_matches = self._select_best_variant_per_exposure(all_ranked_matches)

        for match in ranked_matches:
            symbol = str(match["symbol"]).upper()
            if module == "laboratory" and resolved["execute_orders"] and symbol in broker_blocked_symbols:
                skipped_duplicates += 1
                self._count_reason(order_skip_reason_counts, "same_scan_broker_failure")
                self._audit_lab_symbol_broker_cooldown(db, match=match, reason="same_scan_broker_failure")
                continue
            if (
                module == "laboratory"
                and resolved["execute_orders"]
                and self._has_recent_lab_symbol_order_failure(db, symbol)
            ):
                skipped_duplicates += 1
                self._count_reason(order_skip_reason_counts, "recent_symbol_broker_failure")
                self._audit_lab_symbol_broker_cooldown(db, match=match, reason="recent_symbol_broker_failure")
                continue
            production_manifest_check: dict[str, Any] | None = None
            if module == "fox_hunter":
                production_manifest_check = self._fox_match_production_manifest_status(
                    db,
                    match,
                    cache=production_manifest_status_cache,
                    now=production_manifest_checked_at,
                )
            if production_manifest_check is not None and not bool(production_manifest_check["valid"]):
                rejected_by_production_manifest += 1
                reason_code = str(production_manifest_check.get("reason_code") or "unknown")
                self._count_reason(order_skip_reason_counts, f"production_manifest:{reason_code}")
                production_manifest_rejection_reason_counts[reason_code] = (
                    production_manifest_rejection_reason_counts.get(reason_code, 0) + 1
                )
                db.add(
                    AuditLog(
                        actor=module,
                        action="entry_match_rejected_by_production_manifest",
                        entity_type="discovered_pattern_match",
                        entity_id=str(match.get("pattern_id", "")),
                        details_json={
                            "match": match,
                            "reason": reason_code,
                            "production_manifest_status": production_manifest_check,
                        },
                    )
                )
                db.commit()
                continue
            entry_gate = ((match.get("metrics") or {}).get("entry_gate") or {})
            if settings.entry_gate_enabled and not bool(entry_gate.get("passed", False)):
                rejected_by_entry_gate += 1
                gate_reasons = self._entry_gate_reasons(entry_gate)
                self._count_reason(
                    order_skip_reason_counts,
                    f"entry_gate:{gate_reasons[0]}" if gate_reasons else "entry_gate",
                )
                self._audit_entry_gate_rejection(db, module=module, match=match, entry_gate=entry_gate)
                if module == "laboratory" and self._is_lab_near_miss_shadow_candidate(match, entry_gate):
                    opened = self._open_near_miss_shadow_observation(
                        db,
                        match=match,
                        resolved=resolved,
                        session=session,
                    )
                    if opened is not None:
                        signal, observation = opened
                        signals_created += 1
                        signal_ids.append(signal.id)
                        near_miss_signal_ids.append(signal.id)
                        paper_observations_opened += 1
                        near_miss_shadow_observations_opened += 1
                        paper_observation_trade_ids.append(observation.id)
                        near_miss_trade_ids.append(observation.id)
                        continue
                continue
            duplicate_signal = self._duplicate_signal(db, match, module=module)
            if duplicate_signal is not None:
                if (
                    module == "laboratory"
                    and resolved["execute_orders"]
                    and self._can_submit_duplicate_lab_signal(db, duplicate_signal)
                ):
                    try:
                        self._prepare_lab_signal_for_order_submission(duplicate_signal, match)
                        trade = IBKRBroker(settings).submit_signal_bracket(
                            db,
                            duplicate_signal,
                            reason=self._execution_reason(module),
                        )
                        orders_submitted += 1
                        trade_ids.append(trade.id)
                        db.add(
                            AuditLog(
                                actor=module,
                                action="duplicate_entry_signal_order_submitted",
                                entity_type="signal",
                                entity_id=str(duplicate_signal.id),
                                details_json={"match": match, "trade_id": trade.id},
                            )
                        )
                        db.commit()
                    except Exception as exc:  # noqa: BLE001
                        outcome = mark_signal_order_failure(duplicate_signal, str(exc))
                        self._count_reason(order_skip_reason_counts, str(outcome["reason_code"]))
                        order_errors.append(
                            {
                                "signal_id": duplicate_signal.id,
                                "symbol": duplicate_signal.symbol,
                                "error": str(exc),
                                "reason_code": outcome["reason_code"],
                                "retryable": outcome["retryable"],
                                "next_action": outcome["next_action"],
                            }
                        )
                        if outcome["reason_code"] in {
                            "ibkr_bracket_not_accepted",
                            "broker_submission_failed",
                        }:
                            broker_blocked_symbols.add(duplicate_signal.symbol.upper())
                        db.add(
                            AuditLog(
                                actor=module,
                                action="duplicate_entry_signal_order_submission_failed",
                                entity_type="signal",
                                entity_id=str(duplicate_signal.id),
                                details_json={"error": str(exc), "outcome": outcome, "match": match},
                            )
                        )
                        db.commit()
                else:
                    skipped_duplicates += 1
                    self._count_reason(order_skip_reason_counts, "duplicate_signal")
                    db.add(
                        AuditLog(
                            actor=module,
                            action="entry_match_skipped_idempotent",
                            entity_type="discovered_pattern_match",
                            entity_id=str(match.get("pattern_id", "")),
                            details_json={
                                "signal_idempotency_key": self._signal_idempotency_key(module, match),
                                "reason": "signal_already_exists_for_pattern_symbol_variant_bar",
                            },
                        )
                    )
                    db.commit()
                continue
            if self._has_active_exposure(db, match, module=module):
                skipped_duplicates += 1
                self._count_reason(order_skip_reason_counts, "active_exposure")
                db.add(
                    AuditLog(
                        actor=module,
                        action="entry_match_skipped_active_exposure",
                        entity_type="discovered_pattern_match",
                        entity_id=str(match.get("pattern_id", "")),
                        details_json={
                            "match": match,
                            "reason": "active_signal_or_trade_for_pattern_symbol",
                        },
                    )
                )
                db.commit()
                continue
            if module != "laboratory" and self._has_recent_signal(db, match, module=module):
                skipped_cooldown += 1
                self._count_reason(order_skip_reason_counts, "cooldown")
                db.add(
                    AuditLog(
                        actor=module,
                        action="entry_match_skipped_by_cooldown",
                        entity_type="discovered_pattern_match",
                        entity_id=str(match.get("pattern_id", "")),
                        details_json={
                            "match": match,
                            "cooldown_minutes": settings.entry_cooldown_minutes,
                        },
                    )
                )
                db.commit()
                continue
            candidate = self._candidate_from_match(match)
            risk = RiskManager(settings).validate_candidate(
                candidate,
                db,
                execution_context="laboratory" if module == "laboratory" else "live",
            )
            if not risk.approved:
                rejected_by_risk += 1
                self._count_reason(order_skip_reason_counts, "risk")
                db.add(
                    AuditLog(
                        actor=module,
                        action="entry_match_rejected_by_risk",
                        entity_type="discovered_pattern_match",
                        entity_id=str(match.get("pattern_id", "")),
                        details_json={"match": match, "risk": risk.model_dump(mode="json")},
                    )
                )
                db.commit()
                continue
            entry_quality = build_entry_quality(
                match=match,
                risk=risk,
                settings=settings,
                execution_requested=bool(resolved["execute_orders"]),
                market_session=session,
            )
            quality_rejected = (
                entry_quality["score"] < settings.entry_min_quality_score
                or entry_quality["flags"]
            )
            if module != "laboratory" and quality_rejected:
                rejected_by_entry_quality += 1
                self._count_reason(order_skip_reason_counts, "entry_quality")
                db.add(
                    AuditLog(
                        actor=module,
                        action="entry_match_rejected_by_quality",
                        entity_type="discovered_pattern_match",
                        entity_id=str(match.get("pattern_id", "")),
                        details_json={
                            "match": match,
                            "entry_quality": entry_quality,
                            "min_quality_score": settings.entry_min_quality_score,
                        },
                    )
                )
                db.commit()
                continue
            ambiguity_block = self._ambiguity_gate(match, entry_quality)
            if ambiguity_block is not None:
                # Audit §3.1.4: two patterns nearly tied on the same window and
                # quality below the escalated bar -> abstain, keep the outcome
                # observable as a near-miss shadow (reason: ambiguous_match).
                rejected_by_ambiguity += 1
                self._count_reason(order_skip_reason_counts, "ambiguous_match")
                db.add(
                    AuditLog(
                        actor=module,
                        action="entry_match_rejected_by_ambiguity",
                        entity_type="discovered_pattern_match",
                        entity_id=str(match.get("pattern_id", "")),
                        details_json={
                            "match": match,
                            "entry_quality": entry_quality,
                            "ambiguity_gate": ambiguity_block,
                        },
                    )
                )
                db.commit()
                if module == "laboratory":
                    opened = self._open_near_miss_shadow_observation(
                        db,
                        match=match,
                        resolved=resolved,
                        session=session,
                        extra_reasons=["ambiguous_match"],
                    )
                    if opened is not None:
                        signal, observation = opened
                        signals_created += 1
                        signal_ids.append(signal.id)
                        near_miss_signal_ids.append(signal.id)
                        paper_observations_opened += 1
                        near_miss_shadow_observations_opened += 1
                        paper_observation_trade_ids.append(observation.id)
                        near_miss_trade_ids.append(observation.id)
                continue
            if not resolved["store_signals"]:
                self._count_reason(order_skip_reason_counts, "store_signals_disabled")
                continue

            signal = self._store_signal(
                db,
                module=module,
                match=match,
                candidate=candidate,
                risk=risk,
                execute_orders=bool(resolved["execute_orders"]),
                requested_execute_orders=requested_execute_orders,
                execution_degrade_reason=execution_degrade_reason,
                market_session=session,
                entry_quality=entry_quality,
            )
            signals_created += 1
            signal_ids.append(signal.id)

            if not resolved["execute_orders"]:
                self._count_reason(
                    order_skip_reason_counts,
                    self._no_order_reason(
                        module,
                        match=match,
                        requested_execute_orders=requested_execute_orders,
                        execute_orders=bool(resolved["execute_orders"]),
                        execution_degrade_reason=execution_degrade_reason,
                    )
                    or "orders_disabled",
                )
                if module == "laboratory":
                    observation = self._open_lab_observation(
                        db,
                        signal=signal,
                        match=match,
                        risk=risk,
                    )
                    if observation is not None:
                        paper_observations_opened += 1
                        shadow_no_order_observations_opened += 1
                        paper_observation_trade_ids.append(observation.id)
                        shadow_no_order_trade_ids.append(observation.id)
                continue

            try:
                trade = IBKRBroker(settings).submit_signal_bracket(
                    db,
                    signal,
                    reason=self._execution_reason(module),
                )
                orders_submitted += 1
                trade_ids.append(trade.id)
            except Exception as exc:  # noqa: BLE001
                outcome = mark_signal_order_failure(signal, str(exc))
                self._count_reason(order_skip_reason_counts, str(outcome["reason_code"]))
                order_errors.append(
                    {
                        "signal_id": signal.id,
                        "symbol": signal.symbol,
                        "error": str(exc),
                        "reason_code": outcome["reason_code"],
                        "retryable": outcome["retryable"],
                        "next_action": outcome["next_action"],
                    }
                )
                if outcome["reason_code"] in {"ibkr_bracket_not_accepted", "broker_submission_failed"}:
                    broker_blocked_symbols.add(signal.symbol.upper())
                db.add(
                    AuditLog(
                        actor=module,
                        action="entry_order_submission_failed",
                        entity_type="signal",
                        entity_id=str(signal.id),
                        details_json={"error": str(exc), "outcome": outcome, "match": match},
                    )
                )
                db.commit()

        result = {
            "module": module,
            "patterns_checked": match_result["patterns_checked"],
            "symbols_checked": match_result["symbols_checked"],
            "matches_found": len(ranked_matches),
            "entry_variants_considered": len(all_ranked_matches),
            "signals_created": signals_created,
            "orders_submitted": orders_submitted,
            "skipped_duplicates": skipped_duplicates,
            "skipped_cooldown": skipped_cooldown,
            "rejected_by_entry_gate": rejected_by_entry_gate,
            "rejected_by_entry_quality": rejected_by_entry_quality,
            "rejected_by_ambiguity": rejected_by_ambiguity,
            "rejected_by_risk": rejected_by_risk,
            "rejected_by_production_manifest": rejected_by_production_manifest,
            "production_manifest_rejection_reason_counts": production_manifest_rejection_reason_counts,
            "near_miss_shadow_observations_opened": near_miss_shadow_observations_opened,
            "order_errors": order_errors,
            "order_skip_reason_counts": order_skip_reason_counts,
            "signal_ids": signal_ids,
            "near_miss_signal_ids": near_miss_signal_ids,
            "trade_ids": trade_ids,
            "paper_observations_opened": paper_observations_opened,
            "paper_observations_closed": observation_lifecycle["closed_observations"],
            "paper_observation_trade_ids": paper_observation_trade_ids,
            "near_miss_trade_ids": near_miss_trade_ids,
            "shadow_no_order_observations_opened": shadow_no_order_observations_opened,
            "shadow_no_order_trade_ids": shadow_no_order_trade_ids,
            "paper_observation_lifecycle": observation_lifecycle,
            "top_opportunities": self._top_opportunities(ranked_matches),
            **self._scan_execution_metadata(
                module,
                requested_execute_orders=requested_execute_orders,
                execute_orders=bool(resolved["execute_orders"]),
                execution_degrade_reason=execution_degrade_reason,
            ),
            "store_signals": resolved["store_signals"],
            "execute_orders": resolved["execute_orders"],
            "similarity_threshold": match_result["similarity_threshold"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        from tradeo.services.runtime_status import write_entry_scan_status

        write_entry_scan_status(module, result, settings)
        return result

    def status(self, db: Session) -> dict[str, Any]:
        from tradeo.db.models import DiscoveredPattern, DiscoveredPatternStatus
        from tradeo.services.runtime_status import entry_scan_status, worker_runtime_status

        lab_statuses = NovelPatternMatcher._statuses_for_module("laboratory")
        laboratory_patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(DiscoveredPattern.status.in_(lab_statuses))
            .count()
        )
        legacy_runtime_blocked_patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(
                DiscoveredPattern.status.in_(
                    [
                        DiscoveredPatternStatus.PREMIUM_CANDIDATE,
                        DiscoveredPatternStatus.PAPER_CANDIDATE,
                    ]
                )
            )
            .count()
        )
        production_patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(DiscoveredPattern.status == DiscoveredPatternStatus.PRODUCTION)
            .all()
        )
        production_manifest_statuses = [
            production_manifest_status(pattern) for pattern in production_patterns
        ]
        production_manifest_patterns = [
            item for item in production_manifest_statuses if bool(item["valid"])
        ]
        production_manifest_blocked_reason_counts = self._reason_counts(
            item for item in production_manifest_statuses if not bool(item["valid"])
        )
        settings = self.settings
        assert settings is not None
        worker_status = worker_runtime_status(settings)
        session = market_session_status()
        market_open = bool(session["regular_session_open"])
        laboratory_market_ok = market_open or not settings.laboratory_market_hours_only
        fox_market_ok = market_open or not settings.fox_hunter_market_hours_only
        laboratory_ok = (
            settings.scheduler_enabled
            and settings.laboratory_scanner_enabled
            and bool(worker_status["ok"])
            and laboratory_market_ok
        )
        fox_hunter_ok = (
            settings.scheduler_enabled
            and settings.fox_hunter_enabled
            and bool(worker_status["ok"])
            and fox_market_ok
        )
        laboratory_state = "ok" if laboratory_ok else "market_closed" if not laboratory_market_ok else "stopped"
        fox_state = "ok" if fox_hunter_ok else "market_closed" if not fox_market_ok else "stopped"
        laboratory_entry_status = entry_scan_status("laboratory", settings)
        fox_entry_status = entry_scan_status("fox_hunter", settings)
        from tradeo.services.system_controls import runtime_kill_switch, runtime_kill_switch_active

        runtime_kill_switch_enabled = runtime_kill_switch_active(db)
        runtime_kill_switch_control = runtime_kill_switch(db)
        paper_order_safety_ok = (
            not settings.kill_switch_enabled
            and not runtime_kill_switch_enabled
            and settings.trading_mode == "paper"
            and not settings.live_armed
            and int(settings.ibkr_port) not in {7496, 4001}
        )
        # Lab paper order permission is intentionally independent from the
        # auto-submit toggle: paper mode should stay available unless a severe
        # safety gate blocks it or the operator explicitly disables scanning.
        paper_orders_allowed = paper_order_safety_ok
        default_lab_execute_orders = (
            settings.laboratory_auto_submit_paper_orders and paper_orders_allowed
        )
        live_orders_allowed = (
            settings.fox_hunter_auto_submit_live_orders
            and settings.live_armed
            and not settings.kill_switch_enabled
            and not runtime_kill_switch_enabled
        )
        return {
            "research": {"purpose": "discover_new_patterns"},
            "laboratory": {
                "purpose": "paper_validate_research_patterns",
                "enabled": settings.laboratory_scanner_enabled,
                "operational_ok": laboratory_ok,
                "state": laboratory_state,
                "market_session": session,
                "worker": worker_status,
                "auto_submit_paper_orders": settings.laboratory_auto_submit_paper_orders,
                "paper_orders_allowed": paper_orders_allowed,
                "paper_order_safety_ok": paper_order_safety_ok,
                "default_execute_orders": default_lab_execute_orders,
                "default_execution_mode": (
                    "ibkr_paper" if default_lab_execute_orders else LAB_SHADOW_EXECUTION_MODE
                ),
                "default_shadow_only": not default_lab_execute_orders,
                "runtime_kill_switch_enabled": runtime_kill_switch_enabled,
                "runtime_kill_switch_reason": (
                    runtime_kill_switch_control.reason if runtime_kill_switch_control else None
                ),
                "blocked_but_healthy": laboratory_ok and not paper_orders_allowed,
                "execution_block_reason": None
                if paper_orders_allowed
                else self._paper_order_block_reason(
                    settings,
                    paper_order_safety_ok,
                    runtime_kill_switch_enabled=runtime_kill_switch_enabled,
                ),
                "eligible_patterns": laboratory_patterns,
                "legacy_runtime_blocked_patterns": legacy_runtime_blocked_patterns,
                "symbols_checked": laboratory_entry_status["symbols_checked"],
                "last_symbols_checked": laboratory_entry_status["last_symbols_checked"],
                "last_scan": self._entry_status_summary(laboratory_entry_status),
            },
            "fox_hunter": {
                "purpose": "live_trade_production_patterns",
                "enabled": settings.fox_hunter_enabled,
                "operational_ok": fox_hunter_ok,
                "state": fox_state,
                "market_session": session,
                "worker": worker_status,
                "auto_submit_live_orders": settings.fox_hunter_auto_submit_live_orders,
                "live_orders_allowed": live_orders_allowed,
                "runtime_kill_switch_enabled": runtime_kill_switch_enabled,
                "runtime_kill_switch_reason": (
                    runtime_kill_switch_control.reason if runtime_kill_switch_control else None
                ),
                "blocked_but_healthy": fox_hunter_ok and not live_orders_allowed,
                "execution_block_reason": None
                if live_orders_allowed
                else self._live_order_block_reason(
                    settings,
                    runtime_kill_switch_enabled=runtime_kill_switch_enabled,
                ),
                "eligible_patterns": len(production_manifest_patterns),
                "production_status_patterns": len(production_patterns),
                "production_manifest_required": True,
                "production_gate_required": "DirectorProductionGate",
                "production_manifest_policy": (
                    "canonical_manifest_with_director_production_gate_paper_fill_evidence"
                ),
                "production_manifest_blocked_patterns": len(production_patterns)
                - len(production_manifest_patterns),
                "production_manifest_blocked_reason_counts": production_manifest_blocked_reason_counts,
                "live_readiness": {
                    "orders_allowed": live_orders_allowed,
                    "live_armed": settings.live_armed,
                    "auto_submit_live_orders": settings.fox_hunter_auto_submit_live_orders,
                    "eligible_production_manifests": len(production_manifest_patterns),
                    "production_status_patterns": len(production_patterns),
                    "block_reason": None
                    if live_orders_allowed
                    else self._live_order_block_reason(
                        settings,
                        runtime_kill_switch_enabled=runtime_kill_switch_enabled,
                    ),
                },
                "symbols_checked": fox_entry_status["symbols_checked"],
                "last_symbols_checked": fox_entry_status["last_symbols_checked"],
                "last_scan": self._entry_status_summary(fox_entry_status),
                "live_armed": settings.live_armed,
            },
        }

    @staticmethod
    def _entry_status_summary(entry_status: dict[str, Any]) -> dict[str, Any]:
        return {
            "patterns_checked": entry_status.get("patterns_checked", 0),
            "matches_found": entry_status.get("matches_found", 0),
            "execute_orders": entry_status.get("execute_orders", True),
            "signals_created": entry_status.get("signals_created", 0),
            "orders_submitted": entry_status.get("orders_submitted", 0),
            "skipped_duplicates": entry_status.get("skipped_duplicates", 0),
            "skipped_cooldown": entry_status.get("skipped_cooldown", 0),
            "rejected_by_entry_gate": entry_status.get("rejected_by_entry_gate", 0),
            "rejected_by_entry_quality": entry_status.get("rejected_by_entry_quality", 0),
            "rejected_by_risk": entry_status.get("rejected_by_risk", 0),
            "rejected_by_production_manifest": entry_status.get("rejected_by_production_manifest", 0),
            "production_manifest_rejection_reason_counts": entry_status.get(
                "production_manifest_rejection_reason_counts", {}
            ),
            "order_errors": entry_status.get("order_errors", []),
            "order_skip_reason_counts": entry_status.get("order_skip_reason_counts", {}),
            "zero_order_scan_streak": entry_status.get("zero_order_scan_streak", 0),
            "zero_order_alert": entry_status.get("zero_order_alert", False),
            "zero_order_block_reason": entry_status.get("zero_order_block_reason"),
            "generated_at": entry_status.get("generated_at"),
        }

    @staticmethod
    def _paper_order_block_reason(
        settings: Settings,
        paper_order_safety_ok: bool,
        *,
        runtime_kill_switch_enabled: bool = False,
    ) -> str:
        if settings.kill_switch_enabled:
            return "kill_switch_enabled"
        if runtime_kill_switch_enabled:
            return "runtime_kill_switch_enabled"
        if settings.trading_mode != "paper":
            return "trading_mode_not_paper"
        if settings.live_armed:
            return "live_armed_blocks_laboratory"
        if not paper_order_safety_ok:
            return "ibkr_live_port_blocked"
        return "unknown"

    @staticmethod
    def _live_order_block_reason(
        settings: Settings,
        *,
        runtime_kill_switch_enabled: bool = False,
    ) -> str:
        if not settings.fox_hunter_auto_submit_live_orders:
            return "live_auto_submit_disabled"
        if not settings.live_armed:
            return "live_armed_false"
        if settings.kill_switch_enabled:
            return "kill_switch_enabled"
        if runtime_kill_switch_enabled:
            return "runtime_kill_switch_enabled"
        return "unknown"

    def _requires_market_hours(self, module: EntryModule) -> bool:
        settings = self.settings
        assert settings is not None
        return (
            settings.laboratory_market_hours_only
            if module == "laboratory"
            else settings.fox_hunter_market_hours_only
        )

    @staticmethod
    def _market_closed_result(
        module: EntryModule,
        resolved: dict[str, Any],
        session: dict[str, object],
    ) -> dict[str, Any]:
        return {
            "module": module,
            "patterns_checked": 0,
            "symbols_checked": 0,
            "matches_found": 0,
            "entry_variants_considered": 0,
            "signals_created": 0,
            "orders_submitted": 0,
            "skipped_duplicates": 0,
            "skipped_cooldown": 0,
            "rejected_by_entry_gate": 0,
            "rejected_by_entry_quality": 0,
            "rejected_by_ambiguity": 0,
            "rejected_by_risk": 0,
            "rejected_by_production_manifest": 0,
            "production_manifest_rejection_reason_counts": {},
            "near_miss_shadow_observations_opened": 0,
            "order_errors": [],
            "order_skip_reason_counts": {},
            "signal_ids": [],
            "near_miss_signal_ids": [],
            "trade_ids": [],
            "paper_observations_opened": 0,
            "paper_observations_closed": 0,
            "paper_observation_trade_ids": [],
            "near_miss_trade_ids": [],
            "shadow_no_order_observations_opened": 0,
            "shadow_no_order_trade_ids": [],
            "paper_observation_lifecycle": {
                "open_observations": 0,
                "closed_observations": 0,
                "closed_trade_ids": [],
                "data_errors": [],
            },
            "top_opportunities": [],
            "store_signals": resolved["store_signals"],
            "execute_orders": resolved["execute_orders"],
            "similarity_threshold": resolved["similarity_threshold"],
            "skipped_reason": session.get("state", "market_closed"),
            "market_session": session,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _scan_execution_metadata(
        module: EntryModule,
        *,
        requested_execute_orders: bool,
        execute_orders: bool,
        execution_degrade_reason: str | None,
    ) -> dict[str, Any]:
        return {
            "requested_execute_orders": requested_execute_orders,
            "execution_mode": PatternEntryScanner._scan_execution_mode(
                module,
                execute_orders=execute_orders,
            ),
            "execution_degraded_to_shadow": (
                module == "laboratory"
                and requested_execute_orders
                and not execute_orders
            ),
            "execution_degrade_reason": execution_degrade_reason,
        }

    @staticmethod
    def _scan_execution_mode(module: EntryModule, *, execute_orders: bool) -> str | None:
        if module == "laboratory":
            return "ibkr_paper" if execute_orders else LAB_SHADOW_EXECUTION_MODE
        if module == "fox_hunter" and execute_orders:
            return "ibkr_live"
        return None

    @staticmethod
    def _count_reason(reason_counts: dict[str, int], reason: str | None) -> None:
        reason_key = str(reason or "unknown").strip() or "unknown"
        reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1

    @staticmethod
    def _no_order_reason(
        module: EntryModule,
        *,
        match: dict[str, Any],
        requested_execute_orders: bool,
        execute_orders: bool,
        execution_degrade_reason: str | None,
    ) -> str | None:
        if module != "laboratory" or execute_orders:
            return None
        if execution_degrade_reason:
            return execution_degrade_reason
        if match.get("near_miss"):
            near_miss_type = str(match.get("near_miss_type") or "")
            if near_miss_type == "ambiguous_match_shadow":
                return "ambiguous_match_shadow_observation"
            return "entry_gate_volume_near_miss_shadow"
        return (
            "paper_order_requested_but_safety_degraded"
            if requested_execute_orders
            else "paper_order_submission_disabled"
        )

    @classmethod
    def _order_decision_metadata(
        cls,
        module: EntryModule,
        *,
        match: dict[str, Any],
        requested_execute_orders: bool,
        execute_orders: bool,
        execution_degrade_reason: str | None,
    ) -> dict[str, Any]:
        no_order_reason = cls._no_order_reason(
            module,
            match=match,
            requested_execute_orders=requested_execute_orders,
            execute_orders=execute_orders,
            execution_degrade_reason=execution_degrade_reason,
        )
        decision = {
            "requested_execute_orders": requested_execute_orders,
            "execute_orders": execute_orders,
            "execution_request_mode": cls._scan_execution_mode(module, execute_orders=execute_orders),
            "submitted_to_broker": execute_orders,
            "no_order_reason": no_order_reason,
        }
        return {key: value for key, value in decision.items() if value is not None}

    def _resolved_options(self, module: EntryModule, **overrides: Any) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        if module == "fox_hunter":
            defaults = {
                "limit": settings.fox_hunter_symbol_limit,
                "max_patterns": settings.fox_hunter_max_patterns,
                "max_results": settings.discovery_match_max_results,
                "similarity_threshold": settings.fox_hunter_similarity_threshold,
                "store_signals": settings.fox_hunter_store_signals,
                "execute_orders": settings.fox_hunter_auto_submit_live_orders,
            }
        else:
            defaults = {
                "limit": settings.laboratory_symbol_limit,
                "max_patterns": settings.laboratory_max_patterns,
                "max_results": settings.laboratory_match_max_results,
                "similarity_threshold": settings.laboratory_similarity_threshold,
                "store_signals": settings.laboratory_store_signals,
                "execute_orders": settings.laboratory_auto_submit_paper_orders,
            }
        return {key: defaults[key] if value is None else value for key, value in overrides.items()}

    def _validate_module_execution(
        self,
        module: EntryModule,
        *,
        execute_orders: bool | None,
    ) -> None:
        settings = self.settings
        assert settings is not None
        execute = execute_orders
        if execute is None:
            execute = (
                settings.fox_hunter_auto_submit_live_orders
                if module == "fox_hunter"
                else settings.laboratory_auto_submit_paper_orders
            )
        if not execute:
            return
        if settings.kill_switch_enabled:
            raise PatternEntryScannerSafetyError("kill switch blocks scanner order execution")
        if module == "laboratory":
            if settings.trading_mode != "paper" or settings.live_armed:
                raise PatternEntryScannerSafetyError(
                    "Laboratory can only auto-submit orders in paper mode"
                )
            if int(settings.ibkr_port) in {7496, 4001}:
                raise PatternEntryScannerSafetyError("Laboratory refuses live IBKR ports")
            return
        if not settings.live_armed:
            raise PatternEntryScannerSafetyError(
                "Fox Hunter live execution requires live_armed=true"
            )

    @staticmethod
    def _fox_match_has_active_manifest(db: Session, match: dict[str, Any]) -> bool:
        return bool(
            PatternEntryScanner._fox_match_production_manifest_status(
                db,
                match,
                cache={},
                now=datetime.now(timezone.utc),
            )["valid"]
        )

    @staticmethod
    def _fox_match_production_manifest_status(
        db: Session,
        match: dict[str, Any],
        *,
        cache: dict[int, dict[str, Any]],
        now: datetime,
    ) -> dict[str, Any]:
        try:
            pattern_id = int(match.get("pattern_id") or 0)
        except (TypeError, ValueError):
            return {"valid": False, "reason_code": "missing_pattern_id", "checked_at": now.isoformat()}
        if pattern_id <= 0:
            return {"valid": False, "reason_code": "missing_pattern_id", "checked_at": now.isoformat()}
        cached = cache.get(pattern_id)
        if cached is not None:
            return cached
        pattern = db.get(DiscoveredPattern, pattern_id)
        status = production_manifest_status(pattern, now=now)
        cache[pattern_id] = status
        return status

    def _candidate_from_match(self, match: dict[str, Any]) -> PatternCandidate:
        metrics = match.get("metrics") or {}
        features = dict(metrics.get("features") or {})
        features["entry_variant_id"] = str(match.get("entry_variant_id") or "")
        features["regime_key"] = str((match.get("regime") or {}).get("regime_key") or "")
        for key in ("pattern_family_key", "canonical_pattern_key", "pattern_key", "pattern_id"):
            if match.get(key) is not None:
                features[key] = str(match.get(key) or "")
        return PatternCandidate(
            symbol=str(match["symbol"]),
            pattern=str(match["pattern_name"]),
            side=str(match["side"]),
            timeframe=str(match["timeframe"]),
            entry=float(match["entry_price"]),
            stop=float(match["stop_price"]),
            target=float(match["target_price"]),
            reward_risk=float(match["reward_risk"]),
            confidence=float(match["score"]),
            rule_score=float(match["similarity"]),
            ml_score=float(metrics.get("pattern_score", 0.0)),
            vision_score=float(metrics.get("pattern_stability_score", 0.0)),
            composite_score=float(match.get("entry_score") or match["score"]),
            features=features,
            notes=[str(match.get("notes", ""))],
        )

    @classmethod
    def _has_active_exposure(cls, db: Session, match: dict[str, Any], *, module: EntryModule) -> bool:
        active_signals = (
            db.query(Signal)
            .filter(Signal.symbol == str(match["symbol"]))
            .filter(Signal.pattern == str(match["pattern_name"]))
            .filter(
                Signal.status.in_(
                    [
                        SignalStatus.WATCHLIST,
                        SignalStatus.PAPER_APPROVED,
                        SignalStatus.PENDING_HUMAN_APPROVAL,
                        SignalStatus.LIVE_APPROVED,
                    ]
                )
            )
            .all()
        )
        if any(cls._signal_belongs_to_module(signal, module) for signal in active_signals):
            return True
        active_trades = (
            db.query(Trade)
            .options(joinedload(Trade.signal))
            .filter(Trade.symbol == str(match["symbol"]))
            .filter(Trade.pattern == str(match["pattern_name"]))
            .filter(Trade.status == TradeStatus.OPEN)
            .all()
        )
        return any(cls._trade_belongs_to_module(trade, module) for trade in active_trades)

    @staticmethod
    def _signal_idempotency_key(module: EntryModule, match: dict[str, Any]) -> str:
        """Stable identity of a signal: same pattern, symbol, variant and bar.

        Cooldowns only guard a time window; a worker restart or a re-scan of the
        same completed bar can still emit the same economic signal twice. The
        key pins the signal to (pattern, symbol, variant, bar_ts) so re-scans of
        an unchanged bar are no-ops.
        """
        return "|".join(
            (
                str(module),
                str(match.get("pattern_id") or ""),
                str(match.get("symbol") or "").upper(),
                str(match.get("timeframe") or ""),
                str(match.get("entry_variant_id") or ""),
                str(match.get("window_end") or ""),
            )
        )

    def _has_duplicate_signal(self, db: Session, match: dict[str, Any], *, module: EntryModule) -> bool:
        return self._duplicate_signal(db, match, module=module) is not None

    def _duplicate_signal(self, db: Session, match: dict[str, Any], *, module: EntryModule) -> Signal | None:
        if not str(match.get("window_end") or ""):
            return None
        key = self._signal_idempotency_key(module, match)
        existing = (
            db.query(Signal)
            .filter(Signal.symbol == str(match["symbol"]))
            .filter(Signal.pattern == str(match["pattern_name"]))
            .all()
        )
        for signal in existing:
            metadata = signal.metadata_json or {}
            if str(metadata.get("signal_idempotency_key") or "") == key:
                return signal
        return None

    def _can_submit_duplicate_lab_signal(self, db: Session, signal: Signal) -> bool:
        metadata = signal.metadata_json or {}
        if signal.status != SignalStatus.PAPER_APPROVED:
            return False
        if metadata.get("near_miss") or metadata.get("near_miss_shadow"):
            return False
        outcome = metadata.get("execution_outcome") or {}
        if isinstance(outcome, dict):
            if outcome.get("retryable") is False:
                return False
            updated_at = self._parse_datetime(outcome.get("updated_at"))
            if updated_at is not None:
                settings = self.settings
                assert settings is not None
                retry_after = timedelta(minutes=max(5, int(settings.entry_cooldown_minutes)))
                if datetime.now(timezone.utc) - updated_at < retry_after:
                    return False
        existing_trade = db.query(Trade).filter(Trade.signal_id == signal.id).first()
        return existing_trade is None

    def _has_recent_lab_symbol_order_failure(self, db: Session, symbol: str) -> bool:
        settings = self.settings
        assert settings is not None
        retry_after = timedelta(minutes=max(60, int(settings.entry_cooldown_minutes)))
        cutoff = datetime.now(timezone.utc) - retry_after
        signals = (
            db.query(Signal)
            .filter(Signal.symbol == symbol.upper())
            .filter(Signal.status == SignalStatus.PAPER_APPROVED)
            .all()
        )
        for signal in signals:
            if not self._signal_belongs_to_module(signal, "laboratory"):
                continue
            outcome = (signal.metadata_json or {}).get("execution_outcome") or {}
            if not isinstance(outcome, dict):
                continue
            if outcome.get("reason_code") not in {"ibkr_bracket_not_accepted", "broker_submission_failed"}:
                continue
            updated_at = self._parse_datetime(outcome.get("updated_at"))
            if updated_at is not None and updated_at >= cutoff:
                return True
        return False

    @staticmethod
    def _audit_lab_symbol_broker_cooldown(db: Session, *, match: dict[str, Any], reason: str) -> None:
        db.add(
            AuditLog(
                actor="laboratory",
                action="entry_match_skipped_symbol_broker_cooldown",
                entity_type="discovered_pattern_match",
                entity_id=str(match.get("pattern_id", "")),
                details_json={
                    "match": match,
                    "reason": reason,
                    "symbol": str(match.get("symbol") or "").upper(),
                },
            )
        )
        db.commit()

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _prepare_lab_signal_for_order_submission(signal: Signal, match: dict[str, Any]) -> None:
        metadata = dict(signal.metadata_json or {})
        for key in ("no_ibkr_order", "observation_only", "paper_only"):
            metadata.pop(key, None)
        metadata.update(
            {
                "evidence_type": EvidenceType.IBKR_PAPER_ORDER.value,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "execution_mode": "ibkr",
                "execution_requested": True,
                "paper_order_requested": True,
                "execution_request_mode": "ibkr_paper",
                "entry_module": "laboratory",
                "entry_variant_id": metadata.get("entry_variant_id") or match.get("entry_variant_id"),
                "entry_variant": metadata.get("entry_variant") or match.get("entry_variant"),
                "entry_audit": metadata.get("entry_audit") or match.get("entry_audit"),
                "regime": metadata.get("regime") or match.get("regime"),
                "regime_fit": metadata.get("regime_fit") or match.get("regime_fit"),
            }
        )
        signal.metadata_json = metadata
        signal.human_approved = True

    def _has_recent_signal(self, db: Session, match: dict[str, Any], *, module: EntryModule) -> bool:
        settings = self.settings
        assert settings is not None
        cooldown_minutes = max(0, int(settings.entry_cooldown_minutes))
        if cooldown_minutes <= 0:
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
        recent_signals = (
            db.query(Signal)
            .filter(Signal.symbol == str(match["symbol"]))
            .filter(Signal.pattern == str(match["pattern_name"]))
            .filter(Signal.created_at >= cutoff)
            .all()
        )
        variant = str(match.get("entry_variant_id") or "")
        for signal in recent_signals:
            if not self._signal_belongs_to_module(signal, module):
                continue
            metadata = signal.metadata_json or {}
            previous_variant = str(metadata.get("entry_variant_id") or "")
            if not variant or not previous_variant or previous_variant == variant:
                return True
        return False

    @staticmethod
    def _signal_belongs_to_module(signal: Signal, module: EntryModule) -> bool:
        metadata = signal.metadata_json or {}
        entry_module = metadata.get("entry_module")
        if entry_module:
            return str(entry_module) == module
        if module == "fox_hunter":
            return signal.strategy_version.startswith("fox_hunter_")
        purpose = str(metadata.get("purpose") or "")
        return signal.strategy_version.startswith(("laboratory_", "ibkr_paper_", "ibkr_smoke_")) or (
            purpose.startswith("ibkr_paper_")
        )

    @classmethod
    def _trade_belongs_to_module(cls, trade: Trade, module: EntryModule) -> bool:
        if trade.signal is not None:
            return cls._signal_belongs_to_module(trade.signal, module)
        metadata = trade.metadata_json or {}
        source_module = metadata.get("entry_module") or metadata.get("source_module")
        if source_module:
            return str(source_module) == module
        reason = str(metadata.get("reason") or "")
        if module == "fox_hunter":
            return reason.startswith("fox_hunter")
        execution_mode = str(metadata.get("execution_mode") or "")
        return reason.startswith("laboratory") or execution_mode in {"paper", "lab_shadow_observation"}

    @staticmethod
    def _top_opportunities(matches: list[dict[str, Any]], *, limit: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "rank": match.get("opportunity_rank"),
                "rank_score": match.get("opportunity_rank_score"),
                "symbol": match.get("symbol"),
                "pattern_name": match.get("pattern_name"),
                "entry_variant_id": match.get("entry_variant_id"),
                "regime_key": (match.get("regime") or {}).get("regime_key"),
                "entry_score": match.get("entry_score"),
                "similarity": match.get("similarity"),
                "entry_gate_passed": ((match.get("metrics") or {}).get("entry_gate") or {}).get("passed"),
                "entry_gate_reason": ((match.get("metrics") or {}).get("entry_gate") or {}).get("reason"),
                "entry_rejection_reasons": ((match.get("metrics") or {}).get("entry_gate") or {}).get(
                    "rejection_reasons", []
                ),
                "near_miss_shadow_candidate": match.get("near_miss_shadow_candidate"),
                "history_count": (match.get("opportunity_rank_components") or {}).get("history_count"),
                "history_expectancy_r": (match.get("opportunity_rank_components") or {}).get(
                    "history_expectancy_r"
                ),
                "rank_reason": match.get("opportunity_rank_reason"),
            }
            for match in matches[:limit]
        ]

    @staticmethod
    def _select_best_variant_per_exposure(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected: dict[tuple[str, str], dict[str, Any]] = {}
        for match in matches:
            key = (str(match.get("symbol") or ""), str(match.get("pattern_name") or ""))
            current = selected.get(key)
            if current is None or float(match.get("opportunity_rank_score") or 0.0) > float(
                current.get("opportunity_rank_score") or 0.0
            ):
                selected[key] = match
        ordered = sorted(
            selected.values(),
            key=lambda item: (
                float(item.get("opportunity_rank_score") or 0.0),
                float(item.get("entry_score") or 0.0),
                float(item.get("score") or 0.0),
            ),
            reverse=True,
        )
        for index, match in enumerate(ordered, start=1):
            match["opportunity_rank"] = index
        return ordered

    @staticmethod
    def _reason_counts(statuses: Any) -> dict[str, int]:
        counts: dict[str, int] = {}
        for status in statuses:
            reason = str(status.get("reason_code") or "unknown")
            counts[reason] = counts.get(reason, 0) + 1
        return counts

    def _execution_history(self, db: Session, module: EntryModule) -> dict[tuple[str, ...], dict[str, float]]:
        trades = (
            db.query(Trade)
            .options(joinedload(Trade.signal))
            .filter(Trade.status == TradeStatus.CLOSED)
            .order_by(Trade.closed_at.desc(), Trade.opened_at.desc())
            .limit(500)
            .all()
        )
        by_key: dict[tuple[str, ...], list[float]] = {}
        for trade in trades:
            signal = trade.signal
            if signal is None:
                continue
            metadata = signal.metadata_json or {}
            if metadata.get("entry_module") != module:
                continue
            trade_metadata = evidence_metadata_with_stored_columns(
                trade.metadata_json or {},
                evidence_type=trade.evidence_type,
                evidence_quality=trade.evidence_quality,
            )
            if not is_director_review_paper_fill_evidence(
                trade_metadata,
                trade_status=trade.status,
                signal_metadata=metadata,
                broker_order_id=trade.broker_order_id,
            ):
                continue
            variant = str(metadata.get("entry_variant_id") or "*")
            regime_key = str((metadata.get("regime") or {}).get("regime_key") or "*")
            keys = [
                (trade.pattern, trade.symbol, variant, regime_key),
                (trade.pattern, "*", variant, regime_key),
                (trade.pattern, trade.symbol, variant, "*"),
                (trade.pattern, "*", variant, "*"),
                (trade.pattern, trade.symbol, "*", "*"),
                (trade.pattern, "*", "*", "*"),
            ]
            for key in keys:
                by_key.setdefault(key, []).append(float(trade.r_multiple or 0.0))
        return {key: self._history_item(values) for key, values in by_key.items()}

    def _ambiguity_gate(
        self,
        match: dict[str, Any],
        entry_quality: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Ambiguity with teeth (audit §3.1.4): block ambiguous matches that do
        not clear the escalated quality bar. Returns the block details, or None
        when the match may proceed. Annotates the match either way so the
        escalation is auditable on stored signals.
        """
        settings = self.settings
        assert settings is not None
        if not settings.entry_ambiguity_gate_enabled:
            return None
        ambiguity = match.get("match_ambiguity") or (match.get("metrics") or {}).get(
            "match_ambiguity"
        ) or {}
        ratio = self._safe_float(
            match.get("ambiguity_ratio", ambiguity.get("ambiguity_ratio")), 0.0
        )
        if ratio < float(settings.entry_ambiguity_ratio_threshold):
            return None
        required_quality = float(settings.entry_min_quality_score) + float(
            settings.entry_ambiguity_quality_margin
        )
        quality_score = self._safe_float(entry_quality.get("score"), 0.0)
        details = {
            "ambiguity_ratio": round(ratio, 6),
            "ambiguity_ratio_threshold": float(settings.entry_ambiguity_ratio_threshold),
            "second_best_pattern_key": ambiguity.get("second_best_pattern_key"),
            "required_quality_score": round(required_quality, 6),
            "entry_quality_score": round(quality_score, 6),
            "escalated": True,
            "passed": quality_score >= required_quality,
        }
        match["ambiguity_gate"] = details
        metrics = match.get("metrics")
        if isinstance(metrics, dict):
            metrics["ambiguity_gate"] = details
        if details["passed"]:
            return None
        return details

    def _open_near_miss_shadow_observation(
        self,
        db: Session,
        *,
        match: dict[str, Any],
        resolved: dict[str, Any],
        session: dict[str, Any],
        extra_reasons: list[str] | None = None,
    ) -> tuple[Signal, Trade] | None:
        settings = self.settings
        assert settings is not None
        if not resolved["store_signals"]:
            return None
        entry_gate = ((match.get("metrics") or {}).get("entry_gate") or {})
        if self._has_duplicate_signal(db, match, module="laboratory"):
            return None
        candidate = self._candidate_from_match(match)
        risk = RiskManager(settings).validate_candidate(
            candidate,
            db,
            execution_context="laboratory",
        )
        if not risk.approved:
            db.add(
                AuditLog(
                    actor="laboratory",
                    action="near_miss_shadow_rejected_by_risk",
                    entity_type="discovered_pattern_match",
                    entity_id=str(match.get("pattern_id", "")),
                    details_json={"match": match, "risk": risk.model_dump(mode="json")},
                )
            )
            db.commit()
            return None
        entry_quality = build_entry_quality(
            match=match,
            risk=risk,
            settings=settings,
            execution_requested=False,
            market_session=session,
        )
        if float(entry_quality.get("score") or 0.0) < 0.45:
            db.add(
                AuditLog(
                    actor="laboratory",
                    action="near_miss_shadow_rejected_by_quality",
                    entity_type="discovered_pattern_match",
                    entity_id=str(match.get("pattern_id", "")),
                    details_json={
                        "match": match,
                        "entry_quality": entry_quality,
                        "min_near_miss_quality_score": 0.45,
                    },
                )
            )
            db.commit()
            return None
        near_miss_reasons = self._entry_gate_reasons(entry_gate)
        for reason in extra_reasons or []:
            if reason not in near_miss_reasons:
                near_miss_reasons.append(reason)
        if extra_reasons and "ambiguous_match" in extra_reasons:
            match = self._mark_near_miss_shadow_match(
                match,
                near_miss_reasons,
                near_miss_type="ambiguous_match_shadow",
                note="abstained: ambiguous match below escalated quality bar.",
            )
        else:
            match = self._mark_near_miss_shadow_match(match, near_miss_reasons)
        entry_quality = dict(entry_quality)
        entry_quality["near_miss_shadow"] = True
        entry_quality["actionable"] = False
        entry_quality["label"] = "watch"
        entry_quality["flags"] = sorted(set(list(entry_quality.get("flags") or []) + ["near_miss_shadow"]))
        signal = self._store_signal(
            db,
            module="laboratory",
            match=match,
            candidate=candidate,
            risk=risk,
            execute_orders=False,
            requested_execute_orders=False,
            execution_degrade_reason=None,
            market_session=session,
            entry_quality=entry_quality,
        )
        observation = self._open_lab_observation(db, signal=signal, match=match, risk=risk)
        if observation is None:
            return None
        db.add(
            AuditLog(
                actor="laboratory",
                action="near_miss_shadow_observation_opened",
                entity_type="trade",
                entity_id=str(observation.id),
                details_json={
                    "signal_id": signal.id,
                    "trade_id": observation.id,
                    "match": match,
                    "entry_gate": entry_gate,
                    "near_miss_reasons": near_miss_reasons,
                    "no_ibkr_order": True,
                },
            )
        )
        db.commit()
        return signal, observation

    def _is_lab_near_miss_shadow_candidate(
        self,
        match: dict[str, Any],
        entry_gate: dict[str, Any],
    ) -> bool:
        settings = self.settings
        assert settings is not None
        if bool(entry_gate.get("passed", False)):
            return False
        if not str(match.get("entry_variant_id") or ""):
            return False
        if not str((match.get("regime") or {}).get("regime_key") or ""):
            return False
        trigger = str(entry_gate.get("trigger") or match.get("entry_trigger") or "")
        if trigger in {"", "no_operational_trigger", "insufficient_history"}:
            return False
        trigger_score = self._safe_float(
            entry_gate.get("trigger_score"),
            1.0 if trigger not in {"", "no_operational_trigger"} else 0.0,
        )
        if trigger_score <= 0:
            return False
        reasons = set(self._entry_gate_reasons(entry_gate))
        if not reasons or not reasons & LAB_NEAR_MISS_VOLUME_REASONS:
            return False
        if reasons & LAB_NEAR_MISS_HARD_REASONS:
            return False
        if any(reason not in LAB_NEAR_MISS_VOLUME_REASONS for reason in reasons):
            return False
        if entry_gate.get("regime_ok") is False:
            return False
        if entry_gate.get("volatility_ok") is False:
            return False
        if entry_gate.get("not_extended") is False:
            return False
        metrics = match.get("metrics") or {}
        features = metrics.get("features") or {}
        atr_pct = self._safe_float(entry_gate.get("atr_pct", features.get("atr_pct")), 0.0)
        if atr_pct > settings.max_atr_pct:
            return False
        extension_atr = self._safe_float(entry_gate.get("extension_atr"), 0.0)
        if extension_atr > settings.entry_max_extension_atr:
            return False
        rank = self._safe_int(match.get("opportunity_rank"))
        rank_score = self._safe_float(match.get("opportunity_rank_score"), 0.0)
        entry_score = self._safe_float(entry_gate.get("entry_score", match.get("entry_score")), 0.0)
        if entry_score < max(LAB_NEAR_MISS_MIN_ENTRY_SCORE, settings.entry_min_score):
            return False
        if rank_score < LAB_NEAR_MISS_MIN_RANK_SCORE:
            return False
        top_ranked = rank is not None and rank <= LAB_NEAR_MISS_TOP_RANK_LIMIT
        return top_ranked or rank_score >= LAB_NEAR_MISS_HIGH_RANK_SCORE

    @staticmethod
    def _entry_gate_reasons(entry_gate: dict[str, Any]) -> list[str]:
        reasons = entry_gate.get("rejection_reasons")
        collected: list[str] = []
        if isinstance(reasons, list):
            collected.extend(str(reason).strip() for reason in reasons if str(reason).strip())
        reason = str(entry_gate.get("reason") or "").strip()
        if reason and reason not in {"entry gate failed", "entry gate passed"}:
            collected.extend(part.strip() for part in reason.replace(",", ";").split(";") if part.strip())
        if entry_gate.get("volume_confirmed") is False:
            collected.append("insufficient_volume")
        deduped: list[str] = []
        for reason_item in collected:
            if reason_item not in deduped:
                deduped.append(reason_item)
        return deduped

    @staticmethod
    def _safe_float(value: Any, default: float) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return number if math.isfinite(number) else default

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _mark_near_miss_shadow_match(
        match: dict[str, Any],
        reasons: list[str],
        *,
        near_miss_type: str = "volume_only_entry_gate_shadow",
        note: str = "entry gate failed only on soft volume confirmation.",
    ) -> dict[str, Any]:
        enriched = dict(match)
        metrics = dict(enriched.get("metrics") or {})
        entry_gate = dict(metrics.get("entry_gate") or {})
        entry_gate["near_miss_shadow"] = True
        entry_gate["near_miss"] = True
        entry_gate["would_have_failed_entry_gate"] = True
        entry_gate["near_miss_reasons"] = reasons
        entry_gate["entry_gate_rejection_reasons"] = reasons
        metrics["entry_gate"] = entry_gate
        metrics["near_miss"] = True
        metrics["near_miss_shadow"] = True
        metrics["near_miss_reasons"] = reasons
        metrics["entry_gate_rejection_reasons"] = reasons
        metrics["would_have_failed_entry_gate"] = True
        metrics["paper_only"] = True
        metrics["no_ibkr_order"] = True
        metrics["evidence_type"] = EvidenceType.NEAR_MISS_SHADOW.value
        metrics["evidence_quality"] = EvidenceQuality.NORMAL.value
        enriched["metrics"] = metrics
        enriched["near_miss"] = True
        enriched["near_miss_shadow"] = True
        enriched["near_miss_shadow_candidate"] = True
        enriched["near_miss_type"] = near_miss_type
        enriched["near_miss_reasons"] = reasons
        enriched["entry_gate_rejection_reasons"] = reasons
        enriched["entry_gate_reason"] = str(entry_gate.get("reason") or ";".join(reasons))
        enriched["would_have_failed_entry_gate"] = True
        enriched["paper_only"] = True
        enriched["no_ibkr_order"] = True
        enriched["observation_only"] = True
        enriched["evidence_type"] = EvidenceType.NEAR_MISS_SHADOW.value
        enriched["evidence_quality"] = EvidenceQuality.NORMAL.value
        enriched["notes"] = (
            f"{enriched.get('notes', '')} Near-miss Lab shadow observation; {note}"
        ).strip()
        return enriched

    @staticmethod
    def _audit_entry_gate_rejection(
        db: Session,
        *,
        module: EntryModule,
        match: dict[str, Any],
        entry_gate: dict[str, Any],
    ) -> None:
        db.add(
            AuditLog(
                actor=module,
                action="entry_match_rejected_by_entry_gate",
                entity_type="discovered_pattern_match",
                entity_id=str(match.get("pattern_id", "")),
                details_json={"match": match, "entry_gate": entry_gate},
            )
        )
        db.commit()

    @staticmethod
    def _history_score(values: list[float]) -> float:
        if not values:
            return 0.5
        expectancy = sum(values) / len(values)
        wins = [value for value in values if value > 0]
        losses = [abs(value) for value in values if value < 0]
        win_rate = len(wins) / len(values)
        profit_factor = (sum(wins) / sum(losses)) if losses else (sum(wins) if wins else 0.0)
        profit_factor_score = max(0.0, min(1.0, profit_factor / 3.0))
        chronological = list(reversed(values))
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for value in chronological:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        drawdown_score = max(0.0, min(1.0, 1.0 - max_drawdown / 6.0))
        split = max(1, min(5, len(values) // 2 or 1))
        recent = values[:split]
        older = values[split:] or recent
        recent_expectancy = sum(recent) / len(recent)
        older_expectancy = sum(older) / len(older)
        decay_score = max(0.0, min(1.0, 0.5 + (recent_expectancy - older_expectancy) / 2.0))
        expectancy_score = max(0.0, min(1.0, 0.5 + expectancy / 2.0))
        raw_score = (
            expectancy_score * 0.35
            + win_rate * 0.20
            + profit_factor_score * 0.20
            + drawdown_score * 0.15
            + decay_score * 0.10
        )
        confidence = min(1.0, len(values) / 10.0)
        return round(0.5 * (1.0 - confidence) + raw_score * confidence, 6)

    def _history_item(self, values: list[float]) -> dict[str, float]:
        wins = [value for value in values if value > 0]
        losses = [abs(value) for value in values if value < 0]
        profit_factor = (sum(wins) / sum(losses)) if losses else (sum(wins) if wins else 0.0)
        chronological = list(reversed(values))
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for value in chronological:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        split = max(1, min(5, len(values) // 2 or 1))
        recent = values[:split]
        older = values[split:] or recent
        recent_expectancy = sum(recent) / len(recent)
        older_expectancy = sum(older) / len(older)
        decay_score = max(0.0, min(1.0, 0.5 + (recent_expectancy - older_expectancy) / 2.0))
        return {
            "score": self._history_score(values),
            "count": float(len(values)),
            "expectancy_r": round(sum(values) / len(values), 6) if values else 0.0,
            "win_rate": round(len(wins) / len(values), 6) if values else 0.0,
            "profit_factor": round(profit_factor, 6),
            "max_drawdown_r": round(max_drawdown, 6),
            "decay_score": round(decay_score, 6),
            "recent_expectancy_r": round(recent_expectancy, 6),
            "older_expectancy_r": round(older_expectancy, 6),
        }

    def _store_signal(
        self,
        db: Session,
        *,
        module: EntryModule,
        match: dict[str, Any],
        candidate: PatternCandidate,
        risk,
        execute_orders: bool,
        requested_execute_orders: bool,
        execution_degrade_reason: str | None,
        market_session: dict[str, Any] | None = None,
        entry_quality: dict[str, Any] | None = None,
    ):
        settings = self.settings
        assert settings is not None
        if module == "fox_hunter":
            status = (
                SignalStatus.LIVE_APPROVED
                if settings.live_armed and execute_orders
                else SignalStatus.PENDING_HUMAN_APPROVAL
            )
            human_approved = status == SignalStatus.LIVE_APPROVED
        else:
            status = SignalStatus.WATCHLIST if match.get("near_miss") else SignalStatus.PAPER_APPROVED
            human_approved = False if match.get("near_miss") else execute_orders
        entry_quality = entry_quality or build_entry_quality(
            match=match,
            risk=risk,
            settings=settings,
            execution_requested=execute_orders,
            market_session=market_session,
        )
        signal_snapshot = build_signal_snapshot(
            match=match,
            risk=risk,
            settings=settings,
            entry_quality=entry_quality,
            execution_requested=execute_orders,
            market_session=market_session,
        )
        spread_snapshot = capture_signal_spread_snapshot(
            symbol=candidate.symbol,
            entry=candidate.entry,
            stop=candidate.stop,
            settings=settings,
            provider=self.quote_provider,
        )
        evidence_type = self._signal_evidence_type(
            module,
            match=match,
            execute_orders=execute_orders,
        )
        no_order_reason = self._no_order_reason(
            module,
            match=match,
            requested_execute_orders=requested_execute_orders,
            execute_orders=execute_orders,
            execution_degrade_reason=execution_degrade_reason,
        )
        order_decision = self._order_decision_metadata(
            module,
            match=match,
            requested_execute_orders=requested_execute_orders,
            execute_orders=execute_orders,
            execution_degrade_reason=execution_degrade_reason,
        )
        execution_outcome = (
            {
                "status": "near_miss_shadow_observation",
                "reason_code": "entry_gate_volume_near_miss_shadow",
                "reason": (
                    "Entry gate failed only volume confirmation; Lab opened a "
                    "shadow observation with no IBKR order."
                ),
                "retryable": False,
                "next_action": "collect_shadow_outcome",
            }
            if match.get("near_miss")
            else None
        )
        if no_order_reason and execution_outcome is None:
            execution_outcome = {
                "status": "no_order_shadow_observation",
                "reason_code": no_order_reason,
                "reason": "Lab did not submit an IBKR Paper order for this signal.",
                "retryable": False,
                "next_action": "collect_shadow_outcome",
            }
        elif no_order_reason and execution_outcome is not None:
            execution_outcome["reason_code"] = no_order_reason
            execution_outcome["no_order_reason"] = no_order_reason
        signal = Signal(
            symbol=candidate.symbol,
            pattern=candidate.pattern,
            side=candidate.side,
            timeframe=candidate.timeframe,
            entry=candidate.entry,
            stop=candidate.stop,
            target=candidate.target,
            reward_risk=candidate.reward_risk,
            confidence=candidate.confidence,
            composite_score=candidate.composite_score,
            risk_usd=risk.risk_usd,
            suggested_qty=risk.suggested_qty,
            strategy_version=f"{module}_pattern_{match['pattern_id']}",
            status=status,
            supervisor_notes=str(match.get("notes", "")),
            human_approved=human_approved,
            metadata_json={
                "evidence_type": evidence_type,
                "evidence_quality": EvidenceQuality.NORMAL.value,
                "entry_module": module,
                "signal_idempotency_key": self._signal_idempotency_key(module, match),
                "bar_window_end": str(match.get("window_end") or ""),
                "pattern_id": match["pattern_id"],
                "pattern_key": match["pattern_key"],
                "pattern_family_key": match.get("pattern_family_key"),
                "canonical_pattern_key": match.get("canonical_pattern_key"),
                "pattern_status": match.get("pattern_status"),
                "pattern_promotion_status": match.get("pattern_promotion_status"),
                "production_manifest": match.get("production_manifest"),
                "entry_variant_id": match.get("entry_variant_id"),
                "entry_variant": match.get("entry_variant"),
                "entry_audit": match.get("entry_audit"),
                "regime": match.get("regime"),
                "regime_fit": match.get("regime_fit"),
                "opportunity_rank": match.get("opportunity_rank"),
                "opportunity_rank_score": match.get("opportunity_rank_score"),
                "opportunity_rank_components": match.get("opportunity_rank_components"),
                "opportunity_rank_reason": match.get("opportunity_rank_reason"),
                "entry_quality_score": entry_quality["score"],
                "entry_quality": entry_quality,
                "signal_snapshot": signal_snapshot,
                "spread_snapshot": spread_snapshot,
                "spread_observed_pct": spread_snapshot.get("spread_observed_pct"),
                "execution_requested": execute_orders,
                "requested_execute_orders": requested_execute_orders,
                "execution_request_mode": self._scan_execution_mode(
                    module,
                    execute_orders=execute_orders,
                ),
                "execution_degrade_reason": execution_degrade_reason,
                "order_decision": order_decision,
                "paper_order_requested": module == "laboratory" and execute_orders,
                "match": match,
                "entry_gate": match.get("metrics", {}).get("entry_gate"),
                "near_miss": bool(match.get("near_miss")),
                "near_miss_shadow": bool(match.get("near_miss_shadow")),
                "near_miss_type": match.get("near_miss_type"),
                "near_miss_reasons": match.get("near_miss_reasons") or [],
                "entry_gate_rejection_reasons": match.get("entry_gate_rejection_reasons") or [],
                "entry_gate_reason": match.get("entry_gate_reason"),
                "would_have_failed_entry_gate": bool(match.get("would_have_failed_entry_gate")),
                "observation_only": module == "laboratory" and not execute_orders,
                "execution_mode": self._signal_execution_mode(module, execute_orders=execute_orders),
                "paper_only": module == "laboratory" and not execute_orders,
                "no_ibkr_order": module == "laboratory" and not execute_orders,
                "no_order_reason": no_order_reason,
                "execution_outcome": execution_outcome,
                "risk": risk.model_dump(mode="json"),
                "director_audit_required": True,
            },
        )
        db.add(signal)
        db.add(
            AuditLog(
                actor=module,
                action="entry_signal_created",
                entity_type="signal",
                details_json={"signal": signal.metadata_json},
            )
        )
        db.commit()
        db.refresh(signal)
        return signal

    @staticmethod
    def _signal_execution_mode(module: EntryModule, *, execute_orders: bool) -> str | None:
        if module == "laboratory" and not execute_orders:
            return LAB_SHADOW_EXECUTION_MODE
        if execute_orders:
            return "ibkr"
        return None

    @staticmethod
    def _signal_evidence_type(
        module: EntryModule,
        *,
        match: dict[str, Any],
        execute_orders: bool,
    ) -> str | None:
        if module == "laboratory":
            if match.get("near_miss"):
                return EvidenceType.NEAR_MISS_SHADOW.value
            if not execute_orders:
                return EvidenceType.SHADOW_NO_ORDER.value
            return EvidenceType.IBKR_PAPER_ORDER.value
        if execute_orders:
            return EvidenceType.LIVE_ORDER.value
        return None

    @staticmethod
    def _execution_reason(module: EntryModule) -> str:
        if module == "fox_hunter":
            return "fox_hunter production live execution"
        return "laboratory IBKR paper validation"

    def _observation_service(self) -> LabPaperObservationService:
        provider = getattr(self.matcher, "provider", None)
        return LabPaperObservationService(settings=self.settings, provider=provider)

    def _close_lab_observations(self, db: Session, module: EntryModule) -> dict[str, Any]:
        if module != "laboratory":
            return {
                "open_observations": 0,
                "closed_observations": 0,
                "closed_trade_ids": [],
                "data_errors": [],
            }
        return self._observation_service().close_open_observations(db)

    def _open_lab_observation(
        self,
        db: Session,
        *,
        signal: Signal,
        match: dict[str, Any],
        risk,
    ) -> Trade | None:
        return self._observation_service().open_observation(
            db,
            signal=signal,
            match=match,
            risk=risk,
        )
