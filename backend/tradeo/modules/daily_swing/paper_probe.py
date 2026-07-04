from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "tradeo.daily_swing.paper_probe.v1"
MONDAY_RUN_DATE = date(2026, 7, 6)
INDEPENDENCE_DAY_OBSERVED_2026 = date(2026, 7, 3)


@dataclass(frozen=True)
class DailySwingConfig:
    mode: str = "paper_probe"
    live_armed: bool = False
    paper_enabled: bool = True
    allow_live_orders: bool = False
    stocks_only: bool = True
    long_only: bool = True
    no_options: bool = True
    no_short: bool = True
    no_margin: bool = True
    no_market_on_open: bool = True
    no_market_on_close: bool = True
    kill_switch_required: bool = True
    max_new_trades_per_day: int = 2
    max_open_positions: int = 5
    max_position_value: float = 1500.0
    max_total_gross_exposure: float = 10000.0
    max_symbol_risk_pct: float = 0.0025
    normalized_equity: float = 25000.0
    entry_window_et: str = "09:35-10:00"
    signal_date: str = "2026-07-02"
    run_date: str = "2026-07-06"
    primary_pattern_id: str = "DSS-PB-001"
    reserve_pattern_id: str = "DSS-BO-001"
    allowed_order_type: str = "LMT"
    min_price: float = 10.0
    min_adv20: int = 1_000_000
    min_dollar_volume20: float = 20_000_000.0


DEFAULT_CONFIG = DailySwingConfig()


@dataclass(frozen=True)
class MarketBar:
    symbol: str
    bar_date: date
    close: float
    sma50: float
    sma200: float
    atr14: float
    rsi2: float
    adv20: int
    dollar_volume20: float
    product_type: str = "STK"
    spy_close: float = 625.0
    spy_sma200: float = 560.0
    spy_return20: float = 0.021


@dataclass(frozen=True)
class SignalCandidate:
    pattern_id: str
    symbol: str
    signal_date: date
    last_valid_bar_date: date
    close: float
    atr14: float
    score: float
    reason: str


@dataclass(frozen=True)
class DailySwingOrder:
    pattern_id: str
    signal_id: str
    symbol: str
    signal_date: str
    last_valid_bar_date: str
    entry_plan: str
    entry_order_type: str
    limit_price: float
    limit_price_logic: str
    stop_price: float
    target_price: float
    time_stop_date: str
    quantity: int
    risk_R: float
    expected_R_distribution: dict[str, float]
    regime_snapshot: dict[str, Any]
    spec_hash: str = field(default="")

    def with_hash(self) -> "DailySwingOrder":
        payload = asdict(self)
        payload.pop("spec_hash", None)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return DailySwingOrder(**{**payload, "spec_hash": digest})


def repo_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists() and (candidate / "docker-compose.yml").exists():
            return candidate
    raise SystemExit("could not locate Tradeo repo root")


def load_config(path: Path | None = None) -> DailySwingConfig:
    if path is None or not path.exists():
        return DEFAULT_CONFIG
    raw: dict[str, Any] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or ":" not in clean:
            continue
        key, value = clean.split(":", 1)
        raw[key.strip()] = _parse_scalar(value.strip())
    known = {field.name for field in DailySwingConfig.__dataclass_fields__.values()}
    return DailySwingConfig(**{**asdict(DEFAULT_CONFIG), **{k: v for k, v in raw.items() if k in known}})


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip("'\"")
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def last_valid_trading_day(run_date: date) -> date:
    candidate = run_date - timedelta(days=1)
    holidays = {INDEPENDENCE_DAY_OBSERVED_2026}
    while candidate.weekday() >= 5 or candidate in holidays:
        candidate -= timedelta(days=1)
    return candidate


def classify_paper_probe_candidate(metrics: dict[str, Any]) -> str:
    if not metrics.get("real_backtest", False):
        return "research_gap"
    if metrics.get("lookahead_findings", 1) or metrics.get("leakage_findings", 1):
        return "rejected"
    if metrics.get("oos_expectancy_net", 0.0) <= 0:
        return "near_miss"
    if metrics.get("cost_x2_expectancy", 0.0) <= 0:
        return "near_miss"
    if metrics.get("symbol_count", 0) < 8:
        return "near_miss"
    if metrics.get("top3_symbol_concentration", 1.0) > 0.55:
        return "near_miss"
    if metrics.get("recent_12m_expectancy", -1.0) < 0:
        return "near_miss"
    return "paper_probe_candidate"


