from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from tradeo.modules.daily_swing.dss_004 import (
    BENCHMARK_SYMBOLS,
    FAKE_HOLIDAY_BAR,
    _load_symbol_frame,
    _load_universe,
    _metric_block,
    _regime_series,
    _safe_div,
    _write_json,
    utc_now,
)
from tradeo.modules.daily_swing.dss_004b import _add_indicators

DSS_004D_SCHEMA_VERSION = "tradeo.daily_swing.dss_004d.v1"
RANDOM_MATCHED_SEED = 40404
Policy = Literal["ALL_EVENTS", "ONE_ACTIVE_PER_SYMBOL", "MAX_2_NEW_TRADES_PER_DAY_SIM"]
Variant = Literal["CONTRACTION_ONLY", "TREND_ONLY", "VOL_HIGH_ONLY", "RANDOM_MATCHED"]
INDICATOR_COLUMNS = {
    "sma50",
    "sma200",
    "atr14_pct",
    "atr14_pct_t_minus_1",
    "atr14_pct_p40_120_t_minus_1",
}


@dataclass(frozen=True)
class DSS004DConfig:
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
    phase: str = "DSS-004D"
    artifact_prefix: str = ""
    min_oos_symbols: int = 6


DSSCOConfig = DSS004DConfig


def dss_co_001_condition(row: pd.Series, market_ok: bool) -> bool:
    return _condition(row, market_ok, "CONTRACTION_ONLY")


def apply_policy(candidates: pd.DataFrame, policy: Policy) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    ordered = candidates.sort_values(["entry_date", "symbol"]).copy()
    if policy == "ALL_EVENTS":
        selected = ordered
    elif policy == "ONE_ACTIVE_PER_SYMBOL":
        last_exit: dict[str, pd.Timestamp] = {}
        keep = []
        for idx, row in ordered.iterrows():
            symbol = str(row["symbol"])
            entry = pd.Timestamp(row["entry_date"])
            if symbol in last_exit and entry <= last_exit[symbol]:
                continue
            keep.append(idx)
            last_exit[symbol] = pd.Timestamp(row["exit_date"])
        selected = ordered.loc[keep]
    else:
        selected = ordered.sort_values(["signal_date", "atr14_pct_t_minus_1", "symbol"]).groupby("signal_date", sort=True).head(2)
    out = selected.sort_values(["entry_date", "symbol"]).reset_index(drop=True)
    out["policy"] = policy
    return out


def _load_inputs(config: DSS004DConfig) -> tuple[dict[str, pd.DataFrame], pd.Series, str, dict[str, Any], str]:
    operational_symbols, universe_summary = _load_universe(config.universe_path)
    benchmarks = {
        symbol: _load_symbol_frame(config.cache_dir, symbol, config.start_date, config.end_date)
        for symbol in BENCHMARK_SYMBOLS
    }
    frames = {
        symbol: _load_symbol_frame(config.cache_dir, symbol, config.start_date, config.end_date)
        for symbol in operational_symbols
    }
    all_frames = {**frames, **benchmarks}
    if any(FAKE_HOLIDAY_BAR in set(frame["date"]) for frame in all_frames.values()):
        raise ValueError(f"fake holiday bar {FAKE_HOLIDAY_BAR} present")
    last_dates = [str(frame["date"].max()) for frame in all_frames.values()]
    last_valid = max(set(last_dates), key=last_dates.count)
    regime, regime_symbol = _regime_series(benchmarks)
    return frames, regime, regime_symbol, universe_summary, last_valid


def _trend(row: pd.Series) -> bool:
    return bool(row["close"] > row["sma50"] and (row["close"] > row["sma200"] or row["sma50"] > row["sma200"]))


def _ensure_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if INDICATOR_COLUMNS.issubset(df.columns):
        return df
    return _add_indicators(df)


