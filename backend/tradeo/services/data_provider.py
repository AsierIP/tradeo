from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import Any, Protocol

import pandas as pd

from tradeo.core.config import (
    DAILY_CAP_SEGMENT_CHOICES,
    get_settings,
    normalize_daily_cap_segment_name,
)
from tradeo.services.technical_indicators import normalize_ohlcv


class MarketDataProvider(Protocol):
    def fetch_ohlcv(
        self, symbol: str, period: str = "2y", interval: str = "1d"
    ) -> pd.DataFrame: ...


_DAILY_INTERVALS = {"1d", "1day", "1 day", "daily"}
# Bar widths for the intraday intervals the IBKR provider understands; used
# both for completeness masking and for bar-relative refresh gap thresholds.
_INTRADAY_BAR_MINUTES = {
    "1m": 1,
    "1min": 1,
    "1 min": 1,
    "1 mins": 1,
    "5m": 5,
    "5min": 5,
    "5 min": 5,
    "5 mins": 5,
    "15m": 15,
    "15min": 15,
    "15 min": 15,
    "15 mins": 15,
    "30m": 30,
    "30min": 30,
    "30 min": 30,
    "30 mins": 30,
    "1h": 60,
    "60m": 60,
    "60min": 60,
    "60 min": 60,
    "60 mins": 60,
    "1 hour": 60,
}
UNIVERSE_POLICY_STOCK_ONLY = "stock_only"
UNIVERSE_POLICY_ETF_MACRO = "etf_macro"
UNIVERSE_POLICY_CHOICES = (UNIVERSE_POLICY_STOCK_ONLY, UNIVERSE_POLICY_ETF_MACRO)
DEFAULT_DAILY_CAP_SEGMENT = "mid"
DAILY_UNIVERSE_SCOPE_BY_CAP_SEGMENT = {
    "mega": "daily_megacap",
    "large": "daily_largecap",
    "mid": "daily_midcap",
}
DAILY_UNIVERSE_FILE_ATTR_BY_CAP_SEGMENT = {
    "mega": "daily_mega_universe_file",
    "large": "daily_large_universe_file",
    "mid": "daily_mid_universe_file",
}
_CACHE_PATH_LOCKS_GUARD = Lock()
_CACHE_PATH_LOCKS: dict[Path, Lock] = {}
_UPSTREAM_FETCH_SEMAPHORE_GUARD = Lock()
_UPSTREAM_FETCH_SEMAPHORE: BoundedSemaphore | None = None
_UPSTREAM_FETCH_SEMAPHORE_LIMIT = 0


def _normalized_interval_key(interval: str) -> str:
    return " ".join(str(interval).strip().lower().split())


def _cache_path_lock(path: Path) -> Lock:
    resolved = path.resolve()
    with _CACHE_PATH_LOCKS_GUARD:
        lock = _CACHE_PATH_LOCKS.get(resolved)
        if lock is None:
            lock = Lock()
            _CACHE_PATH_LOCKS[resolved] = lock
        return lock


def _upstream_fetch_semaphore(limit: int) -> BoundedSemaphore:
    global _UPSTREAM_FETCH_SEMAPHORE, _UPSTREAM_FETCH_SEMAPHORE_LIMIT
    safe_limit = max(1, int(limit or 1))
    with _UPSTREAM_FETCH_SEMAPHORE_GUARD:
        if _UPSTREAM_FETCH_SEMAPHORE is None or _UPSTREAM_FETCH_SEMAPHORE_LIMIT != safe_limit:
            _UPSTREAM_FETCH_SEMAPHORE = BoundedSemaphore(safe_limit)
            _UPSTREAM_FETCH_SEMAPHORE_LIMIT = safe_limit
        return _UPSTREAM_FETCH_SEMAPHORE


def is_daily_interval(interval: str | None) -> bool:
    return _normalized_interval_key(interval or "1d") in _DAILY_INTERVALS


def normalize_universe_policy(value: str | None) -> str:
    policy = str(value or UNIVERSE_POLICY_STOCK_ONLY).strip().lower()
    if policy not in UNIVERSE_POLICY_CHOICES:
        raise ValueError(
            f"unknown universe policy: {value!r}; expected one of "
            f"{','.join(UNIVERSE_POLICY_CHOICES)}"
        )
    return policy


