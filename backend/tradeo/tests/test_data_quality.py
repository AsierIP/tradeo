from __future__ import annotations

import numpy as np
import pandas as pd

from tradeo.services.data_quality import (
    ISSUE_CALENDAR_GAP,
    ISSUE_INSUFFICIENT_BARS,
    ISSUE_STALE_CLOSES,
    ISSUE_SUSPECT_BAR_RETURN,
    ISSUE_ZERO_VOLUME,
    assess_ohlcv_quality,
)
from tradeo.tests.fixtures import fixture_ohlcv


def test_clean_fixture_is_research_grade() -> None:
    df = fixture_ohlcv("AAPL", bars=300)
    report = assess_ohlcv_quality(df, "AAPL")
    assert report.research_grade
    assert report.issues == []
    assert report.bars == 300


def test_empty_frame_is_rejected() -> None:
    report = assess_ohlcv_quality(pd.DataFrame(columns=["open", "high", "low", "close", "volume"]))
    assert not report.research_grade
    assert ISSUE_INSUFFICIENT_BARS in report.issues


def test_insufficient_bars_flagged() -> None:
    df = fixture_ohlcv("AAPL", bars=30)
    report = assess_ohlcv_quality(df, "AAPL", min_bars=60)
    assert ISSUE_INSUFFICIENT_BARS in report.issues


def test_zero_volume_run_flagged() -> None:
    df = fixture_ohlcv("HALT", bars=200)
    df.loc[df.index[-80:], "volume"] = 0.0
    report = assess_ohlcv_quality(df, "HALT")
    assert ISSUE_ZERO_VOLUME in report.issues
    assert report.zero_volume_pct >= 0.15


def test_stale_close_run_flagged() -> None:
    df = fixture_ohlcv("FROZEN", bars=200)
    df.loc[df.index[-20:], "close"] = 12.34
    report = assess_ohlcv_quality(df, "FROZEN")
    assert ISSUE_STALE_CLOSES in report.issues
    assert report.longest_stale_close_run >= 20


def test_calendar_gap_flagged_for_daily_bars() -> None:
    df = fixture_ohlcv("GAPPY", bars=200)
    # Remove 15 business days from the middle of the series.
    df = pd.concat([df.iloc[:100], df.iloc[115:]])
    report = assess_ohlcv_quality(df, "GAPPY", interval="1d")
    assert ISSUE_CALENDAR_GAP in report.issues
    assert report.max_single_gap_business_days >= 15


def test_calendar_gap_ignored_for_intraday() -> None:
    df = fixture_ohlcv("GAPPY", bars=200)
    df = pd.concat([df.iloc[:100], df.iloc[115:]])
    report = assess_ohlcv_quality(df, "GAPPY", interval="5m")
    assert ISSUE_CALENDAR_GAP not in report.issues


def test_suspect_split_jump_flagged() -> None:
    df = fixture_ohlcv("SPLIT", bars=200)
    df.loc[df.index[-50:], ["open", "high", "low", "close"]] *= 10.0
    report = assess_ohlcv_quality(df, "SPLIT")
    assert ISSUE_SUSPECT_BAR_RETURN in report.issues
    assert report.max_bar_return_ratio > 4.0


def test_downward_split_jump_flagged_symmetrically() -> None:
    df = fixture_ohlcv("RSPLIT", bars=200)
    df.loc[df.index[-50:], ["open", "high", "low", "close"]] /= 10.0
    report = assess_ohlcv_quality(df, "RSPLIT")
    assert ISSUE_SUSPECT_BAR_RETURN in report.issues


def test_report_to_dict_is_json_friendly() -> None:
    df = fixture_ohlcv("AAPL", bars=120)
    payload = assess_ohlcv_quality(df, "AAPL").to_dict()
    assert payload["symbol"] == "AAPL"
    assert isinstance(payload["issues"], list)
    assert payload["research_grade"] is True
    assert all(np.isfinite(payload[k]) for k in ("zero_volume_pct", "max_bar_return_ratio"))


def test_scanner_skips_low_quality_symbols(monkeypatch) -> None:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from tradeo.db.models import AuditLog
    from tradeo.db.session import Base
    from tradeo.schemas import ScanRequest
    from tradeo.services.scanner import MarketScanner

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, future=True)()

    bad = fixture_ohlcv("BAD", bars=200)
    bad.loc[bad.index[-80:], "volume"] = 0.0

    class _Provider:
        def fetch_ohlcv(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
            return bad

    scanner = MarketScanner(provider=_Provider())
    response = scanner.run(ScanRequest(force_symbols=["BAD"]), session, store=True)

    assert response.data_quality_skips == 1
    assert response.candidates == 0
    session.commit()
    audit_rows = session.execute(
        select(AuditLog).where(AuditLog.action == "market_data_quality_reject")
    ).scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].entity_id == "BAD"
    assert ISSUE_ZERO_VOLUME in audit_rows[0].details_json["issues"]
