from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.agents.pattern_discovery_lab_agent import PatternDiscoveryLabAgent
from tradeo.core.config import Settings
from tradeo.db.models import Signal, SignalStatus
from tradeo.db.session import Base
from tradeo.modules.shared.entry_scanner import PatternEntryScanner
from tradeo.research.cluster_research_engine import ClusterResearchEngine
from tradeo.research.novel_pattern_matcher import NovelPatternMatcher
from tradeo.research.types import ClusterCandidate, ForwardOutcome, WindowSample
from tradeo.research.validation_gate import ValidationGate
from tradeo.services.market_session import US_EQUITY_TZ


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _sample(symbol: str, day_index: int, *, winner: bool) -> WindowSample:
    entry = 100.0
    risk = 5.0
    end = date(2024, 1, 2) + timedelta(days=day_index)
    if winner:
        highs = [101.0, 104.0, 121.0]
        lows = [99.5, 99.0, 103.0]
        closes = [100.5, 103.0, 120.0]
    else:
        highs = [100.5, 100.2, 100.1]
        lows = [99.0, 94.0, 93.5]
        closes = [99.5, 94.5, 94.0]
    return WindowSample(
        symbol=symbol,
        timeframe="1d",
        window_size=20,
        start=(end - timedelta(days=20)).isoformat(),
        end=end.isoformat(),
        year=end.year,
        vector=np.asarray([1.0, 0.5], dtype=np.float32),
        chart={},
        features={},
        outcome=ForwardOutcome(
            forward_returns={10: closes[-1] / entry - 1.0},
            entry_price=entry,
            risk_proxy=risk,
            forward_end=(end + timedelta(days=10)).isoformat(),
            long_mfe_r=(max(highs) - entry) / risk,
            long_mae_r=max(0.0, (entry - min(lows)) / risk),
            long_outcome_r=(closes[-1] - entry) / risk,
            long_hit_4r=winner,
            short_mfe_r=(entry - min(lows)) / risk,
            short_mae_r=max(0.0, (max(highs) - entry) / risk),
            short_outcome_r=(entry - closes[-1]) / risk,
            short_hit_4r=False,
            forward_highs=highs,
            forward_lows=lows,
            forward_closes=closes,
        ),
    )


def _candidate(name: str, *, p_value: float, sharpe: float, n_eff: float) -> ClusterCandidate:
    return ClusterCandidate(
        pattern_key=f"novel_long_w20_{name}",
        name=name,
        side="long",
        timeframe="1d",
        window_size=20,
        cluster_id=0,
        centroid=[0.0, 0.0],
        sample_count=150,
        symbol_count=10,
        year_count=3,
        score=1.0,
        validation_passed=False,
        validation_reasons=[],
        metrics={
            "null_p_value": p_value,
            "trade_sharpe": sharpe,
            "real_variant_count": 144,
            "quant_validation": {
                "n_eff": n_eff,
                "sharpe_per_trade": sharpe,
                "skew": 0.0,
                "kurtosis": 3.0,
                "expectancy_ci95_low": 0.05,
            },
            "effective_sample_count": n_eff,
        },
        feature_summary={},
        examples=[],
    )


# ---------------------------------------------------------------------------
# Engine: n_eff y tau por patrón
# ---------------------------------------------------------------------------


def test_engine_quant_validation_dedups_overlapping_occurrences() -> None:
    engine = ClusterResearchEngine()
    # 30 ocurrencias del mismo símbolo en días consecutivos: outcomes de 10 días
    # solapados ⇒ tras dedup + pesos, n_eff debe ser MUCHO menor que n_raw.
    samples = [_sample("AAA", i, winner=(i % 2 == 0)) for i in range(30)]
    quant = engine._quant_validation_metrics(samples, side="long", rr=4.0)
    assert quant["n_raw"] == 30
    assert quant["n_unique"] < 10
    assert quant["n_eff"] <= quant["n_unique"]
    assert quant["method"] == "dedup_uniqueness_stationary_bootstrap_newey_west"


def test_engine_quant_validation_keeps_disjoint_symbols() -> None:
    engine = ClusterResearchEngine()
    # Misma fecha en símbolos distintos: dedup por símbolo no los toca, pero los
    # pesos de unicidad sí reparten la barra compartida del calendario.
    samples = [_sample(f"SYM{i}", 0, winner=True) for i in range(5)]
    quant = engine._quant_validation_metrics(samples, side="long", rr=4.0)
    assert quant["n_unique"] == 5
    assert abs(quant["n_eff"] - 1.0) < 1e-6  # mismas fechas ⇒ un solo episodio de mercado


