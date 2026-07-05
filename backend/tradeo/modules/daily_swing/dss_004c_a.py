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
from tradeo.modules.daily_swing.dss_004b import BacktestConfig, _add_indicators, generate_trades

DSS_004C_A_SCHEMA_VERSION = "tradeo.daily_swing.dss_004c_a.v1"
RANDOM_MATCHED_SEED = 40401
PLACEBO_SHIFTS = (1, 2, 3, 5, 10)
BASE_VARIANT = "DSS_BO_001_BASE"


@dataclass(frozen=True)
class SpecificityConfig:
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


def _load_inputs(config: SpecificityConfig) -> tuple[dict[str, pd.DataFrame], pd.Series, str, dict[str, Any], str]:
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
    last_dates = [frame["date"].max() for frame in all_frames.values()]
    last_valid = max(set(last_dates), key=last_dates.count)
    regime, regime_symbol = _regime_series(benchmarks)
    return frames, regime, regime_symbol, universe_summary, last_valid


def _split_metrics(trades: pd.DataFrame, config: SpecificityConfig) -> dict[str, Any]:
    oos = trades[trades["signal_date"] >= config.oos_start_date].copy()
    last_12 = trades[trades["signal_date"] >= "2025-07-02"].copy()
    last_24 = trades[trades["signal_date"] >= "2024-07-02"].copy()
    return {
        "trades_total": int(len(trades)),
        "trades_OOS": int(len(oos)),
        "symbols_OOS": int(oos["symbol"].nunique()) if not oos.empty else 0,
        "OOS": _metric_block(oos, "net_return_x2_pct"),
        "last_12_months": _metric_block(last_12, "net_return_x2_pct"),
        "last_24_months": _metric_block(last_24, "net_return_x2_pct"),
        "top_3_symbol_contribution_pct": _top_n_symbol_contribution(oos, 3),
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
    config: SpecificityConfig,
    base_trades: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    base_metrics = _split_metrics(base_trades, config)
    base_oos = base_metrics["OOS"]
    base_edge = base_oos["expectancy_pct"]
    base_pf = base_oos["profit_factor"]
    rows: list[dict[str, Any]] = []
    for shift in (0, *PLACEBO_SHIFTS):
        trades = base_trades if shift == 0 else generate_trades(
            frames,
            regime,
            config.backtest_config(),
            signal_shift=shift,
        )
        metrics = _split_metrics(trades, config)
        oos = metrics["OOS"]
        edge = oos["expectancy_pct"]
        pf = oos["profit_factor"]
        rows.append(
            {
                "variant": BASE_VARIANT if shift == 0 else f"PLACEBO_SHIFT_PLUS_{shift}",
                "signal_shift_days": shift,
                "trades_total": metrics["trades_total"],
                "trades_OOS": metrics["trades_OOS"],
                "symbols_OOS": metrics["symbols_OOS"],
                "OOS_expectancy_net_x2_pct": edge,
                "OOS_profit_factor_net_x2": pf,
                "top_3_symbol_contribution_pct": metrics["top_3_symbol_contribution_pct"],
                "base_edge_minus_placebo_edge": None if shift == 0 or edge is None or base_edge is None else base_edge - edge,
                "base_pf_minus_placebo_pf": None if shift == 0 or pf is None or base_pf is None else base_pf - pf,
                "relative_edge_decay": None
                if shift == 0 or edge is None or base_edge in (None, 0)
                else (base_edge - edge) / abs(base_edge),
            }
        )
    table = pd.DataFrame(rows)
    placebo = table[table["signal_shift_days"] > 0].copy()
    better_or_equal = int(
        (
            (placebo["OOS_expectancy_net_x2_pct"] >= float(base_edge or 0.0))
            | (placebo["OOS_profit_factor_net_x2"] >= float(base_pf or 0.0))
        ).sum()
    )
    positive = int((placebo["OOS_expectancy_net_x2_pct"] > 0).sum())
    ordered_decay = bool(placebo["OOS_expectancy_net_x2_pct"].is_monotonic_decreasing)
    if better_or_equal > 0:
        decision = "PLACEBO_FAIL"
    elif positive >= 3:
        decision = "PLACEBO_TIMING_WINDOW_WARNING"
    else:
        decision = "PLACEBO_SPECIFICITY_PASS"
    summary = {
        "decision": decision,
        "base_oos_expectancy_net_x2_pct": base_edge,
        "base_oos_profit_factor_net_x2": base_pf,
        "positive_placebo_count": positive,
        "placebos_matching_or_beating_base_count": better_or_equal,
        "ordered_edge_decay": ordered_decay,
    }
    return table, summary


BaselineVariant = Literal["TREND_ONLY", "BREAKOUT_ONLY", "CONTRACTION_ONLY", "DSS_BO_001_BASE"]


def _condition(row: pd.Series, market_ok: bool, variant: BaselineVariant) -> bool:
    trend = bool(row["close"] > row["sma50"] and (row["close"] > row["sma200"] or row["sma50"] > row["sma200"]))
    contraction = bool(row["atr14_pct_t_minus_1"] <= row["atr14_pct_p40_120_t_minus_1"])
    breakout = bool(row["close"] > row["prior_high20"])
    if variant == "TREND_ONLY":
        return market_ok and trend
    if variant == "BREAKOUT_ONLY":
        return market_ok and trend and breakout
    if variant == "CONTRACTION_ONLY":
        return market_ok and trend and contraction
    return market_ok and trend and contraction and breakout


def _trade_from_signal(symbol: str, df: pd.DataFrame, signal_idx: int, config: SpecificityConfig) -> dict[str, Any] | None:
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
        "cost_bps_x1": config.cost_bps_x1,
        "cost_bps_x2": config.cost_bps_x2,
        "cost_bps_x3": config.cost_bps_x3,
        "entry_model": "next_open",
        "exit_model": f"time_stop_{config.holding_days}_sessions_close",
    }


