from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from hashlib import blake2b
import json
import math
from pathlib import Path
from typing import Any, Literal, Protocol

import pandas as pd

from tradeo.core.config import Settings, get_settings
from tradeo.services.data_provider import MarketDataProvider, normalize_ohlcv
from tradeo.services.provider_factory import get_market_data_provider

ProductPolicy = Literal["stock_only", "all", "etf_macro"]

_EVENT_RISK_KEYWORDS = (
    "biopharma",
    "biotech",
    "pharma",
    "pharmaceutical",
    "therapeutics",
    "oncology",
    "clinical",
    "acquisition",
    "spac",
    "warrant",
)

_PRODUCT_FLAG_ORDER = ("etf", "fund", "leveraged", "inverse", "crypto", "commodity", "country", "adr")
_PRODUCT_POLICY_BLOCKED_FLAGS = (
    "leveraged",
    "inverse",
    "crypto",
    "commodity",
    "country",
    "etf",
    " fund ",
)
_PRODUCT_CLASS_FIELDS = (
    "product_class",
    "asset_class",
    "asset_type",
    "instrument",
    "instrument_type",
    "security_type",
    "sec_type",
    "sectype",
    "quote_type",
    "quotetype",
    "type",
)
_PRODUCT_FLAG_FIELDS = (
    "product_flags",
    "asset_flags",
    "instrument_flags",
    "tags",
    "leveraged",
    "inverse",
)
_STOCK_PRODUCT_VALUES = {
    "adr",
    "ads",
    "common stock",
    "common_stock",
    "equity",
    "ordinary share",
    "ordinary_share",
    "share",
    "stock",
    "stk",
}
_PRODUCT_VALUE_FLAGS = {
    "closed end fund": ("fund",),
    "closed_end_fund": ("fund",),
    "commodity": ("commodity",),
    "commodity etf": ("etf", "commodity"),
    "commodity_etf": ("etf", "commodity"),
    "country": ("country",),
    "country etf": ("etf", "country"),
    "country_etf": ("etf", "country"),
    "crypto": ("crypto",),
    "crypto etf": ("etf", "crypto"),
    "crypto_etf": ("etf", "crypto"),
    "etf": ("etf",),
    "etn": ("etf",),
    "etp": ("etf",),
    "exchange traded fund": ("etf",),
    "exchange traded note": ("etf",),
    "exchange traded product": ("etf",),
    "exchange_traded_fund": ("etf",),
    "exchange_traded_note": ("etf",),
    "exchange_traded_product": ("etf",),
    "fund": ("fund",),
    "inverse": ("inverse",),
    "inverse etf": ("etf", "inverse"),
    "inverse_etf": ("etf", "inverse"),
    "leveraged": ("leveraged",),
    "leveraged etf": ("etf", "leveraged"),
    "leveraged_etf": ("etf", "leveraged"),
    "mutual fund": ("fund",),
    "mutual_fund": ("fund",),
}