def test_engine_match_tau_from_cluster_dispersion() -> None:
    engine = ClusterResearchEngine(match_tau_percentile=92.5)
    rng = np.random.default_rng(11)
    centroid = np.zeros(8)
    vectors = rng.normal(0.0, 0.3, size=(200, 8))
    tau = engine._match_tau_similarity(vectors, centroid)
    similarities = 1.0 / (1.0 + np.linalg.norm(vectors - centroid, axis=1) / np.sqrt(8))
    coverage = float(np.mean(similarities >= tau))
    assert 0.90 <= coverage <= 0.95  # ~92.5% de los miembros reales pasan tau


# ---------------------------------------------------------------------------
# Agente: BH-FDR del run + DSR de familia
# ---------------------------------------------------------------------------


def _agent(tmp_path) -> PatternDiscoveryLabAgent:
    settings = Settings(
        reports_dir=str(tmp_path / "reports"),
        artifacts_dir=str(tmp_path / "artifacts"),
    )

    class _NoProvider:
        def fetch_ohlcv(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("no debe pedir datos")

    return PatternDiscoveryLabAgent(provider=_NoProvider(), settings=settings)


def test_run_level_inference_applies_fdr_and_family_dsr(tmp_path) -> None:
    agent = _agent(tmp_path)
    strong = _candidate("strong", p_value=0.001, sharpe=0.6, n_eff=90.0)
    noise = [
        _candidate(f"noise{i}", p_value=0.30 + 0.05 * i, sharpe=0.05 * (i % 3), n_eff=80.0)
        for i in range(8)
    ]
    candidates = [strong, *noise]
    agent._apply_run_level_inference(candidates)
    assert strong.metrics["fdr_passed"] is True
    assert all(c.metrics["fdr_passed"] is False for c in noise)
    assert strong.metrics["fdr_test_count"] == 9
    assert strong.metrics["dsr_family_n_trials"] >= 144
    assert strong.metrics["dsr_family"] is not None
    # El DSR de familia debe estar deflactado respecto al PSR puro.
    assert 0.0 <= strong.metrics["dsr_family"] <= 1.0


def test_validation_gate_rejects_low_n_eff_and_failed_fdr(tmp_path) -> None:
    settings = Settings(
        reports_dir=str(tmp_path / "reports"), artifacts_dir=str(tmp_path / "artifacts")
    )
    gate = ValidationGate(settings)

    thin = _candidate("thin", p_value=0.001, sharpe=0.5, n_eff=12.0)
    thin.metrics["fdr_passed"] = True
    gate.evaluate(thin)
    assert thin.validation_passed is False
    assert any("muestras efectivas insuficientes" in r for r in thin.validation_reasons)

    failed_fdr = _candidate("failedfdr", p_value=0.40, sharpe=0.5, n_eff=90.0)
    failed_fdr.metrics["fdr_passed"] = False
    failed_fdr.metrics["fdr_q"] = 0.05
    gate.evaluate(failed_fdr)
    assert failed_fdr.validation_passed is False
    assert any("BH-FDR" in r for r in failed_fdr.validation_reasons)


def test_validation_gate_caps_lab_candidate_without_dsr(tmp_path) -> None:
    settings = Settings(
        reports_dir=str(tmp_path / "reports"), artifacts_dir=str(tmp_path / "artifacts")
    )
    gate = ValidationGate(settings)
    candidate = _candidate("promising", p_value=0.001, sharpe=0.6, n_eff=90.0)
    candidate.metrics.update(
        {
            "fdr_passed": True,
            "best_rr": 3.0,
            "best_expectancy_r": 0.5,
            "best_profit_factor": 2.2,
            "best_max_drawdown_r": 4.0,
            "expectancy_r": 0.5,
            "profit_factor": 2.2,
            "stability_score": 0.8,
            "out_of_sample_expectancy_r": 0.3,
            "out_of_sample_profit_factor": 1.9,
            "rr_metrics": {"3": {"expectancy_r": 0.5, "profit_factor": 2.2}},
            "train_sample_count": 150,
            "dsr_family": 0.40,  # por debajo de discovery_min_dsr=0.95
            "dsr_family_n_trials": 5000,
        }
    )
    gate.evaluate(candidate)
    assert candidate.metrics["promotion_status"] != "lab_candidate"
    assert any("DSR familia" in w for w in candidate.metrics["validation_warnings"])


# ---------------------------------------------------------------------------
# Matcher: vela viva y umbral por patrón
# ---------------------------------------------------------------------------


def _daily_df(end: date, bars: int = 30) -> pd.DataFrame:
    idx = pd.date_range(end=pd.Timestamp(end), periods=bars, freq="B")
    values = np.linspace(100.0, 110.0, bars)
    return pd.DataFrame(
        {
            "open": values,
            "high": values + 1,
            "low": values - 1,
            "close": values,
            "volume": np.full(bars, 1e6),
        },
        index=idx,
    )


def test_matcher_drops_live_daily_bar_during_session() -> None:
    in_session = datetime(2026, 6, 10, 12, 0, tzinfo=US_EQUITY_TZ)  # miércoles 12:00 NY
    df = _daily_df(end=date(2026, 6, 10))
    trimmed = NovelPatternMatcher._drop_incomplete_daily_bar(df, "1d", now=in_session)
    assert len(trimmed) == len(df) - 1
    assert pd.Timestamp(trimmed.index[-1]).date() == date(2026, 6, 9)


def test_matcher_keeps_bar_after_close_and_yesterday_bars() -> None:
    after_close = datetime(2026, 6, 10, 16, 30, tzinfo=US_EQUITY_TZ)
    df_today = _daily_df(end=date(2026, 6, 10))
    assert len(NovelPatternMatcher._drop_incomplete_daily_bar(df_today, "1d", now=after_close)) == len(
        df_today
    )
    in_session = datetime(2026, 6, 10, 12, 0, tzinfo=US_EQUITY_TZ)
    df_yesterday = _daily_df(end=date(2026, 6, 9))
    assert len(
        NovelPatternMatcher._drop_incomplete_daily_bar(df_yesterday, "1d", now=in_session)
    ) == len(df_yesterday)


def test_matcher_ignores_intraday_frames() -> None:
    in_session = datetime(2026, 6, 10, 12, 0, tzinfo=US_EQUITY_TZ)
    df = _daily_df(end=date(2026, 6, 10))
    assert len(NovelPatternMatcher._drop_incomplete_daily_bar(df, "1h", now=in_session)) == len(df)


class _PatternStub:
    def __init__(self, tau: float | None) -> None:
        self.metrics_json = {} if tau is None else {"match_tau_similarity": tau}


def test_matcher_per_pattern_threshold_uses_floor_and_tau(tmp_path) -> None:
    settings = Settings(
        reports_dir=str(tmp_path / "reports"), artifacts_dir=str(tmp_path / "artifacts")
    )
    matcher = NovelPatternMatcher(provider=object(), settings=settings)
    assert matcher._effective_threshold(_PatternStub(0.80), 0.45) == 0.80
    assert matcher._effective_threshold(_PatternStub(0.20), 0.45) == 0.45  # el global es suelo
    assert matcher._effective_threshold(_PatternStub(None), 0.45) == 0.45
    settings_off = Settings(
        reports_dir=str(tmp_path / "r2"),
        artifacts_dir=str(tmp_path / "a2"),
        discovery_match_per_pattern_threshold=False,
    )
    matcher_off = NovelPatternMatcher(provider=object(), settings=settings_off)
    assert matcher_off._effective_threshold(_PatternStub(0.80), 0.45) == 0.45


# ---------------------------------------------------------------------------
# Lab: idempotencia de señal (pattern, symbol, variante, barra)
# ---------------------------------------------------------------------------


def _match_dict(window_end: str) -> dict:
    return {
        "pattern_id": 7,
        "pattern_name": "DISCOVERED_LONG_W20_C01_TEST",
        "symbol": "LABX",
        "timeframe": "1d",
        "entry_variant_id": "breakout_v1",
        "window_end": window_end,
    }


def test_signal_idempotency_key_is_stable_per_bar() -> None:
    key_a = PatternEntryScanner._signal_idempotency_key("laboratory", _match_dict("2026-06-09"))
    key_b = PatternEntryScanner._signal_idempotency_key("laboratory", _match_dict("2026-06-09"))
    key_c = PatternEntryScanner._signal_idempotency_key("laboratory", _match_dict("2026-06-10"))
    assert key_a == key_b
    assert key_a != key_c
    assert PatternEntryScanner._signal_idempotency_key("fox_hunter", _match_dict("2026-06-09")) != key_a


def test_duplicate_signal_detected_for_same_bar(tmp_path) -> None:
    db = _session()
    settings = Settings(
        reports_dir=str(tmp_path / "reports"), artifacts_dir=str(tmp_path / "artifacts")
    )
    scanner = PatternEntryScanner(settings=settings, matcher=object())
    match = _match_dict("2026-06-09")
    db.add(
        Signal(
            symbol="LABX",
            pattern="DISCOVERED_LONG_W20_C01_TEST",
            side="long",
            timeframe="1d",
            entry=100.0,
            stop=95.0,
            target=115.0,
            reward_risk=3.0,
            confidence=0.7,
            composite_score=0.7,
            strategy_version="laboratory_pattern_7",
            status=SignalStatus.PAPER_APPROVED,
            metadata_json={
                "entry_module": "laboratory",
                "signal_idempotency_key": PatternEntryScanner._signal_idempotency_key(
                    "laboratory", match
                ),
            },
        )
    )
    db.commit()
    assert scanner._has_duplicate_signal(db, match, module="laboratory") is True
    assert scanner._has_duplicate_signal(db, _match_dict("2026-06-10"), module="laboratory") is False
    assert scanner._has_duplicate_signal(db, match, module="fox_hunter") is False