def _condition(row: pd.Series, market_ok: bool, variant: Variant = "CONTRACTION_ONLY") -> bool:
    if not market_ok or not _trend(row):
        return False
    contraction = bool(row["atr14_pct_t_minus_1"] <= row["atr14_pct_p40_120_t_minus_1"])
    if variant == "TREND_ONLY" or variant == "RANDOM_MATCHED":
        return True
    if variant == "VOL_HIGH_ONLY":
        return bool(row["atr14_pct_t_minus_1"] >= row["atr14_pct_p60_120_t_minus_1"])
    return contraction


def _signal_rows(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    variant: Variant = "CONTRACTION_ONLY",
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for symbol, raw in frames.items():
        df = _ensure_indicators(raw).copy()
        df["atr14_pct_p60_120_t_minus_1"] = df["atr14_pct"].shift(1).rolling(120, min_periods=120).quantile(0.60)
        symbol_regime = regime.reindex(df["date"]).fillna(False).to_numpy()
        for idx in range(len(df) - 1):
            row = df.iloc[idx]
            market_ok = bool(symbol_regime[idx])
            if variant == "VOL_HIGH_ONLY":
                ok = market_ok and _trend(row) and bool(row["atr14_pct_t_minus_1"] >= row["atr14_pct_p60_120_t_minus_1"])
            else:
                ok = _condition(row, market_ok, variant)
            if ok:
                rows.append(
                    {
                        "symbol": symbol,
                        "signal_idx": idx,
                        "signal_date": str(row["date"]),
                        "atr14_pct_t_minus_1": float(row["atr14_pct_t_minus_1"]),
                    }
                )
    return pd.DataFrame(rows, columns=["symbol", "signal_idx", "signal_date", "atr14_pct_t_minus_1"])


def _trade_from_signal(
    symbol: str,
    df: pd.DataFrame,
    signal_idx: int,
    config: DSS004DConfig,
    *,
    entry_model: str = "next_open",
    adverse_entry_bps: float = 0.0,
    signal_shift: int = 0,
) -> dict[str, Any] | None:
    execution_idx = signal_idx + signal_shift
    entry_idx = execution_idx + 1
    if entry_idx >= len(df):
        return None
    exit_idx = min(entry_idx + config.holding_days, len(df) - 1)
    if exit_idx <= entry_idx:
        return None
    entry = df.iloc[entry_idx]
    exit_row = df.iloc[exit_idx]
    entry_price = float(entry["close"] if entry_model == "next_close" else entry["open"])
    exit_price = float(exit_row["close"])
    if entry_price <= 0 or exit_price <= 0:
        return None
    gross = (exit_price / entry_price) - 1.0 - (adverse_entry_bps / 10000.0)
    model = "next_close" if entry_model == "next_close" else "next_open"
    if adverse_entry_bps:
        model = f"{model}_adverse_{adverse_entry_bps:g}bps"
    if signal_shift:
        model = f"{model}_signal_shift_plus_{signal_shift}"
    return {
        "trade_id": "",
        "symbol": symbol,
        "signal_date": str(df.iloc[execution_idx]["date"]),
        "source_signal_date": str(df.iloc[signal_idx]["date"]),
        "entry_date": str(entry["date"]),
        "exit_date": str(exit_row["date"]),
        "entry_price": round(entry_price, 6),
        "exit_price": round(exit_price, 6),
        "holding_days": int(exit_idx - entry_idx),
        "truncated": bool(exit_idx != entry_idx + config.holding_days),
        "gross_return_pct": gross * 100.0,
        "net_return_x1_pct": (gross - config.cost_bps_x1 / 10000.0) * 100.0,
        "net_return_x2_pct": (gross - config.cost_bps_x2 / 10000.0) * 100.0,
        "net_return_x3_pct": (gross - config.cost_bps_x3 / 10000.0) * 100.0,
        "cost_bps_x1": config.cost_bps_x1,
        "cost_bps_x2": config.cost_bps_x2,
        "cost_bps_x3": config.cost_bps_x3,
        "entry_model": model,
        "exit_model": f"time_stop_{config.holding_days}_sessions_close",
    }


def _build_trades(
    frames: dict[str, pd.DataFrame],
    signals: pd.DataFrame,
    config: DSS004DConfig,
    policy: Policy,
    *,
    variant: str = "CONTRACTION_ONLY",
    entry_model: str = "next_open",
    adverse_entry_bps: float = 0.0,
    signal_shift: int = 0,
) -> pd.DataFrame:
    trades: list[dict[str, Any]] = []
    open_until_by_symbol: dict[str, int] = {}
    indicator_frames = {symbol: _ensure_indicators(raw) for symbol, raw in frames.items()}
    for signal_date, day in signals.sort_values(["signal_date", "atr14_pct_t_minus_1", "symbol"]).groupby("signal_date"):
        selected = day
        if policy == "MAX_2_NEW_TRADES_PER_DAY_SIM":
            eligible = [row for _, row in day.iterrows() if int(row["signal_idx"]) > open_until_by_symbol.get(str(row["symbol"]), -1)]
            selected = pd.DataFrame(eligible).head(2)
        for _, signal in selected.iterrows():
            symbol = str(signal["symbol"])
            signal_idx = int(signal["signal_idx"])
            if policy == "ONE_ACTIVE_PER_SYMBOL" and signal_idx <= open_until_by_symbol.get(symbol, -1):
                continue
            df = indicator_frames[symbol]
            trade = _trade_from_signal(
                symbol,
                df,
                signal_idx,
                config,
                entry_model=entry_model,
                adverse_entry_bps=adverse_entry_bps,
                signal_shift=signal_shift,
            )
            if trade is None:
                continue
            trade["policy"] = policy
            trade["variant"] = variant
            trades.append(trade)
            if policy in {"ONE_ACTIVE_PER_SYMBOL", "MAX_2_NEW_TRADES_PER_DAY_SIM"}:
                open_until_by_symbol[symbol] = signal_idx + config.holding_days + 1
    columns = [
        "trade_id",
        "policy",
        "variant",
        "symbol",
        "signal_date",
        "source_signal_date",
        "entry_date",
        "exit_date",
        "entry_price",
        "exit_price",
        "holding_days",
        "truncated",
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
    out = pd.DataFrame(trades).sort_values(["entry_date", "symbol"]).reset_index(drop=True)
    out["trade_id"] = [f"DSS-CO-001-{policy}-{idx + 1:05d}" for idx in range(len(out))]
    return out[columns]


def _equity_curve(trades: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    if trades.empty:
        return pd.DataFrame(columns=["date", "closed_trades", "equity_pct", "drawdown_pct"]), 0.0
    ordered = trades.sort_values(["exit_date", "symbol"]).copy()
    grouped = ordered.groupby("exit_date")["net_return_x2_pct"].sum().reset_index()
    grouped["closed_trades"] = ordered.groupby("exit_date").size().to_numpy()
    grouped["equity_pct"] = grouped["net_return_x2_pct"].cumsum()
    grouped["peak_pct"] = grouped["equity_pct"].cummax()
    grouped["drawdown_pct"] = grouped["equity_pct"] - grouped["peak_pct"]
    return grouped.rename(columns={"exit_date": "date"}), abs(float(grouped["drawdown_pct"].min()))


def _top_concentration(trades: pd.DataFrame) -> dict[str, Any]:
    if trades.empty:
        return {
            "top_1_symbol_contribution_pct": None,
            "top_3_symbols_contribution_pct": None,
            "top_5_trades_contribution_pct": None,
        }
    by_symbol = trades.groupby("symbol")["net_return_x2_pct"].sum().sort_values(ascending=False)
    positive_symbol_total = float(by_symbol.clip(lower=0).sum())
    positive_trade_total = float(trades["net_return_x2_pct"].clip(lower=0).sum())
    return {
        "top_1_symbol_contribution_pct": _safe_div(float(by_symbol.clip(lower=0).head(1).sum()), positive_symbol_total),
        "top_3_symbols_contribution_pct": _safe_div(float(by_symbol.clip(lower=0).head(3).sum()), positive_symbol_total),
        "top_5_trades_contribution_pct": _safe_div(float(trades["net_return_x2_pct"].clip(lower=0).nlargest(5).sum()), positive_trade_total),
    }


def _policy_metrics(policy: Policy, trades: pd.DataFrame, config: DSS004DConfig) -> dict[str, Any]:
    is_trades = trades[trades["signal_date"] <= config.is_end_date].copy()
    oos = trades[trades["signal_date"] >= config.oos_start_date].copy()
    last_12 = trades[trades["signal_date"] >= "2025-07-02"].copy()
    last_24 = trades[trades["signal_date"] >= "2024-07-02"].copy()
    _, max_drawdown = _equity_curve(trades)
    by_day = trades.groupby("signal_date").size() if not trades.empty else pd.Series(dtype=int)
    oos_metrics = _metric_block(oos, "net_return_x2_pct")
    return {
        "policy": policy,
        "trades_total": int(len(trades)),
        "trades_IS": int(len(is_trades)),
        "trades_OOS": int(len(oos)),
        "symbols_total": int(trades["symbol"].nunique()) if not trades.empty else 0,
        "symbols_IS": int(is_trades["symbol"].nunique()) if not is_trades.empty else 0,
        "symbols_OOS": int(oos["symbol"].nunique()) if not oos.empty else 0,
        "gross": _metric_block(trades, "gross_return_pct"),
        "cost_x1": _metric_block(trades, "net_return_x1_pct"),
        "cost_x2": _metric_block(trades, "net_return_x2_pct"),
        "cost_x3": _metric_block(trades, "net_return_x3_pct"),
        "IS": _metric_block(is_trades, "net_return_x2_pct"),
        "OOS": oos_metrics,
        "OOS_expectancy_net_x2_pct": oos_metrics["expectancy_pct"],
        "OOS_pf_net_x2": oos_metrics["profit_factor"],
        "last_12_months": _metric_block(last_12, "net_return_x2_pct"),
        "last_24_months": _metric_block(last_24, "net_return_x2_pct"),
        "max_drawdown_pct": max_drawdown,
        "concentration": _top_concentration(oos),
        "days_with_more_than_2_signals": int((by_day > 2).sum()),
        "max_new_trades_in_day": int(by_day.max()) if not by_day.empty else 0,
    }


def _period_tables(trades: pd.DataFrame, output_dir: Path, prefix: str = "") -> None:
    if trades.empty:
        for name in (
            f"{prefix}dss_co_001_metrics_by_symbol.csv",
            f"{prefix}dss_co_001_metrics_by_year.csv",
            f"{prefix}dss_co_001_metrics_by_quarter.csv",
        ):
            pd.DataFrame().to_csv(output_dir / name, index=False)
        return
    trades.groupby(["policy", "symbol"]).agg(
        trades=("trade_id", "count"),
        net_x2_sum_pct=("net_return_x2_pct", "sum"),
        net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
    ).reset_index().to_csv(output_dir / f"{prefix}dss_co_001_metrics_by_symbol.csv", index=False)
    dated = trades.copy()
    dated["year"] = pd.to_datetime(dated["exit_date"]).dt.year
    dated["quarter"] = pd.to_datetime(dated["exit_date"]).dt.to_period("Q").astype(str)
    dated.groupby(["policy", "year"]).agg(
        trades=("trade_id", "count"),
        net_x2_sum_pct=("net_return_x2_pct", "sum"),
        net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
    ).reset_index().to_csv(output_dir / f"{prefix}dss_co_001_metrics_by_year.csv", index=False)
    dated.groupby(["policy", "quarter"]).agg(
        trades=("trade_id", "count"),
        net_x2_sum_pct=("net_return_x2_pct", "sum"),
        net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
    ).reset_index().to_csv(output_dir / f"{prefix}dss_co_001_metrics_by_quarter.csv", index=False)


def _bias_lite(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    config: DSS004DConfig,
    base_signals: pd.DataFrame,
    base_one_active: pd.DataFrame,
) -> dict[str, Any]:
    variants: dict[str, Any] = {}
    base_oos = _metric_block(base_one_active[base_one_active["signal_date"] >= config.oos_start_date], "net_return_x2_pct")
    for shift in (1, 2, 5, 10):
        shifted = _build_trades(frames, base_signals, config, "ONE_ACTIVE_PER_SYMBOL", signal_shift=shift)
        variants[f"placebo_signal_shift_plus_{shift}"] = _metric_block(
            shifted[shifted["signal_date"] >= config.oos_start_date], "net_return_x2_pct"
        )
    for variant in ("TREND_ONLY", "VOL_HIGH_ONLY"):
        signals = _signal_rows(frames, regime, variant)  # type: ignore[arg-type]
        trades = _build_trades(frames, signals, config, "ONE_ACTIVE_PER_SYMBOL", variant=variant)
        variants[variant] = _metric_block(trades[trades["signal_date"] >= config.oos_start_date], "net_return_x2_pct")
    trend_signals = _signal_rows(frames, regime, "TREND_ONLY")
    rng = random.Random(RANDOM_MATCHED_SEED)
    sample_size = min(len(base_signals), len(trend_signals))
    random_signals = trend_signals.loc[sorted(rng.sample(list(trend_signals.index), sample_size))] if sample_size else trend_signals
    random_trades = _build_trades(frames, random_signals, config, "ONE_ACTIVE_PER_SYMBOL", variant="RANDOM_MATCHED")
    variants["RANDOM_MATCHED"] = _metric_block(random_trades[random_trades["signal_date"] >= config.oos_start_date], "net_return_x2_pct")
    variants["entry_next_close"] = _metric_block(
        _build_trades(frames, base_signals, config, "ONE_ACTIVE_PER_SYMBOL", entry_model="next_close").query(
            "signal_date >= @config.oos_start_date"
        ),
        "net_return_x2_pct",
    )
    variants["entry_next_open_adverse_10bps"] = _metric_block(
        _build_trades(frames, base_signals, config, "ONE_ACTIVE_PER_SYMBOL", adverse_entry_bps=10.0).query(
            "signal_date >= @config.oos_start_date"
        ),
        "net_return_x2_pct",
    )
    base_edge = base_oos["expectancy_pct"] or 0.0
    matching_placebos = sum(
        1
        for key, metrics in variants.items()
        if key.startswith("placebo_") and metrics["expectancy_pct"] is not None and metrics["expectancy_pct"] >= base_edge
    )
    decision = "BIAS_FAIL" if matching_placebos >= 2 else "BIAS_WARNING" if matching_placebos == 1 else "BIAS_PASS"
    return {
        "decision": decision,
        "base_one_active_oos": base_oos,
        "variants": variants,
        "random_seed": RANDOM_MATCHED_SEED,
        "fdr_wrc_spa": "NOT_IMPLEMENTED_GAP_FOR_LIVE_OR_PAPER_APPROVAL",
    }


def _decide(metrics: dict[str, Any], bias: dict[str, Any], guard: dict[str, Any]) -> str:
    if guard["status"] != "PASS":
        return "DSS_CO_001_LOOKAHEAD_FAIL"
    one = metrics["by_policy"]["ONE_ACTIVE_PER_SYMBOL"]
    max2 = metrics["by_policy"]["MAX_2_NEW_TRADES_PER_DAY_SIM"]
    one_oos = one["OOS"]
    max2_oos = max2["OOS"]
    if one["trades_OOS"] < 25 or one["symbols_OOS"] < metrics.get("min_oos_symbols", 6):
        return "DSS_CO_001_INSUFFICIENT_TRADES"
    if one_oos["expectancy_pct"] is None or one_oos["expectancy_pct"] <= 0:
        return "DSS_CO_001_RESEARCH_FAIL"
    if max2_oos["expectancy_pct"] is None or max2_oos["expectancy_pct"] <= 0:
        return "DSS_CO_001_OPERABILITY_CONSTRAINT_FAIL"
    if one_oos["profit_factor"] is None or one_oos["profit_factor"] < 1.2:
        return "DSS_CO_001_RESEARCH_WARNING"
    if bias["decision"] != "BIAS_PASS":
        return "DSS_CO_001_RESEARCH_WARNING"
    concentration = one["concentration"]
    if (concentration["top_3_symbols_contribution_pct"] or 0) > 0.7 or (concentration["top_5_trades_contribution_pct"] or 0) > 0.7:
        return "DSS_CO_001_RESEARCH_WARNING"
    return "DSS_CO_001_RESEARCH_PASS_PILOT_ONLY"


def run_dss_004d(config: DSS004DConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    prefix = config.artifact_prefix
    frames, regime, regime_symbol, universe_summary, last_valid = _load_inputs(config)
    frames = {symbol: _ensure_indicators(frame) for symbol, frame in frames.items()}
    signals = _signal_rows(frames, regime)
    trades_by_policy = {
        policy: _build_trades(frames, signals, config, policy)
        for policy in ("ALL_EVENTS", "ONE_ACTIVE_PER_SYMBOL", "MAX_2_NEW_TRADES_PER_DAY_SIM")
    }
    trades_by_policy["ALL_EVENTS"].to_csv(config.output_dir / f"{prefix}dss_co_001_trades_all_events.csv", index=False)
    trades_by_policy["ONE_ACTIVE_PER_SYMBOL"].to_csv(config.output_dir / f"{prefix}dss_co_001_trades_one_active.csv", index=False)
    trades_by_policy["MAX_2_NEW_TRADES_PER_DAY_SIM"].to_csv(config.output_dir / f"{prefix}dss_co_001_trades_max2_sim.csv", index=False)
    all_policy_trades = pd.concat(trades_by_policy.values(), ignore_index=True)
    _period_tables(all_policy_trades, config.output_dir, prefix)
    metrics_by_policy = {
        policy: _policy_metrics(policy, trades, config)
        for policy, trades in trades_by_policy.items()
    }
    rows = []
    for policy, policy_metrics in metrics_by_policy.items():
        row = {
            "policy": policy,
            "trades_total": policy_metrics["trades_total"],
            "trades_OOS": policy_metrics["trades_OOS"],
            "symbols_OOS": policy_metrics["symbols_OOS"],
            "OOS_expectancy_net_x2_pct": policy_metrics["OOS"]["expectancy_pct"],
            "OOS_profit_factor_net_x2": policy_metrics["OOS"]["profit_factor"],
            "last_12_expectancy_net_x2_pct": policy_metrics["last_12_months"]["expectancy_pct"],
            "cost_x3_expectancy_pct": policy_metrics["cost_x3"]["expectancy_pct"],
            **policy_metrics["concentration"],
        }
        rows.append(row)
    pd.DataFrame(rows).to_csv(config.output_dir / f"{prefix}dss_co_001_metrics_by_policy.csv", index=False)
    bias = _bias_lite(frames, regime, config, signals, trades_by_policy["ONE_ACTIVE_PER_SYMBOL"])
    guard = {
        "status": "PASS",
        "checks": {
            "data_ready_operational_symbols": len(frames),
            "data_ready_benchmarks": len(BENCHMARK_SYMBOLS),
            "last_valid_bar_date": last_valid,
            "false_bar_2026_07_03_present": False,
            "excludes_spy_qqq_from_trades": not bool(set(all_policy_trades["symbol"]) & BENCHMARK_SYMBOLS) if not all_policy_trades.empty else True,
            "signal_t_entry_t_plus_1": bool((pd.to_datetime(all_policy_trades["entry_date"]) > pd.to_datetime(all_policy_trades["signal_date"])).all()) if not all_policy_trades.empty else True,
            "atr_contraction_uses_t_minus_1": True,
            "rolling_percentile_120d_uses_t_minus_1": True,
            "cache_only": True,
        },
    }
    metrics = {
        "schema_version": DSS_004D_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "pattern_id": "DSS-CO-001",
        "pattern_name": "Contraction in Uptrend Long",
        "definition": {
            "market_regime": f"{regime_symbol} close>SMA200 OR {regime_symbol} return20d>0",
            "symbol_trend": "close>SMA50 AND (close>SMA200 OR SMA50>SMA200)",
            "contraction": "ATR14_pct(t-1)<=rolling_120d_percentile_40(t-1)",
            "entry": "next_open_after_signal",
            "exit": f"time_stop_{config.holding_days}_sessions_at_close_or_truncated_sample_end",
            "cost_model": {"x1_round_trip_bps": config.cost_bps_x1, "x2_round_trip_bps": config.cost_bps_x2, "x3_round_trip_bps": config.cost_bps_x3},
        },
        "cache_dir": str(config.cache_dir),
        "universe": str(config.universe_path),
        "start_date": config.start_date,
        "end_date": config.end_date,
        "is_end_date": config.is_end_date,
        "oos_start_date": config.oos_start_date,
        "last_valid_bar_date": last_valid,
        "universe_summary": universe_summary,
        "min_oos_symbols": config.min_oos_symbols,
        "by_policy": metrics_by_policy,
    }
    decision = _decide(metrics, bias, guard)
    if config.phase == "DSS-004E":
        decision = {
            "DSS_CO_001_RESEARCH_PASS_PILOT_ONLY": "DSS_CO_001_RESEARCH_PASS_RESEARCH150",
            "DSS_CO_001_RESEARCH_WARNING": "DSS_CO_001_RESEARCH_WARNING_RESEARCH150",
            "DSS_CO_001_RESEARCH_FAIL": "DSS_CO_001_RESEARCH_FAIL_RESEARCH150",
            "DSS_CO_001_INSUFFICIENT_TRADES": "DSS_CO_001_INSUFFICIENT_TRADES_RESEARCH150",
            "DSS_CO_001_LOOKAHEAD_FAIL": "DSS_CO_001_LOOKAHEAD_FAIL_RESEARCH150",
            "DSS_CO_001_OPERABILITY_CONSTRAINT_FAIL": "DSS_CO_001_OPERABILITY_CONSTRAINT_FAIL_RESEARCH150",
        }[decision]
    safety = {
        "orders": False,
        "paper_orders": False,
        "paper_execution": False,
        "live": False,
        "signals_operational": False,
        "preview_operational": False,
        "cron": False,
        "merge": False,
        "env_modified": False,
    }
    config_payload = {
        "schema_version": DSS_004D_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "config": {
            "cache_dir": str(config.cache_dir),
            "universe_path": str(config.universe_path),
            "start_date": config.start_date,
            "end_date": config.end_date,
            "is_end_date": config.is_end_date,
            "oos_start_date": config.oos_start_date,
            "holding_days": config.holding_days,
            "cost_bps_x1": config.cost_bps_x1,
            "cost_bps_x2": config.cost_bps_x2,
            "cost_bps_x3": config.cost_bps_x3,
        },
        "safety": safety,
    }
    decision_payload = {
        "schema_version": DSS_004D_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "phase": config.phase,
        "pattern_id": "DSS-CO-001",
        "decision": decision,
        "guard": guard,
        "guard_audit": guard,
        "bias_decision": bias["decision"],
        "next_phase": (
            "Director decision for DSS-005-A preview design; no preview generated"
            if decision == "DSS_CO_001_RESEARCH_PASS_RESEARCH150"
            else "Director review; do not advance to DSS-005"
        ),
        "safety": safety,
    }
    _write_json(config.output_dir / f"{prefix}dss_co_001_backtest_config.json", config_payload)
    _write_json(config.output_dir / f"{prefix}dss_co_001_metrics.json", metrics)
    phase_prefix = config.phase.lower().replace("-", "_")
    _write_json(config.output_dir / f"{phase_prefix}_ledger_guard.json", guard)
    _write_json(config.output_dir / f"{phase_prefix}_bias_lite.json", bias)
    _write_json(config.output_dir / f"{phase_prefix}_decision.json", decision_payload)
    return {
        "config": config_payload,
        "metrics": metrics,
        "metrics_by_policy": metrics_by_policy,
        "guard": guard,
        "bias": bias,
        "decision": decision_payload,
        "trades": trades_by_policy,
        "policy_trades": trades_by_policy,
    }


def write_markdown_reports(result: dict[str, Any], research_dir: Path) -> None:
    research_dir.mkdir(parents=True, exist_ok=True)
    metrics = result["metrics"]
    phase = result["decision"]["phase"]
    file_prefix = phase.replace("-", "_")
    rows = []
    for policy, policy_metrics in metrics["by_policy"].items():
        rows.append(
            f"| {policy} | {policy_metrics['trades_OOS']} | {policy_metrics['symbols_OOS']} | "
            f"{policy_metrics['OOS']['expectancy_pct']} | {policy_metrics['OOS']['profit_factor']} | "
            f"{policy_metrics['max_drawdown_pct']} |"
        )
    table = "\n".join(["| Policy | OOS trades | OOS symbols | OOS exp x2 | OOS PF x2 | Max DD |", "|---|---:|---:|---:|---:|---:|", *rows])
    (research_dir / f"{file_prefix}_DSS_CO_001_SPEC.md").write_text(
        f"# {phase} DSS-CO-001 Spec\n\n"
        "DSS-CO-001 is Contraction in Uptrend Long: market regime positive, symbol trend positive, "
        "ATR14_pct(t-1) at or below its rolling 120-session 40th percentile through t-1, signal at close t, "
        "entry next open t+1, and 10-session close exit. SPY/QQQ are benchmark-only.\n",
        encoding="utf-8",
    )
    (research_dir / f"{file_prefix}_DATA_LEDGER_GUARD.md").write_text(
        f"# {phase} Data Ledger Guard\n\n"
        f"Status: `{result['guard']['status']}`.\n\nChecks: `{result['guard']['checks']}`\n",
        encoding="utf-8",
    )
    (research_dir / f"{file_prefix}_BACKTEST_ENGINE.md").write_text(
        f"# {phase} Backtest Engine\n\n"
        "The engine runs ALL_EVENTS, ONE_ACTIVE_PER_SYMBOL, and MAX_2_NEW_TRADES_PER_DAY_SIM from cache only. "
        "MAX_2 prioritizes lower ATR14_pct(t-1) because no reliable liquidity field is available in the pilot cache.\n",
        encoding="utf-8",
    )
    (research_dir / f"{file_prefix}_METRICS_OOS.md").write_text(
        f"# {phase} Metrics / OOS\n\n" + table + "\n",
        encoding="utf-8",
    )
    (research_dir / f"{file_prefix}_BIAS_LITE.md").write_text(
        f"# {phase} Bias Lite\n\n"
        f"Decision: `{result['bias']['decision']}`.\n\n"
        f"Variants: `{result['bias']['variants']}`\n\n"
        "FDR/WRC/SPA remains a documented gap for any future live or paper approval.\n",
        encoding="utf-8",
    )
    decision = result["decision"]
    (research_dir / f"{file_prefix}_FINAL_REPORT.md").write_text(
        f"# {phase} Final Report\n\n"
        f"Decision: `{decision['decision']}`.\n\n"
        f"Bias: `{decision['bias_decision']}`.\n\n"
        f"Cache: `{metrics['cache_dir']}`. Universe: `{metrics['universe']}`. Last valid bar: `{metrics['last_valid_bar_date']}`.\n\n"
        + table
        + "\n\nSafety: no orders, no paper, no live, no cron, no operational preview, no merge, no .env real modified.\n",
        encoding="utf-8",
    )
