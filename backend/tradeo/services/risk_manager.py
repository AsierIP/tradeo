from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from tradeo.core.config import Settings, get_settings
from tradeo.db.models import RiskLedger, Signal, SignalStatus, Trade, TradeStatus
from tradeo.schemas import PatternCandidate, RiskDecision


@dataclass
class AccountState:
    equity: float
    cash: float
    open_positions: int
    open_risk: float
    realized_pnl_today: float


class RiskManager:
    """Hard risk gate for every candidate.

    With 3,000 USD starting capital and 1% risk, max risk per trade is 30 USD.
    The manager rejects candidates before any broker adapter can see them.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def account_state(self, db: Session) -> AccountState:
        open_trades = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).all()
        open_positions = len(open_trades)
        open_risk = sum(abs(t.entry - t.stop) * t.qty for t in open_trades)
        today = datetime.now(timezone.utc).date().isoformat()
        ledger = db.query(RiskLedger).filter(RiskLedger.day == today).one_or_none()
        realized = ledger.realized_pnl if ledger else 0.0
        # v0 uses configured capital as equity until a broker sync or paper fills update it.
        equity = self.settings.initial_capital_usd + realized
        cash = equity
        return AccountState(equity=equity, cash=cash, open_positions=open_positions, open_risk=open_risk, realized_pnl_today=realized)

    def validate_candidate(self, candidate: PatternCandidate, db: Session | None = None) -> RiskDecision:
        hard: list[str] = []
        warnings: list[str] = []
        settings = self.settings
        equity = settings.initial_capital_usd
        open_positions = 0
        realized_today = 0.0
        if db is not None:
            state = self.account_state(db)
            equity = state.equity
            open_positions = state.open_positions
            realized_today = state.realized_pnl_today

        if settings.kill_switch_enabled:
            hard.append("kill_switch_enabled")
        if candidate.side == "long" and not settings.allow_longs:
            hard.append("longs_disabled")
        if candidate.side == "short" and not settings.allow_shorts:
            hard.append("shorts_disabled")
        if candidate.reward_risk < settings.min_reward_risk:
            hard.append(f"reward_risk_below_{settings.min_reward_risk}")
        if open_positions >= settings.max_open_positions:
            hard.append("max_open_positions_reached")
        if realized_today <= -settings.initial_capital_usd * settings.daily_loss_limit_pct:
            hard.append("daily_loss_limit_reached")

        risk_per_share = abs(candidate.entry - candidate.stop)
        if risk_per_share <= 0:
            hard.append("invalid_stop_distance")
            return RiskDecision(approved=False, reason=";".join(hard), hard_rejections=hard, warnings=warnings)

        risk_budget = equity * settings.risk_per_trade_pct
        qty_by_risk = int(risk_budget // risk_per_share)
        max_position_value = equity * settings.max_position_value_pct
        qty_by_notional = int(max_position_value // candidate.entry)
        qty = max(0, min(qty_by_risk, qty_by_notional))
        risk_usd = round(qty * risk_per_share, 2)
        notional = round(qty * candidate.entry, 2)

        if qty <= 0:
            hard.append("position_size_zero")
        if notional > equity * settings.max_gross_exposure_pct and not settings.allow_margin:
            hard.append("gross_exposure_exceeds_cash_limit")
        if risk_usd > risk_budget * 1.0001:
            hard.append("risk_budget_exceeded")
        if candidate.features.get("avg_dollar_volume", 0) < settings.min_avg_dollar_volume:
            hard.append("liquidity_filter_failed")
        if candidate.features.get("atr_pct", 0) > settings.max_atr_pct:
            hard.append("atr_filter_failed")
        if candidate.confidence < 0.68:
            warnings.append("confidence_under_preferred_threshold")

        approved = not hard
        reason = "approved" if approved else ";".join(hard)
        return RiskDecision(
            approved=approved,
            suggested_qty=qty,
            risk_usd=risk_usd,
            notional_usd=notional,
            reason=reason,
            hard_rejections=hard,
            warnings=warnings,
        )

    def approve_signal_for_live(self, signal: Signal) -> bool:
        return (
            signal.status == SignalStatus.PENDING_HUMAN_APPROVAL
            and signal.human_approved
            and self.settings.live_armed
        )
