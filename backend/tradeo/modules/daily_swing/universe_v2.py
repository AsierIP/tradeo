from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import blake2b
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

SCHEMA_VERSION = "tradeo.daily_swing.universe_v2.v1"
SUMMARY_SCHEMA_VERSION = "tradeo.daily_swing.universe_v2.summary.v1"
BUCKET_VERSION = "daily_focus_universe_v2"
ETF_MACRO_BUCKET = "etf_macro"
REQUIRED_BUCKETS: tuple[str, ...] = (
    "mega_large_cap",
    "large_cap_core",
    "liquid_mid_cap",
    "liquid_small_cap",
    "high_beta_growth",
    "defensive_quality",
    "sector_leaders",
    ETF_MACRO_BUCKET,
)
STOCK_BUCKETS = tuple(bucket for bucket in REQUIRED_BUCKETS if bucket != ETF_MACRO_BUCKET)
DEFAULT_RUNTIME_OUTPUT_PATH = Path("artifacts/runtime/daily_swing/universe_daily_swing_v2.csv")
DEFAULT_RESEARCH_DIR = Path("research/daily_swing/universe")
DEFAULT_BUCKET_SUMMARY_CSV = DEFAULT_RESEARCH_DIR / "daily_universe_v2_bucket_summary.csv"
DEFAULT_BUCKET_SUMMARY_JSON = DEFAULT_RESEARCH_DIR / "daily_universe_v2_bucket_summary.json"

_ETF_SYMBOLS = {
    "AGG",
    "ARKK",
    "DIA",
    "EEM",
    "EFA",
    "GLD",
    "HYG",
    "IEF",
    "IWM",
    "LQD",
    "QQQ",
    "SHY",
    "SMH",
    "SPY",
    "TLT",
    "VTI",
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLU",
    "XLV",
    "XLY",
}
_ETF_PRODUCT_VALUES = {
    "etf",
    "etn",
    "etp",
    "exchange traded fund",
    "exchange traded note",
    "exchange traded product",
    "fund",
}
_STOCK_PRODUCT_VALUES = {
    "adr",
    "common stock",
    "common_stock",
    "equity",
    "ordinary share",
    "ordinary_share",
    "share",
    "stock",
    "stk",
}
_PRODUCT_CLASS_FIELDS = (
    "product_class",
    "asset_class",
    "asset_type",
    "instrument",
    "instrument_type",
    "product_type",
    "quote_type",
    "security_type",
    "sec_type",
)
_ETF_HINTS = (
    " etf ",
    " etn ",
    " etp ",
    " exchange traded fund ",
    " exchange-traded fund ",
    " exchange traded note ",
    " index fund ",
    " spdr ",
    " ishares ",
    " vanguard ",
    " proshares ",
    " invesco ",
    " select sector ",
)
_ADR_HINTS = (" adr ", " american depositary ", " depositary receipt ")
_NUMERIC_FIELDS = ("priority", "liquidity_score", "quality_score", "beta_score", "score")
MIN_LIQUIDITY_SCORE_BY_BUCKET = {
    "mega_large_cap": 0.60,
    "large_cap_core": 0.50,
    "liquid_mid_cap": 0.35,
    "liquid_small_cap": 0.25,
    "high_beta_growth": 0.35,
    "defensive_quality": 0.35,
    "sector_leaders": 0.40,
    ETF_MACRO_BUCKET: 0.50,
}


@dataclass(frozen=True, slots=True)
class DailySwingUniverseV2Config:
    max_symbols_per_bucket: int = 8
    required_buckets: tuple[str, ...] = REQUIRED_BUCKETS
    bucket_version: str = BUCKET_VERSION
    market_cap_point_in_time_source: str | None = None
    rotation_salt: str | None = None


@dataclass(frozen=True, slots=True)
class DailySwingUniverseV2Result:
    rows: pd.DataFrame
    bucket_summary: pd.DataFrame
    metadata: dict[str, Any]
    output_path: Path | None = None
    summary_csv_path: Path | None = None
    summary_json_path: Path | None = None

    @property
    def selected_symbols(self) -> list[str]:
        if self.rows.empty:
            return []
        selected = self.rows[self.rows["selected"]].sort_values(["bucket", "bucket_rank", "symbol"])
        return [str(symbol) for symbol in selected["symbol"].tolist()]


