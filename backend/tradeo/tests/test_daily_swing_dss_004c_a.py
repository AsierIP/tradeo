from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from tradeo.modules.daily_swing.dss_004c_a import (
    SpecificityConfig,
    _final_decision,
    matched_baseline_audit,
    run_dss_004c_a_specificity,
)


def _bars(symbol: str, days: int = 390, fake_holiday: bool = False) -> pd.DataFrame:
    rows = []
    cursor = date(2024, 1, 2)
    price = 100.0
    while len(rows) < days:
        if cursor.weekday() < 5 and cursor.isoformat() != "2026-07-03":
            if len(rows) > 170 and len(rows) % 30 == 0:
                price *= 1.055
            else:
                price *= 1.0015
            rows.append(
                {
                    "symbol": symbol,
                    "date": cursor.isoformat(),
                    "open": price * 0.998,
                    "high": price * 1.003,
                    "low": price * 0.997,
                    "close": price,
                    "volume": 1_000_000,
                }
            )
        cursor += timedelta(days=1)
    if fake_holiday:
        rows.append(
            {
                "symbol": symbol,
                "date": "2026-07-03",
                "open": 1,
                "high": 1,
                "low": 1,
                "close": 1,
                "volume": 1,
            }
        )
    return pd.DataFrame(rows)


def _write_fixture(tmp_path, universe_text: str | None = None, fake_holiday: bool = False) -> tuple:
    cache = tmp_path / "cache"
    cache.mkdir()
    for symbol in ("AAPL", "MSFT", "SPY", "QQQ"):
        _bars(symbol, fake_holiday=fake_holiday and symbol == "AAPL").to_csv(cache / f"{symbol}.csv", index=False)
    universe = tmp_path / "universe.csv"
    universe.write_text(
        universe_text
        or (
            "symbol,benchmark_only,operational_eligible,product_type\n"
            "AAPL,false,true,STK\n"
            "MSFT,false,true,STK\n"
            "SPY,true,false,STK\n"
            "QQQ,true,false,STK\n"
        ),
        encoding="utf-8",
    )
    return cache, universe, tmp_path / "out"


def _config(cache, universe, out) -> SpecificityConfig:
    return SpecificityConfig(
        cache_dir=cache,
        universe_path=universe,
        start_date="2024-01-02",
        end_date="2026-07-02",
        is_end_date="2024-12-31",
        oos_start_date="2025-01-01",
        output_dir=out,
    )


def test_dss_004c_a_placebo_oos_separated_from_full_sample(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_004c_a_specificity(_config(cache, universe, out))
    placebo = pd.read_csv(out / "dss_004c_a_placebo_oos.csv")
    assert set(placebo["signal_shift_days"]) == {0, 1, 2, 3, 5, 10}
    assert "OOS_expectancy_net_x2_pct" in placebo.columns
    assert result["placebo"]["summary"]["base_oos_expectancy_net_x2_pct"] is not None


def test_dss_004c_a_baselines_do_not_use_future_data(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    run_dss_004c_a_specificity(_config(cache, universe, out))
    guards = pd.read_json(out / "dss_004c_a_guards_summary.json")
    assert guards.loc["entry_date_after_signal_date", "checks"]
    assert guards.loc["signal_t_entry_t_plus_1", "checks"]


def test_dss_004c_a_random_matched_reproducible_seed(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    first = run_dss_004c_a_specificity(_config(cache, universe, out))
    second_table, second_summary = matched_baseline_audit(
        {symbol: pd.read_csv(cache / f"{symbol}.csv") for symbol in ("AAPL", "MSFT")},
        pd.Series(True, index=pd.read_csv(cache / "SPY.csv")["date"].astype(str)),
        _config(cache, universe, out),
        first["base_trades"],
    )
    first_random = first["baselines"]["table"].query("variant == 'RANDOM_MATCHED'").reset_index(drop=True)
    second_random = second_table.query("variant == 'RANDOM_MATCHED'").reset_index(drop=True)
    pd.testing.assert_frame_equal(first_random, second_random)
    assert second_summary["random_seed"] == 40401


def test_dss_004c_a_excludes_spy_qqq_from_trades(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path)
    result = run_dss_004c_a_specificity(_config(cache, universe, out))
    assert not set(result["base_trades"]["symbol"]) & {"SPY", "QQQ"}
    assert result["guards"]["checks"]["excludes_spy_qqq_from_trades"]


def test_dss_004c_a_rejects_fake_2026_07_03_bar(tmp_path) -> None:
    cache, universe, out = _write_fixture(tmp_path, fake_holiday=True)
    with pytest.raises(ValueError, match="2026-07-03"):
        run_dss_004c_a_specificity(_config(cache, universe, out))


def test_dss_004c_a_decision_requires_placebo_and_baseline_results() -> None:
    assert _final_decision("PLACEBO_SPECIFICITY_PASS", "BASELINE_PASS", "PASS") == "DSS_BO_001_SPECIFICITY_CONTINUES"
    assert _final_decision("PLACEBO_FAIL", "BASELINE_PASS", "PASS") == "DSS_BO_001_PLACEBO_FAIL"
    assert _final_decision("PLACEBO_SPECIFICITY_PASS", "BASELINE_FAIL", "PASS") == "DSS_BO_001_BASELINE_EXPLAINED_FAIL"
    assert _final_decision("PLACEBO_SPECIFICITY_PASS", "BASELINE_PASS", "FAIL") == "DSS_BO_001_INCONCLUSIVE"
