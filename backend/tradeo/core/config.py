from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TradingMode = Literal["research", "paper", "live"]


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

    allow_longs: bool = True
    allow_shorts: bool = True
    allow_options: bool = False
    allow_margin: bool = False

    market_data_provider: str = "ibkr"
    allow_synthetic_market_data: bool = False
    universe_file: str = "/app/data/universe_us_mid_small.csv"
    strategy_config_file: str = "/app/config/strategy_cup_v0.json"
    reports_dir: str = "/app/reports"
    artifacts_dir: str = "/app/artifacts"

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
    discovery_rr_levels: str = "1.5,2.0,2.5,3.0,4.0,5.0"
    discovery_stride: int = 3
    discovery_max_total_windows: int = 12000
    discovery_max_windows_per_symbol: int = 450
    discovery_min_cluster_size: int = 60
    discovery_max_clusters_per_window: int = 12
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
    discovery_min_reward_risk: float = 2.5
    discovery_candidate_reward_risk: float = 3.0
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
    discovery_match_max_results: int = 100
    discovery_registry_similarity_threshold: float = 0.96
    research_director_enabled: bool = True
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

    # Laboratory scans validated Research patterns in paper mode. It may create
    # auditable paper signals continuously, but it never sends IB orders unless
    # explicitly enabled.
    laboratory_scanner_enabled: bool = True
    laboratory_scan_minutes: int = 5
    laboratory_symbol_limit: int = 80
    laboratory_max_patterns: int = 25
    laboratory_similarity_threshold: float = 0.45
    laboratory_store_signals: bool = True
    laboratory_auto_submit_paper_orders: bool = False
    laboratory_market_hours_only: bool = True

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

    openai_api_key: str | None = None
    openai_supervisor_model: str = "gpt-5.5-pro"
    openai_supervisor_enabled: bool = False

    ibkr_host: str = "host.docker.internal"
    ibkr_port: int = 7497
    ibkr_client_id: int = 17
    ibkr_account: str | None = None
    ibkr_readonly: bool = True
    ibkr_connect_timeout_seconds: float = 8.0
    ibkr_order_timeout_seconds: float = 20.0
    ibkr_max_order_value_usd: float = 1500.0
    ibkr_allow_market_orders: bool = False
    ibkr_allowed_symbols: str = ""

    @property
    def ibkr_allowed_symbol_set(self) -> set[str]:
        return {s.strip().upper() for s in self.ibkr_allowed_symbols.split(",") if s.strip()}

    scheduler_enabled: bool = True
    scheduler_scan_minutes: int = 15
    scheduler_report_hour_utc: int = 22

    watchdog_enabled: bool = True
    watchdog_interval_minutes: int = 5
    watchdog_stale_discovery_minutes: int = 30
    watchdog_close_stale_discovery_runs: bool = True

    @field_validator("market_data_provider")
    @classmethod
    def only_ibkr_market_data(cls, value: str) -> str:
        if value.lower() != "ibkr":
            raise ValueError("Tradeo only permits IBKR market data; non-IBKR providers are disabled")
        return "ibkr"

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

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


    @property
    def discovery_window_size_list(self) -> list[int]:
        return [int(x.strip()) for x in self.discovery_window_sizes.split(",") if x.strip()]

    @property
    def discovery_forward_bar_list(self) -> list[int]:
        return [int(x.strip()) for x in self.discovery_forward_bars.split(",") if x.strip()]

    @property
    def discovery_rr_level_list(self) -> list[float]:
        values = sorted({float(x.strip()) for x in self.discovery_rr_levels.split(",") if x.strip()})
        return values or [1.5, 2.0, 2.5, 3.0, 4.0, 5.0]

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
