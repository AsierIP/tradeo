from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from time import sleep
from typing import Any

import pandas as pd

from tradeo.core.config import get_settings
from tradeo.modules.daily_swing.paper_probe import last_valid_trading_day, repo_root, write_csv

DSS_003_SCHEMA_VERSION = "tradeo.daily_swing.dss_003.v1"
BENCHMARK_SYMBOLS = ("SPY", "QQQ")
FALLBACK_LIQUID_STOCKS = (
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "GOOGL",
    "GOOG",
    "AVGO",
    "TSLA",
    "COST",
    "NFLX",
    "AMD",
    "CRM",
    "ADBE",
    "ORCL",
    "NOW",
    "QCOM",
    "INTC",
    "TXN",
    "MU",
    "AMAT",
    "LRCX",
    "KLAC",
    "PANW",
    "CRWD",
    "SNOW",
    "SHOP",
    "UBER",
    "ABNB",
    "BKNG",
    "MELI",
    "PDD",
    "PYPL",
    "COIN",
    "HOOD",
    "JPM",
    "BAC",
    "WFC",
    "GS",
    "MS",
    "V",
    "MA",
    "AXP",
    "C",
    "SCHW",
    "BLK",
    "UNH",
    "LLY",
    "JNJ",
    "MRK",
    "ABBV",
    "TMO",
    "DHR",
    "ISRG",
    "VRTX",
    "REGN",
    "PFE",
    "AMGN",
    "GILD",
    "BSX",
    "MDT",
    "PG",
    "KO",
    "PEP",
    "WMT",
    "HD",
    "LOW",
    "MCD",
    "SBUX",
    "NKE",
    "TGT",
    "CMG",
    "CAVA",
    "DECK",
    "LULU",
    "XOM",
    "CVX",
    "COP",
    "SLB",
    "EOG",
    "LIN",
    "APD",
    "SHW",
    "CAT",
    "DE",
    "GE",
    "HON",
    "ETN",
    "EMR",
    "BA",
    "LMT",
    "RTX",
    "UPS",
    "FDX",
    "UNP",
    "CSX",
    "NEE",
    "DUK",
    "SO",
    "PLTR",
    "APP",
    "HIMS",
    "CROX",
    "WING",
    "FOUR",
    "MNDY",
    "CRDO",
    "NXT",
    "ZETA",
    "ENPH",
    "AAON",
    "CVLT",
    "FN",
    "TMDX",
    "BROS",
    "AX",
    "ALGM",
    "APPF",
    "CALM",
    "FRPT",
    "INSP",
    "LRN",
    "OLLI",
    "SKYW",
    "CME",
    "ADP",
    "CDNS",
    "SNPS",
    "ADI",
    "MRVL",
    "APH",
    "TTD",
    "DDOG",
    "TEAM",
    "ZS",
    "NET",
)
REQUIRED_BAR_COLUMNS = ("symbol", "date", "open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class CacheResult:
    status: str
    fetched: int
    skipped: int
    failed: int
    manifest_path: Path
    error: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _seed_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for source in (root / "data" / "universe_us_mid_caps.csv", root / "data" / "universe_us_small_caps.csv"):
        for row in read_rows(source):
            symbol = (row.get("symbol") or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            rows.append(
                {
                    "symbol": symbol,
                    "name": row.get("name", ""),
                    "source": str(source.relative_to(root)),
                    "source_rank": str(len(rows) + 1),
                    "cap_segment": row.get("cap_segment", ""),
                }
            )
    return rows


def build_daily_universes(repo: Path | None = None) -> dict[str, Path]:
    root = repo_root(repo)
    runtime_dir = root / "artifacts" / "runtime" / "daily_swing"
    research_dir = root / "research" / "daily_swing"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)

    seed = _seed_rows(root)
    by_symbol = {row["symbol"]: row for row in seed}
    for symbol in FALLBACK_LIQUID_STOCKS:
        by_symbol.setdefault(
            symbol,
            {
                "symbol": symbol,
                "name": "",
                "source": "fallback_liquid_stock_list",
                "source_rank": str(len(by_symbol) + 1),
                "cap_segment": "large_liquid_fallback",
            },
        )

    operational = [by_symbol[symbol] for symbol in by_symbol if symbol not in BENCHMARK_SYMBOLS]
    benchmarks = [
        {
            "symbol": symbol,
            "name": symbol,
            "source": "benchmark_required",
            "source_rank": "0",
            "cap_segment": "benchmark",
        }
        for symbol in BENCHMARK_SYMBOLS
    ]
    tiers = {"smoke": 10, "pilot": 50, "research": 150}
    paths: dict[str, Path] = {}
    fields = [
        "symbol",
        "name",
        "tier",
        "benchmark_only",
        "operational_eligible",
        "product_type",
        "security_type",
        "source",
        "source_rank",
        "cap_segment",
        "classification_status",
        "exclusion_reason",
    ]
    for tier, limit in tiers.items():
        rows: list[dict[str, Any]] = []
        for row in operational[:limit]:
            rows.append(
                {
                    **row,
                    "tier": tier,
                    "benchmark_only": False,
                    "operational_eligible": True,
                    "product_type": "STK",
                    "security_type": "stock",
                    "classification_status": "stock_only_seed_or_fallback",
                    "exclusion_reason": "",
                }
            )
        for row in benchmarks:
            rows.append(
                {
                    **row,
                    "tier": tier,
                    "benchmark_only": True,
                    "operational_eligible": False,
                    "product_type": "ETF",
                    "security_type": "benchmark_etf",
                    "classification_status": "benchmark_only",
                    "exclusion_reason": "benchmark_not_operational_symbol",
                }
            )
        path = runtime_dir / f"dss_003_universe_{tier}.csv"
        write_csv(path, rows, fields)
        paths[tier] = path

    (research_dir / "DSS_003_UNIVERSE.md").write_text(
        f"""# DSS-003 Universe

Built three Daily universes for cache warmup:

- smoke: 10 stocks + SPY/QQQ benchmark-only
- pilot: 50 stocks + SPY/QQQ benchmark-only
- research: {min(150, len(operational))} stocks + SPY/QQQ benchmark-only

Source priority:
1. Existing repo seed universes under `data/`.
2. Stable fallback liquid stock list, used only to make the pilot/research cache warmup broad enough.

Operational rows are `product_type=STK` and `operational_eligible=true`. SPY and QQQ are present only as regime benchmarks and are not eligible operational symbols.
""",
        encoding="utf-8",
    )
    return paths


def _load_universe(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    rows = read_rows(path)
    if limit is not None:
        return rows[:limit]
    return rows


def cache_daily_ohlcv(
    *,
    universe_path: Path,
    out_dir: Path,
    duration: str,
    end_date: str,
    source: str = "ibkr",
    read_only: bool = False,
    limit: int | None = None,
    resume: bool = False,
    sleep_seconds: float = 0.0,
    dry_run: bool = False,
    force: bool = False,
) -> CacheResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir.parent / "dss_003_daily_cache_manifest.json"
    rows = _load_universe(universe_path, limit=limit)
    manifest: dict[str, Any] = {
        "schema_version": DSS_003_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "source": source,
        "universe": str(universe_path),
        "out_dir": str(out_dir),
        "duration": duration,
        "end_date": end_date,
        "read_only": read_only,
        "dry_run": dry_run,
        "adjusted": source == "ibkr",
        "symbols": [],
    }
    if not read_only:
        manifest["status"] = "BLOCKED_READ_ONLY_REQUIRED"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return CacheResult("BLOCKED_READ_ONLY_REQUIRED", 0, 0, len(rows), manifest_path)
    if source != "ibkr":
        manifest["status"] = "BLOCKED_UNSUPPORTED_SOURCE"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return CacheResult("BLOCKED_UNSUPPORTED_SOURCE", 0, 0, len(rows), manifest_path)

    settings = get_settings()
    if not settings.ibkr_readonly:
        manifest["status"] = "BLOCKED_SETTINGS_NOT_READ_ONLY"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return CacheResult("BLOCKED_SETTINGS_NOT_READ_ONLY", 0, 0, len(rows), manifest_path)

    provider = None
    if not dry_run:
        from tradeo.services.ibkr_data_provider import IBKRHistoricalDataProvider

        provider = IBKRHistoricalDataProvider(settings=settings)

    fetched = skipped = failed = 0
    first_error: str | None = None
    for row in rows:
        symbol = (row.get("symbol") or "").upper().strip()
        if not symbol:
            continue
        output_path = out_dir / f"{symbol}.csv"
        symbol_record: dict[str, Any] = {
            "symbol": symbol,
            "benchmark_only": _truthy(row.get("benchmark_only")),
            "path": str(output_path),
            "status": "DRY_RUN" if dry_run else "PENDING",
        }
        if output_path.exists() and resume and not force:
            skipped += 1
            symbol_record["status"] = "SKIPPED_EXISTS"
            manifest["symbols"].append(symbol_record)
            continue
        if dry_run:
            skipped += 1
            manifest["symbols"].append(symbol_record)
            continue
        try:
            assert provider is not None
            df = provider.fetch_ohlcv(symbol, period=duration.lower().replace(" ", ""), interval="1d")
            normalized = bars_to_cache_frame(df, symbol=symbol, source=source)
            normalized.to_csv(output_path, index=False)
            fetched += 1
            symbol_record.update(
                {
                    "status": "FETCHED",
                    "rows": int(len(normalized)),
                    "first_date": normalized["date"].min() if not normalized.empty else None,
                    "last_date": normalized["date"].max() if not normalized.empty else None,
                }
            )
        except Exception as exc:  # noqa: BLE001 - provider exposes heterogeneous IBKR/runtime failures.
            failed += 1
            first_error = first_error or str(exc)
            symbol_record.update({"status": "FETCH_FAILED", "error": str(exc)})
            if not resume:
                manifest["symbols"].append(symbol_record)
                break
        manifest["symbols"].append(symbol_record)
        if sleep_seconds > 0:
            sleep(sleep_seconds)

    if failed:
        status = "BLOCKED_IBKR_READONLY" if first_error else "FETCH_FAILED"
    elif dry_run:
        status = "DRY_RUN_OK"
    else:
        status = "CACHE_WRITTEN"
    manifest["status"] = status
    manifest["fetched"] = fetched
    manifest["skipped"] = skipped
    manifest["failed"] = failed
    manifest["error"] = first_error
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return CacheResult(status, fetched, skipped, failed, manifest_path, first_error)


def bars_to_cache_frame(df: pd.DataFrame, *, symbol: str, source: str) -> pd.DataFrame:
    out = df.copy()
    if "date" not in out.columns:
        out = out.reset_index(names="date")
    out["date"] = pd.to_datetime(out["date"]).dt.date.astype(str)
    out["symbol"] = symbol.upper()
    out["source"] = source
    out["currency"] = "USD"
    out["exchange"] = "SMART"
    out["bar_status"] = "VALID"
    out["retrieved_at"] = utc_now()
    out["adjusted"] = source == "ibkr"
    columns = [
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "currency",
        "exchange",
        "bar_status",
        "retrieved_at",
        "adjusted",
    ]
    return out[columns].sort_values(["symbol", "date"]).reset_index(drop=True)


def check_daily_ohlcv_quality(
    *,
    cache_dir: Path,
    universe_path: Path,
    end_date: str,
    report_csv: Path,
    summary_json: Path,
    min_operational_ready: int = 50,
) -> dict[str, Any]:
    rows = read_rows(universe_path)
    expected_last = last_valid_trading_day(date.fromisoformat(end_date)).isoformat()
    quality_rows: list[dict[str, Any]] = []
    false_holiday_bar = False
    operational_ready = 0
    benchmark_ready = 0
    for row in rows:
        symbol = (row.get("symbol") or "").upper().strip()
        benchmark_only = _truthy(row.get("benchmark_only"))
        path = cache_dir / f"{symbol}.csv"
        status = "FETCH_FAILED"
        reason = "cache file missing"
        bars = 0
        first_date = ""
        last_date = ""
        if path.exists():
            try:
                df = pd.read_csv(path)
                status, reason = classify_symbol_quality(df, expected_last_date=expected_last)
                bars = int(len(df))
                if "date" in df.columns and not df.empty:
                    dates = pd.to_datetime(df["date"], errors="coerce").dt.date.astype(str)
                    first_date = str(dates.min())
                    last_date = str(dates.max())
                    false_holiday_bar = false_holiday_bar or bool((dates == "2026-07-03").any())
            except Exception as exc:  # noqa: BLE001 - keep gate report complete.
                status = "QUALITY_READ_FAILED"
                reason = str(exc)
        if status == "DATA_READY" and benchmark_only:
            benchmark_ready += 1
        if status == "DATA_READY" and not benchmark_only:
            operational_ready += 1
        quality_rows.append(
            {
                "symbol": symbol,
                "benchmark_only": benchmark_only,
                "status": status,
                "reason": reason,
                "bars": bars,
                "first_date": first_date,
                "last_date": last_date,
                "expected_last_valid_bar_date": expected_last,
                "path": str(path),
            }
        )

    report_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    write_csv(
        report_csv,
        quality_rows,
        [
            "symbol",
            "benchmark_only",
            "status",
            "reason",
            "bars",
            "first_date",
            "last_date",
            "expected_last_valid_bar_date",
            "path",
        ],
    )
    data_gate = (
        "PASS"
        if operational_ready >= min_operational_ready and benchmark_ready >= 2 and not false_holiday_bar
        else "BLOCKED"
    )
    summary = {
        "schema_version": DSS_003_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "data_gate": data_gate,
        "operational_ready": operational_ready,
        "benchmark_ready": benchmark_ready,
        "min_operational_ready": min_operational_ready,
        "false_bar_2026_07_03_present": false_holiday_bar,
        "last_valid_bar_date": expected_last,
        "report_csv": str(report_csv),
    }
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def classify_symbol_quality(df: pd.DataFrame, *, expected_last_date: str) -> tuple[str, str]:
    missing = [column for column in REQUIRED_BAR_COLUMNS if column not in df.columns]
    if missing:
        return "MISSING_COLUMNS", f"missing columns: {missing}"
    if df.empty:
        return "TOO_SHORT", "no bars"
    if df["date"].duplicated().any():
        return "DUPLICATE_DATES", "duplicate dates"
    dates = pd.to_datetime(df["date"], errors="coerce")
    if dates.isna().any():
        return "INVALID_DATE", "unparseable date"
    date_strings = dates.dt.date.astype(str)
    if (date_strings == "2026-07-03").any():
        return "HOLIDAY_BAR_ERROR", "contains 2026-07-03 USA holiday bar"
    if date_strings.max() != expected_last_date:
        return "TOO_SHORT", f"last bar {date_strings.max()} != expected {expected_last_date}"
    numeric = df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any():
        return "NAN_CRITICAL", "critical NaN/non-numeric OHLCV"
    if (numeric["volume"] < 0).any():
        return "INVALID_OHLC", "negative volume"
    if (numeric["high"] < numeric[["open", "close", "low"]].max(axis=1)).any():
        return "INVALID_OHLC", "high below open/close/low"
    if (numeric["low"] > numeric[["open", "close", "high"]].min(axis=1)).any():
        return "INVALID_OHLC", "low above open/close/high"
    if len(df) < 252:
        return "TOO_SHORT", "less than 252 daily bars"
    return "DATA_READY", "ok"


def write_dss_003_reports(repo: Path | None, cache_result: CacheResult, quality_summary: dict[str, Any]) -> dict[str, Any]:
    root = repo_root(repo)
    research_dir = root / "research" / "daily_swing"
    runtime_dir = root / "artifacts" / "runtime" / "daily_swing"
    research_dir.mkdir(parents=True, exist_ok=True)
    decision = (
        "DAILY_CACHE_READY_FOR_BACKTEST"
        if quality_summary.get("data_gate") == "PASS"
        else ("BLOCKED_IBKR_READONLY" if cache_result.status == "BLOCKED_IBKR_READONLY" else "BLOCKED_QUALITY")
    )
    decision_doc = {
        "schema_version": DSS_003_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "decision": decision,
        "cache_status": cache_result.status,
        "data_gate": quality_summary.get("data_gate"),
        "operational_ready": quality_summary.get("operational_ready"),
        "benchmark_ready": quality_summary.get("benchmark_ready"),
        "false_bar_2026_07_03_present": quality_summary.get("false_bar_2026_07_03_present"),
        "last_valid_bar_date": quality_summary.get("last_valid_bar_date"),
        "orders_allowed": False,
        "live_allowed": False,
        "next_phase": "DSS-004 backtest DSS-PB-001" if decision == "DAILY_CACHE_READY_FOR_BACKTEST" else "resolve cache/data source blocker",
        "error": cache_result.error,
    }
    (runtime_dir / "dss_003_decision.json").write_text(
        json.dumps(decision_doc, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (research_dir / "DSS_003_DATA_SOURCE_AUDIT.md").write_text(
        """# DSS-003 Data Source Audit

Best existing path: reuse `IBKRHistoricalDataProvider.fetch_ohlcv()` from `backend/tradeo/services/ibkr_data_provider.py`.

Findings:
- It already qualifies `Stock(symbol, SMART, USD)` and requests historical bars through IBKR.
- It supports `1d` via `_bar_size_from_interval`.
- It uses `TRADEO_MARKET_DATA_WHAT_TO_SHOW`, default `ADJUSTED_LAST`.
- It has no reusable Daily cache writer, manifest, resume, or quality gate.

Decision: add `scripts/cache_daily_ohlcv.py` and `scripts/check_daily_ohlcv_quality.py` as read-only Daily cache tooling, without changing intraday infrastructure.
""",
        encoding="utf-8",
    )
    (research_dir / "DSS_003_CACHE_LOADER.md").write_text(
        f"""# DSS-003 Cache Loader

Loader: `scripts/cache_daily_ohlcv.py`

Cache status: {cache_result.status}
Fetched: {cache_result.fetched}
Skipped: {cache_result.skipped}
Failed: {cache_result.failed}
Manifest: `{cache_result.manifest_path}`

The loader requires explicit `--read-only`. It writes one CSV per symbol and a manifest. It is idempotent with `--resume` and refuses unsupported sources.

Error: {cache_result.error or 'none'}
""",
        encoding="utf-8",
    )
    (research_dir / "DSS_003_DATA_QUALITY_GATE.md").write_text(
        f"""# DSS-003 Data Quality Gate

DATA_GATE={quality_summary.get('data_gate')}

- Operational DATA_READY: {quality_summary.get('operational_ready')}
- Benchmark DATA_READY: {quality_summary.get('benchmark_ready')}
- Required operational DATA_READY: {quality_summary.get('min_operational_ready')}
- 2026-07-03 false bar present: {quality_summary.get('false_bar_2026_07_03_present')}
- Last valid bar date: {quality_summary.get('last_valid_bar_date')}

Quality report: `{quality_summary.get('report_csv')}`
""",
        encoding="utf-8",
    )
    (research_dir / "DSS_003_FINAL_REPORT.md").write_text(
        f"""# DSS-003 Final Report

Decision: {decision}

No orders were sent. No IBKR write/action path was used. `.env` was not modified.

- Cache status: {cache_result.status}
- DATA_GATE: {quality_summary.get('data_gate')}
- Operational DATA_READY: {quality_summary.get('operational_ready')}
- Benchmark DATA_READY: {quality_summary.get('benchmark_ready')}
- 2026-07-03 false bar present: {quality_summary.get('false_bar_2026_07_03_present')}
- last_valid_bar_date: {quality_summary.get('last_valid_bar_date')}
- Read-only required: true

Next phase: {decision_doc['next_phase']}.
""",
        encoding="utf-8",
    )
    return decision_doc


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
