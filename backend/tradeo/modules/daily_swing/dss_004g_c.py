from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from tradeo.modules.daily_swing.dss_004 import BENCHMARK_SYMBOLS, _metric_block, _write_json, utc_now
from tradeo.modules.daily_swing.dss_004d import _build_trades, _ensure_indicators, _load_inputs, _signal_rows, _top_concentration
from tradeo.modules.daily_swing.dss_004g_b import DSS004GBConfig, build_cw_episodes, build_cw_trades

DSS_004G_C_SCHEMA_VERSION = "tradeo.daily_swing.dss_004g_c.v1"
BOOTSTRAP_SEED = 40411
BOOTSTRAP_ITERATIONS = 1000
FDR_Q = 0.05


@dataclass(frozen=True)
class DSS004GCConfig:
    cache_dir: Path
    universe_path: Path
    start_date: str
    end_date: str
    is_end_date: str
    oos_start_date: str
    output_dir: Path
    research_dir: Path
    bootstrap_iterations: int = BOOTSTRAP_ITERATIONS

    def to_dss004gb(self) -> DSS004GBConfig:
        return DSS004GBConfig(
            cache_dir=self.cache_dir,
            universe_path=self.universe_path,
            start_date=self.start_date,
            end_date=self.end_date,
            is_end_date=self.is_end_date,
            oos_start_date=self.oos_start_date,
            output_dir=self.output_dir,
            research_dir=self.research_dir,
            bootstrap_iterations=100,
        )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _oos(trades: pd.DataFrame, config: DSS004GCConfig) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    date_col = "first_signal_date" if "first_signal_date" in trades.columns else "signal_date"
    out = trades[trades[date_col].astype(str) >= config.oos_start_date].copy()
    out["first_signal_date"] = out[date_col].astype(str)
    if "variant" not in out.columns:
        out["variant"] = ""
    return out


def _normalise_trade_columns(trades: pd.DataFrame, strategy_id: str, config: DSS004GCConfig) -> pd.DataFrame:
    out = _oos(trades, config)
    if out.empty:
        return out
    out = out.copy()
    out["strategy_id"] = strategy_id
    out["symbol_month"] = out["symbol"].astype(str) + "-" + pd.to_datetime(out["first_signal_date"]).dt.to_period("M").astype(str)
    return out


def build_test_matrix(output_dir: Path) -> pd.DataFrame:
    rows = [
        ("DSS_CW_001_BASE_MAX2", "artifacts/runtime/daily_swing/dss_cw_001_trades_max2_episode.csv", "candidate", "OOS trades", "MAX_2_NEW_EPISODES_PER_DAY", True, "Frozen DSS-CW-001 base"),
        ("DSS_CW_WINDOW_PLACEBO_PLUS_1", "recomputed cache-only from DSS-CW-001 episodes", "adversarial", "OOS trades", "MAX_2_NEW_EPISODES_PER_DAY", True, "Declared timing placebo"),
        ("DSS_CW_WINDOW_PLACEBO_PLUS_2", "recomputed cache-only from DSS-CW-001 episodes", "adversarial", "OOS trades", "MAX_2_NEW_EPISODES_PER_DAY", True, "Declared timing placebo"),
        ("DSS_CW_WINDOW_PLACEBO_PLUS_5", "recomputed cache-only from DSS-CW-001 episodes", "adversarial", "OOS trades", "MAX_2_NEW_EPISODES_PER_DAY", True, "Declared timing placebo"),
        ("DSS_CW_WINDOW_PLACEBO_PLUS_10", "recomputed cache-only from DSS-CW-001 episodes", "adversarial", "OOS trades", "MAX_2_NEW_EPISODES_PER_DAY", True, "Declared timing placebo"),
        ("DSS_CO_001_MAX2", "artifacts/runtime/daily_swing/dss_004e_dss_co_001_trades_max2_sim.csv", "baseline", "OOS trades", "MAX_2_NEW_TRADES_PER_DAY_SIM", True, "Canonical research-150 CO comparison"),
        ("TREND_ONLY_EPISODE_LIKE", "recomputed cache-only from research cache", "baseline", "OOS trades", "MAX_2_NEW_TRADES_PER_DAY_SIM", True, "Declared baseline"),
        ("RANDOM_MATCHED_EPISODE_LIKE", "recomputed cache-only from research cache", "baseline", "OOS trades", "MAX_2_NEW_TRADES_PER_DAY_SIM", True, "Declared matched baseline"),
        ("VOL_HIGH_ONLY_EPISODE_LIKE", "recomputed cache-only from research cache", "baseline", "OOS trades", "MAX_2_NEW_TRADES_PER_DAY_SIM", True, "Declared baseline"),
        ("DSS_BO_001_REFERENCE", "artifacts/runtime/daily_swing/dss_bo_001_trades.csv", "reference", "OOS trades", "REFERENCE_ONLY", False, "Existing artifact is historical 49-symbol reference, not research-150 compatible"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "strategy_id",
            "source_artifact",
            "role",
            "sample_type",
            "expected_policy",
            "included_in_stat_family",
            "included_reason",
        ],
    )


