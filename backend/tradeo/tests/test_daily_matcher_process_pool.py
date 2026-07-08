from __future__ import annotations

import hashlib
import os
from typing import Any

import numpy as np
import pandas as pd

from tradeo.core.config import Settings
from tradeo.db.models import DiscoveredPatternMatch, DiscoveredPatternStatus
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.tests.test_pattern_entry_scanner import add_pattern, session_factory


def stable_ohlcv(symbol: str, bars: int = 360) -> pd.DataFrame:
    seed = int.from_bytes(hashlib.blake2b(symbol.encode(), digest_size=8).digest(), "big")
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0005, 0.02, bars)
    price = 30 * np.exp(np.cumsum(returns))
    open_ = price * (1 + rng.normal(0, 0.006, bars))
    high = np.maximum(open_, price) * (1 + rng.uniform(0.004, 0.02, bars))
    low = np.minimum(open_, price) * (1 - rng.uniform(0.004, 0.02, bars))
    volume = rng.integers(600_000, 4_000_000, bars).astype(float)
    volume[-1] *= 1.8
    index = pd.date_range(end=pd.Timestamp("2026-06-30", tz="UTC"), periods=bars, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": price, "volume": volume},
        index=index,
    )


class StablePidGuardedProvider:
    def __init__(self, symbols: list[str], bars: int = 360) -> None:
        self.parent_pid = os.getpid()
        self.symbol = symbols[0]
        self.symbols = symbols
        all_symbols = set(symbols) | {"SPY", "QQQ"}
        self.frames = {symbol: stable_ohlcv(symbol, bars=bars) for symbol in all_symbols}
        self.df = self.frames[self.symbol]
        self.fetch_calls: list[tuple[int, str, str, str]] = []

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        if os.getpid() != self.parent_pid:
            raise AssertionError("process-pool workers must not fetch provider data")
        key = symbol.upper()
        self.fetch_calls.append((os.getpid(), key, period, interval))
        return self.frames[key].copy()


def matcher_settings(*, process_pool: bool = False) -> Settings:
    return Settings(
        discovery_match_complete_bars_only=False,
        discovery_match_similarity_threshold=0.0,
        discovery_match_max_patterns=0,
        discovery_match_max_results=0,
        discovery_match_per_pattern_threshold=False,
        discovery_match_ambiguity_hard_gate_enabled=False,
        discovery_match_conformal_gate_enabled=False,
        discovery_match_knn_enabled=False,
        discovery_match_shape_dtw_enabled=False,
        entry_gate_enabled=False,
        entry_variant_max_per_pattern_symbol=1,
        data_quality_filter_enabled=False,
        discovery_match_process_pool_enabled=process_pool,
        discovery_match_process_workers=2,
        discovery_match_process_min_symbols=1,
        discovery_match_native_threads_per_process=1,
        discovery_match_process_start_method="fork",
    )


def stable_matches(result: dict[str, Any]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            match["symbol"],
            match["timeframe"],
            match["pattern_id"],
            match["entry_variant_id"],
            match["status"],
            round(float(match["score"]), 8),
            round(float(match["similarity"]), 8),
            round(float(match["entry_score"]), 8),
            bool(match["entry_gate_passed"]),
            match["window_end"],
        )
        for match in result["matches"]
    )


def test_daily_matcher_process_pool_matches_serial_store_false(monkeypatch) -> None:
    db = session_factory()
    symbols = [f"SYM{i:03d}" for i in range(18)]
    provider = StablePidGuardedProvider(symbols=symbols)
    for i in range(6):
        add_pattern(
            db,
            provider,
            status=DiscoveredPatternStatus.PAPER_CANDIDATE,
            key_suffix=f"_paper_{i}",
        )

    def fail_store(*args, **kwargs):
        raise AssertionError("store=False must not call _store_matches")

    monkeypatch.setattr(NovelPatternMatcher, "_store_matches", fail_store)

    serial = NovelPatternMatcher(
        provider=provider,
        settings=matcher_settings(process_pool=False),
    ).match_current(db, symbols=symbols, module="daily", store=False)
    process = NovelPatternMatcher(
        provider=provider,
        settings=matcher_settings(process_pool=True),
    ).match_current(db, symbols=symbols, module="daily", store=False)

    assert serial["execution_mode"] == "serial"
    assert process["execution_mode"] == "process_pool"
    assert process["stored_matches"] == 0
    assert db.query(DiscoveredPatternMatch).count() == 0
    assert process["patterns_checked"] == serial["patterns_checked"]
    assert process["symbols_checked"] == serial["symbols_checked"]
    assert process["symbols_by_timeframe"] == serial["symbols_by_timeframe"]
    assert process["regime_gate_blocked"] == serial["regime_gate_blocked"]
    assert process["reward_risk_gate_blocked"] == serial["reward_risk_gate_blocked"]
    assert process["ambiguity_gate_blocked"] == serial["ambiguity_gate_blocked"]
    assert stable_matches(process) == stable_matches(serial)
    assert {pid for pid, *_ in provider.fetch_calls} == {provider.parent_pid}
