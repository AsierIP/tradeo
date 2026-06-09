from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import (
    DiscoveredPattern,
    DiscoveredPatternMatch,
    DiscoveredPatternStatus,
    Signal,
    SignalStatus,
    Trade,
    TradeStatus,
)
from tradeo.db.session import Base
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.pattern_embedding_engine import PatternEmbeddingEngine
from tradeo.services.lab_paper_observations import LAB_SHADOW_EXECUTION_MODE, LabPaperObservationService
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


class StaticProvider:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

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


def match_payload(**overrides):
    payload = {
        "module": "laboratory",
        "pattern_id": 1,
        "pattern_name": "dedupe_pattern",
        "pattern_key": "dedupe_key",
        "pattern_status": "lab_candidate",
        "pattern_promotion_status": "lab_candidate",
        "symbol": "LABX",
        "timeframe": "1d",
        "side": "long",
        "similarity": 0.7,
        "score": 0.7,
        "entry_score": 0.7,
        "entry_gate_passed": True,
        "entry_trigger": "breakout",
        "entry_variant_id": "next_bar_limit_retest",
        "entry_variant": {"id": "next_bar_limit_retest"},
        "entry_price": 10.0,
        "stop_price": 9.0,
        "target_price": 14.0,
        "reward_risk": 4.0,
        "window_end": "2026-06-09T00:00:00+00:00",
        "status": "lab_entry_candidate",
        "notes": "test",
        "chart": {},
        "metrics": {
            "entry_variant_id": "next_bar_limit_retest",
            "entry_gate": {"passed": True, "reason": "entry gate passed"},
        },
    }
    payload.update(overrides)
    return payload


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
    assert result["entry_variants_considered"] >= 1
    assert result["signals_created"] == 1
    assert result["paper_observations_opened"] == 1
    assert result["paper_observation_trade_ids"]
    signal_id = result["signal_ids"][0]
    signal = db.get(Signal, signal_id)
    assert signal.status == SignalStatus.PAPER_APPROVED
    assert signal.human_approved is False
    assert signal.metadata_json["entry_module"] == "laboratory"
    assert signal.metadata_json["entry_variant_id"]
    assert signal.metadata_json["entry_audit"]["available_data_cutoff_ts"]
    assert signal.metadata_json["entry_audit"]["entry_eligible_ts"]
    assert signal.metadata_json["entry_audit"]["source_bar_hash"]
    assert signal.metadata_json["regime"]["regime_key"]
    assert signal.metadata_json["entry_quality_score"] > 0
    assert signal.metadata_json["entry_quality"]["label"] in {"blocked", "weak", "watch", "actionable", "high"}
    assert isinstance(signal.metadata_json["entry_quality"]["flags"], list)
    assert signal.metadata_json["opportunity_rank"] == 1
    assert signal.metadata_json["opportunity_rank_score"] > 0
    assert signal.metadata_json["signal_snapshot"]["symbol"] == provider.symbol
    assert signal.metadata_json["signal_snapshot"]["entry_variant_id"] == signal.metadata_json["entry_variant_id"]
    assert signal.metadata_json["signal_snapshot"]["entry_audit"]["source_bar_hash"]
    assert signal.metadata_json["signal_snapshot"]["risk"]["approved"] is True
    stored_match = (
        db.query(DiscoveredPatternMatch)
        .filter(
            DiscoveredPatternMatch.metrics_json["entry_variant_id"].as_string()
            == signal.metadata_json["entry_variant_id"]
        )
        .one()
    )
    assert stored_match.metrics_json["entry_variant_id"] == signal.metadata_json["entry_variant_id"]
    assert stored_match.metrics_json["entry_variant"]["id"] == signal.metadata_json["entry_variant_id"]
    observation = db.get(Trade, result["paper_observation_trade_ids"][0])
    assert observation.status == TradeStatus.OPEN
    assert observation.signal_id == signal.id
    assert observation.metadata_json["execution_mode"] == LAB_SHADOW_EXECUTION_MODE
    assert observation.metadata_json["no_ibkr_order"] is True


