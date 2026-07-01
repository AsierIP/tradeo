from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tradeo.core.config import Settings
from tradeo.services.intraday_universe_builder import (
    IntradayUniverseBuilder,
    IntradayUniverseThresholds,
)


class FakeProvider:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.frames = frames

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        return self.frames[symbol].copy()


def _frame(price: float, volume: float, *, rows: int = 160, spike: bool = False) -> pd.DataFrame:
    index = pd.date_range("2026-01-01", periods=rows, freq="30min", tz="UTC")
    close = pd.Series([price * (1.0 + (idx % 7) * 0.0001) for idx in range(rows)], index=index, dtype=float)
    if spike:
        close.iloc[rows // 2] = price * 1.50
    return pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.004,
            "low": close * 0.996,
            "close": close,
            "volume": volume,
        },
        index=index,
    )


def _builder(tmp_path: Path, frames: dict[str, pd.DataFrame]) -> IntradayUniverseBuilder:
    return IntradayUniverseBuilder(
        settings=Settings(market_data_cache_dir=str(tmp_path / "cache")),
        provider_factory=lambda *, cache_refresh_enabled: FakeProvider(frames),
    )


def _liquid_thresholds() -> IntradayUniverseThresholds:
    return IntradayUniverseThresholds(
        min_price=3.0,
        min_median_dollar_volume=1_000_000,
        min_rows=120,
        max_event_bar_return_pct=0.35,
    )


def test_intraday_universe_builder_scores_and_rejects_bad_candidates(tmp_path: Path) -> None:
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "symbol,name,cap_segment,sector,note\n"
        "GOODA,Good A,midcap,tech,ordinary liquid candidate\n"
        "GOODB,Good B,midcap,industrial,ordinary liquid candidate\n"
        "LOWP,Low Price,smallcap,retail,ordinary low price\n"
        "BIOX,Bio X Therapeutics,smallcap,healthcare,clinical biotech\n",
        encoding="utf-8",
    )
    frames = {
        "GOODA": _frame(40.0, 300_000),
        "GOODB": _frame(25.0, 260_000),
        "LOWP": _frame(1.5, 2_000_000),
        "BIOX": _frame(30.0, 300_000, spike=True),
    }
    builder = _builder(tmp_path, frames)

    result = builder.build(
        seed_files=[seed],
        output_path=tmp_path / "universe.csv",
        limit=10,
        period="60d",
        interval="30m",
        thresholds=IntradayUniverseThresholds(
            min_price=3.0,
            min_median_dollar_volume=5_000_000,
            min_rows=120,
            max_event_bar_return_pct=0.35,
        ),
        rotation_salt="test",
    )

    output = pd.read_csv(result.output_path)
    assert result.selected_symbols == ["GOODA", "GOODB"]
    assert set(output.loc[output["selected"], "symbol"]) == {"GOODA", "GOODB"}
    low_reasons = output.loc[output["symbol"] == "LOWP", "reason_codes"].iloc[0]
    bio_reasons = output.loc[output["symbol"] == "BIOX", "reason_codes"].iloc[0]
    assert "price_below_min" in low_reasons
    assert "event_driven_keyword" in bio_reasons
    assert "event_bar_return_high" in bio_reasons
    assert result.metadata["selected_count"] == 2


def test_intraday_universe_builder_uses_bucket_cap_before_backfill(tmp_path: Path) -> None:
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "symbol,name,cap_segment,sector,note\n"
        "TECA,Tech A,midcap,tech,ordinary\n"
        "TECB,Tech B,midcap,tech,ordinary\n"
        "TECC,Tech C,midcap,tech,ordinary\n"
        "FINA,Finance A,midcap,finance,ordinary\n",
        encoding="utf-8",
    )
    frames = {symbol: _frame(30.0 + idx, 300_000) for idx, symbol in enumerate(["TECA", "TECB", "TECC", "FINA"])}
    builder = _builder(tmp_path, frames)

    result = builder.build(
        seed_files=[seed],
        output_path=tmp_path / "universe.csv",
        limit=3,
        thresholds=IntradayUniverseThresholds(
            min_median_dollar_volume=1_000_000,
            min_rows=120,
            max_bucket_pct=0.34,
        ),
        rotation_salt="test",
    )

    assert "FINA" in result.selected_symbols
    assert len(result.selected_symbols) == 3


