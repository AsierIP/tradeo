from __future__ import annotations

from sqlalchemy.orm import Session

from tradeo.db.models import PatternMetric, Trade, TradeStatus
from tradeo.services.technical_indicators import max_drawdown_pct


def refresh_pattern_metrics(db: Session) -> list[PatternMetric]:
    trades = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED).all()
    by_pattern: dict[str, list[Trade]] = {}
    for t in trades:
        by_pattern.setdefault(t.pattern, []).append(t)
    metrics: list[PatternMetric] = []
    for pattern, ts in by_pattern.items():
        r_values = [t.r_multiple for t in ts]
        wins = [r for r in r_values if r > 0]
        losses = [r for r in r_values if r < 0]
        profit_factor = sum(wins) / abs(sum(losses)) if losses else sum(wins)
        equity = [3000.0]
        for r in r_values:
            equity.append(equity[-1] * (1 + 0.01 * r))
        metric = db.query(PatternMetric).filter(PatternMetric.pattern == pattern).one_or_none()
        if metric is None:
            metric = PatternMetric(pattern=pattern, strategy_version="cup_v0")
            db.add(metric)
        metric.total_trades = len(ts)
        metric.win_rate = len(wins) / len(ts) if ts else 0
        metric.profit_factor = profit_factor
        metric.expectancy_r = sum(r_values) / len(r_values) if r_values else 0
        metric.avg_r_multiple = metric.expectancy_r
        metric.max_drawdown_pct = max_drawdown_pct(equity)
        metrics.append(metric)
    db.commit()
    return metrics
