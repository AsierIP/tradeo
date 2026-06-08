from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import DiscoveredPattern, DiscoveredPatternStatus, Signal, SignalStatus
from tradeo.db.session import Base
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.services.pattern_entry_scanner import (
    PatternEntryScanner,
    PatternEntryScannerSafetyError,
)
from tradeo.tests.fixtures import fixture_ohlcv


class FixtureProvider:
    def __init__(self, symbol: str = "LABX") -> None:
        self.symbol = symbol
        self.df = fixture_ohlcv(symbol, bars=260)

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d"):
        return self.df.copy()


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def add_pattern(
    db,
    provider: FixtureProvider,
    *,
    status: DiscoveredPatternStatus,
) -> DiscoveredPattern:
    window = provider.df.iloc[-20:]
    vector, _, _ = PatternEmbeddingEngine().embed(window)
    pattern = DiscoveredPattern(
        pattern_key=f"{status.value}_key",
        name=f"{status.value}_pattern",
        status=status,
        side="long",
        timeframe="1d",
        window_size=20,
        sample_count=120,
        symbol_count=12,
        year_count=3,
        score=0.9,
        reward_risk_estimate=4.0,
        expectancy_r=0.4,
        profit_factor=2.1,
        win_rate=0.55,
        stability_score=0.8,
        out_of_sample_expectancy_r=0.3,
        out_of_sample_profit_factor=1.9,
        best_rr=4.0,
        validation_passed=True,
        promotion_status=status.value,
        centroid_json=vector.tolist(),
        metrics_json={"scaler_mean": [0.0] * len(vector), "scaler_scale": [1.0] * len(vector)},
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


def scanner(provider: FixtureProvider, **settings_overrides) -> PatternEntryScanner:
    settings = Settings(
        min_avg_dollar_volume=0,
        max_atr_pct=1.0,
        laboratory_auto_submit_paper_orders=False,
        fox_hunter_enabled=False,
        **settings_overrides,
    )
    matcher = NovelPatternMatcher(provider=provider, settings=settings)
    return PatternEntryScanner(settings=settings, matcher=matcher)


def test_laboratory_scanner_creates_paper_signal_for_validated_lab_pattern() -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    result = scanner(provider).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )

    assert result["matches_found"] == 1
    assert result["signals_created"] == 1
    signal_id = result["signal_ids"][0]
    signal = db.get(Signal, signal_id)
    assert signal.status == SignalStatus.PAPER_APPROVED
    assert signal.human_approved is False
    assert signal.metadata_json["entry_module"] == "laboratory"


def test_fox_hunter_ignores_lab_patterns_and_uses_production_only() -> None:
    db = session_factory()
    provider = FixtureProvider("FOXX")
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    production = add_pattern(db, provider, status=DiscoveredPatternStatus.PRODUCTION)

    result = scanner(provider).scan(
        db,
        module="fox_hunter",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )

    assert result["patterns_checked"] == 1
    assert result["signals_created"] == 1
    signal = db.get(Signal, result["signal_ids"][0])
    assert signal.pattern == production.name
    assert signal.status == SignalStatus.PENDING_HUMAN_APPROVAL
    assert signal.metadata_json["entry_module"] == "fox_hunter"


def test_laboratory_refuses_live_port_execution() -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    live_port_scanner = scanner(
        provider,
        trading_mode="paper",
        ibkr_port=4001,
    )

    try:
        live_port_scanner.scan(
            db,
            module="laboratory",
            symbols=[provider.symbol],
            execute_orders=True,
        )
    except PatternEntryScannerSafetyError as exc:
        assert "refuses live IBKR ports" in str(exc)
    else:
        raise AssertionError("Laboratory must not execute through live IBKR ports")
