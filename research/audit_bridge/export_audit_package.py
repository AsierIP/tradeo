#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


AUDIT_ID = "2026-06-07_ib_paper_patterns"
ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "research" / "audit_bridge"
REQUEST_ROOT = BRIDGE / "requests" / AUDIT_ID
CONFIG_ROOT = REQUEST_ROOT / "config_snapshot"
LOCAL_TZ = ZoneInfo("Europe/Madrid")
EVIDENCE_NEAR_MISS_SHADOW = "near_miss_shadow"
EVIDENCE_SHADOW_NO_ORDER = "shadow_no_order"
EVIDENCE_IBKR_PAPER_ORDER = "ibkr_paper_order"
EVIDENCE_IBKR_PAPER_FILL = "ibkr_paper_fill"
EVIDENCE_QUALITY_STANDARD = "standard"
EVIDENCE_QUALITY_DEGRADED = "degraded"
FILL_PROVENANCE_BROKER_EXECUTION = "broker_execution"
FILL_PROVENANCE_BROKER_STATEMENT_IMPORT = "broker_statement_import"
LAB_SHADOW_EXECUTION_MODE = "lab_shadow_observation"
REAL_FILL_PROVENANCE = {
    FILL_PROVENANCE_BROKER_EXECUTION,
    FILL_PROVENANCE_BROKER_STATEMENT_IMPORT,
}
FILL_ID_KEYS = (
    "fill_id",
    "broker_fill_id",
    "ib_fill_id",
    "execution_id",
    "exec_id",
    "ib_exec_id",
    "broker_execution_id",
    "execution_hash",
    "broker_execution_hash",
    "ib_execution_hash",
    "fill_id_hash",
)
ENTRY_FILL_ID_KEYS = tuple(f"entry_{key}" for key in FILL_ID_KEYS) + FILL_ID_KEYS
EXIT_FILL_ID_KEYS = tuple(f"exit_{key}" for key in FILL_ID_KEYS) + FILL_ID_KEYS
BROKER_TIMESTAMP_KEYS = (
    "broker_execution_time",
    "ib_execution_time",
    "broker_executed_at",
    "execution_time",
    "executed_at",
    "fill_time",
    "broker_fill_time",
    "statement_execution_time",
)
ENTRY_BROKER_TIMESTAMP_KEYS = tuple(f"entry_{key}" for key in BROKER_TIMESTAMP_KEYS) + (
    "entry_fill_time",
) + BROKER_TIMESTAMP_KEYS
EXIT_BROKER_TIMESTAMP_KEYS = tuple(f"exit_{key}" for key in BROKER_TIMESTAMP_KEYS) + (
    "exit_fill_time",
) + BROKER_TIMESTAMP_KEYS
COMMISSION_KEYS = (
    "commission",
    "commission_usd",
    "broker_commission",
    "ib_commission",
    "fees",
    "other_fees",
)
EVIDENCE_NESTED_METADATA_KEYS = (
    "broker_execution",
    "execution",
    "execution_report",
    "execution_observation",
    "broker_statement",
    "statement_row",
)

PATTERN_CATALOG_COLUMNS = [
    "pattern_id",
    "pattern_name",
    "pattern_version",
    "description",
    "hypothesis",
    "detection_rule_plaintext",
    "entry_rule_plaintext",
    "exit_rule_plaintext",
    "stop_rule_plaintext",
    "take_profit_rule_plaintext",
    "time_stop_rule_plaintext",
    "timeframe",
    "asset_class",
    "universe",
    "session_filter",
    "min_volume_filter",
    "min_price_filter",
    "uses_fundamental_data",
    "uses_news_data",
    "uses_options_data",
    "uses_future_data",
    "known_risks",
    "status",
    "created_at",
    "first_seen",
    "last_seen",
]

PATTERN_EVENTS_COLUMNS = [
    "event_id",
    "pattern_id",
    "detected_at",
    "market_timestamp",
    "timezone",
    "ticker",
    "exchange",
    "timeframe",
    "bar_open_time",
    "bar_close_time",
    "signal_price",
    "bid_at_signal",
    "ask_at_signal",
    "spread_at_signal",
    "volume_at_signal",
    "atr_at_signal",
    "volatility_context",
    "market_regime",
    "sector",
    "was_trade_triggered",
    "trade_id",
    "reason_not_traded",
    "duplicate_group_id",
    "is_independent_sample",
    "data_available_at_signal",
    "available_data_cutoff_ts",
    "decision_ts",
    "entry_eligible_ts",
    "label_generated_ts",
    "source_bar_hash",
    "split_id",
    "features_used_json",
    "notes",
]

PAPER_TRADES_COLUMNS = [
    "trade_id",
    "event_id",
    "pattern_id",
    "evidence_type",
    "evidence_quality",
    "ticker",
    "side",
    "quantity",
    "entry_signal_time",
    "entry_order_time",
    "entry_fill_time",
    "entry_signal_price",
    "entry_order_type",
    "entry_limit_price",
    "entry_fill_price",
    "exit_signal_time",
    "exit_order_time",
    "exit_fill_time",
    "exit_order_type",
    "exit_limit_price",
    "exit_fill_price",
    "exit_reason",
    "gross_pnl",
    "commission",
    "estimated_spread_cost",
    "estimated_slippage",
    "other_fees",
    "net_pnl",
    "return_pct",
    "mae",
    "mfe",
    "holding_period_seconds",
    "risk_amount",
    "r_multiple",
    "account_equity_snapshot",
    "position_size_method",
    "notes",
]

IB_FILLS_COLUMNS = [
    "fill_id_hash",
    "trade_id",
    "order_id_hash",
    "ib_execution_time",
    "timezone",
    "ticker",
    "side",
    "quantity",
    "price",
    "commission",
    "liquidity_flag",
    "exchange",
    "order_type",
    "account_id_redacted",
    "raw_status",
    "notes",
]

EXPERIMENT_COLUMNS = [
    "experiment_id",
    "pattern_id",
    "variant_id",
    "created_at",
    "tested_at",
    "status",
    "reason_status",
    "parameters_json",
    "dataset_start",
    "dataset_end",
    "in_sample_start",
    "in_sample_end",
    "out_of_sample_start",
    "out_of_sample_end",
    "paper_live_start",
    "paper_live_end",
    "number_of_assets_tested",
    "number_of_events",
    "number_of_trades",
    "gross_pnl",
    "net_pnl",
    "winrate",
    "profit_factor",
    "sharpe",
    "sortino",
    "max_drawdown",
    "candidate_trial_count",
    "global_trial_count",
    "adjusted_p_value",
    "wrc_p_value",
    "spa_p_value",
    "fit_scope",
    "score_input_scope",
    "event_ledger_hash",
    "nested_discovery_replay_status",
    "nested_discovery_replay_implemented",
    "nested_discovery_replay_passed",
    "edge_claim",
    "drift_status",
    "active_blockers",
    "registry_path",
    "registry_hash",
    "registry_previous_hash",
    "registry_run_manifest_hash",
    "registry_hash_chain_valid",
    "notes",
]

METRICS_BY_PATTERN_COLUMNS = [
    "pattern_id",
    "sample_count",
    "independent_sample_count",
    "trade_count",
    "ticker_count",
    "sector_count",
    "first_seen",
    "last_seen",
    "gross_pnl",
    "net_pnl",
    "avg_trade",
    "median_trade",
    "std_trade",
    "winrate",
    "avg_win",
    "avg_loss",
    "payoff_ratio",
    "profit_factor",
    "expectancy",
    "max_drawdown",
    "max_consecutive_losses",
    "best_trade",
    "worst_trade",
    "top_5_trades_pnl",
    "bottom_5_trades_pnl",
    "pnl_without_best_trade",
    "pnl_without_top_5_trades",
    "pnl_without_worst_trade",
    "sharpe",
    "sortino",
    "calmar",
    "avg_holding_period_seconds",
    "notes",
]

METRICS_BY_TICKER_COLUMNS = [
    "pattern_id",
    "ticker",
    "trade_count",
    "event_count",
    "net_pnl",
    "winrate",
    "profit_factor",
    "avg_trade",
    "max_drawdown",
    "first_seen",
    "last_seen",
    "notes",
]

METRICS_BY_PERIOD_COLUMNS = [
    "period_start",
    "period_end",
    "period_type",
    "pattern_id",
    "event_count",
    "trade_count",
    "gross_pnl",
    "net_pnl",
    "winrate",
    "profit_factor",
    "max_drawdown",
    "market_regime",
    "notes",
]

METRICS_BY_REGIME_COLUMNS = [
    "pattern_id",
    "market_regime",
    "analysis_available",
    "empty_reason",
    "trade_count",
    "event_count",
    "gross_pnl",
    "net_pnl",
    "avg_trade",
    "expectancy_r",
    "winrate",
    "profit_factor",
    "max_drawdown",
    "best_trade",
    "worst_trade",
    "first_seen",
    "last_seen",
    "notes",
]

METRICS_BY_ENTRY_VARIANT_COLUMNS = [
    "pattern_id",
    "entry_variant_id",
    "analysis_available",
    "empty_reason",
    "trade_count",
    "event_count",
    "gross_pnl",
    "net_pnl",
    "avg_trade",
    "expectancy_r",
    "winrate",
    "profit_factor",
    "max_drawdown",
    "best_trade",
    "worst_trade",
    "first_seen",
    "last_seen",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-id", default=AUDIT_ID)
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--pattern-limit", type=int, default=500)
    parser.add_argument("--match-limit", type=int, default=500)
    args = parser.parse_args()

    env = read_env(ROOT / ".env")
    api_url = (args.api_url or env.get("TRADEO_API_URL") or "http://localhost:8000/api").rstrip("/")
    user = env.get("TRADEO_ADMIN_USERNAME", "admin")
    password = env.get("TRADEO_ADMIN_PASSWORD", "change-me")
    package = BRIDGE / "requests" / args.audit_id
    package.mkdir(parents=True, exist_ok=True)
    (package / "config_snapshot").mkdir(parents=True, exist_ok=True)

    patterns = api_get(api_url, f"/research/discovered-patterns?limit={args.pattern_limit}", user, password)
    runs = api_get(api_url, "/research/runs?limit=200", user, password)
    matches = api_get(api_url, f"/research/current-matches?limit={args.match_limit}", user, password)
    laboratory_overview = api_get_optional(api_url, "/laboratory/overview", user, password, default={})

    examples_by_pattern: dict[int, list[dict[str, Any]]] = {}
    for pattern in patterns:
        examples_by_pattern[int(pattern["id"])] = api_get(
            api_url, f"/research/discovered-patterns/{pattern['id']}/examples", user, password
        )

    universe_symbols = read_universe_symbols(ROOT / "data" / "universe_us_mid_small.csv")
    git_commit = run_git("rev-parse", "HEAD")
    git_branch = run_git("branch", "--show-current")
    created_at = datetime.now(LOCAL_TZ).isoformat(timespec="seconds")
    generated_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    context = {
        "audit_id": args.audit_id,
        "created_at": created_at,
        "generated_utc": generated_utc,
        "git_commit": git_commit,
        "git_branch": git_branch,
        "env": env,
        "api_url": api_url,
        "universe_symbols": universe_symbols,
    }

    pattern_catalog_rows = build_pattern_catalog(patterns, examples_by_pattern, context)
    event_rows = build_pattern_events(patterns, examples_by_pattern, matches, context)
    paper_trade_rows = build_paper_trades(patterns, laboratory_overview)
    exported_trade_ids = {
        str(row.get("trade_id") or "")
        for row in paper_trade_rows
        if str(row.get("trade_id") or "").strip()
    }
    fill_rows = build_ib_fills(laboratory_overview, exported_trade_ids=exported_trade_ids)
    experiment_rows = build_experiment_registry(
        patterns,
        examples_by_pattern,
        runs,
        context,
        event_rows_by_pattern=group_event_rows_by_pattern(event_rows),
    )
    metrics_pattern_rows = build_metrics_by_pattern(
        patterns,
        examples_by_pattern,
        paper_trade_rows,
        event_rows=event_rows,
    )
    metrics_ticker_rows = build_metrics_by_ticker(examples_by_pattern)
    metrics_period_rows = build_metrics_by_period(examples_by_pattern)
    metrics_regime_rows = build_metrics_by_regime(patterns, event_rows, paper_trade_rows)
    metrics_entry_variant_rows = build_metrics_by_entry_variant(patterns, paper_trade_rows)

    write_csv(package / "pattern_catalog.csv", PATTERN_CATALOG_COLUMNS, pattern_catalog_rows)
    write_csv(package / "pattern_events.csv", PATTERN_EVENTS_COLUMNS, event_rows)
    write_csv(package / "paper_trades.csv", PAPER_TRADES_COLUMNS, paper_trade_rows)
    write_csv(package / "ib_fills.csv", IB_FILLS_COLUMNS, fill_rows)
    write_csv(package / "experiment_registry.csv", EXPERIMENT_COLUMNS, experiment_rows)
    write_csv(package / "metrics_by_pattern.csv", METRICS_BY_PATTERN_COLUMNS, metrics_pattern_rows)
    write_csv(package / "metrics_by_ticker.csv", METRICS_BY_TICKER_COLUMNS, metrics_ticker_rows)
    write_csv(package / "metrics_by_period.csv", METRICS_BY_PERIOD_COLUMNS, metrics_period_rows)
    write_csv(package / "metrics_by_regime.csv", METRICS_BY_REGIME_COLUMNS, metrics_regime_rows)
    write_csv(package / "metrics_by_entry_variant.csv", METRICS_BY_ENTRY_VARIANT_COLUMNS, metrics_entry_variant_rows)

    write_audit_request(package, context, patterns, pattern_catalog_rows, metrics_pattern_rows, experiment_rows, event_rows)
    write_audit_summary_for_chatgpt(
        package,
        pattern_catalog_rows,
        event_rows,
        experiment_rows,
        metrics_pattern_rows,
        metrics_ticker_rows,
        metrics_period_rows,
        metrics_regime_rows,
        metrics_entry_variant_rows,
        paper_trade_rows,
        fill_rows,
    )
    write_manifest(
        package,
        context,
        patterns,
        event_rows,
        experiment_rows,
        paper_trade_rows,
        fill_rows,
        metrics_regime_rows,
        metrics_entry_variant_rows,
    )
    write_code_references(package, patterns)
    write_config_snapshot(package / "config_snapshot", context)
    write_supporting_docs(package, context, patterns, event_rows, experiment_rows, paper_trade_rows, fill_rows)
    write_hashes(package)

    print(json.dumps({
        "audit_id": args.audit_id,
        "patterns_exported": len(patterns),
        "events_exported": len(event_rows),
        "paper_trades_exported": len(paper_trade_rows),
        "fills_exported": len(fill_rows),
        "experiments_exported": len(experiment_rows),
        "metrics_by_regime_rows": len(metrics_regime_rows),
        "metrics_by_entry_variant_rows": len(metrics_entry_variant_rows),
        "package": str(package.relative_to(ROOT)),
    }, indent=2))
    return 0


def read_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        env[key.strip()] = value
    return env


def api_get(api_url: str, path: str, user: str, password: str) -> Any:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    request = Request(f"{api_url}{path}", headers={"Authorization": f"Basic {token}"})
    with urlopen(request, timeout=120) as response:  # noqa: S310 - local admin API export
        return json.loads(response.read().decode("utf-8"))


def api_get_optional(api_url: str, path: str, user: str, password: str, *, default: Any) -> Any:
    try:
        return api_get(api_url, path, user, password)
    except Exception:  # noqa: BLE001
        return default


def run_git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def read_universe_symbols(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [row["symbol"].strip().upper() for row in csv.DictReader(handle) if row.get("symbol")]


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: csv_value(row.get(column, "")) for column in columns})


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def pattern_id(pattern: dict[str, Any]) -> str:
    return f"PATTERN_{int(pattern['id']):06d}"