def bh_qvalues(pvalues: list[float]) -> list[float]:
    if not pvalues:
        return []
    indexed = sorted(enumerate(pvalues), key=lambda item: item[1], reverse=True)
    n = len(pvalues)
    out = [1.0] * n
    running = 1.0
    for rank_from_end, (idx, pvalue) in enumerate(indexed):
        rank = n - rank_from_end
        running = min(running, float(pvalue) * n / rank)
        out[idx] = min(1.0, running)
    return out


def _bootstrap_means(trades: pd.DataFrame, cluster: str, iterations: int, seed: int) -> list[float]:
    if trades.empty:
        return []
    rng = random.Random(seed)
    groups = [group["net_return_x2_pct"].astype(float).tolist() for _, group in trades.groupby(cluster)]
    if not groups:
        return []
    means: list[float] = []
    for _ in range(iterations):
        sample: list[float] = []
        for _ in groups:
            sample.extend(rng.choice(groups))
        means.append(float(pd.Series(sample).mean()))
    return means


def _pvalue_mean_positive(trades: pd.DataFrame, cluster: str, iterations: int, seed: int) -> tuple[float, float, float]:
    means = _bootstrap_means(trades, cluster, iterations, seed)
    if not means:
        return 1.0, 0.0, 0.0
    pvalue = (sum(mean <= 0 for mean in means) + 1) / (len(means) + 1)
    return float(pvalue), float(pd.Series(means).quantile(0.05)), float(pd.Series(means).median())


