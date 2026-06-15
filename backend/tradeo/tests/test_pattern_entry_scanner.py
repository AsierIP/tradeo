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
from tradeo.services.evidence import EvidenceQuality, EvidenceType, FillProvenance
from tradeo.services.system_controls import activate_runtime_kill_switch
from tradeo.modules.fox_hunter.production_manifest import build_production_manifest
from tradeo.modules.laboratory.paper_observations import LAB_SHADOW_EXECUTION_MODE, LabPaperObservationService
from tradeo.modules.shared.entry_scanner import (
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


class NoBarsProvider:
    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d"):
        raise ValueError(f"IBKR returned no bars for {symbol}")


class StaticMatcher:
    def __init__(self, provider: FixtureProvider, matches: list[dict]) -> None:
        self.provider = provider
        self.matches = matches

    def match_current(self, *args, **kwargs):
        return {
            "patterns_checked": len({match.get("pattern_id") for match in self.matches}),
            "symbols_checked": len({match.get("symbol") for match in self.matches}),
            "matches": self.matches,
            "stored_matches": len(self.matches),
            "similarity_threshold": 0.45,
        }


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


def add_shadow_observation(
    db,
    *,
    opened_at: datetime,
    signal_metadata: dict | None = None,
    trade_metadata: dict | None = None,
) -> tuple[Signal, Trade]:
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
        metadata_json=signal_metadata or {"entry_module": "laboratory", "pattern_id": 1},
    )
    db.add(signal)
    db.flush()
    metadata = {
        "execution_mode": LAB_SHADOW_EXECUTION_MODE,
        "observation_only": True,
        "no_ibkr_order": True,
    }
    metadata.update(trade_metadata or {})
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
        metadata_json=metadata,
    )
    db.add(trade)
    db.commit()
    return signal, trade


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


def near_miss_volume_payload(**overrides):
    payload = match_payload(
        pattern_name="near_miss_volume_pattern",
        pattern_key="near_miss_volume_key",
        similarity=0.86,
        score=0.86,
        entry_score=0.68,
        entry_gate_passed=False,
        entry_trigger="breakout",
        entry_variant_id="volume_confirmed_close",
        entry_variant={"id": "volume_confirmed_close", "order_style": "shadow_observation"},
        entry_audit={
            "available_data_cutoff_ts": "2026-06-09T00:00:00+00:00",
            "entry_eligible_ts": "2026-06-10T00:00:00+00:00",
            "source_bar_hash": "near-miss-hash",
        },
        regime={"regime_key": "market_up|uptrend|normal_vol|liquid|rs_leader"},
        regime_fit={"score": 0.74},
        metrics={
            "pattern_score": 0.86,
            "pattern_expectancy_r": 0.4,
            "pattern_profit_factor": 2.2,
            "pattern_stability_score": 0.85,
            "features": {"avg_dollar_volume": 10_000_000, "atr_pct": 0.04},
            "entry_gate": {
                "passed": False,
                "trigger": "breakout",
                "trigger_score": 1.0,
                "entry_score": 0.68,
                "volume_ratio": 0.92,
                "volume_confirmed": False,
                "atr_pct": 0.04,
                "volatility_ok": True,
                "extension_atr": 0.6,
                "not_extended": True,
                "regime_ok": True,
                "reason": "insufficient_volume",
                "rejection_reasons": ["insufficient_volume"],
            },
        },
    )
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
        # Fixtures terminan en la barra de "hoy": sin esto el resultado del
        # matcher dependeria de si el test corre antes o despues del cierre NY.
        "discovery_match_complete_bars_only": False,
        "artifacts_dir": "/tmp/tradeo-test-artifacts",
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
    assert signal.metadata_json["evidence_type"] == EvidenceType.SHADOW_NO_ORDER.value
    assert signal.metadata_json["evidence_quality"] == EvidenceQuality.NORMAL.value
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
    assert observation.metadata_json["evidence_type"] == EvidenceType.SHADOW_NO_ORDER.value
    assert observation.metadata_json["evidence_quality"] == EvidenceQuality.NORMAL.value
    assert observation.metadata_json["no_ibkr_order"] is True


