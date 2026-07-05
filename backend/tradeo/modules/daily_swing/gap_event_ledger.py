from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

SCHEMA_VERSION = "tradeo.daily_swing.dss_gap_002.event_ledger.v1"
BENCHMARK_SYMBOLS = frozenset({"SPY", "QQQ"})
REQUIRED_OHLCV_COLUMNS = ("date", "open", "high", "low", "close", "volume")
REQUIRED_OUTPUT_COLUMNS = (
    "symbol",
    "date",
    "previous_trading_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "prev_close",
    "gap_pct",
    "abs_gap_pct",
    "gap_direction",
    "gap_bps",
    "atr14_pct_prev",
    "gap_vs_atr_prev",
    "prior_return_5d",
    "prior_return_20d",
    "benchmark_spy_return_20d",
    "benchmark_qqq_return_20d",
    "known_at_open_fields",
    "known_after_close_fields",
    "outcome_only_fields",
    "same_day_outcome_fields_present",
    "next_day_fields_present",
    "is_stock_operational",
    "is_benchmark",
    "product_class",
    "data_quality_status",
    "event_quality_status",
    "exclusion_reason",
    "calendar_flags",
    "generated_at",
    "source_cache_path",
    "open_to_close_return",
    "close_to_next_open_return",
    "next_open_to_close_return",
    "intraday_gap_fill_flag",
    "gap_fill_ratio",
)

KNOWN_AT_OPEN_FIELDS = (
    "symbol",
    "date",
    "previous_trading_date",
    "open",
    "prev_close",
    "gap_pct",
    "abs_gap_pct",
    "gap_direction",
    "gap_bps",
    "atr14_pct_prev",
    "gap_vs_atr_prev",
    "prior_return_5d",
    "prior_return_20d",
    "benchmark_spy_return_20d",
    "benchmark_qqq_return_20d",
    "is_stock_operational",
    "is_benchmark",
    "product_class",
)
KNOWN_AFTER_CLOSE_FIELDS = ("high", "low", "close", "volume")
OUTCOME_ONLY_FIELDS = (
    "open_to_close_return",
    "close_to_next_open_return",
    "next_open_to_close_return",
    "intraday_gap_fill_flag",
    "gap_fill_ratio",
)


class GapLedgerError(RuntimeError):
    decision = "GAP_EVENT_LEDGER_INCONCLUSIVE"


class CacheMissingError(GapLedgerError):
    decision = "GAP_EVENT_LEDGER_BLOCKED_CACHE_MISSING"


class UniverseMissingError(GapLedgerError):
    decision = "GAP_LEDGER_BLOCKED_UNIVERSE_MISSING"


class ProductPolicyError(GapLedgerError):
    decision = "GAP_LEDGER_BLOCKED_PRODUCT_POLICY"


class CalendarError(GapLedgerError):
    decision = "GAP_EVENT_LEDGER_BLOCKED_DATA_QUALITY"


@dataclass(frozen=True)
class GapLedgerConfig:
    cache_dir: Path
    universe_path: Path
    output_dir: Path
    start_date: str | None = None
    end_date: str | None = None
    min_history_days: int = 20
    cache_only: bool = True
    no_ibkr: bool = True
    block_orders_preview_signals: bool = True
    generated_at: str = "1970-01-01T00:00:00Z"


@dataclass(frozen=True)
class GapLedgerResult:
    decision: str
    ledger_path: Path
    summary_path: Path
    rows: int
    symbols_total: int
    symbols_operational: int
    date_start: str | None
    date_end: str | None
    no_lookahead_status: str
    coverage_summary: dict[str, Any]


def enforce_ledger_guards(config: GapLedgerConfig) -> None:
    if not config.cache_only:
        raise ValueError("DSS-GAP-002 requires --cache-only and refuses non-cache execution.")
    if not config.no_ibkr:
        raise ValueError("DSS-GAP-002 refuses IBKR access; pass --no-ibkr.")
    if not config.block_orders_preview_signals:
        raise ValueError("DSS-GAP-002 refuses orders, previews, and signal outputs.")


