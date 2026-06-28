from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import blake2b
import json
import math
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from tradeo.core.config import Settings, get_settings
from tradeo.services.data_provider import MarketDataProvider, load_universe, normalize_ohlcv
from tradeo.services.provider_factory import get_market_data_provider

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
    ) -> IntradayUniverseBuildResult:
        thresholds = thresholds or IntradayUniverseThresholds()
        rotation_salt = rotation_salt or datetime.now(UTC).strftime("%Y-%m-%d")
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
            )
            for candidate in candidates
        ]
        selected = self._select(scored, limit=limit, thresholds=thresholds)
        selected_keys = {row["symbol"] for row in selected}
        for row in scored:
            row["selected"] = row["symbol"] in selected_keys
            row["status"] = "selected" if row["selected"] else row["status"]
        selected_rank = {row["symbol"]: idx + 1 for idx, row in enumerate(selected)}
        for row in scored:
            row["rank"] = selected_rank.get(row["symbol"], 0)

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        metadata_path = output.with_suffix(".metadata.json")
        columns = self._output_columns()
        pd.DataFrame(scored).sort_values(
            ["selected", "rank", "score", "symbol"], ascending=[False, True, False, True]
        )[columns].to_csv(output, index=False)
        metadata = self._metadata(
            seed_files=seed_files,
            output_path=output,
            period=period,
            interval=interval,
            limit=limit,
            thresholds=thresholds,
            cache_refresh_enabled=cache_refresh_enabled,
            rotation_salt=rotation_salt,
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
            df = load_universe(str(path))
            for row in df.to_dict(orient="records"):
                symbol = str(row.get("symbol") or "").upper().strip()
                if not symbol:
                    continue
                existing = by_symbol.get(symbol)
                source = str(path)
                if existing is not None:
                    existing.source = ",".join(sorted(set(existing.source.split(",") + [source])))
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
    ) -> dict[str, Any]:
        base = {
            "symbol": candidate.symbol,
            "name": candidate.name,
            "cap_segment": candidate.cap_segment,
            "sector": candidate.sector,
            "note": candidate.note,
            "source": candidate.source,
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
            return {**base, "reason_codes": f"data_unavailable:{type(exc).__name__}", "error": str(exc)[:240]}
        metrics = self._metrics(df)
        reasons = self._rejection_reasons(metrics, candidate, thresholds)
        score = self._score(metrics, candidate, thresholds)
        status = "eligible" if not reasons else "rejected"
        return {
            **base,
            **metrics,
            "status": status,
            "reason_codes": ";".join(reasons),
            "score": round(score, 6),
        }

    def _metrics(self, df: pd.DataFrame) -> dict[str, Any]:
        if df.empty:
            return {"rows": 0}
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
        spread_score = 1.0 - min(1.0, float(metrics.get("spread_proxy_bps") or 0.0) / max(thresholds.max_spread_proxy_bps, 1.0))
        zero_score = 1.0 - min(1.0, float(metrics.get("zero_volume_pct") or 0.0) / max(thresholds.max_zero_volume_pct, 1e-6))
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

    def _metadata(
        self,
        **kwargs: Any,
    ) -> dict[str, Any]:
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
                key: (str(value) if isinstance(value, Path) else value)
                for key, value in kwargs.items()
                if key != "thresholds"
            },
            "thresholds": kwargs["thresholds"].__dict__,
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
        digest = blake2b(f"{salt}|{symbol}".encode(), digest_size=4).hexdigest()
        return digest

    @staticmethod
    def _rotation_jitter(symbol: str) -> float:
        digest = blake2b(symbol.encode(), digest_size=2).hexdigest()
        return int(digest, 16) / 65535.0

    @staticmethod
    def _bucket(row: dict[str, Any]) -> str:
        return str(row.get("sector") or row.get("cap_segment") or "unknown").strip().lower() or "unknown"