def test_laboratory_status_allows_paper_when_auto_submit_is_disabled() -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    status = scanner(provider, laboratory_auto_submit_paper_orders=False).status(db)
    lab = status["laboratory"]

    assert lab["auto_submit_paper_orders"] is False
    assert lab["paper_order_safety_ok"] is True
    assert lab["paper_orders_allowed"] is True
    assert lab["execution_block_reason"] is None


def test_laboratory_status_blocks_paper_on_grave_safety_gate() -> None:
    db = session_factory()
    provider = FixtureProvider()

    status = scanner(provider, kill_switch_enabled=True).status(db)
    lab = status["laboratory"]

    assert lab["paper_order_safety_ok"] is False
    assert lab["paper_orders_allowed"] is False
    assert lab["execution_block_reason"] == "kill_switch_enabled"


def test_laboratory_status_blocks_paper_on_runtime_kill_switch() -> None:
    db = session_factory()
    provider = FixtureProvider()
    activate_runtime_kill_switch(
        db,
        reason="reconciliation divergence",
        actor="test",
        details={"symbol": "AAPL"},
    )

    status = scanner(provider).status(db)
    lab = status["laboratory"]

    assert lab["paper_order_safety_ok"] is False
    assert lab["paper_orders_allowed"] is False
    assert lab["runtime_kill_switch_enabled"] is True
    assert lab["runtime_kill_switch_reason"] == "reconciliation divergence"
    assert lab["execution_block_reason"] == "runtime_kill_switch_enabled"


def test_fox_status_blocks_live_on_runtime_kill_switch() -> None:
    db = session_factory()
    provider = FixtureProvider()
    activate_runtime_kill_switch(
        db,
        reason="reconciliation divergence",
        actor="test",
        details={"symbol": "AAPL"},
    )

    status = scanner(
        provider,
        fox_hunter_auto_submit_live_orders=True,
        trading_mode="live",
        live_trading_enabled=True,
        live_trading_confirmation_value="I_ACCEPT_LIVE_MARKET_RISK",
    ).status(db)
    fox = status["fox_hunter"]

    assert fox["live_orders_allowed"] is False
    assert fox["runtime_kill_switch_enabled"] is True
    assert fox["runtime_kill_switch_reason"] == "reconciliation divergence"
    assert fox["execution_block_reason"] == "runtime_kill_switch_enabled"


def test_laboratory_scanner_keeps_paper_observation_when_collection_filters_fail() -> None:
    db = session_factory()
    provider = FixtureProvider()
    match = match_payload(
        reward_risk=1.0,
        target_price=11.0,
        metrics={
            "pattern_score": 0.95,
            "pattern_expectancy_r": 0.8,
            "pattern_profit_factor": 4.0,
            "pattern_stability_score": 0.95,
            "features": {"avg_dollar_volume": 0, "atr_pct": 9.0},
            "entry_gate": {
                "passed": True,
                "trigger": "breakout",
                "entry_score": 1.0,
                "volume_ratio": 5.0,
                "extension_atr": 0.1,
                "regime_ok": True,
            },
        },
    )
    settings = scanner(
        provider,
        min_reward_risk=2.5,
        min_avg_dollar_volume=1_000_000,
        max_atr_pct=1.0,
        entry_min_quality_score=0.99,
    ).settings

    result = PatternEntryScanner(
        settings=settings,
        matcher=StaticMatcher(provider, [match]),
    ).scan(db, module="laboratory", symbols=[provider.symbol], store_signals=True)

    assert result["rejected_by_risk"] == 0
    assert result["rejected_by_entry_quality"] == 0
    assert result["signals_created"] == 1
    assert result["paper_observations_opened"] == 1
    signal = db.get(Signal, result["signal_ids"][0])
    assert signal.metadata_json["entry_quality"]["score"] < 0.99
    warnings = signal.metadata_json["signal_snapshot"]["risk"]["warnings"]
    assert "reward_risk_below_2.5" in warnings
    assert "liquidity_filter_failed" in warnings
    assert "atr_filter_failed" in warnings
    assert "thin_liquidity" not in signal.metadata_json["entry_quality"]["flags"]


