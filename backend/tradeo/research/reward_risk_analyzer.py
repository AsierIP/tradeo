from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tradeo.research.types import Side, WindowSample


@dataclass(slots=True)
class RewardRiskAnalyzer:
    """Evaluate a cluster across multiple target R levels.

    The scoring is intentionally adjustable. It favors real edge quality:
    expectancy, profit factor, enough hit rate, MFE/MAE efficiency, and limited
    drawdown. Higher R is not automatically better.
    """

    rr_levels: list[float]
    min_samples: int = 100

    def analyze(self, samples: list[WindowSample], side: Side) -> dict[str, object]:
        metrics = {self._key(rr): self.metrics_for_rr(samples, side, rr) for rr in self.rr_levels}
        candidates = [
            m
            for m in metrics.values()
            if float(m["expectancy_r"]) > 0 and float(m["profit_factor"]) > 1 and int(m["sample_count"]) >= self.min_samples
        ]
        best = max(candidates, key=self._edge_score, default=max(metrics.values(), key=self._edge_score) if metrics else {})
        best_rr = float(best.get("rr", 0.0)) if best else 0.0
        return {
            "rr_metrics": metrics,
            "best_rr": best_rr,
            "best_tested_rr": best_rr,
            "best_expectancy_r": float(best.get("expectancy_r", 0.0)) if best else 0.0,
            "best_profit_factor": float(best.get("profit_factor", 0.0)) if best else 0.0,
            "best_win_rate": float(best.get("win_rate", 0.0)) if best else 0.0,
            "best_max_drawdown_r": float(best.get("max_drawdown_r", 0.0)) if best else 0.0,
            "best_score": round(self._edge_score(best), 5) if best else 0.0,
        }

    def metrics_for_rr(self, samples: list[WindowSample], side: Side, rr: float) -> dict[str, float | int]:
        results: list[float] = []
        target_bars: list[int] = []
        stop_bars: list[int] = []
        mfe: list[float] = []
        mae: list[float] = []
        costs: list[float] = []
        for sample in samples:
            result, target_bar, stop_bar = self._simulate_sample(sample, side, rr)
            results.append(result)
            if target_bar is not None:
                target_bars.append(target_bar)
            if stop_bar is not None:
                stop_bars.append(stop_bar)
            mfe.append(sample.outcome.mfe_for(side))
            mae.append(sample.outcome.mae_for(side))
            costs.append(max(0.0, float(sample.outcome.execution_cost_r)))

        arr = np.asarray(results, dtype=float)
        wins = arr[arr > 0]
        losses = arr[arr < 0]
        gross_win = float(wins.sum()) if len(wins) else 0.0
        gross_loss = abs(float(losses.sum())) if len(losses) else 0.0
        pf = gross_win / gross_loss if gross_loss > 0 else gross_win
        avg_mfe = float(np.mean(mfe)) if mfe else 0.0
        avg_mae = float(np.mean(mae)) if mae else 0.0
        return {
            "rr": float(rr),
            "target_r": float(rr),
            "win_rate": round(float(np.mean(arr > 0)), 5) if len(arr) else 0.0,
            "loss_rate": round(float(np.mean(arr < 0)), 5) if len(arr) else 0.0,
            "target_hit_rate": round(len(target_bars) / len(arr), 5) if len(arr) else 0.0,
            "stop_hit_rate": round(len(stop_bars) / len(arr), 5) if len(arr) else 0.0,
            "expectancy_r": round(float(np.mean(arr)), 5) if len(arr) else 0.0,
            "profit_factor": round(float(pf), 5),
            "avg_win_r": round(float(np.mean(wins)), 5) if len(wins) else 0.0,
            "avg_loss_r": round(float(abs(np.mean(losses))), 5) if len(losses) else 0.0,
            "median_result_r": round(float(np.median(arr)), 5) if len(arr) else 0.0,
            "avg_mfe_r": round(avg_mfe, 5),
            "avg_mae_r": round(avg_mae, 5),
            "mfe_mae_ratio": round(avg_mfe / max(avg_mae, 1e-9), 5),
            "avg_execution_cost_r": round(float(np.mean(costs)), 5) if costs else 0.0,
            "max_drawdown_r": round(self._max_drawdown(arr), 5),
            "avg_bars_to_target": round(float(np.mean(target_bars)), 3) if target_bars else 0.0,
            "avg_bars_to_stop": round(float(np.mean(stop_bars)), 3) if stop_bars else 0.0,
            "sample_count": int(len(arr)),
        }

    @staticmethod
    def _simulate_sample(sample: WindowSample, side: Side, rr: float) -> tuple[float, int | None, int | None]:
        entry = sample.outcome.entry_price
        risk = max(sample.outcome.risk_proxy, 1e-9)
        highs = sample.outcome.forward_highs
        lows = sample.outcome.forward_lows
        closes = sample.outcome.forward_closes
        if not highs or not lows or not closes:
            fallback = max(-1.0, min(rr, sample.outcome.outcome_for(side)))
            fallback -= max(0.0, float(sample.outcome.execution_cost_r))
            return float(fallback), None, None
        cost_r = max(0.0, float(sample.outcome.execution_cost_r))

        if side == "long":
            target = entry + risk * rr
            stop = entry - risk
            for idx, (high, low) in enumerate(zip(highs, lows, strict=False), start=1):
                if float(low) <= stop:
                    return -1.0 - cost_r, None, idx
                if float(high) >= target:
                    return float(rr) - cost_r, idx, None
            return float(max(-1.0, min(rr, (closes[-1] - entry) / risk)) - cost_r), None, None

        target = entry - risk * rr
        stop = entry + risk
        for idx, (high, low) in enumerate(zip(highs, lows, strict=False), start=1):
            if float(high) >= stop:
                return -1.0 - cost_r, None, idx
            if float(low) <= target:
                return float(rr) - cost_r, idx, None
        return float(max(-1.0, min(rr, (entry - closes[-1]) / risk)) - cost_r), None, None

    @staticmethod
    def _max_drawdown(results: np.ndarray) -> float:
        if len(results) == 0:
            return 0.0
        equity = np.cumsum(results)
        peak = np.maximum.accumulate(equity)
        return float(np.max(peak - equity))

    @staticmethod
    def _edge_score(metrics: dict[str, object]) -> float:
        if not metrics:
            return -1e9
        expectancy = float(metrics.get("expectancy_r", 0.0))
        profit_factor = float(metrics.get("profit_factor", 0.0))
        win_rate = float(metrics.get("win_rate", 0.0))
        mfe_mae_ratio = float(metrics.get("mfe_mae_ratio", 0.0))
        drawdown = float(metrics.get("max_drawdown_r", 0.0))
        drawdown_penalty = min(drawdown / 12.0, 1.0)
        return (
            expectancy * 0.45
            + min(profit_factor / 3.0, 1.0) * 0.25
            + min(win_rate / 0.5, 1.0) * 0.10
            + min(mfe_mae_ratio / 4.0, 1.0) * 0.10
            - drawdown_penalty * 0.10
        )

    @staticmethod
    def _key(rr: float) -> str:
        return f"{float(rr):g}"
