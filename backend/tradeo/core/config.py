from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TradingMode = Literal["research", "paper", "live"]
TradeoFocusMode = Literal["daily_only", "all"]

SENSITIVE_ENV_KEY_PARTS = (
    "ACCOUNT",
    "API_KEY",
    "CONFIRMATION_VALUE",
    "KEY",
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "USERNAME",
)


def _env_key_for_field(field_name: str) -> str:
    return f"TRADEO_{field_name.upper()}"


def _is_sensitive_env_key(key: str) -> bool:
    upper = key.upper()
    return any(part in upper for part in SENSITIVE_ENV_KEY_PARTS)


def _env_keys_from_file(path: Path) -> set[str]:
    """Return only key names from a dotenv-style file; values are never retained."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    keys: set[str] = set()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if key:
            keys.add(key)
    return keys


class Settings(BaseSettings):
    """Runtime settings for Tradeo.

    The defaults are deliberately conservative: paper mode, no live orders, no options,
    no margin and conservative reward/risk requirements.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TRADEO_", extra="ignore")

    app_name: str = "Tradeo"
    environment: str = "local"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = "postgresql+psycopg://tradeo:tradeo@db:5432/tradeo"
    redis_url: str = "redis://redis:6379/0"

    secret_key: str = "change-me-before-live"
    admin_username: str = "admin"
    admin_password: str = "change-me"

    trading_mode: TradingMode = "paper"
    focus_mode: TradeoFocusMode = "daily_only"
    live_trading_enabled: bool = False
    live_trading_confirmation_phrase: str = "I_ACCEPT_LIVE_MARKET_RISK"
    live_trading_confirmation_value: str = ""
    kill_switch_enabled: bool = False

    initial_capital_usd: float = 3000.0
    risk_per_trade_pct: float = 0.01
    daily_loss_limit_pct: float = 0.02
    monthly_loss_limit_pct: float = 0.08
    max_open_positions: int = 4
    max_gross_exposure_pct: float = 0.95
    min_reward_risk: float = 4.0
    preferred_reward_risk: float = 3.0
    premium_reward_risk: float = 4.0
    max_position_value_pct: float = 0.45
    max_adv_participation_pct: float = 0.005
    max_open_positions_per_pattern_family: int = 2

    allow_longs: bool = True
    allow_shorts: bool = True
    allow_options: bool = False
    allow_margin: bool = False

    market_data_provider: str = "ibkr"
    allow_synthetic_market_data: bool = False
    market_data_cache_enabled: bool = True
    market_data_cache_dir: str = "/app/data/ohlcv_cache"
    market_data_adjusted: bool = True
    market_data_what_to_show: str = "ADJUSTED_LAST"
    # Incremental daily-cache refresh: append only the missing tail after
    # verifying an overlap window against cached bars; any mismatch (e.g.
    # dividend/split re-adjustment) forces an honest full refetch.
    market_data_incremental_enabled: bool = True
    market_data_incremental_overlap_bars: int = 5
    market_data_incremental_min_gap_days: int = 1
    market_data_incremental_max_gap_days: int = 45
    # Intraday cache refresh reuses the same overlap-verified tail append.
    # Gap thresholds are bar-relative (min) and wall-clock (max) because a
    # weekend gap on a 5m cache is normal while a 5-day-old intraday cache
    # is cheaper to refetch in full than to stitch.
    market_data_incremental_intraday_enabled: bool = True
    market_data_incremental_intraday_min_gap_bars: int = 2
    market_data_incremental_intraday_max_gap_days: int = 5
    market_data_upstream_max_concurrency: int = 2
    universe_file: str = "/app/data/universe_us_mid_small.csv"
    daily_universe_file: str = "/app/data/universe_us_mid_small.csv"
    intraday_universe_file: str = "/app/data/universe_us_small_caps.csv"
    intraday_universe_policy: str = "stock_only"
    universe_snapshot_monthly: bool = True
    universe_snapshot_dir: str = "/app/data/universe_snapshots"
    universe_point_in_time_available: bool = False
    # No licensed delisting/PIT membership vendor is wired yet; snapshots stay
    # honest via survivorship flags until this flips with a real data source.
    universe_delisting_data_available: bool = False
    market_regime_benchmark_symbol: str = "SPY"
    market_regime_sma_window: int = 200
    market_regime_vol_window: int = 20
    market_regime_vol_tercile_lookback: int = 252
    # Calibrated regime gate (3.8): minimum research-labeled outcomes in the
    # current benchmark bucket before the calibrated fit replaces heuristics,
    # and whether a calibrated-negative bucket hard-blocks new matches.
    market_regime_outcome_min_samples: int = 12
    market_regime_hard_gate_enabled: bool = False
    survivorship_cap_state: str = "lab_watchlist"
    strategy_config_file: str = "/app/config/strategy_cup_v0.json"
    reports_dir: str = "/app/reports"
    artifacts_dir: str = "/app/artifacts"

    # Intraday lane. Everything is globally disabled by default and remains a
    # no-op unless TRADEO_INTRADAY_ENABLED=true. Live intraday additionally fails
    # closed behind the daily live arm, a real calendar service and EOD flat.
    intraday_enabled: bool = False
    intraday_shadow_enabled: bool = False
    intraday_paper_enabled: bool = False
    intraday_live_enabled: bool = False
    intraday_universe_enabled: bool = False
    intraday_data_sync_enabled: bool = False
    intraday_research_enabled: bool = False
    intraday_research_parallel_timeframes_enabled: bool = False
    intraday_research_parallel_symbol_chunks: int = 1
    intraday_research_process_pool_enabled: bool = False
    intraday_research_process_workers: int = 1
    intraday_research_native_threads_per_process: int = 1
    intraday_research_refresh_market_data_enabled: bool = True
    intraday_candidate_scan_enabled: bool = False
    intraday_observation_closer_enabled: bool = False
    intraday_risk_heartbeat_enabled: bool = True
    intraday_reconciliation_enabled: bool = True
    intraday_eod_flat_enabled: bool = True
    intraday_calendar_enabled: bool = False
    intraday_timeframes: str = "15m,5m"
    intraday_execution_timeframe: str = "1m"
    intraday_session_timezone: str = "America/New_York"
    intraday_no_new_entries_at: str = "15:30"
    intraday_cancel_entries_at: str = "15:45"
    intraday_force_flat_start_at: str = "15:50"
    intraday_hard_flat_deadline_at: str = "15:55"
    intraday_min_price: float = 3.0
    intraday_min_dollar_volume: float = 1_000_000.0
    intraday_max_spread_bps: float = 50.0
    intraday_min_relative_volume: float = 1.5
    intraday_risk_per_trade_pct: float = 0.0025
    intraday_daily_loss_limit_pct: float = 0.005
    intraday_max_open_positions: int = 0
    intraday_max_trades_per_day: int = 0
    intraday_max_trades_per_symbol: int = 0
    intraday_min_reward_risk: float = 4.0
    intraday_pacing_budget_per_10min: int = 0
    intraday_data_sync_interval_seconds: int = 300
    intraday_research_interval_seconds: int = 900
    intraday_research_period: str = "30d"
    intraday_research_limit_default: int = 25
    intraday_research_window_sizes: str = "20,50,100"
    intraday_research_forward_bars: str = "3,6,12"
    intraday_research_stride: int = 1
    intraday_research_max_total_windows: int = 8000
    intraday_research_max_windows_per_symbol: int = 300
    intraday_research_skip_completed_equivalent_runs: bool = False
    intraday_research_min_cluster_size: int = 40
    intraday_research_max_clusters_per_window: int = 8
    intraday_research_min_samples: int = 50
    intraday_research_min_effective_samples: float = 10.0
    intraday_research_min_symbols: int = 6
    intraday_research_min_years: int = 1
    intraday_candidate_scan_interval_seconds: int = 60
    intraday_observation_closer_interval_seconds: int = 60
    intraday_risk_heartbeat_interval_seconds: int = 60
    intraday_reconciliation_interval_seconds: int = 300
    intraday_job_jitter_seconds: int = 10
    intraday_universe_premarket_hour_utc: int = 12
    intraday_universe_premarket_minute_utc: int = 45
    intraday_universe_early_hour_utc: int = 14
    intraday_universe_early_minute_utc: int = 45
    intraday_eod_flat_hour_utc: int = 20
    intraday_eod_flat_minute_utc: int = 55
    intraday_eod_emergency_market_allowed: bool = False

    scan_period: str = "2y"
    scan_interval: str = "1d"
    scan_limit_default: int = 50
    min_avg_dollar_volume: float = 5_000_000.0
    min_price: float = 2.0
    max_atr_pct: float = 0.14

    # Per-symbol OHLCV quality gate applied before pattern detection. Symbols
    # with halted/illiquid bars, frozen feeds, unadjusted splits or calendar
    # holes are skipped and recorded in AuditLog instead of being sampled.
    data_quality_filter_enabled: bool = True
    data_quality_min_bars: int = 60
    data_quality_max_zero_volume_pct: float = 0.15
    data_quality_max_stale_close_run: int = 8
    data_quality_max_single_gap_business_days: int = 5
    data_quality_max_bar_return_ratio: float = 4.0

    # Novel pattern discovery laboratory. This never routes orders; it creates
    # LAB candidates and compact review artifacts for supervisor/API review.
    discovery_enabled: bool = True
    discovery_scheduler_enabled: bool = True
    # >= 1440 means "one run per completed daily bar": the worker switches from an
    # interval to a post-close cron trigger. Intraday reruns over the same daily
    # bar only inflate N_trials without adding information (P0-8).
    discovery_scan_minutes: int = 1440
    discovery_post_close_hour_utc: int = 22
    discovery_post_close_minute_utc: int = 15
    discovery_period: str = "5y"
    discovery_interval: str = "1d"
    discovery_limit_default: int = 80
    discovery_window_sizes: str = "20,50,100,200"
    discovery_forward_bars: str = "5,10,20"
    discovery_rr_levels: str = "2.5,4.0"
    discovery_stride: int = 3
    discovery_max_total_windows: int = 12000
    discovery_max_windows_per_symbol: int = 450
    discovery_min_cluster_size: int = 60
    discovery_max_clusters_per_window: int = 12
    discovery_clusterer_method: str = "auto"
    discovery_clusterer_min_samples: int = 0
    discovery_cluster_consensus_repeats: int = 8
    discovery_cluster_consensus_subsample_pct: float = 0.80
    discovery_min_samples: int = 100
    # Gate over the effective sample size (sum of average-uniqueness weights of
    # deduplicated occurrences). Raw overlapping windows overstate evidence by
    # 4-10x (P0-1); n_eff is what the statistics actually see.
    discovery_min_effective_samples: float = 60.0
    # Run-level Benjamini-Hochberg FDR over the permutation p-values of every
    # cluster evaluated in the run, accepted and rejected alike (P0-2).
    discovery_fdr_q: float = 0.05
    # Family-deflated Sharpe gate for lab_candidate. Uses N_trials accumulated in
    # the global experiment registry so mining more makes the bar rise.
    discovery_min_dsr: float = 0.95
    discovery_min_symbols: int = 8
    discovery_min_years: int = 2
    discovery_min_reward_risk: float = 4.0
    discovery_candidate_reward_risk: float = 4.0
    discovery_premium_reward_risk: float = 4.0
    discovery_max_drawdown_r: float = 12.0
    unvalidated_pattern_min_reward_risk: float = 4.0
    discovery_min_profit_factor: float = 1.8
    discovery_min_expectancy_r: float = 0.25
    discovery_min_stability_score: float = 0.45
    discovery_max_adjusted_p_value: float = 0.25
    discovery_confirmation_min_samples: int = 50
    discovery_confirmation_min_profit_factor: float = 1.6
    discovery_confirmation_min_expectancy_r: float = 0.20
    discovery_out_of_sample_pct: float = 0.25
    discovery_walk_forward_folds: int = 4
    discovery_walk_forward_embargo_samples: int = 5
    discovery_min_walk_forward_positive_rate: float = 0.50
    discovery_min_expectancy_ci_low: float = 0.0
    discovery_max_overfit_score: float = 0.65
    discovery_cost_stress_multipliers: str = "1.0,2.0,3.0"
    discovery_required_cost_stress_multiplier: float = 2.0
    discovery_store_rejected: bool = True
    discovery_report_top_n: int = 20
    discovery_match_enabled: bool = True
    discovery_match_scan_minutes: int = 30
    discovery_match_symbol_limit: int = 80
    discovery_match_max_patterns: int = 25
    discovery_match_similarity_threshold: float = 0.45
    # Never match against a live (incomplete) daily bar: in-session bars carry
    # partial volume and provisional high/low, which breaks Research<->Lab
    # feature parity (P0-3). The matcher drops today's bar before the close.
    discovery_match_complete_bars_only: bool = True
    # Per-pattern similarity threshold derived from the intra-cluster similarity
    # distribution (tau = this percentile of member distances to the centroid).
    # The global similarity threshold remains as a safety floor only (P0-4).
    discovery_match_per_pattern_threshold: bool = True
    discovery_match_tau_percentile: float = 92.5
    # Temporal weighting of the matcher's scaled window (audit §2.2.a): an
    # exponential ramp gamma^(bars_from_end) per channel block so the trigger
    # end of the window dominates the distance. Stays OFF until the false-match
    # harness (§3.1.5) shows fpr_at_recall improves in purged validation; the
    # research run already publishes both curves per pattern.
    discovery_match_temporal_weighting_enabled: bool = False
    discovery_match_temporal_gamma: float = 0.97
    discovery_match_shape_dtw_enabled: bool = False
    discovery_match_shape_dtw_hard_gate_enabled: bool = False
    discovery_match_shape_dtw_method: str = "dtw"
    discovery_match_shape_dtw_band_pct: float = 0.15
    discovery_match_shape_dtw_threshold_quantile: float = 0.90
    discovery_match_shape_soft_dtw_gamma: float = 0.05
    discovery_match_ambiguity_hard_gate_enabled: bool = True
    discovery_match_ambiguity_ratio_threshold: float = 0.95
    discovery_match_ambiguity_entry_score_margin: float = 0.10
    discovery_match_knn_enabled: bool = True
    # Conformal kNN/Mahalanobis gate (audit §3.1.1-3): when Research persisted a
    # prototype_bank (medoids + diagonal covariance + split-conformal taus), the
    # matcher gates on d_knn <= tau_knn AND d_maha <= tau_maha instead of the
    # tau-percentile similarity. The global similarity threshold stays as floor;
    # patterns without a bank keep the legacy per-pattern threshold.
    discovery_match_conformal_gate_enabled: bool = True
    discovery_match_conformal_alpha: float = 0.10
    discovery_match_prototype_medoids: int = 16
    discovery_match_knn_k: int = 3
    discovery_match_max_results: int = 100
    discovery_registry_similarity_threshold: float = 0.96
    research_director_enabled: bool = True
    research_committee_enabled: bool = True
    research_director_interval_minutes: int = 180
    research_director_pattern_limit: int = 120
    entry_gate_enabled: bool = True
    entry_min_score: float = 0.50
    entry_min_quality_score: float = 0.60
    entry_min_regime_score: float = 0.45
    entry_min_volume_ratio: float = 1.05
    entry_max_extension_atr: float = 2.75
    entry_cooldown_minutes: int = 60
    entry_variant_max_per_pattern_symbol: int = 3
    entry_exploration_rate: float = 0.15
    # Ambiguity with teeth (audit §3.1.4): two patterns nearly tied on the same
    # window means the system does not know what it is seeing. Ambiguous matches
    # must clear entry_min_quality_score + margin ("one level up"); otherwise
    # the scanner abstains and records a near-miss shadow (ambiguous_match).
    # The p_meta >= p* + 0.05 clause activates when the meta-model (§2.4) lands.
    entry_ambiguity_gate_enabled: bool = True
    entry_ambiguity_ratio_threshold: float = 0.95
    entry_ambiguity_quality_margin: float = 0.10

    # Laboratory scans validated Research patterns in paper mode. Paper order
    # submission is disabled by default; enabling it still passes through
    # entry/risk, paper-mode, kill-switch, live-armed and IBKR live-port safety
    # gates.
    laboratory_scanner_enabled: bool = True
    laboratory_scan_minutes: int = 5
    # Laboratory paper validation should observe every Research opportunity by
    # default. Use 0 for no cap; Fox/live keeps separate hard limits below.
    laboratory_symbol_limit: int = 0
    laboratory_max_patterns: int = 0
    laboratory_match_max_results: int = 0
    laboratory_similarity_threshold: float = 0.45
    laboratory_store_signals: bool = True
    laboratory_auto_submit_paper_orders: bool = False
    laboratory_allow_watchlist_paper_orders: bool = False
    laboratory_market_hours_only: bool = True

    # Daily Setup Watchlist is a read-only/metadata layer between rejected and
    # Lab Paper Probe. It never submits orders directly.
    daily_setup_watchlist_enabled: bool = True
    daily_setup_max_age_days: int = 5
    daily_setup_reevaluate_after_close: bool = True
    daily_setup_max_active: int = 100
    daily_setup_allow_paper_on_entry_ready: bool = False
    daily_setup_route_entry_ready_to_lab: bool = True

    # Daily execution lane. This is separate from intraday and laboratory
    # validation: it only scans completed daily-bar patterns that Research has
    # promoted to confirmed/paper/premium candidate states. Disabled by default
    # so a deploy cannot start broker submission without an explicit operator
    # switch.
    daily_paper_execution_enabled: bool = False
    daily_paper_scan_minutes: int = 1440
    daily_paper_post_close_hour_utc: int = 22
    daily_paper_post_close_minute_utc: int = 30
    daily_paper_symbol_limit: int = 0
    daily_paper_max_patterns: int = 0
    daily_paper_match_max_results: int = 0
    daily_paper_similarity_threshold: float = 0.45
    daily_paper_store_signals: bool = True
    daily_paper_auto_submit_orders: bool = False
    daily_paper_market_hours_only: bool = False

    # Fox Hunter scans production patterns. Live order submission requires both
    # this explicit switch and the existing live_armed safety gate.
    fox_hunter_enabled: bool = True
    fox_hunter_scan_minutes: int = 1
    fox_hunter_symbol_limit: int = 80
    fox_hunter_max_patterns: int = 25
    fox_hunter_similarity_threshold: float = 0.50
    fox_hunter_store_signals: bool = True
    fox_hunter_auto_submit_live_orders: bool = False
    fox_hunter_market_hours_only: bool = True

    # Director sequential evaluation (informe §4.7). n=10 closed lab trades is
    # only the review trigger; the decision additionally uses a Bayesian
    # posterior shrunk toward the Research expectancy, an SPRT fast-kill and a
    # KS lab-vs-research distribution check.
    director_sequential_evaluation_enabled: bool = True
    director_posterior_min_probability: float = 0.80
    director_posterior_min_edge_r: float = 0.10
    director_sprt_alpha: float = 0.05
    director_sprt_beta: float = 0.20
    director_min_eff_trades: int = 25
    director_min_symbols: int = 8
    director_min_days: int = 10
    # Implementation shortfall gate (informe §4.6): median slippage_R over real
    # broker fills must stay below this for the pattern's edge to count as
    # executable.
    director_max_median_slippage_r: float = 0.10
    director_min_slippage_samples: int = 5

    # DB <-> IBKR reconciliation (informe §4.5). Confirmed divergence between
    # open trades in the DB and broker positions/open orders activates the
    # runtime kill switch automatically. Broker connection failures never do.
    reconciliation_enabled: bool = True
    reconciliation_interval_minutes: int = 30
    reconciliation_auto_kill_switch: bool = True
    reconciliation_auto_repair_paper_exits: bool = False
    live_readiness_worker_max_age_seconds: int = 90
    live_readiness_reconciliation_max_age_seconds: int = 3900

    # Pattern health monitor (informe §4.8): CUSUM over realized R per trade
    # vs the Research expectancy for PRODUCTION/DIRECTOR_REVIEW patterns. A
    # downward trigger marks the pattern drift_status='decaying' and the
    # matcher stops generating new signals for it until re-validation.
    health_monitor_enabled: bool = True
    health_monitor_interval_minutes: int = 60
    health_monitor_min_trades: int = 8
    health_monitor_cusum_k: float = 0.5
    health_monitor_cusum_h: float = 4.0
    health_monitor_shortfall_cusum_k: float = 0.025
    health_monitor_shortfall_cusum_h: float = 0.20
    health_monitor_block_decaying: bool = True

    openai_api_key: str | None = None
    openai_supervisor_model: str = "gpt-5.5-pro"
    openai_supervisor_enabled: bool = False

    ibkr_host: str = "host.docker.internal"
    ibkr_port: int = 7497
    ibkr_client_id: int = 17
    ibkr_account: str | None = None
    ibkr_blocked_accounts: str = ""
    ibkr_readonly: bool = True
    ibkr_connect_timeout_seconds: float = 8.0
    ibkr_order_timeout_seconds: float = 20.0
    ibkr_max_order_value_usd: float = 1500.0
    ibkr_paper_bracket_max_distance_pct: float = 0.20
    ibkr_allow_market_orders: bool = False
    ibkr_allowed_symbols: str = ""
    ibkr_whatif_timeout_seconds: float = 8.0
    ibkr_execution_preflight_quote_timeout_seconds: float = 4.0
    ibkr_execution_preflight_quote_max_age_seconds: float = 5.0
    ibkr_execution_preflight_max_spread_pct: float = 0.005
    ibkr_execution_preflight_max_spread_cost_r: float = 0.05
    ibkr_execution_preflight_max_entry_slippage_pct: float = 0.0025
    ibkr_execution_preflight_max_entry_slippage_r: float = 0.10
    ibkr_execution_preflight_min_bid_size: float = 100.0
    ibkr_execution_preflight_min_ask_size: float = 100.0
    ibkr_execution_preflight_min_top_of_book_notional_usd: float = 1000.0
    ibkr_execution_preflight_whatif_enabled: bool = True
    ibkr_execution_preflight_max_commission_usd: float = 5.0
    ibkr_execution_preflight_max_commission_r: float = 0.05

    # Per-signal quote snapshot (informe §3.3.1): capture real bid/ask/last at
    # signal time so spread becomes a datum, not a proxy. Fail-soft: a failed
    # snapshot never blocks the signal, only records itself as unavailable.
    signal_spread_snapshot_enabled: bool = True
    signal_spread_snapshot_timeout_seconds: float = 4.0

    @property
    def ibkr_allowed_symbol_set(self) -> set[str]:
        return {s.strip().upper() for s in self.ibkr_allowed_symbols.split(",") if s.strip()}

    @property
    def ibkr_blocked_account_set(self) -> set[str]:
        return {s.strip().upper() for s in self.ibkr_blocked_accounts.split(",") if s.strip()}

    scheduler_enabled: bool = True
    scheduler_scan_minutes: int = 15
    scheduler_report_hour_utc: int = 22

    watchdog_enabled: bool = True
    watchdog_interval_minutes: int = 5
    watchdog_stale_discovery_minutes: int = 30
    watchdog_close_stale_discovery_runs: bool = True
    ops_alerting_enabled: bool = True
    false_match_metrics_job_enabled: bool = True
    false_match_metrics_hour_utc: int = 23
    false_match_metrics_minute_utc: int = 45
    false_match_metrics_high_fpr_threshold: float = 0.25

    self_improvement_max_trials: int = 80
    self_improvement_sampling_seed: int = 20260611
    self_improvement_max_pbo: float = 0.10
    self_improvement_min_pbo_blocks: int = 16
    self_improvement_plateau_pf_fraction: float = 0.80
    # Wave4-D nested optimization (fail-closed: disabling it blocks acceptance).
    self_improvement_nested_enabled: bool = True
    self_improvement_nested_outer_folds: int = 5
    self_improvement_nested_inner_trials: int = 64
    self_improvement_nested_max_pbo: float = 0.10
    self_improvement_nested_seed: int = 17
    self_improvement_nested_use_optuna: bool = True

    @field_validator("market_data_provider")
    @classmethod
    def only_ibkr_market_data(cls, value: str) -> str:
        if value.lower() != "ibkr":
            raise ValueError("Tradeo only permits IBKR market data; non-IBKR providers are disabled")
        return "ibkr"

    @field_validator("focus_mode", mode="before")
    @classmethod
    def known_focus_mode(cls, value: str) -> str:
        mode = str(value or "daily_only").strip().lower().replace("-", "_")
        aliases = {
            "daily": "daily_only",
            "daily_only": "daily_only",
            "all": "all",
            "full": "all",
            "unrestricted": "all",
        }
        if mode not in aliases:
            raise ValueError("focus_mode must be daily_only or all")
        return aliases[mode]

    @field_validator("allow_synthetic_market_data")
    @classmethod
    def synthetic_market_data_disabled(cls, value: bool) -> bool:
        if value:
            raise ValueError("Synthetic market data is forbidden")
        return False

    @field_validator("risk_per_trade_pct", "daily_loss_limit_pct", "monthly_loss_limit_pct")
    @classmethod
    def pct_bounds(cls, value: float) -> float:
        if value <= 0 or value > 0.5:
            raise ValueError("risk percentages must be between 0 and 0.5")
        return value

    @field_validator("intraday_timeframes")
    @classmethod
    def intraday_timeframes_must_be_explicit(cls, value: str) -> str:
        timeframes = [item.strip() for item in value.split(",") if item.strip()]
        if not timeframes:
            raise ValueError("intraday_timeframes must include at least one explicit timeframe")
        return ",".join(timeframes)

    @field_validator("intraday_risk_per_trade_pct", "intraday_daily_loss_limit_pct")
    @classmethod
    def intraday_pct_bounds(cls, value: float) -> float:
        if value < 0 or value > 0.5:
            raise ValueError("intraday risk percentages must be between 0 and 0.5")
        return value

    @field_validator(
        "intraday_min_price",
        "intraday_min_dollar_volume",
        "intraday_max_spread_bps",
        "intraday_min_relative_volume",
        "intraday_min_reward_risk",
        "intraday_research_min_effective_samples",
    )
    @classmethod
    def non_negative_intraday_thresholds(cls, value: float) -> float:
        if value < 0:
            raise ValueError("intraday thresholds must be non-negative")
        return value

    @field_validator(
        "intraday_max_open_positions",
        "intraday_max_trades_per_day",
        "intraday_max_trades_per_symbol",
        "intraday_pacing_budget_per_10min",
        "intraday_data_sync_interval_seconds",
        "intraday_research_interval_seconds",
        "intraday_research_process_workers",
        "intraday_research_native_threads_per_process",
        "intraday_research_limit_default",
        "intraday_research_stride",
        "intraday_research_max_total_windows",
        "intraday_research_max_windows_per_symbol",
        "intraday_research_min_cluster_size",
        "intraday_research_max_clusters_per_window",
        "intraday_research_min_samples",
        "intraday_research_min_symbols",
        "intraday_research_min_years",
        "intraday_candidate_scan_interval_seconds",
        "intraday_observation_closer_interval_seconds",
        "intraday_risk_heartbeat_interval_seconds",
        "intraday_reconciliation_interval_seconds",
        "intraday_job_jitter_seconds",
        "intraday_universe_premarket_hour_utc",
        "intraday_universe_premarket_minute_utc",
        "intraday_universe_early_hour_utc",
        "intraday_universe_early_minute_utc",
        "intraday_eod_flat_hour_utc",
        "intraday_eod_flat_minute_utc",
        "daily_setup_max_age_days",
        "daily_setup_max_active",
    )
    @classmethod
    def non_negative_intraday_ints(cls, value: int) -> int:
        if value < 0:
            raise ValueError("intraday integer settings must be non-negative")
        return value

    @field_validator("intraday_universe_policy")
    @classmethod
    def known_intraday_universe_policy(cls, value: str) -> str:
        policy = str(value or "stock_only").strip().lower()
        if policy not in {"stock_only", "etf_macro"}:
            raise ValueError("intraday universe policy must be stock_only or etf_macro")
        return policy

    @model_validator(mode="after")
    def intraday_live_fails_closed(self) -> "Settings":
        blockers = self.intraday_live_config_blockers
        if self.intraday_live_enabled and blockers:
            raise ValueError(
                "intraday live is blocked by config: " + ",".join(sorted(blockers))
            )
        return self

    @field_validator(
        "ibkr_execution_preflight_quote_timeout_seconds",
        "ibkr_execution_preflight_quote_max_age_seconds",
        "ibkr_whatif_timeout_seconds",
        "ibkr_execution_preflight_max_spread_pct",
        "ibkr_execution_preflight_max_spread_cost_r",
        "ibkr_execution_preflight_max_entry_slippage_pct",
        "ibkr_execution_preflight_max_entry_slippage_r",
        "ibkr_execution_preflight_min_bid_size",
        "ibkr_execution_preflight_min_ask_size",
        "ibkr_execution_preflight_min_top_of_book_notional_usd",
        "ibkr_execution_preflight_max_commission_usd",
        "ibkr_execution_preflight_max_commission_r",
    )
    @classmethod
    def non_negative_execution_preflight_threshold(cls, value: float) -> float:
        if value < 0:
            raise ValueError("IBKR execution preflight thresholds must be non-negative")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def intraday_timeframe_list(self) -> list[str]:
        return [timeframe.strip() for timeframe in self.intraday_timeframes.split(",") if timeframe.strip()]

    @property
    def intraday_research_window_size_list(self) -> list[int]:
        return [int(x.strip()) for x in self.intraday_research_window_sizes.split(",") if x.strip()]

    @property
    def intraday_research_forward_bar_list(self) -> list[int]:
        return [int(x.strip()) for x in self.intraday_research_forward_bars.split(",") if x.strip()]

    @property
    def intraday_live_config_blockers(self) -> list[str]:
        blockers: list[str] = []
        if not self.intraday_enabled:
            blockers.append("intraday_disabled")
        if not self.live_armed:
            blockers.append("daily_live_not_armed")
        if self.ibkr_readonly:
            blockers.append("ibkr_readonly")
        if not self.intraday_calendar_enabled:
            blockers.append("intraday_calendar_disabled")
        if not self.intraday_eod_flat_enabled:
            blockers.append("intraday_eod_flat_disabled")
        return blockers

    @property
    def intraday_live_armed(self) -> bool:
        return self.intraday_live_enabled and not self.intraday_live_config_blockers

    @property
    def daily_focus_only(self) -> bool:
        return self.focus_mode == "daily_only"

    def redacted_config_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        for field_name in sorted(type(self).model_fields):
            env_key = _env_key_for_field(field_name)
            value = getattr(self, field_name)
            if _is_sensitive_env_key(env_key):
                snapshot[env_key] = "<redacted>" if value not in (None, "") else ""
            elif isinstance(value, Path):
                snapshot[env_key] = str(value)
            else:
                snapshot[env_key] = value
        return snapshot

    def config_doctor(
        self,
        *,
        env_path: str | Path = ".env",
        example_path: str | Path = ".env.example",
    ) -> dict[str, Any]:
        env_file = Path(env_path)
        example_file = Path(example_path)
        env_keys = _env_keys_from_file(env_file)
        example_keys = _env_keys_from_file(example_file)
        documented_intraday_keys = {
            _env_key_for_field(name)
            for name in type(self).model_fields
            if name.startswith("intraday_")
        }
        missing_from_env = sorted(example_keys - env_keys) if env_file.exists() else []
        undocumented_env_keys = sorted(
            key for key in (env_keys - example_keys) if key.startswith("TRADEO_")
        )
        missing_intraday_example_keys = sorted(documented_intraday_keys - example_keys)
        critical_defaults = self._critical_default_warnings()
        blockers = {
            "intraday_live": self.intraday_live_config_blockers,
            "intraday_paper": self._intraday_paper_blockers(),
        }
        has_warnings = bool(
            undocumented_env_keys
            or missing_intraday_example_keys
            or critical_defaults
            or blockers["intraday_live"]
        )
        return {
            "ok": not has_warnings,
            "status": "warning" if has_warnings else "ok",
            "redacted": True,
            "env": {
                "env_file_present": env_file.exists(),
                "example_file_present": example_file.exists(),
                "missing_keys_count": len(missing_from_env),
                "missing_keys": missing_from_env,
                "undocumented_tradeo_keys": undocumented_env_keys,
            },
            "intraday": {
                "enabled": self.intraday_enabled,
                "shadow_enabled": self.intraday_shadow_enabled,
                "paper_enabled": self.intraday_paper_enabled,
                "live_enabled": self.intraday_live_enabled,
                "live_armed": self.intraday_live_armed,
                "timeframes": self.intraday_timeframe_list,
                "missing_example_keys": missing_intraday_example_keys,
                "blockers": blockers,
            },
            "critical_defaults": critical_defaults,
            "secret_values_exposed": False,
        }

    def _critical_default_warnings(self) -> list[dict[str, str]]:
        warnings: list[dict[str, str]] = []
        defaults = type(self).model_fields
        for field_name, reason in (
            ("secret_key", "default_secret_key"),
            ("admin_password", "default_admin_password"),
        ):
            if getattr(self, field_name) == defaults[field_name].default:
                warnings.append({"key": _env_key_for_field(field_name), "reason": reason})
        if self.intraday_enabled and self.intraday_pacing_budget_per_10min <= 0:
            warnings.append(
                {
                    "key": "TRADEO_INTRADAY_PACING_BUDGET_PER_10MIN",
                    "reason": "intraday_pacing_budget_blocks_data_jobs",
                }
            )
        return warnings

    def _intraday_paper_blockers(self) -> list[str]:
        blockers: list[str] = []
        if self.intraday_paper_enabled and not self.intraday_enabled:
            blockers.append("intraday_disabled")
        if self.intraday_paper_enabled and not self.intraday_eod_flat_enabled:
            blockers.append("intraday_eod_flat_disabled")
        return blockers

    @property
    def discovery_window_size_list(self) -> list[int]:
        return [int(x.strip()) for x in self.discovery_window_sizes.split(",") if x.strip()]

    @property
    def discovery_forward_bar_list(self) -> list[int]:
        return [int(x.strip()) for x in self.discovery_forward_bars.split(",") if x.strip()]

    @property
    def discovery_rr_level_list(self) -> list[float]:
        values = sorted({float(x.strip()) for x in self.discovery_rr_levels.split(",") if x.strip()})
        return values or [2.5, 4.0]

    @property
    def discovery_cost_stress_multiplier_list(self) -> list[float]:
        values = sorted({float(x.strip()) for x in self.discovery_cost_stress_multipliers.split(",") if x.strip()})
        return values or [1.0, 2.0, 3.0]

    @property
    def reports_path(self) -> Path:
        path = Path(self.reports_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def artifacts_path(self) -> Path:
        path = Path(self.artifacts_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def market_data_cache_path(self) -> Path:
        return self._writable_path(self.market_data_cache_dir, "ohlcv_cache")

    @property
    def universe_snapshot_path(self) -> Path:
        return self._writable_path(self.universe_snapshot_dir, "universe_snapshots")

    @property
    def account_risk_usd(self) -> float:
        return round(self.initial_capital_usd * self.risk_per_trade_pct, 2)

    @property
    def live_armed(self) -> bool:
        return (
            self.trading_mode == "live"
            and self.live_trading_enabled
            and self.live_trading_confirmation_value == self.live_trading_confirmation_phrase
            and not self.kill_switch_enabled
        )

    def _writable_path(self, raw_path: str, fallback_name: str) -> Path:
        path = Path(raw_path)
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            fallback = Path(self.artifacts_dir) / "runtime" / fallback_name
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback


@lru_cache
def get_settings() -> Settings:
    return Settings()