def test_laboratory_matcher_records_feature_parity_and_ambiguity_ratio() -> None:
    db = session_factory()
    provider = FixtureProvider()
    first = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    vector, _, _ = PatternEmbeddingEngine().embed(provider.df.iloc[-20:])
    second = DiscoveredPattern(
        pattern_key="lab_candidate_key_second",
        name="lab_candidate_pattern_second",
        status=DiscoveredPatternStatus.LAB_CANDIDATE,
        side="long",
        timeframe="1d",
        window_size=20,
        sample_count=120,
        symbol_count=12,
        year_count=3,
        score=0.88,
        reward_risk_estimate=4.0,
        expectancy_r=0.35,
        profit_factor=2.0,
        win_rate=0.54,
        stability_score=0.78,
        out_of_sample_expectancy_r=0.25,
        out_of_sample_profit_factor=1.8,
        best_rr=4.0,
        validation_passed=True,
        promotion_status=DiscoveredPatternStatus.LAB_CANDIDATE.value,
        centroid_json=[float(value) + 0.005 for value in vector.tolist()],
        metrics_json={"scaler_mean": [0.0] * len(vector), "scaler_scale": [1.0] * len(vector)},
    )
    db.add(second)
    db.commit()
    db.refresh(second)

    settings = Settings(
        discovery_match_complete_bars_only=False,
        discovery_match_max_patterns=10,
        discovery_match_max_results=10,
        discovery_match_ambiguity_hard_gate_enabled=False,
        entry_gate_enabled=False,
    )
    result = NovelPatternMatcher(provider=provider, settings=settings).match_current(
        db,
        symbols=[provider.symbol],
        store=False,
    )

    assert result["feature_parity_contract"]["contract_id"] == PatternEmbeddingEngine.CONTRACT_ID
    matches = {int(match["pattern_id"]): match for match in result["matches"]}
    assert first.id in matches
    ambiguity = matches[first.id]["match_ambiguity"]
    assert ambiguity["second_best_pattern_id"] == second.id
    assert ambiguity["ambiguity_ratio"] > 0.95
    assert matches[first.id]["metrics"]["match_ambiguity"] == ambiguity
    contract = matches[first.id]["metrics"]["feature_parity_contract"]
    assert contract["research_lab_shared_path"] is True
    assert contract["contract_id"] == PatternEmbeddingEngine.CONTRACT_ID


def test_laboratory_matcher_can_disable_research_result_cap() -> None:
    db = session_factory()
    provider = FixtureProvider()
    first = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    vector, _, _ = PatternEmbeddingEngine().embed(provider.df.iloc[-20:])
    second = DiscoveredPattern(
        pattern_key="lab_candidate_key_uncapped",
        name="lab_candidate_pattern_uncapped",
        status=DiscoveredPatternStatus.LAB_CANDIDATE,
        side="long",
        timeframe="1d",
        window_size=20,
        sample_count=120,
        symbol_count=12,
        year_count=3,
        score=0.88,
        reward_risk_estimate=4.0,
        expectancy_r=0.35,
        profit_factor=2.0,
        win_rate=0.54,
        stability_score=0.78,
        out_of_sample_expectancy_r=0.25,
        out_of_sample_profit_factor=1.8,
        best_rr=4.0,
        validation_passed=True,
        promotion_status=DiscoveredPatternStatus.LAB_CANDIDATE.value,
        centroid_json=[float(value) + 0.005 for value in vector.tolist()],
        metrics_json={"scaler_mean": [0.0] * len(vector), "scaler_scale": [1.0] * len(vector)},
    )
    db.add(second)
    db.commit()

    matcher = NovelPatternMatcher(
        provider=provider,
        settings=Settings(
            discovery_match_complete_bars_only=False,
            discovery_match_max_patterns=10,
            discovery_match_max_results=1,
            laboratory_match_max_results=0,
            discovery_match_ambiguity_hard_gate_enabled=False,
            entry_gate_enabled=False,
        ),
    )

    result = matcher.match_current(db, symbols=[provider.symbol], module="laboratory", store=False)

    assert result["max_results"] is None
    assert {int(match["pattern_id"]) for match in result["matches"]} >= {first.id, second.id}


