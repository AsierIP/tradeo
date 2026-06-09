from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from tradeo.research.reward_risk_analyzer import RewardRiskAnalyzer
from tradeo.research.types import Side, WindowSample


@dataclass(slots=True)
class MarketReplayConfig:
    latency_bars: int = 1
    requested_size_usd: float = 1500.0
    min_fill_ratio: float = 0.10


@dataclass(slots=True)
class MarketReplayEngine:
    """Deterministic trader replay proxy for discovery-stage patterns.

    This is not a broker simulator. It is a conservative research stress test:
    delayed entry, partial fills, fill probability, entry gap, spread/slippage,
    short borrow proxy and size caps all reduce the expected R.
    """

    config: MarketReplayConfig | None = None

    def __post_init__(self) -> None:
        self.config = self.config or MarketReplayConfig()

    def analyze(
        self,
        samples: list[WindowSample],
        side: Side,
        rr: float,
        *,
        cost_multiplier: float = 1.0,
    ) -> dict[str, Any]:
        if not samples:
            return self._empty(rr)
        assert self.config is not None
        results: list[dict[str, float | str | int | None]] = []
        for sample in samples:
            results.append(
                self._simulate_sample(
                    sample,
                    side,
                    rr,
                    latency_bars=max(0, int(self.config.latency_bars)),
                    requested_size_usd=max(1.0, float(self.config.requested_size_usd)),
                    cost_multiplier=cost_multiplier,
                )
            )
        expected = np.asarray([float(row["expected_result_r"]) for row in results], dtype=float)
        full = np.asarray([float(row["full_fill_result_r"]) for row in results], dtype=float)
        fill_ratios = np.asarray([float(row["fill_ratio"]) for row in results], dtype=float)
        fill_probabilities = np.asarray([float(row["fill_probability"]) for row in results], dtype=float)
        late_penalties = np.asarray([float(row["late_entry_penalty_r"]) for row in results], dtype=float)
        gap_penalties = np.asarray([float(row["entry_gap_penalty_r"]) for row in results], dtype=float)
        spread_slippage = np.asarray([float(row["spread_slippage_r"]) for row in results], dtype=float)
        max_sizes = np.asarray([float(row["max_size_usd"]) for row in results], dtype=float)
        labels = self._label_counts([str(row["label"]) for row in results])
        avg_expected = float(np.mean(expected)) if len(expected) else 0.0
        avg_fill_ratio = float(np.mean(fill_ratios)) if len(fill_ratios) else 0.0
        warnings: list[str] = []
        if avg_expected <= 0:
            warnings.append("market replay deja expectancy no positiva")
        if avg_fill_ratio < 0.45:
            warnings.append("market replay detecta fills parciales severos")
        if float(np.mean(late_penalties)) > 0.25:
            warnings.append("late entry penalty alto")
        return {
            "method": "deterministic_latency_partial_fill_replay",
            "sample_count": len(samples),
            "rr": round(float(rr), 5),
            "latency_bars": int(self.config.latency_bars),
            "requested_size_usd": round(float(self.config.requested_size_usd), 2),
            "expected_expectancy_r": round(avg_expected, 5),
            "full_fill_expectancy_r": round(float(np.mean(full)), 5) if len(full) else 0.0,
            "win_rate": round(float(np.mean(expected > 0)), 5) if len(expected) else 0.0,
            "profit_factor": self._profit_factor(expected),
            "max_drawdown_r": round(RewardRiskAnalyzer._max_drawdown(expected), 5),
            "avg_fill_probability": round(float(np.mean(fill_probabilities)), 5),
            "avg_fill_ratio": round(avg_fill_ratio, 5),
            "partial_fill_rate": round(float(np.mean(fill_ratios < 0.999)), 5),
            "no_fill_rate": round(float(np.mean(fill_ratios <= float(self.config.min_fill_ratio))), 5),
            "avg_late_entry_penalty_r": round(float(np.mean(late_penalties)), 5),
            "avg_entry_gap_penalty_r": round(float(np.mean(gap_penalties)), 5),
            "avg_spread_slippage_r": round(float(np.mean(spread_slippage)), 5),
            "p25_max_size_usd": round(float(np.quantile(max_sizes, 0.25)), 2),
            "median_max_size_usd": round(float(np.median(max_sizes)), 2),
            "labels": labels,
            "target_hit_rate": round(labels.get("target", 0) / len(results), 5),
            "stop_hit_rate": round(labels.get("stop", 0) / len(results), 5),
            "timeout_rate": round(labels.get("timeout", 0) / len(results), 5),
            "execution_quality_score": round(self._execution_quality(avg_expected, avg_fill_ratio), 5),
            "passed": bool(avg_expected > 0 and avg_fill_ratio >= 0.35),
            "warnings": warnings,
            "examples": results[:10],
        }

    def _simulate_sample(
        self,
        sample: WindowSample,
        side: Side,
        rr: float,
        *,
        latency_bars: int,
        requested_size_usd: float,
        cost_multiplier: float,
    ) -> dict[str, float | str | int | None]:
        entry = float(sample.outcome.entry_price)
        risk = max(float(sample.outcome.risk_proxy), 1e-9)
        highs = [float(v) for v in sample.outcome.forward_highs]
        lows = [float(v) for v in sample.outcome.forward_lows]
        closes = [float(v) for v in sample.outcome.forward_closes]
        if not highs or not lows or not closes:
            result, target_bar, stop_bar = RewardRiskAnalyzer._simulate_sample(
                sample,
                side,
                rr,
                cost_multiplier=cost_multiplier,
            )
            return self._row(
                sample,
                result=result,
                target_bar=target_bar,
                stop_bar=stop_bar,
                fill_ratio=1.0,
                fill_probability=1.0,
                max_size_usd=requested_size_usd,
                delayed_entry=entry,
                late_penalty=0.0,
                entry_gap_penalty_r=0.0,
                spread_slippage_r=0.0,
            )

        delayed_idx = min(max(0, latency_bars - 1), len(closes) - 1)
        delayed_entry = closes[delayed_idx] if latency_bars else entry
        path_start = min(delayed_idx + (1 if latency_bars else 0), len(closes) - 1)
        path_highs = highs[path_start:]
        path_lows = lows[path_start:]
        path_closes = closes[path_start:]
        late_penalty = self._late_entry_penalty(entry, delayed_entry, risk, side)
        execution = sample.outcome.execution or {}
        fill_probability = max(0.0, min(1.0, float(execution.get("fill_probability", 1.0))))
        max_size_usd = max(0.0, float(execution.get("max_size_usd", requested_size_usd)))
        size_ratio = max(0.0, min(1.0, max_size_usd / requested_size_usd))
        fill_ratio = max(0.0, min(1.0, fill_probability * size_ratio))
        if fill_probability <= 0.0 or fill_ratio < 1e-9:
            fill_ratio = 0.0
        spread_slippage_pct = max(0.0, float(execution.get("spread_proxy_pct", 0.0))) + max(
            0.0,
            float(execution.get("slippage_proxy_pct", 0.0)),
        )
        spread_slippage_r = entry * spread_slippage_pct / risk
        entry_gap_penalty_r = entry * max(
            0.0,
            float(execution.get("entry_gap_penalty_pct", 0.0)),
        ) / risk
        cost_r = RewardRiskAnalyzer._execution_cost_for_sample(
            sample,
            side,
            cost_multiplier=cost_multiplier,
        )
        extra_cost = late_penalty + spread_slippage_r * 0.50
        result, target_bar, stop_bar = self._path_result(
            delayed_entry,
            risk,
            path_highs,
            path_lows,
            path_closes,
            side,
            rr,
            cost_r + extra_cost,
        )
        expected = result * fill_ratio
        row = self._row(
            sample,
            result=result,
            target_bar=target_bar,
            stop_bar=stop_bar,
            fill_ratio=fill_ratio,
            fill_probability=fill_probability,
            max_size_usd=max_size_usd,
            delayed_entry=delayed_entry,
            late_penalty=late_penalty,
            entry_gap_penalty_r=entry_gap_penalty_r,
            spread_slippage_r=spread_slippage_r,
        )
        row["expected_result_r"] = round(float(expected), 5)
        return row

    @staticmethod
    def _path_result(
        entry: float,
        risk: float,
        highs: list[float],
        lows: list[float],
        closes: list[float],
        side: Side,
        rr: float,
        cost_r: float,
    ) -> tuple[float, int | None, int | None]:
        if not highs or not lows or not closes:
            return -float(cost_r), None, None
        if side == "long":
            target = entry + risk * rr
            stop = entry - risk
            for idx, (high, low) in enumerate(zip(highs, lows, strict=False), start=1):
                if low <= stop:
                    return -1.0 - cost_r, None, idx
                if high >= target:
                    return float(rr) - cost_r, idx, None
            return max(-1.0, min(rr, (closes[-1] - entry) / risk)) - cost_r, None, None
        target = entry - risk * rr
        stop = entry + risk
        for idx, (high, low) in enumerate(zip(highs, lows, strict=False), start=1):
            if high >= stop:
                return -1.0 - cost_r, None, idx
            if low <= target:
                return float(rr) - cost_r, idx, None
        return max(-1.0, min(rr, (entry - closes[-1]) / risk)) - cost_r, None, None

    @staticmethod
    def _row(
        sample: WindowSample,
        *,
        result: float,
        target_bar: int | None,
        stop_bar: int | None,
        fill_ratio: float,
        fill_probability: float,
        max_size_usd: float,
        delayed_entry: float,
        late_penalty: float,
        entry_gap_penalty_r: float,
        spread_slippage_r: float,
    ) -> dict[str, float | str | int | None]:
        label = "target" if target_bar is not None else "stop" if stop_bar is not None else "timeout"
        return {
            "symbol": sample.symbol,
            "window_end": sample.end,
            "label": label,
            "full_fill_result_r": round(float(result), 5),
            "expected_result_r": round(float(result * fill_ratio), 5),
            "target_bar": target_bar,
            "stop_bar": stop_bar,
            "fill_probability": round(float(fill_probability), 5),
            "fill_ratio": round(float(fill_ratio), 5),
            "max_size_usd": round(float(max_size_usd), 2),
            "delayed_entry": round(float(delayed_entry), 6),
            "late_entry_penalty_r": round(float(late_penalty), 5),
            "entry_gap_penalty_r": round(float(entry_gap_penalty_r), 5),
            "spread_slippage_r": round(float(spread_slippage_r), 5),
        }

    @staticmethod
    def _late_entry_penalty(entry: float, delayed_entry: float, risk: float, side: Side) -> float:
        if side == "long":
            return max(0.0, (delayed_entry - entry) / risk)
        return max(0.0, (entry - delayed_entry) / risk)

    @staticmethod
    def _profit_factor(values: np.ndarray) -> float:
        if len(values) == 0:
            return 0.0
        wins = values[values > 0]
        losses = values[values < 0]
        gross_loss = abs(float(losses.sum())) if len(losses) else 0.0
        gross_win = float(wins.sum()) if len(wins) else 0.0
        return round(float(gross_win / gross_loss), 5) if gross_loss else round(gross_win, 5)

    @staticmethod
    def _execution_quality(expectancy: float, fill_ratio: float) -> float:
        expectancy_score = max(0.0, min(1.0, expectancy / 1.0))
        return max(0.0, min(1.0, expectancy_score * 0.55 + fill_ratio * 0.45))

    @staticmethod
    def _label_counts(labels: list[str]) -> dict[str, int]:
        counts = {"target": 0, "stop": 0, "timeout": 0}
        for label in labels:
            counts[label] = counts.get(label, 0) + 1
        return counts

    @staticmethod
    def _empty(rr: float) -> dict[str, Any]:
        return {
            "method": "deterministic_latency_partial_fill_replay",
            "sample_count": 0,
            "rr": round(float(rr), 5),
            "expected_expectancy_r": 0.0,
            "full_fill_expectancy_r": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_r": 0.0,
            "avg_fill_probability": 0.0,
            "avg_fill_ratio": 0.0,
            "partial_fill_rate": 0.0,
            "execution_quality_score": 0.0,
            "passed": False,
            "warnings": ["sin muestras para market replay"],
            "examples": [],
        }