_LEVERAGED_INVERSE_SYMBOLS = {
    "AGQ",
    "AAPD",
    "AAPU",
    "AMDD",
    "AMDL",
    "AMZD",
    "AMZU",
    "ARKD",
    "ARKU",
    "BERZ",
    "BITX",
    "BOIL",
    "BULZ",
    "CONL",
    "CURE",
    "DPST",
    "DRIP",
    "DRN",
    "DRV",
    "DUST",
    "ERX",
    "ERY",
    "FAS",
    "FAZ",
    "FNGD",
    "FNGU",
    "GDXD",
    "GDXU",
    "GGLL",
    "GGLS",
    "HIBL",
    "HIBS",
    "KOLD",
    "KORU",
    "LABD",
    "LABU",
    "METD",
    "METU",
    "MSFD",
    "MSFU",
    "MUU",
    "MSTU",
    "MSTZ",
    "NUGT",
    "NVDD",
    "NVDL",
    "NVDQ",
    "QID",
    "QLD",
    "RETL",
    "SDS",
    "SH",
    "SNDQ",
    "SNXX",
    "SOXL",
    "SOXS",
    "SPUU",
    "SPXL",
    "SPXS",
    "SPXU",
    "SQQQ",
    "SSO",
    "TBT",
    "TECL",
    "TECS",
    "TNA",
    "TQQQ",
    "TSLL",
    "TSLQ",
    "TSLS",
    "TZA",
    "UPRO",
    "UVXY",
    "WEBL",
    "WEBS",
    "YANG",
    "YINN",
    "ZSL",
}
_INVERSE_SYMBOLS = {
    "AAPD",
    "AMDD",
    "AMZD",
    "ARKD",
    "BERZ",
    "BITI",
    "DOG",
    "DRIP",
    "DRV",
    "DUST",
    "ERY",
    "FAZ",
    "FNGD",
    "GDXD",
    "GGLS",
    "KOLD",
    "LABD",
    "METD",
    "MSFD",
    "MUD",
    "MSTZ",
    "NVDD",
    "NVDQ",
    "PSQ",
    "QID",
    "SARK",
    "SDS",
    "SH",
    "SNDQ",
    "SOXS",
    "SPXS",
    "SPXU",
    "SQQQ",
    "TBT",
    "TECS",
    "TSLQ",
    "TSLS",
    "TZA",
    "WEBS",
    "YANG",
    "ZSL",
}
_CRYPTO_ETP_SYMBOLS = {
    "ARKB",
    "BITB",
    "BITI",
    "BITO",
    "BITS",
    "BITW",
    "BITX",
    "BLOK",
    "BRRR",
    "BTF",
    "BTCO",
    "BTCW",
    "DEFI",
    "ETHE",
    "ETHA",
    "EZBC",
    "FBTC",
    "GBTC",
    "HODL",
    "IBIT",
    "WGMI",
    "XBTF",
}
_COMMODITY_ETP_SYMBOLS = {
    "AGQ",
    "BNO",
    "BOIL",
    "CANE",
    "COMT",
    "CORN",
    "CPER",
    "DBA",
    "DBC",
    "GLD",
    "GSG",
    "IAU",
    "KOLD",
    "OILK",
    "PDBC",
    "SGOL",
    "SIVR",
    "SLV",
    "SOYB",
    "UGA",
    "UNG",
    "USL",
    "USO",
    "WEAT",
    "ZSL",
}
_COUNTRY_ETF_SYMBOLS = {
    "ASHR",
    "ECH",
    "EIDO",
    "EIS",
    "ENZL",
    "EPHE",
    "EPI",
    "EPOL",
    "EPU",
    "EWA",
    "EWC",
    "EWG",
    "EWH",
    "EWI",
    "EWJ",
    "EWK",
    "EWL",
    "EWM",
    "EWN",
    "EWP",
    "EWQ",
    "EWS",
    "EWT",
    "EWU",
    "EWW",
    "EWY",
    "EWZ",
    "EZA",
    "FXI",
    "GREK",
    "INDA",
    "KORU",
    "KWEB",
    "MCHI",
    "TUR",
    "VNM",
}
_ETF_SYMBOLS = (
    {
        "AGG",
        "ARKK",
        "BIL",
        "DIA",
        "DRAM",
        "EEM",
        "EFA",
        "GDX",
        "GDXJ",
        "HYG",
        "IEF",
        "IVV",
        "IWM",
        "JNK",
        "JPME",
        "LQD",
        "QQQ",
        "QQQM",
        "SGOV",
        "SHV",
        "SHY",
        "SMH",
        "SOXX",
        "SPCX",
        "SPY",
        "TLT",
        "VTI",
        "VOO",
        "XBI",
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
    | _LEVERAGED_INVERSE_SYMBOLS
    | _CRYPTO_ETP_SYMBOLS
    | _COMMODITY_ETP_SYMBOLS
    | _COUNTRY_ETF_SYMBOLS
)
_ADR_HINTS = (" adr", "american depositary", "depositary receipt", "sponsored adr")
_FUND_HINTS = (
    "direxion",
    "etf",
    "etn",
    "etp",
    "exchange traded fund",
    "exchange-traded fund",
    "exchange traded note",
    "exchange traded product",
    "first trust",
    "fund",
    "global x",
    "graniteshares",
    "invesco",
    "ishares",
    "proshares",
    "rex shares",
    "roundhill",
    "spdr",
    "tradr",
    "vaneck",
    "vanguard",
    "wisdomtree",
    "yieldmax",
)
_LEVERAGED_HINTS = ("2x", "3x", "bull", "daily leveraged", "ultra", "leveraged")
_INVERSE_HINTS = ("bear", "inverse", "short")
_CRYPTO_HINTS = ("bitcoin", "bitwise", "btc", "crypto", "ethereum", "ether")
_COMMODITY_HINTS = ("gold", "silver", "oil", "commodity", "natural gas", "crude")
_COUNTRY_HINTS = ("brazil", "china", "korea", "mexico", "country", "emerging markets")


@dataclass(frozen=True, slots=True)
class IntradayUniverseThresholds:
    min_price: float = 3.0
    min_median_dollar_volume: float = 5_000_000.0
    min_rows: int = 120
    max_zero_volume_pct: float = 0.05
    max_stale_close_run: int = 5
    max_spread_proxy_bps: float = 450.0
    max_event_bar_return_pct: float = 0.35
    max_bucket_pct: float = 0.30


@dataclass(slots=True)
class IntradayUniverseCandidate:
    symbol: str
    name: str = ""
    cap_segment: str = ""
    sector: str = ""
    note: str = ""
    source: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IntradayUniverseBuildResult:
    output_path: Path
    metadata_path: Path
    selected_count: int
    rejected_count: int
    total_candidates: int
    selected_symbols: list[str]
    metadata: dict[str, Any]


class _ProviderFactory(Protocol):
    def __call__(self, *, cache_refresh_enabled: bool | None = None) -> MarketDataProvider: ...


@dataclass(slots=True)
class IntradayUniverseBuilder:
    """Build a liquid, auditable intraday research universe.

    The builder intentionally does not promote patterns or touch trading state. It
    converts candidate symbol lists into a scored universe using recent OHLCV
    quality/liquidity metrics, then writes a CSV that can be fed into
    TRADEO_INTRADAY_UNIVERSE_FILE.
    """

    settings: Settings | None = None
    provider_factory: _ProviderFactory = get_market_data_provider

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def build(
        self,
        *,
        seed_files: list[str | Path],
        output_path: str | Path,
        limit: int,
        period: str = "60d",
        interval: str = "30m",
        thresholds: IntradayUniverseThresholds | None = None,
        cache_refresh_enabled: bool = False,
        rotation_salt: str | None = None,
        product_policy: str = "stock_only",
        include_funds: bool = False,
    ) -> IntradayUniverseBuildResult:
        thresholds = thresholds or IntradayUniverseThresholds()
        rotation_salt = rotation_salt or datetime.now(UTC).strftime("%Y-%m-%d")
        product_policy = self._normalize_product_policy(product_policy, include_funds=include_funds)
        candidates = self._load_candidates(seed_files)
        provider = self.provider_factory(cache_refresh_enabled=cache_refresh_enabled)
        scored = [
            self._score_candidate(
                candidate,
                provider=provider,
                period=period,
                interval=interval,
                thresholds=thresholds,
                rotation_salt=rotation_salt,
                product_policy=product_policy,
            )
            for candidate in candidates
        ]
        selected = self._select(scored, limit=limit, thresholds=thresholds)
        selected_keys = {row["symbol"] for row in selected}
        selected_rank = {row["symbol"]: idx + 1 for idx, row in enumerate(selected)}
        for row in scored:
            row["selected"] = row["symbol"] in selected_keys
            row["status"] = "selected" if row["selected"] else row["status"]
            row["rank"] = selected_rank.get(row["symbol"], 0)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        metadata_path = output.with_suffix(".metadata.json")
        pd.DataFrame(scored).sort_values(
            ["selected", "rank", "score", "symbol"],
            ascending=[False, True, False, True],
        )[self._output_columns()].to_csv(output, index=False)

        metadata = self._metadata(
            seed_files=seed_files,
            output_path=output,
            period=period,
            interval=interval,
            limit=limit,
            thresholds=thresholds,
            cache_refresh_enabled=cache_refresh_enabled,
            rotation_salt=rotation_salt,
            product_policy=product_policy,
            scored=scored,
            selected=selected,
        )
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        return IntradayUniverseBuildResult(
            output_path=output,
            metadata_path=metadata_path,
            selected_count=len(selected),
            rejected_count=len(scored) - len(selected),
            total_candidates=len(scored),
            selected_symbols=[row["symbol"] for row in selected],
            metadata=metadata,
        )

    def _load_candidates(self, seed_files: list[str | Path]) -> list[IntradayUniverseCandidate]:
        by_symbol: dict[str, IntradayUniverseCandidate] = {}
        for raw_path in seed_files:
            path = Path(raw_path)
            if not path.exists():
                continue
            df = pd.read_csv(path)
            if "symbol" not in df.columns:
                raise ValueError(f"Universe CSV must include a 'symbol' column: {path}")
            df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
            df = df[df["symbol"].str.len() > 0].drop_duplicates("symbol")
            for row in df.to_dict(orient="records"):
                symbol = str(row.get("symbol") or "").upper().strip()
                if not symbol:
                    continue
                source = str(path)
                existing = by_symbol.get(symbol)
                if existing is not None:
                    existing.source = ",".join(
                        sorted({item for item in existing.source.split(",") if item} | {source})
                    )
                    continue
                by_symbol[symbol] = IntradayUniverseCandidate(
                    symbol=symbol,
                    name=str(row.get("name") or ""),
                    cap_segment=str(row.get("cap_segment") or ""),
                    sector=str(row.get("sector") or ""),
                    note=str(row.get("note") or ""),
                    source=source,
                    raw=row,
                )
        return sorted(by_symbol.values(), key=lambda item: item.symbol)

    def _score_candidate(
        self,
        candidate: IntradayUniverseCandidate,
        *,
        provider: MarketDataProvider,
        period: str,
        interval: str,
        thresholds: IntradayUniverseThresholds,
        rotation_salt: str,
        product_policy: ProductPolicy,
    ) -> dict[str, Any]:
        product = self._classify_product(candidate)
        product_rejection_reason = self._product_rejection_reason(
            product["product_class"],
            product_policy,
        )
        base = {
            "symbol": candidate.symbol,
            "name": candidate.name,
            "cap_segment": candidate.cap_segment,
            "sector": candidate.sector,
            "note": candidate.note,
            "source": candidate.source,
            "product_class": product["product_class"],
            "product_flags": ";".join(product["product_flags"]),
            "product_rejection_reason": product_rejection_reason,
            "period": period,
            "interval": interval,
            "selected": False,
            "rank": 0,
            "status": "rejected",
            "reason_codes": "",
            "score": 0.0,
            "rotation_hash": self._rotation_hash(candidate.symbol, rotation_salt),
        }
        try:
            df = normalize_ohlcv(provider.fetch_ohlcv(candidate.symbol, period=period, interval=interval))
        except Exception as exc:  # noqa: BLE001 - report per-symbol data failures, keep building.
            reason_codes = [f"data_unavailable:{type(exc).__name__}"]
            if product_rejection_reason:
                reason_codes.append(product_rejection_reason)
            return {
                **base,
                "reason_codes": ";".join(reason_codes),
                "error": str(exc)[:240],
                **self._empty_metrics(),
            }
        metrics = self._metrics(df)
        reasons = self._rejection_reasons(metrics, candidate, thresholds)
        if product_rejection_reason:
            reasons.append(product_rejection_reason)
        return {
            **base,
            **metrics,
            "status": "eligible" if not reasons else "rejected",
            "reason_codes": ";".join(reasons),
            "score": round(self._score(metrics, candidate, thresholds), 6),
        }

    @staticmethod
    def _empty_metrics() -> dict[str, Any]:
        return {
            "rows": 0,
            "first_timestamp": "",
            "last_timestamp": "",
            "median_close": 0.0,
            "median_dollar_volume": 0.0,
            "avg_dollar_volume": 0.0,
            "zero_volume_pct": 1.0,
            "stale_close_run": 0,
            "max_abs_bar_return_pct": 0.0,
            "median_abs_bar_return_pct": 0.0,
            "spread_proxy_bps": 0.0,
            "p90_spread_proxy_bps": 0.0,
        }

    def _metrics(self, df: pd.DataFrame) -> dict[str, Any]:
        if df.empty:
            return self._empty_metrics()
        close = df["close"].astype(float)
        volume = df["volume"].astype(float) if "volume" in df else pd.Series([0.0] * len(df), index=df.index)
        dollar_volume = close * volume
        high = df["high"].astype(float) if "high" in df else close
        low = df["low"].astype(float) if "low" in df else close
        returns = close.pct_change().replace([math.inf, -math.inf], pd.NA).dropna()
        spread_proxy_bps = ((high - low).abs() / close.abs().clip(lower=1e-9) * 10_000).replace(
            [math.inf, -math.inf], pd.NA
        )
        return {
            "rows": int(len(df)),
            "first_timestamp": str(df.index[0]),
            "last_timestamp": str(df.index[-1]),
            "median_close": round(float(close.median()), 6),
            "median_dollar_volume": round(float(dollar_volume.median()), 2),
            "avg_dollar_volume": round(float(dollar_volume.mean()), 2),
            "zero_volume_pct": round(float((volume <= 0).mean()), 6),
            "stale_close_run": int(self._max_equal_run(close)),
            "max_abs_bar_return_pct": round(float(returns.abs().max() if len(returns) else 0.0), 6),
            "median_abs_bar_return_pct": round(float(returns.abs().median() if len(returns) else 0.0), 6),
            "spread_proxy_bps": round(float(spread_proxy_bps.median(skipna=True) or 0.0), 3),
            "p90_spread_proxy_bps": round(float(spread_proxy_bps.quantile(0.90) if len(spread_proxy_bps) else 0.0), 3),
        }

    def _rejection_reasons(
        self,
        metrics: dict[str, Any],
        candidate: IntradayUniverseCandidate,
        thresholds: IntradayUniverseThresholds,
    ) -> list[str]:
        reasons: list[str] = []
        if int(metrics.get("rows") or 0) < thresholds.min_rows:
            reasons.append("insufficient_rows")
        if float(metrics.get("median_close") or 0.0) < thresholds.min_price:
            reasons.append("price_below_min")
        if float(metrics.get("median_dollar_volume") or 0.0) < thresholds.min_median_dollar_volume:
            reasons.append("dollar_volume_below_min")
        if float(metrics.get("zero_volume_pct") or 0.0) > thresholds.max_zero_volume_pct:
            reasons.append("zero_volume_high")
        if int(metrics.get("stale_close_run") or 0) > thresholds.max_stale_close_run:
            reasons.append("stale_close_run_high")
        if float(metrics.get("spread_proxy_bps") or 0.0) > thresholds.max_spread_proxy_bps:
            reasons.append("spread_proxy_high")
        if float(metrics.get("max_abs_bar_return_pct") or 0.0) > thresholds.max_event_bar_return_pct:
            reasons.append("event_bar_return_high")
        if self._event_keyword_score(candidate) >= 1.0:
            reasons.append("event_driven_keyword")
        return reasons

    def _score(
        self,
        metrics: dict[str, Any],
        candidate: IntradayUniverseCandidate,
        thresholds: IntradayUniverseThresholds,
    ) -> float:
        rows_score = min(1.0, float(metrics.get("rows") or 0) / max(thresholds.min_rows * 2, 1))
        price_score = min(1.0, max(0.0, float(metrics.get("median_close") or 0.0) / 30.0))
        dv = max(float(metrics.get("median_dollar_volume") or 0.0), 1.0)
        dv_score = min(1.0, math.log10(dv) / 8.0)
        spread_score = 1.0 - min(
            1.0, float(metrics.get("spread_proxy_bps") or 0.0) / max(thresholds.max_spread_proxy_bps, 1.0)
        )
        zero_score = 1.0 - min(
            1.0, float(metrics.get("zero_volume_pct") or 0.0) / max(thresholds.max_zero_volume_pct, 1e-6)
        )
        event_penalty = min(0.35, self._event_keyword_score(candidate) * 0.15)
        return max(
            0.0,
            rows_score * 0.18
            + price_score * 0.10
            + dv_score * 0.34
            + spread_score * 0.20
            + zero_score * 0.10
            + self._rotation_jitter(candidate.symbol) * 0.08
            - event_penalty,
        )

    def _select(
        self,
        scored: list[dict[str, Any]],
        *,
        limit: int,
        thresholds: IntradayUniverseThresholds,
    ) -> list[dict[str, Any]]:
        eligible = [row for row in scored if row.get("status") == "eligible"]
        eligible.sort(key=lambda row: (-float(row.get("score") or 0.0), str(row.get("symbol") or "")))
        if not eligible or limit <= 0:
            return []
        buckets = {self._bucket(row) for row in eligible}
        if len(buckets) <= 1:
            return eligible[:limit]
        max_per_bucket = max(1, math.ceil(limit * thresholds.max_bucket_pct))
        selected: list[dict[str, Any]] = []
        bucket_counts: dict[str, int] = {}
        for row in eligible:
            bucket = self._bucket(row)
            if bucket_counts.get(bucket, 0) >= max_per_bucket:
                continue
            selected.append(row)
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
            if len(selected) >= limit:
                return selected
        selected_symbols = {row["symbol"] for row in selected}
        for row in eligible:
            if row["symbol"] in selected_symbols:
                continue
            selected.append(row)
            if len(selected) >= limit:
                break
        return selected

    def _metadata(self, **kwargs: Any) -> dict[str, Any]:
        scored = kwargs.pop("scored")
        selected = kwargs.pop("selected")
        reason_counts: dict[str, int] = {}
        for row in scored:
            for reason in str(row.get("reason_codes") or "").split(";"):
                if reason:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
        return {
            "schema_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            **{
                key: ([str(item) for item in value] if key == "seed_files" else str(value) if isinstance(value, Path) else value)
                for key, value in kwargs.items()
                if key != "thresholds"
            },
            "thresholds": asdict(kwargs["thresholds"]),
            "product_policy": kwargs["product_policy"],
            "total_candidates": len(scored),
            "selected_count": len(selected),
            "rejected_count": len(scored) - len(selected),
            "reason_counts": dict(sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))),
            "selected_symbols": [row["symbol"] for row in selected],
        }

    @staticmethod
    def _output_columns() -> list[str]:
        return [
            "symbol",
            "name",
            "cap_segment",
            "sector",
            "source",
            "product_class",
            "product_flags",
            "product_rejection_reason",
            "selected",
            "rank",
            "status",
            "score",
            "reason_codes",
            "period",
            "interval",
            "rows",
            "median_close",
            "median_dollar_volume",
            "avg_dollar_volume",
            "zero_volume_pct",
            "stale_close_run",
            "max_abs_bar_return_pct",
            "median_abs_bar_return_pct",
            "spread_proxy_bps",
            "p90_spread_proxy_bps",
            "first_timestamp",
            "last_timestamp",
            "rotation_hash",
            "note",
        ]

    @staticmethod
    def _max_equal_run(series: pd.Series) -> int:
        max_run = 0
        current = 0
        previous: float | None = None
        for value in series.astype(float):
            if previous is not None and value == previous:
                current += 1
            else:
                current = 1
            previous = value
            max_run = max(max_run, current)
        return max_run

    @staticmethod
    def _event_keyword_score(candidate: IntradayUniverseCandidate) -> float:
        text = " ".join([candidate.name, candidate.note, candidate.cap_segment, candidate.sector]).lower()
        return float(sum(1 for keyword in _EVENT_RISK_KEYWORDS if keyword in text))

    @staticmethod
    def _rotation_hash(symbol: str, salt: str) -> str:
        return blake2b(f"{salt}|{symbol}".encode(), digest_size=4).hexdigest()

    @staticmethod
    def _rotation_jitter(symbol: str) -> float:
        return int(blake2b(symbol.encode(), digest_size=2).hexdigest(), 16) / 65535.0

    @staticmethod
    def _bucket(row: dict[str, Any]) -> str:
        return str(row.get("sector") or row.get("cap_segment") or "unknown").strip().lower() or "unknown"

    @staticmethod
    def _normalize_product_policy(policy: str, *, include_funds: bool = False) -> ProductPolicy:
        if include_funds:
            return "all"
        normalized = str(policy or "stock_only").strip().lower().replace("-", "_")
        if normalized in {"stock", "stocks", "common_stock", "stock_only"}:
            return "stock_only"
        if normalized in {"all", "include_funds"}:
            return "all"
        if normalized in {"etf", "funds", "etf_macro"}:
            return "etf_macro"
        raise ValueError(f"Unsupported product_policy: {policy}")

    @classmethod
    def _classify_product(cls, candidate: IntradayUniverseCandidate) -> dict[str, Any]:
        symbol = candidate.symbol.upper().strip()
        text = cls._candidate_product_text(candidate)
        flags: set[str] = set()
        for value in cls._raw_text_values(candidate.raw, _PRODUCT_CLASS_FIELDS):
            cls._add_product_value_flags(flags, value)
        for value in cls._raw_text_values(candidate.raw, _PRODUCT_FLAG_FIELDS):
            cls._add_product_value_flags(flags, value)

        if symbol in _ETF_SYMBOLS:
            flags.add("etf")
        if symbol in _LEVERAGED_INVERSE_SYMBOLS:
            flags.update({"etf", "leveraged"})
        if symbol in _INVERSE_SYMBOLS:
            flags.update({"etf", "inverse"})
        if symbol in _CRYPTO_ETP_SYMBOLS:
            flags.update({"etf", "crypto"})
        if symbol in _COMMODITY_ETP_SYMBOLS:
            flags.update({"etf", "commodity"})
        if symbol in _COUNTRY_ETF_SYMBOLS:
            flags.update({"etf", "country"})

        if cls._contains_any(text, _FUND_HINTS):
            flags.add("etf")
        product_context = bool(flags.intersection({"etf", "fund"})) or " trust " in text
        if cls._contains_any(text, _LEVERAGED_HINTS):
            flags.add("leveraged")
            if product_context:
                flags.add("etf")
        if product_context and cls._contains_any(text, _INVERSE_HINTS):
            flags.update({"etf", "inverse"})
        if product_context and cls._contains_any(text, _CRYPTO_HINTS):
            flags.update({"etf", "crypto"})
        if product_context and cls._contains_any(text, _COMMODITY_HINTS):
            flags.update({"etf", "commodity"})
        if product_context and cls._contains_any(text, _COUNTRY_HINTS):
            flags.update({"etf", "country"})
        if cls._contains_any(text, _ADR_HINTS):
            flags.add("adr")

        ordered_flags = [flag for flag in _PRODUCT_FLAG_ORDER if flag in flags]
        if "etf" in flags and "inverse" in flags:
            product_class = "inverse_etf"
        elif "etf" in flags and "leveraged" in flags:
            product_class = "leveraged_etf"
        elif "etf" in flags and "crypto" in flags:
            product_class = "crypto_etp"
        elif "etf" in flags and "commodity" in flags:
            product_class = "commodity_etp"
        elif "etf" in flags and "country" in flags:
            product_class = "country_etf"
        elif "etf" in flags:
            product_class = "etf"
        elif "fund" in flags:
            product_class = "etf"
        elif "adr" in flags:
            product_class = "adr"
        elif not symbol.isalpha() or len(symbol) > 5:
            product_class = "unknown"
        else:
            product_class = "common_stock"
        return {"product_class": product_class, "product_flags": ordered_flags}

    @staticmethod
    def _product_rejection_reason(product_class: str, product_policy: ProductPolicy) -> str:
        if product_policy == "all":
            return ""
        stock_classes = {"common_stock", "adr"}
        fund_classes = {"etf", "leveraged_etf", "inverse_etf", "crypto_etp", "commodity_etp", "country_etf"}
        if product_policy == "stock_only" and product_class not in stock_classes:
            return f"product_policy:stock_only_excludes_{product_class}"
        if product_policy == "etf_macro" and product_class not in fund_classes:
            return f"product_policy:etf_macro_excludes_{product_class}"
        return ""

    @staticmethod
    def _candidate_product_text(candidate: IntradayUniverseCandidate) -> str:
        values = [
            candidate.name,
            candidate.note,
            candidate.cap_segment,
            candidate.sector,
            *IntradayUniverseBuilder._raw_text_values(candidate.raw, _PRODUCT_CLASS_FIELDS),
            *IntradayUniverseBuilder._raw_text_values(candidate.raw, _PRODUCT_FLAG_FIELDS),
        ]
        return f" {' '.join(' '.join(_clean_text(value).lower().replace('_', ' ').split()) for value in values)} "

    @staticmethod
    def _raw_text_values(raw: dict[str, Any], names: tuple[str, ...]) -> list[str]:
        columns = {str(name).lower(): name for name in raw}
        values: list[str] = []
        for name in names:
            column = columns.get(name)
            if column is None:
                continue
            text = _clean_text(raw.get(column))
            if text:
                values.append(text)
        return values

    @staticmethod
    def _add_product_value_flags(flags: set[str], value: str) -> None:
        normalized = _normalize_product_value(value)
        if not normalized or normalized in _STOCK_PRODUCT_VALUES:
            return
        mapped = _PRODUCT_VALUE_FLAGS.get(normalized)
        if mapped:
            flags.update(mapped)
            return
        for part in _split_product_flags(normalized):
            mapped = _PRODUCT_VALUE_FLAGS.get(part)
            if mapped:
                flags.update(mapped)
                continue
            for marker, marker_flags in _PRODUCT_VALUE_FLAGS.items():
                if marker in part:
                    flags.update(marker_flags)
                    break

    @staticmethod
    def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
        return any(needle in text for needle in needles)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.lower() in {"", "<na>", "nan", "none", "null"} else text


def _normalize_product_value(value: str) -> str:
    text = _clean_text(value).lower().strip()
    return " ".join(text.replace("-", " ").replace("_", " ").split())


def _split_product_flags(value: str) -> list[str]:
    normalized = value.replace("|", ";").replace(",", ";").replace("/", ";")
    return [" ".join(part.split()) for part in normalized.split(";") if part.strip()]