class DailySwingUniverseV2Builder:
    """Build a deterministic daily swing focus universe without market-data refreshes."""

    def __init__(self, config: DailySwingUniverseV2Config | None = None) -> None:
        self.config = config or DailySwingUniverseV2Config()

    def build(
        self,
        *,
        seed_files: Iterable[str | Path] | None = None,
        candidates: Iterable[Mapping[str, Any]] | None = None,
        output_path: str | Path | None = None,
        summary_csv_path: str | Path | None = None,
        summary_json_path: str | Path | None = None,
    ) -> DailySwingUniverseV2Result:
        generated_at = datetime.now(UTC).isoformat()
        rotation_salt = self.config.rotation_salt or generated_at[:10]
        source_rows = self._source_rows(seed_files=seed_files, candidates=candidates)
        market_cap = self._market_cap_metadata()
        normalized = [
            self._normalize_candidate(
                row,
                row_order=index,
                rotation_salt=rotation_salt,
                market_cap=market_cap,
            )
            for index, row in enumerate(source_rows)
        ]
        self._mark_duplicate_symbols(normalized)
        selected_symbols = self._select(normalized)
        for row in normalized:
            symbol = str(row["symbol"])
            selected_rank = selected_symbols.get(symbol)
            if selected_rank is None:
                row["selected"] = False
                row["rank"] = 0
                row["bucket_rank"] = 0
            else:
                row["selected"] = True
                row["status"] = "selected"
                row["rank"] = selected_rank["global_rank"]
                row["bucket_rank"] = selected_rank["bucket_rank"]

        rows = pd.DataFrame(normalized)
        if rows.empty:
            rows = pd.DataFrame(columns=self._output_columns())
        else:
            rows = rows.sort_values(
                ["selected", "bucket", "bucket_rank", "score", "symbol"],
                ascending=[False, True, True, False, True],
            )
            rows = rows[self._output_columns()].reset_index(drop=True)

        bucket_summary = self._bucket_summary(rows, market_cap=market_cap)
        metadata = self._metadata(
            rows=rows,
            bucket_summary=bucket_summary,
            generated_at=generated_at,
            rotation_salt=rotation_salt,
            market_cap=market_cap,
            seed_files=seed_files,
        )

        output = Path(output_path) if output_path is not None else None
        summary_csv = Path(summary_csv_path) if summary_csv_path is not None else None
        summary_json = Path(summary_json_path) if summary_json_path is not None else None
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            rows.to_csv(output, index=False)
        if summary_csv is not None:
            summary_csv.parent.mkdir(parents=True, exist_ok=True)
            bucket_summary.to_csv(summary_csv, index=False)
        if summary_json is not None:
            summary_json.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "schema_version": SUMMARY_SCHEMA_VERSION,
                "generated_at": generated_at,
                "metadata": metadata,
                "bucket_summary": bucket_summary.to_dict(orient="records"),
            }
            summary_json.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True), encoding="utf-8")

        return DailySwingUniverseV2Result(
            rows=rows,
            bucket_summary=bucket_summary,
            metadata=metadata,
            output_path=output,
            summary_csv_path=summary_csv,
            summary_json_path=summary_json,
        )

    def _source_rows(
        self,
        *,
        seed_files: Iterable[str | Path] | None,
        candidates: Iterable[Mapping[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if candidates is not None:
            rows.extend(dict(row) for row in candidates)
        for seed_file in seed_files or ():
            path = Path(seed_file)
            if not path.exists():
                raise FileNotFoundError(path)
            frame = pd.read_csv(path)
            if "symbol" not in frame.columns:
                raise ValueError(f"Daily universe seed file requires a 'symbol' column: {path}")
            for row in frame.to_dict(orient="records"):
                candidate = dict(row)
                candidate.setdefault("source", str(path))
                rows.append(candidate)
        if not rows:
            rows.extend(dict(row) for row in DEFAULT_CANDIDATES)
        return rows

    def _normalize_candidate(
        self,
        row: Mapping[str, Any],
        *,
        row_order: int,
        rotation_salt: str,
        market_cap: Mapping[str, Any],
    ) -> dict[str, Any]:
        symbol = _normalize_symbol(row.get("symbol"))
        raw_bucket = row.get("bucket", row.get("universe_bucket", row.get("focus_bucket")))
        bucket = _normalize_bucket(raw_bucket)
        product_class = _classify_product(symbol, row)
        priority = _number(row.get("priority"), default=50.0)
        liquidity_score = _bounded_number(row.get("liquidity_score"), default=_bucket_default(bucket, "liquidity"))
        quality_score = _bounded_number(row.get("quality_score"), default=_bucket_default(bucket, "quality"))
        beta_score = _bounded_number(row.get("beta_score"), default=_bucket_default(bucket, "beta"))
        score = _number(row.get("score"), default=math.nan)
        if not math.isfinite(score):
            score = _score(
                bucket=bucket,
                priority=priority,
                liquidity_score=liquidity_score,
                quality_score=quality_score,
                beta_score=beta_score,
            )

        reasons = self._reason_codes(
            symbol=symbol,
            bucket=bucket,
            product_class=product_class,
            liquidity_score=liquidity_score,
        )
        status = "eligible" if not reasons else "rejected"
        bucket_reason = _bucket_reason(bucket)
        market_cap_bucket = _market_cap_bucket(bucket, product_class)
        liquidity_bucket = _liquidity_bucket(liquidity_score)
        volatility_bucket = _volatility_bucket(beta_score, bucket)
        beta_proxy = round(beta_score, 6)
        avg_dollar_volume_proxy = _avg_dollar_volume_proxy(bucket, liquidity_score)
        avg_spread_proxy = _avg_spread_proxy(liquidity_score)
        rejection_reason = ";".join(reasons)
        eligible = status == "eligible"
        return {
            "symbol": symbol,
            "company_name": _clean_text(row.get("company_name") or row.get("name")),
            "name": _clean_text(row.get("name")),
            "bucket": bucket,
            "bucket_reason": bucket_reason,
            "bucket_version": self.config.bucket_version,
            "sector": _clean_text(row.get("sector")),
            "industry": _clean_text(row.get("industry")),
            "product_class": product_class,
            "product_type": _clean_text(row.get("product_type") or row.get("asset_type") or row.get("sec_type")),
            "selected": False,
            "rank": 0,
            "bucket_rank": 0,
            "status": status,
            "score": round(score, 6),
            "reason_codes": rejection_reason,
            "rejection_reason": rejection_reason,
            "market_cap_bucket": market_cap_bucket,
            "market_cap_source": market_cap["source"],
            "market_cap_method": market_cap["method"],
            "market_cap_bucket_method": market_cap["method"],
            "survivorship_warning": bool(market_cap["survivorship_warning"]),
            "liquidity_bucket": liquidity_bucket,
            "avg_dollar_volume_proxy": avg_dollar_volume_proxy,
            "avg_spread_proxy": avg_spread_proxy,
            "volatility_bucket": volatility_bucket,
            "beta_proxy": beta_proxy,
            "daily_history_rows": int(_number(row.get("daily_history_rows"), default=0.0)),
            "first_date": _clean_text(row.get("first_date")),
            "last_date": _clean_text(row.get("last_date")),
            "eligible_for_daily_swing": eligible,
            "eligible_for_lab_watchlist": eligible,
            "eligible_for_research": eligible,
            "data_source": _clean_text(row.get("data_source") or row.get("source") or "builtin:daily_universe_v2_proxy_seed"),
            "source": _clean_text(row.get("source") or "builtin:daily_universe_v2_proxy_seed"),
            "priority": round(priority, 6),
            "liquidity_score": round(liquidity_score, 6),
            "quality_score": round(quality_score, 6),
            "beta_score": round(beta_score, 6),
            "notes": _clean_text(row.get("notes") or row.get("note")),
            "rotation_hash": _rotation_hash(symbol, rotation_salt),
            "_row_order": row_order,
        }

    def _reason_codes(
        self,
        *,
        symbol: str,
        bucket: str,
        product_class: str,
        liquidity_score: float,
    ) -> list[str]:
        reasons: list[str] = []
        if not symbol:
            reasons.append("missing_symbol")
        if bucket not in self.config.required_buckets:
            reasons.append("unsupported_bucket")
        is_etf = product_class == "etf"
        if is_etf and bucket != ETF_MACRO_BUCKET:
            reasons.append("etf_must_use_etf_macro")
        if not is_etf and bucket == ETF_MACRO_BUCKET:
            reasons.append("etf_macro_requires_etf")
        if bucket in STOCK_BUCKETS and product_class not in {"common_stock", "adr"}:
            reasons.append("stock_bucket_requires_equity")
        min_liquidity = MIN_LIQUIDITY_SCORE_BY_BUCKET.get(bucket)
        if min_liquidity is not None and liquidity_score < min_liquidity:
            if bucket == "liquid_small_cap":
                reasons.append("low_liquidity_smallcap_requires_warning")
            else:
                reasons.append("liquidity_proxy_below_bucket_minimum")
        return reasons

    @staticmethod
    def _mark_duplicate_symbols(rows: list[dict[str, Any]]) -> None:
        seen: set[str] = set()
        for row in rows:
            symbol = str(row.get("symbol") or "")
            if not symbol:
                continue
            if symbol in seen:
                reasons = [reason for reason in str(row.get("reason_codes") or "").split(";") if reason]
                reasons.append("duplicate_symbol")
                row["reason_codes"] = ";".join(sorted(set(reasons)))
                row["status"] = "rejected"
            else:
                seen.add(symbol)

    def _select(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        selected: dict[str, dict[str, int]] = {}
        global_rank = 1
        max_per_bucket = max(0, int(self.config.max_symbols_per_bucket))
        for bucket in self.config.required_buckets:
            eligible = [
                row
                for row in rows
                if row["bucket"] == bucket and row["status"] == "eligible" and row["symbol"] not in selected
            ]
            eligible.sort(key=lambda row: (-float(row["score"]), int(row["_row_order"]), str(row["symbol"])))
            for bucket_rank, row in enumerate(eligible[:max_per_bucket], start=1):
                selected[str(row["symbol"])] = {
                    "global_rank": global_rank,
                    "bucket_rank": bucket_rank,
                }
                global_rank += 1
        return selected

    def _bucket_summary(self, rows: pd.DataFrame, *, market_cap: Mapping[str, Any]) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        for bucket in self.config.required_buckets:
            bucket_rows = rows[rows["bucket"] == bucket] if not rows.empty else rows
            selected_count = int(bucket_rows["selected"].sum()) if not bucket_rows.empty else 0
            eligible_count = int((bucket_rows["status"].isin(["eligible", "selected"])).sum()) if not bucket_rows.empty else 0
            rejected_count = int((bucket_rows["status"] == "rejected").sum()) if not bucket_rows.empty else 0
            etf_count = int((bucket_rows["product_class"] == "etf").sum()) if not bucket_rows.empty else 0
            records.append(
                {
                    "bucket": bucket,
                    "bucket_version": self.config.bucket_version,
                    "total_rows": int(len(bucket_rows)),
                    "eligible_count": eligible_count,
                    "selected_count": selected_count,
                    "rejected_count": rejected_count,
                    "etf_count": etf_count,
                    "stock_count": int(len(bucket_rows) - etf_count),
                    "market_cap_source": market_cap["source"],
                    "market_cap_method": market_cap["method"],
                    "survivorship_warning": bool(market_cap["survivorship_warning"]),
                }
            )
        return pd.DataFrame(records)

    def _metadata(
        self,
        *,
        rows: pd.DataFrame,
        bucket_summary: pd.DataFrame,
        generated_at: str,
        rotation_salt: str,
        market_cap: Mapping[str, Any],
        seed_files: Iterable[str | Path] | None,
    ) -> dict[str, Any]:
        selected_by_bucket = {
            str(row["bucket"]): int(row["selected_count"])
            for row in bucket_summary.to_dict(orient="records")
        }
        missing_required_buckets = [
            bucket for bucket in self.config.required_buckets if selected_by_bucket.get(bucket, 0) <= 0
        ]
        selected_rows = rows[rows["selected"]] if not rows.empty else rows
        reason_counts: dict[str, int] = {}
        if not rows.empty:
            for reason_field in rows["reason_codes"].astype(str):
                for reason in reason_field.split(";"):
                    if reason:
                        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "bucket_version": self.config.bucket_version,
            "required_buckets": list(self.config.required_buckets),
            "missing_required_buckets": missing_required_buckets,
            "total_candidates": int(len(rows)),
            "selected_count": int(len(selected_rows)),
            "rejected_count": int((rows["status"] == "rejected").sum()) if not rows.empty else 0,
            "selected_by_bucket": selected_by_bucket,
            "selected_symbols": [str(symbol) for symbol in selected_rows["symbol"].tolist()],
            "market_cap_point_in_time": dict(market_cap),
            "constraints": {
                "downloads": "none",
                "etfs_only_bucket": ETF_MACRO_BUCKET,
                "max_symbols_per_bucket": int(self.config.max_symbols_per_bucket),
            },
            "seed_files": [str(path) for path in seed_files or ()],
            "rotation_salt": rotation_salt,
            "reason_counts": dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))),
        }

    def _market_cap_metadata(self) -> dict[str, Any]:
        source = (self.config.market_cap_point_in_time_source or "").strip()
        if source and source.lower() not in {"none", "unavailable", "proxy"}:
            return {
                "source": source,
                "method": "point_in_time",
                "survivorship_warning": False,
            }
        return {
            "source": "unavailable",
            "method": "proxy",
            "survivorship_warning": True,
        }

    @staticmethod
    def _output_columns() -> list[str]:
        return [
            "symbol",
            "company_name",
            "name",
            "bucket",
            "bucket_reason",
            "bucket_version",
            "sector",
            "industry",
            "product_class",
            "product_type",
            "selected",
            "rank",
            "bucket_rank",
            "status",
            "score",
            "reason_codes",
            "rejection_reason",
            "market_cap_bucket",
            "market_cap_source",
            "market_cap_method",
            "market_cap_bucket_method",
            "survivorship_warning",
            "liquidity_bucket",
            "avg_dollar_volume_proxy",
            "avg_spread_proxy",
            "volatility_bucket",
            "beta_proxy",
            "daily_history_rows",
            "first_date",
            "last_date",
            "eligible_for_daily_swing",
            "eligible_for_lab_watchlist",
            "eligible_for_research",
            "data_source",
            "source",
            "priority",
            "liquidity_score",
            "quality_score",
            "beta_score",
            "notes",
            "rotation_hash",
        ]


