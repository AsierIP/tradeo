from __future__ import annotations

import numpy as np

from tradeo.research.conformal_matching import (
    false_positive_rate_at_threshold,
    split_conformal_similarity_threshold,
)


def test_split_conformal_similarity_threshold_controls_recall_contract() -> None:
    similarities = np.linspace(0.50, 0.99, 50)

    report = split_conformal_similarity_threshold(similarities, alpha=0.10)

    assert report["blocked"] is False
    assert report["method"] == "split_conformal_similarity_threshold_v1"
    assert report["target_recall"] == 0.9
    assert report["calibration_count"] == 50
    assert report["recall_on_calibration"] >= 0.9
    assert 0.0 <= report["similarity_threshold"] <= 1.0


def test_split_conformal_similarity_threshold_blocks_invalid_inputs() -> None:
    too_small = split_conformal_similarity_threshold([0.8, 0.9], min_calibration_count=3)
    assert too_small["blocked"] is True
    assert too_small["reason"] == "insufficient_calibration_members"

    out_of_range = split_conformal_similarity_threshold([0.8] * 20 + [1.2])
    assert out_of_range["blocked"] is True
    assert out_of_range["reason"] == "similarities_must_be_unit_interval"

    bad_alpha = split_conformal_similarity_threshold([0.8] * 20, alpha=1.0)
    assert bad_alpha["blocked"] is True
    assert bad_alpha["reason"] == "alpha_must_be_between_0_and_1"


def test_false_positive_rate_at_threshold() -> None:
    report = false_positive_rate_at_threshold([0.2, 0.4, 0.7, 0.9], threshold=0.65)

    assert report["blocked"] is False
    assert report["false_positive_count"] == 2
    assert report["fpr"] == 0.5
    assert report["max_negative_similarity"] == 0.9


def test_false_positive_rate_blocks_empty_bank() -> None:
    report = false_positive_rate_at_threshold([], threshold=0.5)

    assert report["blocked"] is True
    assert report["reason"] == "no_negative_similarities"
