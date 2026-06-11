from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from tradeo.schemas import BacktestMetrics, PatternCandidate
from tradeo.research.quant_validation import tiered_round_trip_cost_r, triple_barrier_outcome
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
        total_signals = 0
        skipped_signals = 0
        for symbol in symbols:
            df = self.provider.fetch_ohlcv(symbol, period=period, interval=interval)
            if len(df) < 260:
                continue
            symbol_trades, symbol_signals, symbol_skipped = self._run_symbol(symbol, df, equity_curve, equity)
            trades.extend(symbol_trades)
            total_signals += symbol_signals
            skipped_signals += symbol_skipped
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
            total_signals=total_signals,
            skipped_signals=skipped_signals,
            skip_rate=round(skipped_signals / total_signals, 4) if total_signals else 0.0,
            trades=[t.__dict__ for t in trades[:500]],
        )
        return metrics

    def _run_symbol(
        self, symbol: str, df: pd.DataFrame, equity_curve: list[float], equity: float
    ) -> tuple[list[SimulatedTrade], int, int]:
        """Simulate one symbol; returns (trades, signals detected, signals skipped).

        Skipped signals are detected candidates that never become trades (entry
        gap pre-filter or canonical gap-entry skip) and must not enter trade
        aggregates.
        """
        trades: list[SimulatedTrade] = []
        signals = 0
        skipped = 0
        i = 230
        max_holding = self.detector.params.max_holding_bars
        while i < len(df) - max_holding - 1:
            lookback = df.iloc[: i + 1]
            candidate = self.detector.detect(symbol, lookback)
            if candidate is None:
                i += 1
                continue
            signals += 1
            # Enter next bar near open. Skip if next open gaps beyond 1R against setup.
            next_bar = df.iloc[i + 1]
            entry = float(next_bar["open"])
            if abs(entry - candidate.entry) / candidate.entry > 0.08:
                skipped += 1
                i += 1
                continue
            simulated = self._simulate_exit(symbol, df.iloc[i + 1 : i + 1 + max_holding], candidate, entry)
            if simulated is None:
                skipped += 1
                i += 1
                continue
            trades.append(simulated)
            equity += equity * self.risk_per_trade_pct * simulated.r_multiple
            equity_curve.append(equity)
            i += max_holding
        return trades, signals, skipped

    def _simulate_exit(
        self, symbol: str, future: pd.DataFrame, candidate: PatternCandidate, entry: float
    ) -> SimulatedTrade | None:
        stop = candidate.stop
        risk_per_share = max(0.01, entry - stop)
        target = candidate.target
        cost_r = tiered_round_trip_cost_r(
            entry_price=entry,
            risk_per_share=risk_per_share,
            avg_dollar_volume=float(candidate.features.get("avg_dollar_volume", 0.0)),
        )
        out = triple_barrier_outcome(
            [candidate.entry, *future["open"].astype(float).tolist()],
            [candidate.entry, *future["high"].astype(float).tolist()],
            [candidate.entry, *future["low"].astype(float).tolist()],
            [candidate.entry, *future["close"].astype(float).tolist()],
            signal_index=0,
            side=1,
            stop_price=float(stop),
            target_price=float(target),
            max_bars=len(future),
            gap_entry_policy="skip",
            round_trip_cost_R=cost_r,
        )
        if out["status"] != "ok":
            # skipped (gap entry) / invalid / no_data: non-trade, excluded from aggregates.
            return None
        exit_idx = int(out["exit_index"] or 1) - 1
        exit_idx = max(0, min(exit_idx, len(future) - 1))
        exit_price = float(out["exit_price"])
        outcome = str(out["reason"])
        exit_date = str(future.index[exit_idx].date())
        r_multiple = float(out["R"])
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