def fdr_light(family: dict[str, pd.DataFrame], config: DSS004GCConfig) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, (strategy_id, trades) in enumerate(family.items()):
        metrics = _metric_block(trades, "net_return_x2_pct")
        symbol_p, symbol_p05, symbol_p50 = _pvalue_mean_positive(trades, "symbol", config.bootstrap_iterations, BOOTSTRAP_SEED + i)
        sm_p, sm_p05, sm_p50 = _pvalue_mean_positive(trades, "symbol_month", config.bootstrap_iterations, BOOTSTRAP_SEED + 100 + i)
        rows.append(
            {
                "strategy_id": strategy_id,
                "trades": metrics["trades"],
                "symbols": metrics["symbols"],
                "oos_expectancy_net_x2_pct": metrics["expectancy_pct"],
                "oos_profit_factor_net_x2": metrics["profit_factor"],
                "winrate": metrics["winrate"],
                "bootstrap_p_value_mean_le_0": max(symbol_p, sm_p),
                "bootstrap_symbol_p_value": symbol_p,
                "bootstrap_symbol_month_p_value": sm_p,
                "bootstrap_symbol_p05_expectancy_pct": symbol_p05,
                "bootstrap_symbol_p50_expectancy_pct": symbol_p50,
                "bootstrap_symbol_month_p05_expectancy_pct": sm_p05,
                "bootstrap_symbol_month_p50_expectancy_pct": sm_p50,
                "effective_sample_symbol_month": int(trades["symbol_month"].nunique()) if not trades.empty else 0,
            }
        )
    result = pd.DataFrame(rows).sort_values("oos_expectancy_net_x2_pct", ascending=False).reset_index(drop=True)
    result["base_rank"] = int(result.index[result["strategy_id"] == "DSS_CW_001_BASE_MAX2"][0] + 1)
    qvalues = bh_qvalues(result["bootstrap_p_value_mean_le_0"].astype(float).tolist())
    result["bh_q_value"] = qvalues
    result["bonferroni_p_value"] = (result["bootstrap_p_value_mean_le_0"].astype(float) * len(result)).clip(upper=1.0)
    result["significant_after_fdr"] = result["bh_q_value"] <= FDR_Q
    result["significant_after_bonferroni"] = result["bonferroni_p_value"] <= FDR_Q
    base = result[result["strategy_id"] == "DSS_CW_001_BASE_MAX2"].iloc[0].to_dict()
    best = result.iloc[0].to_dict()
    placebo_dominance = bool(
        result[result["strategy_id"].str.contains("PLACEBO")]["oos_expectancy_net_x2_pct"].max()
        > float(base["oos_expectancy_net_x2_pct"])
    )
    if placebo_dominance:
        decision = "FDR_PLACEBO_DOMINANCE_FAIL"
    elif not bool(base["significant_after_fdr"]):
        decision = "FDR_BASE_FAIL"
    elif not bool(base["significant_after_bonferroni"]):
        decision = "FDR_BASE_WARNING"
    else:
        decision = "FDR_BASE_PASS"
    summary = {
        "schema_version": DSS_004G_C_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_iterations": config.bootstrap_iterations,
        "fdr_q": FDR_Q,
        "decision": decision,
        "base_strategy_id": "DSS_CW_001_BASE_MAX2",
        "base_rank": int(base["base_rank"]),
        "best_strategy_id": str(best["strategy_id"]),
        "placebo_dominates_base": placebo_dominance,
    }
    return result, summary


def wrc_spa_light(family: dict[str, pd.DataFrame], config: DSS004GCConfig) -> tuple[pd.DataFrame, dict[str, Any]]:
    observed = {sid: float(df["net_return_x2_pct"].mean()) if not df.empty else 0.0 for sid, df in family.items()}
    base_observed = observed["DSS_CW_001_BASE_MAX2"]
    observed_gap = max(observed.values()) - base_observed
    rng = random.Random(BOOTSTRAP_SEED + 5000)
    boot_rows: list[dict[str, Any]] = []
    for iteration in range(config.bootstrap_iterations):
        means: dict[str, float] = {}
        for sid, df in family.items():
            groups = [group["net_return_x2_pct"].astype(float).tolist() for _, group in df.groupby("symbol_month")]
            sample: list[float] = []
            for _ in groups:
                sample.extend(rng.choice(groups))
            means[sid] = float(pd.Series(sample).mean()) if sample else 0.0
        family_best_id = max(means, key=lambda sid: means[sid])
        boot_rows.append(
            {
                "iteration": iteration,
                "best_strategy_id": family_best_id,
                "family_max_expectancy_pct": means[family_best_id],
                "base_expectancy_pct": means["DSS_CW_001_BASE_MAX2"],
                "family_minus_base_pct": means[family_best_id] - means["DSS_CW_001_BASE_MAX2"],
            }
        )
    boot = pd.DataFrame(boot_rows)
    pvalue = float(((boot["family_minus_base_pct"] >= observed_gap).sum() + 1) / (len(boot) + 1)) if not boot.empty else 1.0
    best_strategy_id = max(observed, key=lambda sid: observed[sid])
    base_rank = int(sorted(observed, key=observed.get, reverse=True).index("DSS_CW_001_BASE_MAX2") + 1)
    if best_strategy_id != "DSS_CW_001_BASE_MAX2" and "PLACEBO" in best_strategy_id:
        decision = "WRC_SPA_PLACEBO_BEST_FAIL"
    elif base_rank > 1 and pvalue <= 0.25:
        decision = "WRC_SPA_BASE_FAIL"
    elif base_rank > 1:
        decision = "WRC_SPA_BASE_WARNING"
    else:
        decision = "WRC_SPA_BASE_PASS"
    summary = {
        "schema_version": DSS_004G_C_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "method": "symbol_month bootstrap family-max approximation; research-only, not formal WRC/SPA",
        "bootstrap_seed": BOOTSTRAP_SEED + 5000,
        "bootstrap_iterations": config.bootstrap_iterations,
        "decision": decision,
        "base_strategy_id": "DSS_CW_001_BASE_MAX2",
        "best_strategy_id": best_strategy_id,
        "base_rank": base_rank,
        "family_max_expectancy_pct": observed[best_strategy_id],
        "base_expectancy_pct": base_observed,
        "approximate_p_value_base_vs_family": pvalue,
        "limitations": "Approximation uses resampled symbol-month return clusters and compares family max to base; it is not a formal SPA implementation.",
    }
    return boot, summary


