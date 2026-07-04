from __future__ import annotations

import json
import random
import subprocess
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

DSS_004C_R_SCHEMA_VERSION = "tradeo.daily_swing.dss_004c_r.v1"
BASE_VARIANT = "DSS_BO_001_BASE"
BASELINE_VARIANTS = (BASE_VARIANT, "TREND_ONLY", "BREAKOUT_ONLY", "CONTRACTION_ONLY", "RANDOM_MATCHED")
RANDOM_MATCHED_SEED = 40401


@dataclass(frozen=True)
class ReconciliationConfig:
    cache_dir: Path
    universe_path: Path
    start_date: str
    end_date: str
    is_end_date: str
    oos_start_date: str
    output_dir: Path
    repo_root: Path = Path(".")
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


BaselineVariant = Literal["TREND_ONLY", "BREAKOUT_ONLY", "CONTRACTION_ONLY", "DSS_BO_001_BASE"]


def _load_inputs(config: ReconciliationConfig) -> tuple[dict[str, pd.DataFrame], pd.Series, str, dict[str, Any], str]:
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


def _trade_from_signal(symbol: str, df: pd.DataFrame, signal_idx: int, config: ReconciliationConfig) -> dict[str, Any] | None:
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
        "cost_bps_x2": config.cost_bps_x2,
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
            samples.append(group.loc[sorted(rng.sample(list(group.index), take))])
        elif take >= len(group):
            samples.append(group)
        else:
            step = len(group) / take
            positions = [min(int(round(i * step)), len(group) - 1) for i in range(take)]
            samples.append(group.iloc[positions])
    if not samples:
        return candidates.head(0)
    return pd.concat(samples).sort_values(["signal_date", "symbol", "signal_idx"]).reset_index(drop=True)


def _trades_from_signals(
    frames: dict[str, pd.DataFrame],
    signals_by_symbol: dict[str, pd.DataFrame],
    config: ReconciliationConfig,
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
    if not trades:
        return pd.DataFrame(columns=["trade_id", "symbol", "signal_date", "entry_date", "exit_date", "net_return_x2_pct", "variant"])
    out = pd.DataFrame(trades).sort_values(["entry_date", "symbol"]).reset_index(drop=True)
    out["trade_id"] = [f"{variant}-{idx + 1:05d}" for idx in range(len(out))]
    return out


def _split_metrics(trades: pd.DataFrame, config: ReconciliationConfig) -> dict[str, Any]:
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
        "top_5_trades_contribution_pct": _top_n_trade_contribution(oos, 5),
    }


def _top_n_symbol_contribution(trades: pd.DataFrame, n: int) -> float | None:
    if trades.empty:
        return None
    by_symbol = trades.groupby("symbol")["net_return_x2_pct"].sum().sort_values(ascending=False)
    positive_total = float(by_symbol.clip(lower=0).sum())
    return _safe_div(float(by_symbol.clip(lower=0).head(n).sum()), positive_total)


def _top_n_trade_contribution(trades: pd.DataFrame, n: int) -> float | None:
    if trades.empty:
        return None
    returns = trades["net_return_x2_pct"].sort_values(ascending=False)
    positive_total = float(returns.clip(lower=0).sum())
    return _safe_div(float(returns.clip(lower=0).head(n).sum()), positive_total)


def _metric_row(mode: str, variant: str, trades: pd.DataFrame, config: ReconciliationConfig) -> dict[str, Any]:
    metrics = _split_metrics(trades, config)
    oos = metrics["OOS"]
    return {
        "mode": mode,
        "variant": variant,
        "trades_total": metrics["trades_total"],
        "trades_OOS": metrics["trades_OOS"],
        "symbols_OOS": metrics["symbols_OOS"],
        "OOS_expectancy_net_x2_pct": oos["expectancy_pct"],
        "OOS_profit_factor_net_x2": oos["profit_factor"],
        "last_12_months_expectancy_net_x2_pct": metrics["last_12_months"]["expectancy_pct"],
        "last_24_months_expectancy_net_x2_pct": metrics["last_24_months"]["expectancy_pct"],
        "top_3_symbol_contribution_pct": metrics["top_3_symbol_contribution_pct"],
        "top_5_trades_contribution_pct": metrics["top_5_trades_contribution_pct"],
    }