def test_stock_only_rejects_leveraged_etf_but_keeps_common_stock(tmp_path: Path) -> None:
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "symbol,name,cap_segment,sector,note\n"
        "MSFT,Microsoft Corporation Common Stock,megacap,technology,common stock\n"
        "TQQQ,ProShares UltraPro QQQ ETF,etf,macro,3x leveraged bull fund\n",
        encoding="utf-8",
    )
    frames = {
        "MSFT": _frame(420.0, 500_000),
        "TQQQ": _frame(80.0, 1_000_000),
    }
    builder = _builder(tmp_path, frames)

    result = builder.build(
        seed_files=[seed],
        output_path=tmp_path / "universe.csv",
        limit=10,
        thresholds=IntradayUniverseThresholds(min_median_dollar_volume=1_000_000),
        rotation_salt="test",
    )

    output = pd.read_csv(result.output_path)
    assert result.selected_symbols == ["MSFT"]
    tqqq = output.loc[output["symbol"] == "TQQQ"].iloc[0]
    msft = output.loc[output["symbol"] == "MSFT"].iloc[0]
    assert tqqq["product_class"] == "leveraged_etf"
    assert "leveraged" in tqqq["product_flags"]
    assert tqqq["product_rejection_reason"] == "product_policy:stock_only_excludes_leveraged_etf"
    assert tqqq["reason_codes"] == "product_policy:stock_only_excludes_leveraged_etf"
    assert int(tqqq["rows"]) > 0
    assert bool(tqqq["selected"]) is False
    assert msft["product_class"] == "common_stock"
    assert bool(msft["selected"]) is True
    assert result.metadata["product_policy"] == "stock_only"
    assert result.metadata["reason_counts"]["product_policy:stock_only_excludes_leveraged_etf"] == 1


def test_product_policy_all_keeps_etf_eligible_when_quality_passes(tmp_path: Path) -> None:
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "symbol,name,cap_segment,sector,note\n"
        "TQQQ,ProShares UltraPro QQQ ETF,etf,macro,3x leveraged bull fund\n",
        encoding="utf-8",
    )
    frames = {"TQQQ": _frame(80.0, 1_000_000)}
    builder = IntradayUniverseBuilder(
        settings=Settings(market_data_cache_dir=str(tmp_path / "cache")),
        provider_factory=lambda *, cache_refresh_enabled: FakeProvider(frames),
    )

    result = builder.build(
        seed_files=[seed],
        output_path=tmp_path / "universe.csv",
        limit=10,
        thresholds=IntradayUniverseThresholds(min_median_dollar_volume=1_000_000),
        rotation_salt="test",
        product_policy="all",
    )

    output = pd.read_csv(result.output_path)
    tqqq = output.loc[output["symbol"] == "TQQQ"].iloc[0]
    assert result.selected_symbols == ["TQQQ"]
    assert tqqq["product_class"] == "leveraged_etf"
    assert pd.isna(tqqq["product_rejection_reason"])
    assert not any(reason.startswith("product_policy:") for reason in result.metadata["reason_counts"])


def test_builder_reads_legacy_seed_csv_without_selected_column(tmp_path: Path) -> None:
    seed = tmp_path / "legacy.csv"
    seed.write_text("symbol,name\nMSFT,Microsoft Corporation Common Stock\n", encoding="utf-8")
    frames = {"MSFT": _frame(420.0, 500_000)}
    builder = IntradayUniverseBuilder(
        settings=Settings(market_data_cache_dir=str(tmp_path / "cache")),
        provider_factory=lambda *, cache_refresh_enabled: FakeProvider(frames),
    )

    result = builder.build(
        seed_files=[seed],
        output_path=tmp_path / "universe.csv",
        limit=10,
        thresholds=IntradayUniverseThresholds(min_median_dollar_volume=1_000_000),
        rotation_salt="test",
    )

    output = pd.read_csv(result.output_path)
    assert result.selected_symbols == ["MSFT"]
    assert {"product_class", "product_flags", "product_rejection_reason"}.issubset(output.columns)