def test_current_match_storage_upserts_equivalent_entry_variant() -> None:
    db = session_factory()
    NovelPatternMatcher._store_matches(db, [match_payload(score=0.51, similarity=0.61)])
    NovelPatternMatcher._store_matches(
        db,
        [
            match_payload(
                score=0.88,
                similarity=0.91,
                metrics={
                    "entry_variant_id": "next_bar_limit_retest",
                    "entry_gate": {
                        "passed": False,
                        "reason": "insufficient_volume",
                        "rejection_reasons": ["insufficient_volume"],
                    },
                },
            )
        ],
    )

    rows = db.query(DiscoveredPatternMatch).all()

    assert len(rows) == 1
    assert rows[0].score == 0.88
    assert rows[0].similarity == 0.91
    assert rows[0].metrics_json["seen_count"] == 2
    assert rows[0].metrics_json["entry_gate"]["reason"] == "insufficient_volume"


def test_current_match_storage_keeps_distinct_entry_variants() -> None:
    db = session_factory()
    NovelPatternMatcher._store_matches(db, [match_payload(entry_variant_id="variant_a", metrics={"entry_variant_id": "variant_a"})])
    NovelPatternMatcher._store_matches(db, [match_payload(entry_variant_id="variant_b", metrics={"entry_variant_id": "variant_b"})])

    assert db.query(DiscoveredPatternMatch).count() == 2


def test_lab_shadow_observation_closes_on_target_without_ibkr_order() -> None:
    db = session_factory()
    opened_at = datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc)
    signal = Signal(
        symbol="LABX",
        pattern="shadow_pattern",
        side="long",
        entry=10.0,
        stop=9.0,
        target=12.0,
        reward_risk=2.0,
        confidence=0.7,
        composite_score=0.7,
        risk_usd=10.0,
        suggested_qty=3,
        strategy_version="laboratory_pattern_1",
        status=SignalStatus.PAPER_APPROVED,
        metadata_json={"entry_module": "laboratory", "pattern_id": 1},
    )
    db.add(signal)
    db.flush()
    trade = Trade(
        signal_id=signal.id,
        symbol="LABX",
        pattern="shadow_pattern",
        side="long",
        qty=3,
        entry=10.0,
        stop=9.0,
        target=12.0,
        status=TradeStatus.OPEN,
        opened_at=opened_at,
        metadata_json={
            "execution_mode": LAB_SHADOW_EXECUTION_MODE,
            "observation_only": True,
            "no_ibkr_order": True,
        },
    )
    db.add(trade)
    db.commit()
    df = pd.DataFrame(
        {
            "open": [10.1, 10.3],
            "high": [11.0, 12.4],
            "low": [9.8, 10.2],
            "close": [10.5, 12.1],
            "volume": [1000.0, 1100.0],
        },
        index=pd.to_datetime(["2026-01-03T00:00:00Z", "2026-01-04T00:00:00Z"]),
    )

    result = LabPaperObservationService(settings=Settings(), provider=StaticProvider(df)).close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 1
    assert trade.status == TradeStatus.CLOSED
    assert trade.exit_price == 12.0
    assert trade.r_multiple == 2.0
    assert trade.pnl_usd == 6.0
    assert trade.metadata_json["exit_reason"] == "target_hit"
    assert trade.metadata_json["no_ibkr_order"] is True


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