def test_laboratory_matcher_hard_blocks_ambiguous_weak_entry() -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    vector, _, _ = PatternEmbeddingEngine().embed(provider.df.iloc[-20:])
    db.add(
        DiscoveredPattern(
            pattern_key="lab_candidate_key_ambiguous",
            name="lab_candidate_pattern_ambiguous",
            status=DiscoveredPatternStatus.LAB_CANDIDATE,
            side="long",
            timeframe="1d",
            window_size=20,
            sample_count=120,
            symbol_count=12,
            year_count=3,
            score=0.88,
            reward_risk_estimate=4.0,
            expectancy_r=0.35,
            profit_factor=2.0,
            win_rate=0.54,
            stability_score=0.78,
            out_of_sample_expectancy_r=0.25,
            out_of_sample_profit_factor=1.8,
            best_rr=4.0,
            validation_passed=True,
            promotion_status=DiscoveredPatternStatus.LAB_CANDIDATE.value,
            centroid_json=[float(value) + 0.005 for value in vector.tolist()],
            metrics_json={"scaler_mean": [0.0] * len(vector), "scaler_scale": [1.0] * len(vector)},
        )
    )
    db.commit()

    settings = Settings(
        discovery_match_complete_bars_only=False,
        discovery_match_max_patterns=10,
        discovery_match_max_results=10,
        discovery_match_ambiguity_hard_gate_enabled=True,
        discovery_match_ambiguity_entry_score_margin=0.10,
        entry_min_score=0.99,
    )
    result = NovelPatternMatcher(provider=provider, settings=settings).match_current(
        db,
        symbols=[provider.symbol],
        store=False,
    )

    assert result["ambiguity_hard_gate_enabled"] is True
    assert result["ambiguity_gate_blocked"] >= 1
    assert result["matches"] == []


def test_matcher_effective_threshold_prefers_conformal_tau() -> None:
    db = session_factory()
    provider = FixtureProvider()
    pattern = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    pattern.metrics_json = {
        **pattern.metrics_json,
        "match_tau_similarity": 0.60,
        "match_conformal_similarity_threshold": 0.72,
    }

    matcher = NovelPatternMatcher(
        provider=provider,
        settings=Settings(discovery_match_per_pattern_threshold=True),
    )

    assert matcher._effective_threshold(pattern, 0.45) == 0.72


def test_matcher_optional_knn_medoids_gate_passes_and_blocks() -> None:
    db = session_factory()
    provider = FixtureProvider()
    pattern = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    vector, features, chart = PatternEmbeddingEngine().embed(provider.df.iloc[-20:])
    cached = (provider.df, vector, features, chart)
    base_metrics = {
        **pattern.metrics_json,
        "matcher_medoids_scaled": [
            vector.tolist(),
            (vector + 0.01).tolist(),
            (vector - 0.01).tolist(),
        ],
        "matcher_diag_variance_scaled": [1.0] * len(vector),
        "match_knn_similarity_threshold": 0.70,
        "match_mahalanobis_max_distance": 1.0,
    }
    pattern.metrics_json = base_metrics

    matcher = NovelPatternMatcher(
        provider=provider,
        settings=Settings(
            discovery_match_complete_bars_only=False,
            discovery_match_knn_enabled=True,
            discovery_match_knn_k=3,
        ),
    )
    passed = matcher._similarity_diagnostic(pattern, cached, 0.45)
    assert passed is not None
    assert passed["passed_threshold"] is True
    assert passed["prototype_match"]["passed"] is True
    assert passed["prototype_match"]["knn_similarity"] >= 0.70

    pattern.metrics_json = {
        **base_metrics,
        "matcher_medoids_scaled": [(vector + 100.0).tolist()],
        "match_knn_similarity_threshold": 0.90,
    }
    blocked = matcher._similarity_diagnostic(pattern, cached, 0.45)
    assert blocked is not None
    assert blocked["passed_threshold"] is False
    assert blocked["prototype_match"]["knn_passed"] is False