def normalize_ts(value: Any) -> str:
    if value is None or value == "":
        return ""
    text = str(value).strip()
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    if re.search(r"(Z|[+-]\d\d:\d\d)$", text):
        return text.replace("Z", "+00:00")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return f"{text}T00:00:00+00:00"
    if "T" in text:
        return f"{text}+00:00"
    return f"{text}T00:00:00+00:00"


def next_eligible_ts(value: Any, timeframe: Any) -> str:
    normalized = normalize_ts(value)
    if not normalized:
        return ""
    try:
        base = datetime.fromisoformat(normalized)
    except ValueError:
        return normalized
    tf = str(timeframe or "1d").lower().strip()
    if tf in {"1d", "1 day"}:
        delta_seconds = 24 * 60 * 60
    elif tf in {"1wk", "1 week"}:
        delta_seconds = 7 * 24 * 60 * 60
    elif tf.endswith("m") and tf[:-1].isdigit():
        delta_seconds = int(tf[:-1]) * 60
    elif tf.endswith("h") and tf[:-1].isdigit():
        delta_seconds = int(tf[:-1]) * 60 * 60
    else:
        delta_seconds = 24 * 60 * 60
    return datetime.fromtimestamp(base.timestamp() + delta_seconds, tz=timezone.utc).isoformat()


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def regime_label_from_features(features: Any) -> str:
    if not isinstance(features, dict):
        return "not_persisted"
    score = safe_float(features.get("market_regime_score"), 0.0)
    if score > 0.25:
        return "market_up"
    if score < -0.25:
        return "market_down"
    return "market_mixed"


def sector_label_from_features(features: Any) -> str:
    if not isinstance(features, dict):
        return "not_persisted"
    strength = safe_float(features.get("sector_strength"), 0.0)
    if strength > 0.03:
        return "sector_strong"
    if strength < -0.03:
        return "sector_weak"
    return "sector_neutral"


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def trade_is_closed(trade: dict[str, Any], metadata: dict[str, Any]) -> bool:
    status = str(trade.get("status") or metadata.get("status") or "").strip().lower()
    if status in {"closed", "filled", "done", "executed"}:
        return True
    return bool(trade.get("closed_at") or metadata.get("exit_fill_time"))


def trade_evidence_type(trade: dict[str, Any], metadata: dict[str, Any]) -> str:
    explicit = trade.get("evidence_type") or metadata.get("evidence_type")
    if explicit:
        explicit_type = str(explicit)
        if (
            explicit_type == EVIDENCE_IBKR_PAPER_ORDER
            and trade_is_closed(trade, metadata)
            and fill_provenance(metadata) in REAL_FILL_PROVENANCE
        ):
            return EVIDENCE_IBKR_PAPER_FILL
        return explicit_type
    execution_mode = str(metadata.get("execution_mode") or trade.get("execution_mode") or "").strip().lower()
    if execution_mode == LAB_SHADOW_EXECUTION_MODE or truthy(metadata.get("observation_only")) or truthy(metadata.get("no_ibkr_order")):
        return EVIDENCE_NEAR_MISS_SHADOW if truthy(metadata.get("near_miss")) else EVIDENCE_SHADOW_NO_ORDER
    if execution_mode in {"ibkr", "ibkr_paper", "paper"}:
        return (
            EVIDENCE_IBKR_PAPER_FILL
            if trade_is_closed(trade, metadata) and fill_provenance(metadata) in REAL_FILL_PROVENANCE
            else EVIDENCE_IBKR_PAPER_ORDER
        )
    if trade.get("broker_order_id") or metadata.get("broker_order_id") or metadata.get("parent_order_id"):
        return (
            EVIDENCE_IBKR_PAPER_FILL
            if trade_is_closed(trade, metadata) and fill_provenance(metadata) in REAL_FILL_PROVENANCE
            else EVIDENCE_IBKR_PAPER_ORDER
        )
    return ""


def trade_evidence_quality(metadata: dict[str, Any]) -> str:
    explicit = metadata.get("evidence_quality")
    if explicit:
        return str(explicit)
    if truthy(metadata.get("fallback_used")) or metadata.get("fallback_source"):
        return EVIDENCE_QUALITY_DEGRADED
    return EVIDENCE_QUALITY_STANDARD


def is_exportable_paper_fill_trade(trade: dict[str, Any], metadata: dict[str, Any]) -> bool:
    evidence_type = trade_evidence_type(trade, metadata)
    evidence_quality = trade_evidence_quality(metadata)
    if evidence_type != EVIDENCE_IBKR_PAPER_FILL:
        return False
    if evidence_quality not in {EVIDENCE_QUALITY_STANDARD, "normal"}:
        return False
    if not trade_is_closed(trade, metadata):
        return False
    if (
        truthy(metadata.get("observation_only"))
        or truthy(metadata.get("no_ibkr_order"))
        or truthy(metadata.get("near_miss"))
    ):
        return False
    return (
        fill_provenance(metadata) in REAL_FILL_PROVENANCE
        and has_any_metadata_value(metadata, FILL_ID_KEYS)
        and has_any_metadata_value(metadata, BROKER_TIMESTAMP_KEYS)
        and has_any_metadata_value(metadata, COMMISSION_KEYS)
    )


def fill_provenance(metadata: dict[str, Any]) -> str:
    return str(metadata.get("fill_provenance") or "").strip()


def has_any_metadata_value(metadata: dict[str, Any], keys: tuple[str, ...]) -> bool:
    for source in metadata_sources(metadata):
        for key in keys:
            value = source.get(key)
            if value is not None and str(value).strip() != "":
                return True
    return False


