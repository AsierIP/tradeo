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
        "is_independent_sample", "data_available_at_signal", "features_used_json", "notes",
    ],
    "paper_trades.csv": [
        "trade_id", "event_id", "pattern_id", "ticker", "side", "quantity", "entry_signal_time",
        "entry_order_time", "entry_fill_time", "entry_signal_price", "entry_order_type",
        "entry_limit_price", "entry_fill_price", "exit_signal_time", "exit_order_time",
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
        "max_drawdown", "notes",
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
}

TIMESTAMP_COLUMNS = {
    "pattern_catalog.csv": ["created_at", "first_seen", "last_seen"],
    "pattern_events.csv": ["detected_at", "market_timestamp", "bar_open_time", "bar_close_time"],
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
}

ACCOUNT_RE = re.compile(r"\b(?:DU|DUN|U|F)\d{5,}\b")
TZ_RE = re.compile(r"(?:Z|[+-]\d\d:\d\d)$")
SENSITIVE_KEY_RE = re.compile(
    r"(^|_)(token|secret|password|apikey|api_key|credential|session_id|cookie)(_|$)",
    re.I,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    package = args.package
    errors: list[str] = []
    bridge_root = package.parent.parent

    for rel in REQUIRED_BRIDGE_FILES:
        if not (bridge_root / rel).exists():
            errors.append(f"missing required bridge file: {rel}")

    for rel in REQUIRED_FILES:
        if not (package / rel).exists():
            errors.append(f"missing required file: {rel}")

    manifest = load_json(package / "manifest.json", errors)
    if manifest:
        if manifest.get("contains_sensitive_data") is not False:
            errors.append("manifest.contains_sensitive_data must be false")
        if manifest.get("account_ids_redacted") is not True:
            errors.append("manifest.account_ids_redacted must be true")

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
    check_pnl(csv_rows.get("paper_trades.csv", []), errors)

    if errors:
        print("AUDIT PACKAGE INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print("AUDIT PACKAGE OK")
    print(json.dumps({
        "patterns": len(csv_rows.get("pattern_catalog.csv", [])),
        "events": len(csv_rows.get("pattern_events.csv", [])),
        "paper_trades": len(csv_rows.get("paper_trades.csv", [])),
        "fills": len(csv_rows.get("ib_fills.csv", [])),
        "experiments": len(csv_rows.get("experiment_registry.csv", [])),
    }, indent=2))
    return 0


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.name}: invalid JSON: {exc}")
        return None


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


if __name__ == "__main__":
    sys.exit(main())