def test_laboratory_volume_near_miss_opens_shadow_observation_without_ibkr(monkeypatch) -> None:
    db = session_factory()
    provider = FixtureProvider()
    pattern = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    class FailBroker:
        def __init__(self, settings) -> None:
            self.settings = settings

        def submit_signal_bracket(self, db, signal, *, reason: str = "manual"):
            raise AssertionError("near-miss shadow observations must not call IBKR")

    monkeypatch.setattr("tradeo.modules.shared.entry_scanner.IBKRBroker", FailBroker)
    match = near_miss_volume_payload(
        pattern_id=pattern.id,
        pattern_name=pattern.name,
        pattern_key=pattern.pattern_key,
    )
    cfg = scanner(provider, entry_gate_enabled=True).settings

    result = PatternEntryScanner(settings=cfg, matcher=StaticMatcher(provider, [match])).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )

    assert cfg.laboratory_auto_submit_paper_orders is False
    assert result["rejected_by_entry_gate"] == 1
    assert result["signals_created"] == 1
    assert result["orders_submitted"] == 0
    assert result["paper_observations_opened"] == 1
    assert result["near_miss_shadow_observations_opened"] == 1
    assert result["near_miss_signal_ids"] == result["signal_ids"]
    assert result["near_miss_trade_ids"] == result["paper_observation_trade_ids"]

    signal = db.get(Signal, result["signal_ids"][0])
    assert signal.status == SignalStatus.WATCHLIST
    assert signal.human_approved is False
    signal_meta = signal.metadata_json
    required_keys = {
        "entry_variant_id",
        "regime",
        "entry_gate",
        "entry_quality",
        "opportunity_rank",
        "opportunity_rank_score",
        "near_miss",
        "near_miss_reasons",
        "entry_gate_rejection_reasons",
        "would_have_failed_entry_gate",
        "paper_only",
        "no_ibkr_order",
    }
    assert required_keys.issubset(signal_meta)
    assert signal_meta["near_miss"] is True
    assert signal_meta["near_miss_shadow"] is True
    assert signal_meta["near_miss_reasons"] == ["insufficient_volume"]
    assert signal_meta["entry_gate_rejection_reasons"] == ["insufficient_volume"]
    assert signal_meta["would_have_failed_entry_gate"] is True
    assert signal_meta["paper_only"] is True
    assert signal_meta["no_ibkr_order"] is True
    assert signal_meta["evidence_type"] == EvidenceType.NEAR_MISS_SHADOW.value
    assert signal_meta["evidence_quality"] == EvidenceQuality.NORMAL.value
    assert signal_meta["entry_quality"]["actionable"] is False
    assert signal_meta["entry_module"] == "laboratory"

    observation = db.get(Trade, result["paper_observation_trade_ids"][0])
    trade_meta = observation.metadata_json
    assert observation.status == TradeStatus.OPEN
    assert trade_meta["execution_mode"] == LAB_SHADOW_EXECUTION_MODE
    assert trade_meta["opened_reason"] == "lab_near_miss_volume_shadow_observation"
    assert required_keys.issubset(trade_meta)
    assert trade_meta["near_miss"] is True
    assert trade_meta["paper_only"] is True
    assert trade_meta["no_ibkr_order"] is True
    assert trade_meta["evidence_type"] == EvidenceType.NEAR_MISS_SHADOW.value
    assert trade_meta["evidence_quality"] == EvidenceQuality.NORMAL.value


def test_laboratory_near_miss_hard_blocker_does_not_open_shadow_observation() -> None:
    db = session_factory()
    provider = FixtureProvider()
    pattern = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    match = near_miss_volume_payload(
        pattern_id=pattern.id,
        pattern_name=pattern.name,
        pattern_key=pattern.pattern_key,
    )
    entry_gate = dict(match["metrics"]["entry_gate"])
    entry_gate.update(
        {
            "extension_atr": 3.4,
            "not_extended": False,
            "reason": "insufficient_volume;excessive_extension",
            "rejection_reasons": ["insufficient_volume", "excessive_extension"],
        }
    )
    match["metrics"] = {**match["metrics"], "entry_gate": entry_gate}
    cfg = scanner(provider, entry_gate_enabled=True).settings

    result = PatternEntryScanner(settings=cfg, matcher=StaticMatcher(provider, [match])).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )

    assert result["rejected_by_entry_gate"] == 1
    assert result["signals_created"] == 0
    assert result["paper_observations_opened"] == 0
    assert result["near_miss_shadow_observations_opened"] == 0
    assert db.query(Signal).count() == 0
    assert db.query(Trade).count() == 0


