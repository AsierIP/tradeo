#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


REQUIRED_BRIDGE_FILES = [
    "README.md",
    "AUDIT_CONTRACT.md",
    "validate_audit_package.py",
    "requirements.txt",
]

REQUIRED_FILES = [
    "AUDIT_REQUEST.md",
    "AUDIT_SUMMARY_FOR_CHATGPT.md",
    "manifest.json",
    "pattern_catalog.csv",
    "pattern_events.csv",
    "paper_trades.csv",
    "ib_fills.csv",
    "experiment_registry.csv",
    "metrics_by_pattern.csv",
    "metrics_by_ticker.csv",
    "metrics_by_period.csv",
    "metrics_by_regime.csv",
    "metrics_by_entry_variant.csv",
    "code_references.md",
    "config_snapshot/detector_config.json",
    "config_snapshot/universe_config.json",
    "config_snapshot/risk_config.json",
    "config_snapshot/execution_config.json",
    "config_snapshot/ib_paper_config.redacted.json",
    "config_snapshot/data_config.json",
    "data_lineage.md",
    "known_issues.md",
    "audit_checklist.md",
    "chatgpt_questions.md",
    "reproducibility.md",
    "director_gate_result.json",
]

CSV_COLUMNS = {
    "pattern_catalog.csv": [
        "pattern_id", "pattern_name", "pattern_version", "description", "hypothesis",
        "detection_rule_plaintext", "entry_rule_plaintext", "exit_rule_plaintext",
        "stop_rule_plaintext", "take_profit_rule_plaintext", "time_stop_rule_plaintext",
        "timeframe", "asset_class", "universe", "session_filter", "min_volume_filter",
        "min_price_filter", "uses_fundamental_data", "uses_news_data", "uses_options_data",
        "uses_future_data", "known_risks", "status", "created_at", "first_seen", "last_seen",
    ],
    "pattern_events.csv": [
        "event_id", "pattern_id", "detected_at", "market_timestamp", "timezone", "ticker",
        "exchange", "timeframe", "bar_open_time", "bar_close_time", "signal_price",
        "bid_at_signal", "ask_at_signal", "spread_at_signal", "volume_at_signal",
        "atr_at_signal", "volatility_context", "market_regime", "sector",
        "was_trade_triggered", "trade_id", "reason_not_traded", "duplicate_group_id",
        "is_independent_sample", "data_available_at_signal", "available_data_cutoff_ts",
        "decision_ts", "entry_eligible_ts", "label_generated_ts", "source_bar_hash",
        "split_id", "features_used_json", "notes",
    ],
    "paper_trades.csv": [
        "trade_id", "event_id", "pattern_id", "ticker", "side", "quantity", "entry_signal_time",
        "evidence_type", "evidence_quality", "entry_order_time", "entry_fill_time",
        "entry_signal_price", "entry_order_type", "entry_limit_price", "entry_fill_price",
        "exit_signal_time", "exit_order_time",
        "exit_fill_time", "exit_order_type", "exit_limit_price", "exit_fill_price",
        "exit_reason", "gross_pnl", "commission", "estimated_spread_cost",
        "estimated_slippage", "other_fees", "net_pnl", "return_pct", "mae", "mfe",
        "holding_period_seconds", "risk_amount", "r_multiple", "account_equity_snapshot",
        "position_size_method", "notes",
    ],
    "ib_fills.csv": [
        "fill_id_hash", "trade_id", "order_id_hash", "ib_execution_time", "timezone", "ticker",
        "side", "quantity", "price", "commission", "liquidity_flag", "exchange", "order_type",
        "account_id_redacted", "raw_status", "notes",
    ],
    "experiment_registry.csv": [
        "experiment_id", "pattern_id", "variant_id", "created_at", "tested_at", "status",
        "reason_status", "parameters_json", "dataset_start", "dataset_end", "in_sample_start",
        "in_sample_end", "out_of_sample_start", "out_of_sample_end", "paper_live_start",
        "paper_live_end", "number_of_assets_tested", "number_of_events", "number_of_trades",
        "gross_pnl", "net_pnl", "winrate", "profit_factor", "sharpe", "sortino",
        "max_drawdown", "candidate_trial_count", "global_trial_count", "adjusted_p_value",
        "wrc_p_value", "spa_p_value", "fit_scope", "score_input_scope",
        "event_ledger_hash", "nested_discovery_replay_status",
        "nested_discovery_replay_implemented", "nested_discovery_replay_passed",
        "edge_claim", "drift_status", "active_blockers", "registry_path",
        "registry_hash", "registry_previous_hash", "registry_run_manifest_hash",
        "registry_hash_chain_valid", "notes",
    ],
    "metrics_by_pattern.csv": [
        "pattern_id", "sample_count", "independent_sample_count", "trade_count", "ticker_count",
        "sector_count", "first_seen", "last_seen", "gross_pnl", "net_pnl", "avg_trade",
        "median_trade", "std_trade", "winrate", "avg_win", "avg_loss", "payoff_ratio",
        "profit_factor", "expectancy", "max_drawdown", "max_consecutive_losses", "best_trade",
        "worst_trade", "top_5_trades_pnl", "bottom_5_trades_pnl", "pnl_without_best_trade",
        "pnl_without_top_5_trades", "pnl_without_worst_trade", "sharpe", "sortino", "calmar",
        "avg_holding_period_seconds", "notes",
    ],
    "metrics_by_ticker.csv": [
        "pattern_id", "ticker", "trade_count", "event_count", "net_pnl", "winrate",
        "profit_factor", "avg_trade", "max_drawdown", "first_seen", "last_seen", "notes",
    ],
    "metrics_by_period.csv": [
        "period_start", "period_end", "period_type", "pattern_id", "event_count", "trade_count",
        "gross_pnl", "net_pnl", "winrate", "profit_factor", "max_drawdown", "market_regime", "notes",
    ],
    "metrics_by_regime.csv": [
        "pattern_id", "market_regime", "analysis_available", "empty_reason", "trade_count",
        "event_count", "gross_pnl", "net_pnl", "avg_trade", "expectancy_r", "winrate",
        "profit_factor", "max_drawdown", "best_trade", "worst_trade", "first_seen",
        "last_seen", "notes",
    ],
    "metrics_by_entry_variant.csv": [
        "pattern_id", "entry_variant_id", "analysis_available", "empty_reason", "trade_count",
        "event_count", "gross_pnl", "net_pnl", "avg_trade", "expectancy_r", "winrate",
        "profit_factor", "max_drawdown", "best_trade", "worst_trade", "first_seen",
        "last_seen", "notes",
    ],
}