def sample_daily_bars(signal_date: date) -> list[MarketBar]:
    return [
        MarketBar("AAPL", signal_date, 212.4, 205.1, 184.2, 4.8, 12.0, 54_000_000, 11_469_600_000),
        MarketBar("MSFT", signal_date, 498.1, 486.0, 430.4, 8.7, 18.0, 23_000_000, 11_456_300_000),
        MarketBar("NVDA", signal_date, 158.3, 150.9, 125.2, 5.1, 21.0, 180_000_000, 28_494_000_000),
        MarketBar("AVGO", signal_date, 287.2, 276.0, 215.4, 7.9, 24.0, 22_000_000, 6_318_400_000),
        MarketBar("JPM", signal_date, 286.5, 274.8, 241.7, 5.2, 19.0, 9_000_000, 2_578_500_000),
        MarketBar("LLY", signal_date, 812.0, 794.0, 753.2, 18.0, 17.0, 3_200_000, 2_598_400_000),
        MarketBar("COST", signal_date, 992.0, 970.2, 904.5, 16.0, 16.0, 1_800_000, 1_785_600_000),
        MarketBar("META", signal_date, 718.0, 690.0, 610.0, 14.0, 25.0, 12_500_000, 8_975_000_000),
        MarketBar("SPY", signal_date, 625.0, 612.0, 560.0, 6.0, 43.0, 60_000_000, 37_500_000_000, "ETF"),
        MarketBar("TQQQ", signal_date, 95.0, 90.0, 72.0, 3.0, 20.0, 70_000_000, 6_650_000_000, "ETF"),
    ]


def select_pullback_candidates(
    bars: list[MarketBar],
    *,
    config: DailySwingConfig = DEFAULT_CONFIG,
) -> list[SignalCandidate]:
    selected: list[SignalCandidate] = []
    signal_date = date.fromisoformat(config.signal_date)
    expected_last_bar = last_valid_trading_day(date.fromisoformat(config.run_date))
    for bar in bars:
        if bar.bar_date != expected_last_bar:
            continue
        if config.stocks_only and bar.product_type != "STK":
            continue
        if bar.close < config.min_price:
            continue
        if bar.adv20 < config.min_adv20 and bar.dollar_volume20 < config.min_dollar_volume20:
            continue
        if not (bar.spy_close > bar.spy_sma200 or bar.spy_return20 > 0):
            continue
        if not (bar.close > bar.sma50 and (bar.close > bar.sma200 or bar.sma50 > bar.sma200)):
            continue
        if not (bar.rsi2 <= 25):
            continue
        score = round((25 - bar.rsi2) / 25 + (bar.close / bar.sma50 - 1), 4)
        selected.append(
            SignalCandidate(
                pattern_id=config.primary_pattern_id,
                symbol=bar.symbol,
                signal_date=signal_date,
                last_valid_bar_date=expected_last_bar,
                close=bar.close,
                atr14=bar.atr14,
                score=score,
                reason="uptrend + short pullback + positive SPY regime",
            )
        )
    return sorted(selected, key=lambda item: (-item.score, item.symbol))[: config.max_new_trades_per_day]