def test_laboratory_scanner_prefers_entry_variant_with_paper_history() -> None:
    db = session_factory()
    provider = FixtureProvider()
    historical_signal = Signal(
        symbol=provider.symbol,
        pattern="adaptive_pattern",
        side="long",
        entry=10.0,
        stop=9.0,
        target=14.0,
        reward_risk=4.0,
        confidence=0.7,
        composite_score=0.7,
        risk_usd=10.0,
        suggested_qty=1,
        strategy_version="laboratory_pattern_1",
        status=SignalStatus.EXECUTED,
        metadata_json={
            "entry_module": "laboratory",
            "entry_variant_id": "next_bar_limit_retest",
            "regime": {"regime_key": "market_up|uptrend|normal_vol|liquid|rs_leader"},
        },
    )
    db.add(historical_signal)
    db.flush()
    for _ in range(10):
        db.add(
            Trade(
                signal_id=historical_signal.id,
                symbol=provider.symbol,
                pattern="adaptive_pattern",
                side="long",
                qty=1,
                entry=10.0,
                stop=9.0,
                target=14.0,
                status=TradeStatus.CLOSED,
                pnl_usd=20.0,
                r_multiple=2.0,
            )
        )
    db.commit()

    class VariantMatcher:
        def match_current(self, *args, **kwargs):
            def match(variant: str):
                return {
                    "module": "laboratory",
                    "pattern_id": 1,
                    "pattern_name": "adaptive_pattern",
                    "pattern_key": "adaptive_key",
                    "pattern_status": "lab_candidate",
                    "pattern_promotion_status": "lab_candidate",
                    "symbol": provider.symbol,
                    "timeframe": "1d",
                    "side": "long",
                    "similarity": 0.8,
                    "score": 0.8,
                    "entry_score": 0.8,
                    "entry_gate_passed": True,
                    "entry_trigger": variant,
                    "entry_variant_id": variant,
                    "entry_variant": {"id": variant, "order_style": "next_bar_limit"},
                    "entry_audit": {"source_bar_hash": "abc", "entry_eligible_ts": "2026-06-10T00:00:00+00:00"},
                    "regime": {"regime_key": "market_up|uptrend|normal_vol|liquid|rs_leader"},
                    "regime_fit": {"score": 0.8},
                    "entry_price": 10.0,
                    "stop_price": 9.0,
                    "target_price": 14.0,
                    "reward_risk": 4.0,
                    "metrics": {
                        "pattern_score": 0.8,
                        "pattern_expectancy_r": 0.2,
                        "pattern_profit_factor": 2.0,
                        "pattern_stability_score": 0.8,
                        "features": {"avg_dollar_volume": 10_000_000, "atr_pct": 0.04},
                        "entry_gate": {
                            "passed": True,
                            "trigger": variant,
                            "entry_score": 0.8,
                            "volume_ratio": 2.0,
                            "extension_atr": 0.5,
                            "regime_ok": True,
                        },
                    },
                }

            return {
                "patterns_checked": 1,
                "symbols_checked": 1,
                "matches": [match("momentum_close_next_bar_limit"), match("next_bar_limit_retest")],
                "stored_matches": 2,
                "similarity_threshold": 0.45,
            }

    result = PatternEntryScanner(
        settings=scanner(provider, entry_min_quality_score=0.0).settings,
        matcher=VariantMatcher(),
    ).scan(db, module="laboratory", symbols=[provider.symbol], store_signals=True)

    assert result["entry_variants_considered"] == 2
    signal = db.get(Signal, result["signal_ids"][0])
    assert signal.metadata_json["entry_variant_id"] == "next_bar_limit_retest"
    assert signal.metadata_json["opportunity_rank_components"]["history_count"] >= 1
    assert signal.metadata_json["opportunity_rank_components"]["history_profit_factor"] > 0
    assert signal.metadata_json["opportunity_rank_components"]["history_decay"] >= 0
    assert signal.metadata_json["opportunity_rank_reason"] == "paper_history_weighted"


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


def near_miss_match(provider: FixtureProvider, **overrides):
    payload = {
        "module": "laboratory",
        "pattern_id": 42,
        "pattern_name": "near_miss_pattern",
        "pattern_key": "near_miss_key",
        "pattern_status": "lab_candidate",
        "pattern_promotion_status": "lab_candidate",
        "symbol": provider.symbol,
        "timeframe": "1d",
        "side": "long",
        "similarity": 0.7,
        "score": 0.72,
        "entry_score": 0.56,
        "entry_gate_passed": False,
        "entry_trigger": "next_bar_stop_confirmation",
        "entry_variant_id": "next_bar_stop_confirmation",
        "entry_variant": {"id": "next_bar_stop_confirmation", "order_style": "next_bar_stop"},
        "entry_audit": {
            "source_bar_hash": "near-miss-hash",
            "entry_eligible_ts": "2026-06-10T00:00:00+00:00",
        },
        "regime": {"regime_key": "market_mixed|uptrend|normal_vol|liquid|rs_leader"},
        "regime_fit": {"score": 0.7},
        "entry_price": 10.0,
        "stop_price": 9.0,
        "target_price": 14.0,
        "reward_risk": 4.0,
        "metrics": {
            "pattern_score": 0.8,
            "pattern_expectancy_r": 0.3,
            "pattern_profit_factor": 2.0,
            "pattern_stability_score": 0.8,
            "features": {"avg_dollar_volume": 10_000_000, "atr_pct": 0.04},
            "entry_gate": {
                "passed": False,
                "reason": "insufficient_volume",
                "rejection_reasons": ["insufficient_volume"],
                "trigger": "next_bar_stop_confirmation",
                "entry_score": 0.56,
                "volume_ratio": 0.45,
                "extension_atr": 0.4,
                "regime_ok": True,
            },
        },
    }
    payload.update(overrides)
    return payload