TIMESTAMP_COLUMNS = {
    "pattern_catalog.csv": ["created_at", "first_seen", "last_seen"],
    "pattern_events.csv": [
        "detected_at", "market_timestamp", "bar_open_time", "bar_close_time",
        "available_data_cutoff_ts", "decision_ts", "entry_eligible_ts", "label_generated_ts",
    ],
    "paper_trades.csv": [
        "entry_signal_time", "entry_order_time", "entry_fill_time", "exit_signal_time",
        "exit_order_time", "exit_fill_time",
    ],
    "ib_fills.csv": ["ib_execution_time"],
    "experiment_registry.csv": [
        "created_at", "tested_at", "dataset_start", "dataset_end", "in_sample_start",
        "in_sample_end", "out_of_sample_start", "out_of_sample_end", "paper_live_start", "paper_live_end",
    ],
    "metrics_by_pattern.csv": ["first_seen", "last_seen"],
    "metrics_by_ticker.csv": ["first_seen", "last_seen"],
    "metrics_by_period.csv": ["period_start", "period_end"],
    "metrics_by_regime.csv": ["first_seen", "last_seen"],
    "metrics_by_entry_variant.csv": ["first_seen", "last_seen"],
}

ACCOUNT_RE = re.compile(r"\b(?:DU|DUN|U|F)\d{5,}\b")
TZ_RE = re.compile(r"(?:Z|[+-]\d\d:\d\d)$")
SENSITIVE_KEY_RE = re.compile(
    r"(^|_)(token|secret|password|apikey|api_key|credential|session_id|cookie)(_|$)",
    re.I,
)
LABEL_CONTRACT_SENTINELS = {
    "pending_forward_label",
    "not_recorded_legacy_label",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    package = args.package
    errors, csv_rows = validate_package(package)
    status = validation_report(package, errors, csv_rows)

    if errors:
        print("AUDIT PACKAGE INVALID")
        for error in errors:
            print(f"- {error}")
        print(json.dumps(status, indent=2))
        return 1
    print("AUDIT PACKAGE OK")
    print(json.dumps(status, indent=2))
    return 0


def validate_package(package: Path) -> tuple[list[str], dict[str, list[dict[str, str]]]]:
    errors: list[str] = []
    bridge_root = package.parent.parent

    for rel in REQUIRED_BRIDGE_FILES:
        if not (bridge_root / rel).exists():
            errors.append(f"missing required bridge file: {rel}")

    for rel in REQUIRED_FILES:
        if not (package / rel).exists():
            errors.append(f"missing required file: {rel}")

    manifest = load_json(package / "manifest.json", errors)
    director_gate = load_json(package / "director_gate_result.json", errors)
    if manifest:
        check_manifest(package, manifest, errors)
    if director_gate:
        check_director_gate_result(director_gate, errors)

    csv_rows: dict[str, list[dict[str, str]]] = {}
    for rel, expected_columns in CSV_COLUMNS.items():
        path = package / rel
        if not path.exists():
            continue
        rows, columns = read_csv(path, errors)
        csv_rows[rel] = rows
        missing = [column for column in expected_columns if column not in columns]
        if missing:
            errors.append(f"{rel}: missing columns: {', '.join(missing)}")
        check_timestamps(rel, rows, errors)

    check_sensitive_values(package, errors)
    check_references(csv_rows, errors)
    check_evidence_contract(csv_rows, errors)
    check_experiment_contract(csv_rows, errors)
    check_pnl(csv_rows.get("paper_trades.csv", []), errors)
    check_manifest_counts(manifest, csv_rows, errors)
    check_duplicate_reporting(manifest, csv_rows.get("pattern_events.csv", []), errors)
    check_metric_coherence(csv_rows, errors)
    check_bucket_breakdowns(csv_rows, errors)
    return errors, csv_rows


def validation_report(
    package: Path,
    errors: list[str],
    csv_rows: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    director_gate = load_json_silent(package / "director_gate_result.json")
    director_gate_status = director_gate_status_value(director_gate)
    schema_valid = not errors
    gate_allows_promotion = director_gate_promotion_allowed(director_gate, director_gate_status)
    return {
        "schema_valid": schema_valid,
        "package_valid": schema_valid,
        "director_gate_status": director_gate_status,
        "promotion_allowed": bool(schema_valid and gate_allows_promotion),
        "patterns": len(csv_rows.get("pattern_catalog.csv", [])),
        "events": len(csv_rows.get("pattern_events.csv", [])),
        "paper_trades": len(csv_rows.get("paper_trades.csv", [])),
        "fills": len(csv_rows.get("ib_fills.csv", [])),
        "experiments": len(csv_rows.get("experiment_registry.csv", [])),
        "error_count": len(errors),
    }


def load_json_silent(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def director_gate_status_value(result: Any) -> str:
    if not isinstance(result, dict):
        return "missing"
    status = str(result.get("director_gate_status") or result.get("status") or "").strip().lower()
    if status:
        return status
    summary = result.get("summary")
    if isinstance(summary, dict):
        return (
            str(summary.get("director_gate_status") or summary.get("director_gate") or "")
            .strip()
            .lower()
            or "missing"
        )
    return "missing"


def director_gate_promotion_allowed(result: Any, status: str) -> bool:
    if not isinstance(result, dict):
        return False
    if "promotion_allowed" in result:
        return bool(result.get("promotion_allowed"))
    summary = result.get("summary")
    if isinstance(summary, dict) and "promotion_allowed" in summary:
        return bool(summary.get("promotion_allowed"))
    return status == "passed"


def load_json(path: Path, errors: list[str]) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.name}: invalid JSON: {exc}")
        return None


def check_manifest(package: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    required_fields = [
        "audit_id",
        "created_at",
        "repo_commit",
        "repo_branch",
        "patterns_detected",
        "total_pattern_events",
        "total_paper_trades",
        "total_ib_fills",
        "total_experiment_variants",
        "duplicate_event_groups",
        "duplicate_repeated_rows",
        "metric_breakdowns",
        "files",
    ]
    for field in required_fields:
        if field not in manifest:
            errors.append(f"manifest.{field} is required")
    if manifest.get("contains_sensitive_data") is not False:
        errors.append("manifest.contains_sensitive_data must be false")
    if manifest.get("account_ids_redacted") is not True:
        errors.append("manifest.account_ids_redacted must be true")
    if manifest.get("orders_anonymized") is not True:
        errors.append("manifest.orders_anonymized must be true")
    if manifest.get("director_gate_required") is not True:
        errors.append("manifest.director_gate_required must be true")
    files = manifest.get("files")
    if not isinstance(files, list):
        errors.append("manifest.files must be a list")
        return
    listed_paths = {str(item.get("path", "")) for item in files if isinstance(item, dict)}
    required_manifest_paths = set(REQUIRED_FILES) - {"director_gate_result.json"}
    missing_listed = sorted(required_manifest_paths - listed_paths)
    if missing_listed:
        errors.append("manifest.files missing required paths: " + ", ".join(missing_listed))
    for rel in listed_paths:
        if rel and not (package / rel).exists():
            errors.append(f"manifest.files lists missing file: {rel}")


def check_director_gate_result(result: dict[str, Any], errors: list[str]) -> None:
    status = result.get("status")
    if status not in {"passed", "blocked", "invalid"}:
        errors.append("director_gate_result.json status must be passed, blocked or invalid")
    director_gate_status = result.get("director_gate_status")
    if director_gate_status is not None and director_gate_status != status:
        errors.append("director_gate_result.json director_gate_status must match status")
    if "schema_valid" in result and not isinstance(result.get("schema_valid"), bool):
        errors.append("director_gate_result.json schema_valid must be boolean when present")
    if "package_valid" in result and not isinstance(result.get("package_valid"), bool):
        errors.append("director_gate_result.json package_valid must be boolean when present")
    if "promotion_allowed" in result and not isinstance(result.get("promotion_allowed"), bool):
        errors.append("director_gate_result.json promotion_allowed must be boolean when present")
    if result.get("promotion_allowed") is True and status != "passed":
        errors.append("director_gate_result.json promotion_allowed cannot be true unless status is passed")
    summary = result.get("summary")
    if not isinstance(summary, dict):
        errors.append("director_gate_result.json summary must be an object")
        return
    if summary.get("director_gate") not in {"passed", "blocked", "invalid"}:
        errors.append("director_gate_result.json summary.director_gate must be present")
    if "promotion_allowed" in summary and not isinstance(summary.get("promotion_allowed"), bool):
        errors.append("director_gate_result.json summary.promotion_allowed must be boolean when present")
    for field in ("by_regime", "by_entry_variant"):
        value = summary.get(field)
        if not isinstance(value, dict):
            errors.append(f"director_gate_result.json summary.{field} must be present")
            continue
        available = value.get("available")
        buckets = value.get("buckets") if isinstance(value.get("buckets"), list) else []
        reason = str(value.get("empty_reason", "")).strip()
        if available is False and not reason:
            errors.append(f"director_gate_result.json summary.{field} is empty without empty_reason")
        if available is True and not buckets:
            errors.append(f"director_gate_result.json summary.{field} is available but has no buckets")


def read_csv(path: Path, errors: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            return list(reader), columns
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.name}: invalid CSV: {exc}")
        return [], []


def check_timestamps(rel: str, rows: list[dict[str, str]], errors: list[str]) -> None:
    for column in TIMESTAMP_COLUMNS.get(rel, []):
        for idx, row in enumerate(rows, start=2):
            value = (row.get(column) or "").strip()
            if not value:
                continue
            if rel == "pattern_events.csv" and column == "label_generated_ts" and value in LABEL_CONTRACT_SENTINELS:
                continue
            if not TZ_RE.search(value):
                errors.append(f"{rel}:{idx}: timestamp lacks timezone in {column}: {value}")


def check_sensitive_values(package: Path, errors: list[str]) -> None:
    for path in package.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ACCOUNT_RE.search(text):
            errors.append(f"{path.relative_to(package)}: apparent IB account id present")
        if path.suffix.lower() == ".json":
            try:
                scan_json(json.loads(text), str(path.relative_to(package)), errors)
            except json.JSONDecodeError:
                pass
        if path.suffix.lower() == ".csv":
            with path.open(newline="", encoding="utf-8") as handle:
                for row_num, row in enumerate(csv.DictReader(handle), start=2):
                    for key, value in row.items():
                        if SENSITIVE_KEY_RE.search(key or "") and value and value.upper() not in {"REDACTED", "REDACTED_OR_EMPTY"}:
                            errors.append(f"{path.relative_to(package)}:{row_num}: sensitive field {key} has non-redacted value")


def scan_json(value: Any, location: str, errors: list[str], prefix: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            full = f"{prefix}.{key}" if prefix else str(key)
            if SENSITIVE_KEY_RE.search(str(key)) and child not in ("", None, "REDACTED", "REDACTED_OR_EMPTY"):
                errors.append(f"{location}: sensitive field {full} has non-redacted value")
            scan_json(child, location, errors, full)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            scan_json(child, location, errors, f"{prefix}[{idx}]")


def check_references(csv_rows: dict[str, list[dict[str, str]]], errors: list[str]) -> None:
    pattern_ids = {row["pattern_id"] for row in csv_rows.get("pattern_catalog.csv", []) if row.get("pattern_id")}
    event_ids = {row["event_id"] for row in csv_rows.get("pattern_events.csv", []) if row.get("event_id")}
    trade_ids = {row["trade_id"] for row in csv_rows.get("paper_trades.csv", []) if row.get("trade_id")}
    for rel in ["pattern_events.csv", "paper_trades.csv", "experiment_registry.csv", "metrics_by_pattern.csv", "metrics_by_ticker.csv"]:
        for idx, row in enumerate(csv_rows.get(rel, []), start=2):
            pid = row.get("pattern_id")
            if pid and pid not in pattern_ids:
                errors.append(f"{rel}:{idx}: unknown pattern_id {pid}")
    for idx, row in enumerate(csv_rows.get("paper_trades.csv", []), start=2):
        event_id = row.get("event_id")
        if event_id and event_id not in event_ids:
            errors.append(f"paper_trades.csv:{idx}: unknown event_id {event_id}")
    for idx, row in enumerate(csv_rows.get("ib_fills.csv", []), start=2):
        trade_id = row.get("trade_id")
        if trade_id and trade_id not in trade_ids:
            errors.append(f"ib_fills.csv:{idx}: unknown trade_id {trade_id}")
        if str(row.get("account_id_redacted", "")).strip().lower() != "true":
            errors.append(f"ib_fills.csv:{idx}: account_id_redacted must be true")
        order_id_hash = str(row.get("order_id_hash", "")).strip()
        if order_id_hash and order_id_hash.isdigit():
            errors.append(f"ib_fills.csv:{idx}: order_id_hash appears to contain raw numeric order id")


def check_evidence_contract(csv_rows: dict[str, list[dict[str, str]]], errors: list[str]) -> None:
    for idx, row in enumerate(csv_rows.get("paper_trades.csv", []), start=2):
        evidence_type = str(row.get("evidence_type", "")).strip()
        evidence_quality = str(row.get("evidence_quality", "")).strip()
        if evidence_type != "ibkr_paper_fill":
            errors.append(f"paper_trades.csv:{idx}: evidence_type must be ibkr_paper_fill")
        if evidence_quality not in {"standard", "normal"}:
            errors.append(f"paper_trades.csv:{idx}: evidence_quality must be standard")
        notes = str(row.get("notes", "")).lower()
        if "lab_shadow_observation" in notes or "near_miss" in notes or "no_ibkr_order" in notes:
            errors.append(f"paper_trades.csv:{idx}: shadow/no-broker evidence cannot be exported as paper trade")


def check_experiment_contract(csv_rows: dict[str, list[dict[str, str]]], errors: list[str]) -> None:
    required_fields = ("global_trial_count", "fit_scope", "score_input_scope")
    for idx, row in enumerate(csv_rows.get("experiment_registry.csv", []), start=2):
        for field in required_fields:
            if not str(row.get(field, "")).strip():
                errors.append(f"experiment_registry.csv:{idx}: {field} is required")


def check_pnl(rows: list[dict[str, str]], errors: list[str]) -> None:
    for idx, row in enumerate(rows, start=2):
        fields = ["gross_pnl", "commission", "estimated_spread_cost", "estimated_slippage", "other_fees", "net_pnl"]
        if not all((row.get(field) or "").strip() for field in fields):
            continue
        try:
            gross, commission, spread, slippage, fees, net = [Decimal(row[field]) for field in fields]
        except InvalidOperation:
            errors.append(f"paper_trades.csv:{idx}: invalid PnL decimal")
            continue
        expected = gross - commission - spread - slippage - fees
        if abs(expected - net) > Decimal("0.01"):
            errors.append(f"paper_trades.csv:{idx}: net_pnl formula mismatch expected {expected} got {net}")


def check_manifest_counts(
    manifest: Any,
    csv_rows: dict[str, list[dict[str, str]]],
    errors: list[str],
) -> None:
    if not isinstance(manifest, dict):
        return
    expected = {
        "patterns_detected": len(csv_rows.get("pattern_catalog.csv", [])),
        "total_pattern_events": len(csv_rows.get("pattern_events.csv", [])),
        "total_paper_trades": len(csv_rows.get("paper_trades.csv", [])),
        "total_ib_fills": len(csv_rows.get("ib_fills.csv", [])),
        "total_experiment_variants": len(csv_rows.get("experiment_registry.csv", [])),
        "total_metrics_by_regime_rows": len(csv_rows.get("metrics_by_regime.csv", [])),
        "total_metrics_by_entry_variant_rows": len(csv_rows.get("metrics_by_entry_variant.csv", [])),
    }
    for field, observed in expected.items():
        if field not in manifest:
            errors.append(f"manifest.{field} is required")
            continue
        if as_int(manifest.get(field)) != observed:
            errors.append(f"manifest.{field} mismatch expected {observed} got {manifest.get(field)}")


def check_duplicate_reporting(
    manifest: Any,
    event_rows: list[dict[str, str]],
    errors: list[str],
) -> None:
    if not isinstance(manifest, dict):
        return
    counts: dict[str, int] = {}
    for row in event_rows:
        group = str(row.get("duplicate_group_id", "")).strip()
        if group:
            counts[group] = counts.get(group, 0) + 1
    repeated_counts = [count for count in counts.values() if count > 1]
    duplicate_groups = len(repeated_counts)
    duplicate_repeated_rows = sum(repeated_counts)
    if as_int(manifest.get("duplicate_event_groups")) != duplicate_groups:
        errors.append(
            f"manifest.duplicate_event_groups mismatch expected {duplicate_groups} got {manifest.get('duplicate_event_groups')}"
        )
    if as_int(manifest.get("duplicate_repeated_rows")) != duplicate_repeated_rows:
        errors.append(
            f"manifest.duplicate_repeated_rows mismatch expected {duplicate_repeated_rows} got {manifest.get('duplicate_repeated_rows')}"
        )


def check_metric_coherence(csv_rows: dict[str, list[dict[str, str]]], errors: list[str]) -> None:
    trades_by_pattern: dict[str, list[dict[str, str]]] = {}
    for trade in csv_rows.get("paper_trades.csv", []):
        trades_by_pattern.setdefault(trade.get("pattern_id", ""), []).append(trade)
    for idx, row in enumerate(csv_rows.get("metrics_by_pattern.csv", []), start=2):
        pid = row.get("pattern_id", "")
        trades = trades_by_pattern.get(pid, [])
        trade_count = as_int(row.get("trade_count"))
        if trade_count != len(trades):
            errors.append(f"metrics_by_pattern.csv:{idx}: trade_count expected {len(trades)} got {trade_count}")
        if trade_count == 0:
            for field in ("avg_trade", "median_trade", "winrate", "profit_factor", "expectancy", "max_drawdown"):
                if str(row.get(field, "")).strip():
                    errors.append(f"metrics_by_pattern.csv:{idx}: {field} must be empty when trade_count is zero")
            continue
        gross = sum(decimal_or_zero(trade.get("gross_pnl")) for trade in trades)
        net = sum(decimal_or_zero(trade.get("net_pnl")) for trade in trades)
        if abs(gross - decimal_or_zero(row.get("gross_pnl"))) > Decimal("0.01"):
            errors.append(f"metrics_by_pattern.csv:{idx}: gross_pnl does not match paper_trades.csv")
        if abs(net - decimal_or_zero(row.get("net_pnl"))) > Decimal("0.01"):
            errors.append(f"metrics_by_pattern.csv:{idx}: net_pnl does not match paper_trades.csv")


def check_bucket_breakdowns(csv_rows: dict[str, list[dict[str, str]]], errors: list[str]) -> None:
    for rel, bucket_column in (
        ("metrics_by_regime.csv", "market_regime"),
        ("metrics_by_entry_variant.csv", "entry_variant_id"),
    ):
        rows = csv_rows.get(rel, [])
        if not rows:
            errors.append(f"{rel}: must contain bucket rows or one explicit empty_reason row")
            continue
        available_rows = [row for row in rows if truthy(row.get("analysis_available"))]
        if not available_rows:
            if not any(str(row.get("empty_reason", "")).strip() for row in rows):
                errors.append(f"{rel}: empty breakdown requires non-empty empty_reason")
            continue
        for idx, row in enumerate(rows, start=2):
            if not truthy(row.get("analysis_available")):
                continue
            if not str(row.get(bucket_column, "")).strip():
                errors.append(f"{rel}:{idx}: {bucket_column} is required when analysis_available=true")
            if as_int(row.get("trade_count")) <= 0:
                errors.append(f"{rel}:{idx}: trade_count must be positive when analysis_available=true")


def as_int(value: Any) -> int:
    try:
        text = str(value or "").strip()
        return int(float(text)) if text else 0
    except (TypeError, ValueError):
        return 0


def decimal_or_zero(value: Any) -> Decimal:
    try:
        text = str(value or "").strip()
        return Decimal(text) if text else Decimal("0")
    except InvalidOperation:
        return Decimal("0")


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


if __name__ == "__main__":
    sys.exit(main())