def test_fox_hunter_does_not_open_lab_near_miss_shadow_observation() -> None:
    db = session_factory()
    provider = FixtureProvider("FOXX")
    match = near_miss_volume_payload(
        module="fox_hunter",
        pattern_status="production",
        pattern_promotion_status="production",
        symbol=provider.symbol,
        status="production_entry_candidate",
    )
    cfg = scanner(provider, entry_gate_enabled=True).settings

    result = PatternEntryScanner(settings=cfg, matcher=StaticMatcher(provider, [match])).scan(
        db,
        module="fox_hunter",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )

    assert result["rejected_by_entry_gate"] == 0
    assert result["rejected_by_production_manifest"] == 1
    assert result["signals_created"] == 0
    assert result["paper_observations_opened"] == 0
    assert result["near_miss_shadow_observations_opened"] == 0
    assert db.query(Signal).count() == 0
    assert db.query(Trade).count() == 0


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
    _, trade = add_shadow_observation(db, opened_at=opened_at)
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
    assert trade.metadata_json["evidence_type"] == EvidenceType.SHADOW_NO_ORDER.value
    assert trade.metadata_json["evidence_quality"] == EvidenceQuality.NORMAL.value
    assert trade.metadata_json["no_ibkr_order"] is True


def test_lab_shadow_observation_records_market_data_unavailable_without_fallback() -> None:
    db = session_factory()
    _, trade = add_shadow_observation(
        db,
        opened_at=datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc),
    )

    result = LabPaperObservationService(settings=Settings(), provider=NoBarsProvider()).close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 0
    assert result["diagnosed_observations"] == 1
    assert result["data_errors"][0]["status"] == "market_data_unavailable"
    assert "IBKR returned no bars" in result["data_errors"][0]["reason"]
    assert trade.status == TradeStatus.OPEN
    assert trade.metadata_json["market_data_unavailable"] is True
    assert trade.metadata_json["shadow_lifecycle"]["last_bar"] is None
    assert trade.metadata_json["shadow_lifecycle"]["mark_to_market"] is None
    assert trade.metadata_json["evidence_type"] == EvidenceType.SHADOW_NO_ORDER.value
    assert trade.metadata_json["evidence_quality"] == EvidenceQuality.NORMAL.value
    assert trade.metadata_json["no_ibkr_order"] is True


def test_lab_shadow_observation_marks_to_market_from_signal_snapshot_after_no_bars() -> None:
    db = session_factory()
    _, trade = add_shadow_observation(
        db,
        opened_at=datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc),
        signal_metadata={
            "entry_module": "laboratory",
            "pattern_id": 1,
            "signal_snapshot": {
                "captured_at": "2026-01-02T14:29:00+00:00",
                "features": {"last_close": 10.75},
            },
        },
    )

    result = LabPaperObservationService(settings=Settings(), provider=NoBarsProvider()).close_open_observations(db)
    db.refresh(trade)

    lifecycle = trade.metadata_json["shadow_lifecycle"]
    assert result["closed_observations"] == 0
    assert result["diagnosed_observations"] == 1
    assert trade.status == TradeStatus.OPEN
    assert lifecycle["status"] == "market_data_unavailable"
    assert lifecycle["fallback_used"] is True
    assert lifecycle["fallback_source"] == "signal.metadata_json.signal_snapshot.features.last_close"
    assert lifecycle["mark_to_market"]["price"] == 10.75
    assert lifecycle["mark_to_market"]["unrealized_pnl"] == 2.25
    assert lifecycle["mark_to_market"]["entry"] == 10.0
    assert trade.metadata_json["evidence_type"] == EvidenceType.SHADOW_NO_ORDER.value
    assert trade.metadata_json["evidence_quality"] == EvidenceQuality.DEGRADED.value
    assert trade.metadata_json["no_ibkr_order"] is True