def build_daily_swing_universe_v2(
    *,
    seed_files: Iterable[str | Path] | None = None,
    output_path: str | Path = DEFAULT_RUNTIME_OUTPUT_PATH,
    summary_csv_path: str | Path = DEFAULT_BUCKET_SUMMARY_CSV,
    summary_json_path: str | Path = DEFAULT_BUCKET_SUMMARY_JSON,
    max_symbols_per_bucket: int = 8,
    market_cap_point_in_time_source: str | None = None,
    rotation_salt: str | None = None,
) -> DailySwingUniverseV2Result:
    return DailySwingUniverseV2Builder(
        DailySwingUniverseV2Config(
            max_symbols_per_bucket=max_symbols_per_bucket,
            market_cap_point_in_time_source=market_cap_point_in_time_source,
            rotation_salt=rotation_salt,
        )
    ).build(
        seed_files=seed_files,
        output_path=output_path,
        summary_csv_path=summary_csv_path,
        summary_json_path=summary_json_path,
    )


def _normalize_symbol(value: Any) -> str:
    return _clean_text(value).upper().strip()


def _normalize_bucket(value: Any) -> str:
    return _clean_text(value).lower().strip().replace("-", "_")


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _number(value: Any, *, default: float) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _bounded_number(value: Any, *, default: float) -> float:
    return max(0.0, min(1.0, _number(value, default=default)))


