from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class FeatureScorer:
    """Lightweight deterministic ML-style scorer.

    In production this class can load a trained sklearn model. The v0 scorer is explicit
    and auditable, which matters more than black-box complexity while the system is in
    paper trading and pattern validation.
    """

    min_score: float = 0.0
    max_score: float = 1.0

    def score(self, features: dict[str, Any]) -> float:
        def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
            return float(max(lo, min(hi, x)))

        depth = float(features.get("cup_depth", 0.0))
        symmetry = float(features.get("rim_symmetry", 0.0))
        smoothness = float(features.get("bottom_smoothness", 0.0))
        handle_depth = float(features.get("handle_depth", 0.0))
        volume_ratio = float(features.get("breakout_volume_ratio", 0.0))
        trend_score = float(features.get("trend_score", 0.0))
        atr_pct = float(features.get("atr_pct", 0.0))
        dryup = float(features.get("volume_dryup", 0.0))

        depth_score = clamp(1 - abs(depth - 0.24) / 0.22)
        handle_score = clamp(1 - handle_depth / 0.18)
        volume_score = clamp((volume_ratio - 1.0) / 1.2)
        atr_score = clamp(1 - atr_pct / 0.16)
        dryup_score = clamp((dryup - 0.6) / 0.7)

        score = (
            0.16 * depth_score
            + 0.16 * symmetry
            + 0.14 * smoothness
            + 0.12 * handle_score
            + 0.18 * volume_score
            + 0.12 * trend_score
            + 0.07 * atr_score
            + 0.05 * dryup_score
        )
        return float(np.clip(score, self.min_score, self.max_score))