def normalize_daily_cap_segment(value: str | None) -> str:
    key = normalize_daily_cap_segment_name(value, default=DEFAULT_DAILY_CAP_SEGMENT)
    if key not in DAILY_CAP_SEGMENT_CHOICES:
        raise ValueError(
            f"unknown daily cap segment: {value!r}; expected one of "
            f"{','.join(DAILY_CAP_SEGMENT_CHOICES)}"
        )
    return key


def daily_universe_file_for_segment(settings: Any, daily_cap_segment: str | None = None) -> str:
    segment = normalize_daily_cap_segment(
        daily_cap_segment
        if daily_cap_segment is not None
        else getattr(settings, "daily_universe_cap_segment", DEFAULT_DAILY_CAP_SEGMENT)
    )
    segment_file = str(
        getattr(settings, DAILY_UNIVERSE_FILE_ATTR_BY_CAP_SEGMENT[segment], "") or ""
    ).strip()
    if segment_file:
        return segment_file
    if segment == DEFAULT_DAILY_CAP_SEGMENT:
        return str(getattr(settings, "daily_universe_file", settings.universe_file))
    raise ValueError(
        f"daily {segment} universe file is not configured; set "
        f"TRADEO_{DAILY_UNIVERSE_FILE_ATTR_BY_CAP_SEGMENT[segment].upper()}"
    )


@dataclass(frozen=True)
class UniverseSelection:
    scope: str
    universe_file: str
    universe_policy: str
    daily_cap_segment: str | None = None


def universe_scope_for_interval(
    interval: str | None,
    universe_policy: str | None = None,
    *,
    daily_cap_segment: str | None = None,
) -> str:
    if is_daily_interval(interval):
        segment = normalize_daily_cap_segment(daily_cap_segment)
        scope = DAILY_UNIVERSE_SCOPE_BY_CAP_SEGMENT[segment]
    else:
        scope = "intraday_smallcap"
    policy = normalize_universe_policy(universe_policy)
    return scope if policy == UNIVERSE_POLICY_STOCK_ONLY else f"{scope}_{policy}"


def universe_file_for_interval(
    settings: Any,
    interval: str | None,
    universe_policy: str | None = None,
    *,
    daily_cap_segment: str | None = None,
) -> str:
    normalize_universe_policy(
        universe_policy
        or getattr(settings, "intraday_universe_policy", UNIVERSE_POLICY_STOCK_ONLY)
    )
    if is_daily_interval(interval):
        return daily_universe_file_for_segment(settings, daily_cap_segment=daily_cap_segment)
    return str(getattr(settings, "intraday_universe_file", settings.universe_file))


def resolve_universe_for_interval(
    settings: Any,
    interval: str | None,
    universe_policy: str | None = None,
    *,
    daily_cap_segment: str | None = None,
) -> UniverseSelection:
    policy = normalize_universe_policy(
        universe_policy
        or getattr(settings, "intraday_universe_policy", UNIVERSE_POLICY_STOCK_ONLY)
    )
    is_daily = is_daily_interval(interval)
    segment = (
        normalize_daily_cap_segment(
            daily_cap_segment
            or getattr(settings, "daily_universe_cap_segment", DEFAULT_DAILY_CAP_SEGMENT)
        )
        if is_daily
        else None
    )
    return UniverseSelection(
        scope=universe_scope_for_interval(
            interval,
            universe_policy=policy,
            daily_cap_segment=segment,
        ),
        universe_file=universe_file_for_interval(
            settings,
            interval,
            universe_policy=policy,
            daily_cap_segment=segment,
        ),
        universe_policy=policy,
        daily_cap_segment=segment,
    )


def load_universe(path: str | None = None) -> pd.DataFrame:
    settings = get_settings()
    p = Path(path or settings.universe_file)
    if not p.exists():
        raise FileNotFoundError(f"Universe file not found: {p}")
    df = pd.read_csv(p)
    if "symbol" not in df.columns:
        raise ValueError("Universe CSV must include a 'symbol' column")
    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
    df = df[df["symbol"].str.len() > 0].drop_duplicates("symbol")
    if "selected" in df.columns:
        selected = df["selected"].map(_truthy_universe_selected)
        df = df[selected].copy()
    return df


