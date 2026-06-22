from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any, Iterable, Sequence

import pandas as pd

CONTRACT_VERSION = "intraday-universe-v1"


@dataclass(frozen=True, slots=True)
class IntradayUniverseConfig:
    min_price: float = 3.0
    max_price: float | None = None
    min_abs_gap_pct: float = 3.0
    min_rvol: float = 1.5
    min_avg_dollar_volume: float = 1_000_000.0
    min_dollar_volume: float = 250_000.0
    max_spread_bps: float = 50.0
    max_symbols: int = 25
    excluded_symbols: frozenset[str] = field(default_factory=frozenset)
    manual_watchlist: tuple[str, ...] = ()
    require_data_ok: bool = True


@dataclass(frozen=True, slots=True)
class IntradayUniverseCandidate:
    symbol: str
    score: float
    price: float
    gap_pct: float
    rvol: float
    avg_dollar_volume: float
    spread_bps: float
    dollar_volume: float
    data_ok: bool
    manual_watchlist: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IntradayUniverseRejection:
    symbol: str
    reason: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class IntradayUniverse:
    contract_version: str
    selected: tuple[IntradayUniverseCandidate, ...]
    rejected: tuple[IntradayUniverseRejection, ...]
    filters: dict[str, Any]

    @property
    def symbols(self) -> list[str]:
        return [candidate.symbol for candidate in self.selected]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "symbols": self.symbols,
            "selected": [candidate.to_dict() for candidate in self.selected],
            "rejected": [rejection.to_dict() for rejection in self.rejected],
            "filters": self.filters,
        }


