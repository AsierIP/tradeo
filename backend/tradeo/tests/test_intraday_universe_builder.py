from __future__ import annotations

from pathlib import Path

import pandas as pd

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
    builder = IntradayUniverseBuilder(
        settings=Settings(market_data_cache_dir=str(tmp_path / "cache")),
        provider_factory=lambda *, cache_refresh_enabled: FakeProvider(frames),
    )

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
        "T1,Tech 1,midcap,tech,ordinary\n"
        "T2,Tech 2,midcap,tech,ordinary\n"
        "T3,Tech 3,midcap,tech,ordinary\n"
        "F1,Finance 1,midcap,finance,ordinary\n",
        encoding="utf-8",
    )
    frames = {symbol: _frame(30.0 + idx, 300_000) for idx, symbol in enumerate(["T1", "T2", "T3", "F1"])}
    builder = IntradayUniverseBuilder(
        settings=Settings(market_data_cache_dir=str(tmp_path / "cache")),
        provider_factory=lambda *, cache_refresh_enabled: FakeProvider(frames),
    )

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

    assert "F1" in result.selected_symbols
    assert len(result.selected_symbols) == 3
