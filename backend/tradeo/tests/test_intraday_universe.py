from __future__ import annotations

import pandas as pd

from tradeo.modules.intraday.universe import (
    CONTRACT_VERSION,
    IntradayUniverseBuilder,
    IntradayUniverseConfig,
)


def _candidate_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "FAST",
                "price": 8.0,
                "previous_close": 7.2,
                "rvol": 4.0,
                "avg_volume": 400_000,
                "volume": 250_000,
                "bid": 7.99,
                "ask": 8.01,
                "data_ok": True,
            },
            {
                "symbol": "MANU",
                "price": 6.0,
                "gap_pct": 4.0,
                "rvol": 2.0,
                "avg_dollar_volume": 2_500_000,
                "dollar_volume": 900_000,
                "spread_bps": 20.0,
                "data_ok": True,
            },
            {
                "symbol": "LOWP",
                "price": 2.0,
                "gap_pct": 10.0,
                "rvol": 5.0,
                "avg_dollar_volume": 4_000_000,
                "dollar_volume": 600_000,
                "spread_bps": 10.0,
                "data_ok": True,
            },
            {
                "symbol": "WIDE",
                "price": 7.0,
                "gap_pct": 12.0,
                "rvol": 5.0,
                "avg_dollar_volume": 5_000_000,
                "dollar_volume": 800_000,
                "spread_bps": 120.0,
                "data_ok": True,
            },
            {
                "symbol": "BADQ",
                "price": 9.0,
                "gap_pct": 12.0,
                "rvol": 5.0,
                "avg_dollar_volume": 5_000_000,
                "dollar_volume": 800_000,
                "spread_bps": 10.0,
                "data_ok": False,
            },
            {
                "symbol": "SKIP",
                "price": 9.0,
                "gap_pct": 12.0,
                "rvol": 5.0,
                "avg_dollar_volume": 5_000_000,
                "dollar_volume": 800_000,
                "spread_bps": 10.0,
                "data_ok": True,
            },
        ]
    )


def test_universe_builder_filters_and_prioritizes_manual_watchlist_without_safety_bypass() -> None:
    builder = IntradayUniverseBuilder(
        IntradayUniverseConfig(
            min_price=3.0,
            min_abs_gap_pct=3.0,
            min_rvol=1.5,
            min_avg_dollar_volume=1_000_000,
            min_dollar_volume=500_000,
            max_spread_bps=50.0,
            max_symbols=3,
            manual_watchlist=("MANU", "LOWP", "MISS"),
            excluded_symbols=frozenset({"SKIP"}),
        )
    )

    universe = builder.build(_candidate_frame())

    assert universe.contract_version == CONTRACT_VERSION
    assert universe.symbols == ["MANU", "FAST"]
    assert universe.selected[0].manual_watchlist is True
    assert universe.selected[1].manual_watchlist is False

    rejected = {rejection.symbol: rejection.reason for rejection in universe.rejected}
    assert rejected["LOWP"] == "price"
    assert rejected["MISS"] == "missing_metrics"
    assert rejected["WIDE"] == "spread"
    assert rejected["BADQ"] == "data_not_ok"
    assert rejected["SKIP"] == "excluded"


def test_universe_builder_applies_max_symbols_after_safety_filters_deterministically() -> None:
    frame = pd.DataFrame(
        [
            {
                "symbol": symbol,
                "price": 10.0,
                "gap_pct": gap,
                "rvol": 3.0,
                "avg_dollar_volume": 3_000_000,
                "dollar_volume": 700_000,
                "spread_bps": 15.0,
                "data_ok": True,
            }
            for symbol, gap in (("BBB", 5.0), ("AAA", 5.0), ("CCC", 9.0))
        ]
    )
    builder = IntradayUniverseBuilder(IntradayUniverseConfig(max_symbols=2))

    first = builder.build(frame)
    second = builder.build(frame.sample(frac=1.0, random_state=7))

    assert first.symbols == ["CCC", "AAA"]
    assert second.symbols == first.symbols
    assert {rejection.symbol: rejection.reason for rejection in first.rejected} == {"BBB": "max_symbols"}
