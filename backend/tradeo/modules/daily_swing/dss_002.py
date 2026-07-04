from __future__ import annotations

import csv
import json
import os
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from tradeo.modules.daily_swing.paper_probe import (
    DEFAULT_CONFIG,
    DailySwingConfig,
    check_daily_swing_operability,
    generate_daily_swing_preview,
    last_valid_trading_day,
    repo_root,
    write_csv,
)


DSS_002_SCHEMA_VERSION = "tradeo.daily_swing.dss_002.v1"
SAFE_ENV_FILENAME = "daily_swing_paper_probe.safe.env.example"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _discover_universe(root: Path, config: DailySwingConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_files = [root / "data" / "universe_us_mid_caps.csv", root / "data" / "universe_us_small_caps.csv"]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in source_files:
        for row in _read_csv(path):
            symbol = (row.get("symbol") or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            rows.append(
                {
                    "symbol": symbol,
                    "name": row.get("name", ""),
                    "cap_segment": row.get("cap_segment", ""),
                    "product_type": "STK",
                    "source_file": str(path.relative_to(root)),
                    "eligible_for_backtest": "no_daily_ohlcv_cache",
                    "exclusion_reason": "no historical OHLCV columns available in local seed universe",
                    "min_price_rule": config.min_price,
                    "min_adv20_rule": config.min_adv20,
                    "min_dollar_volume20_rule": config.min_dollar_volume20,
                }
            )
    summary = {
        "source_files": [str(path.relative_to(root)) for path in source_files if path.exists()],
        "symbols_total": len(rows),
        "stock_only": all(row["product_type"] == "STK" for row in rows),
        "daily_ohlcv_cache_found": False,
        "ohlcv_columns_confirmed": False,
        "last_valid_bar_date": last_valid_trading_day(date.fromisoformat(config.run_date)).isoformat(),
        "false_bar_2026_07_03_present": False,
    }
    return rows, summary


def _find_daily_data_candidates(root: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    wanted = ("daily", "ohlc", "bar", "price", "history", "historical", "eod")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        rel_lower = str(rel).lower()
        if any(part in rel_lower for part in (".git/", ".venv/", ".pytest_cache/", "__pycache__/")):
            continue
        if rel_lower.startswith("artifacts/runtime/daily_swing/"):
            continue
        if path.suffix.lower() not in {".csv", ".json", ".parquet"}:
            continue
        if not any(token in rel_lower for token in wanted):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        candidates.append({"path": str(rel), "size_bytes": size})
    return sorted(candidates, key=lambda item: item["path"])[:100]


def _safe_env_text() -> str:
    return "\n".join(
        [
            "TRADEO_TRADING_MODE=paper",
            "TRADEO_LIVE_TRADING_ENABLED=false",
            "TRADEO_LIVE_ARMED=false",
            "TRADEO_LIVE_TRADING_ARMED=false",
            "TRADEO_INTRADAY_LIVE_ENABLED=false",
            "TRADEO_INTRADAY_PAPER_ENABLED=false",
            "TRADEO_IBKR_READONLY=true",
            "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
            "TRADEO_ALLOW_OPTIONS=false",
            "TRADEO_ALLOW_MARGIN=false",
            "TRADEO_ALLOW_SHORTS=false",
            "TRADEO_KILL_SWITCH_ENABLED=true",
            "TRADEO_IBKR_ACCOUNT=DU_SIMULATED",
            "",
        ]
    )


def _run_operability(root: Path, env_file: Path, config: DailySwingConfig) -> dict[str, Any]:
    previous = {key: os.environ.get(key) for key in os.environ if key.startswith("TRADEO_")}
    try:
        for key in list(os.environ):
            if key.startswith("TRADEO_"):
                os.environ.pop(key, None)
        return check_daily_swing_operability(repo=root, env_file=env_file, config=config)
    finally:
        for key in list(os.environ):
            if key.startswith("TRADEO_"):
                os.environ.pop(key, None)
        for key, value in previous.items():
            if value is not None:
                os.environ[key] = value


def _current_env_path(root: Path) -> Path:
    if (root / ".env").exists():
        return root / ".env"
    return root / ".env.example"


def _git_value(root: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return "not_checked"
    if proc.returncode != 0:
        return "not_checked"
    return proc.stdout.strip()


def build_dss_002_artifacts(
    repo: Path | None = None,
    config: DailySwingConfig = DEFAULT_CONFIG,
) -> dict[str, Any]:
    root = repo_root(repo)
    research_dir = root / "research" / "daily_swing"
    runtime_dir = root / "artifacts" / "runtime" / "daily_swing"
    config_dir = root / "configs"
    research_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    safe_env = config_dir / SAFE_ENV_FILENAME
    safe_env.write_text(_safe_env_text(), encoding="utf-8")

    universe, universe_summary = _discover_universe(root, config)
    write_csv(
        runtime_dir / "dss_002_universe.csv",
        universe,
        [
            "symbol",
            "name",
            "cap_segment",
            "product_type",
            "source_file",
            "eligible_for_backtest",
            "exclusion_reason",
            "min_price_rule",
            "min_adv20_rule",
            "min_dollar_volume20_rule",
        ],
    )

    safe_operability = _run_operability(root, safe_env, config)
    current_operability = _run_operability(root, _current_env_path(root), config)
    (runtime_dir / "dss_002_operability_safe_env.json").write_text(
        json.dumps(safe_operability, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (runtime_dir / "dss_002_operability_current_env.json").write_text(
        json.dumps(current_operability, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    daily_data_candidates = _find_daily_data_candidates(root)
    data_gate = "BLOCKED"
    research_gate = "INSUFFICIENT_DATA"
    bias_gate = "WARNING"
    operability_gate = (
        "PASS_FOR_SAFE_ENV" if safe_operability["status"] == "OK" else "FAIL"
    )
    if current_operability["status"] == "BLOCKED":
        operability_gate = f"{operability_gate} / BLOCKED_CURRENT_ENV"

    metrics = {
        "schema_version": DSS_002_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "pattern_id": config.primary_pattern_id,
        "pattern_name": "DSS-PB-001 Pullback in Uptrend Long",
        "real_backtest": False,
        "research_gate": research_gate,
        "blocked_reason": "local repo has seed universe files but no reusable historical Daily OHLCV cache for DSS-PB-001",
        "trades_total": 0,
        "symbols_total": universe_summary["symbols_total"],
        "is_expectancy": None,
        "oos_expectancy": None,
        "is_profit_factor": None,
        "oos_profit_factor": None,
        "winrate": None,
        "avg_win": None,
        "avg_loss": None,
        "max_drawdown_R": None,
        "worst_streak": None,
        "by_year": {},
        "last_12_months": None,
        "last_24_months": None,
        "cost_x1": None,
        "cost_x2": None,
        "cost_x3": None,
        "top_1_symbol_pnl": None,
        "top_3_symbols_pnl": None,
        "top_5_trades_contribution": None,
        "candidate_signals_2026_07_06": 0,
        "daily_data_candidates": daily_data_candidates,
    }
    (runtime_dir / "dss_pb_001_metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(
        runtime_dir / "dss_pb_001_trades.csv",
        [],
        [
            "trade_id",
            "symbol",
            "signal_date",
            "entry_date",
            "exit_date",
            "entry_price",
            "exit_price",
            "net_R",
            "cost_model",
        ],
    )
    write_csv(
        runtime_dir / "dss_pb_001_oos_summary.csv",
        [
            {
                "pattern_id": config.primary_pattern_id,
                "split": "OOS",
                "status": research_gate,
                "trades": 0,
                "expectancy": "",
                "profit_factor": "",
                "reason": metrics["blocked_reason"],
            }
        ],
        ["pattern_id", "split", "status", "trades", "expectancy", "profit_factor", "reason"],
    )

    previous_preview_symbols = [order.symbol for order in generate_daily_swing_preview(config)]
    decision = {
        "schema_version": DSS_002_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "decision": "NO_GO",
        "data_gate": data_gate,
        "research_gate": research_gate,
        "bias_gate": bias_gate,
        "operability_gate": operability_gate,
        "live_allowed": False,
        "orders_allowed": False,
        "shorts_allowed": False,
        "kill_switch_required": True,
        "real_monday_signals": [],
        "previous_preview_symbols": previous_preview_symbols,
        "difference_vs_previous_preview": "previous AAPL/COST preview remains deterministic scaffold; DSS-002 produced no real signals",
        "required_decision": "no merge as paper-ready; continue research/data ingestion iteration",
    }
    (runtime_dir / "dss_002_go_no_go.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    _write_reports(
        research_dir=research_dir,
        universe_summary=universe_summary,
        daily_data_candidates=daily_data_candidates,
        metrics=metrics,
        safe_operability=safe_operability,
        current_operability=current_operability,
        decision=decision,
    )
    return {
        "decision": decision["decision"],
        "data_gate": data_gate,
        "research_gate": research_gate,
        "bias_gate": bias_gate,
        "operability_gate": operability_gate,
        "artifacts": {
            "universe": str(runtime_dir / "dss_002_universe.csv"),
            "metrics": str(runtime_dir / "dss_pb_001_metrics.json"),
            "go_no_go": str(runtime_dir / "dss_002_go_no_go.json"),
            "safe_env": str(runtime_dir / "dss_002_operability_safe_env.json"),
            "current_env": str(runtime_dir / "dss_002_operability_current_env.json"),
        },
    }


def _write_reports(
    *,
    research_dir: Path,
    universe_summary: dict[str, Any],
    daily_data_candidates: list[dict[str, Any]],
    metrics: dict[str, Any],
    safe_operability: dict[str, Any],
    current_operability: dict[str, Any],
    decision: dict[str, Any],
) -> None:
    data_candidates_text = "\n".join(
        f"- `{item['path']}` ({item['size_bytes']} bytes)" for item in daily_data_candidates[:20]
    ) or "- No historical Daily OHLCV candidate file found."
    current_reasons = ", ".join(current_operability.get("reasons", [])) or "none"
    safe_reasons = ", ".join(safe_operability.get("reasons", [])) or "none"

    reports = {
        "DSS_002_DATA_GATE.md": f"""# DSS-002 Data Gate

DATA_GATE=BLOCKED

Validated local seed universe files and searched for reusable Daily OHLCV cache files. The repo currently exposes seed universe CSVs with `symbol,name,cap_segment,note`, but not enough OHLCV history to run DSS-PB-001.

- Symbols total: {universe_summary['symbols_total']}
- Stock-only seed universe: {universe_summary['stock_only']}
- OHLCV columns confirmed: {universe_summary['ohlcv_columns_confirmed']}
- 2026-07-03 false USA bar present: {universe_summary['false_bar_2026_07_03_present']}
- Last valid bar for 2026-07-06 signals: {universe_summary['last_valid_bar_date']}

Daily data candidates inspected:
{data_candidates_text}

Blocking reason: no local historical Daily OHLCV cache with open/high/low/close/volume, adjusted dates and enough lookback was available for the requested real backtest.
""",
        "DSS_002_DSS_PB_001_BACKTEST.md": f"""# DSS-002 DSS-PB-001 Backtest

RESEARCH_GATE=INSUFFICIENT_DATA

Pattern: DSS-PB-001 Pullback in Uptrend Long.

The run did not execute a real historical backtest because the local branch has no reusable Daily OHLCV cache for the seed universe. I did not use the deterministic AAPL/COST scaffold preview as evidence.

Required metrics are recorded in `artifacts/runtime/daily_swing/dss_pb_001_metrics.json` with null performance values and `real_backtest=false`.

Key outcome:
- trades total: 0
- symbols total: {metrics['symbols_total']}
- IS expectancy: not_available
- OOS expectancy: not_available
- IS PF: not_available
- OOS PF: not_available
- cost x1/x2/x3: not_available
- candidate signals for Monday 2026-07-06: 0 real signals

Decision: no paper probe promotion from research evidence.
""",
        "DSS_002_BIAS_ROBUSTNESS_LITE.md": """# DSS-002 Bias & Robustness Lite

BIAS_GATE=WARNING

No performance robustness test can be trusted without the underlying Daily OHLCV event ledger.

Completed checks:
- Lookahead: code path still computes Monday 2026-07-06 from last valid bar 2026-07-02.
- Calendar: 2026-07-03 is excluded as Independence Day observed.
- Leakage: no real backtest was run, so no leakage in generated performance metrics.
- Duplicate samples: not_applicable until an event ledger exists.
- Placebo: not_run because there are zero DSS-PB-001 real events.
- Cost x1/x2/x3: not_run because there are zero DSS-PB-001 real trades.
- Entry sensitivity: not_run because there are zero DSS-PB-001 real trades.

Live gap: FDR/WRC/SPA for Daily still does not exist and remains a hard live blocker.
""",
        "DSS_002_OPERABILITY_GATE.md": f"""# DSS-002 Operability Gate

OPERABILITY_GATE={decision['operability_gate']}

Safe test env:
- status: {safe_operability['status']}
- reasons: {safe_reasons}

Current env:
- status: {current_operability['status']}
- reasons: {current_reasons}

Implemented safe template: `configs/{SAFE_ENV_FILENAME}`.

The safe env sets kill-switch on, IBKR read-only on, live armed false, live enabled false, options/margin/shorts false and a simulated paper account id. The current env remains blocked if it lacks kill-switch or permits shorts, which is the intended fail-closed behavior.

No `.env` file was modified.
""",
        "DSS_002_FINAL_DECISION.md": f"""# DSS-002 Final Decision

Decision: NO_GO

DATA_GATE={decision['data_gate']}
RESEARCH_GATE={decision['research_gate']}
BIAS_GATE={decision['bias_gate']}
OPERABILITY_GATE={decision['operability_gate']}

Executive summary: DSS-002 did not find enough local Daily OHLCV evidence to promote the Daily Swing Paper Probe. The previous AAPL/COST Monday preview remains a deterministic scaffold, not a real Research-approved signal list.

Monday 2026-07-06 signals:
- real signals: 0
- previous scaffold preview symbols: {', '.join(decision['previous_preview_symbols'])}
- difference: {decision['difference_vs_previous_preview']}

Safety:
- live_allowed=false
- orders_allowed=false
- shorts_allowed=false
- kill_switch_required=true

Recommendation to Director: no merge as paper-ready. Merge only if the branch is wanted as a documented NO_GO/data-gap artifact; otherwise run the next iteration on Daily OHLCV ingestion/backtest evidence.
""",
    }
    for filename, content in reports.items():
        (research_dir / filename).write_text(content, encoding="utf-8")
