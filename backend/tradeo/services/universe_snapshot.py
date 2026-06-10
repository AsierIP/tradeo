from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, UTC
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from tradeo.core.config import Settings, get_settings
from tradeo.services.data_provider import load_universe

ALLOWED_US_EXCHANGES = {"NYSE", "NASDAQ", "AMEX", "ARCA", "NYSEARCA"}


@dataclass(slots=True)
class UniverseSnapshotService:
    """Forward point-in-time universe snapshots.

    Historical delisting-aware data needs a licensed source. Until that exists,
    snapshots built by this service are honest from their creation month forward
    and carry `survivorship_biased=true` for backtests that look before the first
    snapshot.
    """

    settings: Settings | None = None

    def __post_init__(self) -> None:
        self.settings = self.settings or get_settings()

    def build_monthly_snapshot(
        self,
        as_of: date | datetime | str | None = None,
        *,
        universe: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        settings = self.settings
        assert settings is not None
        snapshot_date = _coerce_date(as_of)
        month_key = snapshot_date.strftime("%Y-%m")
        raw = universe.copy() if universe is not None else load_universe(settings.universe_file)
        filtered, rules = self._eligible(raw)
        filtered = filtered.sort_values("symbol").drop_duplicates("symbol").reset_index(drop=True)
        filtered["snapshot_month"] = month_key
        filtered["snapshot_as_of"] = snapshot_date.isoformat()
        filtered["point_in_time"] = bool(settings.universe_point_in_time_available)
        filtered["survivorship_biased"] = not bool(settings.universe_point_in_time_available)

        path = settings.universe_snapshot_path / f"{month_key}.csv"
        metadata_path = path.with_suffix(".metadata.json")
        self._atomic_write(path, filtered)
        digest = _sha256_file(path)
        metadata = {
            "schema_version": 1,
            "snapshot_month": month_key,
            "snapshot_as_of": snapshot_date.isoformat(),
            "source_universe_file": settings.universe_file,
            "path": str(path),
            "sha256": digest,
            "row_count": int(len(filtered)),
            "symbols": filtered["symbol"].tolist(),
            "eligibility_rules": rules,
            "point_in_time": bool(settings.universe_point_in_time_available),
            "survivorship_biased": not bool(settings.universe_point_in_time_available),
            "built_at": datetime.now(UTC).isoformat(),
        }
        self._write_json_atomic(metadata_path, metadata)
        return metadata

    def latest_snapshot(self) -> dict[str, Any] | None:
        settings = self.settings
        assert settings is not None
        paths = sorted(settings.universe_snapshot_path.glob("*.metadata.json"))
        if not paths:
            return None
        try:
            payload = json.loads(paths[-1].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def symbols_for_month(self, as_of: date | datetime | str) -> list[str]:
        settings = self.settings
        assert settings is not None
        month_key = _coerce_date(as_of).strftime("%Y-%m")
        path = settings.universe_snapshot_path / f"{month_key}.csv"
        if not path.exists():
            return []
        df = pd.read_csv(path)
        if "symbol" not in df:
            return []
        return df["symbol"].astype(str).str.upper().tolist()

    def _eligible(self, universe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
        settings = self.settings
        assert settings is not None
        df = universe.copy()
        if "symbol" not in df.columns:
            raise ValueError("Universe snapshot requires a 'symbol' column")
        df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
        df = df[df["symbol"].str.len() > 0].copy()
        rules: dict[str, Any] = {
            "min_price": settings.min_price,
            "min_avg_dollar_volume": settings.min_avg_dollar_volume,
            "allowed_exchanges": sorted(ALLOWED_US_EXCHANGES),
            "price_column": "",
            "dollar_volume_column": "",
            "exchange_column": "",
            "missing_filter_columns": [],
        }
        price_col = _first_column(df, ("price", "last_price", "close", "adj_close"))
        if price_col:
            rules["price_column"] = price_col
            df = df[pd.to_numeric(df[price_col], errors="coerce") >= settings.min_price]
        else:
            rules["missing_filter_columns"].append("price")
        dollar_col = _first_column(
            df,
            ("avg_dollar_volume", "average_dollar_volume", "dollar_volume", "adv_usd"),
        )
        if dollar_col:
            rules["dollar_volume_column"] = dollar_col
            df = df[pd.to_numeric(df[dollar_col], errors="coerce") >= settings.min_avg_dollar_volume]
        else:
            rules["missing_filter_columns"].append("avg_dollar_volume")
        exchange_col = _first_column(df, ("exchange", "primary_exchange", "listing_exchange"))
        if exchange_col:
            rules["exchange_column"] = exchange_col
            exchanges = df[exchange_col].astype(str).str.upper().str.strip()
            df = df[exchanges.isin(ALLOWED_US_EXCHANGES)]
        else:
            rules["missing_filter_columns"].append("exchange")
        return df, rules

    @staticmethod
    def _atomic_write(path: Path, df: pd.DataFrame) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            df.to_csv(tmp_path, index=False)
            os.replace(tmp_path, path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(tmp_path, path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


def _coerce_date(value: date | datetime | str | None) -> date:
    if value is None:
        return datetime.now(UTC).date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(value).date()


def _first_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    columns = {str(column).lower(): str(column) for column in df.columns}
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    return ""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
