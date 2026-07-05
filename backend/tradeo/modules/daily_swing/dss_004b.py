from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from tradeo.modules.daily_swing.dss_004 import (
    BENCHMARK_SYMBOLS,
    FAKE_HOLIDAY_BAR,
    _load_symbol_frame,
    _load_universe,
    _metric_block,
    _regime_series,
    _robustness,
    _safe_div,
    _write_json,
    utc_now,
)

DSS_004B_SCHEMA_VERSION = "tradeo.daily_swing.dss_004b.v1"


@dataclass(frozen=True)
class BacktestConfig:
    cache_dir: Path
    universe_path: Path
    start_date: str
    end_date: str
    is_end_date: str
    oos_start_date: str
    output_dir: Path
    holding_days: int = 10
    cost_bps_x1: float = 10.0
    cost_bps_x2: float = 20.0
    cost_bps_x3: float = 30.0


def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sma50"] = out["close"].rolling(50, min_periods=50).mean()
    out["sma200"] = out["close"].rolling(200, min_periods=200).mean()
    high_low = out["high"] - out["low"]
    high_prev_close = (out["high"] - out["close"].shift(1)).abs()
    low_prev_close = (out["low"] - out["close"].shift(1)).abs()
    out["true_range"] = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    out["atr14"] = out["true_range"].rolling(14, min_periods=14).mean()
    out["atr14_pct"] = out["atr14"] / out["close"]
    out["atr14_pct_t_minus_1"] = out["atr14_pct"].shift(1)
    out["atr14_pct_p40_120_t_minus_1"] = out["atr14_pct"].shift(1).rolling(120, min_periods=120).quantile(0.40)
    out["prior_high20"] = out["high"].shift(1).rolling(20, min_periods=20).max()
    return out


