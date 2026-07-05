from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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
from tradeo.modules.daily_swing.dss_004b import BacktestConfig, _add_indicators, generate_trades

DSS_004C_SCHEMA_VERSION = "tradeo.daily_swing.dss_004c.v1"
RANDOM_SEED = 40401


@dataclass(frozen=True)
class AutopsyConfig:
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

    def backtest_config(self) -> BacktestConfig:
        return BacktestConfig(
            cache_dir=self.cache_dir,
            universe_path=self.universe_path,
            start_date=self.start_date,
            end_date=self.end_date,
            is_end_date=self.is_end_date,
            oos_start_date=self.oos_start_date,
            output_dir=self.output_dir,
            holding_days=self.holding_days,
            cost_bps_x1=self.cost_bps_x1,
            cost_bps_x2=self.cost_bps_x2,
            cost_bps_x3=self.cost_bps_x3,
        )


def _load_inputs(config: AutopsyConfig) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame], pd.Series, str, dict[str, Any]]:
    operational_symbols, universe_summary = _load_universe(config.universe_path)
    benchmarks = {
        symbol: _load_symbol_frame(config.cache_dir, symbol, config.start_date, config.end_date)
        for symbol in BENCHMARK_SYMBOLS
    }
    frames = {
        symbol: _load_symbol_frame(config.cache_dir, symbol, config.start_date, config.end_date)
        for symbol in operational_symbols
    }
    if any(FAKE_HOLIDAY_BAR in set(frame["date"]) for frame in [*frames.values(), *benchmarks.values()]):
        raise ValueError(f"fake holiday bar {FAKE_HOLIDAY_BAR} present")
    regime, regime_symbol = _regime_series(benchmarks)
    return frames, benchmarks, regime, regime_symbol, universe_summary


def _split_metrics(trades: pd.DataFrame, config: AutopsyConfig) -> dict[str, Any]:
    is_trades = trades[trades["signal_date"] <= config.is_end_date].copy()
    oos_trades = trades[trades["signal_date"] >= config.oos_start_date].copy()
    return {
        "full": _metric_block(trades, "net_return_x2_pct"),
        "IS": _metric_block(is_trades, "net_return_x2_pct"),
        "OOS": _metric_block(oos_trades, "net_return_x2_pct"),
        "trades_total": int(len(trades)),
        "trades_OOS": int(len(oos_trades)),
        "symbols_OOS": int(oos_trades["symbol"].nunique()) if not oos_trades.empty else 0,
        "top_3_contribution_pct": _top_n_symbol_contribution(oos_trades, 3),
    }


def _top_n_symbol_contribution(trades: pd.DataFrame, n: int) -> float | None:
    if trades.empty:
        return None
    by_symbol = trades.groupby("symbol")["net_return_x2_pct"].sum().sort_values(ascending=False)
    positive_total = float(by_symbol.clip(lower=0).sum())
    return _safe_div(float(by_symbol.clip(lower=0).head(n).sum()), positive_total)


