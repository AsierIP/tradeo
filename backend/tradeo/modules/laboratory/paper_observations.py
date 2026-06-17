from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session, joinedload

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, Signal, Trade, TradeStatus
from tradeo.services.evidence import (
    EvidenceQuality,
    EvidenceType,
    FillProvenance,
    LAB_SHADOW_EXECUTION_MODE,
    with_evidence_metadata,
)
from tradeo.research.quant_validation import triple_barrier_outcome
from tradeo.services.data_provider import MarketDataProvider
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.technical_indicators import normalize_ohlcv

# Map canonical triple-barrier reasons to the shadow lifecycle vocabulary.
# "stop_gap" / "target_gap" pass through unchanged: implementation-shortfall
# accounting already classifies them, and renaming them to *_hit would hide
# that the fill happened at the open, not at the barrier price.
CANONICAL_EXIT_REASON_MAP = {
    "stop": "stop_hit",
    "stop_and_target_conservative": "stop_hit",
    "stop_gap": "stop_gap",
    "target": "target_hit",
    "target_gap": "target_gap",
    "time": "time_stop",
}


@dataclass(slots=True)
class MarketDataFetch:
    frame: pd.DataFrame | None
    error: str | None = None


@dataclass(slots=True)
class FallbackFrame:
    frame: pd.DataFrame
    source: str
    timestamp_source: str