def _bucket_default(bucket: str, metric: str) -> float:
    defaults = {
        "mega_large_cap": {"liquidity": 0.98, "quality": 0.86, "beta": 0.52},
        "large_cap_core": {"liquidity": 0.92, "quality": 0.82, "beta": 0.48},
        "liquid_mid_cap": {"liquidity": 0.76, "quality": 0.62, "beta": 0.66},
        "liquid_small_cap": {"liquidity": 0.58, "quality": 0.46, "beta": 0.78},
        "high_beta_growth": {"liquidity": 0.82, "quality": 0.50, "beta": 0.94},
        "defensive_quality": {"liquidity": 0.78, "quality": 0.94, "beta": 0.30},
        "sector_leaders": {"liquidity": 0.86, "quality": 0.80, "beta": 0.58},
        ETF_MACRO_BUCKET: {"liquidity": 0.96, "quality": 0.70, "beta": 0.55},
    }
    return defaults.get(bucket, {}).get(metric, 0.50)


def _bucket_reason(bucket: str) -> str:
    reasons = {
        "mega_large_cap": "proxy mega/large liquid leadership bucket; market cap point-in-time unavailable",
        "large_cap_core": "proxy large cap core liquidity/quality bucket; market cap point-in-time unavailable",
        "liquid_mid_cap": "proxy liquid mid cap bucket separated from large and small universes",
        "liquid_small_cap": "proxy liquid small cap bucket with explicit liquidity warning gates",
        "high_beta_growth": "proxy high beta growth bucket separated from defensive/core names",
        "defensive_quality": "proxy defensive quality bucket separated from high beta growth",
        "sector_leaders": "proxy sector leadership bucket for relative strength research",
        ETF_MACRO_BUCKET: "ETF macro/regime bucket; never mixed with stock buckets",
    }
    return reasons.get(bucket, "unsupported bucket")


