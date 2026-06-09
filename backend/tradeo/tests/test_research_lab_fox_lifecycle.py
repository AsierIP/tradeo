from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import (
    AuditLog,
    DiscoveredPattern,
    DiscoveredPatternStatus,
    Signal,
    SignalStatus,
    Trade,
    TradeStatus,
)
from tradeo.db.session import Base
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.services.director_review_gate import DirectorReviewGate
from tradeo.services.pattern_entry_scanner import PatternEntryScanner
from tradeo.tests.fixtures import fixture_ohlcv


class FixtureProvider:
    def __init__(self, symbol: str = "LFOX") -> None:
        self.symbol = symbol
        self.df = fixture_ohlcv(symbol, bars=260)
        breakout_close = float(self.df["high"].iloc[-21:-1].max()) * 1.01
        self.df.iloc[-1, self.df.columns.get_loc("close")] = breakout_close
        self.df.iloc[-1, self.df.columns.get_loc("open")] = breakout_close * 0.99
        self.df.iloc[-1, self.df.columns.get_loc("high")] = breakout_close * 1.01
        self.df.iloc[-1, self.df.columns.get_loc("low")] = breakout_close * 0.98
        self.df.iloc[-1, self.df.columns.get_loc("volume")] = (
            float(self.df["volume"].iloc[-21:-1].mean()) * 2.0
        )

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d"):
        return self.df.copy()


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def settings() -> Settings:
    return Settings(
        min_avg_dollar_volume=0,
        max_atr_pct=1.0,
        laboratory_market_hours_only=False,
        fox_hunter_market_hours_only=False,
        laboratory_auto_submit_paper_orders=False,
        fox_hunter_auto_submit_live_orders=False,
        fox_hunter_enabled=True,
        entry_max_extension_atr=99.0,
    )


def add_research_approved_pattern(db, provider: FixtureProvider) -> DiscoveredPattern:
    window = provider.df.iloc[-20:]
    vector, _, _ = PatternEmbeddingEngine().embed(window)
    pattern = DiscoveredPattern(
        pattern_key="RESEARCH_OK_PATTERN",
        name="RESEARCH_OK_PATTERN",
        status=DiscoveredPatternStatus.LAB_CANDIDATE,
        promotion_status="lab_candidate",
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=1,
        sample_count=120,
        symbol_count=12,
        year_count=3,
        score=0.9,
        expectancy_r=0.25,
        profit_factor=1.8,
        best_expectancy_r=0.4,
        best_profit_factor=2.0,
        best_rr=4.0,
        validation_passed=True,
        centroid_json=vector.tolist(),
        metrics_json={"scaler_mean": [0.0] * len(vector), "scaler_scale": [1.0] * len(vector)},
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    return pattern


def close_lab_trade(db, signal: Signal, index: int, r_multiple: float = 1.0) -> None:
    signal.status = SignalStatus.EXECUTED
    db.add(
        Trade(
            signal_id=signal.id,
            symbol=signal.symbol,
            pattern=signal.pattern,
            side=signal.side,
            qty=1,
            entry=signal.entry,
            stop=signal.stop,
            target=signal.target,
            status=TradeStatus.CLOSED,
            pnl_usd=100.0 * r_multiple,
            r_multiple=r_multiple,
            metadata_json={"execution_mode": "ibkr", "ibkr_mode": "paper", "case": index},
        )
    )
    db.commit()


def test_research_to_lab_to_director_to_fox_lifecycle() -> None:
    db = session_factory()
    provider = FixtureProvider()
    cfg = settings()
    matcher = NovelPatternMatcher(provider=provider, settings=cfg)
    scanner = PatternEntryScanner(settings=cfg, matcher=matcher)

    pattern = add_research_approved_pattern(db, provider)

    lab_result = scanner.scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )
    assert lab_result["signals_created"] == 1
    first_signal = db.get(Signal, lab_result["signal_ids"][0])
    assert first_signal is not None
    assert first_signal.metadata_json["pattern_id"] == pattern.id

    close_lab_trade(db, first_signal, 0, r_multiple=1.0)
    for index in range(1, 10):
        signal = Signal(
            symbol=provider.symbol,
            pattern=pattern.name,
            side="long",
            entry=first_signal.entry,
            stop=first_signal.stop,
            target=first_signal.target,
            reward_risk=4.0,
            confidence=0.7,
            composite_score=0.7,
            risk_usd=10.0,
            suggested_qty=1,
            strategy_version=f"laboratory_pattern_{pattern.id}",
            status=SignalStatus.EXECUTED,
            human_approved=True,
            metadata_json={"entry_module": "laboratory", "pattern_id": pattern.id},
        )
        db.add(signal)
        db.commit()
        db.refresh(signal)
        close_lab_trade(db, signal, index, r_multiple=1.0)

    review_result = DirectorReviewGate(min_closed_lab_trades=10).refresh(db)
    db.refresh(pattern)
    assert review_result["marked_for_director_review"] == 1
    assert pattern.status == DiscoveredPatternStatus.DIRECTOR_REVIEW
    assert pattern.metrics_json["lab_execution"]["closed_lab_trades"] == 10
    assert pattern.metrics_json["lab_execution"]["lab_expectancy_r"] == 1.0
    assert pattern.metrics_json["lab_execution"]["research_expectancy_r"] == 0.4

    pattern.status = DiscoveredPatternStatus.PRODUCTION
    pattern.promotion_status = "production"
    db.add(
        AuditLog(
            actor="director",
            action="pattern_promoted_to_production",
            entity_type="discovered_pattern",
            entity_id=str(pattern.id),
            details_json={"source_status": "director_review"},
        )
    )
    db.commit()

    fox_result = scanner.scan(
        db,
        module="fox_hunter",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )
    assert fox_result["patterns_checked"] == 1
    assert fox_result["signals_created"] == 1
    fox_signal = db.get(Signal, fox_result["signal_ids"][0])
    assert fox_signal is not None
    assert fox_signal.metadata_json["entry_module"] == "fox_hunter"
    assert fox_signal.pattern == pattern.name
    assert fox_signal.status == SignalStatus.PENDING_HUMAN_APPROVAL
