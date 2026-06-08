from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from sqlalchemy.orm import Session, joinedload

from tradeo.db.models import Signal, Trade

EntryModule = Literal["laboratory", "fox_hunter"]


def module_overview(db: Session, module: EntryModule, *, limit: int = 80) -> dict[str, Any]:
    signals = [
        signal
        for signal in db.query(Signal).order_by(Signal.created_at.desc()).limit(500).all()
        if _signal_module(signal) == module
    ][:limit]
    signal_ids = {signal.id for signal in signals}
    trades = [
        trade
        for trade in (
            db.query(Trade)
            .options(joinedload(Trade.signal))
            .order_by(Trade.opened_at.desc())
            .limit(500)
            .all()
        )
        if _trade_module(trade) == module or (trade.signal_id in signal_ids)
    ][:limit]
    pnl_points = _pnl_points(list(reversed(trades)))
    total_pnl = pnl_points[-1]["total_pnl_usd"] if pnl_points else 0.0
    closed_trades = [trade for trade in trades if _status_value(trade.status) == "closed"]
    return {
        "module": module,
        "signals": [_signal_to_dict(signal) for signal in signals],
        "trades": [_trade_to_dict(trade) for trade in trades],
        "pnl_points": pnl_points,
        "stats": {
            "signals": len(signals),
            "trades": len(trades),
            "open_trades": sum(1 for trade in trades if _status_value(trade.status) == "open"),
            "closed_trades": len(closed_trades),
            "total_pnl_usd": total_pnl,
            "total_r": round(sum(float(trade.r_multiple or 0.0) for trade in closed_trades), 4),
            "win_rate": (
                sum(1 for trade in closed_trades if float(trade.pnl_usd or 0.0) > 0) / len(closed_trades)
                if closed_trades
                else 0.0
            ),
        },
    }


def _signal_module(signal: Signal) -> str:
    metadata = signal.metadata_json or {}
    entry_module = metadata.get("entry_module")
    if entry_module:
        return str(entry_module)
    if signal.strategy_version.startswith("fox_hunter_"):
        return "fox_hunter"
    if signal.strategy_version.startswith("laboratory_"):
        return "laboratory"
    return "defined"


def _trade_module(trade: Trade) -> str:
    if trade.signal is not None:
        return _signal_module(trade.signal)
    metadata = trade.metadata_json or {}
    source_module = metadata.get("entry_module") or metadata.get("source_module")
    if source_module:
        return str(source_module)
    reason = str(metadata.get("reason") or "")
    if reason.startswith("fox_hunter"):
        return "fox_hunter"
    if reason.startswith("laboratory"):
        return "laboratory"
    return "defined"


def _pnl_points(trades: list[Trade]) -> list[dict[str, Any]]:
    total = 0.0
    points = [{"timestamp": datetime.now().isoformat(), "total_pnl_usd": 0.0, "trade_pnl_usd": 0.0}]
    for trade in trades:
        pnl = float(trade.pnl_usd or 0.0)
        total += pnl
        timestamp = trade.closed_at or trade.opened_at
        points.append(
            {
                "timestamp": timestamp.isoformat() if timestamp else "",
                "total_pnl_usd": round(total, 2),
                "trade_pnl_usd": round(pnl, 2),
                "symbol": trade.symbol,
                "status": _status_value(trade.status),
            }
        )
    return points


def _status_value(status: Any) -> str:
    return str(status.value if hasattr(status, "value") else status)


def _signal_to_dict(signal: Signal) -> dict[str, Any]:
    return {
        "id": signal.id,
        "symbol": signal.symbol,
        "pattern": signal.pattern,
        "side": signal.side,
        "timeframe": signal.timeframe,
        "entry": signal.entry,
        "stop": signal.stop,
        "target": signal.target,
        "reward_risk": signal.reward_risk,
        "confidence": signal.confidence,
        "composite_score": signal.composite_score,
        "risk_usd": signal.risk_usd,
        "suggested_qty": signal.suggested_qty,
        "strategy_version": signal.strategy_version,
        "status": _status_value(signal.status),
        "supervisor_notes": signal.supervisor_notes,
        "human_approved": signal.human_approved,
        "created_at": signal.created_at.isoformat() if signal.created_at else "",
        "metadata_json": signal.metadata_json or {},
    }


def _trade_to_dict(trade: Trade) -> dict[str, Any]:
    return {
        "id": trade.id,
        "signal_id": trade.signal_id,
        "symbol": trade.symbol,
        "pattern": trade.pattern,
        "side": trade.side,
        "qty": trade.qty,
        "entry": trade.entry,
        "stop": trade.stop,
        "target": trade.target,
        "status": _status_value(trade.status),
        "opened_at": trade.opened_at.isoformat() if trade.opened_at else "",
        "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
        "exit_price": trade.exit_price,
        "pnl_usd": trade.pnl_usd,
        "r_multiple": trade.r_multiple,
        "broker_order_id": trade.broker_order_id,
        "metadata_json": trade.metadata_json or {},
    }
