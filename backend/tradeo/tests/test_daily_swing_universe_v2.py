from __future__ import annotations

import json

import pandas as pd

from tradeo.modules.daily_swing.universe_v2 import (
    ETF_MACRO_BUCKET,
    REQUIRED_BUCKETS,
    DailySwingUniverseV2Config,
    DailySwingUniverseV2Builder,
)


def test_default_builder_outputs_required_buckets_and_proxy_market_cap_warning(tmp_path) -> None:
    output = tmp_path / "universe_daily_swing_v2.csv"
    summary_csv = tmp_path / "bucket_summary.csv"
    summary_json = tmp_path / "bucket_summary.json"

    result = DailySwingUniverseV2Builder().build(
        output_path=output,
        summary_csv_path=summary_csv,
        summary_json_path=summary_json,
    )

    assert output.exists()
    assert summary_csv.exists()
    assert summary_json.exists()
    assert result.metadata["missing_required_buckets"] == []
    assert set(result.metadata["selected_by_bucket"]) == set(REQUIRED_BUCKETS)
    assert result.metadata["market_cap_point_in_time"] == {
        "source": "unavailable",
        "method": "proxy",
        "survivorship_warning": True,
    }
    assert set(result.rows.loc[result.rows["selected"], "bucket"]) == set(REQUIRED_BUCKETS)
    assert set(result.rows["market_cap_source"]) == {"unavailable"}
    assert set(result.rows["market_cap_method"]) == {"proxy"}
    assert set(result.rows["market_cap_bucket_method"]) == {"proxy"}
    assert set(result.rows["survivorship_warning"]) == {True}
    required_columns = {
        "symbol",
        "company_name",
        "bucket",
        "bucket_reason",
        "product_class",
        "sector",
        "market_cap_bucket",
        "market_cap_source",
        "liquidity_bucket",
        "avg_dollar_volume_proxy",
        "avg_spread_proxy",
        "volatility_bucket",
        "beta_proxy",
        "daily_history_rows",
        "first_date",
        "last_date",
        "eligible_for_daily_swing",
        "eligible_for_lab_watchlist",
        "eligible_for_research",
        "rejection_reason",
        "data_source",
        "survivorship_warning",
    }
    assert required_columns <= set(result.rows.columns)


def test_etfs_are_selected_only_in_etf_macro_bucket() -> None:
    result = DailySwingUniverseV2Builder().build(
        candidates=[
            {
                "symbol": "SPY",
                "name": "SPDR S&P 500 ETF Trust",
                "bucket": "mega_large_cap",
                "product_type": "ETF",
            },
            {"symbol": "MSFT", "name": "Microsoft Corporation", "bucket": ETF_MACRO_BUCKET},
            {
                "symbol": "QQQ",
                "name": "Invesco QQQ Trust ETF",
                "bucket": ETF_MACRO_BUCKET,
                "product_type": "ETF",
            },
            {"symbol": "AAPL", "name": "Apple Inc.", "bucket": "mega_large_cap"},
        ],
    )

    rows = result.rows.set_index("symbol")
    assert bool(rows.loc["QQQ", "selected"]) is True
    assert rows.loc["QQQ", "bucket"] == ETF_MACRO_BUCKET
    assert bool(rows.loc["AAPL", "selected"]) is True
    assert bool(rows.loc["SPY", "selected"]) is False
    assert "etf_must_use_etf_macro" in rows.loc["SPY", "reason_codes"]
    assert bool(rows.loc["MSFT", "selected"]) is False
    assert "etf_macro_requires_etf" in rows.loc["MSFT", "reason_codes"]

    selected_etfs = result.rows[(result.rows["selected"]) & (result.rows["product_class"] == "etf")]
    assert set(selected_etfs["bucket"]) == {ETF_MACRO_BUCKET}


def test_seed_file_build_is_local_and_writes_summary_payload(tmp_path) -> None:
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "symbol,name,bucket,product_type\n"
        "AAPL,Apple Inc.,mega_large_cap,STK\n"
        "SPY,SPDR S&P 500 ETF Trust,etf_macro,ETF\n",
        encoding="utf-8",
    )
    summary_json = tmp_path / "summary.json"

    result = DailySwingUniverseV2Builder().build(
        seed_files=[seed],
        output_path=tmp_path / "universe.csv",
        summary_csv_path=tmp_path / "summary.csv",
        summary_json_path=summary_json,
    )

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["metadata"]["constraints"]["downloads"] == "none"
    assert payload["metadata"]["seed_files"] == [str(seed)]
    assert payload["metadata"]["selected_count"] == 2
    assert pd.read_csv(result.output_path).shape[0] == 2


def test_verified_pit_market_cap_source_clears_survivorship_warning() -> None:
    result = DailySwingUniverseV2Builder(
        config=DailySwingUniverseV2Config(market_cap_point_in_time_source="wrds-crsp-snapshot")
    ).build(candidates=[{"symbol": "AAPL", "bucket": "mega_large_cap", "product_type": "STK"}])

    assert result.metadata["market_cap_point_in_time"] == {
        "source": "wrds-crsp-snapshot",
        "method": "point_in_time",
        "survivorship_warning": False,
    }


def test_low_liquidity_smallcap_is_rejected_with_warning() -> None:
    result = DailySwingUniverseV2Builder().build(
        candidates=[
            {
                "symbol": "THIN",
                "name": "Thin Smallcap Inc.",
                "bucket": "liquid_small_cap",
                "product_type": "STK",
                "liquidity_score": 0.0,
            }
        ],
    )

    row = result.rows.set_index("symbol").loc["THIN"]
    assert bool(row["selected"]) is False
    assert row["status"] == "rejected"
    assert bool(row["eligible_for_daily_swing"]) is False
    assert "low_liquidity_smallcap_requires_warning" in row["rejection_reason"]
    assert row["liquidity_bucket"] == "illiquid_proxy_rejected"