def placebo_oos_audit(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    config: AutopsyConfig,
    base_trades: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base = _split_metrics(base_trades, config)
    base_oos = base["OOS"]
    for shift in (0, 1, 2, 3, 5, 10):
        trades = base_trades if shift == 0 else generate_trades(frames, regime, config.backtest_config(), signal_shift=shift)
        metrics = _split_metrics(trades, config)
        oos = metrics["OOS"]
        rows.append(
            {
                "variant": "DSS_BO_001_BASE" if shift == 0 else f"PLACEBO_SHIFT_PLUS_{shift}",
                "signal_shift_days": shift,
                "trades_total": metrics["trades_total"],
                "trades_OOS": metrics["trades_OOS"],
                "symbols_OOS": metrics["symbols_OOS"],
                "expectancy_net_x2_OOS_pct": oos["expectancy_pct"],
                "profit_factor_net_x2_OOS": oos["profit_factor"],
                "top_3_contribution_pct": metrics["top_3_contribution_pct"],
                "base_edge_minus_placebo_edge": None if shift == 0 or oos["expectancy_pct"] is None else base_oos["expectancy_pct"] - oos["expectancy_pct"],
                "base_pf_minus_placebo_pf": None if shift == 0 or oos["profit_factor"] is None else base_oos["profit_factor"] - oos["profit_factor"],
            }
        )
    table = pd.DataFrame(rows)
    placebo = table[table["signal_shift_days"] > 0]
    base_edge = float(base_oos["expectancy_pct"] or 0.0)
    base_pf = float(base_oos["profit_factor"] or 0.0)
    better_count = int(((placebo["expectancy_net_x2_OOS_pct"] >= base_edge) | (placebo["profit_factor_net_x2_OOS"] >= base_pf)).sum())
    positive_count = int((placebo["expectancy_net_x2_OOS_pct"] > 0).sum())
    decision = (
        "PLACEBO_FAIL"
        if better_count >= 2
        else "PLACEBO_TIMING_WINDOW_WARNING"
        if positive_count >= 3
        else "PLACEBO_SPECIFICITY_PASS"
    )
    return table, {
        "decision": decision,
        "base_oos_expectancy_pct": base_oos["expectancy_pct"],
        "base_oos_profit_factor": base_oos["profit_factor"],
        "positive_placebo_count": positive_count,
        "placebos_matching_or_beating_base_count": better_count,
    }


def _condition(row: pd.Series, market_ok: bool, variant: str) -> bool:
    trend = bool(row["close"] > row["sma50"] and (row["close"] > row["sma200"] or row["sma50"] > row["sma200"]))
    contraction = bool(row["atr14_pct_t_minus_1"] <= row["atr14_pct_p40_120_t_minus_1"])
    breakout = bool(row["close"] > row["prior_high20"])
    if variant == "TREND_ONLY":
        return market_ok and trend
    if variant == "BREAKOUT_ONLY":
        return market_ok and trend and breakout
    if variant == "CONTRACTION_ONLY":
        return market_ok and trend and contraction
    if variant == "DSS_BO_001_BASE":
        return market_ok and trend and contraction and breakout
    raise ValueError(f"unknown baseline variant: {variant}")


def _trade_from_signal(symbol: str, df: pd.DataFrame, signal_idx: int, config: AutopsyConfig) -> dict[str, Any] | None:
    entry_idx = signal_idx + 1
    exit_idx = min(entry_idx + config.holding_days, len(df) - 1)
    if entry_idx >= len(df) or exit_idx <= entry_idx:
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
        "holding_days": int(exit_idx - entry_idx),
        "gross_return_pct": gross * 100.0,
        "net_return_x1_pct": (gross - config.cost_bps_x1 / 10000.0) * 100.0,
        "net_return_x2_pct": (gross - config.cost_bps_x2 / 10000.0) * 100.0,
        "net_return_x3_pct": (gross - config.cost_bps_x3 / 10000.0) * 100.0,
        "entry_model": "next_open",
        "exit_model": f"time_stop_{config.holding_days}_sessions_close",
    }


def _candidate_trades(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    config: AutopsyConfig,
    variant: str,
    sampler: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
) -> pd.DataFrame:
    trades: list[dict[str, Any]] = []
    for symbol, raw in frames.items():
        df = _add_indicators(raw)
        symbol_regime = regime.reindex(df["date"]).fillna(False).to_numpy()
        candidates: list[int] = []
        for idx in range(len(df) - 1):
            if _condition(df.iloc[idx], bool(symbol_regime[idx]), variant):
                candidates.append(idx)
        if sampler is not None and candidates:
            candidate_df = pd.DataFrame({"signal_idx": candidates, "signal_date": df.iloc[candidates]["date"].to_list()})
            candidates = sampler(candidate_df)["signal_idx"].astype(int).to_list()
        last_exit_idx = -1
        for idx in candidates:
            if idx <= last_exit_idx:
                continue
            trade = _trade_from_signal(symbol, df, idx, config)
            if trade is None:
                continue
            last_exit_idx = idx + config.holding_days + 1
            trades.append(trade)
    if not trades:
        return pd.DataFrame(columns=generate_trades(frames, regime, config.backtest_config()).columns)
    out = pd.DataFrame(trades).sort_values(["entry_date", "symbol"]).reset_index(drop=True)
    out["trade_id"] = [f"{variant}-{idx + 1:05d}" for idx in range(len(out))]
    return out


