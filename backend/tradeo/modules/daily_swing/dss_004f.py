from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from tradeo.modules.daily_swing.dss_004 import BENCHMARK_SYMBOLS, _metric_block, _write_json, utc_now
from tradeo.modules.daily_swing.dss_004d import (
    DSS004DConfig,
    _build_trades,
    _ensure_indicators,
    _equity_curve,
    _load_inputs,
    _signal_rows,
    _top_concentration,
)

DSS_004F_SCHEMA_VERSION = "tradeo.daily_swing.dss_004f.v1"
OFFSETS = (0, 1, 2, 5, 10)
BOOTSTRAP_SEED = 40406


@dataclass(frozen=True)
class DSS004FConfig:
    cache_dir: Path
    universe_path: Path
    start_date: str
    end_date: str
    is_end_date: str
    oos_start_date: str
    output_dir: Path
    research_dir: Path
    holding_days: int = 10
    cost_bps_x1: float = 10.0
    cost_bps_x2: float = 20.0
    cost_bps_x3: float = 30.0
    bootstrap_iterations: int = 20

    def to_dss004d(self) -> DSS004DConfig:
        return DSS004DConfig(
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
            phase="DSS-004F",
            artifact_prefix="dss_004f_",
            min_oos_symbols=20,
        )


def _session_gap_days(dates: pd.Series) -> pd.Series:
    return pd.to_datetime(dates).diff().dt.days.fillna(999999).astype(int)


def _session_gap_indices(indices: pd.Series) -> pd.Series:
    return pd.to_numeric(indices).diff().fillna(999999).astype(int)


def _dss004d_config(config: DSS004FConfig) -> DSS004DConfig:
    return config.to_dss004d()


def build_episodes(signals: pd.DataFrame, frames: dict[str, pd.DataFrame], config: DSS004FConfig) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for episode_type, max_gap in (("EPISODE_CONTIGUOUS", 1), ("EPISODE_GAP_3", 3), ("EPISODE_GAP_5", 5)):
        for symbol, group in signals.sort_values(["symbol", "signal_idx"]).groupby("symbol"):
            ordered = group.reset_index(drop=True).copy()
            ordered["gap_sessions"] = _session_gap_indices(ordered["signal_idx"])
            ordered["episode_num"] = (ordered["gap_sessions"] > max_gap).cumsum()
            df = frames[str(symbol)].set_index("date")
            for episode_num, episode in ordered.groupby("episode_num"):
                first = episode.iloc[0]
                last = episode.iloc[-1]
                first_date = str(first["signal_date"])
                last_date = str(last["signal_date"])
                snapshot = df.loc[first_date]
                rows.append(
                    {
                        "episode_type": episode_type,
                        "symbol": symbol,
                        "episode_id": f"{episode_type}-{symbol}-{int(episode_num):05d}",
                        "first_signal_date": first_date,
                        "last_signal_date": last_date,
                        "first_signal_idx": int(first["signal_idx"]),
                        "last_signal_idx": int(last["signal_idx"]),
                        "episode_length_days": int((pd.Timestamp(last_date) - pd.Timestamp(first_date)).days + 1),
                        "number_of_raw_signals": int(len(episode)),
                        "min_ATR14_pct_rank": float(episode["atr14_pct_t_minus_1"].min()),
                        "max_ATR14_pct_rank": float(episode["atr14_pct_t_minus_1"].max()),
                        "regime_snapshot": True,
                        "trend_snapshot": bool(
                            snapshot["close"] > snapshot["sma50"]
                            and (snapshot["close"] > snapshot["sma200"] or snapshot["sma50"] > snapshot["sma200"])
                        ),
                        "sample": "OOS" if first_date >= config.oos_start_date else "IS",
                    }
                )
    episodes = pd.DataFrame(rows)
    primary = episodes[episodes["episode_type"] == "EPISODE_GAP_5"].copy()
    by_symbol = primary.groupby("symbol").size() if not primary.empty else pd.Series(dtype=int)
    by_month = pd.to_datetime(primary["first_signal_date"]).dt.to_period("M").astype(str).value_counts().sort_index() if not primary.empty else pd.Series(dtype=int)
    raw_per_episode = primary["number_of_raw_signals"] if not primary.empty else pd.Series(dtype=float)
    summary = {
        "schema_version": DSS_004F_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "primary_episode_type": "EPISODE_GAP_5",
        "raw_signals_total": int(len(signals)),
        "raw_signals_OOS": int((signals["signal_date"] >= config.oos_start_date).sum()) if not signals.empty else 0,
        "episodes_total": int(len(primary)),
        "episodes_OOS": int((primary["sample"] == "OOS").sum()) if not primary.empty else 0,
        "raw_signals_per_episode_mean": float(raw_per_episode.mean()) if not raw_per_episode.empty else None,
        "raw_signals_per_episode_median": float(raw_per_episode.median()) if not raw_per_episode.empty else None,
        "raw_signals_per_episode_p95": float(raw_per_episode.quantile(0.95)) if not raw_per_episode.empty else None,
        "episodes_per_symbol_mean": float(by_symbol.mean()) if not by_symbol.empty else None,
        "episodes_per_symbol_max": int(by_symbol.max()) if not by_symbol.empty else 0,
        "episodes_by_month": by_month.to_dict(),
        "partial_decision": (
            "EPISODE_OVERLAP_HEAVY"
            if not raw_per_episode.empty and float(raw_per_episode.mean()) >= 4.0
            else "EPISODE_STRUCTURE_OK"
        ),
    }
    return episodes, summary


