from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from tradeo.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def json_type() -> Any:
    # PostgreSQL uses JSONB; SQLite/testing can use generic JSON.
    return JSONB().with_variant(JSON(), "sqlite")


class SignalStatus(str, Enum):
    WATCHLIST = "watchlist"
    REJECTED = "rejected"
    PAPER_APPROVED = "paper_approved"
    PENDING_HUMAN_APPROVAL = "pending_human_approval"
    LIVE_APPROVED = "live_approved"
    EXECUTED = "executed"
    EXPIRED = "expired"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Signal(Base):
    """Canonical trading signal.

    Intraday extensions must use ``metadata_json["intraday"]`` for
    session-scoped fields such as ``session_id``, ``entry_variant`` and
    ``window_end``. Orders remain represented by Signal/Trade plus ledgers; WP-02
    intentionally does not introduce a parallel order table.
    """

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    pattern: Mapped[str] = mapped_column(String(80), index=True)
    side: Mapped[str] = mapped_column(String(8))
    timeframe: Mapped[str] = mapped_column(String(16), default="1d")
    entry: Mapped[float] = mapped_column(Float)
    stop: Mapped[float] = mapped_column(Float)
    target: Mapped[float] = mapped_column(Float)
    reward_risk: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    composite_score: Mapped[float] = mapped_column(Float)
    risk_usd: Mapped[float] = mapped_column(Float, default=0.0)
    suggested_qty: Mapped[int] = mapped_column(Integer, default=0)
    strategy_version: Mapped[str] = mapped_column(String(80), default="cup_v0")
    status: Mapped[SignalStatus] = mapped_column(SAEnum(SignalStatus), default=SignalStatus.WATCHLIST)
    supervisor_notes: Mapped[str] = mapped_column(Text, default="")
    human_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)

    trades: Mapped[list["Trade"]] = relationship(back_populates="signal")


class Trade(Base):
    """Canonical trade/fill lifecycle row.

    Intraday-only execution metadata belongs under ``metadata_json["intraday"]``
    (for example ``must_flat_by``, ``reduce_only_after`` and EOD flat details)
    so daily Trade semantics stay unchanged.
    """

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    pattern: Mapped[str] = mapped_column(String(80), index=True)
    side: Mapped[str] = mapped_column(String(8))
    qty: Mapped[int] = mapped_column(Integer)
    entry: Mapped[float] = mapped_column(Float)
    stop: Mapped[float] = mapped_column(Float)
    target: Mapped[float] = mapped_column(Float)
    status: Mapped[TradeStatus] = mapped_column(SAEnum(TradeStatus), default=TradeStatus.OPEN)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_usd: Mapped[float] = mapped_column(Float, default=0.0)
    r_multiple: Mapped[float] = mapped_column(Float, default=0.0)
    broker_order_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    evidence_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    evidence_quality: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)

    signal: Mapped[Signal | None] = relationship(back_populates="trades")


_SIGNALS_INTRADAY_DEDUPE_PG = Index(
    "uq_signals_intraday_dedupe_pg",
    Signal.symbol,
    Signal.pattern,
    Signal.timeframe,
    text(
        "COALESCE("
        "metadata_json -> 'intraday' ->> 'entry_variant', "
        "metadata_json -> 'intraday' ->> 'entry_variant_id'"
        ")"
    ),
    text("metadata_json -> 'intraday' ->> 'window_end'"),
    text("metadata_json -> 'intraday' ->> 'session_id'"),
    unique=True,
    postgresql_where=text(
        "metadata_json ? 'intraday' "
        "AND metadata_json -> 'intraday' ->> 'session_id' IS NOT NULL "
        "AND COALESCE("
        "metadata_json -> 'intraday' ->> 'entry_variant', "
        "metadata_json -> 'intraday' ->> 'entry_variant_id'"
        ") IS NOT NULL "
        "AND metadata_json -> 'intraday' ->> 'window_end' IS NOT NULL"
    ),
).ddl_if(dialect="postgresql")

