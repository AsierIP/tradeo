from __future__ import annotations

import numpy as np

from tradeo.research.sequential_tests import (
    alpha_spending_boundary,
    alpha_spending_evaluation,
    normal_msprt_edge,
)


def test_alpha_spending_boundary_gets_less_strict_over_time() -> None:
    early = alpha_spending_boundary(look_index=2, max_looks=20, alpha=0.05)
    late = alpha_spending_boundary(look_index=20, max_looks=20, alpha=0.05)

    assert early["method"] == "obrien_fleming"
    assert early["cumulative_alpha_spent"] < late["cumulative_alpha_spent"]
    assert early["z_boundary"] > late["z_boundary"]


def test_alpha_spending_evaluation_supports_strong_edge() -> None:
    lab_r = np.full(20, 0.35)

    result = alpha_spending_evaluation(
        lab_r,
        max_looks=20,
        min_edge_r=0.10,
        sigma=0.40,
        alpha=0.05,
    )

    assert result["diagnostic_only"] is True
    assert result["decision"] == "edge_supported"
    assert result["z_stat"] > result["boundary"]["z_boundary"]


def test_normal_msprt_edge_reports_bayes_factor_decision() -> None:
    lab_r = np.full(18, 0.45)

    result = normal_msprt_edge(
        lab_r,
        null_mean=0.0,
        prior_mean=0.40,
        prior_sd=0.15,
        sigma=0.50,
        alpha=0.05,
    )

    assert result["method"] == "normal_mixture_sprt_v1"
    assert result["decision"] == "edge_supported"
    assert result["log_bayes_factor"] >= result["edge_threshold"]