def _trade_from_episode(
    episode: pd.Series,
    frames: dict[str, pd.DataFrame],
    config: DSS004FConfig,
    offset: int,
    policy: str,
) -> dict[str, Any] | None:
    symbol = str(episode["symbol"])
    df = frames[symbol]
    signal_idx = int(episode["first_signal_idx"]) + offset
    entry_idx = signal_idx + 1
    if entry_idx >= len(df):
        return None
    exit_idx = min(entry_idx + config.holding_days, len(df) - 1)
    if exit_idx <= entry_idx:
        return None
    entry = df.iloc[entry_idx]
    exit_row = df.iloc[exit_idx]
    entry_price = float(entry["open"])
    exit_price = float(exit_row["close"])
    if entry_price <= 0 or exit_price <= 0:
        return None
    gross = (exit_price / entry_price) - 1.0
    return {
        "episode_id": episode["episode_id"],
        "episode_type": episode["episode_type"],
        "policy": policy,
        "offset": offset,
        "symbol": symbol,
        "first_signal_date": episode["first_signal_date"],
        "source_first_signal_date": episode["first_signal_date"],
        "offset_signal_date": str(df.iloc[signal_idx]["date"]),
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
    }


def _summarize_trades(trades: pd.DataFrame, config: DSS004FConfig) -> dict[str, Any]:
    oos = trades[trades["first_signal_date"] >= config.oos_start_date].copy() if not trades.empty else trades
    last_12 = trades[trades["first_signal_date"] >= "2025-07-02"].copy() if not trades.empty else trades
    last_24 = trades[trades["first_signal_date"] >= "2024-07-02"].copy() if not trades.empty else trades
    _, max_drawdown = _equity_curve(oos.rename(columns={"first_signal_date": "signal_date"}) if not oos.empty else oos)
    returns = oos["net_return_x2_pct"].tolist() if not oos.empty else []
    worst_streak = 0
    current = 0
    for value in returns:
        current = current + 1 if value < 0 else 0
        worst_streak = max(worst_streak, current)
    return {
        "episodes_total": int(len(trades)),
        "episodes_OOS": int(len(oos)),
        "symbols_OOS": int(oos["symbol"].nunique()) if not oos.empty else 0,
        "OOS": _metric_block(oos, "net_return_x2_pct"),
        "last_12_months": _metric_block(last_12, "net_return_x2_pct"),
        "last_24_months": _metric_block(last_24, "net_return_x2_pct"),
        "concentration": _top_concentration(oos.rename(columns={"episode_id": "trade_id"}) if not oos.empty else oos),
        "max_drawdown_pct": max_drawdown,
        "worst_loss_streak": worst_streak,
    }


