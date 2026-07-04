from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

BENCHMARK_SYMBOLS = {"SPY", "QQQ"}
DSS_004_SCHEMA_VERSION = "tradeo.daily_swing.dss_004.v1"
FAKE_HOLIDAY_BAR = "2026-07-03"


@dataclass(frozen=True)
class BacktestConfig:
    cache_dir: Path
    universe_path: Path
    start_date: str
    end_date: str
    is_end_date: str
    oos_start_date: str
    output_dir: Path
    holding_days: int = 5
    cost_bps_x1: float = 10.0
    cost_bps_x2: float = 20.0
    cost_bps_x3: float = 30.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _load_universe(path: Path) -> tuple[list[str], dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"universe file missing: {path}")
    universe = pd.read_csv(path)
    required = {"symbol", "benchmark_only", "operational_eligible", "product_type"}
    missing = required - set(universe.columns)
    if missing:
        raise ValueError(f"universe missing columns: {sorted(missing)}")

    universe["symbol"] = universe["symbol"].astype(str).str.upper().str.strip()
    universe["benchmark_only_bool"] = universe["benchmark_only"].map(_parse_bool)
    universe["operational_eligible_bool"] = universe["operational_eligible"].map(_parse_bool)
    operational = universe[universe["operational_eligible_bool"]].copy()
    operational_symbols = operational["symbol"].tolist()

    benchmark_operational = sorted(set(operational_symbols) & BENCHMARK_SYMBOLS)
    if benchmark_operational:
        raise ValueError(f"benchmarks marked operational: {benchmark_operational}")
    non_stock = operational[operational["product_type"].astype(str).str.upper() != "STK"]
    if not non_stock.empty:
        raise ValueError(f"non-stock operational symbols: {non_stock['symbol'].tolist()}")
    benchmarks = set(universe[universe["benchmark_only_bool"]]["symbol"])
    missing_benchmarks = sorted(BENCHMARK_SYMBOLS - benchmarks)
    if missing_benchmarks:
        raise ValueError(f"missing benchmark rows: {missing_benchmarks}")

    return operational_symbols, {
        "universe_rows": int(len(universe)),
        "operational_symbols": len(operational_symbols),
        "benchmark_symbols": sorted(benchmarks & BENCHMARK_SYMBOLS),
        "operational_etf_or_fund_rows": 0,
    }


