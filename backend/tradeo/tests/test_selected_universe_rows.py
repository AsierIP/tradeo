from __future__ import annotations

from pathlib import Path

from tradeo.services.data_provider import load_universe


def test_legacy_universe_csv_without_selected_column_loads_all_rows(tmp_path: Path) -> None:
    universe = tmp_path / "legacy.csv"
    universe.write_text("symbol,name\nmsft,Microsoft\n nvda,Nvidia\n", encoding="utf-8")

    loaded = load_universe(str(universe))

    assert loaded["symbol"].tolist() == ["MSFT", "NVDA"]


def test_universe_csv_with_selected_column_loads_selected_rows_only(tmp_path: Path) -> None:
    universe = tmp_path / "builder_output.csv"
    universe.write_text(
        "symbol,name,selected,product_class\n"
        "MSFT,Microsoft,true,common_stock\n"
        "TQQQ,ProShares UltraPro QQQ ETF,false,leveraged_etf\n"
        "AAPL,Apple,selected,common_stock\n",
        encoding="utf-8",
    )

    loaded = load_universe(str(universe))

    assert loaded["symbol"].tolist() == ["MSFT", "AAPL"]