def timing_verdict(fdr: pd.DataFrame, family: dict[str, pd.DataFrame]) -> dict[str, Any]:
    base = fdr[fdr["strategy_id"] == "DSS_CW_001_BASE_MAX2"].iloc[0].to_dict()
    placebo = fdr[fdr["strategy_id"].str.contains("PLACEBO")].copy()
    placebo_dominators = placebo[placebo["oos_expectancy_net_x2_pct"] >= float(base["oos_expectancy_net_x2_pct"])]
    rows = []
    for _, row in placebo.iterrows():
        trades = family[str(row["strategy_id"])]
        rows.append(
            {
                "strategy_id": row["strategy_id"],
                "expectancy_pct": row["oos_expectancy_net_x2_pct"],
                "profit_factor": row["oos_profit_factor_net_x2"],
                "q_value": row["bh_q_value"],
                "bootstrap_symbol_p05_expectancy_pct": row["bootstrap_symbol_p05_expectancy_pct"],
                "last_12_months_expectancy_pct": _metric_block(trades[trades["first_signal_date"] >= "2025-07-02"], "net_return_x2_pct")["expectancy_pct"],
                "max_drawdown_pct": _max_drawdown_pct(trades),
                **_top_concentration(trades.rename(columns={"episode_id": "trade_id"})),
            }
        )
    if len(placebo_dominators) >= 2:
        decision = "TIMING_PLACEBO_DOMINANCE_FAIL"
        classification = "placebos dominate base; timing is not specific"
    elif len(placebo_dominators) == 1:
        decision = "TIMING_WINDOW_INDISTINGUISHABLE_WARNING"
        classification = "base and placebos form an indistinguishable timing window"
    elif float(base["oos_expectancy_net_x2_pct"]) > placebo["oos_expectancy_net_x2_pct"].max():
        decision = "TIMING_SPECIFICITY_PASS"
        classification = "base dominates declared placebos"
    else:
        decision = "TIMING_INCONCLUSIVE"
        classification = "timing comparison inconclusive"
    return {
        "schema_version": DSS_004G_C_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "decision": decision,
        "classification": classification,
        "base": base,
        "placebos": rows,
        "placebo_dominators": placebo_dominators["strategy_id"].tolist(),
    }