class IntradayUniverseBuilder:
    """Build a small-cap intraday universe from precomputed session metrics.

    Manual watchlist symbols are allowed to receive deterministic priority, but
    only after they pass the same safety filters as every other symbol.
    """

    def __init__(self, config: IntradayUniverseConfig | None = None) -> None:
        self.config = config or IntradayUniverseConfig()

    def build(
        self,
        candidates: pd.DataFrame,
        *,
        manual_watchlist: Sequence[str] | None = None,
        exclusions: Iterable[str] | None = None,
        max_symbols: int | None = None,
    ) -> IntradayUniverse:
        if "symbol" not in candidates.columns:
            raise ValueError("Intraday universe candidates require a 'symbol' column")

        cfg = self.config
        manual_symbols = _normalize_symbols(cfg.manual_watchlist)
        manual_symbols.extend(symbol for symbol in _normalize_symbols(manual_watchlist) if symbol not in manual_symbols)
        manual_rank = {symbol: idx for idx, symbol in enumerate(manual_symbols)}
        excluded = set(_normalize_symbols(cfg.excluded_symbols))
        excluded.update(_normalize_symbols(exclusions))
        limit = cfg.max_symbols if max_symbols is None else max(0, int(max_symbols))

        frame = candidates.copy()
        frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
        frame = frame[frame["symbol"].str.len() > 0].copy()
        frame = frame.drop_duplicates("symbol", keep="last")

        accepted: list[IntradayUniverseCandidate] = []
        rejected: list[IntradayUniverseRejection] = []
        seen = set(frame["symbol"].tolist())
        for symbol in manual_symbols:
            if symbol not in seen:
                rejected.append(
                    IntradayUniverseRejection(
                        symbol=symbol,
                        reason="missing_metrics",
                        details={"manual_watchlist": True},
                    )
                )

        for _, row in frame.sort_values("symbol").iterrows():
            symbol = str(row["symbol"])
            evaluation = self._evaluate_row(
                row,
                excluded=excluded,
                manual_watchlist=symbol in manual_rank,
            )
            if isinstance(evaluation, IntradayUniverseRejection):
                rejected.append(evaluation)
            else:
                accepted.append(evaluation)

        accepted.sort(
            key=lambda item: (
                0 if item.manual_watchlist else 1,
                manual_rank.get(item.symbol, 10**9),
                -item.score,
                item.symbol,
            )
        )
        selected = accepted[:limit]
        for candidate in accepted[limit:]:
            rejected.append(
                IntradayUniverseRejection(
                    symbol=candidate.symbol,
                    reason="max_symbols",
                    details={"max_symbols": limit, "score": candidate.score},
                )
            )

        return IntradayUniverse(
            contract_version=CONTRACT_VERSION,
            selected=tuple(selected),
            rejected=tuple(sorted(rejected, key=lambda item: (item.symbol, item.reason))),
            filters={
                "min_price": cfg.min_price,
                "max_price": cfg.max_price,
                "min_abs_gap_pct": cfg.min_abs_gap_pct,
                "min_rvol": cfg.min_rvol,
                "min_avg_dollar_volume": cfg.min_avg_dollar_volume,
                "min_dollar_volume": cfg.min_dollar_volume,
                "max_spread_bps": cfg.max_spread_bps,
                "max_symbols": limit,
                "require_data_ok": cfg.require_data_ok,
                "manual_watchlist": manual_symbols,
                "excluded_symbols": sorted(excluded),
            },
        )

    def _evaluate_row(
        self,
        row: pd.Series,
        *,
        excluded: set[str],
        manual_watchlist: bool,
    ) -> IntradayUniverseCandidate | IntradayUniverseRejection:
        cfg = self.config
        symbol = str(row["symbol"])
        if symbol in excluded:
            return IntradayUniverseRejection(symbol=symbol, reason="excluded")

        data_ok = _bool_value(_lookup(row, ("data_ok", "market_data_ok", "quality_ok")), default=True)
        if cfg.require_data_ok and not data_ok:
            return IntradayUniverseRejection(symbol=symbol, reason="data_not_ok")

        metrics = {
            "price": _price(row),
            "gap_pct": _gap_pct(row),
            "rvol": _number(_lookup(row, ("rvol", "relative_volume", "rel_volume"))),
            "avg_dollar_volume": _avg_dollar_volume(row),
            "spread_bps": _spread_bps(row),
            "dollar_volume": _dollar_volume(row),
        }
        missing = sorted(name for name, value in metrics.items() if value is None)
        if missing:
            return IntradayUniverseRejection(
                symbol=symbol,
                reason="missing_metrics",
                details={"missing": missing},
            )

        price = float(metrics["price"])
        gap_pct = float(metrics["gap_pct"])
        rvol = float(metrics["rvol"])
        avg_dollar_volume = float(metrics["avg_dollar_volume"])
        spread_bps = float(metrics["spread_bps"])
        dollar_volume = float(metrics["dollar_volume"])

        checks = (
            ("price", price >= cfg.min_price, {"price": price, "min_price": cfg.min_price}),
            (
                "max_price",
                cfg.max_price is None or price <= cfg.max_price,
                {"price": price, "max_price": cfg.max_price},
            ),
            (
                "gap",
                abs(gap_pct) >= cfg.min_abs_gap_pct,
                {"gap_pct": gap_pct, "min_abs_gap_pct": cfg.min_abs_gap_pct},
            ),
            ("rvol", rvol >= cfg.min_rvol, {"rvol": rvol, "min_rvol": cfg.min_rvol}),
            (
                "adv",
                avg_dollar_volume >= cfg.min_avg_dollar_volume,
                {
                    "avg_dollar_volume": avg_dollar_volume,
                    "min_avg_dollar_volume": cfg.min_avg_dollar_volume,
                },
            ),
            (
                "spread",
                spread_bps <= cfg.max_spread_bps,
                {"spread_bps": spread_bps, "max_spread_bps": cfg.max_spread_bps},
            ),
            (
                "dollar_volume",
                dollar_volume >= cfg.min_dollar_volume,
                {"dollar_volume": dollar_volume, "min_dollar_volume": cfg.min_dollar_volume},
            ),
        )
        for reason, passed, details in checks:
            if not passed:
                return IntradayUniverseRejection(symbol=symbol, reason=reason, details=details)

        score = _score(
            abs_gap_pct=abs(gap_pct),
            rvol=rvol,
            avg_dollar_volume=avg_dollar_volume,
            dollar_volume=dollar_volume,
            spread_bps=spread_bps,
        )
        return IntradayUniverseCandidate(
            symbol=symbol,
            score=score,
            price=price,
            gap_pct=gap_pct,
            rvol=rvol,
            avg_dollar_volume=avg_dollar_volume,
            spread_bps=spread_bps,
            dollar_volume=dollar_volume,
            data_ok=data_ok,
            manual_watchlist=manual_watchlist,
        )