def matched_baseline_audit(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    config: AutopsyConfig,
    base_trades: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    base_counts = (
        base_trades.assign(year=pd.to_datetime(base_trades["signal_date"]).dt.year)
        .groupby(["symbol", "year"])
        .size()
        .to_dict()
    )

    def matched_sampler(candidates: pd.DataFrame) -> pd.DataFrame:
        if candidates.empty:
            return candidates
        local = candidates.copy()
        local["year"] = pd.to_datetime(local["signal_date"]).dt.year
        samples = []
        for (symbol_year, group) in local.groupby("year"):
            count = sum(v for (symbol, year), v in base_counts.items() if year == symbol_year)
            take = min(max(count // max(len(frames), 1), 1), len(group))
            samples.append(group.iloc[:: max(len(group) // take, 1)].head(take))
        return pd.concat(samples) if samples else candidates.head(0)

    rng = random.Random(RANDOM_SEED)

    def random_sampler(candidates: pd.DataFrame) -> pd.DataFrame:
        take = min(len(candidates), max(1, int(len(base_trades) / max(len(frames), 1))))
        indices = sorted(rng.sample(list(candidates.index), take))
        return candidates.loc[indices]

    rows = []
    for variant, sampler in (
        ("DSS_BO_001_BASE", None),
        ("TREND_ONLY", matched_sampler),
        ("BREAKOUT_ONLY", matched_sampler),
        ("CONTRACTION_ONLY", matched_sampler),
        ("RANDOM_MATCHED", random_sampler),
    ):
        trades = base_trades if variant == "DSS_BO_001_BASE" else _candidate_trades(frames, regime, config, "TREND_ONLY" if variant == "RANDOM_MATCHED" else variant, sampler)
        metrics = _split_metrics(trades, config)
        oos = metrics["OOS"]
        last_12 = _metric_block(trades[trades["signal_date"] >= "2025-07-02"], "net_return_x2_pct")
        last_24 = _metric_block(trades[trades["signal_date"] >= "2024-07-02"], "net_return_x2_pct")
        rows.append(
            {
                "variant": variant,
                "trades_OOS": metrics["trades_OOS"],
                "symbols_OOS": metrics["symbols_OOS"],
                "expectancy_net_x2_OOS_pct": oos["expectancy_pct"],
                "profit_factor_net_x2_OOS": oos["profit_factor"],
                "last_12_expectancy_pct": last_12["expectancy_pct"],
                "last_24_expectancy_pct": last_24["expectancy_pct"],
                "top_3_contribution_pct": metrics["top_3_contribution_pct"],
            }
        )
    table = pd.DataFrame(rows)
    base_edge = float(table.loc[table["variant"] == "DSS_BO_001_BASE", "expectancy_net_x2_OOS_pct"].iloc[0])
    best_simple = table[table["variant"] != "DSS_BO_001_BASE"]["expectancy_net_x2_OOS_pct"].max()
    decision = "BASELINE_FAIL" if best_simple >= base_edge else "BASELINE_WARNING" if best_simple >= base_edge * 0.8 else "BASELINE_PASS"
    return table, {"decision": decision, "base_oos_expectancy_pct": base_edge, "best_baseline_oos_expectancy_pct": float(best_simple)}


def return_decomposition(frames: dict[str, pd.DataFrame], base_trades: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    columns = [
        "trade_id",
        "symbol",
        "signal_date",
        "entry_date",
        "signal_close_to_next_open_pct",
        "next_open_to_close_day1_pct",
        "day1_to_day3_pct",
        "day3_to_day5_pct",
        "day5_to_day10_pct",
        "mae_pct",
        "mfe_pct",
        "net_return_x2_pct",
    ]
    indexed = {symbol: frame.reset_index(drop=True) for symbol, frame in frames.items()}
    for trade in base_trades.to_dict("records"):
        df = indexed[trade["symbol"]]
        entry_matches = df.index[df["date"] == trade["entry_date"]].to_list()
        signal_matches = df.index[df["date"] == trade["signal_date"]].to_list()
        if not entry_matches or not signal_matches:
            continue
        entry_idx = entry_matches[0]
        signal_idx = signal_matches[0]
        exit_idx = min(entry_idx + int(trade["holding_days"]), len(df) - 1)
        entry_open = float(df.iloc[entry_idx]["open"])

        def close_at(offset: int) -> float:
            return float(df.iloc[min(entry_idx + offset, exit_idx)]["close"])

        lows = df.iloc[entry_idx : exit_idx + 1]["low"].astype(float)
        highs = df.iloc[entry_idx : exit_idx + 1]["high"].astype(float)
        rows.append(
            {
                "trade_id": trade["trade_id"],
                "symbol": trade["symbol"],
                "signal_date": trade["signal_date"],
                "entry_date": trade["entry_date"],
                "signal_close_to_next_open_pct": (entry_open / float(df.iloc[signal_idx]["close"]) - 1.0) * 100.0,
                "next_open_to_close_day1_pct": (close_at(0) / entry_open - 1.0) * 100.0,
                "day1_to_day3_pct": (close_at(3) / close_at(0) - 1.0) * 100.0,
                "day3_to_day5_pct": (close_at(5) / close_at(3) - 1.0) * 100.0,
                "day5_to_day10_pct": (close_at(10) / close_at(5) - 1.0) * 100.0,
                "mae_pct": (float(lows.min()) / entry_open - 1.0) * 100.0,
                "mfe_pct": (float(highs.max()) / entry_open - 1.0) * 100.0,
                "net_return_x2_pct": trade["net_return_x2_pct"],
            }
        )
    table = pd.DataFrame(rows, columns=columns)
    means = {column: float(table[column].mean()) for column in table.columns if column.endswith("_pct")} if not table.empty else {}
    early = (means.get("next_open_to_close_day1_pct", 0.0) or 0.0) + (means.get("day1_to_day3_pct", 0.0) or 0.0)
    late = (means.get("day3_to_day5_pct", 0.0) or 0.0) + (means.get("day5_to_day10_pct", 0.0) or 0.0)
    decision = "TIMING_PASS" if early > 0 and late > 0 else "TIMING_WARNING" if (early + late) > 0 else "TIMING_FAIL"
    return table, {"decision": decision, "mean_segments_pct": means, "early_day1_to_day3_pct": early, "late_day3_to_day10_pct": late}


def stability_audit(base_trades: pd.DataFrame, config: AutopsyConfig) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    oos = base_trades[base_trades["signal_date"] >= config.oos_start_date].copy()
    oos["year"] = pd.to_datetime(oos["signal_date"]).dt.year
    oos["quarter"] = pd.to_datetime(oos["signal_date"]).dt.to_period("Q").astype(str)
    by_period = (
        oos.groupby("quarter")
        .agg(trades=("trade_id", "count"), expectancy_pct=("net_return_x2_pct", "mean"), net_sum_pct=("net_return_x2_pct", "sum"))
        .reset_index()
    )
    by_symbol = (
        oos.groupby("symbol")
        .agg(trades=("trade_id", "count"), expectancy_pct=("net_return_x2_pct", "mean"), net_sum_pct=("net_return_x2_pct", "sum"))
        .reset_index()
        .sort_values("net_sum_pct", ascending=False)
    )

    def excl(symbols: list[str] | None = None, top_trades: int = 0) -> dict[str, Any]:
        sample = oos.copy()
        if symbols:
            sample = sample[~sample["symbol"].isin(symbols)]
        if top_trades:
            top_index = pd.to_numeric(sample["net_return_x2_pct"], errors="coerce").nlargest(top_trades).index
            sample = sample.drop(top_index)
        return _metric_block(sample, "net_return_x2_pct")

    top_symbols = by_symbol["symbol"].head(3).to_list()
    summary = {
        "decision": "STABILITY_PASS",
        "oos": _metric_block(oos, "net_return_x2_pct"),
        "negative_oos_quarters": int((by_period["net_sum_pct"] < 0).sum()) if not by_period.empty else 0,
        "exclude_top_1_symbol": excl(top_symbols[:1]),
        "exclude_top_3_symbols": excl(top_symbols[:3]),
        "exclude_top_5_trades": excl(top_trades=5),
        "sector_audit": "OMITTED_NO_SECTOR_FIELD_IN_PILOT_UNIVERSE",
    }
    if summary["exclude_top_3_symbols"]["expectancy_pct"] is not None and summary["exclude_top_3_symbols"]["expectancy_pct"] <= 0:
        summary["decision"] = "STABILITY_FAIL"
    elif summary["negative_oos_quarters"] >= 3:
        summary["decision"] = "STABILITY_WARNING"
    return by_period, by_symbol, summary


def _final_decision(placebo: str, baseline: str, timing: str, stability: str) -> str:
    if placebo == "PLACEBO_FAIL":
        return "DSS_BO_001_PLACEBO_FAIL"
    if baseline == "BASELINE_FAIL":
        return "DSS_BO_001_BASELINE_EXPLAINED_FAIL"
    if stability == "STABILITY_FAIL":
        return "DSS_BO_001_STABILITY_FAIL"
    if placebo == "PLACEBO_SPECIFICITY_PASS" and baseline == "BASELINE_PASS" and timing == "TIMING_PASS" and stability == "STABILITY_PASS":
        return "DSS_BO_001_SPECIFICITY_PASS"
    if timing in {"TIMING_PASS", "TIMING_WARNING"} and stability in {"STABILITY_PASS", "STABILITY_WARNING"}:
        return "DSS_BO_001_TIMING_WINDOW_WARNING"
    return "DSS_BO_001_INCONCLUSIVE_NEEDS_RESEARCH_150"


def run_dss_004c_autopsy(config: AutopsyConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    frames, _benchmarks, regime, regime_symbol, universe_summary = _load_inputs(config)
    base_trades = generate_trades(frames, regime, config.backtest_config())
    placebo_table, placebo_summary = placebo_oos_audit(frames, regime, config, base_trades)
    baselines_table, baselines_summary = matched_baseline_audit(frames, regime, config, base_trades)
    decomposition_table, timing_summary = return_decomposition(frames, base_trades)
    period_table, symbol_table, stability_summary = stability_audit(base_trades, config)
    decision = _final_decision(
        placebo_summary["decision"],
        baselines_summary["decision"],
        timing_summary["decision"],
        stability_summary["decision"],
    )
    safety = {
        "orders": False,
        "paper_execution": False,
        "live": False,
        "signals_operational": False,
        "preview_operational": False,
        "cron": False,
        "env_modified": False,
    }
    summary = {
        "schema_version": DSS_004C_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "pattern_id": "DSS-BO-001",
        "regime_symbol": regime_symbol,
        "universe_summary": universe_summary,
        "base": _split_metrics(base_trades, config),
        "partial_decisions": {
            "placebo": placebo_summary["decision"],
            "baseline": baselines_summary["decision"],
            "timing": timing_summary["decision"],
            "stability": stability_summary["decision"],
        },
        "decision": decision,
        "next_phase": "DSS-003E research-150 confirmation before DSS-005" if decision == "DSS_BO_001_TIMING_WINDOW_WARNING" else "review Director criteria",
        "safety": safety,
    }
    placebo_table.to_csv(config.output_dir / "dss_004c_placebo_oos.csv", index=False)
    baselines_table.to_csv(config.output_dir / "dss_004c_matched_baselines.csv", index=False)
    decomposition_table.to_csv(config.output_dir / "dss_004c_return_decomposition.csv", index=False)
    period_table.to_csv(config.output_dir / "dss_004c_stability_by_period.csv", index=False)
    symbol_table.to_csv(config.output_dir / "dss_004c_stability_by_symbol.csv", index=False)
    _write_json(config.output_dir / "dss_004c_placebo_oos_summary.json", placebo_summary)
    _write_json(config.output_dir / "dss_004c_matched_baselines_summary.json", baselines_summary)
    _write_json(config.output_dir / "dss_004c_timing_window_summary.json", timing_summary)
    _write_json(config.output_dir / "dss_004c_stability_summary.json", stability_summary)
    _write_json(config.output_dir / "dss_004c_decision.json", summary)
    return {
        "base_trades": base_trades,
        "placebo": {"table": placebo_table, "summary": placebo_summary},
        "baselines": {"table": baselines_table, "summary": baselines_summary},
        "timing": {"table": decomposition_table, "summary": timing_summary},
        "stability": {"by_period": period_table, "by_symbol": symbol_table, "summary": stability_summary},
        "decision": summary,
    }