def _load_symbol_frame(cache_dir: Path, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    path = cache_dir / f"{symbol}.csv"
    if not path.exists():
        raise ValueError(f"cache file missing for {symbol}: {path}")
    df = pd.read_csv(path)
    required = {"symbol", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{symbol} cache missing columns: {sorted(missing)}")
    df["symbol"] = symbol
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    if FAKE_HOLIDAY_BAR in set(df["date"]):
        raise ValueError(f"{symbol} contains fake holiday bar {FAKE_HOLIDAY_BAR}")
    df = df[(df["date"] >= start_date) & (df["date"] <= end_date)].copy()
    df = df.sort_values("date").drop_duplicates("date", keep=False).reset_index(drop=True)
    if df.empty:
        raise ValueError(f"{symbol} has no bars in requested range")
    for column in ("open", "high", "low", "close", "volume"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if df[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise ValueError(f"{symbol} has NaN numeric OHLCV values")
    invalid_ohlc = (df["high"] < df[["open", "close", "low"]].max(axis=1)) | (
        df["low"] > df[["open", "close", "high"]].min(axis=1)
    )
    if bool(invalid_ohlc.any()):
        raise ValueError(f"{symbol} has invalid OHLC rows")
    return df


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sma50"] = out["close"].rolling(50, min_periods=50).mean()
    out["sma200"] = out["close"].rolling(200, min_periods=200).mean()
    out["ret20"] = out["close"].pct_change(20)
    down = out["close"] < out["close"].shift(1)
    streak: list[int] = []
    current = 0
    for value in down.fillna(False).tolist():
        current = current + 1 if value else 0
        streak.append(current)
    out["down_streak"] = streak
    return out


def _regime_series(benchmarks: dict[str, pd.DataFrame]) -> tuple[pd.Series, str]:
    for symbol in ("SPY", "QQQ"):
        frame = _add_indicators(benchmarks[symbol]).set_index("date")
        regime = (frame["close"] > frame["sma200"]) | (frame["ret20"] > 0)
        if int(regime.notna().sum()) > 0:
            return regime.fillna(False), symbol
    raise ValueError("no benchmark has enough data for regime")


def _trade_from_window(
    symbol: str,
    df: pd.DataFrame,
    signal_idx: int,
    holding_days: int,
    cost_bps_x1: float,
    cost_bps_x2: float,
    cost_bps_x3: float,
) -> dict[str, Any] | None:
    entry_idx = signal_idx + 1
    exit_idx = entry_idx + holding_days
    if exit_idx >= len(df):
        return None
    entry = df.iloc[entry_idx]
    exit_row = df.iloc[exit_idx]
    entry_price = float(entry["open"])
    exit_price = float(exit_row["close"])
    if entry_price <= 0 or exit_price <= 0:
        return None
    gross = (exit_price / entry_price) - 1.0
    return {
        "trade_id": "",
        "symbol": symbol,
        "signal_date": str(df.iloc[signal_idx]["date"]),
        "entry_date": str(entry["date"]),
        "exit_date": str(exit_row["date"]),
        "entry_price": round(entry_price, 6),
        "exit_price": round(exit_price, 6),
        "holding_days": holding_days,
        "gross_return_pct": gross * 100.0,
        "net_return_x1_pct": (gross - cost_bps_x1 / 10000.0) * 100.0,
        "net_return_x2_pct": (gross - cost_bps_x2 / 10000.0) * 100.0,
        "net_return_x3_pct": (gross - cost_bps_x3 / 10000.0) * 100.0,
        "cost_bps_x1": cost_bps_x1,
        "cost_bps_x2": cost_bps_x2,
        "cost_bps_x3": cost_bps_x3,
        "entry_model": "next_open",
        "exit_model": f"time_stop_{holding_days}_sessions_close",
    }


def generate_trades(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    config: BacktestConfig,
    *,
    signal_shift: int = 0,
    entry_model: str = "next_open",
    adverse_entry_bps: float = 0.0,
) -> pd.DataFrame:
    trades: list[dict[str, Any]] = []
    for symbol, raw in frames.items():
        df = _add_indicators(raw)
        symbol_regime = regime.reindex(df["date"]).fillna(False).to_numpy()
        last_exit_idx = -1
        for idx in range(len(df) - config.holding_days - 1):
            execution_signal_idx = idx + signal_shift
            if execution_signal_idx <= last_exit_idx or execution_signal_idx >= len(df) - config.holding_days - 1:
                continue
            row = df.iloc[idx]
            trend = bool(
                row["close"] > row["sma50"]
                and (row["close"] > row["sma200"] or row["sma50"] > row["sma200"])
            )
            pullback = 2 <= int(row["down_streak"]) <= 4
            if not bool(symbol_regime[idx]) or not trend or not pullback:
                continue
            trade = _trade_from_window(
                symbol,
                df,
                execution_signal_idx,
                config.holding_days,
                config.cost_bps_x1,
                config.cost_bps_x2,
                config.cost_bps_x3,
            )
            if trade is None:
                continue
            if entry_model == "next_close":
                entry_idx = execution_signal_idx + 1
                exit_idx = entry_idx + config.holding_days
                entry_price = float(df.iloc[entry_idx]["close"])
                exit_price = float(df.iloc[exit_idx]["close"])
                gross = (exit_price / entry_price) - 1.0
                trade.update(
                    {
                        "entry_price": round(entry_price, 6),
                        "gross_return_pct": gross * 100.0,
                        "net_return_x1_pct": (gross - config.cost_bps_x1 / 10000.0) * 100.0,
                        "net_return_x2_pct": (gross - config.cost_bps_x2 / 10000.0) * 100.0,
                        "net_return_x3_pct": (gross - config.cost_bps_x3 / 10000.0) * 100.0,
                        "entry_model": "next_close",
                    }
                )
            if adverse_entry_bps:
                penalty = adverse_entry_bps / 10000.0
                for key in ("gross_return_pct", "net_return_x1_pct", "net_return_x2_pct", "net_return_x3_pct"):
                    trade[key] = trade[key] - penalty * 100.0
                trade["entry_model"] = f"{trade['entry_model']}_adverse_{adverse_entry_bps:g}bps"
            if signal_shift:
                trade["entry_model"] = f"{trade['entry_model']}_signal_shift_plus_{signal_shift}"
            last_exit_idx = execution_signal_idx + config.holding_days + 1
            trades.append(trade)
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        return pd.DataFrame(
            columns=[
                "trade_id",
                "symbol",
                "signal_date",
                "entry_date",
                "exit_date",
                "entry_price",
                "exit_price",
                "holding_days",
                "gross_return_pct",
                "net_return_x1_pct",
                "net_return_x2_pct",
                "net_return_x3_pct",
                "cost_bps_x1",
                "cost_bps_x2",
                "cost_bps_x3",
                "entry_model",
                "exit_model",
            ]
        )
    trades_df = trades_df.sort_values(["entry_date", "symbol"]).reset_index(drop=True)
    trades_df["trade_id"] = [f"DSS-PB-001-{idx + 1:05d}" for idx in range(len(trades_df))]
    return trades_df


def _metric_block(trades: pd.DataFrame, column: str = "net_return_x2_pct") -> dict[str, Any]:
    if trades.empty:
        return {
            "trades": 0,
            "symbols": 0,
            "expectancy_pct": None,
            "profit_factor": None,
            "winrate": None,
            "avg_win_pct": None,
            "avg_loss_pct": None,
            "worst_streak": 0,
        }
    returns = trades[column].astype(float)
    wins = returns[returns > 0]
    losses = returns[returns < 0]
    signs = returns <= 0
    worst = 0
    current = 0
    for losing in signs.tolist():
        current = current + 1 if losing else 0
        worst = max(worst, current)
    return {
        "trades": int(len(trades)),
        "symbols": int(trades["symbol"].nunique()),
        "expectancy_pct": float(returns.mean()),
        "profit_factor": _safe_div(float(wins.sum()), abs(float(losses.sum()))),
        "winrate": float((returns > 0).mean()),
        "avg_win_pct": float(wins.mean()) if len(wins) else None,
        "avg_loss_pct": float(losses.mean()) if len(losses) else None,
        "worst_streak": int(worst),
    }


def _equity_curve(trades: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    if trades.empty:
        return pd.DataFrame(columns=["date", "closed_trades", "equity_pct", "drawdown_pct"]), 0.0
    ordered = trades.sort_values(["exit_date", "symbol"]).copy()
    grouped = ordered.groupby("exit_date")["net_return_x2_pct"].sum().reset_index()
    grouped["closed_trades"] = ordered.groupby("exit_date").size().to_numpy()
    grouped["equity_pct"] = grouped["net_return_x2_pct"].cumsum()
    grouped["peak_pct"] = grouped["equity_pct"].cummax()
    grouped["drawdown_pct"] = grouped["equity_pct"] - grouped["peak_pct"]
    max_dd = abs(float(grouped["drawdown_pct"].min())) if not grouped.empty else 0.0
    return grouped[["exit_date", "closed_trades", "equity_pct", "drawdown_pct"]].rename(
        columns={"exit_date": "date"}
    ), max_dd


def _period_tables(trades: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    if trades.empty:
        for name in ("dss_pb_001_metrics_by_symbol.csv", "dss_pb_001_metrics_by_year.csv", "dss_pb_001_metrics_by_quarter.csv"):
            pd.DataFrame().to_csv(output_dir / name, index=False)
        return {"top_1_symbol_contribution_pct": None, "top_3_symbols_contribution_pct": None, "top_5_trades_contribution_pct": None}
    by_symbol = (
        trades.groupby("symbol")
        .agg(
            trades=("trade_id", "count"),
            net_x2_sum_pct=("net_return_x2_pct", "sum"),
            net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
        )
        .reset_index()
        .sort_values("net_x2_sum_pct", ascending=False)
    )
    by_symbol.to_csv(output_dir / "dss_pb_001_metrics_by_symbol.csv", index=False)
    dated = trades.copy()
    dated["year"] = pd.to_datetime(dated["exit_date"]).dt.year
    dated["quarter"] = pd.to_datetime(dated["exit_date"]).dt.to_period("Q").astype(str)
    by_year = (
        dated.groupby("year")
        .agg(trades=("trade_id", "count"), net_x2_sum_pct=("net_return_x2_pct", "sum"), net_x2_expectancy_pct=("net_return_x2_pct", "mean"))
        .reset_index()
    )
    by_quarter = (
        dated.groupby("quarter")
        .agg(trades=("trade_id", "count"), net_x2_sum_pct=("net_return_x2_pct", "sum"), net_x2_expectancy_pct=("net_return_x2_pct", "mean"))
        .reset_index()
    )
    by_year.to_csv(output_dir / "dss_pb_001_metrics_by_year.csv", index=False)
    by_quarter.to_csv(output_dir / "dss_pb_001_metrics_by_quarter.csv", index=False)
    positive_total = float(by_symbol["net_x2_sum_pct"].clip(lower=0).sum())
    top_1 = _safe_div(float(by_symbol["net_x2_sum_pct"].clip(lower=0).head(1).sum()), positive_total)
    top_3 = _safe_div(float(by_symbol["net_x2_sum_pct"].clip(lower=0).head(3).sum()), positive_total)
    trade_positive_total = float(trades["net_return_x2_pct"].clip(lower=0).sum())
    top_5_trades = _safe_div(float(trades["net_return_x2_pct"].clip(lower=0).nlargest(5).sum()), trade_positive_total)
    return {
        "top_1_symbol_contribution_pct": top_1,
        "top_3_symbols_contribution_pct": top_3,
        "top_5_trades_contribution_pct": top_5_trades,
    }


def _robustness(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    config: BacktestConfig,
    base_trades: pd.DataFrame,
) -> dict[str, Any]:
    variants: dict[str, Any] = {
        "base_next_open": _metric_block(base_trades),
        "entry_next_close": _metric_block(generate_trades(frames, regime, config, entry_model="next_close")),
        "entry_next_open_adverse_10bps": _metric_block(
            generate_trades(frames, regime, config, adverse_entry_bps=10.0)
        ),
    }
    for shift in (1, 2, 5):
        variants[f"placebo_signal_shift_plus_{shift}"] = _metric_block(
            generate_trades(frames, regime, config, signal_shift=shift)
        )
    duplicate_keys = (
        base_trades.groupby(["symbol", "signal_date"]).size().max() if not base_trades.empty else 0
    )
    return {
        "decision": "BIAS_WARNING",
        "lookahead_audit": "PASS_SIGNAL_T_ENTRY_T_PLUS_1",
        "leakage_audit": "PASS_CACHE_ONLY_NO_FUTURE_SIGNAL_FIELDS",
        "duplicate_trades_audit": "PASS" if int(duplicate_keys or 0) <= 1 else "FAIL",
        "holiday_audit": "PASS_NO_2026_07_03_BAR",
        "variants": variants,
        "fdr_wrc_spa": "NOT_IMPLEMENTED_BLOCKS_LIVE_NOT_PAPER_PROBE",
    }


def _candidate_signal_count(frames: dict[str, pd.DataFrame], regime: pd.Series, signal_date: str) -> int:
    count = 0
    for raw in frames.values():
        df = _add_indicators(raw)
        rows = df[df["date"] == signal_date]
        if rows.empty:
            continue
        row = rows.iloc[0]
        trend = bool(
            row["close"] > row["sma50"]
            and (row["close"] > row["sma200"] or row["sma50"] > row["sma200"])
        )
        pullback = 2 <= int(row["down_streak"]) <= 4
        market_ok = bool(regime.reindex([signal_date]).fillna(False).iloc[0])
        if market_ok and trend and pullback:
            count += 1
    return count


def _decision(metrics: dict[str, Any], robustness: dict[str, Any]) -> str:
    oos = metrics["oos"]
    concentration = metrics["concentration"]
    if metrics["trades_total"] == 0:
        return "DSS_PB_001_INSUFFICIENT_TRADES"
    if oos["trades"] < 25 or oos["symbols"] < 6:
        return "DSS_PB_001_INSUFFICIENT_TRADES"
    if oos["expectancy_net_x2_pct"] <= 0 or oos["profit_factor_net_x2"] is None:
        return "DSS_PB_001_RESEARCH_FAIL"
    if oos["profit_factor_net_x2"] < 1.15:
        return "DSS_PB_001_RESEARCH_WARNING"
    if concentration["top_3_symbols_contribution_pct"] and concentration["top_3_symbols_contribution_pct"] > 0.7:
        return "DSS_PB_001_RESEARCH_WARNING"
    if robustness["duplicate_trades_audit"] != "PASS":
        return "DSS_PB_001_LOOKAHEAD_FAIL"
    return "DSS_PB_001_RESEARCH_PASS"


def run_dss_pb_001_backtest(config: BacktestConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    operational_symbols, universe_summary = _load_universe(config.universe_path)
    benchmarks = {
        symbol: _load_symbol_frame(config.cache_dir, symbol, config.start_date, config.end_date)
        for symbol in BENCHMARK_SYMBOLS
    }
    frames = {
        symbol: _load_symbol_frame(config.cache_dir, symbol, config.start_date, config.end_date)
        for symbol in operational_symbols
    }
    all_last_dates = {symbol: frame["date"].max() for symbol, frame in {**frames, **benchmarks}.items()}
    if set(BENCHMARK_SYMBOLS) - set(benchmarks):
        raise ValueError("SPY/QQQ missing")
    last_valid = max(set(all_last_dates.values()), key=list(all_last_dates.values()).count)
    false_bar_present = any(FAKE_HOLIDAY_BAR in set(frame["date"]) for frame in [*frames.values(), *benchmarks.values()])
    if false_bar_present:
        raise ValueError(f"fake holiday bar {FAKE_HOLIDAY_BAR} present")

    regime, regime_symbol = _regime_series(benchmarks)
    trades = generate_trades(frames, regime, config)
    trades_path = config.output_dir / "dss_pb_001_trades.csv"
    trades.to_csv(trades_path, index=False)
    equity, max_drawdown = _equity_curve(trades)
    equity_path = config.output_dir / "dss_pb_001_daily_equity.csv"
    equity.to_csv(equity_path, index=False)

    is_trades = trades[trades["signal_date"] <= config.is_end_date].copy()
    oos_trades = trades[trades["signal_date"] >= config.oos_start_date].copy()
    concentration = _period_tables(trades, config.output_dir)
    last_12 = trades[trades["signal_date"] >= "2025-07-02"].copy()
    last_24 = trades[trades["signal_date"] >= "2024-07-02"].copy()
    candidate_count = _candidate_signal_count(frames, regime, last_valid)

    gross = _metric_block(trades, "gross_return_pct")
    x1 = _metric_block(trades, "net_return_x1_pct")
    x2 = _metric_block(trades, "net_return_x2_pct")
    x3 = _metric_block(trades, "net_return_x3_pct")
    is_x2 = _metric_block(is_trades, "net_return_x2_pct")
    oos_x2 = _metric_block(oos_trades, "net_return_x2_pct")
    robustness = _robustness(frames, regime, config, trades)
    metrics: dict[str, Any] = {
        "schema_version": DSS_004_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "pattern_id": "DSS-PB-001",
        "pattern_name": "Pullback in Uptrend Long",
        "definition": {
            "market_regime": f"{regime_symbol} close>SMA200 OR {regime_symbol} return20d>0",
            "symbol_trend": "close>SMA50 AND (close>SMA200 OR SMA50>SMA200)",
            "pullback": "2_to_4_consecutive_down_closes",
            "entry": "next_open_after_signal",
            "exit": f"time_stop_{config.holding_days}_sessions_at_close",
            "cost_model": {
                "x1_round_trip_bps": config.cost_bps_x1,
                "x2_round_trip_bps": config.cost_bps_x2,
                "x3_round_trip_bps": config.cost_bps_x3,
            },
        },
        "cache_dir": str(config.cache_dir),
        "universe": str(config.universe_path),
        "start_date": config.start_date,
        "end_date": config.end_date,
        "is_end_date": config.is_end_date,
        "oos_start_date": config.oos_start_date,
        "last_valid_bar_date": last_valid,
        "false_bar_2026_07_03_present": false_bar_present,
        "universe_summary": universe_summary,
        "trades_total": int(len(trades)),
        "trades_IS": int(len(is_trades)),
        "trades_OOS": int(len(oos_trades)),
        "symbols_total": int(trades["symbol"].nunique()) if not trades.empty else 0,
        "symbols_IS": int(is_trades["symbol"].nunique()) if not is_trades.empty else 0,
        "symbols_OOS": int(oos_trades["symbol"].nunique()) if not oos_trades.empty else 0,
        "gross": {
            "expectancy_pct": gross["expectancy_pct"],
            "profit_factor": gross["profit_factor"],
        },
        "cost_x1": {
            "expectancy_pct": x1["expectancy_pct"],
            "profit_factor": x1["profit_factor"],
        },
        "cost_x2": {
            "expectancy_pct": x2["expectancy_pct"],
            "profit_factor": x2["profit_factor"],
        },
        "cost_x3": {
            "expectancy_pct": x3["expectancy_pct"],
            "profit_factor": x3["profit_factor"],
        },
        "IS": is_x2,
        "oos": {
            **oos_x2,
            "expectancy_net_x2_pct": oos_x2["expectancy_pct"],
            "profit_factor_net_x2": oos_x2["profit_factor"],
        },
        "last_12_months": _metric_block(last_12, "net_return_x2_pct"),
        "last_24_months": _metric_block(last_24, "net_return_x2_pct"),
        "winrate": x2["winrate"],
        "avg_win_pct": x2["avg_win_pct"],
        "avg_loss_pct": x2["avg_loss_pct"],
        "max_drawdown_pct": max_drawdown,
        "worst_streak": x2["worst_streak"],
        "concentration": concentration,
        "candidate_signals_2026_07_06_research_count": candidate_count,
        "average_exposure_open_trades": None,
        "max_exposure_open_trades": None,
        "risk_R_status": "NOT_AVAILABLE_NO_STOP_RISK_DEFINED_PERCENT_METRICS_USED",
    }
    oos_summary = pd.DataFrame(
        [
            {"segment": "IS", **is_x2},
            {"segment": "OOS", **oos_x2},
            {"segment": "LAST_12_MONTHS", **metrics["last_12_months"]},
            {"segment": "LAST_24_MONTHS", **metrics["last_24_months"]},
        ]
    )
    oos_summary.to_csv(config.output_dir / "dss_pb_001_oos_summary.csv", index=False)
    decision = _decision(metrics, robustness)
    metrics["decision"] = decision

    config_payload = {
        "schema_version": DSS_004_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "config": {
            "cache_dir": str(config.cache_dir),
            "universe": str(config.universe_path),
            "start_date": config.start_date,
            "end_date": config.end_date,
            "is_end_date": config.is_end_date,
            "oos_start_date": config.oos_start_date,
            "holding_days": config.holding_days,
            "cost_bps_x1": config.cost_bps_x1,
            "cost_bps_x2": config.cost_bps_x2,
            "cost_bps_x3": config.cost_bps_x3,
        },
        "safety": {
            "orders": False,
            "paper_execution": False,
            "live": False,
            "signals_operational": False,
            "cron": False,
            "env_modified": False,
        },
    }
    ledger_summary = {
        "schema_version": DSS_004_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "data_ready_symbols": len(operational_symbols),
        "benchmark_ready": len(BENCHMARK_SYMBOLS),
        "last_valid_bar_date": last_valid,
        "false_bar_2026_07_03_present": false_bar_present,
        "no_lookahead": "signal_date_t_entry_date_t_plus_1",
        "regime_symbol": regime_symbol,
    }
    decision_payload = {
        "schema_version": DSS_004_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "decision": decision,
        "pattern_id": "DSS-PB-001",
        "research_pass": decision == "DSS_PB_001_RESEARCH_PASS",
        "next_phase": "DSS-005 paper_probe signal preview only" if decision == "DSS_PB_001_RESEARCH_PASS" else "review Director criteria",
        "safety": config_payload["safety"],
    }

    _write_json(config.output_dir / "dss_pb_001_backtest_config.json", config_payload)
    _write_json(config.output_dir / "dss_pb_001_metrics.json", metrics)
    _write_json(config.output_dir / "dss_004_data_ledger_summary.json", ledger_summary)
    _write_json(config.output_dir / "dss_004_bias_robustness.json", robustness)
    _write_json(config.output_dir / "dss_004_decision.json", decision_payload)
    return {
        "config": config_payload,
        "ledger": ledger_summary,
        "metrics": metrics,
        "robustness": robustness,
        "decision": decision_payload,
        "trades_path": str(trades_path),
        "equity_path": str(equity_path),
    }