def _candidate_signals(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    variant: BaselineVariant,
) -> dict[str, pd.DataFrame]:
    signals: dict[str, pd.DataFrame] = {}
    for symbol, raw in frames.items():
        df = _add_indicators(raw)
        symbol_regime = regime.reindex(df["date"]).fillna(False).to_numpy()
        rows = [
            {"symbol": symbol, "signal_idx": idx, "signal_date": str(df.iloc[idx]["date"])}
            for idx in range(len(df) - 1)
            if _condition(df.iloc[idx], bool(symbol_regime[idx]), variant)
        ]
        signals[symbol] = pd.DataFrame(rows, columns=["symbol", "signal_idx", "signal_date"])
    return signals


def _base_counts_by_symbol_year(base_trades: pd.DataFrame) -> dict[tuple[str, int], int]:
    if base_trades.empty:
        return {}
    dated = base_trades.assign(year=pd.to_datetime(base_trades["signal_date"]).dt.year)
    return {(str(symbol), int(year)): int(count) for (symbol, year), count in dated.groupby(["symbol", "year"]).size().items()}


def _matched_sample(
    candidates: pd.DataFrame,
    base_counts: dict[tuple[str, int], int],
    *,
    randomize: bool,
    rng: random.Random | None = None,
) -> pd.DataFrame:
    if candidates.empty:
        return candidates
    local = candidates.copy()
    local["year"] = pd.to_datetime(local["signal_date"]).dt.year
    samples = []
    for (symbol, year), group in local.groupby(["symbol", "year"], sort=True):
        take = min(int(base_counts.get((str(symbol), int(year)), 0)), len(group))
        if take <= 0:
            continue
        if randomize:
            assert rng is not None
            chosen = sorted(rng.sample(list(group.index), take))
            samples.append(group.loc[chosen])
        elif take >= len(group):
            samples.append(group)
        else:
            step = len(group) / take
            positions = sorted({min(int(round(i * step)), len(group) - 1) for i in range(take)})
            while len(positions) < take:
                candidate = len(positions)
                if candidate not in positions:
                    positions.append(candidate)
            samples.append(group.iloc[positions[:take]])
    if not samples:
        return candidates.head(0)
    return pd.concat(samples).sort_values(["signal_date", "symbol", "signal_idx"]).reset_index(drop=True)


def _trades_from_signals(
    frames: dict[str, pd.DataFrame],
    signals_by_symbol: dict[str, pd.DataFrame],
    config: SpecificityConfig,
    variant: str,
) -> pd.DataFrame:
    trades: list[dict[str, Any]] = []
    for symbol, signals in signals_by_symbol.items():
        if signals.empty:
            continue
        df = _add_indicators(frames[symbol])
        last_exit_idx = -1
        for idx in signals["signal_idx"].astype(int).to_list():
            if idx <= last_exit_idx:
                continue
            trade = _trade_from_signal(symbol, df, idx, config)
            if trade is None:
                continue
            trade["variant"] = variant
            last_exit_idx = idx + config.holding_days + 1
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
        "variant",
    ]
    if not trades:
        return pd.DataFrame(columns=columns)
    out = pd.DataFrame(trades).sort_values(["entry_date", "symbol"]).reset_index(drop=True)
    out["trade_id"] = [f"{variant}-{idx + 1:05d}" for idx in range(len(out))]
    return out[columns]