def test_laboratory_opens_near_miss_shadow_observation_for_soft_volume_failure() -> None:
    db = session_factory()
    provider = FixtureProvider("MISS")

    class NearMissMatcher:
        def match_current(self, *args, **kwargs):
            return {
                "patterns_checked": 1,
                "symbols_checked": 1,
                "matches": [near_miss_match(provider)],
                "stored_matches": 1,
                "similarity_threshold": 0.45,
            }

    result = PatternEntryScanner(
        settings=scanner(provider, entry_gate_enabled=True).settings,
        matcher=NearMissMatcher(),
    ).scan(db, module="laboratory", symbols=[provider.symbol], store_signals=True, execute_orders=False)

    assert result["signals_created"] == 1
    assert result["near_miss_shadow_observations_opened"] == 1
    assert result["orders_submitted"] == 0
    assert result["rejected_by_entry_gate"] == 0
    signal = db.get(Signal, result["signal_ids"][0])
    assert signal.metadata_json["near_miss"] is True
    assert signal.metadata_json["near_miss_shadow"] is True
    assert signal.metadata_json["would_have_failed_entry_gate"] is True
    assert signal.metadata_json["paper_only"] is True
    assert signal.metadata_json["no_ibkr_order"] is True
    assert signal.metadata_json["entry_variant_id"] == "next_bar_stop_confirmation"
    assert signal.metadata_json["regime"]["regime_key"]
    assert signal.metadata_json["entry_gate"]["near_miss_shadow"] is True
    assert signal.metadata_json["entry_quality"]["near_miss_shadow"] is True
    observation = db.get(Trade, result["paper_observation_trade_ids"][0])
    assert observation.metadata_json["execution_mode"] == LAB_SHADOW_EXECUTION_MODE
    assert observation.metadata_json["near_miss_shadow"] is True
    assert observation.metadata_json["no_ibkr_order"] is True


def test_laboratory_does_not_open_near_miss_shadow_for_hard_entry_blocker() -> None:
    db = session_factory()
    provider = FixtureProvider("HARD")
    hard_match = near_miss_match(
        provider,
        entry_score=0.2,
        metrics={
            **near_miss_match(provider)["metrics"],
            "entry_gate": {
                **near_miss_match(provider)["metrics"]["entry_gate"],
                "reason": "weak_entry_score;insufficient_volume",
                "rejection_reasons": ["weak_entry_score", "insufficient_volume"],
                "entry_score": 0.2,
            },
        },
    )

    class HardBlockerMatcher:
        def match_current(self, *args, **kwargs):
            return {
                "patterns_checked": 1,
                "symbols_checked": 1,
                "matches": [hard_match],
                "stored_matches": 1,
                "similarity_threshold": 0.45,
            }

    result = PatternEntryScanner(
        settings=scanner(provider, entry_gate_enabled=True).settings,
        matcher=HardBlockerMatcher(),
    ).scan(db, module="laboratory", symbols=[provider.symbol], store_signals=True, execute_orders=False)

    assert result["signals_created"] == 0
    assert result["near_miss_shadow_observations_opened"] == 0
    assert result["rejected_by_entry_gate"] == 1
    assert db.query(Trade).count() == 0