def _max_drawdown_pct(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    ordered = trades.sort_values(["first_signal_date", "symbol"]).copy()
    equity = ordered["net_return_x2_pct"].astype(float).cumsum()
    drawdown = equity - equity.cummax()
    return abs(float(drawdown.min())) if not drawdown.empty else 0.0


def final_decision(fdr_summary: dict[str, Any], wrc_summary: dict[str, Any], timing: dict[str, Any]) -> str:
    if timing["decision"] == "TIMING_PLACEBO_DOMINANCE_FAIL":
        return "DSS_CW_001_RESEARCH_FAIL_TIMING_NOT_SPECIFIC"
    if fdr_summary["decision"] == "FDR_BASE_FAIL":
        return "DSS_CW_001_RESEARCH_FAIL_MULTIPLE_TESTING"
    if fdr_summary["decision"] == "FDR_PLACEBO_DOMINANCE_FAIL":
        return "DSS_CW_001_RESEARCH_FAIL_PLACEBO_DOMINANCE"
    if wrc_summary["decision"] == "WRC_SPA_PLACEBO_BEST_FAIL":
        return "DSS_CW_001_RESEARCH_FAIL_PLACEBO_DOMINANCE"
    if timing["decision"] == "TIMING_WINDOW_INDISTINGUISHABLE_WARNING":
        return "DSS_CW_001_RESEARCH_WARNING_STAT_LIGHT"
    if fdr_summary["decision"] == "FDR_BASE_PASS" and wrc_summary["decision"] == "WRC_SPA_BASE_PASS":
        return "DSS_CW_001_RESEARCH_SURVIVES_STAT_LIGHT"
    return "DSS_CW_001_RESEARCH_WARNING_STAT_LIGHT"


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    columns = list(df.columns)
    widths = {column: max(len(str(column)), *(len(str(value)) for value in df[column].tolist())) for column in columns}
    header = "| " + " | ".join(str(column).ljust(widths[column]) for column in columns) + " |"
    separator = "| " + " | ".join("-" * widths[column] for column in columns) + " |"
    rows = [
        "| " + " | ".join(str(row[column]).ljust(widths[column]) for column in columns) + " |"
        for _, row in df.iterrows()
    ]
    return "\n".join([header, separator, *rows])


def _build_family(config: DSS004GCConfig) -> dict[str, pd.DataFrame]:
    gb_config = config.to_dss004gb()
    frames, regime, _, _, last_valid = _load_inputs(gb_config.to_dss004d())
    frames = {symbol: _ensure_indicators(frame) for symbol, frame in frames.items()}
    if last_valid != config.end_date:
        raise ValueError(f"unexpected last_valid_bar_date={last_valid}")
    signals = _signal_rows(frames, regime)
    episodes = build_cw_episodes(signals, frames, gb_config)
    family: dict[str, pd.DataFrame] = {}
    family["DSS_CW_001_BASE_MAX2"] = _normalise_trade_columns(
        pd.read_csv(config.output_dir / "dss_cw_001_trades_max2_episode.csv"), "DSS_CW_001_BASE_MAX2", config
    )
    for shift in (1, 2, 5, 10):
        trades, _ = build_cw_trades(episodes, frames, gb_config, "MAX_2_NEW_EPISODES_PER_DAY", signal_shift=shift, variant=f"WINDOW_SHIFT_PLUS_{shift}")
        family[f"DSS_CW_WINDOW_PLACEBO_PLUS_{shift}"] = _normalise_trade_columns(trades, f"DSS_CW_WINDOW_PLACEBO_PLUS_{shift}", config)
    family["DSS_CO_001_MAX2"] = _normalise_trade_columns(
        pd.read_csv(config.output_dir / "dss_004e_dss_co_001_trades_max2_sim.csv"), "DSS_CO_001_MAX2", config
    )
    d_config = gb_config.to_dss004d()
    for variant, strategy_id in (("TREND_ONLY", "TREND_ONLY_EPISODE_LIKE"), ("VOL_HIGH_ONLY", "VOL_HIGH_ONLY_EPISODE_LIKE")):
        base_signals = _signal_rows(frames, regime, variant)
        trades = _build_trades(frames, base_signals, d_config, "MAX_2_NEW_TRADES_PER_DAY_SIM", variant=variant)
        family[strategy_id] = _normalise_trade_columns(trades, strategy_id, config)
    trend_signals = _signal_rows(frames, regime, "TREND_ONLY")
    rng = random.Random(40408)
    sample_size = min(len(signals), len(trend_signals))
    random_signals = trend_signals.loc[sorted(rng.sample(list(trend_signals.index), sample_size))] if sample_size else trend_signals
    random_trades = _build_trades(frames, random_signals, d_config, "MAX_2_NEW_TRADES_PER_DAY_SIM", variant="RANDOM_MATCHED")
    family["RANDOM_MATCHED_EPISODE_LIKE"] = _normalise_trade_columns(random_trades, "RANDOM_MATCHED_EPISODE_LIKE", config)
    for strategy_id, trades in family.items():
        if not trades.empty and bool(set(trades["symbol"]) & BENCHMARK_SYMBOLS):
            raise ValueError(f"benchmark leaked into {strategy_id}")
    return family


def artifact_integrity(config: DSS004GCConfig, matrix: pd.DataFrame) -> dict[str, Any]:
    required = [
        "research/daily_swing/DSS_004G_B_FINAL_REPORT.md",
        "artifacts/runtime/daily_swing/dss_004g_b_decision.json",
        "artifacts/runtime/daily_swing/dss_004g_b_bias_adversarial.json",
        "artifacts/runtime/daily_swing/dss_cw_001_metrics.json",
        "artifacts/runtime/daily_swing/dss_cw_001_trades_max2_episode.csv",
        "artifacts/runtime/daily_swing/dss_cw_001_selected_offset_distribution.csv",
    ]
    missing = [path for path in required if not Path(path).exists()]
    guard = _read_json(config.output_dir / "dss_004g_b_ledger_guard.json")
    metrics = _read_json(config.output_dir / "dss_cw_001_metrics.json")
    co_metrics = _read_json(config.output_dir / "dss_004e_dss_co_001_metrics.json")
    old_co_metrics = _read_json(config.output_dir / "dss_co_001_metrics.json") if (config.output_dir / "dss_co_001_metrics.json").exists() else {}
    return {
        "schema_version": DSS_004G_C_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "required_artifacts_missing": missing,
        "status": "PASS" if not missing and guard["status"] == "PASS" else "FAIL",
        "guard_status": guard["status"],
        "research_cache_used": metrics["cache_dir"],
        "oos_start_date": metrics["oos_start_date"],
        "last_valid_bar_date": metrics["last_valid_bar_date"],
        "false_bar_2026_07_03_present": guard["checks"]["false_bar_2026_07_03_present"],
        "spy_qqq_excluded": guard["checks"]["excludes_spy_qqq_from_trades"],
        "test_matrix_rows": int(len(matrix)),
        "metric_correction": {
            "source": "artifact JSON/CSV, not chat summaries",
            "cw_max2_oos_expectancy_pct": metrics["by_policy"]["MAX_2_NEW_EPISODES_PER_DAY"]["OOS"]["expectancy_pct"],
            "cw_max2_pf": metrics["by_policy"]["MAX_2_NEW_EPISODES_PER_DAY"]["OOS"]["profit_factor"],
            "co_research150_max2_oos_expectancy_pct": co_metrics["by_policy"]["MAX_2_NEW_TRADES_PER_DAY_SIM"]["OOS"]["expectancy_pct"],
            "co_research150_max2_pf": co_metrics["by_policy"]["MAX_2_NEW_TRADES_PER_DAY_SIM"]["OOS"]["profit_factor"],
            "old_co_artifact_compatible": False if old_co_metrics else None,
            "old_co_artifact_reason": "standalone dss_co_001 has 49 OOS symbols, so it is not the research-150 comparator",
        },
    }


def write_markdown_reports(result: dict[str, Any], config: DSS004GCConfig) -> None:
    config.research_dir.mkdir(parents=True, exist_ok=True)
    matrix = result["matrix"]
    integrity = result["integrity"]
    fdr = result["fdr"]
    fdr_summary = result["fdr_summary"]
    wrc_summary = result["wrc_summary"]
    timing = result["timing"]
    decision = result["decision"]
    (config.research_dir / "DSS_004G_C_TEST_MATRIX_AND_ARTIFACT_INTEGRITY.md").write_text(
        "# DSS-004G-C Test Matrix And Artifact Integrity\n\n"
        f"Integrity status: `{integrity['status']}`.\n\n"
        f"Metric correction: `{integrity['metric_correction']}`.\n\n"
        + _markdown_table(matrix)
        + "\n",
        encoding="utf-8",
    )
    (config.research_dir / "DSS_004G_C_FDR_LIGHT.md").write_text(
        "# DSS-004G-C FDR-Light\n\n"
        f"Decision: `{fdr_summary['decision']}`. Best: `{fdr_summary['best_strategy_id']}`. Base rank: `{fdr_summary['base_rank']}`.\n\n"
        + _markdown_table(fdr)
        + "\n",
        encoding="utf-8",
    )
    (config.research_dir / "DSS_004G_C_WRC_SPA_LIGHT.md").write_text(
        "# DSS-004G-C WRC/SPA-Light\n\n"
        f"Decision: `{wrc_summary['decision']}`.\n\n"
        f"Best strategy: `{wrc_summary['best_strategy_id']}`. Base rank: `{wrc_summary['base_rank']}`. "
        f"Approx p-value: `{wrc_summary['approximate_p_value_base_vs_family']}`.\n\n"
        f"Limitations: {wrc_summary['limitations']}\n",
        encoding="utf-8",
    )
    (config.research_dir / "DSS_004G_C_TIMING_TERMINAL_VERDICT.md").write_text(
        "# DSS-004G-C Timing Terminal Verdict\n\n"
        f"Decision: `{timing['decision']}`.\n\n"
        f"Classification: {timing['classification']}.\n\n"
        f"Placebo dominators: `{timing['placebo_dominators']}`.\n",
        encoding="utf-8",
    )
    (config.research_dir / "DSS_004G_C_FINAL_REPORT.md").write_text(
        "# DSS-004G-C Final Report\n\n"
        f"Decision: `{decision['decision']}`.\n\n"
        f"FDR: `{fdr_summary['decision']}`. WRC/SPA-light: `{wrc_summary['decision']}`. Timing: `{timing['decision']}`.\n\n"
        "Interpretation: DSS-CW-001 remains research-interesting but is not timing-specific enough for shadow, paper, or DSS-005.\n\n"
        "Safety: no orders, no paper orders, no live orders, no paper execution, no operational preview, no operational signals, "
        "no IBKR, no data downloads, no cron, no .env real modified, no merge.\n\n"
        f"Next phase: `{decision['next_phase']}`.\n",
        encoding="utf-8",
    )


def run_dss_004g_c(config: DSS004GCConfig) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    config.research_dir.mkdir(parents=True, exist_ok=True)
    matrix = build_test_matrix(config.output_dir)
    integrity = artifact_integrity(config, matrix)
    if integrity["status"] != "PASS":
        raise ValueError(f"artifact integrity failed: {integrity}")
    family = _build_family(config)
    family = {sid: trades for sid, trades in family.items() if sid in set(matrix[matrix["included_in_stat_family"]]["strategy_id"])}
    fdr, fdr_summary = fdr_light(family, config)
    boot, wrc_summary = wrc_spa_light(family, config)
    timing = timing_verdict(fdr, family)
    decision_value = final_decision(fdr_summary, wrc_summary, timing)
    decision = {
        "schema_version": DSS_004G_C_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "phase": "DSS-004G-C",
        "pattern_id": "DSS-CW-001",
        "decision": decision_value,
        "artifact_integrity_status": integrity["status"],
        "fdr_decision": fdr_summary["decision"],
        "wrc_spa_decision": wrc_summary["decision"],
        "timing_decision": timing["decision"],
        "safety": {
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
        },
        "next_phase": "Reject DSS-CW-001 as current operational candidate; return to Director search-space decision with no DSS-005 or paper preview.",
    }
    matrix.to_csv(config.output_dir / "dss_004g_c_test_matrix.csv", index=False)
    fdr.to_csv(config.output_dir / "dss_004g_c_fdr_results.csv", index=False)
    boot.to_csv(config.output_dir / "dss_004g_c_bootstrap_family.csv", index=False)
    _write_json(config.output_dir / "dss_004g_c_artifact_integrity.json", integrity)
    _write_json(config.output_dir / "dss_004g_c_fdr_summary.json", fdr_summary)
    _write_json(config.output_dir / "dss_004g_c_wrc_spa_light.json", wrc_summary)
    _write_json(config.output_dir / "dss_004g_c_timing_verdict.json", timing)
    _write_json(config.output_dir / "dss_004g_c_decision.json", decision)
    result = {
        "matrix": matrix,
        "integrity": integrity,
        "family": family,
        "fdr": fdr,
        "fdr_summary": fdr_summary,
        "wrc_summary": wrc_summary,
        "timing": timing,
        "decision": decision,
    }
    write_markdown_reports(result, config)
    return result
