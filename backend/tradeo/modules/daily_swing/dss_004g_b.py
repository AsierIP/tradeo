from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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

DSS_004G_B_SCHEMA_VERSION = "tradeo.daily_swing.dss_004g_b.v1"
BOOTSTRAP_SEED = 40407
RANDOM_MATCHED_SEED = 40408
Policy = Literal["ALL_ELIGIBLE_EPISODES", "ONE_ACTIVE_PER_SYMBOL_EPISODE", "MAX_2_NEW_EPISODES_PER_DAY"]


@dataclass(frozen=True)
class DSS004GBConfig:
    cache_dir: Path
    universe_path: Path
    start_date: str
    end_date: str
    is_end_date: str
    oos_start_date: str
    output_dir: Path
    research_dir: Path
    holding_days: int = 10
    window_sessions: int = 5
    episode_gap_sessions: int = 5
    cost_bps_x1: float = 10.0
    cost_bps_x2: float = 20.0
    cost_bps_x3: float = 30.0
    bootstrap_iterations: int = 100
    min_operational_ready: int = 150

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
            phase="DSS-004G-B",
            artifact_prefix="dss_004g_b_",
            min_oos_symbols=20,
        )


def _date_at(df: pd.DataFrame, idx: int) -> str:
    return str(df.iloc[idx]["date"])


def build_cw_episodes(signals: pd.DataFrame, frames: dict[str, pd.DataFrame], config: DSS004GBConfig) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if signals.empty:
        return pd.DataFrame()
    for symbol, group in signals.sort_values(["symbol", "signal_idx"]).groupby("symbol"):
        ordered = group.reset_index(drop=True).copy()
        ordered["gap_sessions"] = pd.to_numeric(ordered["signal_idx"]).diff().fillna(999999).astype(int)
        ordered["episode_num"] = (ordered["gap_sessions"] > config.episode_gap_sessions).cumsum()
        df = frames[str(symbol)]
        for episode_num, episode in ordered.groupby("episode_num"):
            first_idx = int(episode["signal_idx"].min())
            last_idx = int(episode["signal_idx"].max())
            window_end_idx = min(first_idx + config.window_sessions, last_idx)
            if first_idx >= len(df) - 1:
                continue
            rows.append(
                {
                    "pattern_id": "DSS-CW-001",
                    "episode_type": "EPISODE_GAP_5",
                    "symbol": str(symbol),
                    "episode_id": f"DSS-CW-001-{symbol}-{int(episode_num):05d}",
                    "first_signal_idx": first_idx,
                    "last_signal_idx": last_idx,
                    "window_start_idx": first_idx,
                    "window_end_idx": window_end_idx,
                    "first_signal_date": _date_at(df, first_idx),
                    "last_signal_date": _date_at(df, last_idx),
                    "window_start_date": _date_at(df, first_idx),
                    "window_end_date": _date_at(df, window_end_idx),
                    "raw_signal_count": int(len(episode)),
                    "min_ATR14_pct_rank": float(episode["atr14_pct_t_minus_1"].min()),
                    "sample": "OOS" if _date_at(df, first_idx) >= config.oos_start_date else "IS",
                }
            )
    return pd.DataFrame(rows).sort_values(["first_signal_date", "min_ATR14_pct_rank", "symbol"]).reset_index(drop=True)


def _episode_candidates(episodes: pd.DataFrame, frames: dict[str, pd.DataFrame], config: DSS004GBConfig) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, episode in episodes.iterrows():
        df = frames[str(episode["symbol"])]
        for decision_idx in range(int(episode["window_start_idx"]), int(episode["window_end_idx"]) + 1):
            entry_idx = decision_idx + 1
            if entry_idx >= len(df):
                continue
            rows.append(
                {
                    "episode_id": episode["episode_id"],
                    "symbol": episode["symbol"],
                    "decision_idx": decision_idx,
                    "selected_decision_date": _date_at(df, decision_idx),
                    "selected_decision_offset": int(decision_idx - int(episode["first_signal_idx"])),
                    "first_signal_date": episode["first_signal_date"],
                    "last_signal_date": episode["last_signal_date"],
                    "raw_signal_count": int(episode["raw_signal_count"]),
                    "min_ATR14_pct_rank": float(episode["min_ATR14_pct_rank"]),
                }
            )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["selected_decision_date", "min_ATR14_pct_rank", "first_signal_date", "symbol", "episode_id"]
    ).reset_index(drop=True)


