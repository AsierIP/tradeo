from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from tradeo.core.config import get_settings
from tradeo.services.technical_indicators import normalize_ohlcv


class MarketDataProvider(Protocol):
    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        ...


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
    return df


def pick_symbols(limit: int | None = None, force_symbols: list[str] | None = None) -> list[str]:
    if force_symbols:
        return [s.upper().strip() for s in force_symbols if s.strip()]
    settings = get_settings()
    df = load_universe(settings.universe_file)
    n = limit or settings.scan_limit_default
    return df["symbol"].head(n).tolist()


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
        self._cache: dict[tuple[str, str, str], pd.DataFrame] = {}

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        key = (symbol.upper(), period, interval)
        if key not in self._cache:
            csv_path = self._cache_path(*key)
            if csv_path.exists():
                df = self._read_csv(csv_path)
                df = self._maybe_refresh(df, key=key, csv_path=csv_path)
            else:
                assert self.upstream is not None
                df = self.upstream.fetch_ohlcv(symbol, period=period, interval=interval)
                df = self._annotate(df, symbol=key[0], period=period, interval=interval)
                self._atomic_write(csv_path, df, key=key, refresh_mode="full_fetch")
            self._cache[key] = self._complete_bars_only(df)
        return self._cache[key].copy()

    def _maybe_refresh(
        self,
        cached: pd.DataFrame,
        *,
        key: tuple[str, str, str],
        csv_path: Path,
    ) -> pd.DataFrame:
        """Append the missing daily tail after verifying overlap bars.

        Adjusted feeds rewrite history on splits/dividends, so an incremental
        append is only trusted when the refetched overlap matches the cached
        bars; otherwise the whole artifact is refetched.
        """
        symbol, period, interval = key
        if (
            not self.incremental_enabled
            or interval.lower() not in {"1d", "1day", "1 day"}
            or cached.empty
        ):
            return cached
        last_ts = pd.Timestamp(cached.index[-1])
        gap_days = (datetime.now(UTC).date() - last_ts.date()).days - 1
        if gap_days < int(self.incremental_min_gap_days or 1):
            return cached
        assert self.upstream is not None
        if gap_days > int(self.incremental_max_gap_days or 45):
            df = self.upstream.fetch_ohlcv(symbol, period=period, interval=interval)
            df = self._annotate(df, symbol=symbol, period=period, interval=interval)
            self._atomic_write(csv_path, df, key=key, refresh_mode="full_refetch_gap_too_large")
            return df
        overlap_bars = max(1, int(self.incremental_overlap_bars or 5))
        tail_days = gap_days + overlap_bars * 2 + 4
        tail = self.upstream.fetch_ohlcv(symbol, period=f"{tail_days}d", interval=interval)
        tail = self._annotate(tail, symbol=symbol, period=period, interval=interval)
        if not self._overlap_matches(cached, tail, overlap_bars=overlap_bars):
            df = self.upstream.fetch_ohlcv(symbol, period=period, interval=interval)
            df = self._annotate(df, symbol=symbol, period=period, interval=interval)
            self._atomic_write(csv_path, df, key=key, refresh_mode="full_refetch_overlap_mismatch")
            return df
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

    def data_manifest(self, symbols: list[str] | None = None) -> dict[str, Any]:
        """Return a deterministic manifest over cached OHLCV artifacts."""
        assert self.cache_dir is not None
        requested = {s.upper() for s in symbols} if symbols else None
        entries: dict[str, Any] = {}
        for csv_path in sorted(self.cache_dir.glob("*.csv")):
            meta_path = csv_path.with_suffix(".metadata.json")
            metadata = self._read_metadata(meta_path)
            symbol = str(metadata.get("symbol") or csv_path.stem.split("_", 1)[0]).upper()
            if requested is not None and symbol not in requested:
                continue
            digest = _sha256_file(csv_path)
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
            json.dumps(payload["entries"], sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        return payload

    def _cache_path(self, symbol: str, period: str, interval: str) -> Path:
        assert self.cache_dir is not None
        safe = "_".join(_safe_part(part) for part in (symbol.upper(), interval, period))
        return self.cache_dir / f"{safe}.csv"

    def _annotate(self, df: pd.DataFrame, *, symbol: str, period: str, interval: str) -> pd.DataFrame:
        out = normalize_ohlcv(df)
        out = out.copy()
        out["adjusted"] = bool(self.adjusted)
        out["what_to_show"] = str(self.what_to_show or "")
        out["bar_complete"] = self._bar_complete_mask(out.index, interval)
        return out

    @staticmethod
    def _bar_complete_mask(index: pd.Index, interval: str) -> list[bool]:
        if interval.lower() not in {"1d", "1day", "1 day"}:
            return [True] * len(index)
        today = datetime.now(UTC).date()
        return [pd.Timestamp(value).date() < today for value in index]

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
        incremental_supported = bool(
            self.incremental_enabled and key[2].lower() in {"1d", "1day", "1 day"}
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
    def _read_metadata(path: Path) -> dict[str, Any]:
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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
