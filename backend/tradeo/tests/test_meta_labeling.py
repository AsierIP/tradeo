from __future__ import annotations

import numpy as np

from tradeo.research.meta_labeling import (
    MetaLabelCalibrationConfig,
    expected_calibration_error,
    feature_leakage_guard,
    meta_label_calibration_report,
)


def test_meta_label_calibration_passes_selective_calibrated_probabilities() -> None:
    y = np.array([1] * 10 + [1] * 20 + [0] * 70)
    probabilities = np.array([1.0] * 10 + [2.0 / 9.0] * 90)

    report = meta_label_calibration_report(
        y,
        probabilities,
        config=MetaLabelCalibrationConfig(
            brier_max=0.22,
            ece_max=0.01,
            min_top_decile_uplift=0.60,
            min_samples=100,
            min_top_decile_count=10,
        ),
    )

    assert report["blocked"] is False
    assert report["passed"] is True
    assert report["base_win_rate"] == 0.3
    assert report["top_win_rate"] == 1.0
    assert report["top_decile_uplift"] == 0.7
    assert report["breakeven_probability"] == 0.2
    assert report["selected_expectancy_r_at_breakeven"] > 0


def test_meta_label_calibration_blocks_underpowered_or_invalid_inputs() -> None:
    too_small = meta_label_calibration_report([1, 0], [0.8, 0.2])
    assert too_small["blocked"] is True
    assert too_small["reason"] == "insufficient_samples"

    invalid = meta_label_calibration_report([1, 2] * 30, [0.8, 0.2] * 30)
    assert invalid["blocked"] is True
    assert invalid["reason"] == "labels_must_be_binary"

    bad_probability = meta_label_calibration_report([1, 0] * 30, [1.2, 0.2] * 30)
    assert bad_probability["blocked"] is True
    assert bad_probability["reason"] == "probabilities_must_be_finite_unit_interval"


def test_meta_label_calibration_fails_flat_model_without_uplift() -> None:
    y = np.array([1, 0] * 50)
    probabilities = np.full(100, 0.5)

    report = meta_label_calibration_report(
        y,
        probabilities,
        config=MetaLabelCalibrationConfig(min_samples=100),
    )

    assert report["blocked"] is False
    assert report["passed"] is False
    assert report["top_decile_uplift"] <= 0.0


def test_expected_calibration_error_weighted_bins() -> None:
    y = np.array([1, 1, 0, 0], dtype=float)
    p = np.array([0.75, 0.75, 0.25, 0.25], dtype=float)
    weights = np.array([2.0, 2.0, 1.0, 1.0], dtype=float)

    ece, bins = expected_calibration_error(y, p, sample_weight=weights, n_bins=2)

    assert round(ece, 6) == 0.25
    assert len(bins) == 2
    assert bins[0]["observed_win_rate"] == 0.0
    assert bins[1]["observed_win_rate"] == 1.0


def test_feature_leakage_guard_requires_decision_time_parity() -> None:
    clean = feature_leakage_guard(
        {"entry_quality": 0.7, "atr_pct": 0.02},
        {"entry_quality": 0.7, "atr_pct": 0.02},
    )
    assert clean["passed"] is True

    leaked = feature_leakage_guard(
        {"entry_quality": 0.7, "future_return": 0.4},
        {"entry_quality": 0.7, "future_return": -0.1},
    )
    assert leaked["passed"] is False
    assert leaked["difference_count"] == 1
    assert leaked["differences"][0]["feature"] == "future_return"
