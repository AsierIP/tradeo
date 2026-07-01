from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "build_us_listed_stock_candidates.py"
SPEC = importlib.util.spec_from_file_location("build_us_listed_stock_candidates", SCRIPT_PATH)
assert SPEC is not None
builder = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(builder)


def _write_inputs(tmp_path: Path, *, nasdaq_rows: str = "", otherlisted_rows: str = "") -> tuple[Path, Path]:
    nasdaq = tmp_path / "nasdaqlisted.txt"
    otherlisted = tmp_path / "otherlisted.txt"
    nasdaq.write_text(
        "Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
        f"{nasdaq_rows}"
        "File Creation Time: 0701202600:00|||||||\n",
        encoding="utf-8",
    )
    otherlisted.write_text(
        "ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n"
        f"{otherlisted_rows}"
        "File Creation Time: 0701202600:00|||||||\n",
        encoding="utf-8",
    )
    return nasdaq, otherlisted


def _build(tmp_path: Path, *, nasdaq_rows: str = "", otherlisted_rows: str = "", include_adrs: bool = True):
    nasdaq, otherlisted = _write_inputs(tmp_path, nasdaq_rows=nasdaq_rows, otherlisted_rows=otherlisted_rows)
    return builder.build_candidates(
        nasdaq_source=str(nasdaq),
        otherlisted_source=str(otherlisted),
        include_adrs=include_adrs,
    )


def test_nasdaq_etf_is_excluded(tmp_path: Path) -> None:
    result = _build(tmp_path, nasdaq_rows="QQQ|Invesco QQQ Trust ETF|Q|N|N|100|Y|N\n")

    assert result["rows"] == []
    assert result["excluded_counts"]["nasdaq_etf"] == 1


def test_test_issue_is_excluded(tmp_path: Path) -> None:
    result = _build(tmp_path, nasdaq_rows="TEST|Test Company Common Stock|Q|Y|N|100|N|N\n")

    assert result["rows"] == []
    assert result["excluded_counts"]["nasdaq_test_issue"] == 1


def test_warrant_unit_and_right_are_excluded(tmp_path: Path) -> None:
    result = _build(
        tmp_path,
        nasdaq_rows=(
            "ABCW|ABC Corp Warrant|Q|N|N|100|N|N\n"
            "ABCU|ABC Corp Unit|Q|N|N|100|N|N\n"
            "ABCR|ABC Corp Right|Q|N|N|100|N|N\n"
        ),
    )

    assert result["rows"] == []
    assert result["excluded_counts"]["nasdaq_excluded_text"] == 3


def test_common_stock_is_included(tmp_path: Path) -> None:
    result = _build(tmp_path, nasdaq_rows="MSFT|Microsoft Corporation Common Stock|Q|N|N|100|N|N\n")

    assert [row["symbol"] for row in result["rows"]] == ["MSFT"]
    assert result["rows"][0]["candidate_type"] == "common_stock"
    assert result["rows"][0]["is_adr"] is False


def test_adr_ads_is_included_when_enabled(tmp_path: Path) -> None:
    result = _build(tmp_path, nasdaq_rows="ASML|ASML Holding N.V. American Depositary Shares|Q|N|N|100|N|N\n")

    assert [row["symbol"] for row in result["rows"]] == ["ASML"]
    assert result["rows"][0]["candidate_type"] == "adr"
    assert result["rows"][0]["is_adr"] is True


def test_adr_ads_is_excluded_when_disabled(tmp_path: Path) -> None:
    result = _build(
        tmp_path,
        nasdaq_rows="ASML|ASML Holding N.V. American Depositary Shares|Q|N|N|100|N|N\n",
        include_adrs=False,
    )

    assert result["rows"] == []
    assert result["excluded_counts"]["nasdaqlisted_adr_disabled"] == 1


def test_ads_prefix_company_name_is_not_adr(tmp_path: Path) -> None:
    result = _build(tmp_path, nasdaq_rows="ADSE|ADS-TEC ENERGY PLC - Ordinary Shares|Q|N|N|100|N|N\n")

    assert [row["symbol"] for row in result["rows"]] == ["ADSE"]
    assert result["rows"][0]["candidate_type"] == "ordinary_share"
    assert result["rows"][0]["is_adr"] is False


def test_otherlisted_etf_is_excluded(tmp_path: Path) -> None:
    result = _build(tmp_path, otherlisted_rows="SPY|SPDR S&P 500 ETF|P|SPY|Y|100|N|SPY\n")

    assert result["rows"] == []
    assert result["excluded_counts"]["otherlisted_etf"] == 1


def test_metadata_includes_counts(tmp_path: Path) -> None:
    result = _build(
        tmp_path,
        nasdaq_rows=(
            "MSFT|Microsoft Corporation Common Stock|Q|N|N|100|N|N\n"
            "QQQ|Invesco QQQ Trust ETF|Q|N|N|100|Y|N\n"
        ),
        otherlisted_rows="BABA|Alibaba Group Holding Limited American Depositary Shares|N|BABA|N|100|N|BABA\n",
    )
    metadata = {
        "raw_nasdaq_rows": result["raw_nasdaq_rows"],
        "raw_otherlisted_rows": result["raw_otherlisted_rows"],
        "output_rows": len(result["rows"]),
        "excluded_counts": dict(result["excluded_counts"]),
        "candidate_type_counts": {
            candidate_type: sum(1 for row in result["rows"] if row["candidate_type"] == candidate_type)
            for candidate_type in {row["candidate_type"] for row in result["rows"]}
        },
    }

    assert metadata["raw_nasdaq_rows"] == 2
    assert metadata["raw_otherlisted_rows"] == 1
    assert metadata["output_rows"] == 2
    assert metadata["excluded_counts"]["nasdaq_etf"] == 1
    assert metadata["candidate_type_counts"] == {"adr": 1, "common_stock": 1}