def _trade_from_window(
    symbol: str,
    df: pd.DataFrame,
    signal_idx: int,
    config: BacktestConfig,
    *,
    entry_model: str = "next_open",
    adverse_entry_bps: float = 0.0,
) -> dict[str, Any] | None:
    entry_idx = signal_idx + 1
    exit_idx = min(entry_idx + config.holding_days, len(df) - 1)
    if entry_idx >= len(df) or exit_idx <= entry_idx:
        return None
    entry = df.iloc[entry_idx]
    exit_row = df.iloc[exit_idx]
    entry_price = float(entry["close"] if entry_model == "next_close" else entry["open"])
    exit_price = float(exit_row["close"])
    if entry_price <= 0 or exit_price <= 0:
        return None
    gross = (exit_price / entry_price) - 1.0 - (adverse_entry_bps / 10000.0)
    return {
        "trade_id": "",
        "symbol": symbol,
        "signal_date": str(df.iloc[signal_idx]["date"]),
        "entry_date": str(entry["date"]),
        "exit_date": str(exit_row["date"]),
        "entry_price": round(entry_price, 6),
        "exit_price": round(exit_price, 6),
        "holding_days": int(exit_idx - entry_idx),
        "gross_return_pct": gross * 100.0,
        "net_return_x1_pct": (gross - config.cost_bps_x1 / 10000.0) * 100.0,
        "net_return_x2_pct": (gross - config.cost_bps_x2 / 10000.0) * 100.0,
        "net_return_x3_pct": (gross - config.cost_bps_x3 / 10000.0) * 100.0,
        "cost_bps_x1": config.cost_bps_x1,
        "cost_bps_x2": config.cost_bps_x2,
        "cost_bps_x3": config.cost_bps_x3,
        "entry_model": "next_close" if entry_model == "next_close" else "next_open",
        "exit_model": f"time_stop_{config.holding_days}_sessions_close",
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
        for idx in range(len(df) - 1):
            execution_signal_idx = idx + signal_shift
            if execution_signal_idx <= last_exit_idx or execution_signal_idx >= len(df) - 1:
                continue
            row = df.iloc[idx]
            trend = bool(
                row["close"] > row["sma50"]
                and (row["close"] > row["sma200"] or row["sma50"] > row["sma200"])
            )
            contraction = bool(row["atr14_pct_t_minus_1"] <= row["atr14_pct_p40_120_t_minus_1"])
            breakout = bool(row["close"] > row["prior_high20"])
            if not bool(symbol_regime[idx]) or not trend or not contraction or not breakout:
                continue
            trade = _trade_from_window(
                symbol,
                df,
                execution_signal_idx,
                config,
                entry_model=entry_model,
                adverse_entry_bps=adverse_entry_bps,
            )
            if trade is None:
                continue
            if adverse_entry_bps:
                trade["entry_model"] = f"{trade['entry_model']}_adverse_{adverse_entry_bps:g}bps"
            if signal_shift:
                trade["entry_model"] = f"{trade['entry_model']}_signal_shift_plus_{signal_shift}"
            last_exit_idx = execution_signal_idx + config.holding_days + 1
            trades.append(trade)
    columns = [
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
    if not trades:
        return pd.DataFrame(columns=columns)
    trades_df = pd.DataFrame(trades).sort_values(["entry_date", "symbol"]).reset_index(drop=True)
    trades_df["trade_id"] = [f"DSS-BO-001-{idx + 1:05d}" for idx in range(len(trades_df))]
    return trades_df[columns]


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
    names = (
        "dss_bo_001_metrics_by_symbol.csv",
        "dss_bo_001_metrics_by_year.csv",
        "dss_bo_001_metrics_by_quarter.csv",
    )
    if trades.empty:
        for name in names:
            pd.DataFrame().to_csv(output_dir / name, index=False)
        return {
            "top_1_symbol_contribution_pct": None,
            "top_3_symbols_contribution_pct": None,
            "top_5_trades_contribution_pct": None,
        }
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
    by_symbol.to_csv(output_dir / names[0], index=False)
    dated = trades.copy()
    dated["year"] = pd.to_datetime(dated["exit_date"]).dt.year
    dated["quarter"] = pd.to_datetime(dated["exit_date"]).dt.to_period("Q").astype(str)
    dated.groupby("year").agg(
        trades=("trade_id", "count"),
        net_x2_sum_pct=("net_return_x2_pct", "sum"),
        net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
    ).reset_index().to_csv(output_dir / names[1], index=False)
    dated.groupby("quarter").agg(
        trades=("trade_id", "count"),
        net_x2_sum_pct=("net_return_x2_pct", "sum"),
        net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
    ).reset_index().to_csv(output_dir / names[2], index=False)
    positive_total = float(by_symbol["net_x2_sum_pct"].clip(lower=0).sum())
    trade_positive_total = float(trades["net_return_x2_pct"].clip(lower=0).sum())
    return {
        "top_1_symbol_contribution_pct": _safe_div(float(by_symbol["net_x2_sum_pct"].clip(lower=0).head(1).sum()), positive_total),
        "top_3_symbols_contribution_pct": _safe_div(float(by_symbol["net_x2_sum_pct"].clip(lower=0).head(3).sum()), positive_total),
        "top_5_trades_contribution_pct": _safe_div(float(trades["net_return_x2_pct"].clip(lower=0).nlargest(5).sum()), trade_positive_total),
    }


def _candidate_signal_count(frames: dict[str, pd.DataFrame], regime: pd.Series, signal_date: str) -> int:
    count = 0
    for raw in frames.values():
        df = _add_indicators(raw)
        rows = df[df["date"] == signal_date]
        if rows.empty:
            continue
        row = rows.iloc[0]
        trend = bool(row["close"] > row["sma50"] and (row["close"] > row["sma200"] or row["sma50"] > row["sma200"]))
        contraction = bool(row["atr14_pct_t_minus_1"] <= row["atr14_pct_p40_120_t_minus_1"])
        breakout = bool(row["close"] > row["prior_high20"])
        market_ok = bool(regime.reindex([signal_date]).fillna(False).iloc[0])
        if market_ok and trend and contraction and breakout:
            count += 1
    return count


def _decision(metrics: dict[str, Any], robustness: dict[str, Any]) -> str:
    oos = metrics["oos"]
    concentration = metrics["concentration"]
    if metrics["trades_total"] == 0 or oos["trades"] < 25 or oos["symbols"] < 6:
        return "DSS_BO_001_INSUFFICIENT_TRADES"
    if robustness["duplicate_trades_audit"] != "PASS":
        return "DSS_BO_001_LOOKAHEAD_FAIL"
    if oos["expectancy_net_x2_pct"] <= 0 or oos["profit_factor_net_x2"] is None:
        return "DSS_BO_001_RESEARCH_FAIL"
    if oos["profit_factor_net_x2"] < 1.15:
        return "DSS_BO_001_RESEARCH_WARNING"
    if concentration["top_3_symbols_contribution_pct"] and concentration["top_3_symbols_contribution_pct"] > 0.7:
        return "DSS_BO_001_RESEARCH_WARNING"
    if robustness["decision"] == "BIAS_WARNING":
        return "DSS_BO_001_RESEARCH_WARNING"
    return "DSS_BO_001_RESEARCH_PASS"


def run_dss_bo_001_backtest(config: BacktestConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    operational_symbols, universe_summary = _load_universe(config.universe_path)
    benchmarks = {symbol: _load_symbol_frame(config.cache_dir, symbol, config.start_date, config.end_date) for symbol in BENCHMARK_SYMBOLS}
    frames = {symbol: _load_symbol_frame(config.cache_dir, symbol, config.start_date, config.end_date) for symbol in operational_symbols}
    all_frames = {**frames, **benchmarks}
    false_bar_present = any(FAKE_HOLIDAY_BAR in set(frame["date"]) for frame in all_frames.values())
    if false_bar_present:
        raise ValueError(f"fake holiday bar {FAKE_HOLIDAY_BAR} present")
    all_last_dates = {symbol: frame["date"].max() for symbol, frame in all_frames.items()}
    last_valid = max(set(all_last_dates.values()), key=list(all_last_dates.values()).count)
    regime, regime_symbol = _regime_series(benchmarks)
    trades = generate_trades(frames, regime, config)
    trades_path = config.output_dir / "dss_bo_001_trades.csv"
    trades.to_csv(trades_path, index=False)
    equity, max_drawdown = _equity_curve(trades)
    equity_path = config.output_dir / "dss_bo_001_daily_equity.csv"
    equity.to_csv(equity_path, index=False)

    is_trades = trades[trades["signal_date"] <= config.is_end_date].copy()
    oos_trades = trades[trades["signal_date"] >= config.oos_start_date].copy()
    concentration = _period_tables(trades, config.output_dir)
    last_12 = trades[trades["signal_date"] >= "2025-07-02"].copy()
    last_24 = trades[trades["signal_date"] >= "2024-07-02"].copy()
    gross = _metric_block(trades, "gross_return_pct")
    x1 = _metric_block(trades, "net_return_x1_pct")
    x2 = _metric_block(trades, "net_return_x2_pct")
    x3 = _metric_block(trades, "net_return_x3_pct")
    is_x2 = _metric_block(is_trades, "net_return_x2_pct")
    oos_x2 = _metric_block(oos_trades, "net_return_x2_pct")
    robustness = _robustness(frames, regime, config, trades)
    robustness["variants"] = {
        "base_next_open": _metric_block(trades),
        "entry_next_close": _metric_block(generate_trades(frames, regime, config, entry_model="next_close")),
        "entry_next_open_adverse_10bps": _metric_block(generate_trades(frames, regime, config, adverse_entry_bps=10.0)),
        "placebo_signal_shift_plus_1": _metric_block(generate_trades(frames, regime, config, signal_shift=1)),
        "placebo_signal_shift_plus_2": _metric_block(generate_trades(frames, regime, config, signal_shift=2)),
        "placebo_signal_shift_plus_5": _metric_block(generate_trades(frames, regime, config, signal_shift=5)),
    }
    placebo_edges = [
        robustness["variants"][f"placebo_signal_shift_plus_{shift}"]["expectancy_pct"]
        for shift in (1, 2, 5)
    ]
    robustness["decision"] = "BIAS_WARNING" if all(edge and edge > 0 for edge in placebo_edges) else "BIAS_PASS"
    metrics: dict[str, Any] = {
        "schema_version": DSS_004B_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "pattern_id": "DSS-BO-001",
        "pattern_name": "Volatility Contraction Breakout Long",
        "definition": {
            "market_regime": f"{regime_symbol} close>SMA200 OR {regime_symbol} return20d>0",
            "symbol_trend": "close>SMA50 AND (close>SMA200 OR SMA50>SMA200)",
            "contraction": "ATR14_pct(t-1)<=rolling_120d_percentile_40(t-1)",
            "breakout": "close_t>prior_high20_t_minus_1",
            "entry": "next_open_after_signal",
            "exit": f"time_stop_{config.holding_days}_sessions_at_close",
            "cost_model": {"x1_round_trip_bps": config.cost_bps_x1, "x2_round_trip_bps": config.cost_bps_x2, "x3_round_trip_bps": config.cost_bps_x3},
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
        "gross": {"expectancy_pct": gross["expectancy_pct"], "profit_factor": gross["profit_factor"]},
        "cost_x1": {"expectancy_pct": x1["expectancy_pct"], "profit_factor": x1["profit_factor"]},
        "cost_x2": {"expectancy_pct": x2["expectancy_pct"], "profit_factor": x2["profit_factor"]},
        "cost_x3": {"expectancy_pct": x3["expectancy_pct"], "profit_factor": x3["profit_factor"]},
        "IS": is_x2,
        "oos": {**oos_x2, "expectancy_net_x2_pct": oos_x2["expectancy_pct"], "profit_factor_net_x2": oos_x2["profit_factor"]},
        "last_12_months": _metric_block(last_12, "net_return_x2_pct"),
        "last_24_months": _metric_block(last_24, "net_return_x2_pct"),
        "winrate": x2["winrate"],
        "avg_win_pct": x2["avg_win_pct"],
        "avg_loss_pct": x2["avg_loss_pct"],
        "max_drawdown_pct": max_drawdown,
        "worst_streak": x2["worst_streak"],
        "concentration": concentration,
        "candidate_signals_2026_07_06_research_count": _candidate_signal_count(frames, regime, last_valid),
        "risk_R_status": "NOT_AVAILABLE_NO_STOP_RISK_DEFINED_PERCENT_METRICS_USED",
    }
    pd.DataFrame([{"segment": "IS", **is_x2}, {"segment": "OOS", **oos_x2}, {"segment": "LAST_12_MONTHS", **metrics["last_12_months"]}, {"segment": "LAST_24_MONTHS", **metrics["last_24_months"]}]).to_csv(
        config.output_dir / "dss_bo_001_oos_summary.csv", index=False
    )
    decision = _decision(metrics, robustness)
    metrics["decision"] = decision
    safety = {"orders": False, "paper_execution": False, "live": False, "signals_operational": False, "cron": False, "env_modified": False}
    config_payload = {"schema_version": DSS_004B_SCHEMA_VERSION, "generated_at": utc_now(), "config": config.__dict__ | {"cache_dir": str(config.cache_dir), "universe_path": str(config.universe_path), "output_dir": str(config.output_dir)}, "safety": safety}
    ledger_summary = {"schema_version": DSS_004B_SCHEMA_VERSION, "generated_at": utc_now(), "data_ready_symbols": len(operational_symbols), "benchmark_ready": len(BENCHMARK_SYMBOLS), "last_valid_bar_date": last_valid, "false_bar_2026_07_03_present": false_bar_present, "no_lookahead": "signal_date_t_entry_date_t_plus_1", "atr_contraction": "uses_t_minus_1", "breakout": "uses_prior_high20", "regime_symbol": regime_symbol}
    decision_payload = {"schema_version": DSS_004B_SCHEMA_VERSION, "generated_at": utc_now(), "decision": decision, "pattern_id": "DSS-BO-001", "research_pass": decision == "DSS_BO_001_RESEARCH_PASS", "next_phase": "manual Director review only" if decision == "DSS_BO_001_RESEARCH_PASS" else "review Director criteria", "safety": safety}
    _write_json(config.output_dir / "dss_bo_001_backtest_config.json", config_payload)
    _write_json(config.output_dir / "dss_bo_001_metrics.json", metrics)
    _write_json(config.output_dir / "dss_004b_data_ledger_summary.json", ledger_summary)
    _write_json(config.output_dir / "dss_004b_bias_robustness.json", robustness)
    _write_json(config.output_dir / "dss_004b_decision.json", decision_payload)
    return {"config": config_payload, "ledger": ledger_summary, "metrics": metrics, "robustness": robustness, "decision": decision_payload, "trades_path": str(trades_path), "equity_path": str(equity_path)}
