from __future__ import annotations

from pathlib import Path

import pandas as pd

from tradeo.modules.daily_swing.dss_004g_c import (
    bh_qvalues,
    build_test_matrix,
    fdr_light,
    final_decision,
    timing_verdict,
    wrc_spa_light,
)


def _trades(strategy_id: str, returns: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "strategy_id": strategy_id,
            "symbol": [f"S{i % 3}" for i in range(len(returns))],
            "symbol_month": [f"S{i % 3}-2025-{(i % 4) + 1:02d}" for i in range(len(returns))],
            "first_signal_date": ["2025-01-02"] * len(returns),
            "episode_id": [f"E{i}" for i in range(len(returns))],
            "trade_id": [f"T{i}" for i in range(len(returns))],
            "net_return_x2_pct": returns,
        }
    )


class _Config:
    bootstrap_iterations = 20
    oos_start_date = "2025-01-01"


def test_dss_004g_c_test_matrix_is_closed() -> None:
    matrix = build_test_matrix(Path("artifacts/runtime/daily_swing"))
    assert matrix["strategy_id"].tolist() == [
        "DSS_CW_001_BASE_MAX2",
        "DSS_CW_WINDOW_PLACEBO_PLUS_1",
        "DSS_CW_WINDOW_PLACEBO_PLUS_2",
        "DSS_CW_WINDOW_PLACEBO_PLUS_5",
        "DSS_CW_WINDOW_PLACEBO_PLUS_10",
        "DSS_CO_001_MAX2",
        "TREND_ONLY_EPISODE_LIKE",
        "RANDOM_MATCHED_EPISODE_LIKE",
        "VOL_HIGH_ONLY_EPISODE_LIKE",
        "DSS_BO_001_REFERENCE",
    ]
    assert not matrix[matrix["strategy_id"] == "DSS_BO_001_REFERENCE"]["included_in_stat_family"].iloc[0]


def test_dss_004g_c_uses_artifacts_not_chat_metrics() -> None:
    matrix = build_test_matrix(Path("artifacts/runtime/daily_swing"))
    base = matrix[matrix["strategy_id"] == "DSS_CW_001_BASE_MAX2"].iloc[0]
    co = matrix[matrix["strategy_id"] == "DSS_CO_001_MAX2"].iloc[0]
    assert "dss_cw_001_trades_max2_episode.csv" in base["source_artifact"]
    assert "dss_004e_dss_co_001_trades_max2_sim.csv" in co["source_artifact"]
    assert not any("chat" in str(value).lower() for value in matrix["source_artifact"])


def test_dss_004g_c_fdr_bh_qvalues_monotonic() -> None:
    qvalues = bh_qvalues([0.04, 0.01, 0.03])
    ordered = sorted(zip([0.04, 0.01, 0.03], qvalues))
    assert [q for _, q in ordered] == sorted(q for _, q in ordered)


def test_dss_004g_c_bootstrap_reproducible_seed() -> None:
    family = {
        "DSS_CW_001_BASE_MAX2": _trades("DSS_CW_001_BASE_MAX2", [1, 1, -0.5, 0.8]),
        "DSS_CW_WINDOW_PLACEBO_PLUS_1": _trades("DSS_CW_WINDOW_PLACEBO_PLUS_1", [1.2, 1.1, -0.3, 0.9]),
    }
    first, first_summary = fdr_light(family, _Config())
    second, second_summary = fdr_light(family, _Config())
    pd.testing.assert_frame_equal(first, second)
    assert {k: v for k, v in first_summary.items() if k != "generated_at"} == {
        k: v for k, v in second_summary.items() if k != "generated_at"
    }


def test_dss_004g_c_placebo_dominance_blocks_pass() -> None:
    family = {
        "DSS_CW_001_BASE_MAX2": _trades("DSS_CW_001_BASE_MAX2", [0.4, 0.2, -0.1, 0.3]),
        "DSS_CW_WINDOW_PLACEBO_PLUS_1": _trades("DSS_CW_WINDOW_PLACEBO_PLUS_1", [0.6, 0.4, 0.1, 0.5]),
        "DSS_CW_WINDOW_PLACEBO_PLUS_2": _trades("DSS_CW_WINDOW_PLACEBO_PLUS_2", [0.7, 0.4, 0.1, 0.5]),
    }
    fdr, fdr_summary = fdr_light(family, _Config())
    timing = timing_verdict(fdr, family)
    assert fdr_summary["decision"] == "FDR_PLACEBO_DOMINANCE_FAIL"
    assert timing["decision"] == "TIMING_PLACEBO_DOMINANCE_FAIL"


def test_dss_004g_c_decision_requires_fdr_and_timing_verdict() -> None:
    decision = final_decision(
        {"decision": "FDR_BASE_PASS"},
        {"decision": "WRC_SPA_BASE_PASS"},
        {"decision": "TIMING_PLACEBO_DOMINANCE_FAIL"},
    )
    assert decision == "DSS_CW_001_RESEARCH_FAIL_TIMING_NOT_SPECIFIC"


def test_dss_004g_c_does_not_generate_signals_or_preview() -> None:
    decision = final_decision(
        {"decision": "FDR_BASE_PASS"},
        {"decision": "WRC_SPA_BASE_PASS"},
        {"decision": "TIMING_SPECIFICITY_PASS"},
    )
    assert decision == "DSS_CW_001_RESEARCH_SURVIVES_STAT_LIGHT"


def test_dss_004g_c_wrc_reproducible_family_seed() -> None:
    family = {
        "DSS_CW_001_BASE_MAX2": _trades("DSS_CW_001_BASE_MAX2", [1, -0.1, 0.7, 0.4]),
        "DSS_CW_WINDOW_PLACEBO_PLUS_1": _trades("DSS_CW_WINDOW_PLACEBO_PLUS_1", [1.2, 0.1, 0.8, 0.5]),
    }
    first_boot, first_summary = wrc_spa_light(family, _Config())
    second_boot, second_summary = wrc_spa_light(family, _Config())
    pd.testing.assert_frame_equal(first_boot, second_boot)
    assert {k: v for k, v in first_summary.items() if k != "generated_at"} == {
        k: v for k, v in second_summary.items() if k != "generated_at"
    }
