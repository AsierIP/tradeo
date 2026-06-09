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
            if float(m["expectancy_r"]) > 0
            and float(m["profit_factor"]) > 1
            and int(m["sample_count"]) >= self.min_samples
        ]
        best = max(
            candidates,
            key=self._edge_score,
            default=max(metrics.values(), key=self._edge_score) if metrics else {},
        )
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

    def metrics_for_rr(
        self,
        samples: list[WindowSample],
        side: Side,
        rr: float,
        *,
        cost_multiplier: float = 1.0,
    ) -> dict[str, float | int]:
        results: list[float] = []
        target_bars: list[int] = []
        stop_bars: list[int] = []
        mfe: list[float] = []
        mae: list[float] = []
        costs: list[float] = []
        gap_adverse: list[float] = []
        mfe_before_mae: list[bool] = []
        strong_close_without_target: list[bool] = []
        labels: dict[str, int] = {"target": 0, "stop": 0, "timeout": 0}
        speed_labels: dict[str, int] = {}
        fill_probabilities: list[float] = []
        max_sizes: list[float] = []
        spread_pct: list[float] = []
        slippage_pct: list[float] = []
        entry_gap_penalty_pct: list[float] = []
        short_borrow_pct: list[float] = []
        for sample in samples:
            result, target_bar, stop_bar = self._simulate_sample(sample, side, rr, cost_multiplier=cost_multiplier)
            results.append(result)
            if target_bar is not None:
                target_bars.append(target_bar)
            if stop_bar is not None:
                stop_bars.append(stop_bar)
            mfe.append(sample.outcome.mfe_for(side))
            mae.append(sample.outcome.mae_for(side))
            costs.append(self._execution_cost_for_sample(sample, side, cost_multiplier=cost_multiplier))
            label = "target" if target_bar is not None else "stop" if stop_bar is not None else "timeout"
            labels[label] = labels.get(label, 0) + 1
            speed = self._speed_label(target_bar, stop_bar, len(sample.outcome.forward_closes))
            speed_labels[speed] = speed_labels.get(speed, 0) + 1
            if side == "long":
                gap_adverse.append(sample.outcome.long_gap_adverse_r)
                mfe_before_mae.append(sample.outcome.long_mfe_before_mae)
                strong_close_without_target.append(sample.outcome.long_strong_close_without_target)
            else:
                gap_adverse.append(sample.outcome.short_gap_adverse_r)
                mfe_before_mae.append(sample.outcome.short_mfe_before_mae)
                strong_close_without_target.append(sample.outcome.short_strong_close_without_target)
            execution = sample.outcome.execution or {}
            fill_probabilities.append(float(execution.get("fill_probability", 0.0)))
            max_sizes.append(float(execution.get("max_size_usd", 0.0)))
            spread_pct.append(float(execution.get("spread_proxy_pct", 0.0)))
            slippage_pct.append(float(execution.get("slippage_proxy_pct", 0.0)))
            entry_gap_penalty_pct.append(float(execution.get("entry_gap_penalty_pct", 0.0)))
            short_borrow_pct.append(float(execution.get("short_borrow_proxy_pct", 0.0)))

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
            "triple_barrier_labels": labels,
            "avg_gap_adverse_r": round(float(np.mean(gap_adverse)), 5) if gap_adverse else 0.0,
            "mfe_before_mae_rate": round(float(np.mean(mfe_before_mae)), 5) if mfe_before_mae else 0.0,
            "strong_close_without_target_rate": round(float(np.mean(strong_close_without_target)), 5)
            if strong_close_without_target
            else 0.0,
            "speed_label_counts": speed_labels,
            "fast_target_rate": round(speed_labels.get("fast_target", 0) / len(arr), 5) if len(arr) else 0.0,
            "slow_target_rate": round(speed_labels.get("slow_target", 0) / len(arr), 5) if len(arr) else 0.0,
            "timeout_rate": round(labels.get("timeout", 0) / len(arr), 5) if len(arr) else 0.0,
            "avg_fill_probability": round(float(np.mean(fill_probabilities)), 5) if fill_probabilities else 0.0,
            "p25_max_size_usd": round(float(np.quantile(max_sizes, 0.25)), 2) if max_sizes else 0.0,
            "median_max_size_usd": round(float(np.median(max_sizes)), 2) if max_sizes else 0.0,
            "avg_spread_proxy_pct": round(float(np.mean(spread_pct)), 6) if spread_pct else 0.0,
            "avg_slippage_proxy_pct": round(float(np.mean(slippage_pct)), 6) if slippage_pct else 0.0,
            "avg_entry_gap_penalty_pct": round(float(np.mean(entry_gap_penalty_pct)), 6)
            if entry_gap_penalty_pct
            else 0.0,
            "avg_short_borrow_proxy_pct": round(float(np.mean(short_borrow_pct)), 6)
            if short_borrow_pct
            else 0.0,
            "sample_count": int(len(arr)),
            "cost_multiplier": float(cost_multiplier),
        }

    @staticmethod
    def _simulate_sample(
        sample: WindowSample,
        side: Side,
        rr: float,
        *,
        cost_multiplier: float = 1.0,
    ) -> tuple[float, int | None, int | None]:
        entry = sample.outcome.entry_price
        risk = max(sample.outcome.risk_proxy, 1e-9)
        highs = sample.outcome.forward_highs
        lows = sample.outcome.forward_lows
        closes = sample.outcome.forward_closes
        if not highs or not lows or not closes:
            fallback = max(-1.0, min(rr, sample.outcome.outcome_for(side)))
            fallback -= RewardRiskAnalyzer._execution_cost_for_sample(sample, side, cost_multiplier=cost_multiplier)
            return float(fallback), None, None
        cost_r = RewardRiskAnalyzer._execution_cost_for_sample(sample, side, cost_multiplier=cost_multiplier)

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
    def _execution_cost_for_sample(sample: WindowSample, side: Side, *, cost_multiplier: float = 1.0) -> float:
        cost_r = max(0.0, float(sample.outcome.execution_cost_r))
        if side == "short":
            borrow_pct = max(0.0, float((sample.outcome.execution or {}).get("short_borrow_proxy_pct", 0.0)))
            borrow_r = sample.outcome.entry_price * borrow_pct / max(sample.outcome.risk_proxy, 1e-9)
            cost_r += borrow_r
        return float(cost_r * max(0.0, float(cost_multiplier)))

    @staticmethod
    def _speed_label(target_bar: int | None, stop_bar: int | None, horizon: int) -> str:
        if target_bar is None:
            return "stopped" if stop_bar is not None else "timeout"
        fast_cutoff = max(2, int(np.ceil(max(horizon, 1) * 0.25)))
        slow_cutoff = max(fast_cutoff + 1, int(np.ceil(max(horizon, 1) * 0.70)))
        if target_bar <= fast_cutoff:
            return "fast_target"
        if target_bar >= slow_cutoff:
            return "slow_target"
        return "normal_target"

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
