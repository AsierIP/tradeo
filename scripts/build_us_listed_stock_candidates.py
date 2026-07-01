#!/usr/bin/env python3
"""Build a broad official US listed stock candidate file from Nasdaq Trader.

The output is only a candidate seed for the intraday universe builder. It does
not submit orders, alter gates, or mark any symbol as research-ready.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Iterable
from urllib.request import urlopen

DEFAULT_NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
DEFAULT_OTHERLISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

EXCLUDED_NAME_TERMS = (
    "warrant",
    "warrants",
    "unit",
    "units",
    "right",
    "rights",
    "preferred",
    "preference",
    "note",
    "notes",
    "bond",
    "debenture",
    "redeemable",
    "acquisition right",
    "etf",
    "etn",
    "fund",
    "trust",
)
NASDAQ_EXTRA_EXCLUDED_TERMS = ("nextshares",)
ADR_TERMS = (
    "american depositary shares",
    "american depositary share",
    "american depository shares",
    "american depository share",
)
COMMON_STOCK_TERMS = (
    "common stock",
    "class a common stock",
    "class b common stock",
    "class c common stock",
)
ORDINARY_SHARE_TERMS = ("ordinary shares", "ordinary share")
COMMON_SHARE_TERMS = ("common shares", "common share")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nasdaq-url", default=DEFAULT_NASDAQ_URL)
    parser.add_argument("--otherlisted-url", default=DEFAULT_OTHERLISTED_URL)
    parser.add_argument("--output", default="artifacts/runtime/us_listed_stock_candidates.csv")
    parser.add_argument("--include-adrs", dest="include_adrs", action="store_true", default=True)
    parser.add_argument("--no-include-adrs", dest="include_adrs", action="store_false")
    parser.add_argument("--max-symbols", type=int, default=None)
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    result = build_candidates(
        nasdaq_source=args.nasdaq_url,
        otherlisted_source=args.otherlisted_url,
        include_adrs=args.include_adrs,
        max_symbols=args.max_symbols,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_candidates(output, result["rows"])
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nasdaq_source": args.nasdaq_url,
        "otherlisted_source": args.otherlisted_url,
        "raw_nasdaq_rows": result["raw_nasdaq_rows"],
        "raw_otherlisted_rows": result["raw_otherlisted_rows"],
        "output_rows": len(result["rows"]),
        "excluded_counts": dict(sorted(result["excluded_counts"].items())),
        "candidate_type_counts": dict(sorted(Counter(row["candidate_type"] for row in result["rows"]).items())),
    }
    metadata_path = output.with_suffix(".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    if not args.json_only:
        print(f"us listed candidates={len(result['rows'])} output={output}")
        print("JSON:")
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0 if result["rows"] else 2


def build_candidates(
    *,
    nasdaq_source: str,
    otherlisted_source: str,
    include_adrs: bool = True,
    max_symbols: int | None = None,
) -> dict[str, object]:
    excluded_counts: Counter[str] = Counter()
    rows: list[dict[str, object]] = []
    seen_symbols: set[str] = set()

    nasdaq_rows = read_symbol_directory(nasdaq_source)
    otherlisted_rows = read_symbol_directory(otherlisted_source)

    for raw in nasdaq_rows:
        candidate = candidate_from_nasdaq_row(raw, include_adrs=include_adrs, excluded_counts=excluded_counts)
        if candidate is None:
            continue
        if candidate["symbol"] in seen_symbols:
            excluded_counts["duplicate_symbol"] += 1
            continue
        rows.append(candidate)
        seen_symbols.add(str(candidate["symbol"]))
        if max_symbols is not None and len(rows) >= max_symbols:
            break

    if max_symbols is None or len(rows) < max_symbols:
        for raw in otherlisted_rows:
            candidate = candidate_from_otherlisted_row(raw, include_adrs=include_adrs, excluded_counts=excluded_counts)
            if candidate is None:
                continue
            if candidate["symbol"] in seen_symbols:
                excluded_counts["duplicate_symbol"] += 1
                continue
            rows.append(candidate)
            seen_symbols.add(str(candidate["symbol"]))
            if max_symbols is not None and len(rows) >= max_symbols:
                break

    return {
        "rows": rows,
        "raw_nasdaq_rows": len(nasdaq_rows),
        "raw_otherlisted_rows": len(otherlisted_rows),
        "excluded_counts": excluded_counts,
    }


def read_symbol_directory(source: str) -> list[dict[str, str]]:
    text = read_text_source(source)
    lines = [line for line in text.splitlines() if line and not line.startswith("File Creation Time:")]
    if not lines:
        return []
    reader = csv.DictReader(lines, delimiter="|")
    return [{str(k): str(v or "") for k, v in row.items() if k is not None} for row in reader]


def read_text_source(source: str) -> str:
    path = Path(source)
    if path.exists():
        return path.read_text(encoding="utf-8")
    with urlopen(source, timeout=30) as response:  # noqa: S310 - official user-provided market-data URLs.
        return response.read().decode("utf-8")


def candidate_from_nasdaq_row(
    raw: dict[str, str],
    *,
    include_adrs: bool,
    excluded_counts: Counter[str],
) -> dict[str, object] | None:
    symbol = normalize_symbol(raw.get("Symbol", ""))
    name = normalize_space(raw.get("Security Name", ""))
    if not symbol:
        excluded_counts["missing_symbol"] += 1
        return None
    if is_yes(raw.get("ETF")):
        excluded_counts["nasdaq_etf"] += 1
        return None
    if is_yes(raw.get("Test Issue")):
        excluded_counts["nasdaq_test_issue"] += 1
        return None
    if is_yes(raw.get("NextShares")):
        excluded_counts["nasdaq_nextshares"] += 1
        return None
    if has_excluded_text(symbol, name, NASDAQ_EXTRA_EXCLUDED_TERMS):
        excluded_counts["nasdaq_excluded_text"] += 1
        return None
    return make_candidate(
        symbol=symbol,
        name=name,
        exchange="NASDAQ",
        source="nasdaqlisted",
        raw_symbol=raw.get("Symbol", ""),
        raw_security_name=raw.get("Security Name", ""),
        is_etf=is_yes(raw.get("ETF")),
        is_test_issue=is_yes(raw.get("Test Issue")),
        include_adrs=include_adrs,
        excluded_counts=excluded_counts,
    )


def candidate_from_otherlisted_row(
    raw: dict[str, str],
    *,
    include_adrs: bool,
    excluded_counts: Counter[str],
) -> dict[str, object] | None:
    symbol = normalize_symbol(raw.get("ACT Symbol", ""))
    name = normalize_space(raw.get("Security Name", ""))
    if not symbol:
        excluded_counts["missing_symbol"] += 1
        return None
    if is_yes(raw.get("ETF")):
        excluded_counts["otherlisted_etf"] += 1
        return None
    if is_yes(raw.get("Test Issue")):
        excluded_counts["otherlisted_test_issue"] += 1
        return None
    if has_excluded_text(symbol, name):
        excluded_counts["otherlisted_excluded_text"] += 1
        return None
    return make_candidate(
        symbol=symbol,
        name=name,
        exchange=normalize_exchange(raw.get("Exchange", "")),
        source="otherlisted",
        raw_symbol=raw.get("ACT Symbol", ""),
        raw_security_name=raw.get("Security Name", ""),
        is_etf=is_yes(raw.get("ETF")),
        is_test_issue=is_yes(raw.get("Test Issue")),
        include_adrs=include_adrs,
        excluded_counts=excluded_counts,
    )


def make_candidate(
    *,
    symbol: str,
    name: str,
    exchange: str,
    source: str,
    raw_symbol: str,
    raw_security_name: str,
    is_etf: bool,
    is_test_issue: bool,
    include_adrs: bool,
    excluded_counts: Counter[str],
) -> dict[str, object] | None:
    candidate_type = classify_candidate_type(name)
    is_adr = candidate_type == "adr"
    if is_adr and not include_adrs:
        excluded_counts[f"{source}_adr_disabled"] += 1
        return None
    return {
        "symbol": symbol,
        "name": name,
        "exchange": exchange,
        "source": source,
        "candidate_type": candidate_type,
        "is_adr": is_adr,
        "is_etf": is_etf,
        "is_test_issue": is_test_issue,
        "raw_symbol": raw_symbol,
        "raw_security_name": raw_security_name,
        "note": "",
    }


def write_candidates(output: Path, rows: Iterable[dict[str, object]]) -> None:
    fieldnames = [
        "symbol",
        "name",
        "exchange",
        "source",
        "candidate_type",
        "is_adr",
        "is_etf",
        "is_test_issue",
        "raw_symbol",
        "raw_security_name",
        "note",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def classify_candidate_type(name: str) -> str:
    text = f" {normalize_space(name).lower()} "
    if any(term in text for term in ADR_TERMS) or has_adr_ticker_token(text):
        return "adr"
    if any(term in text for term in ORDINARY_SHARE_TERMS):
        return "ordinary_share"
    if any(term in text for term in COMMON_SHARE_TERMS):
        return "common_share"
    if any(term in text for term in COMMON_STOCK_TERMS):
        return "common_stock"
    return "unknown_equity"


def has_adr_ticker_token(text: str) -> bool:
    return bool(re.search(r"(?<![a-z])ad[rs](?![a-z-])", text))


def has_excluded_text(symbol: str, name: str, extra_terms: tuple[str, ...] = ()) -> bool:
    text = f" {normalize_space(symbol).lower()} {normalize_space(name).lower()} "
    terms = EXCLUDED_NAME_TERMS + extra_terms
    return any(re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", text) for term in terms)


def normalize_symbol(value: str) -> str:
    return normalize_space(value).upper()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_exchange(value: str) -> str:
    exchange = normalize_space(value).upper()
    return exchange or "UNKNOWN"


def is_yes(value: str | None) -> bool:
    return str(value or "").strip().upper() == "Y"


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.stderr.write("interrupted\n")
        raise SystemExit(130)
