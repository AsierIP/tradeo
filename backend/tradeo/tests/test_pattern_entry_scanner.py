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
        self.fetch_calls: list[tuple[str, str, str]] = []

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d"):
        self.fetch_calls.append((symbol.upper(), period, interval))
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
    defaults = {
        "min_avg_dollar_volume": 0,
        "max_atr_pct": 1.0,
        "laboratory_auto_submit_paper_orders": False,
        "laboratory_market_hours_only": False,
        "fox_hunter_enabled": False,
        "fox_hunter_market_hours_only": False,
        "entry_gate_enabled": False,
        "entry_min_quality_score": 0.0,
        "entry_cooldown_minutes": 0,
    }
    defaults.update(settings_overrides)
    settings = Settings(**defaults)
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
    assert signal.metadata_json["entry_quality_score"] > 0
    assert signal.metadata_json["entry_quality"]["label"] in {"blocked", "weak", "watch", "actionable", "high"}
    assert isinstance(signal.metadata_json["entry_quality"]["flags"], list)
    assert signal.metadata_json["opportunity_rank"] == 1
    assert signal.metadata_json["opportunity_rank_score"] > 0
    assert signal.metadata_json["signal_snapshot"]["symbol"] == provider.symbol
    assert signal.metadata_json["signal_snapshot"]["risk"]["approved"] is True


def test_laboratory_scanner_marks_ibkr_bracket_failure_retryable(monkeypatch) -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    class BrokenBroker:
        def __init__(self, settings) -> None:
            self.settings = settings

        def submit_signal_bracket(self, db, signal, *, reason: str = "manual"):
            raise RuntimeError("IBKR did not acknowledge every bracket leg with a permId")

    monkeypatch.setattr("tradeo.services.pattern_entry_scanner.IBKRBroker", BrokenBroker)

    result = scanner(provider, ibkr_readonly=False).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=True,
    )

    signal = db.get(Signal, result["signal_ids"][0])
    outcome = signal.metadata_json["execution_outcome"]
    assert result["orders_submitted"] == 0
    assert result["order_errors"][0]["reason_code"] == "ibkr_bracket_not_accepted"
    assert result["order_errors"][0]["retryable"] is True
    assert outcome["status"] == "retry_order_submission"
    assert outcome["next_action"] == "retry_order_submission"


def test_laboratory_scanner_rejects_match_without_entry_trigger() -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    class NoTriggerMatcher:
        def match_current(self, *args, **kwargs):
            return {
                "patterns_checked": 1,
                "symbols_checked": 1,
                "matches": [
                    {
                        "module": "laboratory",
                        "pattern_id": 1,
                        "pattern_name": "no_trigger_pattern",
                        "pattern_key": "no_trigger_key",
                        "pattern_status": "lab_candidate",
                        "pattern_promotion_status": "lab_candidate",
                        "symbol": provider.symbol,
                        "timeframe": "1d",
                        "side": "long",
                        "similarity": 0.9,
                        "score": 0.9,
                        "entry_score": 0.2,
                        "entry_gate_passed": False,
                        "entry_trigger": "no_operational_trigger",
                        "entry_price": 10.0,
                        "stop_price": 9.0,
                        "target_price": 14.0,
                        "reward_risk": 4.0,
                        "metrics": {
                            "features": {"avg_dollar_volume": 10_000_000, "atr_pct": 0.04},
                            "entry_gate": {
                                "passed": False,
                                "trigger": "no_operational_trigger",
                                "entry_score": 0.2,
                            },
                        },
                    }
                ],
                "stored_matches": 1,
                "similarity_threshold": 0.45,
            }

    result = PatternEntryScanner(
        settings=scanner(provider, entry_gate_enabled=True).settings,
        matcher=NoTriggerMatcher(),
    ).scan(db, module="laboratory", symbols=[provider.symbol], store_signals=True)

    assert result["rejected_by_entry_gate"] == 1
    assert result["signals_created"] == 0
    assert db.query(Signal).count() == 0


def test_laboratory_scanner_rejects_low_quality_match() -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    class LowQualityMatcher:
        def match_current(self, *args, **kwargs):
            return {
                "patterns_checked": 1,
                "symbols_checked": 1,
                "matches": [
                    {
                        "module": "laboratory",
                        "pattern_id": 1,
                        "pattern_name": "low_quality_pattern",
                        "pattern_key": "low_quality_key",
                        "pattern_status": "lab_candidate",
                        "pattern_promotion_status": "lab_candidate",
                        "symbol": provider.symbol,
                        "timeframe": "1d",
                        "side": "long",
                        "similarity": 0.1,
                        "score": 0.1,
                        "entry_score": 0.1,
                        "entry_gate_passed": True,
                        "entry_trigger": "momentum_close",
                        "entry_price": 10.0,
                        "stop_price": 9.0,
                        "target_price": 14.0,
                        "reward_risk": 4.0,
                        "metrics": {
                            "pattern_score": 0.1,
                            "pattern_expectancy_r": 0.0,
                            "pattern_profit_factor": 0.0,
                            "pattern_stability_score": 0.1,
                            "features": {"avg_dollar_volume": 10_000_000, "atr_pct": 0.04},
                            "entry_gate": {
                                "passed": True,
                                "trigger": "momentum_close",
                                "entry_score": 0.1,
                                "volume_ratio": 1.5,
                                "extension_atr": 0.5,
                                "regime_ok": True,
                            },
                        },
                    }
                ],
                "stored_matches": 1,
                "similarity_threshold": 0.45,
            }

    cfg = scanner(provider, entry_min_quality_score=0.8).settings
    result = PatternEntryScanner(settings=cfg, matcher=LowQualityMatcher()).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
    )

    assert result["rejected_by_entry_quality"] == 1
    assert result["signals_created"] == 0
    assert db.query(Signal).count() == 0