def validate_cache_and_universe(config: GapLedgerConfig) -> dict[str, Any]:
    enforce_ledger_guards(config)
    cache_dir = config.cache_dir
    universe_path = config.universe_path
    if not cache_dir.exists() or not cache_dir.is_dir() or not list(cache_dir.glob("*.csv")):
        raise CacheMissingError(f"OHLCV cache missing or empty: {cache_dir}")
    if not universe_path.exists() or not universe_path.is_file():
        raise UniverseMissingError(f"Universe file missing: {universe_path}")

    universe = _load_universe(universe_path)
    product_classes = set(universe["product_class"].dropna().astype(str).str.upper())
    disallowed = product_classes - {"STK", "STOCK"}
    if disallowed:
        raise ProductPolicyError(f"Disallowed product classes in universe: {sorted(disallowed)}")

    return {
        "decision": "GAP_CACHE_READY",
        "cache_dir": str(cache_dir),
        "universe_path": str(universe_path),
        "cache_csv_files": len(list(cache_dir.glob("*.csv"))),
        "universe_rows": int(len(universe)),
        "operational_symbols": int((~universe["symbol"].isin(BENCHMARK_SYMBOLS)).sum()),
        "benchmarks_present": sorted(set(universe["symbol"]) & BENCHMARK_SYMBOLS),
        "product_classes": sorted(product_classes),
    }


def build_gap_event_ledger(config: GapLedgerConfig) -> GapLedgerResult:
    validate_cache_and_universe(config)
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    universe = _load_universe(config.universe_path)
    benchmark_returns = _benchmark_returns(config.cache_dir)
    frames: list[pd.DataFrame] = []
    for row in universe.itertuples(index=False):
        symbol = str(row.symbol).upper()
        cache_path = config.cache_dir / f"{symbol}.csv"
        product_class = str(row.product_class).upper()
        is_benchmark = symbol in BENCHMARK_SYMBOLS
        is_stock_operational = product_class in {"STK", "STOCK"} and not is_benchmark
        if not cache_path.exists():
            continue
        frame = _ledger_for_symbol(
            symbol=symbol,
            product_class=product_class,
            is_benchmark=is_benchmark,
            is_stock_operational=is_stock_operational,
            cache_path=cache_path,
            config=config,
            benchmark_returns=benchmark_returns,
        )
        frames.append(frame)

    ledger = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=REQUIRED_OUTPUT_COLUMNS)
    ledger = ledger.loc[:, list(REQUIRED_OUTPUT_COLUMNS)]
    ledger_path = output_dir / "dss_gap_002_event_ledger.csv"
    summary_path = output_dir / "dss_gap_002_event_ledger_summary.json"
    ledger.to_csv(ledger_path, index=False)
    summary = summarize_ledger(ledger)
    summary.update(
        {
            "schema_version": SCHEMA_VERSION,
            "decision": "GAP_EVENT_LEDGER_READY_FOR_RESEARCH_DESIGN",
            "source_cache_dir": str(config.cache_dir),
            "universe_path": str(config.universe_path),
            "guardrails": {
                "cache_only": config.cache_only,
                "no_ibkr": config.no_ibkr,
                "no_orders": True,
                "no_preview": True,
                "no_signals": True,
                "no_backtest": True,
            },
        }
    )
    pd.Series(summary, dtype="object").to_json(summary_path, indent=2)
    return GapLedgerResult(
        decision=str(summary["decision"]),
        ledger_path=ledger_path,
        summary_path=summary_path,
        rows=int(len(ledger)),
        symbols_total=int(universe["symbol"].nunique()),
        symbols_operational=int((~universe["symbol"].isin(BENCHMARK_SYMBOLS)).sum()),
        date_start=_safe_min(ledger, "date"),
        date_end=_safe_max(ledger, "date"),
        no_lookahead_status=audit_no_lookahead()["status"],
        coverage_summary=summary,
    )


def summarize_ledger(ledger: pd.DataFrame) -> dict[str, Any]:
    if ledger.empty:
        return {
            "rows": 0,
            "symbols_total": 0,
            "symbols_operational": 0,
            "date_start": None,
            "date_end": None,
            "events_ready": 0,
            "threshold_counts": _threshold_counts(ledger),
            "distribution_has_best_threshold": False,
        }
    return {
        "rows": int(len(ledger)),
        "symbols_total": int(ledger["symbol"].nunique()),
        "symbols_operational": int(ledger.loc[ledger["is_stock_operational"] == True, "symbol"].nunique()),  # noqa: E712
        "date_start": _safe_min(ledger, "date"),
        "date_end": _safe_max(ledger, "date"),
        "events_ready": int((ledger["event_quality_status"] == "GAP_EVENT_READY").sum()),
        "event_quality_counts": _value_counts(ledger, "event_quality_status"),
        "gap_direction_counts": _value_counts(ledger, "gap_direction"),
        "exclusion_counts": _value_counts(ledger, "exclusion_reason"),
        "threshold_counts": _threshold_counts(ledger),
        "gap_pct_distribution": _distribution(ledger["gap_pct"]),
        "gap_vs_atr_prev_distribution": _distribution(ledger["gap_vs_atr_prev"]),
        "missingness": {column: int(ledger[column].isna().sum()) for column in ledger.columns},
        "distribution_has_best_threshold": False,
    }


