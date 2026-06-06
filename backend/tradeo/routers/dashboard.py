from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from tradeo.core.config import get_settings
from tradeo.core.security import require_admin
from tradeo.db.models import EquityPoint, PatternMetric, Signal, Trade, TradeStatus
from tradeo.db.session import get_db
from tradeo.schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(_: str = Depends(require_admin), db: Session = Depends(get_db)) -> DashboardSummary:
    settings = get_settings()
    equity = db.query(EquityPoint).order_by(EquityPoint.timestamp.asc()).limit(500).all()
    metrics = db.query(PatternMetric).order_by(PatternMetric.pattern.asc()).all()
    signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(25).all()
    open_trades = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).order_by(Trade.opened_at.desc()).all()
    return DashboardSummary(
        mode=settings.trading_mode,
        live_armed=settings.live_armed,
        kill_switch_enabled=settings.kill_switch_enabled,
        initial_capital_usd=settings.initial_capital_usd,
        risk_per_trade_usd=settings.account_risk_usd,
        min_reward_risk=settings.min_reward_risk,
        equity=equity,
        pattern_metrics=metrics,
        recent_signals=signals,
        open_trades=open_trades,
        supervisor_state={
            "policy": "paper-first; live requires explicit env arming + human approval",
            "min_trades_before_live_review": 40,
            "min_profit_factor": 1.8,
            "min_expectancy_r": 0.25,
            "max_drawdown_pct": 12.0,
        },
    )
