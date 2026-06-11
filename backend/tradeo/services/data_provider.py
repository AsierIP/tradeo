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

    def __post_init__(self) -> None:
        if self.upstream is None:
            raise ValueError("CachedMarketDataProvider requires an explicit real-data upstream")
        settings = get_settings()
        self.cache_dir = self.cache_dir or settings.market_data_cache_path
        self.adjusted = settings.market_data_adjusted if self.adjusted is None else self.adjusted
        self.what_to_show = self.what_to_show or settings.market_data_what_to_show
        self._cache: dict[tuple[str, str, str], pd.DataFrame] = {}

    def fetch_ohlcv(self, symbol: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
        key = (symbol.upper(), period, interval)
        if key not in self._cache:
            csv_path = self._cache_path(*key)
            if csv_path.exists():
                df = self._read_csv(csv_path)
            else:
                assert self.upstream is not None
                df = self.upstream.fetch_ohlcv(symbol, period=period, interval=interval)
                df = self._annotate(df, symbol=key[0], period=period, interval=interval)
                self._atomic_write(csv_path, df, key=key)
            self._cache[key] = self._complete_bars_only(df)
        return self._cache[key].copy()

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

    def _atomic_write(self, path: Path, df: pd.DataFrame, *, key: tuple[str, str, str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        meta_path = path.with_suffix(".metadata.json")
        tmp_meta = meta_path.with_name(f".{meta_path.name}.{os.getpid()}.tmp")
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
                "provider_boundary": "period_interval_fetch",
                "incremental_fetch_supported": False,
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
