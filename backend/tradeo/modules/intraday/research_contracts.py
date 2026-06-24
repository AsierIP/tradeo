from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

INTRADAY_RESEARCH_CORE_VERSION = "intraday-research-core-v2"
_REQUIRED_OHLCV = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class IntradayResearchDataContract:
    symbol: str
    session_id: str
    data_cutoff_ts: datetime
    decision_ts: datetime
    entry_eligible_ts: datetime
    timeframes: tuple[str, ...]
    manifest_hash: str
    frame_hashes: dict[str, str]
    complete_bars_by_timeframe: dict[str, int]
    reason_codes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    contract_version: str = INTRADAY_RESEARCH_CORE_VERSION

    @property
    def accepted(self) -> bool:
        return not self.reason_codes

    def to_intraday_metadata(self) -> dict[str, Any]:
        return {
            "intraday": {
                "research_core_version": self.contract_version,
                "accepted": self.accepted,
                "symbol": self.symbol,
                "session_id": self.session_id,
                "data_cutoff_ts": self.data_cutoff_ts.isoformat(),
                "decision_ts": self.decision_ts.isoformat(),
                "entry_eligible_ts": self.entry_eligible_ts.isoformat(),
                "timeframes": list(self.timeframes),
                "manifest_hash": self.manifest_hash,
                "frame_hashes": dict(self.frame_hashes),
                "complete_bars_by_timeframe": dict(self.complete_bars_by_timeframe),
                "reason_codes": list(self.reason_codes),
                "metadata": dict(self.metadata),
            }
        }


class IntradayResearchDataContractBuilder:
    """Closed-bar contract with vectorized validation and deterministic hashes."""

    def build(
        self,
        bars_by_timeframe: Mapping[str, pd.DataFrame],
        *,
        symbol: str,
        session_id: str,
        decision_ts: datetime | None = None,
        min_bars_by_timeframe: Mapping[str, int] | None = None,
        required_timeframes: Iterable[str] | None = None,
    ) -> IntradayResearchDataContract:
        now = _as_utc(decision_ts or datetime.now(timezone.utc))
        timeframes = tuple(required_timeframes or bars_by_timeframe.keys())
        min_bars = {str(k): int(v) for k, v in (min_bars_by_timeframe or {}).items()}
        reasons: list[str] = []
        hashes: dict[str, str] = {}
        counts: dict[str, int] = {}
        last_seen: list[datetime] = []
        quality: dict[str, Any] = {}
        for timeframe in timeframes:
            frame = bars_by_timeframe.get(timeframe)
            if frame is None:
                reasons.append(f"missing_timeframe:{timeframe}")
                continue
            try:
                clean = normalize_intraday_bars(frame)
            except ValueError as exc:
                reasons.append(f"invalid_bars:{timeframe}:{exc}")
                continue
            duplicates = int(clean.index.duplicated(keep="last").sum())
            zero_volume = int((clean["volume"].to_numpy(dtype=float) <= 0).sum())
            if duplicates:
                reasons.append(f"duplicates:{timeframe}")
            if zero_volume:
                reasons.append(f"zero_volume:{timeframe}")
            if len(clean) < min_bars.get(timeframe, 1):
                reasons.append(f"insufficient_bars:{timeframe}")
            hashes[timeframe] = hash_frame(clean)
            counts[timeframe] = len(clean)
            last_seen.append(_as_utc(clean.index[-1].to_pydatetime()))
            quality[timeframe] = {
                "bars": len(clean),
                "duplicates": duplicates,
                "zero_volume": zero_volume,
            }
        cutoff = min(last_seen) if last_seen else now
        entry_ts = _as_utc(
            (pd.Timestamp(cutoff) + timeframe_delta(timeframes[-1] if timeframes else "5m")).to_pydatetime()
        )
        manifest_hash = hash_text(
            repr((symbol.upper(), session_id, timeframes, hashes, counts, cutoff.isoformat()))
        )
        if not last_seen:
            reasons.append("no_valid_timeframes")
        return IntradayResearchDataContract(
            symbol=symbol.upper().strip(),
            session_id=str(session_id),
            data_cutoff_ts=cutoff,
            decision_ts=now,
            entry_eligible_ts=entry_ts,
            timeframes=timeframes,
            manifest_hash=manifest_hash,
            frame_hashes=hashes,
            complete_bars_by_timeframe=counts,
            reason_codes=tuple(dict.fromkeys(reasons)),
            metadata={"quality": quality, "math_backend": "numpy_vectorized_hash"},
        )


def normalize_intraday_bars(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise ValueError("intraday bars require DatetimeIndex")
    out = frame.copy()
    out.columns = [str(c).lower().replace(" ", "_") for c in out.columns]
    missing = [c for c in _REQUIRED_OHLCV if c not in out.columns]
    if missing:
        raise ValueError(f"missing OHLCV columns: {missing}")
    cols = list(_REQUIRED_OHLCV) + [c for c in ("bid", "ask") if c in out.columns]
    out = out[cols].sort_index()
    for col in cols:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    values = out.to_numpy(dtype=float)
    if out.empty or np.isnan(values).any() or not np.isfinite(values).all():
        raise ValueError("empty_or_non_finite_bars")
    return out


def hash_frame(frame: pd.DataFrame) -> str:
    columns = sorted(frame.columns)
    digest = sha256()
    digest.update("|".join(columns).encode())
    digest.update(np.ascontiguousarray(frame.index.asi8.astype(np.int64)).tobytes())
    digest.update(np.ascontiguousarray(frame[columns].to_numpy(dtype=np.float64)).tobytes())
    return digest.hexdigest()


def hash_text(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def timeframe_delta(timeframe: str) -> pd.Timedelta:
    value = timeframe.lower().strip()
    if value.endswith("m"):
        return pd.Timedelta(minutes=int(value[:-1]))
    if value.endswith("h"):
        return pd.Timedelta(hours=int(value[:-1]))
    return pd.Timedelta(minutes=5)


def as_utc(value: datetime) -> datetime:
    return _as_utc(value)


def json_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
