from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from tradeo.db.models import (
    IntradayFlattenAttempt,
    IntradayPacingLedger,
    IntradayRiskLedger,
    IntradaySession,
    IntradaySymbolState,
    IntradayUniverseSnapshot,
    Signal,
)
from tradeo.db.session import Base


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _intraday_session() -> IntradaySession:
    opened = datetime(2026, 6, 22, 13, 30, tzinfo=timezone.utc)
    closed = datetime(2026, 6, 22, 20, 0, tzinfo=timezone.utc)
    return IntradaySession(
        session_date=date(2026, 6, 22),
        market="NYSE",
        timezone="America/New_York",
        regular_open_at=opened,
        regular_close_at=closed,
        no_new_entries_at=datetime(2026, 6, 22, 19, 30, tzinfo=timezone.utc),
        cancel_entries_at=datetime(2026, 6, 22, 19, 40, tzinfo=timezone.utc),
        force_flat_start_at=datetime(2026, 6, 22, 19, 45, tzinfo=timezone.utc),
        hard_flat_deadline_at=datetime(2026, 6, 22, 19, 55, tzinfo=timezone.utc),
    )


def test_intraday_session_tables_persist_independent_state() -> None:
    db = _db_session()
    session = _intraday_session()
    db.add(session)
    db.flush()

    db.add(
        IntradayUniverseSnapshot(
            session_id=session.id,
            session_date=session.session_date,
            bucket="open",
            timeframe="5m",
            symbols_json=["SOUN"],
            filters_json={"min_price": 3},
            excluded_json=[{"symbol": "XYZ", "reason": "spread"}],
            pacing_budget_json={"remaining": 4},
        )
    )
    db.add(
        IntradaySymbolState(
            session_id=session.id,
            session_date=session.session_date,
            symbol="SOUN",
            timeframe="5m",
            status="active",
        )
    )
    db.add(
        IntradayPacingLedger(
            session_id=session.id,
            session_date=session.session_date,
            request_type="historical",
            symbol="SOUN",
            timeframe="5m",
            allowed=True,
            budget_remaining=3,
        )
    )
    db.add(
        IntradayRiskLedger(
            session_id=session.id,
            session_date=session.session_date,
            event_type="entry_reserved",
            symbol="SOUN",
            timeframe="5m",
            scope="intraday",
            delta_risk_usd=5.0,
        )
    )
    db.add(
        IntradayFlattenAttempt(
            session_id=session.id,
            session_date=session.session_date,
            symbol="SOUN",
            action="preview_reduce_only_exit",
            side="SELL",
            qty=10,
            status="preview",
        )
    )
    db.commit()

    stored = db.query(IntradaySession).one()
    assert stored.session_date == date(2026, 6, 22)
    assert stored.universe_snapshots[0].symbols_json == ["SOUN"]
    assert stored.symbol_states[0].status == "active"
    assert stored.pacing_events[0].allowed is True
    assert stored.risk_events[0].scope == "intraday"
    assert stored.flatten_attempts[0].status == "preview"


def test_intraday_signal_dedupe_uses_metadata_namespace() -> None:
    db = _db_session()
    payload = {
        "intraday": {
            "session_id": "2026-06-22",
            "entry_variant": "breakout_v1",
            "window_end": "2026-06-22T14:35:00Z",
        }
    }
    for _ in range(2):
        db.add(
            Signal(
                symbol="SOUN",
                pattern="intraday_breakout",
                side="long",
                timeframe="5m",
                entry=10.0,
                stop=9.5,
                target=12.0,
                reward_risk=4.0,
                confidence=0.7,
                composite_score=0.8,
                metadata_json=payload,
            )
        )
    with pytest.raises(IntegrityError):
        db.commit()