def _market_cap_bucket(bucket: str, product_class: str) -> str:
    if product_class == "etf" or bucket == ETF_MACRO_BUCKET:
        return "etf_macro_not_equity_market_cap"
    mapping = {
        "mega_large_cap": "mega_large_cap_proxy",
        "large_cap_core": "large_cap_proxy",
        "liquid_mid_cap": "mid_cap_proxy",
        "liquid_small_cap": "small_cap_proxy",
        "high_beta_growth": "growth_proxy_mixed_cap",
        "defensive_quality": "quality_proxy_mixed_cap",
        "sector_leaders": "sector_leader_proxy_mixed_cap",
    }
    return mapping.get(bucket, "unknown_proxy")


def _liquidity_bucket(liquidity_score: float) -> str:
    if liquidity_score >= 0.80:
        return "high_liquidity_proxy"
    if liquidity_score >= 0.50:
        return "medium_liquidity_proxy"
    if liquidity_score >= 0.25:
        return "low_liquidity_proxy_warning"
    return "illiquid_proxy_rejected"


def _volatility_bucket(beta_score: float, bucket: str) -> str:
    if bucket == "high_beta_growth" or beta_score >= 0.80:
        return "high_volatility_proxy"
    if bucket == "defensive_quality" or beta_score <= 0.40:
        return "low_volatility_proxy"
    return "medium_volatility_proxy"