_SIGNALS_INTRADAY_DEDUPE_SQLITE = Index(
    "uq_signals_intraday_dedupe_sqlite",
    Signal.symbol,
    Signal.pattern,
    Signal.timeframe,
    text(
        "COALESCE("
        "json_extract(metadata_json, '$.intraday.entry_variant'), "
        "json_extract(metadata_json, '$.intraday.entry_variant_id')"
        ")"
    ),
    text("json_extract(metadata_json, '$.intraday.window_end')"),
    text("json_extract(metadata_json, '$.intraday.session_id')"),
    unique=True,
    sqlite_where=text(
        "json_extract(metadata_json, '$.intraday.session_id') IS NOT NULL "
        "AND COALESCE("
        "json_extract(metadata_json, '$.intraday.entry_variant'), "
        "json_extract(metadata_json, '$.intraday.entry_variant_id')"
        ") IS NOT NULL "
        "AND json_extract(metadata_json, '$.intraday.window_end') IS NOT NULL"
    ),
).ddl_if(dialect="sqlite")


class IntradaySession(Base):
    __tablename__ = "intraday_sessions"
    __table_args__ = (
        UniqueConstraint("session_date", "market", name="uq_intraday_sessions_date_market"),
        Index("ix_intraday_sessions_session_date_state", "session_date", "state"),
        Index("ix_intraday_sessions_session_date_flat_status", "session_date", "flat_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    market: Mapped[str] = mapped_column(String(24), default="US")
    timezone: Mapped[str] = mapped_column(String(64), default="America/New_York")
    regular_open_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    regular_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_half_day: Mapped[bool] = mapped_column(Boolean, default=False)
    no_new_entries_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancel_entries_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    force_flat_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    hard_flat_deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(40), default="PREMARKET_PREP", index=True)
    flat_status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    flat_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    flat_failed_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    universe_snapshots: Mapped[list["IntradayUniverseSnapshot"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    symbol_states: Mapped[list["IntradaySymbolState"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    pacing_events: Mapped[list["IntradayPacingLedger"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    risk_events: Mapped[list["IntradayRiskLedger"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    flatten_attempts: Mapped[list["IntradayFlattenAttempt"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class IntradayUniverseSnapshot(Base):
    __tablename__ = "intraday_universe_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "bucket",
            "timeframe",
            "generated_at",
            name="uq_intraday_universe_snapshot_version",
        ),
        Index("ix_intraday_universe_snapshots_session_date_bucket", "session_date", "bucket"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("intraday_sessions.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    bucket: Mapped[str] = mapped_column(String(40), default="premarket", index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="multi", index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    symbols_json: Mapped[list[str]] = mapped_column(json_type(), default=list)
    filters_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    excluded_json: Mapped[list[dict[str, Any]]] = mapped_column(json_type(), default=list)
    pacing_budget_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[IntradaySession] = relationship(back_populates="universe_snapshots")


class IntradaySymbolState(Base):
    __tablename__ = "intraday_symbol_state"
    __table_args__ = (
        UniqueConstraint("session_id", "symbol", "timeframe", name="uq_intraday_symbol_state_symbol_timeframe"),
        Index("ix_intraday_symbol_state_session_date_symbol", "session_date", "symbol"),
        Index("ix_intraday_symbol_state_session_date_status", "session_date", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("intraday_sessions.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="multi", index=True)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    trades_today: Mapped[int] = mapped_column(Integer, default=0)
    signals_today: Mapped[int] = mapped_column(Integer, default=0)
    open_position_qty: Mapped[float] = mapped_column(Float, default=0.0)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_stop_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_signal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str] = mapped_column(Text, default="")
    risk_used_usd: Mapped[float] = mapped_column(Float, default=0.0)
    realized_r: Mapped[float] = mapped_column(Float, default=0.0)
    unrealized_r: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    session: Mapped[IntradaySession] = relationship(back_populates="symbol_states")


class IntradayPacingLedger(Base):
    __tablename__ = "intraday_pacing_ledger"
    __table_args__ = (
        Index("ix_intraday_pacing_ledger_session_date_symbol", "session_date", "symbol"),
        Index("ix_intraday_pacing_ledger_timeframe_status", "timeframe", "status"),
        Index("ix_intraday_pacing_ledger_request_type_timestamp", "request_type", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("intraday_sessions.id"), nullable=True, index=True)
    session_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    request_type: Mapped[str] = mapped_column(String(60), index=True)
    symbol: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="", index=True)
    status: Mapped[str] = mapped_column(String(40), default="allowed", index=True)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    budget_remaining: Mapped[int] = mapped_column(Integer, default=0)
    blocked_reason: Mapped[str] = mapped_column(Text, default="")
    ibkr_error_code: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)

    session: Mapped[IntradaySession | None] = relationship(back_populates="pacing_events")


class IntradayRiskLedger(Base):
    __tablename__ = "intraday_risk_ledger"
    __table_args__ = (
        Index("ix_intraday_risk_ledger_session_date_symbol", "session_date", "symbol"),
        Index("ix_intraday_risk_ledger_timeframe_status", "timeframe", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("intraday_sessions.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    symbol: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="", index=True)
    status: Mapped[str] = mapped_column(String(40), default="recorded", index=True)
    scope: Mapped[str] = mapped_column(String(20), default="intraday", index=True)
    source_signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True, index=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), nullable=True, index=True)
    delta_risk_usd: Mapped[float] = mapped_column(Float, default=0.0)
    daily_loss_used_usd: Mapped[float] = mapped_column(Float, default=0.0)
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    session: Mapped[IntradaySession] = relationship(back_populates="risk_events")
    source_signal: Mapped[Signal | None] = relationship()
    trade: Mapped[Trade | None] = relationship()


class IntradayFlattenAttempt(Base):
    __tablename__ = "intraday_flatten_attempts"
    __table_args__ = (
        Index("ix_intraday_flatten_attempts_session_date_status", "session_date", "status"),
        Index("ix_intraday_flatten_attempts_symbol_status", "symbol", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("intraday_sessions.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date, index=True)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), nullable=True, index=True)
    source_signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="", index=True)
    broker_position_qty_before: Mapped[float] = mapped_column(Float, default=0.0)
    db_position_qty_before: Mapped[float] = mapped_column(Float, default=0.0)
    action: Mapped[str] = mapped_column(String(60), index=True)
    order_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    perm_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    side: Mapped[str] = mapped_column(String(8), default="")
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    broker_response_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    verified_position_qty_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason_code: Mapped[str] = mapped_column(String(80), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[IntradaySession] = relationship(back_populates="flatten_attempts")
    trade: Mapped[Trade | None] = relationship()
    source_signal: Mapped[Signal | None] = relationship()


class IntradayWorkItem(Base):
    """Distributed Research/Lab work item with hard dedupe and lease state."""

    __tablename__ = "intraday_work_items"
    __table_args__ = (
        UniqueConstraint("work_fingerprint", name="uq_intraday_work_items_fingerprint"),
        Index("ix_intraday_work_items_scope_status_priority", "scope", "status", "priority"),
        Index("ix_intraday_work_items_lane_status", "lane", "status"),
        Index("ix_intraday_work_items_session_symbol_status", "session_id", "symbol", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope: Mapped[str] = mapped_column(String(24), index=True)
    lane: Mapped[str] = mapped_column(String(48), index=True)
    symbol: Mapped[str] = mapped_column(String(24), default="", index=True)
    session_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="", index=True)
    pattern_key: Mapped[str] = mapped_column(String(160), default="", index=True)
    entry_variant_id: Mapped[str] = mapped_column(String(120), default="")
    window_start: Mapped[str] = mapped_column(String(80), default="")
    window_end: Mapped[str] = mapped_column(String(80), default="", index=True)
    work_fingerprint: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    data_manifest_hash: Mapped[str] = mapped_column(String(80), default="")
    params_hash: Mapped[str] = mapped_column(String(80), default="")
    split_id: Mapped[str] = mapped_column(String(80), default="")
    priority: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    lease_owner: Mapped[str] = mapped_column(String(120), default="", index=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    result_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    reason_codes_json: Mapped[list[str]] = mapped_column(json_type(), default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class IntradayWorkerHeartbeat(Base):
    __tablename__ = "intraday_worker_heartbeats"
    __table_args__ = (
        Index("ix_intraday_worker_heartbeats_scope_lane_status", "scope", "lane", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    worker_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    scope: Mapped[str] = mapped_column(String(24), default="", index=True)
    lane: Mapped[str] = mapped_column(String(48), default="", index=True)
    status: Mapped[str] = mapped_column(String(40), default="online", index=True)
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)


class EquityPoint(Base):
    __tablename__ = "equity_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    equity: Mapped[float] = mapped_column(Float)
    cash: Mapped[float] = mapped_column(Float)
    open_risk: Mapped[float] = mapped_column(Float, default=0.0)


class PatternMetric(Base):
    __tablename__ = "pattern_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern: Mapped[str] = mapped_column(String(80), index=True)
    strategy_version: Mapped[str] = mapped_column(String(80), default="cup_v0")
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    expectancy_r: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown_pct: Mapped[float] = mapped_column(Float, default=0.0)
    avg_r_multiple: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    state: Mapped[str] = mapped_column(String(40), default="lab")
    parent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    params_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(80), default="system")
    entity_id: Mapped[str] = mapped_column(String(80), default="")
    details_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)


class SystemControl(Base):
    """Runtime operational controls that must survive process restarts.

    The env-based kill switch (TRADEO_KILL_SWITCH_ENABLED) is immutable at
    runtime because Settings are cached at startup. Automatic safety triggers
    (broker reconciliation divergence) persist their state here so every order
    path can honour it immediately, without editing .env and restarting.
    """

    __tablename__ = "system_controls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(80), default="")
    details_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RiskLedger(Base):
    __tablename__ = "risk_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[str] = mapped_column(String(12), index=True)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    open_risk: Mapped[float] = mapped_column(Float, default=0.0)
    halted: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentMessageSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    BLOCKING = "blocking"


class AgentMessage(Base):
    """Versioned, idempotent message bus row for bridge agents (informe §5).

    Bridge agents never call each other directly: they publish evidence here
    and consumers poll/mark consumption. Rows are immutable once written
    except for ``consumed_by``. Promotion state is never written through this
    table — only evidence and blocks.
    """

    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    agent: Mapped[str] = mapped_column(String(80), index=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    produced_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    input_refs: Mapped[list[str]] = mapped_column(json_type(), default=list)
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    severity: Mapped[AgentMessageSeverity] = mapped_column(
        SAEnum(AgentMessageSeverity), default=AgentMessageSeverity.INFO, index=True
    )
    consumed_by: Mapped[list[str]] = mapped_column(json_type(), default=list)
    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)


class DiscoveredPatternStatus(str, Enum):
    LAB = "lab"
    LAB_WATCHLIST = "lab_watchlist"
    LAB_CANDIDATE = "lab_candidate"
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFIRMED_CANDIDATE = "confirmed_candidate"
    FAILED_CONFIRMATION = "failed_confirmation"
    DIRECTOR_REVIEW = "director_review"
    PREMIUM_CANDIDATE = "premium_candidate"
    PAPER_CANDIDATE = "paper_candidate"
    PRODUCTION = "production"
    REJECTED = "rejected"


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="running", index=True)
    symbols_scanned: Mapped[int] = mapped_column(Integer, default=0)
    windows_sampled: Mapped[int] = mapped_column(Integer, default=0)
    clusters_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    accepted_patterns: Mapped[int] = mapped_column(Integer, default=0)
    rejected_patterns: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    params_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    summary_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    report_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    patterns: Mapped[list["DiscoveredPattern"]] = relationship(back_populates="run")


class ResearchAnalyzedWindow(Base):
    __tablename__ = "research_analyzed_windows"
    __table_args__ = (
        Index(
            "ix_research_analyzed_windows_universe_symbol_timeframe",
            "universe_key",
            "symbol",
            "timeframe",
        ),
        Index("ix_research_analyzed_windows_window_end", "window_end"),
        Index("ix_research_analyzed_windows_run_id", "run_id"),
        Index("ix_research_analyzed_windows_universe_key", "universe_key"),
        Index("ix_research_analyzed_windows_source_artifact", "source_artifact_path"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_runs.id"), nullable=True)
    cadence: Mapped[str] = mapped_column(String(24), default="", index=True)
    universe_key: Mapped[str] = mapped_column(String(160), default="")
    universe_scope: Mapped[str] = mapped_column(String(80), default="", index=True)
    universe_file: Mapped[str] = mapped_column(String(500), default="")
    universe_hash: Mapped[str] = mapped_column(String(80), default="")
    symbol: Mapped[str] = mapped_column(String(24), default="")
    timeframe: Mapped[str] = mapped_column(String(16), default="")
    window_start: Mapped[str] = mapped_column(String(80), default="")
    window_end: Mapped[str] = mapped_column(String(80), default="")
    window_size: Mapped[int] = mapped_column(Integer, default=0)
    forward_end: Mapped[str] = mapped_column(String(80), default="")
    data_period: Mapped[str] = mapped_column(String(40), default="")
    data_manifest_hash: Mapped[str] = mapped_column(String(80), default="")
    data_artifact_path: Mapped[str] = mapped_column(String(500), default="")
    data_artifact_sha256: Mapped[str] = mapped_column(String(80), default="")
    data_rows: Mapped[int] = mapped_column(Integer, default=0)
    source_kind: Mapped[str] = mapped_column(String(40), default="sampler", index=True)
    source_artifact_path: Mapped[str] = mapped_column(String(500), default="")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ResearchExperimentRegistryExperiment(Base):
    __tablename__ = "research_experiment_registry_experiments"
    __table_args__ = (
        Index("ix_research_registry_experiments_family", "family_id"),
        Index("ix_research_registry_experiments_pattern", "pattern_key"),
        Index("ix_research_registry_experiments_latest_run", "latest_run_id"),
        Index(
            "ix_research_registry_experiments_side_timeframe",
            "side",
            "timeframe",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String(500), unique=True)
    family_id: Mapped[str] = mapped_column(String(160), default="")
    pattern_key: Mapped[str] = mapped_column(String(160), default="")
    variant_id: Mapped[str] = mapped_column(String(160), default="")
    side: Mapped[str] = mapped_column(String(8), default="")
    timeframe: Mapped[str] = mapped_column(String(16), default="")
    window_size: Mapped[int] = mapped_column(Integer, default=0)
    first_run_id: Mapped[str] = mapped_column(String(80), default="")
    latest_run_id: Mapped[str] = mapped_column(String(80), default="")
    replication_count: Mapped[int] = mapped_column(Integer, default=1)
    candidate_trial_count: Mapped[int] = mapped_column(Integer, default=1)
    global_trial_count_after: Mapped[int] = mapped_column(Integer, default=0)
    edge_claim: Mapped[str] = mapped_column(String(40), default="NO_DEMOSTRADO")
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ResearchExperimentRegistryRun(Base):
    __tablename__ = "research_experiment_registry_runs"
    __table_args__ = (
        Index("ix_research_registry_runs_run_id", "run_id"),
        Index("ix_research_registry_runs_registered_at", "registered_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), unique=True)
    registered_at: Mapped[str] = mapped_column(String(80), default="")
    candidate_count: Mapped[int] = mapped_column(Integer, default=0)
    new_experiments: Mapped[int] = mapped_column(Integer, default=0)
    repeated_experiments: Mapped[int] = mapped_column(Integer, default=0)
    previous_registry_hash: Mapped[str] = mapped_column(String(80), default="")
    run_manifest_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    registry_hash: Mapped[str] = mapped_column(String(80), default="", index=True)
    params_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ResearchExperimentRegistrySnapshot(Base):
    __tablename__ = "research_experiment_registry_snapshots"
    __table_args__ = (
        Index("ix_research_registry_snapshots_created_at", "created_at"),
        Index("ix_research_registry_snapshots_run_manifest_hash", "run_manifest_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registry_hash: Mapped[str] = mapped_column(String(80), unique=True)
    previous_registry_hash: Mapped[str] = mapped_column(String(80), default="")
    run_manifest_hash: Mapped[str] = mapped_column(String(80), default="")
    global_trial_count: Mapped[int] = mapped_column(Integer, default=0)
    experiment_count: Mapped[int] = mapped_column(Integer, default=0)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ResearchArtifactRetention(Base):
    __tablename__ = "research_artifact_retention"
    __table_args__ = (
        Index("ix_research_artifact_retention_kind", "kind"),
        Index("ix_research_artifact_retention_params_hash", "params_hash"),
        Index("ix_research_artifact_retention_path", "path"),
        Index("ix_research_artifact_retention_mtime", "mtime"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_registry: Mapped[str] = mapped_column(String(500), default="")
    path: Mapped[str] = mapped_column(String(500), default="")
    content_hash: Mapped[str] = mapped_column(String(80), default="")
    kind: Mapped[str] = mapped_column(String(80), default="")
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    mtime: Mapped[str] = mapped_column(String(80), default="")
    params_hash: Mapped[str] = mapped_column(String(80), default="")
    parse_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    pattern_count: Mapped[int] = mapped_column(Integer, default=0)
    params_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    patterns_json: Mapped[list[dict[str, Any]]] = mapped_column(json_type(), default=list)
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ResearchDirectorArtifact(Base):
    __tablename__ = "research_director_artifacts"
    __table_args__ = (
        Index("ix_research_director_artifacts_run_id", "run_id"),
        Index("ix_research_director_artifacts_kind", "kind"),
        Index("ix_research_director_artifacts_path", "path"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(80), default="")
    kind: Mapped[str] = mapped_column(String(80), default="")
    path: Mapped[str] = mapped_column(String(500), default="")
    content_hash: Mapped[str] = mapped_column(String(80), default="")
    payload_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    content_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class DiscoveredPattern(Base):
    __tablename__ = "discovered_patterns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("discovery_runs.id"), nullable=True, index=True)
    pattern_key: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    status: Mapped[DiscoveredPatternStatus] = mapped_column(
        SAEnum(DiscoveredPatternStatus), default=DiscoveredPatternStatus.LAB, index=True
    )
    side: Mapped[str] = mapped_column(String(8), default="long")
    timeframe: Mapped[str] = mapped_column(String(16), default="1d")
    window_size: Mapped[int] = mapped_column(Integer, default=50)
    cluster_id: Mapped[int] = mapped_column(Integer, default=0)
    pattern_family_key: Mapped[str] = mapped_column(String(160), default="", index=True)
    canonical_pattern_key: Mapped[str] = mapped_column(String(160), default="", index=True)
    variant_key: Mapped[str] = mapped_column(String(160), default="")
    variant_count: Mapped[int] = mapped_column(Integer, default=1)
    drift_status: Mapped[str] = mapped_column(String(40), default="stable", index=True)
    drift_score: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    symbol_count: Mapped[int] = mapped_column(Integer, default=0)
    year_count: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reward_risk_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    expectancy_r: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_mfe_r: Mapped[float] = mapped_column(Float, default=0.0)
    avg_mae_r: Mapped[float] = mapped_column(Float, default=0.0)
    stability_score: Mapped[float] = mapped_column(Float, default=0.0)
    out_of_sample_expectancy_r: Mapped[float] = mapped_column(Float, default=0.0)
    out_of_sample_profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    best_rr: Mapped[float] = mapped_column(Float, default=0.0)
    best_tested_rr: Mapped[float] = mapped_column(Float, default=0.0)
    best_expectancy_r: Mapped[float] = mapped_column(Float, default=0.0)
    best_profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    best_win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    best_max_drawdown_r: Mapped[float] = mapped_column(Float, default=0.0)
    preferred_rr_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_rr_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    promotion_status: Mapped[str] = mapped_column(String(40), default="rejected", index=True)
    promotion_reason: Mapped[str] = mapped_column(Text, default="")
    confirmation_status: Mapped[str] = mapped_column(String(40), default="", index=True)
    confirmation_priority_score: Mapped[float] = mapped_column(Float, default=0.0)
    confirmation_reason: Mapped[str] = mapped_column(Text, default="")
    confirmation_next_action: Mapped[str] = mapped_column(Text, default="")
    confirmation_attempts: Mapped[int] = mapped_column(Integer, default=0)
    rr_metrics_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    rejection_reasons_json: Mapped[list[str]] = mapped_column(json_type(), default=list)
    in_sample_expectancy_r: Mapped[float] = mapped_column(Float, default=0.0)
    in_sample_profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    out_of_sample_win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    out_of_sample_max_drawdown_r: Mapped[float] = mapped_column(Float, default=0.0)
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_reasons_json: Mapped[list[str]] = mapped_column(json_type(), default=list)
    centroid_json: Mapped[list[float]] = mapped_column(json_type(), default=list)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    feature_summary_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    run: Mapped[DiscoveryRun | None] = relationship(back_populates="patterns")
    examples: Mapped[list["DiscoveredPatternExample"]] = relationship(
        back_populates="pattern", cascade="all, delete-orphan"
    )
    metric_snapshots: Mapped[list["DiscoveredPatternMetric"]] = relationship(
        back_populates="pattern", cascade="all, delete-orphan"
    )


class DiscoveredPatternExample(Base):
    __tablename__ = "discovered_pattern_examples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern_id: Mapped[int] = mapped_column(ForeignKey("discovered_patterns.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="1d")
    window_start: Mapped[str] = mapped_column(String(40), default="")
    window_end: Mapped[str] = mapped_column(String(40), default="")
    forward_end: Mapped[str] = mapped_column(String(40), default="")
    entry_price: Mapped[float] = mapped_column(Float, default=0.0)
    risk_proxy: Mapped[float] = mapped_column(Float, default=0.0)
    outcome_r: Mapped[float] = mapped_column(Float, default=0.0)
    mfe_r: Mapped[float] = mapped_column(Float, default=0.0)
    mae_r: Mapped[float] = mapped_column(Float, default=0.0)
    similarity: Mapped[float] = mapped_column(Float, default=0.0)
    kind: Mapped[str] = mapped_column(String(24), default="typical")
    chart_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    features_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pattern: Mapped[DiscoveredPattern] = relationship(back_populates="examples")


class DiscoveredPatternMetric(Base):
    __tablename__ = "discovered_pattern_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern_id: Mapped[int] = mapped_column(ForeignKey("discovered_patterns.id"), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    split: Mapped[str] = mapped_column(String(32), default="full")
    metrics_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)

    pattern: Mapped[DiscoveredPattern] = relationship(back_populates="metric_snapshots")


class DiscoveredPatternMatch(Base):
    __tablename__ = "discovered_pattern_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern_id: Mapped[int] = mapped_column(ForeignKey("discovered_patterns.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="1d")
    side: Mapped[str] = mapped_column(String(8), default="long")
    similarity: Mapped[float] = mapped_column(Float, default=0.0)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    entry_price: Mapped[float] = mapped_column(Float, default=0.0)
    stop_price: Mapped[float] = mapped_column(Float, default=0.0)
    target_price: Mapped[float] = mapped_column(Float, default=0.0)
    reward_risk: Mapped[float] = mapped_column(Float, default=4.0)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    window_end: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(40), default="lab_watchlist", index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    chart_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)

    pattern: Mapped[DiscoveredPattern] = relationship()