def test_laboratory_scanner_processes_best_ranked_opportunity_first() -> None:
    db = session_factory()
    provider = FixtureProvider()

    class RankingMatcher:
        def match_current(self, *args, **kwargs):
            def match(name: str, score: float, entry_score: float, expectancy: float):
                return {
                    "module": "laboratory",
                    "pattern_id": 1 if name == "weak_pattern" else 2,
                    "pattern_name": name,
                    "pattern_key": f"{name}_key",
                    "pattern_status": "lab_candidate",
                    "pattern_promotion_status": "lab_candidate",
                    "symbol": provider.symbol,
                    "timeframe": "1d",
                    "side": "long",
                    "similarity": score,
                    "score": score,
                    "entry_score": entry_score,
                    "entry_gate_passed": True,
                    "entry_trigger": "breakout",
                    "entry_price": 10.0,
                    "stop_price": 9.0,
                    "target_price": 14.0,
                    "reward_risk": 4.0,
                    "metrics": {
                        "pattern_score": score,
                        "pattern_expectancy_r": expectancy,
                        "pattern_profit_factor": 2.0,
                        "pattern_stability_score": score,
                        "features": {"avg_dollar_volume": 10_000_000, "atr_pct": 0.04},
                        "entry_gate": {
                            "passed": True,
                            "trigger": "breakout",
                            "entry_score": entry_score,
                            "volume_ratio": 2.0,
                            "extension_atr": 0.5,
                            "regime_ok": True,
                        },
                    },
                }

            return {
                "patterns_checked": 2,
                "symbols_checked": 1,
                "matches": [
                    match("weak_pattern", 0.2, 0.2, 0.0),
                    match("strong_pattern", 0.9, 0.9, 0.5),
                ],
                "stored_matches": 2,
                "similarity_threshold": 0.45,
            }

    result = PatternEntryScanner(
        settings=scanner(provider, entry_min_quality_score=0.0).settings,
        matcher=RankingMatcher(),
    ).scan(db, module="laboratory", symbols=[provider.symbol], store_signals=True)

    assert result["signals_created"] == 2
    first_signal = db.get(Signal, result["signal_ids"][0])
    second_signal = db.get(Signal, result["signal_ids"][1])
    assert first_signal.pattern == "strong_pattern"
    assert first_signal.metadata_json["opportunity_rank"] == 1
    assert second_signal.metadata_json["opportunity_rank"] == 2


def test_laboratory_scanner_respects_symbol_pattern_cooldown() -> None:
    db = session_factory()
    provider = FixtureProvider()
    pattern = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    db.add(
        Signal(
            symbol=provider.symbol,
            pattern=pattern.name,
            side="long",
            entry=10.0,
            stop=9.0,
            target=14.0,
            reward_risk=4.0,
            confidence=0.7,
            composite_score=0.7,
            risk_usd=10.0,
            suggested_qty=1,
            strategy_version=f"laboratory_pattern_{pattern.id}",
            status=SignalStatus.EXPIRED,
            metadata_json={"entry_module": "laboratory", "pattern_id": pattern.id},
        )
    )
    db.commit()

    result = scanner(provider, entry_cooldown_minutes=60).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
    )

    assert result["skipped_cooldown"] == 1
    assert result["signals_created"] == 0


def test_laboratory_scanner_skips_signal_creation_when_market_closed(monkeypatch) -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    monkeypatch.setattr(
        "tradeo.services.pattern_entry_scanner.market_session_status",
        lambda: {
            "market": "us_equities",
            "timezone": "America/New_York",
            "regular_session_open": False,
            "state": "market_closed",
            "checked_at": "2026-06-09T01:30:00-04:00",
            "regular_hours": "09:30-16:00",
        },
    )

    result = scanner(provider, laboratory_market_hours_only=True).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )

    assert result["skipped_reason"] == "market_closed"
    assert result["symbols_checked"] == 0
    assert result["signals_created"] == 0
    assert db.query(Signal).count() == 0


def test_fox_hunter_ignores_lab_patterns_and_uses_production_only() -> None:
    db = session_factory()
    provider = FixtureProvider("FOXX")
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    add_pattern(db, provider, status=DiscoveredPatternStatus.DIRECTOR_REVIEW)
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


def test_laboratory_matcher_reuses_symbol_data_across_patterns() -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_WATCHLIST)

    result = scanner(provider).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=False,
        execute_orders=False,
    )

    assert result["patterns_checked"] == 2
    assert result["matches_found"] == 2
    assert provider.fetch_calls.count(("SPY", "3mo", "1d")) == 1
    assert provider.fetch_calls.count(("QQQ", "3mo", "1d")) == 1
    assert provider.fetch_calls.count((provider.symbol, "3mo", "1d")) == 1
    assert len(provider.fetch_calls) == 3