def _avg_dollar_volume_proxy(bucket: str, liquidity_score: float) -> float:
    anchors = {
        "mega_large_cap": 500_000_000.0,
        "large_cap_core": 250_000_000.0,
        "liquid_mid_cap": 75_000_000.0,
        "liquid_small_cap": 20_000_000.0,
        "high_beta_growth": 100_000_000.0,
        "defensive_quality": 120_000_000.0,
        "sector_leaders": 160_000_000.0,
        ETF_MACRO_BUCKET: 400_000_000.0,
    }
    return round(anchors.get(bucket, 10_000_000.0) * max(0.0, liquidity_score), 2)


def _avg_spread_proxy(liquidity_score: float) -> float:
    return round(max(2.0, 100.0 * (1.0 - max(0.0, min(1.0, liquidity_score)))), 4)


def _score(
    *,
    bucket: str,
    priority: float,
    liquidity_score: float,
    quality_score: float,
    beta_score: float,
) -> float:
    priority_score = 1.0 - min(max(priority, 0.0), 100.0) / 100.0
    if bucket == "high_beta_growth":
        weights = (0.34, 0.16, 0.40, 0.10)
    elif bucket == "defensive_quality":
        weights = (0.28, 0.52, 0.08, 0.12)
    elif bucket == ETF_MACRO_BUCKET:
        weights = (0.58, 0.22, 0.10, 0.10)
    else:
        weights = (0.42, 0.34, 0.12, 0.12)
    return (
        liquidity_score * weights[0]
        + quality_score * weights[1]
        + beta_score * weights[2]
        + priority_score * weights[3]
    )


def _rotation_hash(symbol: str, salt: str) -> str:
    return blake2b(f"{salt}|{symbol}".encode(), digest_size=4).hexdigest()


