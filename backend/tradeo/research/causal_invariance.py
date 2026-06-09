from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from tradeo.research.reward_risk_analyzer import RewardRiskAnalyzer
from tradeo.research.types import Side, WindowSample


BucketFn = Callable[[WindowSample], str]


@dataclass(slots=True)
class CausalInvariantTester:
    """Invariant diagnostics across market partitions.

    Discovery patterns should not depend on three symbols, one year or one
    friendly regime. This module produces challengeable bucket evidence and
    expected-fail zones without touching persistent schema.
    """

    min_bucket_samples: int = 8
    min_positive_bucket_rate: float = 0.45

    def analyze(self, samples: list[WindowSample], side: Side, rr: float) -> dict[str, Any]:
        if not samples:
            return self._empty()
        outcomes = np.asarray(
            [RewardRiskAnalyzer._simulate_sample(sample, side, rr)[0] for sample in samples],
            dtype=float,
        )
        groupers: dict[str, BucketFn] = {
            "year": lambda s: str(s.year),
            "symbol": lambda s: s.symbol,
            "market_regime": self._market_bucket,
            "volatility_regime": self._vol_bucket,
            "trend_regime": self._trend_bucket,
            "sector_proxy": self._sector_bucket,
            "liquidity_regime": self._liquidity_bucket,
        }
        groups = {
            name: self._bucket_metrics(samples, outcomes, bucket_fn)
            for name, bucket_fn in groupers.items()
        }
        expected_fails = self._expected_fail_buckets(groups)
        group_scores = [
            self._group_invariance_score(rows)
            for name, rows in groups.items()
            if name not in {"symbol"} and len(rows) > 0
        ]
        symbol_dependency = self._symbol_dependency(samples)
        coverage_score = min(1.0, len({s.symbol for s in samples}) / 12.0) * 0.5 + min(
            1.0,
            len({s.year for s in samples}) / 4.0,
        ) * 0.5
        invariance_score = (
            (float(np.mean(group_scores)) if group_scores else 0.0) * 0.60
            + coverage_score * 0.25
            + (1.0 if symbol_dependency["no_three_symbol_dependency"] else 0.0) * 0.15
        )
        warnings: list[str] = []
        if not symbol_dependency["no_three_symbol_dependency"]:
            warnings.append("dependencia excesiva de pocos simbolos/eventos")
        if expected_fails:
            warnings.append("hay buckets expected-fail que requieren condiciones de muerte")
        if invariance_score < 0.45:
            warnings.append("invariancia causal debil entre regimenes")
        return {
            "method": "bucket_invariance_proxy",
            "sample_count": len(samples),
            "rr": round(float(rr), 5),
            "invariance_score": round(float(max(0.0, min(1.0, invariance_score))), 5),
            "positive_bucket_rate": round(float(np.mean([score > 0 for score in group_scores])), 5)
            if group_scores
            else 0.0,
            "bucket_groups": groups,
            "expected_fail_buckets": expected_fails,
            "symbol_dependency": symbol_dependency,
            "coverage_score": round(float(coverage_score), 5),
            "passed": bool(
                invariance_score >= self.min_positive_bucket_rate
                and symbol_dependency["no_three_symbol_dependency"]
            ),
            "warnings": warnings,
        }

    def _bucket_metrics(
        self,
        samples: list[WindowSample],
        outcomes: np.ndarray,
        bucket_fn: BucketFn,
    ) -> list[dict[str, Any]]:
        buckets: dict[str, list[float]] = {}
        for sample, outcome in zip(samples, outcomes, strict=True):
            buckets.setdefault(bucket_fn(sample), []).append(float(outcome))
        rows: list[dict[str, Any]] = []
        for bucket, values in buckets.items():
            arr = np.asarray(values, dtype=float)
            rows.append(
                {
                    "bucket": bucket,
                    "sample_count": int(len(arr)),
                    "expectancy_r": round(float(np.mean(arr)), 5),
                    "win_rate": round(float(np.mean(arr > 0)), 5),
                    "support_ok": bool(len(arr) >= self.min_bucket_samples),
                    "positive": bool(float(np.mean(arr)) > 0),
                }
            )
        return sorted(rows, key=lambda row: (int(row["sample_count"]), str(row["bucket"])), reverse=True)

    def _group_invariance_score(self, rows: list[dict[str, Any]]) -> float:
        if not rows:
            return 0.0
        supported = [row for row in rows if bool(row["support_ok"])]
        if not supported:
            return 0.0
        positive_rate = sum(1 for row in supported if bool(row["positive"])) / len(supported)
        weak_penalty = sum(
            1
            for row in supported
            if not bool(row["positive"]) and float(row["expectancy_r"]) <= -0.10
        ) / len(supported)
        return float(max(0.0, min(1.0, positive_rate - weak_penalty * 0.35)))

    @staticmethod
    def _expected_fail_buckets(groups: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        fails: list[dict[str, Any]] = []
        for group_name, rows in groups.items():
            for row in rows:
                if int(row["sample_count"]) < 3:
                    continue
                if float(row["expectancy_r"]) < 0:
                    fails.append(
                        {
                            "group": group_name,
                            "bucket": row["bucket"],
                            "sample_count": row["sample_count"],
                            "expectancy_r": row["expectancy_r"],
                            "reason": "negative expectancy bucket",
                        }
                    )
                elif not bool(row["support_ok"]):
                    fails.append(
                        {
                            "group": group_name,
                            "bucket": row["bucket"],
                            "sample_count": row["sample_count"],
                            "expectancy_r": row["expectancy_r"],
                            "reason": "underpowered bucket",
                        }
                    )
        return sorted(fails, key=lambda row: (float(row["expectancy_r"]), int(row["sample_count"])))[:20]

    @staticmethod
    def _symbol_dependency(samples: list[WindowSample]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for sample in samples:
            counts[sample.symbol] = counts.get(sample.symbol, 0) + 1
        total = max(1, len(samples))
        sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
        top1 = sorted_counts[0][1] / total if sorted_counts else 0.0
        top3 = sum(count for _, count in sorted_counts[:3]) / total if sorted_counts else 0.0
        return {
            "symbol_count": len(counts),
            "top_symbol": sorted_counts[0][0] if sorted_counts else "",
            "top_symbol_share": round(float(top1), 5),
            "top3_symbol_share": round(float(top3), 5),
            "no_three_symbol_dependency": bool(len(counts) > 3 and top3 <= 0.70 and top1 <= 0.45),
        }

    @staticmethod
    def _market_bucket(sample: WindowSample) -> str:
        value = float(sample.features.get("market_regime_score", 0.0))
        if value > 0.25:
            return "market_up"
        if value < -0.25:
            return "market_down"
        return "market_mixed"

    @staticmethod
    def _vol_bucket(sample: WindowSample) -> str:
        value = float(sample.features.get("volatility_regime", 1.0))
        if value > 1.25:
            return "high_vol"
        if value < 0.80:
            return "low_vol"
        return "normal_vol"

    @staticmethod
    def _trend_bucket(sample: WindowSample) -> str:
        value = float(sample.features.get("trend_regime", 0.0))
        if value > 0.25:
            return "uptrend"
        if value < -0.25:
            return "downtrend"
        return "mixed_trend"

    @staticmethod
    def _sector_bucket(sample: WindowSample) -> str:
        value = float(sample.features.get("sector_strength", 0.0))
        if value > 0.03:
            return "sector_strong"
        if value < -0.03:
            return "sector_weak"
        return "sector_neutral"

    @staticmethod
    def _liquidity_bucket(sample: WindowSample) -> str:
        value = float(sample.features.get("liquidity_score", 0.0))
        if value >= 0.70:
            return "liquid"
        if value <= 0.35:
            return "thin"
        return "mid_liquidity"

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {
            "method": "bucket_invariance_proxy",
            "sample_count": 0,
            "invariance_score": 0.0,
            "positive_bucket_rate": 0.0,
            "bucket_groups": {},
            "expected_fail_buckets": [],
            "symbol_dependency": {
                "symbol_count": 0,
                "top_symbol": "",
                "top_symbol_share": 0.0,
                "top3_symbol_share": 0.0,
                "no_three_symbol_dependency": False,
            },
            "coverage_score": 0.0,
            "passed": False,
            "warnings": ["sin muestras para invariancia"],
        }
