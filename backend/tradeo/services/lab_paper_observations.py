from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from loguru import logger
from sqlalchemy.orm import Session, joinedload

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import AuditLog, Signal, Trade, TradeStatus
from tradeo.services.data_provider import MarketDataProvider
from tradeo.services.provider_factory import get_market_data_provider
from tradeo.services.technical_indicators import normalize_ohlcv

LAB_SHADOW_EXECUTION_MODE = "lab_shadow_observation"


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
        metadata = {
            "execution_mode": LAB_SHADOW_EXECUTION_MODE,
            "source_module": "laboratory",
            "observation_only": True,
            "no_ibkr_order": True,
            "entry_variant_id": match.get("entry_variant_id"),
            "entry_variant": match.get("entry_variant"),
            "pattern_id": match.get("pattern_id"),
            "pattern_key": match.get("pattern_key"),
            "regime": match.get("regime"),
            "regime_fit": match.get("regime_fit"),
            "entry_audit": match.get("entry_audit"),
            "opportunity_rank": match.get("opportunity_rank"),
            "opportunity_rank_score": match.get("opportunity_rank_score"),
            "opportunity_rank_components": match.get("opportunity_rank_components"),
            "near_miss": bool(match.get("near_miss")),
            "near_miss_shadow": bool(match.get("near_miss_shadow")),
            "near_miss_reasons": match.get("near_miss_reasons") or [],
            "would_have_failed_entry_gate": bool(match.get("would_have_failed_entry_gate")),
            "paper_only": True,
            "opened_reason": "lab_entry_candidate_shadow_observation",
            "entry_fill_time": now.isoformat(),
            "entry_fill_price": signal.entry,
            "entry_order_type": "shadow_observation",
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
                    "no_ibkr_order": True,
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
        data_errors: list[dict[str, str]] = []
        frame_cache: dict[tuple[str, str], pd.DataFrame | None] = {}
        for trade in observations:
            signal = trade.signal
            timeframe = signal.timeframe if signal is not None else "1d"
            key = (trade.symbol.upper(), timeframe)
            if key not in frame_cache:
                frame_cache[key] = self._fetch_frame(trade.symbol, timeframe)
            frame = frame_cache[key]
            if frame is None:
                data_errors.append({"symbol": trade.symbol, "reason": "market_data_unavailable"})
                continue
            outcome = self._evaluate_trade(trade, frame)
            if outcome is None:
                continue
            self._close_trade(db, trade, outcome)
            closed_ids.append(trade.id)
        if closed_ids:
            db.commit()
        return {
            "open_observations": len(observations) - len(closed_ids),
            "closed_observations": len(closed_ids),
            "closed_trade_ids": closed_ids,
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

    def _fetch_frame(self, symbol: str, timeframe: str) -> pd.DataFrame | None:
        assert self.provider is not None
        try:
            return normalize_ohlcv(self.provider.fetch_ohlcv(symbol, period="6mo", interval=timeframe))
        except Exception as exc:  # noqa: BLE001
            logger.warning("lab shadow observation data fetch failed for {} / {}: {}", symbol, timeframe, exc)
            return None

    def _evaluate_trade(self, trade: Trade, frame: pd.DataFrame) -> dict[str, Any] | None:
        opened_at = self._as_utc(trade.opened_at)
        future = frame[[self._as_utc(idx) > opened_at for idx in frame.index]]
        if future.empty:
            return None
        side = trade.side.lower().strip()
        risk = abs(float(trade.entry) - float(trade.stop))
        if risk <= 0:
            return None
        max_holding_bars = max(1, max(self.settings.discovery_forward_bar_list if self.settings else [20]))
        rows_seen: list[dict[str, Any]] = []
        for idx, row in future.iterrows():
            rows_seen.append(row.to_dict())
            high = float(row["high"])
            low = float(row["low"])
            if side == "short":
                stop_hit = high >= float(trade.stop)
                target_hit = low <= float(trade.target)
            else:
                stop_hit = low <= float(trade.stop)
                target_hit = high >= float(trade.target)
            if stop_hit:
                return {
                    "exit_price": float(trade.stop),
                    "closed_at": self._as_utc(idx),
                    "exit_reason": "stop_hit",
                    "bars": rows_seen,
                }
            if target_hit:
                return {
                    "exit_price": float(trade.target),
                    "closed_at": self._as_utc(idx),
                    "exit_reason": "target_hit",
                    "bars": rows_seen,
                }
        if len(rows_seen) < max_holding_bars:
            return None
        last_idx = future.index[min(max_holding_bars, len(future)) - 1]
        last_row = future.iloc[min(max_holding_bars, len(future)) - 1]
        return {
            "exit_price": float(last_row["close"]),
            "closed_at": self._as_utc(last_idx),
            "exit_reason": "time_stop",
            "bars": rows_seen[:max_holding_bars],
        }

    def _close_trade(self, db: Session, trade: Trade, outcome: dict[str, Any]) -> None:
        exit_price = float(outcome["exit_price"])
        risk = abs(float(trade.entry) - float(trade.stop))
        if trade.side.lower().strip() == "short":
            pnl = (float(trade.entry) - exit_price) * int(trade.qty)
            r_multiple = (float(trade.entry) - exit_price) / max(risk, 1e-9)
        else:
            pnl = (exit_price - float(trade.entry)) * int(trade.qty)
            r_multiple = (exit_price - float(trade.entry)) / max(risk, 1e-9)
        closed_at = outcome["closed_at"]
        metadata = dict(trade.metadata_json or {})
        bars = outcome.get("bars") or []
        mfe, mae = self._mfe_mae_r(trade, bars)
        metadata.update(
            {
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
            }
        )
        trade.status = TradeStatus.CLOSED
        trade.closed_at = closed_at
        trade.exit_price = round(exit_price, 4)
        trade.pnl_usd = round(pnl, 4)
        trade.r_multiple = round(r_multiple, 6)
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
                    "no_ibkr_order": True,
                },
            )
        )

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