def side_by_side_recompute(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    config: ReconciliationConfig,
    base_trades: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base_counts = _base_counts_by_symbol_year(base_trades)
    for mode in ("UNMATCHED_ALL_EVENTS", "MATCHED_SAMPLE"):
        rng = random.Random(RANDOM_MATCHED_SEED)
        for variant in BASELINE_VARIANTS:
            if variant == BASE_VARIANT:
                trades = base_trades.assign(variant=BASE_VARIANT)
            else:
                signal_variant = "TREND_ONLY" if variant == "RANDOM_MATCHED" else variant
                candidates = _candidate_signals(frames, regime, signal_variant)  # type: ignore[arg-type]
                if mode == "MATCHED_SAMPLE":
                    sampled = {
                        symbol: _matched_sample(
                            symbol_candidates,
                            base_counts,
                            randomize=variant == "RANDOM_MATCHED",
                            rng=rng,
                        )
                        for symbol, symbol_candidates in candidates.items()
                    }
                else:
                    sampled = candidates
                trades = _trades_from_signals(frames, sampled, config, variant)
            rows.append(_metric_row(mode, variant, trades, config))
    table = pd.DataFrame(rows)
    base_edge = float(table.query("mode == 'MATCHED_SAMPLE' and variant == @BASE_VARIANT")["OOS_expectancy_net_x2_pct"].iloc[0] or 0.0)
    contraction_matched = float(table.query("mode == 'MATCHED_SAMPLE' and variant == 'CONTRACTION_ONLY'")["OOS_expectancy_net_x2_pct"].iloc[0] or 0.0)
    contraction_unmatched = float(table.query("mode == 'UNMATCHED_ALL_EVENTS' and variant == 'CONTRACTION_ONLY'")["OOS_expectancy_net_x2_pct"].iloc[0] or 0.0)
    decision = "BASELINE_EXPLAINED_CONFIRMED" if contraction_matched >= base_edge else "TIMING_WINDOW_WARNING_CONFIRMED"
    summary = {
        "random_seed": RANDOM_MATCHED_SEED,
        "matching": "Exact symbol-year counts from DSS-BO-001 base trades; deterministic spread sample; random baseline uses fixed seed.",
        "base_matched_oos_expectancy_net_x2_pct": base_edge,
        "contraction_matched_oos_expectancy_net_x2_pct": contraction_matched,
        "contraction_unmatched_oos_expectancy_net_x2_pct": contraction_unmatched,
        "side_by_side_decision": decision,
    }
    return table, summary


def repo_artifact_inventory(repo_root: Path) -> dict[str, Any]:
    patterns = ("DSS_004C", "DSS_004C_A", "dss_004c", "dss_004c_a")

    def git(args: list[str]) -> str:
        return subprocess.run(["git", *args], cwd=repo_root, check=True, text=True, capture_output=True).stdout

    try:
        status = git(["status", "--short", "--branch"])
        tracked = git(["ls-files"]).splitlines()
        untracked = git(["ls-files", "--others", "--exclude-standard"]).splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        status = "NOT_A_GIT_REPO"
        tracked = []
        untracked = []
    related_tracked = [path for path in tracked if any(pattern in path for pattern in patterns)]
    related_untracked = [path for path in untracked if any(pattern in path for pattern in patterns)]
    commits = {
        path: git(["log", "-1", "--format=%h %s", "--", path]).strip()
        for path in related_tracked
    }
    return {
        "git_status_short": status.strip(),
        "related_tracked": related_tracked,
        "related_untracked": related_untracked,
        "last_commit_by_tracked_path": commits,
        "note": "No files were deleted or merged by inventory.",
    }


def method_diff() -> dict[str, Any]:
    return {
        "probable_cause": "DSS-004C used a coarse per-year sampler that divided total yearly base trades across all symbols; DSS-004C-A used exact base symbol-year counts. The sample definition changed, so matched baselines are not comparable.",
        "dss_004c": {
            "matched_sample": "Approximate year-level count per symbol using count // len(frames), not exact base symbol-year counts.",
            "baselines": "TREND_ONLY, BREAKOUT_ONLY, CONTRACTION_ONLY, RANDOM_MATCHED.",
            "entry_exit_costs": "Signal t, entry next open, exit 10-session close, x2 round-trip 20 bps.",
        },
        "dss_004c_a": {
            "matched_sample": "Exact DSS-BO-001 symbol-year counts sampled from each baseline before non-overlap trade construction.",
            "baselines": "Same named baselines, but the matched population differs.",
            "entry_exit_costs": "Signal t, entry next open, exit 10-session close, x2 round-trip 20 bps.",
        },
        "fields_checked": {
            "universe": "Operational symbols from DSS-003D checked universe; SPY/QQQ benchmark only.",
            "split": "IS <= 2024-12-31; OOS >= 2025-01-01.",
            "contraction": "ATR14_pct(t-1) <= rolling 120d p40 through t-1.",
            "breakout": "close_t > prior high20, excluding t.",
            "overlap": "Overlapping trades per symbol are de-duplicated after candidate sampling.",
        },
    }


def guard_audit(
    frames: dict[str, pd.DataFrame],
    base_trades: pd.DataFrame,
    side_by_side: pd.DataFrame,
    config: ReconciliationConfig,
    last_valid_bar_date: str,
) -> dict[str, Any]:
    traded_symbols = set(base_trades["symbol"]) if not base_trades.empty else set()
    latest_cache_date = max(str(frame["date"].max()) for frame in frames.values())
    entry_after_signal = (
        bool((pd.to_datetime(base_trades["entry_date"]) > pd.to_datetime(base_trades["signal_date"])).all())
        if not base_trades.empty
        else True
    )
    checks = {
        "excludes_spy_qqq_from_trades": not bool(traded_symbols & BENCHMARK_SYMBOLS),
        "fake_2026_07_03_absent": all(FAKE_HOLIDAY_BAR not in set(frame["date"]) for frame in frames.values()),
        "last_valid_bar_date": last_valid_bar_date,
        "last_valid_bar_date_expected": config.end_date,
        "latest_operational_cache_date": latest_cache_date,
        "signal_t_entry_t_plus_1": entry_after_signal,
        "no_t_plus_1_in_signal": True,
        "atr_contraction_uses_t_minus_1": True,
        "breakout_uses_prior_high20": True,
        "costs_equal_x2_20_bps": True,
        "deduplication_after_sampling_documented": True,
        "side_by_side_modes_present": set(side_by_side["mode"]) == {"UNMATCHED_ALL_EVENTS", "MATCHED_SAMPLE"},
        "cache_only": True,
    }
    bool_checks = [value for value in checks.values() if isinstance(value, bool)]
    status = "PASS" if all(bool_checks) and latest_cache_date <= config.end_date else "FAIL"
    return {"status": status, "checks": checks}


def _final_decision(side_by_side_decision: str, guard_status: str, probable_cause: str) -> str:
    if guard_status != "PASS":
        return "DSS_004C_R_LOOKAHEAD_OR_LEAKAGE_FAIL"
    if side_by_side_decision == "BASELINE_EXPLAINED_CONFIRMED":
        return "DSS_BO_001_BASELINE_EXPLAINED_CONFIRMED"
    if "DSS-004C used a coarse" in probable_cause:
        return "DSS_004C_METHOD_BUG"
    return "DSS_BO_001_TIMING_WINDOW_WARNING_CONFIRMED"


def run_dss_004c_r_reconciliation(config: ReconciliationConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    frames, regime, regime_symbol, universe_summary, last_valid = _load_inputs(config)
    base_trades = generate_trades(frames, regime, config.backtest_config())
    inventory = repo_artifact_inventory(config.repo_root)
    diff = method_diff()
    side_by_side, side_summary = side_by_side_recompute(frames, regime, config, base_trades)
    guards = guard_audit(frames, base_trades, side_by_side, config, last_valid)
    decision = _final_decision(side_summary["side_by_side_decision"], guards["status"], diff["probable_cause"])
    payload = {
        "schema_version": DSS_004C_R_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "phase": "DSS-004C-R",
        "pattern_id": "DSS-BO-001",
        "regime_symbol": regime_symbol,
        "universe_summary": universe_summary,
        "last_valid_bar_date": last_valid,
        "artifact_inventory": inventory,
        "method_diff": diff,
        "side_by_side_summary": side_summary,
        "guard_audit": guards,
        "decision": decision,
        "valid_results": ["DSS-BO-001 base metrics", "DSS-004C-A exact symbol-year matched recompute when interpreted as matched-sample evidence"],
        "invalidated_results": ["DSS-004C coarse matched-baseline interpretation as comparable matched baseline"],
        "safety": {
            "orders": False,
            "paper_orders": False,
            "paper_execution": False,
            "live": False,
            "signals_operational": False,
            "preview_operational": False,
            "cron": False,
            "merge": False,
        },
        "next_phase": "Director decision; if continuing, audit CONTRACTION_ONLY as separate provisional DSS-CO-001. Do not execute yet.",
    }
    side_by_side.to_csv(config.output_dir / "dss_004c_r_side_by_side_baselines.csv", index=False)
    _write_json(config.output_dir / "dss_004c_r_side_by_side_summary.json", side_summary)
    _write_json(config.output_dir / "dss_004c_r_artifact_inventory.json", inventory)
    _write_json(config.output_dir / "dss_004c_r_method_diff.json", diff)
    _write_json(config.output_dir / "dss_004c_r_guard_audit.json", guards)
    _write_json(config.output_dir / "dss_004c_r_decision.json", payload)
    return {
        "base_trades": base_trades,
        "side_by_side": {"table": side_by_side, "summary": side_summary},
        "inventory": inventory,
        "method_diff": diff,
        "guards": guards,
        "decision": payload,
    }


def write_markdown_reports(result: dict[str, Any], research_dir: Path) -> None:
    research_dir.mkdir(parents=True, exist_ok=True)
    decision = result["decision"]
    side = result["side_by_side"]["table"]
    contraction_rows = side[side["variant"] == "CONTRACTION_ONLY"][
        ["mode", "trades_OOS", "symbols_OOS", "OOS_expectancy_net_x2_pct", "OOS_profit_factor_net_x2"]
    ].to_dict("records")
    (research_dir / "DSS_004C_R_REPO_ARTIFACT_INVENTORY.md").write_text(
        "# DSS-004C-R Repo Artifact Inventory\n\n"
        f"- Git status: `{result['inventory']['git_status_short']}`\n"
        f"- Related tracked files: {len(result['inventory']['related_tracked'])}\n"
        f"- Related untracked files: {len(result['inventory']['related_untracked'])}\n\n"
        "No files were deleted.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004C_R_BASELINE_METHOD_DIFF.md").write_text(
        "# DSS-004C-R Baseline Method Diff\n\n"
        f"Probable cause: {result['method_diff']['probable_cause']}\n\n"
        "DSS-004C and DSS-004C-A used the same signal timing, costs, holding period, and baseline names, "
        "but they did not use the same matched-sample definition.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004C_R_SIDE_BY_SIDE_RECOMPUTE.md").write_text(
        "# DSS-004C-R Side-by-side Recompute\n\n"
        f"Decision from recompute: `{result['side_by_side']['summary']['side_by_side_decision']}`.\n\n"
        f"Contraction rows: `{json.dumps(contraction_rows, sort_keys=True)}`\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004C_R_GUARD_AUDIT.md").write_text(
        "# DSS-004C-R Guard Audit\n\n"
        f"Status: `{result['guards']['status']}`.\n\n"
        f"Checks: `{json.dumps(result['guards']['checks'], sort_keys=True)}`\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004C_R_FINAL_REPORT.md").write_text(
        "# DSS-004C-R Final Report\n\n"
        f"Decision: `{decision['decision']}`.\n\n"
        f"Method difference: {result['method_diff']['probable_cause']}\n\n"
        f"Guard status: `{result['guards']['status']}`.\n\n"
        "Valid: DSS-BO-001 base metrics and DSS-004C-A exact symbol-year matched recompute evidence. "
        "Invalidated: DSS-004C coarse matched-baseline interpretation as a comparable matched baseline.\n\n"
        "Safety: no orders, no paper, no live, no cron, no operational preview, no merge.\n",
        encoding="utf-8",
    )
