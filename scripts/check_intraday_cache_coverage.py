#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tradeo.core.config import get_settings
from tradeo.services.data_provider import pick_symbols, universe_file_for_interval


def main() -> int:
    parser = argparse.ArgumentParser(description="Check exact OHLCV cache coverage before intraday scouting.")
    parser.add_argument("--period", required=True)
    parser.add_argument("--timeframes", required=True, help="Comma-separated timeframes, e.g. 30m or 15m,5m")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--min-coverage", type=float, default=0.90)
    parser.add_argument("--min-rows", type=int, default=1)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    timeframes = [item.strip() for item in args.timeframes.split(",") if item.strip()]
    limit = int(args.limit or settings.intraday_research_limit_default)
    rows = []
    for timeframe in timeframes:
        symbols = pick_symbols(
            limit=limit,
            interval=timeframe,
            universe_file=universe_file_for_interval(settings, timeframe),
        )
        for symbol in symbols:
            rows.append(check_one(settings.market_data_cache_path, symbol, timeframe, args.period, args.min_rows))

    ok_count = sum(1 for row in rows if row["ok"])
    total = len(rows)
    coverage = ok_count / max(total, 1)
    missing = [row for row in rows if not row["ok"]]
    report = {
        "period": args.period,
        "timeframes": timeframes,
        "limit": limit,
        "cache_dir": str(settings.market_data_cache_path),
        "total": total,
        "ok": ok_count,
        "missing_or_bad": len(missing),
        "coverage": round(coverage, 6),
        "min_coverage": float(args.min_coverage),
        "ready_for_cache_only_scouting": coverage >= float(args.min_coverage),
        "missing_preview": missing[:25],
    }
    if not args.json_only:
        print(
            f"coverage={report['coverage']:.2%} ok={ok_count}/{total} "
            f"period={args.period} timeframes={','.join(timeframes)} cache={settings.market_data_cache_path}"
        )
        if missing:
            print("missing_or_bad preview:")
            for row in missing[:25]:
                print(f"- {row['symbol']} {row['timeframe']} {row['reason']} {row['path']}")
        print("JSON:")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready_for_cache_only_scouting"] else 2


def check_one(cache_dir: Path, symbol: str, timeframe: str, period: str, min_rows: int) -> dict[str, Any]:
    path = cache_path(cache_dir, symbol, timeframe, period)
    meta_path = path.with_suffix(".metadata.json")
    row = {"symbol": symbol, "timeframe": timeframe, "period": period, "path": str(path), "ok": False, "reason": ""}
    if not path.exists():
        row["reason"] = "csv_missing"
        return row
    if not meta_path.exists():
        row["reason"] = "metadata_missing"
        return row
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        row["reason"] = "metadata_invalid_json"
        return row
    if str(meta.get("symbol") or "").upper() != symbol.upper():
        row["reason"] = "metadata_symbol_mismatch"
        return row
    if str(meta.get("period") or "") != str(period):
        row["reason"] = "metadata_period_mismatch"
        return row
    if str(meta.get("interval") or "") != str(timeframe):
        row["reason"] = "metadata_interval_mismatch"
        return row
    rows = int(meta.get("rows") or 0)
    row["rows"] = rows
    if rows < int(min_rows):
        row["reason"] = "rows_below_min"
        return row
    row["ok"] = True
    row["reason"] = "ok"
    row["last_timestamp"] = str(meta.get("last_timestamp") or "")
    return row


def cache_path(cache_dir: Path, symbol: str, timeframe: str, period: str) -> Path:
    safe = "_".join(safe_part(part) for part in (symbol.upper(), timeframe, period))
    return cache_dir / f"{safe}.csv"


def safe_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "."} else "_" for ch in value).strip("._")


if __name__ == "__main__":
    raise SystemExit(main())