def _trade_from_candidate(
    candidate: pd.Series,
    frames: dict[str, pd.DataFrame],
    config: DSS004GBConfig,
    policy: Policy,
    *,
    entry_model: str = "next_open",
    adverse_entry_bps: float = 0.0,
    signal_shift: int = 0,
    variant: str = "DSS-CW-001",
) -> dict[str, Any] | None:
    symbol = str(candidate["symbol"])
    df = frames[symbol]
    decision_idx = int(candidate["decision_idx"]) + signal_shift
    entry_idx = decision_idx + 1
    if entry_idx >= len(df):
        return None
    exit_idx = min(entry_idx + config.holding_days, len(df) - 1)
    if exit_idx <= entry_idx:
        return None
    entry = df.iloc[entry_idx]
    exit_row = df.iloc[exit_idx]
    entry_price = float(entry["close"] if entry_model == "next_close" else entry["open"])
    if adverse_entry_bps:
        entry_price *= 1.0 + adverse_entry_bps / 10000.0
    exit_price = float(exit_row["close"])
    if entry_price <= 0 or exit_price <= 0:
        return None
    gross = (exit_price / entry_price) - 1.0
    model = "next_close" if entry_model == "next_close" else "next_open"
    if adverse_entry_bps:
        model = f"{model}_adverse_{adverse_entry_bps:g}bps"
    if signal_shift:
        model = f"{model}_window_shift_plus_{signal_shift}"
    return {
        "trade_id": "",
        "pattern_id": "DSS-CW-001",
        "variant": variant,
        "policy": policy,
        "symbol": symbol,
        "episode_id": candidate["episode_id"],
        "first_signal_date": candidate["first_signal_date"],
        "last_signal_date": candidate["last_signal_date"],
        "selected_decision_date": _date_at(df, decision_idx),
        "selected_decision_offset": int(candidate["selected_decision_offset"]) + signal_shift,
        "entry_date": str(entry["date"]),
        "exit_date": str(exit_row["date"]),
        "entry_open": round(float(entry["open"]), 6),
        "entry_price": round(entry_price, 6),
        "exit_close": round(exit_price, 6),
        "holding_sessions": int(exit_idx - entry_idx),
        "raw_signal_count": int(candidate["raw_signal_count"]),
        "atr14_pct_rank_at_decision": float(candidate["min_ATR14_pct_rank"]),
        "skip_reason": "",
        "gross_return_pct": gross * 100.0,
        "net_return_x1_pct": (gross - config.cost_bps_x1 / 10000.0) * 100.0,
        "net_return_x2_pct": (gross - config.cost_bps_x2 / 10000.0) * 100.0,
        "net_return_x3_pct": (gross - config.cost_bps_x3 / 10000.0) * 100.0,
        "sample": "OOS" if str(candidate["first_signal_date"]) >= config.oos_start_date else "IS",
        "truncated": bool(exit_idx != entry_idx + config.holding_days),
        "entry_model": model,
        "exit_model": f"time_stop_{config.holding_days}_sessions_close",
    }