def test_lab_shadow_observation_closes_from_metadata_bar_after_no_bars() -> None:
    db = session_factory()
    _, trade = add_shadow_observation(
        db,
        opened_at=datetime(2026, 1, 2, 14, 30, tzinfo=timezone.utc),
        trade_metadata={
            "latest_bar": {
                "timestamp": "2026-01-02T14:35:00+00:00",
                "open": 10.2,
                "high": 12.4,
                "low": 10.1,
                "close": 12.1,
                "volume": 1200,
            },
        },
    )

    result = LabPaperObservationService(settings=Settings(), provider=NoBarsProvider()).close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 1
    assert result["diagnosed_observations"] == 0
    assert trade.status == TradeStatus.CLOSED
    assert trade.exit_price == 12.0
    assert trade.metadata_json["exit_reason"] == "target_hit"
    assert trade.metadata_json["evidence_type"] == EvidenceType.SHADOW_NO_ORDER.value
    assert trade.metadata_json["evidence_quality"] == EvidenceQuality.DEGRADED.value
    assert trade.metadata_json["fallback_used"] is True
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

    monkeypatch.setattr("tradeo.modules.shared.entry_scanner.IBKRBroker", BrokenBroker)

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


def test_laboratory_runtime_kill_switch_downgrades_to_shadow_observation(monkeypatch) -> None:
    db = session_factory()
    provider = FixtureProvider()
    pattern = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    activate_runtime_kill_switch(db, reason="reconciliation divergence", actor="test")

    class FailBroker:
        def __init__(self, settings) -> None:
            self.settings = settings

        def submit_signal_bracket(self, db, signal, *, reason: str = "manual"):
            raise AssertionError("runtime kill switch should prevent broker calls")

    monkeypatch.setattr("tradeo.modules.shared.entry_scanner.IBKRBroker", FailBroker)
    match = match_payload(pattern_id=pattern.id, pattern_name=pattern.name, pattern_key=pattern.pattern_key)

    result = PatternEntryScanner(
        settings=scanner(provider, laboratory_auto_submit_paper_orders=True).settings,
        matcher=StaticMatcher(provider, [match]),
    ).scan(db, module="laboratory", symbols=[provider.symbol], store_signals=True)

    assert result["execute_orders"] is False
    assert result["signals_created"] == 1
    assert result["orders_submitted"] == 0
    assert result["order_errors"] == []
    assert result["paper_observations_opened"] == 1
    signal = db.get(Signal, result["signal_ids"][0])
    assert signal.metadata_json["no_ibkr_order"] is True


def test_laboratory_resubmits_duplicate_signal_without_broker_trade(monkeypatch) -> None:
    db = session_factory()
    provider = FixtureProvider()
    pattern = add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)
    match = match_payload(pattern_id=pattern.id, pattern_name=pattern.name, pattern_key=pattern.pattern_key)
    cfg = scanner(provider, ibkr_readonly=False).settings
    idempotency_key = PatternEntryScanner._signal_idempotency_key("laboratory", match)
    signal = Signal(
        symbol=match["symbol"],
        pattern=match["pattern_name"],
        side="long",
        entry=10.0,
        stop=9.0,
        target=14.0,
        reward_risk=4.0,
        confidence=0.8,
        composite_score=0.8,
        risk_usd=10.0,
        suggested_qty=1,
        strategy_version=f"laboratory_pattern_{pattern.id}",
        status=SignalStatus.PAPER_APPROVED,
        metadata_json={
            "entry_module": "laboratory",
            "pattern_id": pattern.id,
            "signal_idempotency_key": idempotency_key,
            "entry_variant_id": match["entry_variant_id"],
            "no_ibkr_order": True,
        },
    )
    db.add(signal)
    db.commit()

    class PaperBroker:
        def __init__(self, settings) -> None:
            self.settings = settings

        def submit_signal_bracket(self, db, signal, *, reason: str = "manual"):
            trade = Trade(
                signal_id=signal.id,
                symbol=signal.symbol,
                pattern=signal.pattern,
                side=signal.side,
                qty=signal.suggested_qty,
                entry=signal.entry,
                stop=signal.stop,
                target=signal.target,
                status=TradeStatus.OPEN,
                opened_at=datetime.now(timezone.utc),
                broker_order_id="paper-backfill",
                metadata_json={"execution_mode": "ibkr", "reason": reason},
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)
            return trade

    monkeypatch.setattr("tradeo.modules.shared.entry_scanner.IBKRBroker", PaperBroker)

    result = PatternEntryScanner(settings=cfg, matcher=StaticMatcher(provider, [match])).scan(
        db,
        module="laboratory",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=True,
    )

    assert result["signals_created"] == 0
    assert result["skipped_duplicates"] == 0
    assert result["orders_submitted"] == 1
    assert db.query(Trade).filter(Trade.signal_id == signal.id).count() == 1


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