def offset_timing_audit(
    episodes: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    config: DSS004FConfig,
    *,
    policy: str = "EPISODE_GAP_5_ALL_EPISODES",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    primary = episodes[episodes["episode_type"] == "EPISODE_GAP_5"].sort_values(["first_signal_date", "symbol"]).copy()
    rows = []
    for offset in OFFSETS:
        for _, episode in primary.iterrows():
            trade = _trade_from_episode(episode, frames, config, offset, policy)
            if trade is not None:
                rows.append(trade)
    trades = pd.DataFrame(rows)
    by_offset: dict[str, Any] = {}
    for offset in OFFSETS:
        by_offset[str(offset)] = _summarize_trades(trades[trades["offset"] == offset].copy(), config)
    base = by_offset["0"]["OOS"]
    comparisons = {}
    for offset in OFFSETS:
        metrics = by_offset[str(offset)]["OOS"]
        comparisons[str(offset)] = {
            "base_minus_offset_expectancy": None
            if base["expectancy_pct"] is None or metrics["expectancy_pct"] is None
            else base["expectancy_pct"] - metrics["expectancy_pct"],
            "base_minus_offset_pf": None
            if base["profit_factor"] is None or metrics["profit_factor"] is None
            else base["profit_factor"] - metrics["profit_factor"],
        }
    delayed_beats = sum(
        1
        for offset in (1, 2, 5, 10)
        if by_offset[str(offset)]["OOS"]["expectancy_pct"] is not None
        and base["expectancy_pct"] is not None
        and by_offset[str(offset)]["OOS"]["expectancy_pct"] >= base["expectancy_pct"]
    )
    if delayed_beats >= 3:
        partial = "TIMING_WINDOW_CONFIRMED"
    elif delayed_beats >= 1:
        partial = "TIMING_INCONCLUSIVE"
    else:
        partial = "BASE_TIMING_RECOVERED_AFTER_EPISODE_DEDUP"
    return trades, {
        "schema_version": DSS_004F_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "policy": policy,
        "by_offset": by_offset,
        "comparisons": comparisons,
        "delayed_offsets_equal_or_better": delayed_beats,
        "partial_decision": partial,
    }


def overlap_effective_sample_audit(
    raw_trades: dict[str, pd.DataFrame],
    episodes: pd.DataFrame,
    episode_trades: pd.DataFrame,
    config: DSS004FConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    primary = episodes[episodes["episode_type"] == "EPISODE_GAP_5"].copy()
    episode_lookup = primary[["symbol", "first_signal_idx", "last_signal_idx", "episode_id"]].copy()
    policy_summary = {}
    for policy, trades in raw_trades.items():
        if trades.empty:
            policy_summary[policy] = {}
            continue
        marked = trades.copy()
        marked["entry_date_dt"] = pd.to_datetime(marked["entry_date"])
        marked["exit_date_dt"] = pd.to_datetime(marked["exit_date"])
        overlap_flags = []
        for _, group in marked.sort_values(["symbol", "entry_date_dt"]).groupby("symbol"):
            running_exit = pd.Timestamp.min
            for _, trade in group.iterrows():
                entry = pd.Timestamp(trade["entry_date_dt"])
                exit_date = pd.Timestamp(trade["exit_date_dt"])
                overlap_flags.append(entry <= running_exit)
                if exit_date > running_exit:
                    running_exit = exit_date
        by_entry = marked.groupby("entry_date").size()
        oos = marked[marked["signal_date"] >= config.oos_start_date]
        policy_summary[policy] = {
            "trades_total": int(len(marked)),
            "trades_OOS": int(len(oos)),
            "overlap_pct_by_symbol": float(sum(overlap_flags) / len(overlap_flags)) if overlap_flags else None,
            "approx_effective_events": int(primary[primary["sample"] == "OOS"]["episode_id"].nunique()),
            "mean_simultaneous_new_trades": float(by_entry.mean()) if not by_entry.empty else None,
            "max_simultaneous_new_trades": int(by_entry.max()) if not by_entry.empty else 0,
            "days_with_more_than_2_signals": int((by_entry > 2).sum()),
            "trades_sharing_episode_pct": 1.0 if not episode_lookup.empty else None,
            "raw_oos": _metric_block(oos, "net_return_x2_pct"),
        }
    boot_rows = []
    oos_episode_trades = episode_trades[
        (episode_trades["offset"] == 0) & (episode_trades["first_signal_date"] >= config.oos_start_date)
    ].copy()
    rng = random.Random(BOOTSTRAP_SEED)
    for cluster in ("symbol", "symbol_month"):
        sample = oos_episode_trades.copy()
        if sample.empty:
            continue
        sample["symbol_month"] = sample["symbol"] + "-" + pd.to_datetime(sample["first_signal_date"]).dt.to_period("M").astype(str)
        groups = [group.copy() for _, group in sample.groupby(cluster)]
        for iteration in range(config.bootstrap_iterations):
            pieces = [rng.choice(groups) for _ in groups]
            draw = pd.concat(pieces, ignore_index=True)
            metrics = _metric_block(draw, "net_return_x2_pct")
            boot_rows.append(
                {
                    "cluster": cluster,
                    "iteration": iteration,
                    "expectancy_pct": metrics["expectancy_pct"],
                    "profit_factor": metrics["profit_factor"],
                    "trades": len(draw),
                }
            )
    bootstrap = pd.DataFrame(boot_rows)
    bootstrap_summary = {}
    for cluster, group in bootstrap.groupby("cluster") if not bootstrap.empty else []:
        bootstrap_summary[cluster] = {
            "expectancy_mean": float(group["expectancy_pct"].mean()),
            "expectancy_p05": float(group["expectancy_pct"].quantile(0.05)),
            "expectancy_p50": float(group["expectancy_pct"].quantile(0.50)),
            "expectancy_p95": float(group["expectancy_pct"].quantile(0.95)),
            "pf_p05": float(group["profit_factor"].dropna().quantile(0.05)) if group["profit_factor"].notna().any() else None,
            "pf_p50": float(group["profit_factor"].dropna().quantile(0.50)) if group["profit_factor"].notna().any() else None,
            "pf_p95": float(group["profit_factor"].dropna().quantile(0.95)) if group["profit_factor"].notna().any() else None,
        }
    symbol_p05 = bootstrap_summary.get("symbol", {}).get("expectancy_p05")
    partial = "EFFECTIVE_SAMPLE_WARNING" if symbol_p05 is not None and symbol_p05 <= 0 else "EFFECTIVE_SAMPLE_OK"
    raw_overlap = {
        policy: {
            "overlap_trade_pct": summary.get("overlap_pct_by_symbol"),
            "effective_events_approx": summary.get("approx_effective_events"),
            **summary,
        }
        for policy, summary in policy_summary.items()
    }
    return bootstrap, {
        "schema_version": DSS_004F_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "policy_summary": policy_summary,
        "raw_overlap": raw_overlap,
        "episode_dedup_oos": _summarize_trades(oos_episode_trades, config),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_iterations": config.bootstrap_iterations,
        "bootstrap_summary": bootstrap_summary,
        "partial_decision": partial,
    }


def _cluster_bootstrap(episode_trades: pd.DataFrame, config: DSS004FConfig) -> pd.DataFrame:
    oos_episode_trades = episode_trades[
        (episode_trades["offset"] == 0) & (episode_trades["first_signal_date"] >= config.oos_start_date)
    ].copy()
    boot_rows = []
    rng = random.Random(BOOTSTRAP_SEED)
    for cluster in ("symbol", "symbol_month"):
        sample = oos_episode_trades.copy()
        if sample.empty:
            continue
        sample["symbol_month"] = sample["symbol"] + "-" + pd.to_datetime(sample["first_signal_date"]).dt.to_period("M").astype(str)
        groups = [group.copy() for _, group in sample.groupby(cluster)]
        for iteration in range(config.bootstrap_iterations):
            draw = pd.concat([rng.choice(groups) for _ in groups], ignore_index=True)
            metrics = _metric_block(draw, "net_return_x2_pct")
            boot_rows.append(
                {
                    "cluster": cluster,
                    "iteration": iteration,
                    "expectancy_pct": metrics["expectancy_pct"],
                    "profit_factor": metrics["profit_factor"],
                    "trades": len(draw),
                }
            )
    return pd.DataFrame(boot_rows)


def portfolio_timing_constraints(
    episodes: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    config: DSS004FConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    primary = episodes[episodes["episode_type"] == "EPISODE_GAP_5"].sort_values(
        ["first_signal_date", "min_ATR14_pct_rank", "symbol"]
    )
    rows = []
    for offset in OFFSETS:
        open_until: dict[str, pd.Timestamp] = {}
        for date, day in primary.groupby("first_signal_date", sort=True):
            selected = []
            for _, episode in day.iterrows():
                symbol = str(episode["symbol"])
                if pd.Timestamp(date) <= open_until.get(symbol, pd.Timestamp.min):
                    continue
                selected.append(episode)
                if len(selected) == 2:
                    break
            for episode in selected:
                trade = _trade_from_episode(episode, frames, config, offset, "MAX_2_NEW_EPISODES_PER_DAY")
                if trade is None:
                    continue
                rows.append(trade)
                open_until[str(episode["symbol"])] = pd.Timestamp(trade["exit_date"])
    trades = pd.DataFrame(rows)
    by_offset = {str(offset): _summarize_trades(trades[trades["offset"] == offset].copy(), config) for offset in OFFSETS}
    base = by_offset["0"]["OOS"]
    viable = base["expectancy_pct"] is not None and base["expectancy_pct"] > 0 and (base["profit_factor"] or 0) >= 1.15
    delayed = sum(
        1
        for offset in (1, 2, 5, 10)
        if by_offset[str(offset)]["OOS"]["expectancy_pct"] is not None
        and base["expectancy_pct"] is not None
        and by_offset[str(offset)]["OOS"]["expectancy_pct"] >= base["expectancy_pct"]
    )
    partial = "PORTFOLIO_TIMING_WARNING" if viable and delayed else "PORTFOLIO_TIMING_OK" if viable else "PORTFOLIO_TIMING_FAIL"
    return trades, {
        "schema_version": DSS_004F_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "policy": "MAX_2_NEW_EPISODES_PER_DAY",
        "priority": "lower ATR14_pct_rank, then stable symbol order; no reliable dollar-volume field in cache",
        "by_offset": by_offset,
        "partial_decision": partial,
    }


def _decide(offset_summary: dict[str, Any], overlap_summary: dict[str, Any], portfolio_summary: dict[str, Any]) -> str:
    if overlap_summary["partial_decision"] == "EFFECTIVE_SAMPLE_FAIL":
        return "DSS_CO_001_EFFECTIVE_SAMPLE_FAIL"
    if offset_summary["partial_decision"] == "BASE_TIMING_RECOVERED_AFTER_EPISODE_DEDUP":
        return "DSS_CO_001_BASE_TIMING_RECOVERED_AFTER_DEDUP"
    if offset_summary["partial_decision"] == "TIMING_WINDOW_CONFIRMED":
        return "DSS_CO_001_TIMING_WINDOW_CONFIRMED"
    if portfolio_summary["partial_decision"] == "PORTFOLIO_TIMING_FAIL":
        return "DSS_CO_001_OVERLAP_INFLATED_EDGE_FAIL"
    return "DSS_CO_001_INCONCLUSIVE"


def run_dss_004f(config: DSS004FConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.research_dir.mkdir(parents=True, exist_ok=True)
    d_config = config.to_dss004d()
    frames, regime, regime_symbol, universe_summary, last_valid = _load_inputs(d_config)
    frames = {symbol: _ensure_indicators(frame) for symbol, frame in frames.items()}
    signals = _signal_rows(frames, regime)
    if bool(set(signals["symbol"]) & BENCHMARK_SYMBOLS) if not signals.empty else False:
        raise ValueError("SPY/QQQ leaked into operational signals")
    if last_valid != "2026-07-02":
        raise ValueError(f"unexpected last_valid_bar_date={last_valid}")
    raw_trades = {
        policy: _build_trades(frames, signals, d_config, policy)
        for policy in ("ALL_EVENTS", "ONE_ACTIVE_PER_SYMBOL", "MAX_2_NEW_TRADES_PER_DAY_SIM")
    }
    episodes, episode_summary = build_episodes(signals, frames, config)
    offset_trades, offset_summary = offset_timing_audit(episodes, frames, config)
    bootstrap, overlap_summary = overlap_effective_sample_audit(raw_trades, episodes, offset_trades, config)
    portfolio_trades, portfolio_summary = portfolio_timing_constraints(episodes, frames, config)
    decision = _decide(offset_summary, overlap_summary, portfolio_summary)
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
        "ibkr_used": False,
        "downloaded_more_data": False,
    }
    decision_payload = {
        "schema_version": DSS_004F_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "phase": "DSS-004F",
        "pattern_id": "DSS-CO-001",
        "decision": decision,
        "last_valid_bar_date": last_valid,
        "false_bar_2026_07_03_present": False,
        "regime_symbol": regime_symbol,
        "universe_summary": universe_summary,
        "episode_decision": episode_summary["partial_decision"],
        "offset_timing_decision": offset_summary["partial_decision"],
        "overlap_effective_sample_decision": overlap_summary["partial_decision"],
        "portfolio_timing_decision": portfolio_summary["partial_decision"],
        "safety": safety,
        "next_phase": (
            "Design DSS-CW-001 Contraction Window in a separate research task; no DSS-005 and no paper preview"
            if decision == "DSS_CO_001_TIMING_WINDOW_CONFIRMED"
            else "Director review; no DSS-005"
        ),
    }
    episodes.to_csv(config.output_dir / "dss_004f_episodes.csv", index=False)
    offset_trades.to_csv(config.output_dir / "dss_004f_offset_timing_by_episode.csv", index=False)
    bootstrap.to_csv(config.output_dir / "dss_004f_cluster_bootstrap.csv", index=False)
    portfolio_trades.to_csv(config.output_dir / "dss_004f_portfolio_timing_constraints.csv", index=False)
    _write_json(config.output_dir / "dss_004f_episode_summary.json", episode_summary)
    _write_json(config.output_dir / "dss_004f_offset_timing_summary.json", offset_summary)
    _write_json(config.output_dir / "dss_004f_overlap_summary.json", overlap_summary)
    _write_json(config.output_dir / "dss_004f_portfolio_timing_summary.json", portfolio_summary)
    _write_json(config.output_dir / "dss_004f_decision.json", decision_payload)
    write_markdown_reports(
        {
            "episode_summary": episode_summary,
            "offset_summary": offset_summary,
            "overlap_summary": overlap_summary,
            "portfolio_summary": portfolio_summary,
            "decision": decision_payload,
            "safety": safety,
        },
        config.research_dir,
    )
    return {
        "episodes": episodes,
        "offset_trades": offset_trades,
        "bootstrap": bootstrap,
        "portfolio_trades": portfolio_trades,
        "episode_summary": episode_summary,
        "offset_summary": offset_summary,
        "overlap_summary": overlap_summary,
        "portfolio_summary": portfolio_summary,
        "decision": decision_payload,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def write_markdown_reports(result: dict[str, Any], research_dir: Path) -> None:
    episode = result["episode_summary"]
    offset = result["offset_summary"]
    overlap = result["overlap_summary"]
    portfolio = result["portfolio_summary"]
    decision = result["decision"]
    offset_rows = []
    for off, metrics in offset["by_offset"].items():
        oos = metrics["OOS"]
        offset_rows.append(
            f"| {off} | {metrics['episodes_OOS']} | {metrics['symbols_OOS']} | "
            f"{_fmt(oos['expectancy_pct'])} | {_fmt(oos['profit_factor'])} | "
            f"{_fmt(metrics['last_12_months']['expectancy_pct'])} |"
        )
    portfolio_rows = []
    for off, metrics in portfolio["by_offset"].items():
        oos = metrics["OOS"]
        portfolio_rows.append(
            f"| {off} | {metrics['episodes_OOS']} | {metrics['symbols_OOS']} | "
            f"{_fmt(oos['expectancy_pct'])} | {_fmt(oos['profit_factor'])} | "
            f"{_fmt(metrics['max_drawdown_pct'])} | {metrics['worst_loss_streak']} |"
        )
    research_dir.mkdir(parents=True, exist_ok=True)
    (research_dir / "DSS_004F_EPISODE_BUILDER.md").write_text(
        "# DSS-004F Episode Builder\n\n"
        f"Primary episode type: `{episode['primary_episode_type']}`.\n\n"
        f"Raw signals total/OOS: `{episode['raw_signals_total']}` / `{episode['raw_signals_OOS']}`.\n\n"
        f"Episodes total/OOS: `{episode['episodes_total']}` / `{episode['episodes_OOS']}`.\n\n"
        f"Raw signals per episode mean/median/p95: `{_fmt(episode['raw_signals_per_episode_mean'])}` / "
        f"`{_fmt(episode['raw_signals_per_episode_median'])}` / `{_fmt(episode['raw_signals_per_episode_p95'])}`.\n\n"
        f"Partial decision: `{episode['partial_decision']}`.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004F_OFFSET_TIMING_AUDIT.md").write_text(
        "# DSS-004F Offset Timing Audit\n\n"
        "| Offset | OOS episodes | OOS symbols | OOS exp x2 | OOS PF x2 | Last 12m exp x2 |\n"
        "|---:|---:|---:|---:|---:|---:|\n"
        + "\n".join(offset_rows)
        + f"\n\nPartial decision: `{offset['partial_decision']}`.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004F_OVERLAP_EFFECTIVE_SAMPLE.md").write_text(
        "# DSS-004F Overlap / Effective Sample\n\n"
        f"Partial decision: `{overlap['partial_decision']}`.\n\n"
        f"Bootstrap seed: `{overlap['bootstrap_seed']}`; iterations: `{overlap['bootstrap_iterations']}`.\n\n"
        f"Bootstrap summary: `{overlap['bootstrap_summary']}`.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004F_PORTFOLIO_TIMING_CONSTRAINTS.md").write_text(
        "# DSS-004F Portfolio-Like Timing Constraints\n\n"
        "| Offset | OOS episodes | OOS symbols | OOS exp x2 | OOS PF x2 | Max DD | Worst loss streak |\n"
        "|---:|---:|---:|---:|---:|---:|---:|\n"
        + "\n".join(portfolio_rows)
        + f"\n\nPartial decision: `{portfolio['partial_decision']}`.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004F_FINAL_REPORT.md").write_text(
        "# DSS-004F Final Report\n\n"
        f"Decision: `{decision['decision']}`.\n\n"
        f"Episode builder: `{episode['partial_decision']}`.\n\n"
        f"Offset timing: `{offset['partial_decision']}`.\n\n"
        f"Overlap/effective sample: `{overlap['partial_decision']}`.\n\n"
        f"Portfolio timing: `{portfolio['partial_decision']}`.\n\n"
        "Safety: no orders, no paper orders, no live, no paper execution, no operational preview, "
        "no operational signals, no cron, no .env modification, no IBKR, no data downloads, no merge.\n",
        encoding="utf-8",
    )