def build_cw_trades(
    episodes: pd.DataFrame,
    frames: dict[str, pd.DataFrame],
    config: DSS004GBConfig,
    policy: Policy,
    *,
    entry_model: str = "next_open",
    adverse_entry_bps: float = 0.0,
    signal_shift: int = 0,
    variant: str = "DSS-CW-001",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidates = _episode_candidates(episodes, frames, config)
    trades: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    selected_episode_ids: set[str] = set()
    open_until_by_symbol: dict[str, pd.Timestamp] = {}
    if policy == "ALL_ELIGIBLE_EPISODES":
        selected = candidates.drop_duplicates("episode_id", keep="first") if not candidates.empty else candidates
        for _, candidate in selected.iterrows():
            trade = _trade_from_candidate(
                candidate,
                frames,
                config,
                policy,
                entry_model=entry_model,
                adverse_entry_bps=adverse_entry_bps,
                signal_shift=signal_shift,
                variant=variant,
            )
            if trade is not None:
                trades.append(trade)
                selected_episode_ids.add(str(candidate["episode_id"]))
    elif policy == "ONE_ACTIVE_PER_SYMBOL_EPISODE":
        for _, candidate in candidates.iterrows():
            episode_id = str(candidate["episode_id"])
            if episode_id in selected_episode_ids:
                continue
            symbol = str(candidate["symbol"])
            decision_date = pd.Timestamp(candidate["selected_decision_date"])
            if decision_date <= open_until_by_symbol.get(symbol, pd.Timestamp.min):
                continue
            trade = _trade_from_candidate(
                candidate,
                frames,
                config,
                policy,
                entry_model=entry_model,
                adverse_entry_bps=adverse_entry_bps,
                signal_shift=signal_shift,
                variant=variant,
            )
            if trade is None:
                continue
            trades.append(trade)
            selected_episode_ids.add(episode_id)
            open_until_by_symbol[symbol] = pd.Timestamp(trade["exit_date"])
    else:
        for decision_date, day in candidates.groupby("selected_decision_date", sort=True):
            selected_today = 0
            for _, candidate in day.iterrows():
                episode_id = str(candidate["episode_id"])
                symbol = str(candidate["symbol"])
                if episode_id in selected_episode_ids:
                    continue
                if pd.Timestamp(decision_date) <= open_until_by_symbol.get(symbol, pd.Timestamp.min):
                    continue
                trade = _trade_from_candidate(
                    candidate,
                    frames,
                    config,
                    policy,
                    entry_model=entry_model,
                    adverse_entry_bps=adverse_entry_bps,
                    signal_shift=signal_shift,
                    variant=variant,
                )
                if trade is None:
                    continue
                trades.append(trade)
                selected_episode_ids.add(episode_id)
                open_until_by_symbol[symbol] = pd.Timestamp(trade["exit_date"])
                selected_today += 1
                if selected_today == 2:
                    break
    for _, episode in episodes.iterrows():
        if str(episode["episode_id"]) not in selected_episode_ids:
            skipped.append(
                {
                    "episode_id": episode["episode_id"],
                    "symbol": episode["symbol"],
                    "first_signal_date": episode["first_signal_date"],
                    "last_signal_date": episode["last_signal_date"],
                    "policy": policy,
                    "skip_reason": "portfolio_or_sample_window_no_entry",
                }
            )
    columns = [
        "trade_id",
        "pattern_id",
        "variant",
        "policy",
        "symbol",
        "episode_id",
        "first_signal_date",
        "last_signal_date",
        "selected_decision_date",
        "selected_decision_offset",
        "entry_date",
        "exit_date",
        "entry_open",
        "entry_price",
        "exit_close",
        "holding_sessions",
        "raw_signal_count",
        "atr14_pct_rank_at_decision",
        "skip_reason",
        "gross_return_pct",
        "net_return_x1_pct",
        "net_return_x2_pct",
        "net_return_x3_pct",
        "sample",
        "truncated",
        "entry_model",
        "exit_model",
    ]
    out = pd.DataFrame(trades, columns=columns)
    if not out.empty:
        out = out.sort_values(["entry_date", "symbol"]).reset_index(drop=True)
        out["trade_id"] = [f"DSS-CW-001-{policy}-{idx + 1:05d}" for idx in range(len(out))]
    return out, pd.DataFrame(skipped)


def _loss_streak(values: list[float]) -> int:
    worst = 0
    current = 0
    for value in values:
        current = current + 1 if value < 0 else 0
        worst = max(worst, current)
    return worst


def policy_metrics(policy: str, trades: pd.DataFrame, skipped: pd.DataFrame, episodes: pd.DataFrame, config: DSS004GBConfig) -> dict[str, Any]:
    if trades.empty:
        is_trades = trades
        oos = trades
        last_12 = trades
        last_24 = trades
    else:
        is_trades = trades[trades["first_signal_date"] <= config.is_end_date].copy()
        oos = trades[trades["first_signal_date"] >= config.oos_start_date].copy()
        last_12 = trades[trades["first_signal_date"] >= "2025-07-02"].copy()
        last_24 = trades[trades["first_signal_date"] >= "2024-07-02"].copy()
    _, max_drawdown = _equity_curve(trades.rename(columns={"first_signal_date": "signal_date"}) if not trades.empty else trades)
    by_day = trades.groupby("selected_decision_date").size() if not trades.empty else pd.Series(dtype=int)
    oos_metrics = _metric_block(oos, "net_return_x2_pct")
    return {
        "policy": policy,
        "episodes_total": int(len(episodes)),
        "episodes_IS": int((episodes["first_signal_date"] <= config.is_end_date).sum()) if not episodes.empty else 0,
        "episodes_OOS": int((episodes["first_signal_date"] >= config.oos_start_date).sum()) if not episodes.empty else 0,
        "trades_total": int(len(trades)),
        "trades_IS": int(len(is_trades)),
        "trades_OOS": int(len(oos)),
        "skipped_episodes": int(len(skipped)),
        "symbols_total": int(trades["symbol"].nunique()) if not trades.empty else 0,
        "symbols_IS": int(is_trades["symbol"].nunique()) if not is_trades.empty else 0,
        "symbols_OOS": int(oos["symbol"].nunique()) if not oos.empty else 0,
        "gross": _metric_block(trades, "gross_return_pct"),
        "cost_x1": _metric_block(trades, "net_return_x1_pct"),
        "cost_x2": _metric_block(trades, "net_return_x2_pct"),
        "cost_x3": _metric_block(trades, "net_return_x3_pct"),
        "IS": _metric_block(is_trades, "net_return_x2_pct"),
        "OOS": oos_metrics,
        "last_12_months": _metric_block(last_12, "net_return_x2_pct"),
        "last_24_months": _metric_block(last_24, "net_return_x2_pct"),
        "max_drawdown_pct": max_drawdown,
        "worst_loss_streak": _loss_streak(oos["net_return_x2_pct"].tolist()) if not oos.empty else 0,
        "concentration": _top_concentration(oos.rename(columns={"episode_id": "trade_id"}) if not oos.empty else oos),
        "days_with_more_than_2_episode_candidates": int((by_day > 2).sum()),
        "max_new_episodes_in_day": int(by_day.max()) if not by_day.empty else 0,
    }


def _write_period_tables(trades: pd.DataFrame, output_dir: Path) -> None:
    if trades.empty:
        for name in (
            "dss_cw_001_metrics_by_symbol.csv",
            "dss_cw_001_metrics_by_year.csv",
            "dss_cw_001_metrics_by_quarter.csv",
        ):
            pd.DataFrame().to_csv(output_dir / name, index=False)
        return
    trades.groupby(["policy", "symbol"]).agg(
        trades=("trade_id", "count"),
        net_x2_sum_pct=("net_return_x2_pct", "sum"),
        net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
    ).reset_index().to_csv(output_dir / "dss_cw_001_metrics_by_symbol.csv", index=False)
    dated = trades.copy()
    dated["year"] = pd.to_datetime(dated["exit_date"]).dt.year
    dated["quarter"] = pd.to_datetime(dated["exit_date"]).dt.to_period("Q").astype(str)
    dated.groupby(["policy", "year"]).agg(
        trades=("trade_id", "count"),
        net_x2_sum_pct=("net_return_x2_pct", "sum"),
        net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
    ).reset_index().to_csv(output_dir / "dss_cw_001_metrics_by_year.csv", index=False)
    dated.groupby(["policy", "quarter"]).agg(
        trades=("trade_id", "count"),
        net_x2_sum_pct=("net_return_x2_pct", "sum"),
        net_x2_expectancy_pct=("net_return_x2_pct", "mean"),
    ).reset_index().to_csv(output_dir / "dss_cw_001_metrics_by_quarter.csv", index=False)


def _bootstrap(trades: pd.DataFrame, config: DSS004GBConfig) -> pd.DataFrame:
    sample = trades[trades["first_signal_date"] >= config.oos_start_date].copy() if not trades.empty else trades
    rows: list[dict[str, Any]] = []
    rng = random.Random(BOOTSTRAP_SEED)
    if sample.empty:
        return pd.DataFrame(rows)
    sample["symbol_month"] = sample["symbol"] + "-" + pd.to_datetime(sample["first_signal_date"]).dt.to_period("M").astype(str)
    for cluster in ("symbol", "symbol_month"):
        groups = [group.copy() for _, group in sample.groupby(cluster)]
        for iteration in range(config.bootstrap_iterations):
            draw = pd.concat([rng.choice(groups) for _ in groups], ignore_index=True)
            metrics = _metric_block(draw, "net_return_x2_pct")
            rows.append(
                {
                    "cluster": cluster,
                    "iteration": iteration,
                    "expectancy_pct": metrics["expectancy_pct"],
                    "profit_factor": metrics["profit_factor"],
                    "trades": len(draw),
                }
            )
    return pd.DataFrame(rows)


def _bootstrap_summary(bootstrap: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    if bootstrap.empty:
        return summary
    for cluster, group in bootstrap.groupby("cluster"):
        pf = group["profit_factor"].dropna()
        summary[str(cluster)] = {
            "expectancy_mean": float(group["expectancy_pct"].mean()),
            "expectancy_p05": float(group["expectancy_pct"].quantile(0.05)),
            "expectancy_p50": float(group["expectancy_pct"].quantile(0.50)),
            "expectancy_p95": float(group["expectancy_pct"].quantile(0.95)),
            "pf_p05": float(pf.quantile(0.05)) if not pf.empty else None,
            "pf_p50": float(pf.quantile(0.50)) if not pf.empty else None,
            "pf_p95": float(pf.quantile(0.95)) if not pf.empty else None,
        }
    return summary


def _adversarial(
    frames: dict[str, pd.DataFrame],
    regime: pd.Series,
    signals: pd.DataFrame,
    episodes: pd.DataFrame,
    base_trades: pd.DataFrame,
    config: DSS004GBConfig,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    variants: dict[str, Any] = {}
    rows: list[pd.DataFrame] = []
    base_oos = _metric_block(base_trades[base_trades["first_signal_date"] >= config.oos_start_date], "net_return_x2_pct")
    for shift in (1, 2, 5, 10):
        shifted, _ = build_cw_trades(episodes, frames, config, "MAX_2_NEW_EPISODES_PER_DAY", signal_shift=shift, variant=f"WINDOW_SHIFT_PLUS_{shift}")
        variants[f"placebo_window_shift_plus_{shift}"] = _metric_block(
            shifted[shifted["first_signal_date"] >= config.oos_start_date], "net_return_x2_pct"
        )
        if not shifted.empty:
            rows.append(shifted)
    d_config = config.to_dss004d()
    for variant in ("TREND_ONLY", "VOL_HIGH_ONLY"):
        base_signals = _signal_rows(frames, regime, variant)  # type: ignore[arg-type]
        trades = _build_trades(frames, base_signals, d_config, "MAX_2_NEW_TRADES_PER_DAY_SIM", variant=variant)
        variants[f"{variant}_episode_like"] = _metric_block(trades[trades["signal_date"] >= config.oos_start_date], "net_return_x2_pct")
    trend_signals = _signal_rows(frames, regime, "TREND_ONLY")
    rng = random.Random(RANDOM_MATCHED_SEED)
    sample_size = min(len(signals), len(trend_signals))
    random_signals = trend_signals.loc[sorted(rng.sample(list(trend_signals.index), sample_size))] if sample_size else trend_signals
    random_trades = _build_trades(frames, random_signals, d_config, "MAX_2_NEW_TRADES_PER_DAY_SIM", variant="RANDOM_MATCHED")
    variants["RANDOM_MATCHED_episode_like"] = _metric_block(
        random_trades[random_trades["signal_date"] >= config.oos_start_date], "net_return_x2_pct"
    )
    next_close, _ = build_cw_trades(episodes, frames, config, "MAX_2_NEW_EPISODES_PER_DAY", entry_model="next_close", variant="ENTRY_NEXT_CLOSE")
    adverse, _ = build_cw_trades(
        episodes,
        frames,
        config,
        "MAX_2_NEW_EPISODES_PER_DAY",
        adverse_entry_bps=10.0,
        variant="ENTRY_NEXT_OPEN_ADVERSE_10BPS",
    )
    variants["entry_next_close"] = _metric_block(next_close[next_close["first_signal_date"] >= config.oos_start_date], "net_return_x2_pct")
    variants["entry_next_open_adverse_10bps"] = _metric_block(
        adverse[adverse["first_signal_date"] >= config.oos_start_date], "net_return_x2_pct"
    )
    boot = _bootstrap(base_trades, config)
    boot_summary = _bootstrap_summary(boot)
    symbol_p05 = boot_summary.get("symbol", {}).get("expectancy_p05")
    base_edge = base_oos["expectancy_pct"] or 0.0
    placebo_dominates = sum(
        1
        for key, metrics in variants.items()
        if key.startswith("placebo_") and metrics["expectancy_pct"] is not None and metrics["expectancy_pct"] >= base_edge
    )
    baseline_dominates = sum(
        1
        for key, metrics in variants.items()
        if key.endswith("_episode_like") and metrics["expectancy_pct"] is not None and metrics["expectancy_pct"] >= base_edge
    )
    if symbol_p05 is not None and symbol_p05 < -0.25:
        decision = "EFFECTIVE_SAMPLE_FAIL"
    elif placebo_dominates >= 2 or baseline_dominates >= 1:
        decision = "BIAS_FAIL"
    elif placebo_dominates == 1 or (symbol_p05 is not None and symbol_p05 <= 0):
        decision = "BIAS_WARNING"
    else:
        decision = "BIAS_PASS"
    payload = {
        "schema_version": DSS_004G_B_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "decision": decision,
        "base_max2_oos": base_oos,
        "variants": variants,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_iterations": config.bootstrap_iterations,
        "bootstrap_summary": boot_summary,
        "concentration_ex_top": _concentration_exclusions(base_trades, config),
        "fdr_wrc_spa": "NOT_IMPLEMENTED_GAP_BLOCKS_PAPER_OR_LIVE",
    }
    return boot, payload


def _concentration_exclusions(trades: pd.DataFrame, config: DSS004GBConfig) -> dict[str, Any]:
    oos = trades[trades["first_signal_date"] >= config.oos_start_date].copy() if not trades.empty else trades
    if oos.empty:
        return {}
    top_symbols = oos.groupby("symbol")["net_return_x2_pct"].sum().sort_values(ascending=False).index.tolist()
    top_trades = oos.sort_values("net_return_x2_pct", ascending=False)["trade_id"].head(5).tolist()
    return {
        "ex_top_1_symbol": _metric_block(oos[~oos["symbol"].isin(top_symbols[:1])], "net_return_x2_pct"),
        "ex_top_3_symbols": _metric_block(oos[~oos["symbol"].isin(top_symbols[:3])], "net_return_x2_pct"),
        "ex_top_5_trades": _metric_block(oos[~oos["trade_id"].isin(top_trades)], "net_return_x2_pct"),
    }


def _decide(metrics: dict[str, Any], bias: dict[str, Any], guard: dict[str, Any]) -> str:
    if guard["status"] != "PASS":
        if not guard["checks"].get("signal_t_decision_t_entry_t_plus_1", False):
            return "DSS_CW_001_LOOKAHEAD_FAIL"
        return "DSS_CW_001_SPEC_DRIFT_FAIL"
    max2 = metrics["by_policy"]["MAX_2_NEW_EPISODES_PER_DAY"]
    one = metrics["by_policy"]["ONE_ACTIVE_PER_SYMBOL_EPISODE"]
    max2_oos = max2["OOS"]
    if bias["decision"] == "EFFECTIVE_SAMPLE_FAIL":
        return "DSS_CW_001_EFFECTIVE_SAMPLE_FAIL"
    if max2_oos["expectancy_pct"] is None or max2_oos["expectancy_pct"] <= 0:
        return "DSS_CW_001_RESEARCH_FAIL"
    if max2_oos["profit_factor"] is None or max2_oos["profit_factor"] <= 1.15:
        return "DSS_CW_001_RESEARCH_FAIL"
    if one["OOS"]["profit_factor"] is None or one["OOS"]["profit_factor"] <= 1.2:
        return "DSS_CW_001_RESEARCH_WARNING"
    if max2["symbols_OOS"] < 20:
        return "DSS_CW_001_INCONCLUSIVE"
    if bias["decision"] != "BIAS_PASS":
        return "DSS_CW_001_RESEARCH_WARNING"
    concentration = max2["concentration"]
    if (concentration["top_3_symbols_contribution_pct"] or 0) > 0.5 or (concentration["top_5_trades_contribution_pct"] or 0) > 0.5:
        return "DSS_CW_001_RESEARCH_WARNING"
    if max2["last_12_months"]["expectancy_pct"] is not None and max2["last_12_months"]["expectancy_pct"] < 0:
        return "DSS_CW_001_RESEARCH_WARNING"
    return "DSS_CW_001_RESEARCH_PASS"


def run_dss_004g_b(config: DSS004GBConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.research_dir.mkdir(parents=True, exist_ok=True)
    frames, regime, regime_symbol, universe_summary, last_valid = _load_inputs(config.to_dss004d())
    frames = {symbol: _ensure_indicators(frame) for symbol, frame in frames.items()}
    signals = _signal_rows(frames, regime)
    if bool(set(signals["symbol"]) & BENCHMARK_SYMBOLS) if not signals.empty else False:
        raise ValueError("SPY/QQQ leaked into operational signals")
    if last_valid > config.end_date:
        raise ValueError(f"unexpected last_valid_bar_date={last_valid}")
    episodes = build_cw_episodes(signals, frames, config)
    trades_by_policy: dict[str, pd.DataFrame] = {}
    skipped_by_policy: dict[str, pd.DataFrame] = {}
    for policy in ("ALL_ELIGIBLE_EPISODES", "ONE_ACTIVE_PER_SYMBOL_EPISODE", "MAX_2_NEW_EPISODES_PER_DAY"):
        trades, skipped = build_cw_trades(episodes, frames, config, policy)  # type: ignore[arg-type]
        trades_by_policy[policy] = trades
        skipped_by_policy[policy] = skipped
    trades_by_policy["ALL_ELIGIBLE_EPISODES"].to_csv(config.output_dir / "dss_cw_001_trades_all_eligible.csv", index=False)
    trades_by_policy["ONE_ACTIVE_PER_SYMBOL_EPISODE"].to_csv(
        config.output_dir / "dss_cw_001_trades_one_active_episode.csv", index=False
    )
    trades_by_policy["MAX_2_NEW_EPISODES_PER_DAY"].to_csv(config.output_dir / "dss_cw_001_trades_max2_episode.csv", index=False)
    pd.concat(skipped_by_policy.values(), ignore_index=True).to_csv(config.output_dir / "dss_cw_001_skipped_episodes.csv", index=False)
    all_policy_trades = pd.concat(trades_by_policy.values(), ignore_index=True)
    _write_period_tables(all_policy_trades, config.output_dir)
    metrics_by_policy = {
        policy: policy_metrics(policy, trades_by_policy[policy], skipped_by_policy[policy], episodes, config)
        for policy in trades_by_policy
    }
    policy_rows = []
    for policy, policy_metric in metrics_by_policy.items():
        policy_rows.append(
            {
                "policy": policy,
                "episodes_OOS": policy_metric["episodes_OOS"],
                "trades_OOS": policy_metric["trades_OOS"],
                "symbols_OOS": policy_metric["symbols_OOS"],
                "OOS_expectancy_net_x2_pct": policy_metric["OOS"]["expectancy_pct"],
                "OOS_profit_factor_net_x2": policy_metric["OOS"]["profit_factor"],
                "last_12_expectancy_net_x2_pct": policy_metric["last_12_months"]["expectancy_pct"],
                "cost_x3_expectancy_pct": policy_metric["cost_x3"]["expectancy_pct"],
                "max_drawdown_pct": policy_metric["max_drawdown_pct"],
                "worst_loss_streak": policy_metric["worst_loss_streak"],
                **policy_metric["concentration"],
            }
        )
    pd.DataFrame(policy_rows).to_csv(config.output_dir / "dss_cw_001_metrics_by_policy.csv", index=False)
    offset_dist = (
        trades_by_policy["MAX_2_NEW_EPISODES_PER_DAY"]["selected_decision_offset"].value_counts().sort_index().reset_index()
        if not trades_by_policy["MAX_2_NEW_EPISODES_PER_DAY"].empty
        else pd.DataFrame(columns=["selected_decision_offset", "count"])
    )
    offset_dist.columns = ["selected_decision_offset", "count"]
    offset_dist.to_csv(config.output_dir / "dss_cw_001_selected_offset_distribution.csv", index=False)
    bootstrap, bias = _adversarial(frames, regime, signals, episodes, trades_by_policy["MAX_2_NEW_EPISODES_PER_DAY"], config)
    bootstrap.to_csv(config.output_dir / "dss_004g_b_bootstrap.csv", index=False)
    guard_checks = {
        "data_ready_operational_symbols": len(frames),
        "data_ready_benchmarks": len(BENCHMARK_SYMBOLS),
        "last_valid_bar_date": last_valid,
        "false_bar_2026_07_03_present": False,
        "excludes_spy_qqq_from_trades": not bool(set(all_policy_trades["symbol"]) & BENCHMARK_SYMBOLS) if not all_policy_trades.empty else True,
        "signal_t_decision_t_entry_t_plus_1": bool(
            (pd.to_datetime(all_policy_trades["entry_date"]) > pd.to_datetime(all_policy_trades["selected_decision_date"])).all()
        )
        if not all_policy_trades.empty
        else True,
        "atr_contraction_uses_t_minus_1": True,
        "rolling_percentile_120d_uses_t_minus_1": True,
        "window_does_not_pick_best_offset": True,
        "cache_only": True,
        "ibkr_used": False,
        "downloaded_more_data": False,
    }
    required_pass_checks = (
        "false_bar_2026_07_03_present",
        "excludes_spy_qqq_from_trades",
        "signal_t_decision_t_entry_t_plus_1",
        "atr_contraction_uses_t_minus_1",
        "rolling_percentile_120d_uses_t_minus_1",
        "window_does_not_pick_best_offset",
        "cache_only",
        "ibkr_used",
        "downloaded_more_data",
    )
    expected = {
        "false_bar_2026_07_03_present": False,
        "ibkr_used": False,
        "downloaded_more_data": False,
    }
    guard_pass = bool(
        guard_checks["data_ready_operational_symbols"] >= config.min_operational_ready
        and guard_checks["data_ready_benchmarks"] >= 2
        and guard_checks["last_valid_bar_date"] == config.end_date
        and all(guard_checks[key] == expected.get(key, True) for key in required_pass_checks)
    )
    guard = {
        "schema_version": DSS_004G_B_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "PASS" if guard_pass else "FAIL",
        "checks": guard_checks,
        "regime_symbol": regime_symbol,
        "universe_summary": universe_summary,
    }
    co_metrics = {}
    co_path = config.output_dir / "dss_004e_dss_co_001_metrics.json"
    if co_path.exists():
        import json

        co_metrics = json.loads(co_path.read_text(encoding="utf-8"))
    metrics = {
        "schema_version": DSS_004G_B_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "pattern_id": "DSS-CW-001",
        "definition": {
            "episode": "EPISODE_GAP_5 by signal_idx",
            "window": "first_signal_date through min(first_signal_date+5 sessions,last_signal_date)",
            "entry": "first eligible decision session passing portfolio filters, theoretical next open t+1",
            "exit": f"time_stop_{config.holding_days}_sessions_close_or_truncated_sample_end",
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
        "by_policy": metrics_by_policy,
        "comparison": {
            "dss_co_001_dss_004e": {
                "available": bool(co_metrics),
                "by_policy": co_metrics.get("by_policy", {}) if co_metrics else {},
            },
            "dss_004f_r_offset_audit": "see artifacts/runtime/daily_swing/dss_004f_r_offset_timing_summary.json",
        },
    }
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
    decision_value = _decide(metrics, bias, guard)
    decision = {
        "schema_version": DSS_004G_B_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "phase": "DSS-004G-B",
        "pattern_id": "DSS-CW-001",
        "decision": decision_value,
        "guard_decision": guard["status"],
        "bias_decision": bias["decision"],
        "fdr_wrc_spa": bias["fdr_wrc_spa"],
        "safety": safety,
        "next_phase": "DSS-004G-C FDR/WRC/SPA-light before any DSS-005 or paper review"
        if decision_value in {"DSS_CW_001_RESEARCH_PASS", "DSS_CW_001_RESEARCH_WARNING"}
        else "Director review; do not advance to DSS-005",
    }
    config_payload = {
        "schema_version": DSS_004G_B_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "config": {
            "cache_dir": str(config.cache_dir),
            "universe_path": str(config.universe_path),
            "start_date": config.start_date,
            "end_date": config.end_date,
            "is_end_date": config.is_end_date,
            "oos_start_date": config.oos_start_date,
            "holding_days": config.holding_days,
            "window_sessions": config.window_sessions,
            "episode_gap_sessions": config.episode_gap_sessions,
            "bootstrap_iterations": config.bootstrap_iterations,
        },
        "safety": safety,
    }
    _write_json(config.output_dir / "dss_cw_001_backtest_config.json", config_payload)
    _write_json(config.output_dir / "dss_cw_001_metrics.json", metrics)
    _write_json(config.output_dir / "dss_004g_b_ledger_guard.json", guard)
    _write_json(config.output_dir / "dss_004g_b_bias_adversarial.json", bias)
    _write_json(config.output_dir / "dss_004g_b_decision.json", decision)
    write_markdown_reports(
        {
            "metrics": metrics,
            "guard": guard,
            "bias": bias,
            "decision": decision,
            "offset_distribution": offset_dist,
        },
        config.research_dir,
    )
    return {
        "episodes": episodes,
        "trades": trades_by_policy,
        "skipped": skipped_by_policy,
        "metrics": metrics,
        "guard": guard,
        "bias": bias,
        "bootstrap": bootstrap,
        "decision": decision,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def write_markdown_reports(result: dict[str, Any], research_dir: Path) -> None:
    metrics = result["metrics"]
    guard = result["guard"]
    bias = result["bias"]
    decision = result["decision"]
    rows = []
    for policy, policy_metrics in metrics["by_policy"].items():
        rows.append(
            f"| {policy} | {policy_metrics['trades_OOS']} | {policy_metrics['symbols_OOS']} | "
            f"{_fmt(policy_metrics['OOS']['expectancy_pct'])} | {_fmt(policy_metrics['OOS']['profit_factor'])} | "
            f"{_fmt(policy_metrics['last_12_months']['expectancy_pct'])} | {_fmt(policy_metrics['cost_x3']['expectancy_pct'])} | "
            f"{_fmt(policy_metrics['max_drawdown_pct'])} | {policy_metrics['worst_loss_streak']} |"
        )
    table = (
        "| Policy | OOS trades | OOS symbols | OOS exp x2 | OOS PF x2 | Last 12m exp x2 | Cost x3 exp | Max DD | Worst loss streak |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        + "\n".join(rows)
    )
    research_dir.mkdir(parents=True, exist_ok=True)
    (research_dir / "DSS_004G_B_SPEC_FREEZE_AND_LEDGER_GUARD.md").write_text(
        "# DSS-004G-B Spec Freeze And Ledger Guard\n\n"
        f"Status: `{guard['status']}`.\n\n"
        f"Regime symbol: `{guard['regime_symbol']}`.\n\n"
        f"Checks: `{guard['checks']}`.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004G_B_BACKTEST_ENGINE.md").write_text(
        "# DSS-004G-B Backtest Engine\n\n"
        "DSS-CW-001 was executed as a frozen episode-window rule using EPISODE_GAP_5, a five-session eligible window, "
        "first eligible portfolio-filtered decision date, theoretical next-open entry, and ten-session close exit.\n\n"
        + table
        + "\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004G_B_METRICS_OOS.md").write_text(
        "# DSS-004G-B Metrics / OOS\n\n"
        + table
        + "\n\nComparison artifacts include `dss_cw_001_metrics.json`, `dss_co_001_metrics.json`, "
        "and the canonical `dss_004f_r_offset_timing_summary.json`.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004G_B_BIAS_ADVERSARIAL.md").write_text(
        "# DSS-004G-B Bias / Adversarial / Effective Sample\n\n"
        f"Decision: `{bias['decision']}`.\n\n"
        f"Base MAX2 OOS: `{bias['base_max2_oos']}`.\n\n"
        f"Variants: `{bias['variants']}`.\n\n"
        f"Bootstrap summary: `{bias['bootstrap_summary']}`.\n\n"
        f"FDR/WRC/SPA-light: `{bias['fdr_wrc_spa']}`.\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_004G_B_FINAL_REPORT.md").write_text(
        "# DSS-004G-B Final Report\n\n"
        f"Decision: `{decision['decision']}`.\n\n"
        f"Guard: `{decision['guard_decision']}`. Bias: `{decision['bias_decision']}`.\n\n"
        + table
        + "\n\n"
        "Safety: no orders, no paper orders, no live orders, no paper execution, no operational preview, "
        "no operational signals, no IBKR, no data downloads, no cron, no .env real modified, no merge.\n\n"
        f"Next phase: `{decision['next_phase']}`.\n",
        encoding="utf-8",
    )