@dataclass(slots=True)
class LabPaperObservationService:
    """Open and evaluate laboratory paper observations without broker orders."""

    settings: Settings | None = None
    provider: MarketDataProvider | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()
        self.provider = self.provider or get_market_data_provider()

    def open_observation(
        self,
        db: Session,
        *,
        signal: Signal,
        match: dict[str, Any],
        risk: Any,
    ) -> Trade | None:
        if signal.id is None:
            return None
        existing = (
            db.query(Trade)
            .filter(Trade.signal_id == signal.id)
            .filter(Trade.status == TradeStatus.OPEN)
            .first()
        )
        if existing is not None:
            return existing
        qty = int(getattr(risk, "suggested_qty", 0) or signal.suggested_qty or 0)
        if qty <= 0:
            return None
        now = datetime.now(timezone.utc)
        signal_metadata = signal.metadata_json or {}
        entry_gate = signal_metadata.get("entry_gate") or (match.get("metrics") or {}).get("entry_gate")
        entry_quality = signal_metadata.get("entry_quality") or {}
        near_miss = bool(signal_metadata.get("near_miss") or match.get("near_miss"))
        no_order_reason = (
            signal_metadata.get("no_order_reason")
            or signal_metadata.get("execution_degrade_reason")
            or ("near_miss_shadow" if near_miss else "paper_order_submission_disabled")
        )
        order_decision = signal_metadata.get("order_decision") if isinstance(signal_metadata.get("order_decision"), dict) else {}
        evidence_type = (
            EvidenceType.NEAR_MISS_SHADOW.value
            if near_miss
            else EvidenceType.SHADOW_NO_ORDER.value
        )
        metadata = {
            "evidence_type": evidence_type,
            "evidence_quality": EvidenceQuality.NORMAL.value,
            "fill_provenance": FillProvenance.SHADOW_CLOSE.value,
            "execution_mode": LAB_SHADOW_EXECUTION_MODE,
            "entry_module": "laboratory",
            "source_module": "laboratory",
            "observation_only": True,
            "no_ibkr_order": True,
            "no_order_reason": no_order_reason,
            "order_decision": {
                **order_decision,
                "submitted_to_broker": False,
                "no_order_reason": no_order_reason,
            },
            "entry_variant_id": signal_metadata.get("entry_variant_id") or match.get("entry_variant_id"),
            "entry_variant": signal_metadata.get("entry_variant") or match.get("entry_variant"),
            "pattern_id": signal_metadata.get("pattern_id") or match.get("pattern_id"),
            "pattern_key": signal_metadata.get("pattern_key") or match.get("pattern_key"),
            "regime": signal_metadata.get("regime") or match.get("regime"),
            "regime_fit": signal_metadata.get("regime_fit") or match.get("regime_fit"),
            "entry_gate": entry_gate,
            "entry_quality": entry_quality,
            "entry_audit": signal_metadata.get("entry_audit") or match.get("entry_audit"),
            "opportunity_rank": signal_metadata.get("opportunity_rank") or match.get("opportunity_rank"),
            "opportunity_rank_score": signal_metadata.get("opportunity_rank_score") or match.get("opportunity_rank_score"),
            "opportunity_rank_components": signal_metadata.get("opportunity_rank_components")
            or match.get("opportunity_rank_components"),
            "near_miss": near_miss,
            "near_miss_shadow": bool(signal_metadata.get("near_miss_shadow") or match.get("near_miss_shadow")),
            "near_miss_type": signal_metadata.get("near_miss_type") or match.get("near_miss_type"),
            "near_miss_reasons": signal_metadata.get("near_miss_reasons") or match.get("near_miss_reasons") or [],
            "entry_gate_rejection_reasons": signal_metadata.get("entry_gate_rejection_reasons")
            or match.get("entry_gate_rejection_reasons")
            or [],
            "entry_gate_reason": signal_metadata.get("entry_gate_reason") or match.get("entry_gate_reason"),
            "would_have_failed_entry_gate": bool(
                signal_metadata.get("would_have_failed_entry_gate") or match.get("would_have_failed_entry_gate")
            ),
            "paper_only": True,
            "opened_reason": (
                (
                    "lab_near_miss_ambiguous_match_shadow_observation"
                    if str(
                        signal_metadata.get("near_miss_type") or match.get("near_miss_type") or ""
                    )
                    == "ambiguous_match_shadow"
                    else "lab_near_miss_volume_shadow_observation"
                )
                if near_miss
                else "lab_entry_candidate_shadow_observation"
            ),
            "entry_fill_time": now.isoformat(),
            "entry_fill_price": signal.entry,
            "entry_order_type": "shadow_observation",
            "signal_snapshot": signal_metadata.get("signal_snapshot") or match.get("signal_snapshot"),
            "match": signal_metadata.get("match") or match,
            "commission": 0.0,
            "estimated_spread_cost": 0.0,
            "estimated_slippage": 0.0,
            "other_fees": 0.0,
        }
        trade = Trade(
            signal_id=signal.id,
            symbol=signal.symbol,
            pattern=signal.pattern,
            side=signal.side,
            qty=qty,
            entry=signal.entry,
            stop=signal.stop,
            target=signal.target,
            status=TradeStatus.OPEN,
            opened_at=now,
            evidence_type=evidence_type,
            evidence_quality=EvidenceQuality.NORMAL.value,
            metadata_json=metadata,
        )
        db.add(trade)
        db.add(
            AuditLog(
                actor="laboratory",
                action="lab_shadow_observation_opened",
                entity_type="trade",
                entity_id=str(signal.id),
                details_json={
                    "signal_id": signal.id,
                    "symbol": signal.symbol,
                    "pattern": signal.pattern,
                    "entry_variant_id": match.get("entry_variant_id"),
                    "near_miss": near_miss,
                    "evidence_type": evidence_type,
                    "evidence_quality": EvidenceQuality.NORMAL.value,
                    "no_ibkr_order": True,
                    "no_order_reason": no_order_reason,
                },
            )
        )
        db.commit()
        db.refresh(trade)
        return trade

    def close_open_observations(self, db: Session) -> dict[str, Any]:
        trades = (
            db.query(Trade)
            .options(joinedload(Trade.signal))
            .filter(Trade.status == TradeStatus.OPEN)
            .order_by(Trade.opened_at.asc())
            .limit(500)
            .all()
        )
        observations = [trade for trade in trades if self._is_lab_shadow_observation(trade)]
        closed_ids: list[int] = []
        diagnosed_ids: list[int] = []
        data_errors: list[dict[str, str]] = []
        frame_cache: dict[tuple[str, str], MarketDataFetch] = {}
        for trade in observations:
            signal = trade.signal
            timeframe = signal.timeframe if signal is not None else "1d"
            key = (trade.symbol.upper(), timeframe)
            if key not in frame_cache:
                frame_cache[key] = self._fetch_frame(trade.symbol, timeframe)
            fetch = frame_cache[key]
            frame = fetch.frame
            fallback: FallbackFrame | None = None
            if frame is None:
                fallback = self._fallback_frame_from_metadata(trade)
                if fallback is None:
                    diagnostic = self._mark_observation_pending(
                        db,
                        trade,
                        frame=None,
                        reason=fetch.error or "market_data_unavailable",
                        status="market_data_unavailable",
                        fallback=None,
                    )
                    diagnosed_ids.append(trade.id)
                    data_errors.append(diagnostic)
                    continue
                frame = fallback.frame
            outcome = self._evaluate_trade(trade, frame)
            if outcome is None:
                diagnostic = self._mark_observation_pending(
                    db,
                    trade,
                    frame=frame,
                    reason=fetch.error or "awaiting_future_market_bars",
                    status="market_data_unavailable" if fetch.error else "awaiting_future_market_bars",
                    fallback=fallback,
                )
                diagnosed_ids.append(trade.id)
                if fetch.error:
                    data_errors.append(diagnostic)
                continue
            self._close_trade(db, trade, outcome, fallback=fallback)
            closed_ids.append(trade.id)
        if closed_ids or diagnosed_ids:
            db.commit()
        return {
            "open_observations": len(observations) - len(closed_ids),
            "closed_observations": len(closed_ids),
            "closed_trade_ids": closed_ids,
            "diagnosed_observations": len(diagnosed_ids),
            "diagnosed_trade_ids": diagnosed_ids,
            "data_errors": data_errors,
        }

    @staticmethod
    def _is_lab_shadow_observation(trade: Trade) -> bool:
        metadata = trade.metadata_json or {}
        if str(metadata.get("execution_mode") or "") == LAB_SHADOW_EXECUTION_MODE:
            return True
        signal = trade.signal
        if signal is None:
            return False
        signal_meta = signal.metadata_json or {}
        return (
            signal_meta.get("entry_module") == "laboratory"
            and bool(metadata.get("observation_only"))
            and bool(metadata.get("no_ibkr_order"))
        )

    def _fetch_frame(self, symbol: str, timeframe: str) -> MarketDataFetch:
        assert self.provider is not None
        try:
            frame = normalize_ohlcv(self.provider.fetch_ohlcv(symbol, period="6mo", interval=timeframe))
            if frame.empty:
                return MarketDataFetch(None, "provider_returned_no_bars")
            return MarketDataFetch(frame)
        except Exception as exc:  # noqa: BLE001
            logger.warning("lab shadow observation data fetch failed for {} / {}: {}", symbol, timeframe, exc)
            return MarketDataFetch(None, f"provider_fetch_failed: {type(exc).__name__}: {exc}")

    def _evaluate_trade(self, trade: Trade, frame: pd.DataFrame) -> dict[str, Any] | None:
        """Evaluate a shadow observation with the canonical triple-barrier engine.

        Parity contract (informe §6): shadow exits use the same fill rules as
        the backtester and Research RR simulation (`triple_barrier_outcome`),
        instead of an ad-hoc loop that filled gapped stops at the stop price.

        Construction: the shadow position exists from `opened_at` at
        `trade.entry`, before the first future bar. Two synthetic bars pinned
        at the entry price (signal bar + entry bar) precede the future bars so
        every real bar is "posterior to entry" and the canonical open-gap
        rules (fill at the OPEN through a stop, at the TARGET through a
        target) apply to all of them, including the first.
        """
        opened_at = self._as_utc(trade.opened_at)
        future = frame[[self._as_utc(idx) > opened_at for idx in frame.index]]
        if future.empty:
            return None
        side = -1 if trade.side.lower().strip() == "short" else 1
        entry = float(trade.entry)
        risk = abs(entry - float(trade.stop))
        if risk <= 0:
            return None
        max_holding_bars = max(1, max(self.settings.discovery_forward_bar_list if self.settings else [20]))
        synthetic = [entry, entry]
        out = triple_barrier_outcome(
            synthetic + future["open"].astype(float).tolist(),
            synthetic + future["high"].astype(float).tolist(),
            synthetic + future["low"].astype(float).tolist(),
            synthetic + future["close"].astype(float).tolist(),
            signal_index=0,
            side=side,
            stop_price=float(trade.stop),
            target_price=float(trade.target),
            # +1: the synthetic entry bar consumes the first slot of the window
            max_bars=max_holding_bars + 1,
            entry_price=entry,
            gap_entry_policy="skip",
            conservative_both=True,
            round_trip_cost_R=0.0,
        )
        if out["status"] != "ok":
            # 'skipped'/'invalid' only occur for malformed barriers (entry at
            # or beyond stop/target); keep the observation pending so the
            # diagnostic path surfaces it instead of fabricating an exit.
            return None
        reason = str(out["reason"])
        if reason == "time" and len(future) < max_holding_bars:
            return None
        exit_pos = max(0, min(int(out["exit_index"]) - len(synthetic), len(future) - 1))
        rows_seen = [row.to_dict() for _, row in future.iloc[: exit_pos + 1].iterrows()]
        return {
            "exit_price": float(out["exit_price"]),
            "closed_at": self._as_utc(future.index[exit_pos]),
            "exit_reason": CANONICAL_EXIT_REASON_MAP.get(reason, reason),
            "bars": rows_seen,
            "canonical_outcome": {
                "engine": "triple_barrier_outcome",
                "status": str(out["status"]),
                "reason": reason,
                "r_multiple": round(float(out["R"]), 6),
                "mfe_R": round(float(out["mfe_R"]), 6),
                "mae_R": round(float(out["mae_R"]), 6),
                "bars_held": max(0, int(out["bars_held"]) - 1),
                "conservative_both": True,
                "gap_entry_policy": "skip",
                "round_trip_cost_R": 0.0,
            },
        }

    def _close_trade(
        self,
        db: Session,
        trade: Trade,
        outcome: dict[str, Any],
        *,
        fallback: FallbackFrame | None = None,
    ) -> None:
        exit_price = float(outcome["exit_price"])
        risk = abs(float(trade.entry) - float(trade.stop))
        if trade.side.lower().strip() == "short":
            pnl = (float(trade.entry) - exit_price) * int(trade.qty)
            r_multiple = (float(trade.entry) - exit_price) / max(risk, 1e-9)
        else:
            pnl = (exit_price - float(trade.entry)) * int(trade.qty)
            r_multiple = (exit_price - float(trade.entry)) / max(risk, 1e-9)
        closed_at = outcome["closed_at"]
        metadata = with_evidence_metadata(
            trade.metadata_json or {},
            trade_status=TradeStatus.CLOSED,
            evidence_quality=EvidenceQuality.DEGRADED.value if fallback is not None else None,
            fill_provenance=FillProvenance.SHADOW_CLOSE.value,
            degradation_reason=(
                f"fallback_market_data:{fallback.source}" if fallback is not None else None
            ),
        )
        bars = outcome.get("bars") or []
        mfe, mae = self._mfe_mae_r(trade, bars)
        metadata.update(
            {
                "evidence_quality": (
                    EvidenceQuality.DEGRADED.value
                    if fallback is not None
                    else metadata.get("evidence_quality", EvidenceQuality.NORMAL.value)
                ),
                "fallback_used": fallback is not None,
                "fallback_source": fallback.source if fallback is not None else None,
                "fallback_timestamp_source": fallback.timestamp_source if fallback is not None else None,
                "exit_reason": outcome["exit_reason"],
                "exit_fill_time": closed_at.isoformat(),
                "exit_fill_price": round(exit_price, 4),
                "exit_order_type": "shadow_observation_exit",
                "gross_pnl": round(pnl, 4),
                "net_pnl": round(pnl, 4),
                "mfe": round(mfe, 6),
                "mae": round(mae, 6),
                "holding_period_seconds": int((closed_at - self._as_utc(trade.opened_at)).total_seconds()),
                "closed_by": "lab_shadow_observation_lifecycle",
                "canonical_outcome": outcome.get("canonical_outcome"),
            }
        )
        trade.status = TradeStatus.CLOSED
        trade.closed_at = closed_at
        trade.exit_price = round(exit_price, 4)
        trade.pnl_usd = round(pnl, 4)
        trade.r_multiple = round(r_multiple, 6)
        trade.evidence_type = metadata.get("evidence_type")
        trade.evidence_quality = metadata.get("evidence_quality")
        trade.metadata_json = metadata
        db.add(trade)
        db.add(
            AuditLog(
                actor="laboratory",
                action="lab_shadow_observation_closed",
                entity_type="trade",
                entity_id=str(trade.id),
                details_json={
                    "trade_id": trade.id,
                    "symbol": trade.symbol,
                    "exit_reason": outcome["exit_reason"],
                    "r_multiple": trade.r_multiple,
                    "evidence_type": metadata.get("evidence_type"),
                    "evidence_quality": metadata.get("evidence_quality"),
                    "fallback_used": fallback is not None,
                    "no_ibkr_order": True,
                },
            )
        )

    def _mark_observation_pending(
        self,
        db: Session,
        trade: Trade,
        *,
        frame: pd.DataFrame | None,
        reason: str,
        status: str,
        fallback: FallbackFrame | None,
    ) -> dict[str, str]:
        now = datetime.now(timezone.utc)
        metadata = with_evidence_metadata(
            trade.metadata_json or {},
            evidence_quality=EvidenceQuality.DEGRADED.value if fallback is not None else None,
            degradation_reason=(
                f"fallback_market_data:{fallback.source}" if fallback is not None else None
            ),
        )
        last_bar = self._last_bar_snapshot(frame)
        mark = self._mark_to_market(trade, last_bar)
        lifecycle = {
            "status": status,
            "reason": reason,
            "diagnosed_at": now.isoformat(),
            "fallback_used": fallback is not None,
            "fallback_source": fallback.source if fallback is not None else None,
            "fallback_timestamp_source": fallback.timestamp_source if fallback is not None else None,
            "last_bar": last_bar,
            "mark_to_market": mark,
            "no_ibkr_order": True,
            "paper_only": True,
        }
        metadata.update(
            {
                "shadow_lifecycle": lifecycle,
                "last_shadow_lifecycle_status": status,
                "market_data_unavailable": status == "market_data_unavailable",
                "market_data_unavailable_reason": reason if status == "market_data_unavailable" else None,
                "evidence_quality": (
                    EvidenceQuality.DEGRADED.value
                    if fallback is not None
                    else metadata.get("evidence_quality", EvidenceQuality.NORMAL.value)
                ),
                "fallback_used": fallback is not None,
                "fallback_source": fallback.source if fallback is not None else None,
                "fallback_timestamp_source": fallback.timestamp_source if fallback is not None else None,
                "no_ibkr_order": True,
                "paper_only": True,
            }
        )
        trade.metadata_json = metadata
        trade.evidence_type = metadata.get("evidence_type")
        trade.evidence_quality = metadata.get("evidence_quality")
        db.add(trade)
        db.add(
            AuditLog(
                actor="laboratory",
                action=(
                    "lab_shadow_observation_market_data_unavailable"
                    if status == "market_data_unavailable"
                    else "lab_shadow_observation_pending_bars"
                ),
                entity_type="trade",
                entity_id=str(trade.id),
                details_json={
                    "trade_id": trade.id,
                    "symbol": trade.symbol,
                    "status": status,
                    "reason": reason,
                    "fallback_used": fallback is not None,
                    "fallback_source": fallback.source if fallback is not None else None,
                    "mark_to_market": mark,
                    "no_ibkr_order": True,
                },
            )
        )
        return {
            "trade_id": str(trade.id),
            "symbol": trade.symbol,
            "reason": reason,
            "status": status,
            "diagnosed_at": now.isoformat(),
            "fallback_used": str(fallback is not None).lower(),
        }

    def _fallback_frame_from_metadata(self, trade: Trade) -> FallbackFrame | None:
        candidate = self._last_market_bar_candidate(trade)
        if candidate is None:
            return None
        price = self._safe_positive_float(candidate.get("close") or candidate.get("price"))
        if price is None:
            return None
        open_price = self._safe_positive_float(candidate.get("open")) or price
        high = max(self._safe_positive_float(candidate.get("high")) or price, open_price, price)
        low = min(self._safe_positive_float(candidate.get("low")) or price, open_price, price)
        volume = self._safe_non_negative_float(candidate.get("volume")) or 0.0
        timestamp = self._timestamp_or_opened_at(candidate.get("timestamp"), trade.opened_at)
        frame = pd.DataFrame(
            {
                "open": [open_price],
                "high": [high],
                "low": [low],
                "close": [price],
                "volume": [volume],
            },
            index=pd.DatetimeIndex([timestamp]),
        )
        return FallbackFrame(
            frame=normalize_ohlcv(frame),
            source=str(candidate.get("source") or "metadata"),
            timestamp_source=str(candidate.get("timestamp_source") or "opened_at"),
        )

    def _last_market_bar_candidate(self, trade: Trade) -> dict[str, Any] | None:
        metadata = trade.metadata_json or {}
        signal_meta = (trade.signal.metadata_json if trade.signal is not None else {}) or {}
        sources = [
            ("trade.metadata_json", metadata),
            ("signal.metadata_json", signal_meta),
            ("trade.signal_snapshot", metadata.get("signal_snapshot")),
            ("signal.signal_snapshot", signal_meta.get("signal_snapshot")),
            ("trade.match", metadata.get("match")),
            ("signal.match", signal_meta.get("match")),
        ]
        for source_name, payload in sources:
            candidate = self._bar_from_payload(payload, source_name)
            if candidate is not None:
                return candidate
        return None

    def _bar_from_payload(self, payload: Any, source_name: str) -> dict[str, Any] | None:
        if not isinstance(payload, dict):
            return None
        for key in ("last_bar", "latest_bar", "market_bar", "bar", "ohlcv"):
            bar = payload.get(key)
            if isinstance(bar, dict) and self._safe_positive_float(bar.get("close") or bar.get("price")) is not None:
                return {
                    **bar,
                    "source": f"{source_name}.{key}",
                    "timestamp": bar.get("timestamp") or bar.get("time") or bar.get("date"),
                    "timestamp_source": f"{source_name}.{key}",
                }
        entry_gate = payload.get("entry_gate")
        if isinstance(entry_gate, dict):
            price = self._safe_positive_float(entry_gate.get("close") or entry_gate.get("last_close"))
            if price is not None:
                return {
                    "price": price,
                    "open": entry_gate.get("open"),
                    "high": entry_gate.get("high"),
                    "low": entry_gate.get("low"),
                    "volume": entry_gate.get("volume"),
                    "timestamp": self._first_present(
                        entry_gate.get("timestamp"),
                        entry_gate.get("bar_close_time"),
                        entry_gate.get("decision_ts"),
                        entry_gate.get("available_data_cutoff_ts"),
                    ),
                    "source": f"{source_name}.entry_gate.close",
                    "timestamp_source": f"{source_name}.entry_gate",
                }
        features = payload.get("features")
        if isinstance(features, dict):
            price = self._safe_positive_float(features.get("last_close") or features.get("close"))
            if price is not None:
                return {
                    "price": price,
                    "timestamp": self._snapshot_timestamp(payload),
                    "source": f"{source_name}.features.last_close",
                    "timestamp_source": f"{source_name}.captured_at",
                }
        metrics = payload.get("metrics")
        if isinstance(metrics, dict):
            return self._bar_from_payload(metrics, f"{source_name}.metrics")
        snapshot = payload.get("signal_snapshot")
        if isinstance(snapshot, dict):
            return self._bar_from_payload(snapshot, f"{source_name}.signal_snapshot")
        return None

    def _last_bar_snapshot(self, frame: pd.DataFrame | None) -> dict[str, Any] | None:
        if frame is None or frame.empty:
            return None
        idx = frame.index[-1]
        row = frame.iloc[-1]
        return {
            "timestamp": self._as_utc(idx).isoformat(),
            "open": round(float(row["open"]), 4),
            "high": round(float(row["high"]), 4),
            "low": round(float(row["low"]), 4),
            "close": round(float(row["close"]), 4),
            "volume": round(float(row["volume"]), 4),
        }

    def _mark_to_market(self, trade: Trade, last_bar: dict[str, Any] | None) -> dict[str, Any] | None:
        if last_bar is None:
            return None
        last_price = self._safe_positive_float(last_bar.get("close"))
        if last_price is None:
            return None
        risk = abs(float(trade.entry) - float(trade.stop))
        qty = int(trade.qty)
        if trade.side.lower().strip() == "short":
            unrealized = (float(trade.entry) - last_price) * qty
            r_multiple = (float(trade.entry) - last_price) / max(risk, 1e-9)
        else:
            unrealized = (last_price - float(trade.entry)) * qty
            r_multiple = (last_price - float(trade.entry)) / max(risk, 1e-9)
        return {
            "price": round(last_price, 4),
            "unrealized_pnl": round(unrealized, 4),
            "unrealized_r": round(r_multiple, 6),
            "entry": round(float(trade.entry), 4),
            "stop": round(float(trade.stop), 4),
            "target": round(float(trade.target), 4),
            "qty": qty,
        }

    @staticmethod
    def _mfe_mae_r(trade: Trade, bars: list[dict[str, Any]]) -> tuple[float, float]:
        risk = abs(float(trade.entry) - float(trade.stop))
        if risk <= 0 or not bars:
            return 0.0, 0.0
        highs = [float(row["high"]) for row in bars]
        lows = [float(row["low"]) for row in bars]
        if trade.side.lower().strip() == "short":
            mfe = (float(trade.entry) - min(lows)) / risk
            mae = (float(trade.entry) - max(highs)) / risk
        else:
            mfe = (max(highs) - float(trade.entry)) / risk
            mae = (min(lows) - float(trade.entry)) / risk
        return mfe, mae

    @staticmethod
    def _as_utc(value: Any) -> datetime:
        ts = pd.Timestamp(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize(timezone.utc)
        else:
            ts = ts.tz_convert(timezone.utc)
        return ts.to_pydatetime()

    @staticmethod
    def _safe_positive_float(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not pd.notna(number) or number <= 0:
            return None
        return number

    @staticmethod
    def _safe_non_negative_float(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not pd.notna(number) or number < 0:
            return None
        return number

    @staticmethod
    def _timestamp_or_opened_at(value: Any, opened_at: Any) -> datetime:
        if value is None or value == "":
            return LabPaperObservationService._as_utc(opened_at)
        try:
            return LabPaperObservationService._as_utc(value)
        except Exception:  # noqa: BLE001
            return LabPaperObservationService._as_utc(opened_at)

    @staticmethod
    def _first_present(*values: Any) -> Any:
        for value in values:
            if value not in (None, ""):
                return value
        return None

    @staticmethod
    def _snapshot_timestamp(payload: dict[str, Any]) -> Any:
        entry_audit = payload.get("entry_audit") if isinstance(payload.get("entry_audit"), dict) else {}
        return LabPaperObservationService._first_present(
            payload.get("captured_at"),
            entry_audit.get("available_data_cutoff_ts"),
            entry_audit.get("decision_ts"),
            payload.get("window_end"),
        )