def _normalize_symbols(values: Iterable[str] | None) -> list[str]:
    if values is None:
        return []
    symbols: list[str] = []
    for value in values:
        symbol = str(value).upper().strip()
        if symbol and symbol not in symbols:
            symbols.append(symbol)
    return symbols


def _lookup(row: pd.Series, names: tuple[str, ...]) -> Any:
    columns = {str(name).lower(): name for name in row.index}
    for name in names:
        column = columns.get(name)
        if column is not None:
            return row[column]
    return None


def _number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _bool_value(value: Any, *, default: bool) -> bool:
    if value is None or pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "ok", "pass", "passed"}


def _price(row: pd.Series) -> float | None:
    return _number(_lookup(row, ("price", "last_price", "last", "close")))


def _gap_pct(row: pd.Series) -> float | None:
    explicit = _number(_lookup(row, ("gap_pct", "gap_percent", "gap")))
    if explicit is not None:
        return explicit
    price = _price(row)
    previous_close = _number(_lookup(row, ("previous_close", "prev_close", "prior_close")))
    if price is None or previous_close is None or previous_close <= 0:
        return None
    return (price / previous_close - 1.0) * 100.0


def _avg_dollar_volume(row: pd.Series) -> float | None:
    explicit = _number(
        _lookup(
            row,
            (
                "avg_dollar_volume",
                "average_dollar_volume",
                "adv_dollar",
                "adv_usd",
                "avg_daily_dollar_volume",
            ),
        )
    )
    if explicit is not None:
        return explicit
    avg_volume = _number(_lookup(row, ("avg_volume", "average_volume", "adv")))
    price = _price(row)
    if avg_volume is None or price is None:
        return None
    return avg_volume * price


def _dollar_volume(row: pd.Series) -> float | None:
    explicit = _number(_lookup(row, ("dollar_volume", "session_dollar_volume", "premarket_dollar_volume")))
    if explicit is not None:
        return explicit
    volume = _number(_lookup(row, ("volume", "session_volume", "premarket_volume")))
    price = _price(row)
    if volume is None or price is None:
        return None
    return volume * price


def _spread_bps(row: pd.Series) -> float | None:
    explicit = _number(_lookup(row, ("spread_bps", "bid_ask_spread_bps")))
    if explicit is not None:
        return explicit
    spread_pct = _number(_lookup(row, ("spread_pct", "bid_ask_spread_pct")))
    if spread_pct is not None:
        return spread_pct * 100.0 if spread_pct > 1.0 else spread_pct * 10_000.0
    bid = _number(_lookup(row, ("bid",)))
    ask = _number(_lookup(row, ("ask",)))
    if bid is not None and ask is not None and bid > 0 and ask >= bid:
        midpoint = (bid + ask) / 2.0
        return (ask - bid) / midpoint * 10_000.0
    return None


def _score(
    *,
    abs_gap_pct: float,
    rvol: float,
    avg_dollar_volume: float,
    dollar_volume: float,
    spread_bps: float,
) -> float:
    liquidity = math.log10(max(avg_dollar_volume, 1.0)) + math.log10(max(dollar_volume, 1.0))
    spread_penalty = min(spread_bps / 100.0, 5.0)
    return round(abs_gap_pct * 1.5 + rvol * 2.0 + liquidity - spread_penalty, 6)
