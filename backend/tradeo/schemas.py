from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PatternFeatures(BaseModel):
    cup_depth: float = 0.0
    cup_length: int = 0
    rim_symmetry: float = 0.0
    bottom_smoothness: float = 0.0
    handle_depth: float = 0.0
    volume_dryup: float = 0.0
    breakout_volume_ratio: float = 0.0
    atr_pct: float = 0.0
    trend_score: float = 0.0
    avg_dollar_volume: float = 0.0


class PatternCandidate(BaseModel):
    symbol: str
    pattern: str = "mid_small_cap_cup_breakout"
    side: Literal["long", "short"] = "long"
    timeframe: str = "1d"
    entry: float
    stop: float
    target: float
    reward_risk: float
    confidence: float
    rule_score: float
    ml_score: float
    vision_score: float
    composite_score: float
    features: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class RiskDecision(BaseModel):
    approved: bool
    suggested_qty: int = 0
    risk_usd: float = 0.0
    notional_usd: float = 0.0
    reason: str = ""
    hard_rejections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SupervisorDecision(BaseModel):
    approved_for_paper: bool
    eligible_for_live_review: bool
    status: str
    confidence: float
    notes: str
    risk: RiskDecision
    candidate: PatternCandidate


class SignalOut(BaseModel):
    id: int
    symbol: str
    pattern: str
    side: str
    timeframe: str
    entry: float
    stop: float
    target: float
    reward_risk: float
    confidence: float
    composite_score: float
    risk_usd: float
    suggested_qty: int
    strategy_version: str
    status: str
    supervisor_notes: str
    human_approved: bool
    created_at: datetime
    metadata_json: dict[str, Any]

    model_config = {"from_attributes": True}


class TradeOut(BaseModel):
    id: int
    symbol: str
    pattern: str
    side: str
    qty: int
    entry: float
    stop: float
    target: float
    status: str
    opened_at: datetime
    closed_at: datetime | None
    exit_price: float | None
    pnl_usd: float
    r_multiple: float

    model_config = {"from_attributes": True}


class EquityPointOut(BaseModel):
    timestamp: datetime
    equity: float
    cash: float
    open_risk: float

    model_config = {"from_attributes": True}


class PatternMetricOut(BaseModel):
    pattern: str
    strategy_version: str
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    max_drawdown_pct: float
    avg_r_multiple: float

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    mode: str
    live_armed: bool
    kill_switch_enabled: bool
    initial_capital_usd: float
    risk_per_trade_usd: float
    min_reward_risk: float
    equity: list[EquityPointOut]
    pattern_metrics: list[PatternMetricOut]
    recent_signals: list[SignalOut]
    open_trades: list[TradeOut]
    supervisor_state: dict[str, Any]


class ScanRequest(BaseModel):
    limit: int | None = None
    period: str | None = None
    interval: str | None = None
    force_symbols: list[str] | None = None


class ScanResponse(BaseModel):
    scanned: int
    candidates: int
    stored_signals: int
    rejected: int
    data_errors: int = 0
    decisions: list[SupervisorDecision]


class BacktestRequest(BaseModel):
    symbols: list[str] | None = None
    period: str = "3y"
    interval: str = "1d"
    max_symbols: int = 30


class BacktestMetrics(BaseModel):
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    avg_r_multiple: float
    max_drawdown_pct: float
    trades: list[dict[str, Any]] = Field(default_factory=list)


class KillSwitchRequest(BaseModel):
    enabled: bool
    reason: str = "manual"


class SelfImprovementResponse(BaseModel):
    generated: int
    accepted_lab_candidates: int
    best_candidate: dict[str, Any] | None = None
    report_path: str | None = None


class DiscoveryRunRequest(BaseModel):
    limit: int | None = None
    symbols: list[str] | None = None
    period: str | None = None
    interval: str | None = None
    window_sizes: list[int] | None = None
    forward_bars: list[int] | None = None
    stride: int | None = None
    max_total_windows: int | None = None
    max_windows_per_symbol: int | None = None
    min_cluster_size: int | None = None
    max_clusters_per_window: int | None = None
    store_rejected: bool | None = None


