"""ShadowTracker canonical-outcome parity tests (informe §6).

Shadow observation exits must use the same triple-barrier fill rules as the
backtester and Research RR simulation (`triple_barrier_outcome`):

- a bar that opens through the stop fills at the OPEN (worse than the stop),
  never at the stop price;
- a bar that opens through the target fills at the TARGET (a limit order does
  not collect the gap);
- intrabar stop+target in the same bar resolves to the STOP (conservative);
- time stops wait for the full holding window before closing at the close.

The closed trade also persists a `canonical_outcome` metadata block so any
gate decision can be reproduced against the canonical engine output.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tradeo.core.config import Settings
from tradeo.db.models import Signal, SignalStatus, Trade, TradeStatus
from tradeo.db.session import Base
from tradeo.modules.laboratory.paper_observations import (
    CANONICAL_EXIT_REASON_MAP,
    LabPaperObservationService,
)
from tradeo.research.quant_validation import triple_barrier_outcome
from tradeo.services.evidence import EvidenceQuality, EvidenceType

OPENED_AT = datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc)
FIRST_BAR_AT = datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc)


def session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


class FakeProvider:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def fetch_ohlcv(self, symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
        return self._frame


def make_frame(rows: list[dict], start: datetime = FIRST_BAR_AT) -> pd.DataFrame:
    index = pd.DatetimeIndex(
        [pd.Timestamp(start + timedelta(days=offset)) for offset in range(len(rows))]
    )
    return pd.DataFrame(rows, index=index)


def bar(open_: float, high: float, low: float, close: float) -> dict:
    return {"open": open_, "high": high, "low": low, "close": close, "volume": 1000.0}


def add_shadow_observation(
    db,
    *,
    side: str = "long",
    entry: float = 10.0,
    stop: float = 9.0,
    target: float = 14.0,
) -> Trade:
    signal = Signal(
        symbol="AAPL",
        pattern="cup_handle",
        side=side,
        entry=entry,
        stop=stop,
        target=target,
        reward_risk=abs(target - entry) / max(abs(entry - stop), 1e-9),
        confidence=0.7,
        composite_score=0.7,
        risk_usd=10.0,
        suggested_qty=5,
        status=SignalStatus.EXECUTED,
        human_approved=True,
        metadata_json={},
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    trade = Trade(
        signal_id=signal.id,
        symbol="AAPL",
        pattern="cup_handle",
        side=side,
        qty=5,
        entry=entry,
        stop=stop,
        target=target,
        status=TradeStatus.OPEN,
        opened_at=OPENED_AT,
        evidence_type=EvidenceType.SHADOW_NO_ORDER.value,
        evidence_quality=EvidenceQuality.NORMAL.value,
        metadata_json={
            "execution_mode": "lab_shadow_observation",
            "observation_only": True,
            "no_ibkr_order": True,
            "evidence_type": EvidenceType.SHADOW_NO_ORDER.value,
            "evidence_quality": EvidenceQuality.NORMAL.value,
        },
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


def service(frame: pd.DataFrame, *, forward_bars: str = "5,10,20") -> LabPaperObservationService:
    return LabPaperObservationService(
        settings=Settings(discovery_forward_bars=forward_bars),
        provider=FakeProvider(frame),
    )


def test_gap_through_stop_on_first_bar_fills_at_open() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    # First bar after opened_at opens at 8.4, through the 9.0 stop.
    frame = make_frame([bar(8.4, 8.6, 8.2, 8.5)])

    result = service(frame).close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 1
    assert trade.status == TradeStatus.CLOSED
    assert trade.exit_price == pytest.approx(8.4)
    assert trade.r_multiple == pytest.approx(-1.6)
    assert trade.metadata_json["exit_reason"] == "stop_gap"


def test_gap_through_stop_on_later_bar_fills_at_open() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    frame = make_frame(
        [
            bar(10.0, 10.5, 9.8, 10.2),
            bar(8.5, 8.7, 8.3, 8.6),
        ]
    )

    service(frame).close_open_observations(db)
    db.refresh(trade)

    assert trade.exit_price == pytest.approx(8.5)
    assert trade.r_multiple == pytest.approx(-1.5)
    assert trade.metadata_json["exit_reason"] == "stop_gap"


def test_gap_past_target_fills_at_target_not_open() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    frame = make_frame(
        [
            bar(10.0, 10.5, 9.8, 10.2),
            bar(15.0, 15.5, 14.8, 15.2),
        ]
    )

    service(frame).close_open_observations(db)
    db.refresh(trade)

    assert trade.exit_price == pytest.approx(14.0)
    assert trade.r_multiple == pytest.approx(4.0)
    assert trade.metadata_json["exit_reason"] == "target_gap"


def test_intrabar_stop_and_target_resolves_to_stop() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    # Single bar touches both barriers without opening through either.
    frame = make_frame([bar(10.0, 14.5, 8.5, 10.0)])

    service(frame).close_open_observations(db)
    db.refresh(trade)

    assert trade.exit_price == pytest.approx(9.0)
    assert trade.r_multiple == pytest.approx(-1.0)
    assert trade.metadata_json["exit_reason"] == "stop_hit"
    assert trade.metadata_json["canonical_outcome"]["reason"] == "stop_and_target_conservative"


def test_short_side_gap_through_stop_fills_at_open() -> None:
    db = session_factory()
    trade = add_shadow_observation(db, side="short", entry=10.0, stop=11.0, target=6.0)
    frame = make_frame(
        [
            bar(10.0, 10.5, 9.8, 10.2),
            bar(11.6, 11.8, 11.4, 11.7),
        ]
    )

    service(frame).close_open_observations(db)
    db.refresh(trade)

    assert trade.exit_price == pytest.approx(11.6)
    assert trade.r_multiple == pytest.approx(-1.6)
    assert trade.metadata_json["exit_reason"] == "stop_gap"


def test_time_stop_waits_for_full_holding_window() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    quiet = bar(10.0, 10.4, 9.8, 10.1)
    # Window is 3 bars; only 2 available -> must stay open.
    frame = make_frame([quiet, quiet])

    result = service(frame, forward_bars="3").close_open_observations(db)
    db.refresh(trade)

    assert result["closed_observations"] == 0
    assert trade.status == TradeStatus.OPEN

    # With the full window available it closes at the last close.
    frame = make_frame([quiet, quiet, bar(10.0, 10.4, 9.8, 10.3)])
    service(frame, forward_bars="3").close_open_observations(db)
    db.refresh(trade)

    assert trade.status == TradeStatus.CLOSED
    assert trade.exit_price == pytest.approx(10.3)
    assert trade.metadata_json["exit_reason"] == "time_stop"


def test_canonical_outcome_block_is_persisted() -> None:
    db = session_factory()
    trade = add_shadow_observation(db)
    frame = make_frame(
        [
            bar(10.0, 11.0, 9.5, 10.5),
            bar(10.5, 14.5, 10.0, 14.0),
        ]
    )

    service(frame).close_open_observations(db)
    db.refresh(trade)

    block = trade.metadata_json["canonical_outcome"]
    assert block["engine"] == "triple_barrier_outcome"
    assert block["status"] == "ok"
    assert block["reason"] == "target"
    assert block["conservative_both"] is True
    assert block["round_trip_cost_R"] == 0.0
    assert block["bars_held"] == 2
    assert block["r_multiple"] == pytest.approx(4.0)
    assert trade.metadata_json["exit_reason"] == "target_hit"
    assert trade.r_multiple == pytest.approx(block["r_multiple"])


@pytest.mark.parametrize("side", ["long", "short"])
def test_shadow_exit_matches_canonical_engine_directly(side: str) -> None:
    """Engine-level parity: the persisted exit equals triple_barrier_outcome
    run over the same synthetic-entry construction."""
    db = session_factory()
    if side == "long":
        trade = add_shadow_observation(db, side="long", entry=10.0, stop=9.0, target=14.0)
        rows = [
            bar(10.0, 10.8, 9.4, 10.2),
            bar(8.6, 9.2, 8.4, 9.0),
        ]
    else:
        trade = add_shadow_observation(db, side="short", entry=10.0, stop=11.0, target=6.0)
        rows = [
            bar(10.0, 10.6, 9.2, 9.8),
            bar(9.5, 9.7, 5.8, 6.1),
        ]
    frame = make_frame(rows)

    service(frame).close_open_observations(db)
    db.refresh(trade)

    entry = float(trade.entry)
    expected = triple_barrier_outcome(
        [entry, entry, *(r["open"] for r in rows)],
        [entry, entry, *(r["high"] for r in rows)],
        [entry, entry, *(r["low"] for r in rows)],
        [entry, entry, *(r["close"] for r in rows)],
        signal_index=0,
        side=-1 if side == "short" else 1,
        stop_price=float(trade.stop),
        target_price=float(trade.target),
        max_bars=21,
        entry_price=entry,
        gap_entry_policy="skip",
        conservative_both=True,
        round_trip_cost_R=0.0,
    )

    assert trade.status == TradeStatus.CLOSED
    assert trade.exit_price == pytest.approx(float(expected["exit_price"]))
    assert trade.r_multiple == pytest.approx(float(expected["R"]))
    assert trade.metadata_json["exit_reason"] == CANONICAL_EXIT_REASON_MAP[str(expected["reason"])]