def _truthy_universe_selected(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y", "on", "selected"}


def pick_symbols(
    limit: int | None = None,
    force_symbols: list[str] | None = None,
    *,
    interval: str | None = None,
    universe_file: str | None = None,
    universe_policy: str | None = None,
    daily_cap_segment: str | None = None,
) -> list[str]:
    if force_symbols:
        return [s.upper().strip() for s in force_symbols if s.strip()]
    settings = get_settings()
    selected_policy = normalize_universe_policy(
        universe_policy
        or getattr(settings, "intraday_universe_policy", UNIVERSE_POLICY_STOCK_ONLY)
    )
    selected_universe = universe_file or universe_file_for_interval(
        settings,
        interval or settings.scan_interval,
        universe_policy=selected_policy,
        daily_cap_segment=daily_cap_segment,
    )
    df = load_universe(selected_universe)
    if limit is not None and int(limit) <= 0:
        return df["symbol"].tolist()
    n = limit or settings.scan_limit_default
    return df["symbol"].head(int(n)).tolist()


@dataclass
class CachedMarketDataProvider:
    upstream: MarketDataProvider | None = None
    cache_dir: Path | None = None
    adjusted: bool | None = None
    what_to_show: str | None = None
    schema_version: int = 1
    incremental_enabled: bool | None = None
    incremental_overlap_bars: int | None = None
    incremental_min_gap_days: int | None = None
    incremental_max_gap_days: int | None = None
    incremental_intraday_enabled: bool | None = None
    incremental_intraday_min_gap_bars: int | None = None
    incremental_intraday_max_gap_days: int | None = None
    upstream_max_concurrency: int | None = None
    cache_only: bool = False

    def __post_init__(self) -> None:
        if self.upstream is None:
            raise ValueError("CachedMarketDataProvider requires an explicit real-data upstream")
        settings = get_settings()
        self.cache_dir = self.cache_dir or settings.market_data_cache_path
        self.adjusted = settings.market_data_adjusted if self.adjusted is None else self.adjusted
        self.what_to_show = self.what_to_show or settings.market_data_what_to_show
        if self.incremental_enabled is None:
            self.incremental_enabled = settings.market_data_incremental_enabled
        if self.incremental_overlap_bars is None:
            self.incremental_overlap_bars = settings.market_data_incremental_overlap_bars
        if self.incremental_min_gap_days is None:
            self.incremental_min_gap_days = settings.market_data_incremental_min_gap_days
        if self.incremental_max_gap_days is None:
            self.incremental_max_gap_days = settings.market_data_incremental_max_gap_days
        if self.incremental_intraday_enabled is None:
            self.incremental_intraday_enabled = settings.market_data_incremental_intraday_enabled
        if self.incremental_intraday_min_gap_bars is None:
            self.incremental_intraday_min_gap_bars = (
                settings.market_data_incremental_intraday_min_gap_bars
            )
        if self.incremental_intraday_max_gap_days is None:
            self.incremental_intraday_max_gap_days = (
                settings.market_data_incremental_intraday_max_gap_days
            )
        if self.upstream_max_concurrency is None:
            self.upstream_max_concurrency = settings.market_data_upstream_max_concurrency
        self._cache: dict[tuple[str, str, str], pd.DataFrame] = {}

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        key = (symbol.upper(), period, interval)
        if key not in self._cache:
            csv_path = self._cache_path(*key)
            with _cache_path_lock(csv_path):
                if key not in self._cache:
                    if csv_path.exists():
                        df = self._read_csv(csv_path)
                        df = self._maybe_refresh(df, key=key, csv_path=csv_path)
                    elif self.cache_only:
                        raise FileNotFoundError(
                            f"Market data cache miss in cache-only mode: {symbol.upper()} "
                            f"{interval} {period}"
                        )
                    else:
                        df = self._full_refetch(key, csv_path, refresh_mode="full_fetch")
                    self._cache[key] = self._complete_bars_only(df)
        return self._cache[key].copy()

    def _full_refetch(
        self,
        key: tuple[str, str, str],
        csv_path: Path,
        *,
        refresh_mode: str,
    ) -> pd.DataFrame:
        symbol, period, interval = key
        assert self.upstream is not None
        with _upstream_fetch_semaphore(int(self.upstream_max_concurrency or 1)):
            df = self.upstream.fetch_ohlcv(symbol, period=period, interval=interval)
        df = self._annotate(df, symbol=symbol, period=period, interval=interval)
        df = self._complete_bars_only(df)
        self._atomic_write(csv_path, df, key=key, refresh_mode=refresh_mode)
        return df

    def _maybe_refresh(
        self,
        cached: pd.DataFrame,
        *,
        key: tuple[str, str, str],
        csv_path: Path,
    ) -> pd.DataFrame:
        """Append the missing tail after verifying overlap bars.

        Adjusted feeds rewrite history on splits/dividends, so an incremental
        append is only trusted when the refetched overlap matches the cached
        bars; otherwise the whole artifact is refetched. Daily gaps are
        measured in calendar days; intraday gaps in bar widths (min) and
        wall-clock days (max), since a weekend gap on a 5m cache is routine.
        """
        symbol, period, interval = key
        interval_lower = _normalized_interval_key(interval)
        is_daily = interval_lower in _DAILY_INTERVALS
        bar_minutes = _INTRADAY_BAR_MINUTES.get(interval_lower)
        if self.cache_only or not self.incremental_enabled or cached.empty:
            return cached
        if not is_daily and (bar_minutes is None or not self.incremental_intraday_enabled):
            return cached
        last_ts = pd.Timestamp(cached.index[-1])
        now = pd.Timestamp(datetime.now(UTC))
        overlap_bars = max(1, int(self.incremental_overlap_bars or 5))
        if is_daily:
            gap_days = self._complete_business_days_since(last_ts, now)
            if gap_days < int(self.incremental_min_gap_days or 1):
                return cached
            gap_too_large = gap_days > int(self.incremental_max_gap_days or 45)
            tail_days = gap_days + overlap_bars * 2 + 4
        else:
            gap = now - self._as_utc(last_ts)
            min_gap_bars = max(1, int(self.incremental_intraday_min_gap_bars or 1))
            if gap < pd.Timedelta(minutes=bar_minutes * min_gap_bars):
                return cached
            gap_too_large = gap > pd.Timedelta(
                days=int(self.incremental_intraday_max_gap_days or 5)
            )
            # +3 days keeps overlap bars in the tail across weekends/holidays.
            tail_days = int(gap.days) + 3
        if gap_too_large:
            try:
                return self._full_refetch(key, csv_path, refresh_mode="full_refetch_gap_too_large")
            except Exception:  # noqa: BLE001 - a warm cache is better than failing a research run.
                self._atomic_write(
                    csv_path, cached, key=key, refresh_mode="stale_cache_full_refetch_failed"
                )
                return cached
        assert self.upstream is not None
        try:
            with _upstream_fetch_semaphore(int(self.upstream_max_concurrency or 1)):
                tail = self.upstream.fetch_ohlcv(symbol, period=f"{tail_days}d", interval=interval)
        except Exception:  # noqa: BLE001 - keep serving the last verified cache during provider outages.
            self._atomic_write(
                csv_path, cached, key=key, refresh_mode="stale_cache_incremental_failed"
            )
            return cached
        tail = self._annotate(tail, symbol=symbol, period=period, interval=interval)
        tail = self._complete_bars_only(tail)
        if not self._overlap_matches(cached, tail, overlap_bars=overlap_bars):
            try:
                return self._full_refetch(
                    key, csv_path, refresh_mode="full_refetch_overlap_mismatch"
                )
            except Exception:  # noqa: BLE001 - retain cache if the repair fetch is unavailable.
                self._atomic_write(
                    csv_path, cached, key=key, refresh_mode="stale_cache_overlap_refetch_failed"
                )
                return cached
        new_rows = tail[pd.DatetimeIndex(tail.index) > last_ts]
        if new_rows.empty:
            return cached
        merged = pd.concat([cached, new_rows[cached.columns.intersection(new_rows.columns)]])
        merged = merged[~merged.index.duplicated(keep="first")].sort_index()
        self._atomic_write(
            csv_path,
            merged,
            key=key,
            refresh_mode="incremental_append",
            rows_appended=int(len(new_rows)),
        )
        return merged

    @staticmethod
    def _overlap_matches(
        cached: pd.DataFrame,
        tail: pd.DataFrame,
        *,
        overlap_bars: int,
        rel_tolerance: float = 1e-4,
    ) -> bool:
        common = cached.index.intersection(tail.index)
        if len(common) == 0:
            return False
        common = common.sort_values()[-overlap_bars:]
        for column in ("open", "close"):
            if column not in cached.columns or column not in tail.columns:
                continue
            cached_values = cached.loc[common, column].astype(float).to_numpy()
            tail_values = tail.loc[common, column].astype(float).to_numpy()
            scale = abs(cached_values).clip(min=1e-9)
            if (abs(cached_values - tail_values) / scale > rel_tolerance).any():
                return False
        return True

    def data_manifest(
        self,
        symbols: list[str] | None = None,
        *,
        period: str | None = None,
        interval: str | None = None,
    ) -> dict[str, Any]:
        """Return a deterministic manifest over cached OHLCV artifacts."""
        assert self.cache_dir is not None
        requested = {s.upper().strip() for s in symbols if s.strip()} if symbols else None
        entries: dict[str, Any] = {}
        if requested and period and interval:
            csv_paths = [self._cache_path(symbol, period, interval) for symbol in sorted(requested)]
        else:
            csv_paths = sorted(self.cache_dir.glob("*.csv"))
        for csv_path in csv_paths:
            if not csv_path.exists():
                continue
            meta_path = csv_path.with_suffix(".metadata.json")
            metadata = self._read_metadata(meta_path)
            symbol = str(metadata.get("symbol") or csv_path.stem.split("_", 1)[0]).upper()
            if requested is not None and symbol not in requested:
                continue
            metadata_period = metadata.get("period")
            metadata_interval = metadata.get("interval")
            if (
                period is not None
                and metadata_period is not None
                and str(metadata_period) != str(period)
            ):
                continue
            if (
                interval is not None
                and metadata_interval is not None
                and str(metadata_interval) != str(interval)
            ):
                continue
            digest = str(metadata.get("sha256") or "") or _sha256_file(csv_path)
            entries[csv_path.stem] = {
                "symbol": symbol,
                "interval": metadata.get("interval"),
                "period": metadata.get("period"),
                "path": str(csv_path),
                "sha256": digest,
                "rows": metadata.get("rows", 0),
                "adjusted": metadata.get("adjusted", self.adjusted),
                "what_to_show": metadata.get("what_to_show", self.what_to_show),
                "bar_complete_column": "bar_complete",
                "provider_boundary": metadata.get("provider_boundary", "period_interval_fetch"),
                "incremental_fetch_supported": metadata.get("incremental_fetch_supported", False),
                "refresh_mode": metadata.get("refresh_mode", "full_fetch"),
                "last_timestamp": metadata.get("last_timestamp", ""),
            }
        payload = {
            "schema_version": self.schema_version,
            "generated_at": datetime.now(UTC).isoformat(),
            "cache_dir": str(self.cache_dir),
            "artifact_format": "canonical_csv",
            "hash_algorithm": "sha256",
            "entries": entries,
        }
        payload["manifest_hash"] = hashlib.sha256(
            json.dumps(
                payload["entries"], sort_keys=True, separators=(",", ":"), default=str
            ).encode()
        ).hexdigest()
        return payload

    def _cache_path(self, symbol: str, period: str, interval: str) -> Path:
        assert self.cache_dir is not None
        safe = "_".join(_safe_part(part) for part in (symbol.upper(), interval, period))
        return self.cache_dir / f"{safe}.csv"

    def _annotate(
        self, df: pd.DataFrame, *, symbol: str, period: str, interval: str
    ) -> pd.DataFrame:
        out = normalize_ohlcv(df)
        out = out.copy()
        out["adjusted"] = bool(self.adjusted)
        out["what_to_show"] = str(self.what_to_show or "")
        out["bar_complete"] = self._bar_complete_mask(out.index, interval)
        return out

    @staticmethod
    def _bar_complete_mask(index: pd.Index, interval: str) -> list[bool]:
        interval_lower = _normalized_interval_key(interval)
        if interval_lower in _DAILY_INTERVALS:
            today = datetime.now(UTC).date()
            return [pd.Timestamp(value).date() < today for value in index]
        bar_minutes = _INTRADAY_BAR_MINUTES.get(interval_lower)
        if bar_minutes is None:
            return [True] * len(index)
        now = pd.Timestamp(datetime.now(UTC))
        width = pd.Timedelta(minutes=bar_minutes)
        return [CachedMarketDataProvider._as_utc(value) + width <= now for value in index]

    @staticmethod
    def _as_utc(value: Any) -> pd.Timestamp:
        # Naive timestamps are treated as UTC; IBKR intraday bars arrive tz-aware.
        ts = pd.Timestamp(value)
        return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")

    @staticmethod
    def _complete_business_days_since(last_ts: pd.Timestamp, now: pd.Timestamp) -> int:
        """Business dates after ``last_ts`` and before today's incomplete daily bar."""
        start = pd.Timestamp(pd.Timestamp(last_ts).date()) + pd.Timedelta(days=1)
        end = pd.Timestamp(pd.Timestamp(now).date()) - pd.Timedelta(days=1)
        if start > end:
            return 0
        return int(len(pd.bdate_range(start=start, end=end)))

    @staticmethod
    def _complete_bars_only(df: pd.DataFrame) -> pd.DataFrame:
        if "bar_complete" not in df.columns:
            return df
        return df[df["bar_complete"].astype(bool)].copy()

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if df.index.name == "timestamp":
            df.index.name = None
        return df

    def _atomic_write(
        self,
        path: Path,
        df: pd.DataFrame,
        *,
        key: tuple[str, str, str],
        refresh_mode: str = "full_fetch",
        rows_appended: int = 0,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        meta_path = path.with_suffix(".metadata.json")
        tmp_meta = meta_path.with_name(f".{meta_path.name}.{os.getpid()}.tmp")
        interval_lower = _normalized_interval_key(key[2])
        incremental_supported = bool(
            self.incremental_enabled
            and (
                interval_lower in _DAILY_INTERVALS
                or (self.incremental_intraday_enabled and interval_lower in _INTRADAY_BAR_MINUTES)
            )
        )
        try:
            writable = df.copy()
            writable.index.name = "timestamp"
            writable.to_csv(tmp_path, float_format="%.10g", date_format="%Y-%m-%dT%H:%M:%S%z")
            digest = _sha256_file(tmp_path)
            metadata = {
                "schema_version": self.schema_version,
                "symbol": key[0],
                "period": key[1],
                "interval": key[2],
                "rows": int(len(df)),
                "first_timestamp": str(df.index[0]) if len(df) else "",
                "last_timestamp": str(df.index[-1]) if len(df) else "",
                "sha256": digest,
                "adjusted": bool(self.adjusted),
                "what_to_show": str(self.what_to_show or ""),
                "bar_complete_column": "bar_complete",
                "provider_boundary": "period_interval_fetch_with_tail_merge"
                if incremental_supported
                else "period_interval_fetch",
                "incremental_fetch_supported": incremental_supported,
                "refresh_mode": refresh_mode,
                "rows_appended": int(rows_appended),
                "created_at": datetime.now(UTC).isoformat(),
            }
            tmp_meta.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp_path, path)
            os.replace(tmp_meta, meta_path)
        finally:
            for leftover in (tmp_path, tmp_meta):
                if leftover.exists():
                    leftover.unlink()

    @staticmethod
    def _read_metadata(path: Any) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}


def detect_unadjusted_splits(df: pd.DataFrame, *, threshold: float = 0.35) -> list[str]:
    """Heuristic timestamps where a split-like open/previous-close jump appears."""
    if df.empty or "open" not in df or "close" not in df:
        return []
    out = normalize_ohlcv(df)
    previous_close = out["close"].shift(1)
    jump = (out["open"] / previous_close - 1.0).abs()
    volume = out["volume"].astype(float)
    median_volume = volume.rolling(20, min_periods=5).median().shift(1)
    volume_not_extreme = median_volume.isna() | (volume <= median_volume * 3.0)
    timestamps = out.index[(jump > threshold) & volume_not_extreme.fillna(True)]
    return [pd.Timestamp(ts).isoformat() for ts in timestamps]


def _safe_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "."} else "_" for ch in value).strip("._")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
