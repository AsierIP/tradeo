from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from tradeo.schemas import BacktestMetrics, PatternCandidate
from tradeo.services.data_provider import MarketDataProvider
from tradeo.services.pattern_detector import CupPatternDetector
from tradeo.services.technical_indicators import max_drawdown_pct


@dataclass
class SimulatedTrade:
    symbol: str
    entry_date: str
    exit_date: str
    side: str
    entry: float
    stop: float
    target: float
    exit: float
    r_multiple: float
    outcome: str


class Backtester:
    def __init__(
        self,
        provider: MarketDataProvider | None = None,
        detector: CupPatternDetector | None = None,
        starting_equity: float = 3000.0,
        risk_per_trade_pct: float = 0.01,
    ) -> None:
        if provider is None:
            from tradeo.services.provider_factory import get_market_data_provider

            provider = get_market_data_provider()
        self.provider = provider
        self.detector = detector or CupPatternDetector()
        self.starting_equity = starting_equity
        self.risk_per_trade_pct = risk_per_trade_pct

    def run(self, symbols: list[str], period: str = "3y", interval: str = "1d") -> BacktestMetrics:
        trades: list[SimulatedTrade] = []
        equity_curve = [self.starting_equity]
        equity = self.starting_equity
        for symbol in symbols:
            df = self.provider.fetch_ohlcv(symbol, period=period, interval=interval)
            if len(df) < 260:
                continue
            trades.extend(self._run_symbol(symbol, df, equity_curve, equity))
            equity = equity_curve[-1]
        r_values = [t.r_multiple for t in trades]
        wins = [r for r in r_values if r > 0]
        losses = [r for r in r_values if r < 0]
        total = len(trades)
        profit_factor = float(sum(wins) / abs(sum(losses))) if losses else float(sum(wins) or 0.0)
        metrics = BacktestMetrics(
            total_trades=total,
            win_rate=round(len(wins) / total, 4) if total else 0.0,
            profit_factor=round(profit_factor, 4),
            expectancy_r=round(float(np.mean(r_values)), 4) if r_values else 0.0,
            avg_r_multiple=round(float(np.mean(r_values)), 4) if r_values else 0.0,
            max_drawdown_pct=round(max_drawdown_pct(equity_curve), 4),
            trades=[t.__dict__ for t in trades[:500]],
        )
        return metrics

    def _run_symbol(
        self, symbol: str, df: pd.DataFrame, equity_curve: list[float], equity: float
    ) -> list[SimulatedTrade]:
        trades: list[SimulatedTrade] = []
        i = 230
        max_holding = self.detector.params.max_holding_bars
        while i < len(df) - max_holding - 1:
            lookback = df.iloc[: i + 1]
            candidate = self.detector.detect(symbol, lookback)
            if candidate is None:
                i += 1
                continue
            # Enter next bar near open. Skip if next open gaps beyond 1R against setup.
            next_bar = df.iloc[i + 1]
            entry = float(next_bar["open"])
            if abs(entry - candidate.entry) / candidate.entry > 0.08:
                i += 1
                continue
            simulated = self._simulate_exit(symbol, df.iloc[i + 1 : i + 1 + max_holding], candidate, entry)
            trades.append(simulated)
            equity += equity * self.risk_per_trade_pct * simulated.r_multiple
            equity_curve.append(equity)
            i += max_holding
        return trades

    def _simulate_exit(
        self, symbol: str, future: pd.DataFrame, candidate: PatternCandidate, entry: float
    ) -> SimulatedTrade:
        stop = candidate.stop
        risk_per_share = max(0.01, entry - stop)
        target = entry + candidate.reward_risk * risk_per_share
        exit_price = float(future.iloc[-1]["close"])
        outcome = "timeout"
        exit_date = str(future.index[-1].date())
        for idx, row in future.iterrows():
            low = float(row["low"])
            high = float(row["high"])
            if low <= stop:
                exit_price = stop
                outcome = "stop"
                exit_date = str(idx.date())
                break
            if high >= target:
                exit_price = target
                outcome = "target"
                exit_date = str(idx.date())
                break
        r_multiple = (exit_price - entry) / risk_per_share
        return SimulatedTrade(
            symbol=symbol,
            entry_date=str(future.index[0].date()),
            exit_date=exit_date,
            side="long",
            entry=round(entry, 2),
            stop=round(stop, 2),
            target=round(target, 2),
            exit=round(exit_price, 2),
            r_multiple=round(float(r_multiple), 4),
            outcome=outcome,
        )