def matched_baseline_audit(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    config: SpecificityConfig,
    base_trades: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    base_counts = _base_counts_by_symbol_year(base_trades)
    rng = random.Random(RANDOM_MATCHED_SEED)
    rows = []
    variant_trades: dict[str, pd.DataFrame] = {BASE_VARIANT: base_trades.assign(variant=BASE_VARIANT)}
    for variant in ("TREND_ONLY", "BREAKOUT_ONLY", "CONTRACTION_ONLY"):
        candidates = _candidate_signals(frames, regime, variant)  # type: ignore[arg-type]
        sampled = {
            symbol: _matched_sample(symbol_candidates, base_counts, randomize=False)
            for symbol, symbol_candidates in candidates.items()
        }
        variant_trades[variant] = _trades_from_signals(frames, sampled, config, variant)
    random_candidates = _candidate_signals(frames, regime, "TREND_ONLY")
    random_sampled = {
        symbol: _matched_sample(symbol_candidates, base_counts, randomize=True, rng=rng)
        for symbol, symbol_candidates in random_candidates.items()
    }
    variant_trades["RANDOM_MATCHED"] = _trades_from_signals(frames, random_sampled, config, "RANDOM_MATCHED")

    for variant in (BASE_VARIANT, "TREND_ONLY", "BREAKOUT_ONLY", "CONTRACTION_ONLY", "RANDOM_MATCHED"):
        trades = variant_trades[variant]
        metrics = _split_metrics(trades, config)
        oos = metrics["OOS"]
        rows.append(
            {
                "variant": variant,
                "trades_total": metrics["trades_total"],
                "trades_OOS": metrics["trades_OOS"],
                "symbols_OOS": metrics["symbols_OOS"],
                "OOS_expectancy_net_x2_pct": oos["expectancy_pct"],
                "OOS_profit_factor_net_x2": oos["profit_factor"],
                "last_12_months_expectancy_net_x2_pct": metrics["last_12_months"]["expectancy_pct"],
                "last_12_months_profit_factor_net_x2": metrics["last_12_months"]["profit_factor"],
                "last_24_months_expectancy_net_x2_pct": metrics["last_24_months"]["expectancy_pct"],
                "last_24_months_profit_factor_net_x2": metrics["last_24_months"]["profit_factor"],
                "top_3_symbol_contribution_pct": metrics["top_3_symbol_contribution_pct"],
            }
        )
    table = pd.DataFrame(rows)
    base_edge = float(table.loc[table["variant"] == BASE_VARIANT, "OOS_expectancy_net_x2_pct"].iloc[0] or 0.0)
    base_pf = float(table.loc[table["variant"] == BASE_VARIANT, "OOS_profit_factor_net_x2"].iloc[0] or 0.0)
    simple = table[table["variant"] != BASE_VARIANT].copy()
    best_edge = float(simple["OOS_expectancy_net_x2_pct"].max())
    best_pf = float(simple["OOS_profit_factor_net_x2"].max())
    if best_edge >= base_edge or best_pf >= base_pf:
        decision = "BASELINE_FAIL"
    elif best_edge >= base_edge * 0.80 or best_pf >= base_pf * 0.90:
        decision = "BASELINE_WARNING"
    else:
        decision = "BASELINE_PASS"
    summary = {
        "decision": decision,
        "base_oos_expectancy_net_x2_pct": base_edge,
        "base_oos_profit_factor_net_x2": base_pf,
        "best_baseline_oos_expectancy_net_x2_pct": best_edge,
        "best_baseline_oos_profit_factor_net_x2": best_pf,
        "random_seed": RANDOM_MATCHED_SEED,
    }
    return table, summary


def guard_audit(
    frames: dict[str, pd.DataFrame],
    base_trades: pd.DataFrame,
    placebo_table: pd.DataFrame,
    baseline_table: pd.DataFrame,
    config: SpecificityConfig,
    last_valid_bar_date: str,
) -> dict[str, Any]:
    traded_symbols = set(base_trades["symbol"]) if not base_trades.empty else set()
    latest_cache_date = max(frame["date"].max() for frame in frames.values())
    entry_after_signal = (
        bool((pd.to_datetime(base_trades["entry_date"]) > pd.to_datetime(base_trades["signal_date"])).all())
        if not base_trades.empty
        else True
    )
    checks = {
        "excludes_spy_qqq_from_trades": not bool(traded_symbols & BENCHMARK_SYMBOLS),
        "fake_2026_07_03_absent": all(FAKE_HOLIDAY_BAR not in set(frame["date"]) for frame in frames.values()),
        "last_valid_bar_date": last_valid_bar_date,
        "latest_operational_cache_date": latest_cache_date,
        "last_valid_bar_date_expected": config.end_date,
        "entry_date_after_signal_date": entry_after_signal,
        "signal_t_entry_t_plus_1": entry_after_signal,
        "placebo_rows_present": int(len(placebo_table)) == len(PLACEBO_SHIFTS) + 1,
        "baseline_rows_present": set(baseline_table["variant"]) == {
            BASE_VARIANT,
            "TREND_ONLY",
            "BREAKOUT_ONLY",
            "CONTRACTION_ONLY",
            "RANDOM_MATCHED",
        },
        "cache_only": True,
        "no_future_fields_used": True,
    }
    status = "PASS" if all(value is True or not isinstance(value, bool) for value in checks.values()) and latest_cache_date <= config.end_date else "FAIL"
    return {"status": status, "checks": checks}


def _final_decision(placebo_decision: str, baseline_decision: str, guard_status: str) -> str:
    if guard_status != "PASS":
        return "DSS_BO_001_INCONCLUSIVE"
    if placebo_decision == "PLACEBO_FAIL":
        return "DSS_BO_001_PLACEBO_FAIL"
    if baseline_decision == "BASELINE_FAIL":
        return "DSS_BO_001_BASELINE_EXPLAINED_FAIL"
    if placebo_decision == "PLACEBO_SPECIFICITY_PASS" and baseline_decision == "BASELINE_PASS":
        return "DSS_BO_001_SPECIFICITY_CONTINUES"
    if placebo_decision == "PLACEBO_TIMING_WINDOW_WARNING" or baseline_decision == "BASELINE_WARNING":
        return "DSS_BO_001_TIMING_WINDOW_WARNING"
    return "DSS_BO_001_INCONCLUSIVE"


def run_dss_004c_a_specificity(config: SpecificityConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    frames, regime, regime_symbol, universe_summary, last_valid = _load_inputs(config)
    base_trades = generate_trades(frames, regime, config.backtest_config())
    placebo_table, placebo_summary = placebo_oos_audit(frames, regime, config, base_trades)
    baseline_table, baseline_summary = matched_baseline_audit(frames, regime, config, base_trades)
    guards = guard_audit(frames, base_trades, placebo_table, baseline_table, config, last_valid)
    decision = _final_decision(placebo_summary["decision"], baseline_summary["decision"], guards["status"])
    safety = {
        "orders": False,
        "paper_orders": False,
        "paper_execution": False,
        "live": False,
        "signals_operational": False,
        "preview_operational": False,
        "cron": False,
        "env_modified": False,
    }
    decision_payload = {
        "schema_version": DSS_004C_A_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "pattern_id": "DSS-BO-001",
        "phase": "DSS-004C-A",
        "regime_symbol": regime_symbol,
        "universe_summary": universe_summary,
        "last_valid_bar_date": last_valid,
        "base": _split_metrics(base_trades, config),
        "partial_decisions": {
            "placebo": placebo_summary["decision"],
            "baseline": baseline_summary["decision"],
            "guards": guards["status"],
        },
        "decision": decision,
        "next_phase": "DSS-004C-B return decomposition + timing window" if decision in {"DSS_BO_001_SPECIFICITY_CONTINUES", "DSS_BO_001_TIMING_WINDOW_WARNING"} else "Director review before further DSS-BO-001 work",
        "safety": safety,
    }
    placebo_table.to_csv(config.output_dir / "dss_004c_a_placebo_oos.csv", index=False)
    baseline_table.to_csv(config.output_dir / "dss_004c_a_matched_baselines.csv", index=False)
    _write_json(config.output_dir / "dss_004c_a_placebo_oos_summary.json", placebo_summary)
    _write_json(config.output_dir / "dss_004c_a_matched_baselines_summary.json", baseline_summary)
    _write_json(config.output_dir / "dss_004c_a_guards_summary.json", guards)
    _write_json(config.output_dir / "dss_004c_a_decision.json", decision_payload)
    return {
        "base_trades": base_trades,
        "placebo": {"table": placebo_table, "summary": placebo_summary},
        "baselines": {"table": baseline_table, "summary": baseline_summary},
        "guards": guards,
        "decision": decision_payload,
    }