def test_stock_only_product_policy_rejects_etf_and_leveraged_candidates(tmp_path: Path) -> None:
    seed = tmp_path / "seed.csv"
    seed.write_text(
        "symbol,name,cap_segment,sector,note,product_class,security_type,leveraged\n"
        "ACME,Acme Software,midcap,technology,common stock,common_stock,stock,false\n"
        "SPY,SPDR S&P 500 ETF,largecap,funds,index ETF,etf,etf,false\n"
        "TQQQ,ProShares UltraPro QQQ,largecap,funds,3x leveraged ETF,etf,etf,true\n",
        encoding="utf-8",
    )
    frames = {
        "ACME": _frame(40.0, 300_000),
        "SPY": _frame(500.0, 2_000_000),
        "TQQQ": _frame(80.0, 1_000_000),
    }

    result = _builder(tmp_path, frames).build(
        seed_files=[seed],
        output_path=tmp_path / "universe.csv",
        limit=10,
        thresholds=_liquid_thresholds(),
        product_policy="stock_only",
        rotation_salt="test",
    )

    output = pd.read_csv(result.output_path)
    rows = output.set_index("symbol")
    assert result.selected_symbols == ["ACME"]
    assert rows.loc["ACME", "status"] == "selected"
    assert rows.loc["SPY", "status"] == "rejected"
    assert rows.loc["TQQQ", "status"] == "rejected"
    assert rows.loc["SPY", "reason_codes"] == "product_policy:stock_only_excludes_etf"
    assert rows.loc["TQQQ", "reason_codes"] == "product_policy:stock_only_excludes_leveraged_etf"
    assert rows.loc["SPY", "product_rejection_reason"] == "product_policy:stock_only_excludes_etf"
    assert rows.loc["TQQQ", "product_rejection_reason"] == "product_policy:stock_only_excludes_leveraged_etf"
    assert result.metadata["reason_counts"]["product_policy:stock_only_excludes_etf"] == 1
    assert result.metadata["reason_counts"]["product_policy:stock_only_excludes_leveraged_etf"] == 1


@pytest.mark.parametrize("product_policy", ["all", "include_funds"])
def test_product_policy_that_includes_funds_does_not_reject_etf_by_class(
    tmp_path: Path,
    product_policy: str,
) -> None:
    seed = tmp_path / f"{product_policy}.csv"
    seed.write_text(
        "symbol,name,cap_segment,sector,note,product_class,security_type,leveraged\n"
        "ETF1,Broad Market ETF,largecap,funds,index ETF,etf,etf,false\n",
        encoding="utf-8",
    )
    frames = {"ETF1": _frame(100.0, 400_000)}

    result = _builder(tmp_path, frames).build(
        seed_files=[seed],
        output_path=tmp_path / f"{product_policy}_universe.csv",
        limit=10,
        thresholds=_liquid_thresholds(),
        product_policy=product_policy,
        rotation_salt="test",
    )

    output = pd.read_csv(result.output_path)
    row = output.set_index("symbol").loc["ETF1"]
    assert result.selected_symbols == ["ETF1"]
    assert row["status"] == "selected"
    assert "product_policy" not in str(row["reason_codes"])


def test_etf_macro_rejects_common_stock_and_keeps_etf_eligible(tmp_path: Path) -> None:
    seed = tmp_path / "etf_macro.csv"
    seed.write_text(
        "symbol,name,cap_segment,sector,note,product_class,security_type\n"
        "ACME,Acme Software,midcap,technology,common stock,common_stock,stock\n"
        "ETF1,Broad Market ETF,largecap,funds,index ETF,etf,etf\n",
        encoding="utf-8",
    )
    frames = {
        "ACME": _frame(40.0, 300_000),
        "ETF1": _frame(100.0, 400_000),
    }

    result = _builder(tmp_path, frames).build(
        seed_files=[seed],
        output_path=tmp_path / "etf_macro_universe.csv",
        limit=10,
        thresholds=_liquid_thresholds(),
        product_policy="etf_macro",
        rotation_salt="test",
    )

    output = pd.read_csv(result.output_path)
    rows = output.set_index("symbol")
    assert result.selected_symbols == ["ETF1"]
    assert rows.loc["ETF1", "status"] == "selected"
    assert rows.loc["ETF1", "product_class"] == "etf"
    assert "product_policy" not in str(rows.loc["ETF1", "reason_codes"])
    assert rows.loc["ACME", "status"] == "rejected"
    assert rows.loc["ACME", "product_class"] == "common_stock"
    assert rows.loc["ACME", "reason_codes"] == "product_policy:etf_macro_excludes_common_stock"
    assert (
        rows.loc["ACME", "product_rejection_reason"]
        == "product_policy:etf_macro_excludes_common_stock"
    )
    assert result.metadata["product_policy"] == "etf_macro"
    assert result.metadata["reason_counts"]["product_policy:etf_macro_excludes_common_stock"] == 1