class DiscoveryRunResponse(BaseModel):
    run_id: int
    status: str
    symbols_scanned: int
    windows_sampled: int
    clusters_evaluated: int
    accepted_patterns: int
    rejected_patterns: int
    stored_patterns: int
    duration_seconds: float
    report_path: str | None = None
    top_patterns: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DiscoveredPatternOut(BaseModel):
    id: int
    pattern_key: str
    name: str
    status: str
    side: str
    timeframe: str
    window_size: int
    cluster_id: int
    sample_count: int
    symbol_count: int
    year_count: int
    score: float
    reward_risk_estimate: float
    expectancy_r: float
    profit_factor: float
    win_rate: float
    avg_mfe_r: float
    avg_mae_r: float
    stability_score: float
    out_of_sample_expectancy_r: float
    out_of_sample_profit_factor: float
    best_rr: float = 0.0
    best_tested_rr: float = 0.0
    best_expectancy_r: float = 0.0
    best_profit_factor: float = 0.0
    best_win_rate: float = 0.0
    best_max_drawdown_r: float = 0.0
    preferred_rr_passed: bool = False
    premium_rr_passed: bool = False
    promotion_status: str = "rejected"
    promotion_reason: str = ""
    rr_metrics_json: dict[str, Any] = Field(default_factory=dict)
    rejection_reasons_json: list[str] = Field(default_factory=list)
    in_sample_expectancy_r: float = 0.0
    in_sample_profit_factor: float = 0.0
    out_of_sample_win_rate: float = 0.0
    out_of_sample_max_drawdown_r: float = 0.0
    validation_passed: bool
    validation_reasons_json: list[str]
    metrics_json: dict[str, Any]
    feature_summary_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoveredPatternExampleOut(BaseModel):
    id: int
    pattern_id: int
    symbol: str
    timeframe: str
    window_start: str
    window_end: str
    forward_end: str
    entry_price: float
    risk_proxy: float
    outcome_r: float
    mfe_r: float
    mae_r: float
    similarity: float
    kind: str
    chart_json: dict[str, Any]
    features_json: dict[str, Any]

    model_config = {"from_attributes": True}


class DiscoveredPatternMetricOut(BaseModel):
    id: int
    pattern_id: int
    as_of: datetime
    split: str
    metrics_json: dict[str, Any]

    model_config = {"from_attributes": True}


class DiscoveredPatternDetailOut(DiscoveredPatternOut):
    examples: list[DiscoveredPatternExampleOut] = Field(default_factory=list)
    metric_snapshots: list[DiscoveredPatternMetricOut] = Field(default_factory=list)


class DiscoveryRunOut(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    symbols_scanned: int
    windows_sampled: int
    clusters_evaluated: int
    accepted_patterns: int
    rejected_patterns: int
    duration_seconds: float
    params_json: dict[str, Any]
    summary_json: dict[str, Any]
    report_path: str | None

    model_config = {"from_attributes": True}


class NovelPatternMatchRequest(BaseModel):
    symbols: list[str] | None = None
    limit: int | None = None
    max_patterns: int | None = None
    similarity_threshold: float | None = None
    module: Literal["laboratory", "fox_hunter"] = "laboratory"
    store: bool = True


class NovelPatternMatchOut(BaseModel):
    id: int
    pattern_id: int
    symbol: str
    timeframe: str
    side: str
    similarity: float
    score: float
    entry_price: float
    stop_price: float
    target_price: float
    reward_risk: float
    matched_at: datetime
    window_end: str
    status: str
    notes: str
    chart_json: dict[str, Any]
    metrics_json: dict[str, Any]

    model_config = {"from_attributes": True}


class NovelPatternMatchResponse(BaseModel):
    patterns_checked: int
    symbols_checked: int
    matches: list[dict[str, Any]] = Field(default_factory=list)
    stored_matches: int
    module: str = "laboratory"
    similarity_threshold: float
    generated_at: str


class PatternEntryScanRequest(BaseModel):
    symbols: list[str] | None = None
    limit: int | None = None
    max_patterns: int | None = None
    similarity_threshold: float | None = None
    store_signals: bool | None = None
    execute_orders: bool | None = None


class PatternEntryScanResponse(BaseModel):
    module: str
    patterns_checked: int
    symbols_checked: int
    matches_found: int
    signals_created: int
    orders_submitted: int
    skipped_duplicates: int
    rejected_by_risk: int
    order_errors: list[dict[str, Any]] = Field(default_factory=list)
    signal_ids: list[int] = Field(default_factory=list)
    trade_ids: list[int] = Field(default_factory=list)
    store_signals: bool
    execute_orders: bool
    similarity_threshold: float
    generated_at: str