def _classify_product(symbol: str, row: Mapping[str, Any]) -> str:
    text_values = [_clean_text(row.get("name")), _clean_text(row.get("notes") or row.get("note"))]
    for field in _PRODUCT_CLASS_FIELDS:
        text_values.append(_clean_text(row.get(field)))
    normalized_values = {_normalize_product_value(value) for value in text_values if value}
    if symbol in _ETF_SYMBOLS or normalized_values.intersection(_ETF_PRODUCT_VALUES):
        return "etf"
    combined_text = f" {' '.join(value.lower().replace('_', ' ') for value in text_values)} "
    combined_text = " ".join(combined_text.split())
    padded_text = f" {combined_text} "
    if any(hint in padded_text for hint in _ETF_HINTS):
        return "etf"
    if normalized_values.intersection(_STOCK_PRODUCT_VALUES):
        return "adr" if "adr" in normalized_values else "common_stock"
    if any(hint in padded_text for hint in _ADR_HINTS):
        return "adr"
    if symbol.isalpha() and 1 <= len(symbol) <= 5:
        return "common_stock"
    return "unknown"


def _normalize_product_value(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return str(value)
    return value


DEFAULT_CANDIDATES: tuple[dict[str, Any], ...] = (
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "bucket": "mega_large_cap",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 1,
    },
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "bucket": "mega_large_cap",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 2,
        "beta_score": 0.82,
    },
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "bucket": "mega_large_cap",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 3,
    },
    {
        "symbol": "AMZN",
        "name": "Amazon.com Inc.",
        "bucket": "mega_large_cap",
        "sector": "Consumer Discretionary",
        "product_type": "STK",
        "priority": 4,
        "beta_score": 0.70,
    },
    {
        "symbol": "JPM",
        "name": "JPMorgan Chase & Co.",
        "bucket": "large_cap_core",
        "sector": "Financials",
        "product_type": "STK",
        "priority": 1,
    },
    {
        "symbol": "V",
        "name": "Visa Inc.",
        "bucket": "large_cap_core",
        "sector": "Financials",
        "product_type": "STK",
        "priority": 2,
    },
    {
        "symbol": "COST",
        "name": "Costco Wholesale Corporation",
        "bucket": "large_cap_core",
        "sector": "Consumer Staples",
        "product_type": "STK",
        "priority": 3,
    },
    {
        "symbol": "HD",
        "name": "The Home Depot Inc.",
        "bucket": "large_cap_core",
        "sector": "Consumer Discretionary",
        "product_type": "STK",
        "priority": 4,
    },
    {
        "symbol": "NET",
        "name": "Cloudflare Inc.",
        "bucket": "liquid_mid_cap",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 1,
        "beta_score": 0.86,
    },
    {
        "symbol": "DDOG",
        "name": "Datadog Inc.",
        "bucket": "liquid_mid_cap",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 2,
        "beta_score": 0.84,
    },
    {
        "symbol": "DOCU",
        "name": "DocuSign Inc.",
        "bucket": "liquid_mid_cap",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 3,
        "beta_score": 0.78,
    },
    {
        "symbol": "ROKU",
        "name": "Roku Inc.",
        "bucket": "liquid_mid_cap",
        "sector": "Communication Services",
        "product_type": "STK",
        "priority": 4,
        "beta_score": 0.88,
    },
    {
        "symbol": "CELH",
        "name": "Celsius Holdings Inc.",
        "bucket": "liquid_small_cap",
        "sector": "Consumer Staples",
        "product_type": "STK",
        "priority": 1,
        "beta_score": 0.82,
    },
    {
        "symbol": "RUN",
        "name": "Sunrun Inc.",
        "bucket": "liquid_small_cap",
        "sector": "Consumer Discretionary",
        "product_type": "STK",
        "priority": 2,
        "beta_score": 0.92,
    },
    {
        "symbol": "RIOT",
        "name": "Riot Platforms Inc.",
        "bucket": "liquid_small_cap",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 3,
        "beta_score": 0.96,
    },
    {
        "symbol": "AA",
        "name": "Alcoa Corporation",
        "bucket": "liquid_small_cap",
        "sector": "Materials",
        "product_type": "STK",
        "priority": 4,
        "beta_score": 0.74,
    },
    {
        "symbol": "TSLA",
        "name": "Tesla Inc.",
        "bucket": "high_beta_growth",
        "sector": "Consumer Discretionary",
        "product_type": "STK",
        "priority": 1,
        "liquidity_score": 0.96,
        "beta_score": 0.98,
    },
    {
        "symbol": "PLTR",
        "name": "Palantir Technologies Inc.",
        "bucket": "high_beta_growth",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 2,
        "liquidity_score": 0.92,
        "beta_score": 0.95,
    },
    {
        "symbol": "COIN",
        "name": "Coinbase Global Inc.",
        "bucket": "high_beta_growth",
        "sector": "Financials",
        "product_type": "STK",
        "priority": 3,
        "liquidity_score": 0.90,
        "beta_score": 0.98,
    },
    {
        "symbol": "RBLX",
        "name": "Roblox Corporation",
        "bucket": "high_beta_growth",
        "sector": "Communication Services",
        "product_type": "STK",
        "priority": 4,
        "liquidity_score": 0.82,
        "beta_score": 0.91,
    },
    {
        "symbol": "PG",
        "name": "Procter & Gamble Company",
        "bucket": "defensive_quality",
        "sector": "Consumer Staples",
        "product_type": "STK",
        "priority": 1,
        "quality_score": 0.96,
    },
    {
        "symbol": "KO",
        "name": "The Coca-Cola Company",
        "bucket": "defensive_quality",
        "sector": "Consumer Staples",
        "product_type": "STK",
        "priority": 2,
        "quality_score": 0.94,
    },
    {
        "symbol": "JNJ",
        "name": "Johnson & Johnson",
        "bucket": "defensive_quality",
        "sector": "Health Care",
        "product_type": "STK",
        "priority": 3,
        "quality_score": 0.92,
    },
    {
        "symbol": "WMT",
        "name": "Walmart Inc.",
        "bucket": "defensive_quality",
        "sector": "Consumer Staples",
        "product_type": "STK",
        "priority": 4,
        "quality_score": 0.90,
    },
    {
        "symbol": "LLY",
        "name": "Eli Lilly and Company",
        "bucket": "sector_leaders",
        "sector": "Health Care",
        "product_type": "STK",
        "priority": 1,
    },
    {
        "symbol": "AVGO",
        "name": "Broadcom Inc.",
        "bucket": "sector_leaders",
        "sector": "Technology",
        "product_type": "STK",
        "priority": 2,
    },
    {
        "symbol": "XOM",
        "name": "Exxon Mobil Corporation",
        "bucket": "sector_leaders",
        "sector": "Energy",
        "product_type": "STK",
        "priority": 3,
    },
    {
        "symbol": "CAT",
        "name": "Caterpillar Inc.",
        "bucket": "sector_leaders",
        "sector": "Industrials",
        "product_type": "STK",
        "priority": 4,
    },
    {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "bucket": ETF_MACRO_BUCKET,
        "sector": "Macro",
        "product_type": "ETF",
        "priority": 1,
    },
    {
        "symbol": "QQQ",
        "name": "Invesco QQQ Trust ETF",
        "bucket": ETF_MACRO_BUCKET,
        "sector": "Macro",
        "product_type": "ETF",
        "priority": 2,
    },
    {
        "symbol": "IWM",
        "name": "iShares Russell 2000 ETF",
        "bucket": ETF_MACRO_BUCKET,
        "sector": "Macro",
        "product_type": "ETF",
        "priority": 3,
    },
    {
        "symbol": "TLT",
        "name": "iShares 20+ Year Treasury Bond ETF",
        "bucket": ETF_MACRO_BUCKET,
        "sector": "Macro",
        "product_type": "ETF",
        "priority": 4,
    },
    {
        "symbol": "GLD",
        "name": "SPDR Gold Shares ETF",
        "bucket": ETF_MACRO_BUCKET,
        "sector": "Macro",
        "product_type": "ETF",
        "priority": 5,
    },
    {
        "symbol": "XLE",
        "name": "Energy Select Sector SPDR Fund",
        "bucket": ETF_MACRO_BUCKET,
        "sector": "Macro",
        "product_type": "ETF",
        "priority": 6,
    },
)