def test_laboratory_scanner_records_low_quality_match_without_blocking() -> None:
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

    assert result["rejected_by_entry_quality"] == 0
    assert result["signals_created"] == 1
    assert result["paper_observations_opened"] == 1
    signal = db.query(Signal).one()
    assert signal.metadata_json["entry_quality"]["score"] < 0.8
    assert signal.metadata_json["entry_quality"]["label"] == "weak"


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
    for index in range(10):
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
                evidence_type=EvidenceType.IBKR_PAPER_FILL.value,
                evidence_quality=EvidenceQuality.NORMAL.value,
                metadata_json={
                    "execution_mode": "ibkr",
                    "ibkr_mode": "paper",
                    "evidence_type": EvidenceType.IBKR_PAPER_FILL.value,
                    "evidence_quality": EvidenceQuality.NORMAL.value,
                    "fill_provenance": FillProvenance.BROKER_EXECUTION.value,
                    "broker_execution_hash": f"scanner-history-fill-{index}",
                    "broker_execution_time": f"2026-01-{index + 1:02d}T16:00:00+00:00",
                    "commission": 0.0,
                },
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


def test_laboratory_scanner_ignores_symbol_pattern_cooldown() -> None:
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

    assert result["skipped_cooldown"] == 0
    assert result["signals_created"] == 1


def test_laboratory_scanner_ignores_active_exposure_for_new_lab_observation() -> None:
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
            status=SignalStatus.PAPER_APPROVED,
            metadata_json={"entry_module": "laboratory", "pattern_id": pattern.id},
        )
    )
    db.commit()
    match = match_payload(
        pattern_id=pattern.id,
        pattern_name=pattern.name,
        pattern_key=pattern.pattern_key,
        window_end="2026-06-10T00:00:00+00:00",
    )

    result = PatternEntryScanner(
        settings=scanner(provider).settings,
        matcher=StaticMatcher(provider, [match]),
    ).scan(db, module="laboratory", symbols=[provider.symbol], store_signals=True)

    assert result["skipped_duplicates"] == 0
    assert result["signals_created"] == 1


def test_laboratory_scanner_skips_signal_creation_when_market_closed(monkeypatch) -> None:
    db = session_factory()
    provider = FixtureProvider()
    add_pattern(db, provider, status=DiscoveredPatternStatus.LAB_CANDIDATE)

    monkeypatch.setattr(
        "tradeo.modules.shared.entry_scanner.market_session_status",
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

    blocked = scanner(provider).scan(
        db,
        module="fox_hunter",
        symbols=[provider.symbol],
        store_signals=True,
        execute_orders=False,
    )
    assert blocked["patterns_checked"] == 0
    assert blocked["signals_created"] == 0

    production.metrics_json = {
        **(production.metrics_json or {}),
        "production_manifest": build_production_manifest(
            production,
            reviewer="test_director",
            evidence_packet={"approved_for_production": True, "ibkr_paper_fills": 30},
        ),
    }
    db.add(production)
    db.commit()

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

    result = scanner(provider, discovery_match_ambiguity_hard_gate_enabled=False).scan(
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
    benchmark_regime_calls = [
        call
        for call in provider.fetch_calls
        if call[0] == "SPY" and call[2] == "1d" and call[1] != "3mo"
    ]
    assert len(benchmark_regime_calls) == 1
    assert len(provider.fetch_calls) == 4


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
    assert result["rejected_by_entry_gate"] == 1
    signal = db.get(Signal, result["signal_ids"][0])
    assert signal.metadata_json["near_miss"] is True
    assert signal.metadata_json["evidence_type"] == EvidenceType.NEAR_MISS_SHADOW.value
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
    assert observation.metadata_json["evidence_type"] == EvidenceType.NEAR_MISS_SHADOW.value
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
