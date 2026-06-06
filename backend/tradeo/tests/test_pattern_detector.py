from __future__ import annotations

from tradeo.services.pattern_detector import CupPatternDetector
from tradeo.services.technical_indicators import seeded_synthetic_ohlcv
from tradeo.core.config import get_settings


def test_detector_runs_without_crash() -> None:
    df = seeded_synthetic_ohlcv("SYNTH", bars=420)
    candidate = CupPatternDetector().detect("SYNTH", df)
    assert candidate is None or candidate.reward_risk >= get_settings().min_reward_risk
