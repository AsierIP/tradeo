from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
import csv
import json

from tradeo.modules.laboratory.vwap_shadow_recorder import (
    ShadowQuote,
    Side,
    build_vwap_shadow_record,
)

QuoteProvider = Callable[[str], ShadowQuote]


@dataclass(frozen=True, slots=True)
class ShadowBatchRequest:
    symbols: tuple[str, ...]
    side: Side
    vwap_condition: str
    timeframe: str
    market_open: bool | None = None


def load_symbols(*, symbols: str | None = None, universe_file: str | Path | None = None, limit: int | None = None) -> list[str]:
    loaded: list[str] = []
    if symbols:
        loaded.extend(part.strip().upper() for part in symbols.split(",") if part.strip())
    if universe_file:
        loaded.extend(_symbols_from_universe(Path(universe_file)))
    unique = list(dict.fromkeys(symbol for symbol in loaded if symbol))
    if limit is not None and limit > 0:
        return unique[:limit]
    return unique


def run_shadow_batch(
    request: ShadowBatchRequest,
    *,
    quote_provider: QuoteProvider | None = None,
    settings: Any | None = None,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    provider = quote_provider or _safe_unavailable_quote
    records: list[dict[str, Any]] = []
    generated_at = now or datetime.now(timezone.utc)
    for symbol in request.symbols:
        quote = provider(symbol)
        records.append(
            build_vwap_shadow_record(
                symbol=symbol,
                side=request.side,
                vwap_condition=request.vwap_condition,
                timeframe=request.timeframe,
                quote=quote,
                settings=settings,
                now=generated_at,
                market_open=request.market_open,
            )
        )
    return records, summarize_shadow_batch(records, request=request, generated_at=generated_at)


def summarize_shadow_batch(
    records: list[dict[str, Any]],
    *,
    request: ShadowBatchRequest,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    generated = generated_at or datetime.now(timezone.utc)
    decision_counts = Counter(str(record.get("decision")) for record in records)
    quote_counts = Counter(str(record.get("quote_status")) for record in records)
    forbidden = [
        record
        for record in records
        if record.get("order_submitted")
        or record.get("paper_order_submitted")
        or record.get("live_order_submitted")
        or record.get("submit_order_called")
        or record.get("orders_allowed")
        or record.get("live_allowed")
    ]
    return {
        "schema_version": "tradeo.lab_vwap_shadow_batch.v1",
        "generated_at": generated.isoformat(),
        "symbols": [record.get("symbol") for record in records],
        "requested_symbols": list(request.symbols),
        "side": request.side,
        "timeframe": request.timeframe,
        "vwap_condition": request.vwap_condition,
        "events": len(records),
        "decisions": dict(sorted(decision_counts.items())),
        "quote_status": dict(sorted(quote_counts.items())),
        "orders_allowed": False,
        "paper_allowed": False,
        "live_allowed": False,
        "submit_order_called": False,
        "paper_order_submitted": False,
        "live_order_submitted": False,
        "forbidden_outcomes": len(forbidden),
        "status": "blocked_safety" if forbidden else "ok",
    }


def write_shadow_batch_artifacts(
    records: list[dict[str, Any]],
    summary: dict[str, Any],
    *,
    jsonl_out: str | Path,
    summary_json: str | Path,
    summary_md: str | Path,
) -> None:
    jsonl_path = Path(jsonl_out)
    summary_json_path = Path(summary_json)
    summary_md_path = Path(summary_md)
    for path in (jsonl_path, summary_json_path, summary_md_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    summary_md_path.write_text(render_shadow_batch_markdown(summary), encoding="utf-8")


def render_shadow_batch_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# VWAP Lab Shadow Batch",
        "",
        f"- status: `{summary.get('status')}`",
        f"- events: `{summary.get('events')}`",
        f"- symbols: `{', '.join(str(item) for item in summary.get('symbols', []))}`",
        f"- side: `{summary.get('side')}`",
        f"- timeframe: `{summary.get('timeframe')}`",
        f"- vwap_condition: `{summary.get('vwap_condition')}`",
        f"- decisions: `{summary.get('decisions')}`",
        f"- quote_status: `{summary.get('quote_status')}`",
        f"- orders_allowed: `{summary.get('orders_allowed')}`",
        f"- paper_allowed: `{summary.get('paper_allowed')}`",
        f"- live_allowed: `{summary.get('live_allowed')}`",
        f"- submit_order_called: `{summary.get('submit_order_called')}`",
        "",
        "This batch runner appends read-only shadow events only. It does not import broker submission paths.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _symbols_from_universe(path: Path) -> list[str]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        if reader.fieldnames:
            symbol_key = _symbol_key(reader.fieldnames)
            if symbol_key is not None:
                return [str(row.get(symbol_key, "")).strip().upper() for row in reader if row.get(symbol_key)]
        handle.seek(0)
        raw_reader = csv.reader(handle, dialect=dialect)
        return [row[0].strip().upper() for row in raw_reader if row and row[0].strip()]


def _symbol_key(fieldnames: list[str]) -> str | None:
    normalized = {field.strip().lower(): field for field in fieldnames}
    for key in ("symbol", "ticker", "Symbol", "Ticker"):
        if key.lower() in normalized:
            return normalized[key.lower()]
    return fieldnames[0] if fieldnames else None


def _safe_unavailable_quote(symbol: str) -> ShadowQuote:
    return ShadowQuote(source=f"batch_safe_no_quote:{symbol.upper()}")
