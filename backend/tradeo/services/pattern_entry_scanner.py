from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy.orm import Session, joinedload

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, Signal, SignalStatus, Trade, TradeStatus
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.schemas import PatternCandidate
from tradeo.services.ibkr_broker import IBKRBroker
from tradeo.services.lab_paper_observations import LabPaperObservationService
from tradeo.services.market_session import market_session_status
from tradeo.services.order_outcomes import mark_signal_order_failure
from tradeo.services.opportunity_ranking import rank_entry_matches
from tradeo.services.risk_manager import RiskManager
from tradeo.services.signal_quality import build_entry_quality, build_signal_snapshot

EntryModule = Literal["laboratory", "fox_hunter"]


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
            similarity_threshold=similarity_threshold,
            store_signals=store_signals,
            execute_orders=execute_orders,
        )
        observation_lifecycle = self._close_lab_observations(db, module)
        session = market_session_status()
        if self._requires_market_hours(module) and not bool(session["regular_session_open"]):
            result = self._market_closed_result(module, resolved, session)
            result["paper_observations_opened"] = 0
            result["paper_observations_closed"] = observation_lifecycle["closed_observations"]
            result["paper_observation_trade_ids"] = []
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
        rejected_by_risk = 0
        order_errors: list[dict[str, Any]] = []
        signal_ids: list[int] = []
        trade_ids: list[int] = []
        paper_observation_trade_ids: list[int] = []
        paper_observations_opened = 0

        all_ranked_matches = rank_entry_matches(
            match_result["matches"],
            settings=settings,
            execution_history=self._execution_history(db, module),
        )
        ranked_matches = self._select_best_variant_per_exposure(all_ranked_matches)

        for match in ranked_matches:
            entry_gate = ((match.get("metrics") or {}).get("entry_gate") or {})
            if settings.entry_gate_enabled and not bool(entry_gate.get("passed", False)):
                rejected_by_entry_gate += 1
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
                continue
            if self._has_active_exposure(db, match, module=module):
                skipped_duplicates += 1
                continue
            if self._has_recent_signal(db, match, module=module):
                skipped_cooldown += 1
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
            risk = RiskManager(settings).validate_candidate(candidate, db)
            if not risk.approved:
                rejected_by_risk += 1
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
            if entry_quality["score"] < settings.entry_min_quality_score or entry_quality["flags"]:
                rejected_by_entry_quality += 1
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
            if not resolved["store_signals"]:
                continue

            signal = self._store_signal(
                db,
                module=module,
                match=match,
                candidate=candidate,
                risk=risk,
                execute_orders=bool(resolved["execute_orders"]),
                market_session=session,
                entry_quality=entry_quality,
            )
            signals_created += 1
            signal_ids.append(signal.id)

            if not resolved["execute_orders"]:
                if module == "laboratory":
                    observation = self._open_lab_observation(
                        db,
                        signal=signal,
                        match=match,
                        risk=risk,
                    )
                    if observation is not None:
                        paper_observations_opened += 1
                        paper_observation_trade_ids.append(observation.id)
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
            "rejected_by_risk": rejected_by_risk,
            "order_errors": order_errors,
            "signal_ids": signal_ids,
            "trade_ids": trade_ids,
            "paper_observations_opened": paper_observations_opened,
            "paper_observations_closed": observation_lifecycle["closed_observations"],
            "paper_observation_trade_ids": paper_observation_trade_ids,
            "paper_observation_lifecycle": observation_lifecycle,
            "top_opportunities": self._top_opportunities(ranked_matches),
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
        production_patterns = (
            db.query(DiscoveredPattern)
            .filter(DiscoveredPattern.validation_passed.is_(True))
            .filter(DiscoveredPattern.status == DiscoveredPatternStatus.PRODUCTION)
            .count()
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
                "eligible_patterns": laboratory_patterns,
                "symbols_checked": laboratory_entry_status["symbols_checked"],
                "last_symbols_checked": laboratory_entry_status["last_symbols_checked"],
            },
            "fox_hunter": {
                "purpose": "live_trade_production_patterns",
                "enabled": settings.fox_hunter_enabled,
                "operational_ok": fox_hunter_ok,
                "state": fox_state,
                "market_session": session,
                "worker": worker_status,
                "auto_submit_live_orders": settings.fox_hunter_auto_submit_live_orders,
                "eligible_patterns": production_patterns,
                "symbols_checked": fox_entry_status["symbols_checked"],
                "last_symbols_checked": fox_entry_status["last_symbols_checked"],
                "live_armed": settings.live_armed,
            },
        }

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
            "rejected_by_risk": 0,
            "order_errors": [],
            "signal_ids": [],
            "trade_ids": [],
            "paper_observations_opened": 0,
            "paper_observations_closed": 0,
            "paper_observation_trade_ids": [],
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

    def _resolved_options(self, module: EntryModule, **overrides: Any) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        if module == "fox_hunter":
            defaults = {
                "limit": settings.fox_hunter_symbol_limit,
                "max_patterns": settings.fox_hunter_max_patterns,
                "similarity_threshold": settings.fox_hunter_similarity_threshold,
                "store_signals": settings.fox_hunter_store_signals,
                "execute_orders": settings.fox_hunter_auto_submit_live_orders,
            }
        else:
            defaults = {
                "limit": settings.laboratory_symbol_limit,
                "max_patterns": settings.laboratory_max_patterns,
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

    def _candidate_from_match(self, match: dict[str, Any]) -> PatternCandidate:
        metrics = match.get("metrics") or {}
        features = dict(metrics.get("features") or {})
        features["entry_variant_id"] = str(match.get("entry_variant_id") or "")
        features["regime_key"] = str((match.get("regime") or {}).get("regime_key") or "")
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
            status = SignalStatus.PAPER_APPROVED
            human_approved = execute_orders
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
                "entry_module": module,
                "pattern_id": match["pattern_id"],
                "pattern_key": match["pattern_key"],
                "pattern_status": match.get("pattern_status"),
                "pattern_promotion_status": match.get("pattern_promotion_status"),
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
                "match": match,
                "entry_gate": match.get("metrics", {}).get("entry_gate"),
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