def build_order(candidate: SignalCandidate, config: DailySwingConfig = DEFAULT_CONFIG) -> DailySwingOrder:
    risk_per_trade = config.normalized_equity * config.max_symbol_risk_pct
    stop_distance = max(round(candidate.atr14 * 1.2, 2), 0.01)
    raw_qty = int(risk_per_trade // stop_distance)
    value_cap_qty = int(config.max_position_value // candidate.close)
    qty = max(1, min(raw_qty, value_cap_qty))
    limit_price = round(candidate.close * 1.002, 2)
    stop_price = round(candidate.close - stop_distance, 2)
    target_price = round(candidate.close + stop_distance * 1.75, 2)
    signal_id_src = f"{candidate.pattern_id}|{candidate.symbol}|{candidate.signal_date.isoformat()}"
    signal_id = hashlib.sha256(signal_id_src.encode("utf-8")).hexdigest()[:16]
    order = DailySwingOrder(
        pattern_id=candidate.pattern_id,
        signal_id=signal_id,
        symbol=candidate.symbol,
        signal_date=candidate.signal_date.isoformat(),
        last_valid_bar_date=candidate.last_valid_bar_date.isoformat(),
        entry_plan=f"paper-only entry during {config.entry_window_et} ET after spread/gap recheck",
        entry_order_type=config.allowed_order_type,
        limit_price=limit_price,
        limit_price_logic="marketable limit capped at previous close * 1.002; never MOO/MOC",
        stop_price=stop_price,
        target_price=target_price,
        time_stop_date=(MONDAY_RUN_DATE + timedelta(days=8)).isoformat(),
        quantity=qty,
        risk_R=1.0,
        expected_R_distribution={"p10": -1.0, "median": 0.35, "p90": 1.75},
        regime_snapshot={"SPY_close_gt_SMA200": True, "SPY_20d_return_positive": True},
    )
    return order.with_hash()


def generate_daily_swing_preview(config: DailySwingConfig = DEFAULT_CONFIG) -> list[DailySwingOrder]:
    signal_date = date.fromisoformat(config.signal_date)
    bars = sample_daily_bars(signal_date)
    candidates = select_pullback_candidates(bars, config=config)
    orders = [build_order(candidate, config) for candidate in candidates]
    if sum(order.quantity * order.limit_price for order in orders) > config.max_total_gross_exposure:
        raise ValueError("preview exceeds max_total_gross_exposure")
    return orders


def preview_spec_hash(orders: list[DailySwingOrder], config: DailySwingConfig = DEFAULT_CONFIG) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "config": asdict(config),
        "orders": [asdict(order) for order in orders],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def check_daily_swing_operability(
    *,
    repo: Path | None = None,
    env_file: Path | None = None,
    config: DailySwingConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    root = repo_root(repo) if env_file is None else (repo or Path.cwd()).resolve()
    source = env_file or (root / ".env" if (root / ".env").exists() else root / ".env.example")
    env = parse_env_file(source)
    env.update({key: value for key, value in os.environ.items() if key.startswith("TRADEO_")})
    reasons: list[str] = []
    trading_mode = env.get("TRADEO_TRADING_MODE", "").lower()
    ibkr_account = env.get("TRADEO_IBKR_ACCOUNT", "")
    if trading_mode == "live" or truthy(env.get("TRADEO_LIVE_TRADING_ENABLED")):
        reasons.append("live trading flag enabled")
    if truthy(env.get("TRADEO_LIVE_ARMED")) or truthy(env.get("TRADEO_LIVE_TRADING_ARMED")):
        reasons.append("live_armed=true")
    if not config.paper_enabled:
        reasons.append("daily swing paper probe disabled")
    if config.allow_live_orders:
        reasons.append("config allow_live_orders=true")
    if config.kill_switch_required and not truthy(env.get("TRADEO_KILL_SWITCH_ENABLED")):
        reasons.append("kill-switch is not enabled")
    if not truthy(env.get("TRADEO_IBKR_READONLY")):
        reasons.append("TRADEO_IBKR_READONLY is not true for preflight")
    if truthy(env.get("TRADEO_ALLOW_OPTIONS")) or not config.no_options:
        reasons.append("options are allowed")
    if truthy(env.get("TRADEO_ALLOW_MARGIN")) or not config.no_margin:
        reasons.append("margin is allowed")
    if truthy(env.get("TRADEO_ALLOW_SHORTS")) or not config.no_short:
        reasons.append("shorts are allowed")
    if ibkr_account and not ibkr_account.upper().startswith(("DU", "PAPER", "SIM")):
        reasons.append("IBKR account does not look like a paper account")
    orders = generate_daily_swing_preview(config)
    exposure = round(sum(order.quantity * order.limit_price for order in orders), 2)
    if len(orders) > config.max_new_trades_per_day:
        reasons.append("preview exceeds max_new_trades_per_day")
    if exposure > config.max_total_gross_exposure:
        reasons.append("preview exceeds max_total_gross_exposure")
    return {
        "schema_version": SCHEMA_VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "OK" if not reasons else "BLOCKED",
        "reasons": reasons,
        "env_source": str(source),
        "paper_enabled": config.paper_enabled,
        "live_allowed": False,
        "orders_allowed": False,
        "preview_order_count": len(orders),
        "preview_exposure": exposure,
        "preview_spec_hash": preview_spec_hash(orders, config),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def build_daily_swing_artifacts(repo: Path | None = None, config: DailySwingConfig = DEFAULT_CONFIG) -> dict[str, Any]:
    root = repo_root(repo)
    research_dir = root / "research" / "daily_swing"
    runtime_dir = root / "artifacts" / "runtime" / "daily_swing"
    research_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    orders = generate_daily_swing_preview(config)
    spec_hash = preview_spec_hash(orders, config)
    preview = {
        "schema_version": SCHEMA_VERSION,
        "run_date": config.run_date,
        "last_valid_bar_date": last_valid_trading_day(date.fromisoformat(config.run_date)).isoformat(),
        "status": "PREVIEW_ONLY",
        "spec_hash": spec_hash,
        "orders": [asdict(order) for order in orders],
    }
    (runtime_dir / "paper_orders_preview_2026-07-06.json").write_text(
        json.dumps(preview, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(
        runtime_dir / "paper_orders_preview_2026-07-06.csv",
        [asdict(order) for order in orders],
        [
            "pattern_id",
            "signal_id",
            "symbol",
            "signal_date",
            "last_valid_bar_date",
            "entry_order_type",
            "limit_price",
            "stop_price",
            "target_price",
            "time_stop_date",
            "quantity",
            "risk_R",
            "spec_hash",
        ],
    )
    operability = check_daily_swing_operability(repo=root, config=config)
    (runtime_dir / "paper_operability_check.json").write_text(
        json.dumps(operability, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_research_files(root, orders, operability, spec_hash)
    return {"orders": len(orders), "spec_hash": spec_hash, "operability": operability["status"]}


def write_research_files(
    root: Path,
    orders: list[DailySwingOrder],
    operability: dict[str, Any],
    spec_hash: str,
) -> None:
    research_dir = root / "research" / "daily_swing"
    components = [
        {"component": "backend/tradeo/services/backtester.py", "role": "generic backtest engine", "daily_ready": "partial"},
        {"component": "backend/tradeo/services/technical_indicators.py", "role": "indicator primitives", "daily_ready": "usable"},
        {"component": "backend/tradeo/services/ibkr_broker.py", "role": "IBKR safety-gated adapter", "daily_ready": "requires paper guards"},
        {"component": "scripts/check_tradeo_operability.py", "role": "global safety preflight", "daily_ready": "reference"},
        {"component": "backend/tradeo/modules/intraday/*", "role": "intraday-only research stack", "daily_ready": "not reused for signals"},
    ]
    write_csv(
        research_dir / "daily_existing_components.csv",
        components,
        ["component", "role", "daily_ready"],
    )
    metrics = [
        {
            "pattern_id": "DSS-PB-001",
            "classification": "research_gap",
            "real_backtest": False,
            "evidence_source": "scaffold_thresholds_not_historical_backtest",
            "is_expectancy": 0.18,
            "oos_expectancy": 0.07,
            "is_pf": 1.38,
            "oos_pf": 1.24,
            "cost_x2_expectancy": 0.04,
            "max_drawdown_R": -6.2,
            "trades": 184,
            "symbol_count": 38,
            "top3_symbol_concentration": 0.21,
        },
        {
            "pattern_id": "DSS-BO-001",
            "classification": "research_gap",
            "real_backtest": False,
            "evidence_source": "scaffold_thresholds_not_historical_backtest",
            "is_expectancy": 0.13,
            "oos_expectancy": 0.02,
            "is_pf": 1.29,
            "oos_pf": 1.08,
            "cost_x2_expectancy": -0.01,
            "max_drawdown_R": -8.9,
            "trades": 96,
            "symbol_count": 24,
            "top3_symbol_concentration": 0.34,
        },
    ]
    write_csv(
        research_dir / "daily_pattern_catalog.csv",
        [
            {
                "pattern_id": "DSS-PB-001",
                "description": "Pullback in Uptrend Long",
                "variables": "SMA50,SMA200,RSI2,ATR14,SPY regime",
                "horizon": "3-8 daily sessions",
                "entry": "paper LMT after 09:35 ET",
                "exit": "ATR stop, 1.75R target, time stop",
                "universe": "USA liquid stock-only",
            },
            {
                "pattern_id": "DSS-BO-001",
                "description": "Volatility Contraction Breakout Long",
                "variables": "ATR compression, 20/50d high, volume, SPY regime",
                "horizon": "3-8 daily sessions",
                "entry": "reserve only if PB has no valid signals",
                "exit": "ATR stop, time stop",
                "universe": "USA liquid stock-only",
            },
        ],
        ["pattern_id", "description", "variables", "horizon", "entry", "exit", "universe"],
    )
    write_csv(
        research_dir / "daily_research_metrics.csv",
        metrics,
        [
            "pattern_id",
            "classification",
            "real_backtest",
            "evidence_source",
            "is_expectancy",
            "oos_expectancy",
            "is_pf",
            "oos_pf",
            "cost_x2_expectancy",
            "max_drawdown_R",
            "trades",
            "symbol_count",
            "top3_symbol_concentration",
        ],
    )
    markdowns = {
        "DSS_001_DAILY_MAP.md": f"""# DSS-001 Daily Map

Daily-specific production code was not present as a standalone module before this branch. The repo is primarily intraday/research oriented, with reusable broker, backtester, indicator and safety components.

Key decision: add `backend/tradeo/modules/daily_swing/` as the bounded Daily Swing paper-probe surface. It is preview-only by default and treats IBKR execution as blocked until paper safety flags and kill-switch pass.

Generated preview spec hash: `{spec_hash}`.
""",
        "daily_oos_report.md": """# Daily OOS Report

NO-GO for scientific paper eligibility from this branch alone.

`DSS-PB-001` is the operationally preferred pilot pattern, but the branch has not run a real historical Daily backtest against cached/provider data. The metrics CSV is a scaffold showing required fields and thresholds, not evidence for approval.

`DSS-BO-001` remains a reserve research idea. It is not selected for Monday until a real OOS/cost/concentration pass exists.
""",
        "daily_bias_audit.md": """# Daily Bias Audit

- Lookahead: blocked by `last_valid_trading_day`; Monday 2026-07-06 uses Thursday 2026-07-02.
- Holiday: explicit 2026-07-03 observed Independence Day test prevents a fake Friday bar.
- Leakage: preview hashes include signal date, last valid bar date, sizing, entry, stop and target.
- Survivorship: unresolved because the pilot uses current liquid names for preview; live remains blocked and automatic paper submission remains blocked until this is audited.
- Historical evidence: unresolved in this branch; metrics are scaffold placeholders, not backtest output.
- FDR/WRC/SPA: not implemented for Daily in this branch; documented gap, blocks live, does not block paper_probe.
""",
        "DSS_001_MONDAY_RUNBOOK.md": """# DSS-001 Monday Runbook

1. Confirm TWS/IB Gateway is paper only.
2. Run `python scripts/check_daily_swing_paper_operability.py --json-output artifacts/runtime/daily_swing/paper_operability_check.json`.
3. Run `python scripts/plan_daily_swing_paper_orders.py`.
4. Confirm `last_valid_bar_date=2026-07-02` and no row uses 2026-07-03.
5. If operability is BLOCKED, do not submit orders.
6. If no valid signals, record `NO_TRADE_VALID_SIGNAL`.
7. If approved after open, execution window is 09:35-10:00 ET, paper-only, limit orders only.
8. Stop immediately on broker/API errors, hash mismatch, kill-switch failure or live account suspicion.
""",
        "DSS_001_FINAL_REPORT.md": f"""# DSS-001 Final Report

GO/NO-GO: NO-GO for automatic submission and NO-GO for scientific paper eligibility until real Daily backtest evidence exists; GO for code review of the paper-probe planning scaffold.

Preferred pilot pattern: `DSS-PB-001` Pullback in Uptrend Long.

Evidence status: BLOCKED_RESEARCH_GAP. The branch generates deterministic preview orders and safety artifacts, but it does not prove OOS expectancy/PF/cost robustness from real historical data.

Monday preview orders: {len(orders)}.

Operability: {operability["status"]}. Reasons: {", ".join(operability["reasons"]) or "none"}.

Spec hash: `{spec_hash}`.

Recommendation: do not merge as paper-ready. Merge only as a planning scaffold, or require a follow-up branch that runs real Daily backtests before Monday. Live remains blocked.
""",
    }
    for filename, content in markdowns.items():
        (research_dir / filename).write_text(content, encoding="utf-8")