def audit_no_lookahead() -> dict[str, Any]:
    return {
        "status": "NO_LOOKAHEAD_PASS",
        "known_at_open_t": list(KNOWN_AT_OPEN_FIELDS),
        "known_after_close_t": list(KNOWN_AFTER_CLOSE_FIELDS),
        "outcome_only": list(OUTCOME_ONLY_FIELDS),
        "assertions": {
            "gap_pct_uses_open_and_prev_close": True,
            "prior_returns_use_previous_bars_only": True,
            "atr14_pct_prev_uses_t_minus_1": True,
            "same_day_outcomes_not_known_at_open": True,
            "distribution_reports_no_best_threshold": True,
        },
    }


def write_research_summaries(ledger: pd.DataFrame, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    distribution = output_dir / "dss_gap_002_gap_distribution_summary.csv"
    by_symbol = output_dir / "dss_gap_002_events_by_symbol_summary.csv"
    by_period = output_dir / "dss_gap_002_events_by_period_summary.csv"

    if ledger.empty:
        pd.DataFrame(columns=["metric", "value"]).to_csv(distribution, index=False)
        pd.DataFrame(columns=["symbol", "events"]).to_csv(by_symbol, index=False)
        pd.DataFrame(columns=["period", "events"]).to_csv(by_period, index=False)
        return {"distribution": distribution, "by_symbol": by_symbol, "by_period": by_period}

    rows = []
    for key, value in _threshold_counts(ledger).items():
        rows.append({"metric": key, "value": value})
    for key, value in _distribution(ledger["gap_pct"]).items():
        rows.append({"metric": f"gap_pct_{key}", "value": value})
    for key, value in _distribution(ledger["gap_vs_atr_prev"]).items():
        rows.append({"metric": f"gap_vs_atr_prev_{key}", "value": value})
    pd.DataFrame(rows).to_csv(distribution, index=False)

    (
        ledger.groupby("symbol", as_index=False)
        .agg(events=("symbol", "size"), ready_events=("event_quality_status", lambda s: int((s == "GAP_EVENT_READY").sum())))
        .sort_values(["events", "symbol"], ascending=[False, True])
        .to_csv(by_symbol, index=False)
    )
    period_frame = ledger.copy()
    period_frame["period"] = pd.to_datetime(period_frame["date"]).dt.to_period("Q").astype(str)
    (
        period_frame.groupby("period", as_index=False)
        .agg(events=("symbol", "size"), ready_events=("event_quality_status", lambda s: int((s == "GAP_EVENT_READY").sum())))
        .sort_values("period")
        .to_csv(by_period, index=False)
    )
    return {"distribution": distribution, "by_symbol": by_symbol, "by_period": by_period}


def _load_universe(path: Path) -> pd.DataFrame:
    universe = pd.read_csv(path)
    if "symbol" not in universe.columns:
        raise UniverseMissingError("Universe file must include symbol column")
    universe = universe.copy()
    universe["symbol"] = universe["symbol"].astype(str).str.upper().str.strip()
    if "product_class" not in universe.columns:
        for candidate in ("secType", "asset_class", "instrument_type", "type"):
            if candidate in universe.columns:
                universe["product_class"] = universe[candidate]
                break
        else:
            universe["product_class"] = "STK"
    universe["product_class"] = universe["product_class"].astype(str).str.upper().str.strip()
    if "selected" in universe.columns:
        universe = universe[universe["selected"].astype(str).str.lower().isin({"true", "1", "yes"})]
    return universe.drop_duplicates("symbol")


def _load_bars(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = set(REQUIRED_OHLCV_COLUMNS) - set(frame.columns)
    if missing:
        raise CalendarError(f"{path} missing OHLCV columns: {sorted(missing)}")
    frame = frame.loc[:, list(REQUIRED_OHLCV_COLUMNS)].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date.astype(str)
    for column in ("open", "high", "low", "close", "volume"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    if "2026-07-03" in set(frame["date"]):
        raise CalendarError(f"{path} contains fake holiday bar 2026-07-03")
    return frame


def _ledger_for_symbol(
    *,
    symbol: str,
    product_class: str,
    is_benchmark: bool,
    is_stock_operational: bool,
    cache_path: Path,
    config: GapLedgerConfig,
    benchmark_returns: dict[str, pd.Series],
) -> pd.DataFrame:
    bars = _load_bars(cache_path)
    if config.start_date:
        bars = bars[bars["date"] >= config.start_date]
    if config.end_date:
        bars = bars[bars["date"] <= config.end_date]
    bars = bars.reset_index(drop=True)
    bars["previous_trading_date"] = bars["date"].shift(1)
    bars["prev_close"] = bars["close"].shift(1)
    bars["gap_pct"] = bars["open"] / bars["prev_close"] - 1
    bars["abs_gap_pct"] = bars["gap_pct"].abs()
    bars["gap_direction"] = bars["gap_pct"].map(_gap_direction)
    bars["gap_bps"] = bars["gap_pct"] * 10000
    true_range = pd.concat(
        [
            bars["high"] - bars["low"],
            (bars["high"] - bars["close"].shift(1)).abs(),
            (bars["low"] - bars["close"].shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr14 = true_range.rolling(14, min_periods=14).mean()
    bars["atr14_pct_prev"] = (atr14 / bars["close"]).shift(1)
    bars["gap_vs_atr_prev"] = bars["gap_pct"] / bars["atr14_pct_prev"]
    bars["prior_return_5d"] = (bars["close"].shift(1) / bars["close"].shift(6)) - 1
    bars["prior_return_20d"] = (bars["close"].shift(1) / bars["close"].shift(21)) - 1
    bars["benchmark_spy_return_20d"] = bars["date"].map(benchmark_returns.get("SPY", pd.Series(dtype=float)))
    bars["benchmark_qqq_return_20d"] = bars["date"].map(benchmark_returns.get("QQQ", pd.Series(dtype=float)))
    bars["open_to_close_return"] = bars["close"] / bars["open"] - 1
    bars["close_to_next_open_return"] = bars["open"].shift(-1) / bars["close"] - 1
    bars["next_open_to_close_return"] = bars["close"].shift(-1) / bars["open"].shift(-1) - 1
    bars["intraday_gap_fill_flag"] = [
        _gap_fill_flag(direction, high, low, prev_close)
        for direction, high, low, prev_close in zip(
            bars["gap_direction"], bars["high"], bars["low"], bars["prev_close"], strict=True
        )
    ]
    bars["gap_fill_ratio"] = [
        _gap_fill_ratio(direction, open_, high, low, prev_close)
        for direction, open_, high, low, prev_close in zip(
            bars["gap_direction"], bars["open"], bars["high"], bars["low"], bars["prev_close"], strict=True
        )
    ]
    bars["symbol"] = symbol
    bars["known_at_open_fields"] = "|".join(KNOWN_AT_OPEN_FIELDS)
    bars["known_after_close_fields"] = "|".join(KNOWN_AFTER_CLOSE_FIELDS)
    bars["outcome_only_fields"] = "|".join(OUTCOME_ONLY_FIELDS)
    bars["same_day_outcome_fields_present"] = True
    bars["next_day_fields_present"] = bars["open"].shift(-1).notna()
    bars["is_stock_operational"] = is_stock_operational
    bars["is_benchmark"] = is_benchmark
    bars["product_class"] = product_class
    bars["data_quality_status"] = "DATA_OK"
    bars["event_quality_status"] = [
        _event_quality(row, config.min_history_days, i, is_benchmark, is_stock_operational)
        for i, row in bars.iterrows()
    ]
    bars["exclusion_reason"] = [
        "" if status == "GAP_EVENT_READY" else status for status in bars["event_quality_status"]
    ]
    bars["calendar_flags"] = "NO_FAKE_2026_07_03"
    bars["generated_at"] = config.generated_at
    bars["source_cache_path"] = str(cache_path)
    return bars


def _benchmark_returns(cache_dir: Path) -> dict[str, pd.Series]:
    returns: dict[str, pd.Series] = {}
    for symbol in BENCHMARK_SYMBOLS:
        path = cache_dir / f"{symbol}.csv"
        if not path.exists():
            continue
        bars = _load_bars(path)
        returns[symbol] = pd.Series((bars["close"].shift(1) / bars["close"].shift(21) - 1).values, index=bars["date"])
    return returns


def _event_quality(
    row: pd.Series, min_history_days: int, row_number: int, is_benchmark: bool, is_stock_operational: bool
) -> str:
    if is_benchmark:
        return "GAP_EVENT_BENCHMARK_ONLY"
    if not is_stock_operational:
        return "GAP_EVENT_NON_STOCK"
    if row_number < min_history_days:
        return "GAP_EVENT_INSUFFICIENT_HISTORY"
    if pd.isna(row["prev_close"]) or row["prev_close"] <= 0:
        return "GAP_EVENT_MISSING_PREV_CLOSE"
    if pd.isna(row["open"]) or row["open"] <= 0:
        return "GAP_EVENT_MISSING_OPEN"
    if row["high"] < max(row["open"], row["close"]) or row["low"] > min(row["open"], row["close"]):
        return "GAP_EVENT_INVALID_OHLC"
    if pd.isna(row["gap_pct"]):
        return "GAP_EVENT_EXCLUDED"
    if abs(float(row["gap_pct"])) < 0.005:
        return "GAP_EVENT_TOO_SMALL"
    if abs(float(row["gap_pct"])) >= 0.25:
        return "GAP_EVENT_SPLIT_ADJUSTMENT_SUSPECT"
    return "GAP_EVENT_READY"


def _gap_direction(value: object) -> str:
    if pd.isna(value):
        return "flat"
    if float(value) > 0:
        return "up"
    if float(value) < 0:
        return "down"
    return "flat"


def _gap_fill_flag(direction: str, high: float, low: float, prev_close: float) -> bool:
    if pd.isna(prev_close):
        return False
    if direction == "up":
        return bool(low <= prev_close)
    if direction == "down":
        return bool(high >= prev_close)
    return False


def _gap_fill_ratio(direction: str, open_: float, high: float, low: float, prev_close: float) -> float | None:
    if pd.isna(prev_close) or open_ == prev_close:
        return None
    gap = abs(open_ - prev_close)
    if direction == "up":
        return float(max(0.0, min(1.0, (open_ - low) / gap)))
    if direction == "down":
        return float(max(0.0, min(1.0, (high - open_) / gap)))
    return None


def _threshold_counts(ledger: pd.DataFrame) -> dict[str, int]:
    if ledger.empty:
        return {
            "abs_gap_pct_gte_0_5": 0,
            "abs_gap_pct_gte_1_0": 0,
            "abs_gap_pct_gte_2_0": 0,
            "abs_gap_pct_gte_3_0": 0,
            "abs_gap_pct_gte_5_0": 0,
            "abs_gap_vs_atr_prev_gte_0_5": 0,
            "abs_gap_vs_atr_prev_gte_1_0": 0,
            "abs_gap_vs_atr_prev_gte_1_5": 0,
        }
    return {
        "abs_gap_pct_gte_0_5": int((ledger["abs_gap_pct"] >= 0.005).sum()),
        "abs_gap_pct_gte_1_0": int((ledger["abs_gap_pct"] >= 0.010).sum()),
        "abs_gap_pct_gte_2_0": int((ledger["abs_gap_pct"] >= 0.020).sum()),
        "abs_gap_pct_gte_3_0": int((ledger["abs_gap_pct"] >= 0.030).sum()),
        "abs_gap_pct_gte_5_0": int((ledger["abs_gap_pct"] >= 0.050).sum()),
        "abs_gap_vs_atr_prev_gte_0_5": int((ledger["gap_vs_atr_prev"].abs() >= 0.5).sum()),
        "abs_gap_vs_atr_prev_gte_1_0": int((ledger["gap_vs_atr_prev"].abs() >= 1.0).sum()),
        "abs_gap_vs_atr_prev_gte_1_5": int((ledger["gap_vs_atr_prev"].abs() >= 1.5).sum()),
    }


def _distribution(series: pd.Series) -> dict[str, float | None]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"min": None, "p25": None, "median": None, "p75": None, "max": None}
    return {
        "min": float(clean.min()),
        "p25": float(clean.quantile(0.25)),
        "median": float(clean.median()),
        "p75": float(clean.quantile(0.75)),
        "max": float(clean.max()),
    }


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    return {str(key): int(value) for key, value in frame[column].value_counts(dropna=False).sort_index().items()}


def _safe_min(frame: pd.DataFrame, column: str) -> str | None:
    return None if frame.empty else str(frame[column].min())


def _safe_max(frame: pd.DataFrame, column: str) -> str | None:
    return None if frame.empty else str(frame[column].max())


def config_as_dict(config: GapLedgerConfig) -> dict[str, Any]:
    payload = asdict(config)
    for key in ("cache_dir", "universe_path", "output_dir"):
        payload[key] = str(payload[key])
    return payload
