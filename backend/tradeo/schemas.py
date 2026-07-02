from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from tradeo.research.intraday_vwap_conditions import normalize_vwap_condition_spec


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
    data_quality_skips: int = 0
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
    total_signals: int = 0
    skipped_signals: int = 0
    skip_rate: float = 0.0
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
    vwap_condition: str | None = None
    vwap_side_bias: str | None = None
    vwap_max_distance_bps: float | None = None
    vwap_min_slope_bps: float | None = None

    @field_validator("vwap_condition")
    @classmethod
    def known_vwap_condition(cls, value: str | None) -> str | None:
        normalize_vwap_condition_spec(condition=value)
        return value

    @field_validator("vwap_side_bias")
    @classmethod
    def known_vwap_side_bias(cls, value: str | None) -> str | None:
        if value in (None, ""):
            return value
        if str(value).strip().lower() not in {"long", "short"}:
            raise ValueError("vwap_side_bias must be long, short or empty")
        return value


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
    pattern_family_key: str = ""
    canonical_pattern_key: str = ""
    variant_key: str = ""
    variant_count: int = 1
    drift_status: str = "stable"
    drift_score: float = 0.0
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
    confirmation_status: str = ""
    confirmation_priority_score: float = 0.0
    confirmation_reason: str = ""
    confirmation_next_action: str = ""
    confirmation_attempts: int = 0
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
    max_results: int | None = None
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


class ResearchDirectorResponse(BaseModel):
    generated_at: str
    run_id: int | None = None
    patterns_reviewed: int
    hypotheses_created: int
    memory_graph: dict[str, Any]
    active_learning_agenda: list[dict[str, Any]] = Field(default_factory=list)
    director_state: dict[str, Any]
    artifacts: dict[str, str] = Field(default_factory=dict)


class PatternEntryScanRequest(BaseModel):
    symbols: list[str] | None = None
    limit: int | None = None
    max_patterns: int | None = None
    max_results: int | None = None
    similarity_threshold: float | None = None
    store_signals: bool | None = None
    execute_orders: bool | None = None


class PatternEntryScanResponse(BaseModel):
    module: str
    patterns_checked: int
    symbols_checked: int
    matches_found: int
    entry_variants_considered: int = 0
    signals_created: int
    orders_submitted: int
    skipped_duplicates: int
    skipped_cooldown: int = 0
    rejected_by_entry_gate: int = 0
    rejected_by_entry_quality: int = 0
    rejected_by_ambiguity: int = 0
    rejected_by_risk: int
    rejected_by_production_manifest: int = 0
    production_manifest_rejection_reason_counts: dict[str, int] = Field(default_factory=dict)
    order_errors: list[dict[str, Any]] = Field(default_factory=list)
    order_skip_reason_counts: dict[str, int] = Field(default_factory=dict)
    signal_ids: list[int] = Field(default_factory=list)
    near_miss_signal_ids: list[int] = Field(default_factory=list)
    trade_ids: list[int] = Field(default_factory=list)
    paper_observations_opened: int = 0
    paper_observations_closed: int = 0
    paper_observation_trade_ids: list[int] = Field(default_factory=list)
    near_miss_shadow_observations_opened: int = 0
    near_miss_trade_ids: list[int] = Field(default_factory=list)
    shadow_no_order_observations_opened: int = 0
    shadow_no_order_trade_ids: list[int] = Field(default_factory=list)
    paper_observation_lifecycle: dict[str, Any] = Field(default_factory=dict)
    top_opportunities: list[dict[str, Any]] = Field(default_factory=list)
    requested_execute_orders: bool | None = None
    execution_mode: str | None = None
    execution_degraded_to_shadow: bool = False
    execution_degrade_reason: str | None = None
    store_signals: bool
    execute_orders: bool
    similarity_threshold: float
    scan_duration_ms: float | None = None
    skipped_reason: str | None = None
    market_session: dict[str, Any] | None = None
    generated_at: str


class LabPaperHistoryOut(BaseModel):
    closed_trades: int = 0
    open_trades: int = 0
    total_r: float = 0.0
    expectancy_r: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    unique_symbols: int = 0
    unique_days: int = 0
    variant_closed_trades: int = 0
    regime_closed_trades: int = 0
    last_trade_status: str | None = None


class LabOpportunityDiagnosticOut(BaseModel):
    source: str
    status: str
    symbol: str
    pattern: str
    pattern_id: int | None = None
    side: str = ""
    timeframe: str = ""
    entry_variant_id: str = ""
    entry_variant_label: str = ""
    regime_key: str = ""
    rank: int | None = None
    rank_score: float | None = None
    score: float | None = None
    entry_score: float | None = None
    similarity: float | None = None
    opportunity_rank_components: dict[str, Any] = Field(default_factory=dict)
    entry_gate: dict[str, Any] = Field(default_factory=dict)
    entry_gate_components: list[dict[str, Any]] = Field(default_factory=list)
    entry_quality: dict[str, Any] = Field(default_factory=dict)
    regime_fit: dict[str, Any] = Field(default_factory=dict)
    rejection_stage: str | None = None
    rejection_reason: str = ""
    created_at: str = ""
    window_end: str = ""
    paper_history: LabPaperHistoryOut = Field(default_factory=LabPaperHistoryOut)
    promotion: dict[str, Any] = Field(default_factory=dict)
    missing_to_promote: list[str] = Field(default_factory=list)


class LabDiagnosticsResponse(BaseModel):
    generated_at: str
    summary: dict[str, Any]
    opportunities: list[LabOpportunityDiagnosticOut] = Field(default_factory=list)
