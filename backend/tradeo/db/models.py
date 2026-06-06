from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
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
    metadata_json: Mapped[dict[str, Any]] = mapped_column(json_type(), default=dict)

    signal: Mapped[Signal | None] = relationship(back_populates="trades")


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


class RiskLedger(Base):
    __tablename__ = "risk_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[str] = mapped_column(String(12), index=True)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    open_risk: Mapped[float] = mapped_column(Float, default=0.0)
    halted: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DiscoveredPatternStatus(str, Enum):
    LAB = "lab"
    LAB_WATCHLIST = "lab_watchlist"
    LAB_CANDIDATE = "lab_candidate"
    PREMIUM_CANDIDATE = "premium_candidate"
    PAPER_CANDIDATE = "paper_candidate"
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