def first_metadata_value(metadata: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for source in metadata_sources(metadata):
        for key in keys:
            value = source.get(key)
            if value is not None and str(value).strip() != "":
                return value
    return ""


def metadata_sources(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = [metadata]
    for key in EVIDENCE_NESTED_METADATA_KEYS:
        value = metadata.get(key)
        if isinstance(value, dict):
            sources.append(value)
    return sources


def min_max_times(examples: list[dict[str, Any]]) -> tuple[str, str]:
    values = sorted(normalize_ts(e.get("window_end")) for e in examples if e.get("window_end"))
    if not values:
        return "", ""
    return values[0], values[-1]


def best_rr_metrics(pattern: dict[str, Any]) -> dict[str, Any]:
    rr = pattern.get("best_rr") or pattern.get("best_tested_rr") or 0
    metrics = pattern.get("rr_metrics_json") or {}
    key = f"{float(rr):g}" if rr else ""
    if key in metrics:
        return metrics[key]
    return {}


def pattern_research_metrics(pattern: dict[str, Any]) -> dict[str, Any]:
    metrics = pattern.get("metrics_json")
    return metrics if isinstance(metrics, dict) else {}


def metric_value(pattern: dict[str, Any], metrics: dict[str, Any], key: str, default: Any = "") -> Any:
    if key in metrics:
        return metrics.get(key)
    return pattern.get(key, default)


def status_for_experiment(pattern: dict[str, Any]) -> str:
    if pattern.get("validation_passed"):
        return "active" if pattern.get("status") in {"lab", "lab_watchlist", "lab_candidate", "director_review"} else "detected"
    if pattern.get("status") == "rejected":
        return "discarded"
    return "pending_review"


def reason_for(pattern: dict[str, Any]) -> str:
    reasons = pattern.get("validation_reasons_json") or pattern.get("rejection_reasons_json") or []
    if reasons:
        return "; ".join(str(r) for r in reasons)
    return str(pattern.get("promotion_reason") or "")


def build_pattern_catalog(
    patterns: list[dict[str, Any]],
    examples_by_pattern: dict[int, list[dict[str, Any]]],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    env = context["env"]
    universe_count = len(context["universe_symbols"])
    rows = []
    for pattern in patterns:
        examples = examples_by_pattern.get(int(pattern["id"]), [])
        first_seen, last_seen = min_max_times(examples)
        rr = pattern.get("best_rr") or pattern.get("best_tested_rr") or env.get("TRADEO_DISCOVERY_MIN_REWARD_RISK", "2.5")
        rows.append({
            "pattern_id": pattern_id(pattern),
            "pattern_name": pattern.get("name", ""),
            "pattern_version": f"run_{pattern.get('run_id') or 'unknown'}",
            "description": (
                f"Clustered normalized OHLCV window pattern. side={pattern.get('side')}, "
                f"window_size={pattern.get('window_size')}, cluster_id={pattern.get('cluster_id')}."
            ),
            "hypothesis": (
                "Charts close to this cluster centroid may have asymmetric forward R distribution "
                f"for {pattern.get('side')} setups at the tested reward/risk levels."
            ),
            "detection_rule_plaintext": (
                "Normalize OHLCV, compute local deterministic embedding for the configured daily window, "
                "standardize features, cluster historical windows with MiniBatchKMeans, and identify windows "
                f"assigned to cluster {pattern.get('cluster_id')} for window_size={pattern.get('window_size')}. "
                "Current matches compare scaled embedding distance to the stored centroid."
            ),
            "entry_rule_plaintext": (
                "Research entry is the close of the final bar in the detected window. Current lab matches use "
                "latest close as signal/entry reference; no order is submitted by the research lab."
            ),
            "exit_rule_plaintext": (
                "Historical simulation exits at the first stop/target touch in the forward path, or at the final "
                "forward close if neither is touched. If stop and target are both touched intrabar, stop is assumed first."
            ),
            "stop_rule_plaintext": "1R stop based on max(1.5*ATR14, 1.5% of entry, 0.01).",
            "take_profit_rule_plaintext": f"Targets tested at R levels from config; best_rr currently {rr}.",
            "time_stop_rule_plaintext": "Forward bars tested from discovery config; final forward close is used as time-stop fallback.",
            "timeframe": pattern.get("timeframe", "1d"),
            "asset_class": "US equities",
            "universe": f"data/universe_us_mid_small.csv ({universe_count} configured symbols)",
            "session_filter": "Regular daily bars from IBKR historical data; intraday session filter not persisted.",
            "min_volume_filter": env.get("TRADEO_MIN_AVG_DOLLAR_VOLUME", "5000000"),
            "min_price_filter": env.get("TRADEO_MIN_PRICE", "2.0"),
            "uses_fundamental_data": "false",
            "uses_news_data": "false",
            "uses_options_data": "false",
            "uses_future_data": "false",
            "known_risks": "; ".join([
                reason_for(pattern),
                "stored examples are representative, not a full raw event ledger",
                "daily timestamps normalized to UTC when original bars lacked explicit timezone",
            ]).strip("; "),
            "status": pattern.get("status", ""),
            "created_at": normalize_ts(pattern.get("created_at")),
            "first_seen": first_seen,
            "last_seen": last_seen,
        })
    return rows


def build_pattern_events(
    patterns: list[dict[str, Any]],
    examples_by_pattern: dict[int, list[dict[str, Any]]],
    matches: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern_by_id = {int(p["id"]): p for p in patterns}
    for pid, examples in examples_by_pattern.items():
        pattern = pattern_by_id.get(pid)
        if not pattern:
            continue
        for example in examples:
            event_id = f"EVT_{pattern_id(pattern)}_EX_{int(example['id']):06d}"
            window_end = normalize_ts(example.get("window_end"))
            features = example.get("features_json") or {}
            rows.append({
                "event_id": event_id,
                "pattern_id": pattern_id(pattern),
                "detected_at": normalize_ts(example.get("created_at")),
                "market_timestamp": window_end,
                "timezone": "UTC",
                "ticker": example.get("symbol", ""),
                "exchange": "SMART/IBKR",
                "timeframe": example.get("timeframe", pattern.get("timeframe", "1d")),
                "bar_open_time": normalize_ts(example.get("window_start")),
                "bar_close_time": window_end,
                "signal_price": example.get("entry_price", ""),
                "bid_at_signal": "",
                "ask_at_signal": "",
                "spread_at_signal": "",
                "volume_at_signal": "",
                "atr_at_signal": example.get("risk_proxy", ""),
                "volatility_context": f"risk_proxy={example.get('risk_proxy', '')}; mfe_r={example.get('mfe_r', '')}; mae_r={example.get('mae_r', '')}",
                "market_regime": regime_label_from_features(features),
                "sector": sector_label_from_features(features),
                "was_trade_triggered": "false",
                "trade_id": "",
                "reason_not_traded": "Historical representative research sample; not routed to paper execution.",
                "duplicate_group_id": f"DUP_{pattern_id(pattern)}_{example.get('symbol', '')}_{window_end}",
                "is_independent_sample": "true",
                "data_available_at_signal": "true",
                "available_data_cutoff_ts": window_end,
                "decision_ts": window_end,
                "entry_eligible_ts": next_eligible_ts(window_end, example.get("timeframe", pattern.get("timeframe", "1d"))),
                "label_generated_ts": normalize_ts(example.get("forward_end")),
                "source_bar_hash": stable_hash({"example": example.get("id"), "window_end": window_end, "features": features}),
                "split_id": "research_example",
                "features_used_json": features,
                "notes": f"stored_example_kind={example.get('kind', '')}; outcome_r={example.get('outcome_r', '')}; similarity={example.get('similarity', '')}",
            })
    seen_match_events: set[tuple[str, str, str, str, str]] = set()
    for match in matches:
        pattern = pattern_by_id.get(int(match["pattern_id"]))
        if not pattern:
            continue
        matched_at = normalize_ts(match.get("matched_at"))
        window_end = normalize_ts(match.get("window_end"))
        event_id = f"EVT_{pattern_id(pattern)}_MATCH_{int(match['id']):06d}"
        metrics = match.get("metrics_json") or {}
        features = metrics.get("features") or {}
        audit = metrics.get("entry_audit") or {}
        regime = metrics.get("regime") or {}
        source_bar_hash = audit.get("source_bar_hash") or stable_hash(
            {
                "pattern_id": pattern_id(pattern),
                "symbol": match.get("symbol"),
                "timeframe": match.get("timeframe", pattern.get("timeframe", "1d")),
                "window_end": window_end,
                "features": features,
            }
        )
        event_fingerprint = (
            pattern_id(pattern),
            str(match.get("symbol", "")).upper(),
            str(match.get("timeframe", pattern.get("timeframe", "1d"))),
            window_end,
            str(source_bar_hash),
        )
        if event_fingerprint in seen_match_events:
            continue
        seen_match_events.add(event_fingerprint)
        rows.append({
            "event_id": event_id,
            "pattern_id": pattern_id(pattern),
            "detected_at": matched_at,
            "market_timestamp": window_end,
            "timezone": "UTC",
            "ticker": match.get("symbol", ""),
            "exchange": "SMART/IBKR",
            "timeframe": match.get("timeframe", pattern.get("timeframe", "1d")),
            "bar_open_time": "",
            "bar_close_time": window_end,
            "signal_price": match.get("entry_price", ""),
            "bid_at_signal": "",
            "ask_at_signal": "",
            "spread_at_signal": "",
            "volume_at_signal": "",
            "atr_at_signal": "",
            "volatility_context": json.dumps(features, ensure_ascii=False, sort_keys=True),
            "market_regime": regime.get("regime_key") or regime_label_from_features(features),
            "sector": regime.get("sector_regime") or sector_label_from_features(features),
            "was_trade_triggered": "false",
            "trade_id": "",
            "reason_not_traded": "Current lab watchlist match; execution disabled/read-only and requires paper validation.",
            "duplicate_group_id": f"DUP_{pattern_id(pattern)}_{match.get('symbol', '')}_{window_end}",
            "is_independent_sample": "true",
            "data_available_at_signal": "true",
            "available_data_cutoff_ts": audit.get("available_data_cutoff_ts") or window_end,
            "decision_ts": audit.get("decision_ts") or matched_at,
            "entry_eligible_ts": audit.get("entry_eligible_ts")
            or next_eligible_ts(window_end, match.get("timeframe", pattern.get("timeframe", "1d"))),
            "label_generated_ts": audit.get("label_generated_ts") or "",
            "source_bar_hash": source_bar_hash,
            "split_id": audit.get("split_id") or "live_forward_scan_unlabeled",
            "features_used_json": features,
            "notes": (
                f"similarity={match.get('similarity')}; score={match.get('score')}; "
                f"status={match.get('status')}; outcome_pending=true"
            ),
        })
    return rows


def group_event_rows_by_pattern(event_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in event_rows:
        pid = str(row.get("pattern_id") or "").strip()
        if pid:
            grouped[pid].append(row)
    return grouped


def build_paper_trades(patterns: list[dict[str, Any]], laboratory_overview: dict[str, Any]) -> list[dict[str, Any]]:
    signals = {
        int(signal["id"]): signal
        for signal in laboratory_overview.get("signals", [])
        if isinstance(signal, dict) and str(signal.get("id", "")).isdigit()
    }
    pattern_by_name = {str(pattern.get("name")): pattern for pattern in patterns}
    rows: list[dict[str, Any]] = []
    for trade in laboratory_overview.get("trades", []):
        if not isinstance(trade, dict):
            continue
        signal = signals.get(int(trade.get("signal_id") or 0), {})
        metadata = trade.get("metadata_json") or {}
        signal_metadata = signal.get("metadata_json") or {}
        evidence_type = trade_evidence_type(trade, metadata)
        evidence_quality = trade_evidence_quality(metadata)
        if not is_exportable_paper_fill_trade(trade, metadata):
            continue
        pattern_ref = audit_pattern_id(signal_metadata, trade, pattern_by_name)
        if not pattern_ref:
            continue
        event_id = linked_event_id(pattern_ref, signal, trade)
        entry = safe_float(trade.get("entry"), safe_float(signal.get("entry"), 0.0))
        qty = safe_float(trade.get("qty"), 0.0)
        gross_pnl = safe_float(trade.get("pnl_usd"), 0.0)
        commission = safe_float(first_metadata_value(metadata, COMMISSION_KEYS), 0.0)
        estimated_spread = safe_float(metadata.get("estimated_spread_cost"), 0.0)
        estimated_slippage = safe_float(metadata.get("estimated_slippage"), 0.0)
        other_fees = safe_float(metadata.get("other_fees"), 0.0)
        net_pnl = gross_pnl - commission - estimated_spread - estimated_slippage - other_fees
        entry_fill_time = first_metadata_value(metadata, ENTRY_BROKER_TIMESTAMP_KEYS)
        exit_fill_time = first_metadata_value(metadata, EXIT_BROKER_TIMESTAMP_KEYS)
        rows.append(
            {
                "trade_id": trade.get("id"),
                "event_id": event_id,
                "pattern_id": pattern_ref,
                "evidence_type": evidence_type,
                "evidence_quality": evidence_quality,
                "ticker": trade.get("symbol", ""),
                "side": trade.get("side", ""),
                "quantity": trade.get("qty", ""),
                "entry_signal_time": signal.get("created_at", ""),
                "entry_order_time": metadata.get("submitted_at") or trade.get("opened_at", ""),
                "entry_fill_time": entry_fill_time,
                "entry_signal_price": signal.get("entry", entry),
                "entry_order_type": ((signal_metadata.get("entry_variant") or {}).get("order_style")) or "limit",
                "entry_limit_price": signal.get("entry", entry),
                "entry_fill_price": metadata.get("entry_fill_price") or entry,
                "exit_signal_time": trade.get("closed_at", ""),
                "exit_order_time": metadata.get("exit_order_time") or trade.get("closed_at", ""),
                "exit_fill_time": exit_fill_time,
                "exit_order_type": metadata.get("exit_order_type") or "bracket_exit",
                "exit_limit_price": trade.get("target", ""),
                "exit_fill_price": trade.get("exit_price", ""),
                "exit_reason": metadata.get("exit_reason") or trade.get("status", ""),
                "gross_pnl": round(gross_pnl, 4),
                "commission": round(commission, 4),
                "estimated_spread_cost": round(estimated_spread, 4),
                "estimated_slippage": round(estimated_slippage, 4),
                "other_fees": round(other_fees, 4),
                "net_pnl": round(net_pnl, 4),
                "return_pct": round(net_pnl / max(abs(entry * qty), 1e-9), 6) if qty else "",
                "mae": metadata.get("mae"),
                "mfe": metadata.get("mfe"),
                "holding_period_seconds": metadata.get("holding_period_seconds"),
                "risk_amount": signal.get("risk_usd", ""),
                "r_multiple": trade.get("r_multiple", ""),
                "account_equity_snapshot": metadata.get("account_equity_snapshot", ""),
                "position_size_method": "risk_manager_suggested_qty",
                "notes": "; ".join(
                    part
                    for part in (
                        f"entry_variant={signal_metadata.get('entry_variant_id', '')}",
                        f"regime={((signal_metadata.get('regime') or {}).get('regime_key') or '')}",
                        f"execution_mode={metadata.get('execution_mode', '')}",
                    )
                    if part
                ),
            }
        )
    return rows


def build_ib_fills(laboratory_overview: dict[str, Any], *, exported_trade_ids: set[str] | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    allowed_trade_ids = exported_trade_ids if exported_trade_ids is not None else None
    for trade in laboratory_overview.get("trades", []):
        if not isinstance(trade, dict):
            continue
        metadata = trade.get("metadata_json") or {}
        if not is_exportable_paper_fill_trade(trade, metadata):
            continue
        trade_id = str(trade.get("id") or "")
        if allowed_trade_ids is not None and trade_id not in allowed_trade_ids:
            continue
        entry_price = safe_float(metadata.get("entry_fill_price"), safe_float(trade.get("entry"), 0.0))
        opened_at = normalize_ts(first_metadata_value(metadata, ENTRY_BROKER_TIMESTAMP_KEYS))
        if entry_price > 0 and opened_at:
            rows.append(fill_row(trade, metadata, trade_id=trade_id, suffix="ENTRY", timestamp=opened_at, price=entry_price))
        exit_price = safe_float(metadata.get("exit_fill_price"), safe_float(trade.get("exit_price"), 0.0))
        closed_at = normalize_ts(first_metadata_value(metadata, EXIT_BROKER_TIMESTAMP_KEYS))
        if exit_price > 0 and closed_at:
            rows.append(fill_row(trade, metadata, trade_id=trade_id, suffix="EXIT", timestamp=closed_at, price=exit_price))
    return rows


def fill_row(
    trade: dict[str, Any],
    metadata: dict[str, Any],
    *,
    trade_id: str,
    suffix: str,
    timestamp: str,
    price: float,
) -> dict[str, Any]:
    order_ids = metadata.get("order_ids") if isinstance(metadata.get("order_ids"), list) else []
    raw_order_id = order_ids[0] if order_ids else metadata.get("parent_order_id", "")
    fill_keys = ENTRY_FILL_ID_KEYS if suffix == "ENTRY" else EXIT_FILL_ID_KEYS
    fill_id = first_metadata_value(metadata, fill_keys)
    return {
        "fill_id_hash": stable_hash({"fill_id": fill_id, "trade_id": trade_id, "suffix": suffix})[:24],
        "trade_id": trade_id,
        "order_id_hash": stable_hash({"order_id": raw_order_id})[:24] if raw_order_id else "",
        "ib_execution_time": timestamp,
        "timezone": "UTC",
        "ticker": trade.get("symbol", ""),
        "side": trade.get("side", ""),
        "quantity": trade.get("qty", ""),
        "price": round(price, 4),
        "commission": first_metadata_value(metadata, COMMISSION_KEYS),
        "liquidity_flag": metadata.get("liquidity_flag", ""),
        "exchange": "SMART/IBKR",
        "order_type": metadata.get("entry_order_type") or "bracket",
        "account_id_redacted": "true",
        "raw_status": trade.get("status", ""),
        "notes": f"{suffix.lower()} fill source={fill_provenance(metadata)}",
    }


def audit_pattern_id(
    signal_metadata: dict[str, Any],
    trade: dict[str, Any],
    pattern_by_name: dict[str, dict[str, Any]],
) -> str:
    raw_id = signal_metadata.get("pattern_id")
    try:
        if raw_id:
            return f"PATTERN_{int(raw_id):06d}"
    except (TypeError, ValueError):
        pass
    pattern = pattern_by_name.get(str(trade.get("pattern") or ""))
    return pattern_id(pattern) if pattern else ""


def linked_event_id(pattern_ref: str, signal: dict[str, Any], trade: dict[str, Any]) -> str:
    signal_id = signal.get("id") or trade.get("signal_id") or "0"
    return f"EVT_{pattern_ref}_TRADE_SIGNAL_{int(signal_id):06d}" if str(signal_id).isdigit() else f"EVT_{pattern_ref}_TRADE"


def build_experiment_registry(
    patterns: list[dict[str, Any]],
    examples_by_pattern: dict[int, list[dict[str, Any]]],
    runs: list[dict[str, Any]],
    context: dict[str, Any],
    *,
    event_rows_by_pattern: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    run_by_id = {r.get("id"): r for r in runs}
    rows: list[dict[str, Any]] = []
    export_global_trial_count = 0
    for pattern in patterns:
        examples = examples_by_pattern.get(int(pattern["id"]), [])
        first_seen, last_seen = min_max_times(examples)
        run = run_by_id.get(pattern.get("run_id")) or {}
        params = run.get("params_json") or {}
        research_metrics = pattern_research_metrics(pattern)
        rr_metrics = pattern.get("rr_metrics_json") or {}
        if not rr_metrics:
            rr_metrics = {"best": best_rr_metrics(pattern)}
        nested_replay = nested_discovery_replay_metadata(research_metrics)
        registry = registry_metadata(research_metrics)
        edge_claim = edge_claim_metadata(research_metrics)
        stored_event_ledger_hash = event_ledger_hash_metadata(research_metrics)
        event_ledger_hash = stored_event_ledger_hash
        audit_pattern_id = pattern_id(pattern)
        pattern_event_rows = (event_rows_by_pattern or {}).get(audit_pattern_id, [])
        if not event_ledger_hash:
            event_ledger_hash = exported_event_ledger_hash(audit_pattern_id, pattern_event_rows)
        used_export_event_hash = not stored_event_ledger_hash and bool(event_ledger_hash)
        split_bounds = experiment_split_bounds(examples, research_metrics)
        active_blockers = active_blockers_metadata(research_metrics)
        for rr_key, metrics in sorted(rr_metrics.items(), key=lambda item: str(item[0])):
            variant_id = f"RR_{str(rr_key).replace('.', '_')}"
            candidate_trial_count = experiment_trial_count(pattern, research_metrics)
            global_trial_count = metric_value(pattern, research_metrics, "global_trial_count", "")
            if global_trial_count in ("", None):
                export_global_trial_count += max(1, int(candidate_trial_count or 1))
                global_trial_count = export_global_trial_count
            else:
                parsed_global_trial_count = first_positive_int(global_trial_count)
                if parsed_global_trial_count is not None:
                    export_global_trial_count = max(export_global_trial_count, parsed_global_trial_count)
            parameters_json = {
                "rr": metrics.get("rr", rr_key) if isinstance(metrics, dict) else rr_key,
                "window_size": pattern.get("window_size"),
                "cluster_id": pattern.get("cluster_id"),
                "side": pattern.get("side"),
                "run_params": params,
            }
            stored_run_manifest_hash = registry.get("run_manifest_hash") or registry.get("latest_run_manifest_hash")
            run_manifest_hash = (
                stored_run_manifest_hash
                or audit_run_manifest_hash(pattern, run, context)
            )
            stored_registry_hash = registry.get("registry_hash") or registry.get("hash") or registry.get("sha256")
            registry_hash = (
                stored_registry_hash
                or audit_registry_row_hash(
                    pattern=pattern,
                    variant_id=variant_id,
                    parameters_json=parameters_json,
                    run_manifest_hash=run_manifest_hash,
                )
            )
            used_audit_registry_hash = not (stored_registry_hash and stored_run_manifest_hash)
            registry_path = registry.get("path") or "audit_package:experiment_registry.csv"
            registry_hash_chain_valid = registry.get("hash_chain_valid", "")
            if registry_hash_chain_valid == "":
                registry_hash_chain_valid = bool(registry_hash and run_manifest_hash)
            rows.append({
                "experiment_id": f"EXP_{pattern_id(pattern)}_{variant_id}",
                "pattern_id": audit_pattern_id,
                "variant_id": variant_id,
                "created_at": normalize_ts(pattern.get("created_at")),
                "tested_at": normalize_ts(pattern.get("updated_at") or pattern.get("created_at")),
                "status": status_for_experiment(pattern),
                "reason_status": reason_for(pattern),
                "parameters_json": parameters_json,
                "dataset_start": first_seen,
                "dataset_end": last_seen,
                "in_sample_start": split_bounds.get("in_sample_start") or first_seen,
                "in_sample_end": split_bounds.get("in_sample_end", ""),
                "out_of_sample_start": split_bounds.get("out_of_sample_start", ""),
                "out_of_sample_end": split_bounds.get("out_of_sample_end") or last_seen,
                "paper_live_start": "",
                "paper_live_end": "",
                "number_of_assets_tested": pattern.get("symbol_count", ""),
                "number_of_events": pattern.get("sample_count", ""),
                "number_of_trades": "0",
                "gross_pnl": "",
                "net_pnl": "",
                "winrate": metrics.get("win_rate", pattern.get("best_win_rate", "")) if isinstance(metrics, dict) else "",
                "profit_factor": metrics.get("profit_factor", pattern.get("best_profit_factor", "")) if isinstance(metrics, dict) else "",
                "sharpe": "",
                "sortino": "",
                "max_drawdown": metrics.get("max_drawdown_r", pattern.get("best_max_drawdown_r", "")) if isinstance(metrics, dict) else "",
                "candidate_trial_count": candidate_trial_count,
                "global_trial_count": global_trial_count,
                "adjusted_p_value": metric_value(pattern, research_metrics, "adjusted_p_value"),
                "wrc_p_value": metric_value(pattern, research_metrics, "wrc_p_value"),
                "spa_p_value": metric_value(pattern, research_metrics, "spa_p_value"),
                "fit_scope": metric_value(pattern, research_metrics, "fit_scope", {}),
                "score_input_scope": metric_value(pattern, research_metrics, "score_input_scope", {}),
                "event_ledger_hash": event_ledger_hash,
                "nested_discovery_replay_status": nested_replay.get("status", ""),
                "nested_discovery_replay_implemented": nested_replay.get("implemented", ""),
                "nested_discovery_replay_passed": nested_replay.get("passed", ""),
                "edge_claim": edge_claim,
                "drift_status": metric_value(pattern, research_metrics, "drift_status", pattern.get("drift_status", "")),
                "active_blockers": "; ".join(active_blockers),
                "registry_path": registry_path,
                "registry_hash": registry_hash,
                "registry_previous_hash": registry.get("previous_registry_hash", ""),
                "registry_run_manifest_hash": run_manifest_hash,
                "registry_hash_chain_valid": registry_hash_chain_valid,
                "notes": experiment_notes(
                    used_export_event_hash=used_export_event_hash,
                    used_audit_registry_hash=used_audit_registry_hash,
                    split_source=split_bounds.get("source", ""),
                ),
            })
    return rows


def nested_discovery_replay_metadata(metrics: dict[str, Any]) -> dict[str, Any]:
    nested = metrics.get("nested_discovery_replay")
    if not isinstance(nested, dict):
        hypothesis = metrics.get("research_hypothesis")
        if isinstance(hypothesis, dict):
            nested = hypothesis.get("nested_discovery_replay")
    if not isinstance(nested, dict):
        hypothesis = metrics.get("research_hypothesis_package")
        if isinstance(hypothesis, dict):
            nested = hypothesis.get("nested_discovery_replay")
    if not isinstance(nested, dict):
        return {"status": "not_recorded_legacy", "implemented": False, "passed": False}
    status = str(nested.get("status") or "").strip().lower()
    passed = truthy(nested.get("passed")) or status in {"passed", "pass", "ok", "complete", "completed"}
    return {
        "status": status,
        "implemented": truthy(nested.get("implemented")),
        "passed": passed,
    }


def registry_metadata(metrics: dict[str, Any]) -> dict[str, Any]:
    registry = metrics.get("global_experiment_registry")
    return registry if isinstance(registry, dict) else {}


def edge_claim_metadata(metrics: dict[str, Any]) -> str:
    for key in ("edge_claim",):
        value = str(metrics.get(key) or "").strip()
        if value:
            return value
    for key in ("research_hypothesis", "research_hypothesis_package", "global_experiment_registry"):
        payload = metrics.get(key)
        if isinstance(payload, dict):
            value = str(payload.get("edge_claim") or "").strip()
            if value:
                return value
    return "NO_DEMOSTRADO"


def event_ledger_hash_metadata(metrics: dict[str, Any]) -> str:
    for key in ("event_ledger_hash", "event_ledger_sha256"):
        value = str(metrics.get(key) or "").strip()
        if value:
            return value
    for key in ("research_hypothesis", "research_hypothesis_package"):
        payload = metrics.get(key)
        if isinstance(payload, dict):
            value = str(payload.get("event_ledger_hash") or "").strip()
            if value:
                return value
    return ""


def exported_event_ledger_hash(pattern_id_value: str, event_rows: list[dict[str, Any]]) -> str:
    if not event_rows:
        return ""
    canonical_rows = [
        {
            "event_id": row.get("event_id", ""),
            "market_timestamp": row.get("market_timestamp", ""),
            "ticker": row.get("ticker", ""),
            "timeframe": row.get("timeframe", ""),
            "source_bar_hash": row.get("source_bar_hash", ""),
            "split_id": row.get("split_id", ""),
        }
        for row in sorted(event_rows, key=lambda item: str(item.get("event_id", "")))
    ]
    return stable_hash(
        {
            "schema": "tradeo.audit_export.event_ledger_hash.v1",
            "pattern_id": pattern_id_value,
            "events": canonical_rows,
        }
    )


def selection_split_metadata(metrics: dict[str, Any]) -> dict[str, Any]:
    for key in ("selection_split",):
        value = metrics.get(key)
        if isinstance(value, dict):
            return value
    for key in ("research_hypothesis", "research_hypothesis_package"):
        payload = metrics.get(key)
        if isinstance(payload, dict) and isinstance(payload.get("selection_split"), dict):
            return payload["selection_split"]
    return {}


def experiment_split_bounds(examples: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, str]:
    split = selection_split_metadata(metrics)
    bounds = {
        "in_sample_start": normalize_ts(split.get("train_start") or metrics.get("train_start")),
        "in_sample_end": normalize_ts(split.get("train_end") or metrics.get("train_cutoff")),
        "out_of_sample_start": normalize_ts(split.get("holdout_start") or metrics.get("holdout_start")),
        "out_of_sample_end": normalize_ts(split.get("holdout_end") or metrics.get("holdout_end")),
        "source": "selection_split" if split else "",
    }
    if bounds["out_of_sample_start"] and bounds["out_of_sample_end"]:
        return bounds

    derived = derived_holdout_bounds_from_examples(examples, metrics)
    for key, value in derived.items():
        if not bounds.get(key):
            bounds[key] = value
    if derived and not bounds.get("source"):
        bounds["source"] = "exported_event_temporal_holdout"
    return bounds


def derived_holdout_bounds_from_examples(
    examples: list[dict[str, Any]],
    metrics: dict[str, Any],
) -> dict[str, str]:
    values = sorted(normalize_ts(example.get("window_end")) for example in examples if example.get("window_end"))
    values = [value for value in values if value]
    if len(values) < 2:
        return {}
    holdout_count = first_positive_int(
        metrics.get("holdout_sample_count"),
        metrics.get("out_of_sample_sample_count"),
        (metrics.get("out_of_sample_metrics") or {}).get("sample_count")
        if isinstance(metrics.get("out_of_sample_metrics"), dict)
        else None,
    )
    if holdout_count is None:
        holdout_count = max(1, int(round(len(values) * 0.2)))
    holdout_count = min(max(1, holdout_count), len(values) - 1)
    split_index = len(values) - holdout_count
    return {
        "in_sample_start": values[0],
        "in_sample_end": values[split_index - 1],
        "out_of_sample_start": values[split_index],
        "out_of_sample_end": values[-1],
    }


def first_positive_int(*values: Any) -> int | None:
    for value in values:
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return None


def experiment_trial_count(pattern: dict[str, Any], metrics: dict[str, Any]) -> int:
    value = first_positive_int(
        metrics.get("candidate_trial_count"),
        metrics.get("real_variant_count"),
        metrics.get("multiple_testing_trials"),
        pattern.get("variant_count"),
    )
    if value is not None:
        return value
    rr_metrics = pattern.get("rr_metrics_json")
    if isinstance(rr_metrics, dict) and rr_metrics:
        return len(rr_metrics)
    return 1


def audit_run_manifest_hash(pattern: dict[str, Any], run: dict[str, Any], context: dict[str, Any]) -> str:
    return stable_hash(
        {
            "schema": "tradeo.audit_export.run_manifest.v1",
            "run_id": pattern.get("run_id"),
            "run_params": run.get("params_json") or {},
            "repo_commit": context.get("git_commit", ""),
        }
    )


def audit_registry_row_hash(
    *,
    pattern: dict[str, Any],
    variant_id: str,
    parameters_json: dict[str, Any],
    run_manifest_hash: str,
) -> str:
    return stable_hash(
        {
            "schema": "tradeo.audit_export.registry_row.v1",
            "pattern_id": pattern_id(pattern),
            "variant_id": variant_id,
            "run_id": pattern.get("run_id"),
            "created_at": normalize_ts(pattern.get("created_at")),
            "parameters_json": parameters_json,
            "run_manifest_hash": run_manifest_hash,
        }
    )


def experiment_notes(
    *,
    used_export_event_hash: bool,
    used_audit_registry_hash: bool,
    split_source: str,
) -> str:
    notes = ["Research variant metrics are in R units; no paper trade PnL exists yet."]
    if used_export_event_hash:
        notes.append("event_ledger_hash derived from exported pattern_events.csv rows.")
    if used_audit_registry_hash:
        notes.append("registry hashes derived from audit export manifest inputs.")
    if split_source:
        notes.append(f"out_of_sample boundaries source={split_source}.")
    return " ".join(notes)


def active_blockers_metadata(metrics: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key in ("active_blockers", "promotion_blockers", "director_blockers"):
        value = metrics.get(key)
        if isinstance(value, list):
            blockers.extend(str(item) for item in value if str(item).strip())
        elif isinstance(value, str) and value.strip():
            blockers.append(value.strip())
    lab_execution = metrics.get("lab_execution")
    if isinstance(lab_execution, dict):
        value = lab_execution.get("promotion_blockers")
        if isinstance(value, list):
            blockers.extend(str(item) for item in value if str(item).strip())
    return blockers


def build_metrics_by_pattern(
    patterns: list[dict[str, Any]],
    examples_by_pattern: dict[int, list[dict[str, Any]]],
    paper_trade_rows: list[dict[str, Any]],
    *,
    event_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    trades_by_pattern: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in paper_trade_rows:
        trades_by_pattern[str(trade.get("pattern_id") or "")].append(trade)
    sample_counts, independent_counts = event_sample_counts(event_rows or [])
    rows = []
    for pattern in patterns:
        examples = examples_by_pattern.get(int(pattern["id"]), [])
        first_seen, last_seen = min_max_times(examples)
        metrics = best_rr_metrics(pattern)
        audit_id = pattern_id(pattern)
        trades = trades_by_pattern.get(audit_id, [])
        net_values = [safe_float(trade.get("net_pnl"), 0.0) for trade in trades]
        gross_values = [safe_float(trade.get("gross_pnl"), 0.0) for trade in trades]
        r_values = [safe_float(trade.get("r_multiple"), 0.0) for trade in trades]
        wins = [value for value in net_values if value > 0]
        losses = [abs(value) for value in net_values if value < 0]
        trade_count = len(trades)
        avg_win = metrics.get("avg_win_r", "")
        avg_loss = metrics.get("avg_loss_r", "")
        payoff = round(float(avg_win) / float(avg_loss), 6) if trades and avg_win not in ("", 0) and avg_loss not in ("", 0) else ""
        exported_event_count = sample_counts.get(audit_id, len(examples))
        verified_independent_count = independent_counts.get(audit_id, 0)
        rows.append({
            "pattern_id": audit_id,
            "sample_count": exported_event_count,
            "independent_sample_count": verified_independent_count,
            "trade_count": trade_count,
            "ticker_count": pattern.get("symbol_count", ""),
            "sector_count": "",
            "first_seen": first_seen,
            "last_seen": last_seen,
            "gross_pnl": round(sum(gross_values), 4) if trades else "0",
            "net_pnl": round(sum(net_values), 4) if trades else "0",
            "avg_trade": round(sum(net_values) / trade_count, 4) if trades else "",
            "median_trade": metrics.get("median_result_r", "") if trades else "",
            "std_trade": round(float(statistics.pstdev(net_values)), 4) if len(net_values) > 1 else "",
            "winrate": round(len(wins) / trade_count, 6) if trades else "",
            "avg_win": avg_win if trades else "",
            "avg_loss": avg_loss if trades else "",
            "payoff_ratio": payoff,
            "profit_factor": round(sum(wins) / sum(losses), 6) if losses else (round(sum(wins), 6) if wins else ""),
            "expectancy": round(sum(r_values) / trade_count, 6) if trades else "",
            "max_drawdown": max_drawdown(r_values) if trades else "",
            "max_consecutive_losses": "",
            "best_trade": max(net_values) if net_values else "",
            "worst_trade": min(net_values) if net_values else "",
            "top_5_trades_pnl": round(sum(sorted(net_values, reverse=True)[:5]), 4) if net_values else "",
            "bottom_5_trades_pnl": round(sum(sorted(net_values)[:5]), 4) if net_values else "",
            "pnl_without_best_trade": round(sum(net_values) - max(net_values), 4) if net_values else "",
            "pnl_without_top_5_trades": round(sum(net_values) - sum(sorted(net_values, reverse=True)[:5]), 4) if net_values else "",
            "pnl_without_worst_trade": round(sum(net_values) - min(net_values), 4) if net_values else "",
            "sharpe": "",
            "sortino": "",
            "calmar": "",
            "avg_holding_period_seconds": "",
            "notes": (
                "Operational columns use closed paper trades only; research R metrics remain in experiment_registry.csv."
                if trades
                else (
                    "No closed_lab_trades/paper trades; operational performance columns intentionally blank. "
                    f"Exported events={exported_event_count}; verified independent events={verified_independent_count}; "
                    f"raw pattern sample_count={pattern.get('sample_count', '')}."
                )
            ),
        })
    return rows


def event_sample_counts(event_rows: list[dict[str, Any]]) -> tuple[dict[str, int], dict[str, int]]:
    sample_counts: dict[str, int] = defaultdict(int)
    independent_counts: dict[str, int] = defaultdict(int)
    for row in event_rows:
        pid = str(row.get("pattern_id") or "")
        if not pid:
            continue
        sample_counts[pid] += 1
        if str(row.get("is_independent_sample") or "").strip().lower() == "true":
            independent_counts[pid] += 1
    return dict(sample_counts), dict(independent_counts)


def build_metrics_by_regime(
    patterns: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    paper_trade_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not paper_trade_rows:
        return [empty_bucket_row("market_regime")]
    events_by_pattern_regime: dict[tuple[str, str], int] = defaultdict(int)
    for row in event_rows:
        key = (str(row.get("pattern_id", "")), str(row.get("market_regime") or "unknown"))
        events_by_pattern_regime[key] += 1
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for trade in paper_trade_rows:
        regime = note_value(trade.get("notes"), "regime") or "unknown"
        buckets[(str(trade.get("pattern_id", "")), regime)].append(trade)
    rows = []
    known_patterns = {pattern_id(pattern) for pattern in patterns}
    for (pid, regime), trades in sorted(buckets.items()):
        row = performance_bucket_row(
            pattern_id_value=pid,
            bucket_value=regime,
            bucket_column="market_regime",
            trades=trades,
            event_count=events_by_pattern_regime.get((pid, regime), len(trades)),
            notes="Closed paper-trade performance grouped by persisted regime metadata.",
        )
        rows.append(row)
    missing_patterns = known_patterns - {str(row.get("pattern_id", "")) for row in rows}
    for pid in sorted(missing_patterns):
        rows.append(empty_bucket_row("market_regime", pattern_id_value=pid))
    return rows


def build_metrics_by_entry_variant(
    patterns: list[dict[str, Any]],
    paper_trade_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not paper_trade_rows:
        return [empty_bucket_row("entry_variant_id")]
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for trade in paper_trade_rows:
        variant = note_value(trade.get("notes"), "entry_variant") or "unknown"
        buckets[(str(trade.get("pattern_id", "")), variant)].append(trade)
    rows = []
    known_patterns = {pattern_id(pattern) for pattern in patterns}
    for (pid, variant), trades in sorted(buckets.items()):
        row = performance_bucket_row(
            pattern_id_value=pid,
            bucket_value=variant,
            bucket_column="entry_variant_id",
            trades=trades,
            event_count=len(trades),
            notes="Closed paper-trade performance grouped by entry variant metadata.",
        )
        rows.append(row)
    missing_patterns = known_patterns - {str(row.get("pattern_id", "")) for row in rows}
    for pid in sorted(missing_patterns):
        rows.append(empty_bucket_row("entry_variant_id", pattern_id_value=pid))
    return rows


def empty_bucket_row(bucket_column: str, *, pattern_id_value: str = "") -> dict[str, Any]:
    missing = (
        "closed_lab_trades with signal.metadata_json.regime.regime_key"
        if bucket_column == "market_regime"
        else "closed_lab_trades with signal.metadata_json.entry_variant_id"
    )
    return {
        "pattern_id": pattern_id_value,
        bucket_column: "",
        "analysis_available": "false",
        "empty_reason": f"no_closed_lab_trades: missing {missing}; paper_trades.csv has no matching closed trades.",
        "trade_count": "0",
        "event_count": "0",
        "gross_pnl": "0",
        "net_pnl": "0",
        "avg_trade": "",
        "expectancy_r": "",
        "winrate": "",
        "profit_factor": "",
        "max_drawdown": "",
        "best_trade": "",
        "worst_trade": "",
        "first_seen": "",
        "last_seen": "",
        "notes": "Explicit empty bucket for Director audit contract.",
    }


def performance_bucket_row(
    *,
    pattern_id_value: str,
    bucket_value: str,
    bucket_column: str,
    trades: list[dict[str, Any]],
    event_count: int,
    notes: str,
) -> dict[str, Any]:
    net_values = [safe_float(trade.get("net_pnl"), 0.0) for trade in trades]
    gross_values = [safe_float(trade.get("gross_pnl"), 0.0) for trade in trades]
    r_values = [safe_float(trade.get("r_multiple"), 0.0) for trade in trades]
    wins = [value for value in net_values if value > 0]
    losses = [abs(value) for value in net_values if value < 0]
    first_seen, last_seen = trade_time_bounds(trades)
    trade_count = len(trades)
    return {
        "pattern_id": pattern_id_value,
        bucket_column: bucket_value or "unknown",
        "analysis_available": "true",
        "empty_reason": "",
        "trade_count": trade_count,
        "event_count": event_count,
        "gross_pnl": round(sum(gross_values), 4),
        "net_pnl": round(sum(net_values), 4),
        "avg_trade": round(sum(net_values) / trade_count, 4) if trade_count else "",
        "expectancy_r": round(sum(r_values) / trade_count, 6) if trade_count else "",
        "winrate": round(len(wins) / trade_count, 6) if trade_count else "",
        "profit_factor": round(sum(wins) / sum(losses), 6) if losses else (round(sum(wins), 6) if wins else ""),
        "max_drawdown": max_drawdown(r_values),
        "best_trade": max(net_values) if net_values else "",
        "worst_trade": min(net_values) if net_values else "",
        "first_seen": first_seen,
        "last_seen": last_seen,
        "notes": notes,
    }


def note_value(notes: Any, key: str) -> str:
    for part in str(notes or "").split(";"):
        if "=" not in part:
            continue
        raw_key, value = part.split("=", 1)
        if raw_key.strip() == key:
            return value.strip()
    return ""


def trade_time_bounds(trades: list[dict[str, Any]]) -> tuple[str, str]:
    values = sorted(
        normalize_ts(
            trade.get("exit_fill_time")
            or trade.get("exit_order_time")
            or trade.get("entry_fill_time")
            or trade.get("entry_order_time")
        )
        for trade in trades
        if trade.get("exit_fill_time")
        or trade.get("exit_order_time")
        or trade.get("entry_fill_time")
        or trade.get("entry_order_time")
    )
    if not values:
        return "", ""
    return values[0], values[-1]


def build_metrics_by_ticker(examples_by_pattern: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for pid, examples in examples_by_pattern.items():
        fake_pattern = {"id": pid}
        for example in examples:
            buckets[(pattern_id(fake_pattern), str(example.get("symbol", "")))].append(example)
    rows = []
    for (pid, ticker), examples in sorted(buckets.items()):
        outcomes = [float(e.get("outcome_r") or 0.0) for e in examples]
        first_seen, last_seen = min_max_times(examples)
        rows.append({
            "pattern_id": pid,
            "ticker": ticker,
            "trade_count": "0",
            "event_count": len(examples),
            "net_pnl": "0",
            "winrate": ratio(sum(1 for value in outcomes if value > 0), len(outcomes)),
            "profit_factor": profit_factor(outcomes),
            "avg_trade": mean(outcomes),
            "max_drawdown": max_drawdown(outcomes),
            "first_seen": first_seen,
            "last_seen": last_seen,
            "notes": "Aggregated from stored representative examples, not full event ledger.",
        })
    return rows


def build_metrics_by_period(examples_by_pattern: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for pid, examples in examples_by_pattern.items():
        fake_pattern = {"id": pid}
        for example in examples:
            ts = normalize_ts(example.get("window_end"))
            if not ts:
                continue
            week_start = datetime.fromisoformat(ts).date().isoformat()
            buckets[(week_start, pattern_id(fake_pattern))].append(example)
    rows = []
    for (period_start, pid), examples in sorted(buckets.items()):
        outcomes = [float(e.get("outcome_r") or 0.0) for e in examples]
        rows.append({
            "period_start": normalize_ts(period_start),
            "period_end": normalize_ts(period_start),
            "period_type": "day",
            "pattern_id": pid,
            "event_count": len(examples),
            "trade_count": "0",
            "gross_pnl": "0",
            "net_pnl": "0",
            "winrate": ratio(sum(1 for value in outcomes if value > 0), len(outcomes)),
            "profit_factor": profit_factor(outcomes),
            "max_drawdown": max_drawdown(outcomes),
            "market_regime": "not_persisted",
            "notes": "Representative example outcome in R units only; no realized paper PnL.",
        })
    return rows


def ratio(num: int, den: int) -> str:
    return "" if den == 0 else f"{num / den:.6f}"


def mean(values: list[float]) -> str:
    return "" if not values else f"{sum(values) / len(values):.6f}"


def profit_factor(values: list[float]) -> str:
    wins = sum(v for v in values if v > 0)
    losses = abs(sum(v for v in values if v < 0))
    if losses == 0:
        return f"{wins:.6f}" if wins else ""
    return f"{wins / losses:.6f}"


def max_drawdown(values: list[float]) -> str:
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return f"{max_dd:.6f}" if values else ""


def write_manifest(
    package: Path,
    context: dict[str, Any],
    patterns: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    experiment_rows: list[dict[str, Any]],
    paper_trade_rows: list[dict[str, Any]],
    fill_rows: list[dict[str, Any]],
    metrics_regime_rows: list[dict[str, Any]],
    metrics_entry_variant_rows: list[dict[str, Any]],
) -> None:
    duplicate_groups = duplicate_event_groups(event_rows)
    manifest = {
        "audit_id": context["audit_id"],
        "created_at": context["created_at"],
        "created_by": "Claw",
        "repo_commit": context["git_commit"],
        "repo_branch": context["git_branch"],
        "data_source": "Interactive Brokers Paper",
        "environment": context["env"].get("TRADEO_ENVIRONMENT", "local"),
        "timezone": "Europe/Madrid",
        "market_timezone": "America/New_York",
        "asset_class": "US equities",
        "patterns_detected": len(patterns),
        "total_pattern_events": len(event_rows),
        "total_paper_trades": len(paper_trade_rows),
        "total_ib_fills": len(fill_rows),
        "total_experiment_variants": len(experiment_rows),
        "total_metrics_by_regime_rows": len(metrics_regime_rows),
        "total_metrics_by_entry_variant_rows": len(metrics_entry_variant_rows),
        "duplicate_event_groups": duplicate_groups["groups"],
        "duplicate_repeated_rows": duplicate_groups["repeated_rows"],
        "metric_breakdowns": {
            "by_regime": metric_breakdown_state(metrics_regime_rows),
            "by_entry_variant": metric_breakdown_state(metrics_entry_variant_rows),
        },
        "director_gate_required": True,
        "contains_sensitive_data": False,
        "account_ids_redacted": True,
        "orders_anonymized": True,
        "files": [
            {"path": "AUDIT_REQUEST.md", "description": "Human-readable request and pattern summary"},
            {"path": "AUDIT_SUMMARY_FOR_CHATGPT.md", "description": "Computed audit summary, rankings, concentration checks, and preliminary Claw recommendations"},
            {"path": "manifest.json", "description": "Machine-readable package metadata"},
            {"path": "pattern_catalog.csv", "description": "One row per detected pattern"},
            {"path": "pattern_events.csv", "description": "One row per exported independent/representative pattern occurrence"},
            {"path": "paper_trades.csv", "description": "One row per paper trade generated by a pattern"},
            {"path": "ib_fills.csv", "description": "Anonymized IB Paper fills"},
            {"path": "experiment_registry.csv", "description": "All tested variants, including discarded ones"},
            {"path": "metrics_by_pattern.csv", "description": "Aggregated metrics by pattern"},
            {"path": "metrics_by_ticker.csv", "description": "Aggregated metrics by pattern/ticker"},
            {"path": "metrics_by_period.csv", "description": "Aggregated metrics by period"},
            {"path": "metrics_by_regime.csv", "description": "Closed paper-trade performance by market regime, or explicit empty reason"},
            {"path": "metrics_by_entry_variant.csv", "description": "Closed paper-trade performance by entry variant, or explicit empty reason"},
            {"path": "code_references.md", "description": "Code paths and functions relevant to detection, validation, execution, and risk"},
            {"path": "data_lineage.md", "description": "Data origin, transformations, and known data-quality limits"},
            {"path": "known_issues.md", "description": "Known lab limitations and audit warnings"},
            {"path": "audit_checklist.md", "description": "Pre-review checklist for Claw and ChatGPT"},
            {"path": "chatgpt_questions.md", "description": "Explicit questions for the ChatGPT audit"},
            {"path": "reproducibility.md", "description": "Commands and environment needed to reproduce the export"},
            {"path": "file_hashes.sha256", "description": "SHA-256 hashes for package files"},
            {"path": "config_snapshot/detector_config.json", "description": "Detector and discovery settings, redacted"},
            {"path": "config_snapshot/universe_config.json", "description": "Universe settings used for the export"},
            {"path": "config_snapshot/risk_config.json", "description": "Risk settings used by the lab/bot"},
            {"path": "config_snapshot/execution_config.json", "description": "Execution and safety settings, redacted"},
            {"path": "config_snapshot/ib_paper_config.redacted.json", "description": "IB Paper connectivity metadata without account IDs or secrets"},
            {"path": "config_snapshot/data_config.json", "description": "Market data provider settings, redacted"},
        ],
    }
    (package / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def duplicate_event_groups(event_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in event_rows:
        group = str(row.get("duplicate_group_id") or "").strip()
        if group:
            counts[group] += 1
    repeated = [count for count in counts.values() if count > 1]
    return {"groups": len(repeated), "repeated_rows": sum(repeated)}


def metric_breakdown_state(rows: list[dict[str, Any]]) -> dict[str, Any]:
    available_rows = [
        row
        for row in rows
        if str(row.get("analysis_available", "")).strip().lower() == "true"
        and int(float(str(row.get("trade_count") or "0"))) > 0
    ]
    if available_rows:
        return {"available": True, "rows": len(available_rows), "empty_reason": ""}
    reason = next((str(row.get("empty_reason", "")).strip() for row in rows if row.get("empty_reason")), "")
    return {"available": False, "rows": len(rows), "empty_reason": reason}


def write_audit_request(
    package: Path,
    context: dict[str, Any],
    patterns: list[dict[str, Any]],
    pattern_rows: list[dict[str, Any]],
    metrics_rows: list[dict[str, Any]],
    experiment_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
) -> None:
    metric_by_pattern = {row["pattern_id"]: row for row in metrics_rows}
    timeframes = sorted({str(p.get("timeframe", "")) for p in patterns if p.get("timeframe")})
    discarded = sum(1 for row in experiment_rows if row["status"] == "discarded")
    total_paper_trades = sum(to_int(row.get("trade_count")) or 0 for row in metrics_rows)
    table_lines = [
        "| pattern_id | pattern_name | status | sample_count | trade_count | ticker_count | first_seen | last_seen | gross_pnl | net_pnl | winrate | avg_win | avg_loss | profit_factor | max_drawdown | notes |",
        "|---|---|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in pattern_rows:
        metrics = metric_by_pattern.get(row["pattern_id"], {})
        table_lines.append(
            "| {pattern_id} | {pattern_name} | {status} | {sample_count} | {trade_count} | {ticker_count} | {first_seen} | {last_seen} | {gross_pnl} | {net_pnl} | {winrate} | {avg_win} | {avg_loss} | {profit_factor} | {max_drawdown} | {notes} |".format(
                pattern_id=md(row["pattern_id"]),
                pattern_name=md(row["pattern_name"]),
                status=md(row["status"]),
                sample_count=md(metrics.get("sample_count", "")),
                trade_count=md(metrics.get("trade_count", "")),
                ticker_count=md(metrics.get("ticker_count", "")),
                first_seen=md(metrics.get("first_seen", "")),
                last_seen=md(metrics.get("last_seen", "")),
                gross_pnl=md(metrics.get("gross_pnl", "")),
                net_pnl=md(metrics.get("net_pnl", "")),
                winrate=md(metrics.get("winrate", "")),
                avg_win=md(metrics.get("avg_win", "")),
                avg_loss=md(metrics.get("avg_loss", "")),
                profit_factor=md(metrics.get("profit_factor", "")),
                max_drawdown=md(metrics.get("max_drawdown", "")),
                notes=md(metrics.get("notes", "")),
            )
        )

    text = f"""# Audit Request: {context['audit_id']}

## Resumen

- Fecha de generacion: {context['created_at']}
- Commit hash actual del sistema: `{context['git_commit']}`
- Rama actual: `{context['git_branch']}`
- Entorno usado: `{context['env'].get('TRADEO_ENVIRONMENT', 'local')}`
- Version del bot/laboratorio: Tradeo research lab at commit `{context['git_commit']}`
- Fuente de datos: IB Paper / Interactive Brokers historical market data provider
- Timezone principal: Europe/Madrid
- Timezone de mercado: America/New_York
- Mercado: US equities
- Timeframes usados: {', '.join(timeframes) or 'not_available'}
- Universo de activos analizado: `data/universe_us_mid_small.csv`, {len(context['universe_symbols'])} simbolos configurados
- Numero total de patrones detectados/exportados: {len(patterns)}
- Numero total de variantes probadas: {len(experiment_rows)}
- Numero total de variantes descartadas: {discarded}
- Numero de eventos exportados: {len(event_rows)}
- Numero de trades paper cerrados exportados: {total_paper_trades}. Si es 0, falta evidencia `closed_lab_trades` y no se puede rankear por PnL, regimen o entry_variant.

## Que esperamos de ChatGPT

Auditar si los patrones exportados son estadisticamente creibles, reproducibles y operables. En especial: sesgos, lookahead, survivorship, independencia de muestras, concentracion por ticker/fecha/regimen, robustez ante costes, dependencia de outliers, bugs del laboratorio y tests automaticos que faltan.

## Tabla Resumen

{chr(10).join(table_lines)}
"""
    (package / "AUDIT_REQUEST.md").write_text(text, encoding="utf-8")


def md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_code_references(package: Path, patterns: list[dict[str, Any]]) -> None:
    shared = """Detection:
- path: backend/tradeo/research/window_sampler.py
- function: WindowSampler.sample, WindowSampler._forward_outcome
- path: backend/tradeo/research/cluster_research_engine.py
- function: ClusterResearchEngine.discover, ClusterResearchEngine._cluster_window_size

Validation:
- path: backend/tradeo/research/reward_risk_analyzer.py
- function: RewardRiskAnalyzer.analyze, RewardRiskAnalyzer.metrics_for_rr
- path: backend/tradeo/research/validation_gate.py
- function: ValidationGate.evaluate_many

Registry:
- path: backend/tradeo/research/novel_pattern_registry.py
- function: NovelPatternRegistry.store_candidates, NovelPatternRegistry.upsert_candidate

Current Matching:
- path: backend/tradeo/research/novel_pattern_matcher.py
- function: NovelPatternMatcher.match_current

Execution:
- path: backend/tradeo/services/paper_broker.py
- function: PaperBroker.execute_signal
- path: backend/tradeo/services/ibkr_broker.py
- function: IBKRBroker.preview_signal_order, IBKRBroker.submit_signal_bracket

Risk:
- path: backend/tradeo/services/risk_manager.py
- function: RiskManager.check_signal, RiskManager.approve_signal_for_live

Configuration:
- path: backend/tradeo/core/config.py
- class: Settings
- path: config/strategy_cup_v0.json

Tests:
- path: backend/tradeo/tests/test_pattern_discovery_lab.py
- path: backend/tradeo/tests/test_reward_risk_analyzer.py
- path: backend/tradeo/tests/test_data_provider.py

TODOs conocidos:
- Persistir todos los eventos crudos, no solo ejemplos representativos.
- Persistir bid/ask/spread en el momento de senal.
- Persistir sector y regimen de mercado.
- Persistir fills IB anonimizados cuando se active paper execution.
"""
    lines = ["# Code References", ""]
    for pattern in patterns:
        lines.extend([f"## {pattern_id(pattern)}", "", f"Pattern name: `{pattern.get('name', '')}`", "", shared, ""])
    (package / "code_references.md").write_text("\n".join(lines), encoding="utf-8")


def write_config_snapshot(config_dir: Path, context: dict[str, Any]) -> None:
    env = context["env"]
    config_dir.mkdir(parents=True, exist_ok=True)
    strategy = read_json(ROOT / "config" / "strategy_cup_v0.json")
    snapshots = {
        "detector_config.json": {
            "discovery_period": env.get("TRADEO_DISCOVERY_PERIOD", "5y"),
            "discovery_interval": env.get("TRADEO_DISCOVERY_INTERVAL", "1d"),
            "discovery_window_sizes": env.get("TRADEO_DISCOVERY_WINDOW_SIZES", "20,50,100,200"),
            "discovery_forward_bars": env.get("TRADEO_DISCOVERY_FORWARD_BARS", "5,10,20"),
            "discovery_rr_levels": env.get("TRADEO_DISCOVERY_RR_LEVELS", "1.5,2.0,2.5,3.0,4.0,5.0"),
            "discovery_stride": env.get("TRADEO_DISCOVERY_STRIDE", "3"),
            "discovery_min_cluster_size": env.get("TRADEO_DISCOVERY_MIN_CLUSTER_SIZE", "60"),
            "discovery_max_clusters_per_window": env.get("TRADEO_DISCOVERY_MAX_CLUSTERS_PER_WINDOW", "12"),
            "strategy_config": strategy,
        },
        "universe_config.json": {
            "universe_file": "data/universe_us_mid_small.csv",
            "asset_class": "US equities",
            "symbol_count": len(context["universe_symbols"]),
            "symbols": context["universe_symbols"],
        },
        "risk_config.json": {
            "trading_mode": env.get("TRADEO_TRADING_MODE", "paper"),
            "live_trading_enabled": env.get("TRADEO_LIVE_TRADING_ENABLED", "false"),
            "kill_switch_enabled": env.get("TRADEO_KILL_SWITCH_ENABLED", "false"),
            "risk_per_trade_pct": env.get("TRADEO_RISK_PER_TRADE_PCT", "0.01"),
            "daily_loss_limit_pct": env.get("TRADEO_DAILY_LOSS_LIMIT_PCT", "0.02"),
            "monthly_loss_limit_pct": env.get("TRADEO_MONTHLY_LOSS_LIMIT_PCT", "0.08"),
            "max_open_positions": env.get("TRADEO_MAX_OPEN_POSITIONS", "4"),
            "max_position_value_pct": env.get("TRADEO_MAX_POSITION_VALUE_PCT", "0.45"),
        },
        "execution_config.json": {
            "allow_longs": env.get("TRADEO_ALLOW_LONGS", "true"),
            "allow_shorts": env.get("TRADEO_ALLOW_SHORTS", "true"),
            "allow_options": env.get("TRADEO_ALLOW_OPTIONS", "false"),
            "allow_margin": env.get("TRADEO_ALLOW_MARGIN", "false"),
            "ibkr_readonly": env.get("TRADEO_IBKR_READONLY", "true"),
            "ibkr_allow_market_orders": env.get("TRADEO_IBKR_ALLOW_MARKET_ORDERS", "false"),
            "ibkr_max_order_value_usd": env.get("TRADEO_IBKR_MAX_ORDER_VALUE_USD", "1500"),
        },
        "ib_paper_config.redacted.json": {
            "data_source": "Interactive Brokers Paper",
            "ibkr_host": env.get("TRADEO_IBKR_HOST", "host.docker.internal"),
            "ibkr_port": env.get("TRADEO_IBKR_PORT", "7497"),
            "ibkr_client_id": env.get("TRADEO_IBKR_CLIENT_ID", "17"),
            "ibkr_account": "REDACTED_OR_EMPTY",
            "account_id_redacted": True,
            "readonly": env.get("TRADEO_IBKR_READONLY", "true"),
        },
        "data_config.json": {
            "market_data_provider": env.get("TRADEO_MARKET_DATA_PROVIDER", "ibkr"),
            "allow_synthetic_market_data": env.get("TRADEO_ALLOW_SYNTHETIC_MARKET_DATA", "false"),
            "scan_period": env.get("TRADEO_SCAN_PERIOD", "2y"),
            "scan_interval": env.get("TRADEO_SCAN_INTERVAL", "1d"),
            "min_avg_dollar_volume": env.get("TRADEO_MIN_AVG_DOLLAR_VOLUME", "5000000"),
            "min_price": env.get("TRADEO_MIN_PRICE", "2.0"),
            "max_atr_pct": env.get("TRADEO_MAX_ATR_PCT", "0.14"),
        },
    }
    for name, payload in snapshots.items():
        (config_dir / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_supporting_docs(
    package: Path,
    context: dict[str, Any],
    patterns: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    experiment_rows: list[dict[str, Any]],
    paper_trade_rows: list[dict[str, Any]],
    fill_rows: list[dict[str, Any]],
) -> None:
    (package / "data_lineage.md").write_text(f"""# Data Lineage

- Fuente de barras/precios: Interactive Brokers Paper historical data through `IBKRHistoricalDataProvider`.
- Fuente de bid/ask: no persistida en este paquete; campos bid/ask/spread quedan vacios.
- Fuente de paper trades: `paper_trades.csv` exporta {len(paper_trade_rows)} filas desde Laboratorio cuando existen.
- Fuente de fills: `ib_fills.csv` exporta {len(fill_rows)} fills paper reconstruidos desde trades cerrados/registrados cuando existen.
- Fuente de breakdown por regimen: `metrics_by_regime.csv` usa closed paper trades si existen; si no, contiene `empty_reason`.
- Fuente de breakdown por entry variant: `metrics_by_entry_variant.csv` usa `entry_variant_id` de metadata de senal si existen closed paper trades; si no, contiene `empty_reason`.
- Fuente de comisiones/slippage: se exportan desde metadata de trade si estan persistidas; si no, quedan vacias o en cero.
- Fuente de volumen: barras OHLCV de IBKR cuando estan disponibles; el export actual solo conserva volumen en features agregadas si el detector lo genero.
- Ajustes por splits/dividendos: no documentados por barra en el laboratorio actual; requiere auditoria adicional del proveedor IBKR.
- Acciones deslistadas: el universo actual viene de `data/universe_us_mid_small.csv`; no hay control completo de survivorship bias.
- Control survivorship bias: pendiente; el paquete documenta universo usado pero no contiene delistings.
- Control lookahead bias: `WindowSampler` usa ventana hasta `window_end` y forward path posterior solo para label/metricas; revisar codigo citado.
- Sincronizacion timestamps: timestamps diarios sin zona se normalizan a `+00:00`; timezone de mercado declarada `America/New_York`.
- Datos disponibles en el momento de senal: features de embedding sobre ventana historica hasta `window_end`; forward outcomes se calculan despues y no deben usarse en deteccion.
- Datos calculados despues: `outcome_r`, `mfe_r`, `mae_r`, profit factor, expectancy, drawdown, in/out-of-sample metrics.
- Snapshot: generado {context['created_at']} desde API local en caliente; el laboratorio continuo puede seguir insertando runs despues del export.
""", encoding="utf-8")

    (package / "known_issues.md").write_text(f"""# Known Issues

- El laboratorio guarda ejemplos representativos por patron, no todos los eventos crudos. Eventos exportados: {len(event_rows)}.
- Puede haber muestras solapadas por `stride`; independencia estadistica requiere auditoria adicional.
- Bid/ask/spread no estan persistidos en algunos eventos.
- Slippage estimado solo es auditable si cada trade lo persiste en metadata.
- Universo limitado a `data/universe_us_mid_small.csv`.
- Datos actuales vienen de IB Paper/historicos; no equivalen a ejecucion live.
- Posible survivorship bias: no hay archivo de tickers deslistados.
- Posible concentracion por pocos tickers o regimenes: revisar `metrics_by_ticker.csv` y `metrics_by_period.csv`.
- Regimen de mercado y sector se exportan desde features/metadata cuando estan disponibles.
- `metrics_by_regime.csv` y `metrics_by_entry_variant.csv` deben tener filas accionables solo cuando haya `closed_lab_trades`; si no, documentan la razon de vacio.
- Los timestamps diarios se normalizan a UTC cuando el dato original no trae timezone explicita.
- Fills IB Paper exportados en este paquete: {len(fill_rows)}.
- El paquete contiene {len(patterns)} patrones y {len(experiment_rows)} variantes RR; ChatGPT debe revisar tambien variantes descartadas.
""", encoding="utf-8")

    (package / "audit_checklist.md").write_text("""# Audit Checklist

- [ ] No hay claves ni tokens.
- [ ] No hay account IDs reales.
- [ ] Todos los timestamps tienen timezone.
- [ ] Cada patron tiene regla de deteccion clara.
- [ ] Cada patron tiene regla de entrada clara.
- [ ] Cada patron tiene regla de salida clara.
- [ ] Costes separados: comision, spread, slippage, fees.
- [ ] Hay lista de variantes descartadas.
- [ ] Hay numero total de experimentos probados.
- [ ] Hay datos por ticker.
- [ ] Hay datos por periodo.
- [ ] Hay fills de IB Paper o archivo vacio con cabecera.
- [ ] Hay code references.
- [ ] Hay config snapshot.
- [ ] Se indica si cada muestra es independiente.
- [ ] Se indica si hay datos in-sample, out-of-sample y paper-live.
- [ ] Se documentan known issues.
""", encoding="utf-8")

    (package / "chatgpt_questions.md").write_text("""# ChatGPT Questions

1. ¿Los patrones exportados estan definidos de forma objetiva y reproducible?
2. ¿Hay riesgo de lookahead bias?
3. ¿Hay riesgo de survivorship bias?
4. ¿Las muestras son realmente independientes?
5. ¿Hay concentración excesiva en pocos tickers?
6. ¿Hay concentración excesiva en pocos días o régimen de mercado?
7. ¿Los resultados sobreviven a costes realistas?
8. ¿El EV neto es positivo?
9. ¿El patrón depende de pocos trades extremos?
10. ¿Qué patrón debería priorizarse?
11. ¿Qué patrón debería descartarse o congelarse?
12. ¿Qué datos faltan para una validación exhaustiva?
13. ¿Qué cambios necesita el laboratorio de research?
14. ¿Qué tests automáticos deberían añadirse?
15. ¿Qué umbrales mínimos deberían exigirse antes de pasar a paper controlado o live?

Nota: esta exportacion contiene todos los patrones almacenados en el snapshot, no solo cuatro. Si se desea una auditoria limitada a cuatro candidatos, filtrar `pattern_catalog.csv` y mantener el manifest actualizado.
""", encoding="utf-8")

    (package / "reproducibility.md").write_text(f"""# Reproducibility

## Comando usado para exportar patrones

```bash
python3 research/audit_bridge/export_audit_package.py --audit-id {context['audit_id']}
```

## Comando usado para exportar trades

El mismo exportador crea `paper_trades.csv`. Si no hay trades paper en DB, genera cabecera vacia.

## Comando usado para exportar fills

El mismo exportador crea `ib_fills.csv`. Si no hay fills IB Paper anonimizados en DB, genera cabecera vacia.

## Variables de entorno necesarias

- `TRADEO_ADMIN_USERNAME`
- `TRADEO_ADMIN_PASSWORD`
- `TRADEO_MARKET_DATA_PROVIDER`
- `TRADEO_ALLOW_SYNTHETIC_MARKET_DATA`
- `TRADEO_IBKR_HOST`
- `TRADEO_IBKR_PORT`
- `TRADEO_IBKR_CLIENT_ID`
- `TRADEO_IBKR_READONLY`

No incluir valores secretos en el paquete.

## Dependencias principales

- Python standard library para export/validation.
- Tradeo backend local en `http://localhost:8000/api`.
- Docker Compose stack de Tradeo si se quiere regenerar DB/API.
- Backend: Python 3.12 en contenedor.
- Frontend: Node/Next.js segun `frontend/Dockerfile`.

## Validar paquete completo despues del Director gate

```bash
python3 research/audit_bridge/validate_audit_package.py research/audit_bridge/requests/{context['audit_id']}
```

## Ejecutar Director gate antes del validator estricto

```bash
python3 research/audit_bridge/director_gate.py research/audit_bridge/requests/{context['audit_id']} \
  --json-output research/audit_bridge/requests/{context['audit_id']}/director_gate_result.json \
  --markdown-output research/audit_bridge/requests/{context['audit_id']}/director_gate_result.md \
  --allow-blocked-exit-zero
```

## Hashes

Ver `file_hashes.sha256`.
""", encoding="utf-8")


def write_audit_summary_for_chatgpt(
    package: Path,
    pattern_rows: list[dict[str, Any]],
    event_rows: list[dict[str, Any]],
    experiment_rows: list[dict[str, Any]],
    metrics_rows: list[dict[str, Any]],
    metrics_ticker_rows: list[dict[str, Any]],
    metrics_period_rows: list[dict[str, Any]],
    metrics_regime_rows: list[dict[str, Any]],
    metrics_entry_variant_rows: list[dict[str, Any]],
    paper_trade_rows: list[dict[str, Any]],
    fill_rows: list[dict[str, Any]],
) -> None:
    catalog_by_pattern = {row["pattern_id"]: row for row in pattern_rows}
    sample_counts = sorted(to_int(row.get("independent_sample_count")) for row in metrics_rows)
    sample_counts = [value for value in sample_counts if value is not None]
    total_patterns = len(pattern_rows)

    events_by_pattern: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in event_rows:
        events_by_pattern[str(row.get("pattern_id", ""))].append(row)

    summary_rows = [
        ("total patterns", total_patterns),
        ("min independent_sample_count", sample_counts[0] if sample_counts else ""),
        ("p25", percentile(sample_counts, 0.25)),
        ("median", percentile(sample_counts, 0.50)),
        ("p75", percentile(sample_counts, 0.75)),
        ("p90", percentile(sample_counts, 0.90)),
        ("max", sample_counts[-1] if sample_counts else ""),
        ("patterns >= 30 samples", count_ge(sample_counts, 30)),
        ("patterns >= 50 samples", count_ge(sample_counts, 50)),
        ("patterns >= 100 samples", count_ge(sample_counts, 100)),
        ("patterns >= 300 samples", count_ge(sample_counts, 300)),
        ("patterns >= 500 samples", count_ge(sample_counts, 500)),
    ]

    top_by_samples = sorted(
        metrics_rows,
        key=lambda row: (to_int(row.get("independent_sample_count")) or 0, to_int(row.get("sample_count")) or 0),
        reverse=True,
    )[:30]

    pnl_rows = [
        row for row in metrics_rows
        if (to_int(row.get("trade_count")) or 0) > 0 and to_float(row.get("net_pnl")) is not None
    ]
    top_by_pnl = sorted(pnl_rows, key=lambda row: to_float(row.get("net_pnl")) or 0.0, reverse=True)[:30]

    pnl_best_trade = [
        row for row in pnl_rows
        if materially_depends_on(row.get("net_pnl"), row.get("pnl_without_best_trade"))
    ]
    pnl_top5 = [
        row for row in pnl_rows
        if materially_depends_on(row.get("net_pnl"), row.get("pnl_without_top_5_trades"))
    ]
    few_tickers = [row for row in metrics_rows if (to_int(row.get("ticker_count")) or 0) < 5]
    few_days = [
        {"pattern_id": pid, "days": len(unique_event_days(rows))}
        for pid, rows in events_by_pattern.items()
        if len(unique_event_days(rows)) < 5
    ]
    single_regime = [
        {"pattern_id": pid, "regime": next(iter(regimes)) if regimes else ""}
        for pid, rows in events_by_pattern.items()
        for regimes in [{str(row.get("market_regime", "")).strip() for row in rows if str(row.get("market_regime", "")).strip()}]
        if len(regimes) == 1
    ]

    duplicate_groups: dict[str, int] = defaultdict(int)
    for row in event_rows:
        group = str(row.get("duplicate_group_id", "")).strip()
        if group:
            duplicate_groups[group] += 1
    possible_duplicates = sum(count - 1 for count in duplicate_groups.values() if count > 1)
    non_independent = sum(1 for row in event_rows if str(row.get("is_independent_sample", "")).lower() != "true")
    timestamps_without_timezone = count_timestamps_without_timezone(pattern_rows, event_rows, experiment_rows, metrics_rows, metrics_ticker_rows, metrics_period_rows)
    leakage_features = leakage_feature_rows(event_rows)
    uses_future = [row for row in pattern_rows if str(row.get("uses_future_data", "")).lower() == "true"]
    duplicate_variants = count_duplicate_variants(experiment_rows)
    missing_exit = [row for row in pattern_rows if not str(row.get("exit_rule_plaintext", "")).strip()]
    missing_entry = [row for row in pattern_rows if not str(row.get("entry_rule_plaintext", "")).strip()]

    candidates_for_audit = [
        row for row in top_by_samples
        if (to_int(row.get("independent_sample_count")) or 0) >= 100 and (to_int(row.get("ticker_count")) or 0) >= 8
    ][:30]
    needs_more_samples = [row for row in metrics_rows if (to_int(row.get("independent_sample_count")) or 0) < 100]
    freeze_until_more_data = [row for row in metrics_rows if (to_int(row.get("trade_count")) or 0) == 0]
    discard_candidates = [
        row for row in metrics_rows
        if (to_int(row.get("independent_sample_count")) or 0) < 30 or (to_int(row.get("ticker_count")) or 0) < 5
    ]

    validation_stance = (
        f"**Validation stance:** no pattern is approved automatically. "
        f"This package includes {len(paper_trade_rows)} paper trades and {len(fill_rows)} reconstructed fills; "
        "Director must still verify execution quality before promotion."
        if paper_trade_rows or fill_rows
        else "**Validation stance:** no pattern is approved for operation in this package. Paper/live execution validation is unavailable because `paper_trades.csv` and `ib_fills.csv` have zero rows; there are no `closed_lab_trades` from which to rank by regime or entry variant."
    )
    lines = [
        "# Audit Summary For ChatGPT",
        "",
        "Generated from the package CSV exports. This is a lab-audit and candidate-ranking aid only.",
        "",
        validation_stance,
        "",
        "## A. Sample Distribution By Pattern",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    lines.extend(f"| {label} | {value} |" for label, value in summary_rows)

    lines.extend([
        "",
        "## B. Top 30 Patterns By Independent Sample Count",
        "",
        "| pattern_id | pattern_name | independent_sample_count | event_count | ticker_count | first_seen | last_seen | net_pnl_estimado | profit_factor | max_drawdown | status |",
        "|---|---|---:|---:|---:|---|---|---:|---:|---:|---|",
    ])
    for row in top_by_samples:
        catalog = catalog_by_pattern.get(row["pattern_id"], {})
        lines.append(
            f"| {md(row['pattern_id'])} | {md(catalog.get('pattern_name', ''))} | {cell(row.get('independent_sample_count'))} | {cell(row.get('sample_count'))} | {cell(row.get('ticker_count'))} | {cell(row.get('first_seen'))} | {cell(row.get('last_seen'))} | {cell(row.get('net_pnl'))} | {cell(row.get('profit_factor'))} | {cell(row.get('max_drawdown'))} | {md(catalog.get('status', ''))} |"
        )

    lines.extend([
        "",
        "## C. Top 30 Patterns By Estimated Net PnL",
        "",
    ])
    if top_by_pnl:
        lines.extend([
            "| pattern_id | pattern_name | independent_sample_count | trade_count | ticker_count | net_pnl | profit_factor | max_drawdown | pnl_without_best_trade | pnl_without_top_5_trades | status |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ])
        for row in top_by_pnl:
            catalog = catalog_by_pattern.get(row["pattern_id"], {})
            lines.append(
                f"| {md(row['pattern_id'])} | {md(catalog.get('pattern_name', ''))} | {cell(row.get('independent_sample_count'))} | {cell(row.get('trade_count'))} | {cell(row.get('ticker_count'))} | {cell(row.get('net_pnl'))} | {cell(row.get('profit_factor'))} | {cell(row.get('max_drawdown'))} | {cell(row.get('pnl_without_best_trade'))} | {cell(row.get('pnl_without_top_5_trades'))} | {md(catalog.get('status', ''))} |"
            )
    else:
        lines.append("No available `net_pnl` values. Current package has zero paper trades/fills, so PnL ranking is not actionable.")

    lines.extend([
        "",
        "## D. Concentration",
        "",
        "| check | count | notes |",
        "|---|---:|---|",
        f"| patterns whose PnL depends on best trade | {len(pnl_best_trade)} | Requires non-empty PnL fields. |",
        f"| patterns whose PnL depends on top 5 trades | {len(pnl_top5)} | Requires non-empty PnL fields. |",
        f"| patterns concentrated in fewer than 5 tickers | {len(few_tickers)} | Based on `metrics_by_pattern.ticker_count`. |",
        f"| patterns concentrated in fewer than 5 days | {len(few_days)} | Based on unique event dates in `pattern_events.csv`. |",
        f"| patterns concentrated in one market regime | {len(single_regime)} | Current export mostly uses `not_persisted`; regime audit is limited. |",
        f"| regime performance buckets available | {count_available_bucket_rows(metrics_regime_rows)} | See `metrics_by_regime.csv`; empty rows include `empty_reason`. |",
        f"| entry variant performance buckets available | {count_available_bucket_rows(metrics_entry_variant_rows)} | See `metrics_by_entry_variant.csv`; empty rows include `empty_reason`. |",
        "",
        "## E. Automatically Detected Risks",
        "",
        "| risk | count | notes |",
        "|---|---:|---|",
        f"| possible duplicated event rows | {possible_duplicates} | Counted from repeated `duplicate_group_id`. |",
        f"| signals not marked independent | {non_independent} | Any `is_independent_sample` value other than `true`. |",
        f"| timestamps without timezone | {timestamps_without_timezone} | Checked exported timestamp-like fields. |",
        f"| features with possible leakage keywords | {len(leakage_features)} | Keywords: future, forward, outcome, target, label, mfe, mae. Review manually. |",
        f"| patterns with uses_future_data = true | {len(uses_future)} | Must be zero unless explicitly justified. |",
        f"| duplicated or nearly duplicated variants | {duplicate_variants} | Exact duplicate `(pattern_id, parameters_json)` pairs. |",
        f"| patterns without clear exit rule | {len(missing_exit)} | Empty `exit_rule_plaintext`. |",
        f"| patterns without clear entry rule | {len(missing_entry)} | Empty `entry_rule_plaintext`. |",
        "",
        "## F. Preliminary Claw Recommendation",
        "",
        "| bucket | count | recommendation |",
        "|---|---:|---|",
        f"| candidates_for_audit | {len(candidates_for_audit)} | Review first for lab quality and statistical robustness; do not approve for operation. |",
        f"| needs_more_samples | {len(needs_more_samples)} | Gather more independent samples before statistical claims. |",
        f"| likely_duplicates | {possible_duplicates + duplicate_variants} | Deduplicate or explain before ranking. |",
        f"| freeze_until_more_data | {len(freeze_until_more_data)} | No paper trades yet; execution validation unavailable. |",
        f"| discard_candidates | {len(discard_candidates)} | Low sample or low ticker diversity; keep rejected unless new evidence appears. |",
        f"| no_closed_lab_trades_bucket_gap | {int(not paper_trade_rows)} | Fill `paper_trades.csv` with closed lab trades carrying regime and entry_variant metadata before bucket ranking. |",
        "",
        "### First Candidates For Audit",
        "",
        "| pattern_id | pattern_name | independent_sample_count | ticker_count | status |",
        "|---|---|---:|---:|---|",
    ])
    for row in candidates_for_audit[:30]:
        catalog = catalog_by_pattern.get(row["pattern_id"], {})
        lines.append(
            f"| {md(row['pattern_id'])} | {md(catalog.get('pattern_name', ''))} | {cell(row.get('independent_sample_count'))} | {cell(row.get('ticker_count'))} | {md(catalog.get('status', ''))} |"
        )

    lines.extend(["", "### Regime Bucket Snapshot", ""])
    available_regime = [row for row in metrics_regime_rows if str(row.get("analysis_available", "")).lower() == "true"]
    if available_regime:
        lines.extend([
            "| pattern_id | market_regime | trade_count | net_pnl | expectancy_r | profit_factor |",
            "|---|---|---:|---:|---:|---:|",
        ])
        for row in sorted(available_regime, key=lambda item: to_float(item.get("expectancy_r")) or 0.0, reverse=True)[:20]:
            lines.append(
                f"| {md(row.get('pattern_id', ''))} | {md(row.get('market_regime', ''))} | {cell(row.get('trade_count'))} | {cell(row.get('net_pnl'))} | {cell(row.get('expectancy_r'))} | {cell(row.get('profit_factor'))} |"
            )
    else:
        reason = next((str(row.get("empty_reason", "")).strip() for row in metrics_regime_rows if row.get("empty_reason")), "")
        lines.append(reason or "No regime bucket performance is available.")

    lines.extend(["", "### Entry Variant Bucket Snapshot", ""])
    available_variants = [row for row in metrics_entry_variant_rows if str(row.get("analysis_available", "")).lower() == "true"]
    if available_variants:
        lines.extend([
            "| pattern_id | entry_variant_id | trade_count | net_pnl | expectancy_r | profit_factor |",
            "|---|---|---:|---:|---:|---:|",
        ])
        for row in sorted(available_variants, key=lambda item: to_float(item.get("expectancy_r")) or 0.0, reverse=True)[:20]:
            lines.append(
                f"| {md(row.get('pattern_id', ''))} | {md(row.get('entry_variant_id', ''))} | {cell(row.get('trade_count'))} | {cell(row.get('net_pnl'))} | {cell(row.get('expectancy_r'))} | {cell(row.get('profit_factor'))} |"
            )
    else:
        reason = next((str(row.get("empty_reason", "")).strip() for row in metrics_entry_variant_rows if row.get("empty_reason")), "")
        lines.append(reason or "No entry-variant bucket performance is available.")

    lines.extend([
        "",
        "### Bottom-Line Instruction",
        "",
        "Do not approve any pattern from this package. Use it to audit the research lab, detect data/logic issues, and rank candidates for future paper validation.",
        "",
    ])
    (package / "AUDIT_SUMMARY_FOR_CHATGPT.md").write_text("\n".join(lines), encoding="utf-8")


def count_available_bucket_rows(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if str(row.get("analysis_available", "")).strip().lower() == "true")


def to_int(value: Any) -> int | None:
    try:
        text = str(value).strip()
        if not text:
            return None
        return int(float(text))
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def percentile(values: list[int], q: float) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return str(values[0])
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(values) - 1)
    weight = pos - lo
    return f"{values[lo] * (1 - weight) + values[hi] * weight:.2f}"


def count_ge(values: list[int], threshold: int) -> int:
    return sum(1 for value in values if value >= threshold)


def cell(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    return md(text) if text else ""


def materially_depends_on(total_value: Any, reduced_value: Any) -> bool:
    total = to_float(total_value)
    reduced = to_float(reduced_value)
    if total is None or reduced is None or abs(total) < 1e-9:
        return False
    return abs(total - reduced) / abs(total) >= 0.5


def unique_event_days(rows: list[dict[str, Any]]) -> set[str]:
    days = set()
    for row in rows:
        timestamp = str(row.get("market_timestamp") or row.get("detected_at") or "").strip()
        if len(timestamp) >= 10:
            days.add(timestamp[:10])
    return days


def count_timestamps_without_timezone(*row_groups: list[dict[str, Any]]) -> int:
    timestamp_columns = {
        "created_at",
        "first_seen",
        "last_seen",
        "detected_at",
        "market_timestamp",
        "bar_open_time",
        "bar_close_time",
        "tested_at",
        "dataset_start",
        "dataset_end",
        "in_sample_start",
        "in_sample_end",
        "out_of_sample_start",
        "out_of_sample_end",
        "paper_live_start",
        "paper_live_end",
        "period_start",
        "period_end",
    }
    count = 0
    for rows in row_groups:
        for row in rows:
            for key, value in row.items():
                if key not in timestamp_columns:
                    continue
                text = str(value).strip()
                if text and not re.search(r"(?:Z|[+-]\d\d:\d\d)$", text):
                    count += 1
    return count


def leakage_feature_rows(event_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pattern = re.compile(r"\b(future|forward|outcome|target|label|mfe|mae)\b", re.I)
    return [row for row in event_rows if pattern.search(str(row.get("features_used_json", "")))]


def count_duplicate_variants(experiment_rows: list[dict[str, Any]]) -> int:
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    for row in experiment_rows:
        key = (str(row.get("pattern_id", "")), str(row.get("parameters_json", "")))
        if key in seen:
            duplicates += 1
        seen.add(key)
    return duplicates


def write_hashes(package: Path) -> None:
    lines = []
    for path in sorted(package.rglob("*")):
        if not path.is_file() or path.name == "file_hashes.sha256":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(package)}")
    (package / "file_hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
