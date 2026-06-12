"""Per-signal quote snapshot: real bid/ask/last at the moment of the signal.

Informe §3.3.1: one ``reqMktData`` snapshot per signal converts the spread
from a proxy into a datum at the instant that matters. This is **not** a
microstructure feed — reports keep the honest
``microstructure_feed = none_available`` marker; the snapshot carries its own
``data_basis = ibkr_quote_snapshot_at_signal``.

Design constraints:

- **Fail-soft**: a missing/failed snapshot must never block signal creation.
  The result always records ``available`` and a ``reason`` so coverage (the
  informe's ≥95% KPI) is measurable from the data itself.
- **Feature-flagged**: ``TRADEO_SIGNAL_SPREAD_SNAPSHOT_ENABLED`` (default on;
  scanners only call this when IBKR is the market data provider).
- Injectable provider so tests and future non-IBKR sources plug in without
  touching the scanner.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from tradeo.core.config import Settings, get_settings

SPREAD_SNAPSHOT_DATA_BASIS = "ibkr_quote_snapshot_at_signal"
SPREAD_SNAPSHOT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class QuoteSnapshot:
    symbol: str
    bid: float | None
    ask: float | None
    last: float | None
    bid_size: float | None = None
    ask_size: float | None = None
    source: str = SPREAD_SNAPSHOT_DATA_BASIS


class QuoteSnapshotProvider(Protocol):
    def snapshot(self, symbol: str) -> QuoteSnapshot: ...


class IBKRQuoteSnapshotProvider:
    """Single ``reqMktData(snapshot=True)`` per call; connects and disconnects.

    Reuses the broker adapter's defensive connect (client-id rotation,
    timeout). A snapshot request never places orders and works in read-only
    sessions.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def snapshot(self, symbol: str) -> QuoteSnapshot:
        from ib_insync import Stock

        from tradeo.services.ibkr_broker import IBKRBroker

        timeout = float(
            getattr(self.settings, "signal_spread_snapshot_timeout_seconds", 4.0)
        )
        # Cap the broker connect timeout at the snapshot budget: a down TWS
        # must cost at most a few seconds per signal, not the full order path.
        broker_settings = self.settings.model_copy(
            update={
                "ibkr_connect_timeout_seconds": min(
                    float(self.settings.ibkr_connect_timeout_seconds), timeout
                )
            }
        )
        ib = IBKRBroker(settings=broker_settings)._connect()
        try:
            contract = Stock(symbol.upper(), "SMART", "USD")
            qualified = ib.qualifyContracts(contract)
            if not qualified:
                raise RuntimeError(f"could not qualify contract for {symbol}")
            ticker = ib.reqMktData(qualified[0], "", snapshot=True, regulatorySnapshot=False)
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                ib.sleep(0.25)
                if _usable_price(ticker.bid) and _usable_price(ticker.ask):
                    break
            return QuoteSnapshot(
                symbol=symbol.upper(),
                bid=_clean_price(ticker.bid),
                ask=_clean_price(ticker.ask),
                last=_clean_price(ticker.last) or _clean_price(ticker.close),
                bid_size=_clean_size(ticker.bidSize),
                ask_size=_clean_size(ticker.askSize),
            )
        finally:
            if ib.isConnected():
                ib.disconnect()


def capture_signal_spread_snapshot(
    *,
    symbol: str,
    entry: float | None,
    stop: float | None,
    settings: Settings | None = None,
    provider: QuoteSnapshotProvider | None = None,
    provider_factory: Callable[[Settings], QuoteSnapshotProvider] | None = None,
) -> dict[str, Any]:
    """Capture bid/ask/last for one signal; never raises.

    Returns a self-describing record stored on the signal. When bid/ask are
    usable it includes ``spread_observed_pct`` (of mid) and ``spread_cost_r``
    (full spread over per-share risk), the two numbers the cost model and the
    execution-quality audit consume.
    """
    settings = settings or get_settings()
    record: dict[str, Any] = {
        "schema_version": SPREAD_SNAPSHOT_SCHEMA_VERSION,
        "data_basis": SPREAD_SNAPSHOT_DATA_BASIS,
        "microstructure_feed": "none_available",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol.upper(),
        "available": False,
        "reason": "",
        "bid": None,
        "ask": None,
        "last": None,
        "bid_size": None,
        "ask_size": None,
        "mid": None,
        "spread_abs": None,
        "spread_observed_pct": None,
        "spread_cost_r": None,
    }
    if not bool(getattr(settings, "signal_spread_snapshot_enabled", False)):
        record["reason"] = "disabled"
        return record
    try:
        if provider is None:
            factory = provider_factory or (lambda s: IBKRQuoteSnapshotProvider(settings=s))
            provider = factory(settings)
        quote = provider.snapshot(symbol)
    except Exception as exc:  # noqa: BLE001 — fail-soft by contract
        record["reason"] = f"snapshot_failed: {type(exc).__name__}: {exc}"[:300]
        return record

    record["bid"] = quote.bid
    record["ask"] = quote.ask
    record["last"] = quote.last
    record["bid_size"] = quote.bid_size
    record["ask_size"] = quote.ask_size
    record["data_basis"] = quote.source

    if not (_usable_price(quote.bid) and _usable_price(quote.ask)) or quote.ask < quote.bid:
        record["reason"] = "no_usable_bid_ask"
        return record

    mid = (quote.bid + quote.ask) / 2.0
    spread_abs = quote.ask - quote.bid
    record["available"] = True
    record["mid"] = round(mid, 6)
    record["spread_abs"] = round(spread_abs, 6)
    record["spread_observed_pct"] = round(spread_abs / mid, 6) if mid > 0 else None

    risk_per_share = abs(float(entry or 0.0) - float(stop or 0.0))
    if risk_per_share > 0:
        record["spread_cost_r"] = round(spread_abs / risk_per_share, 6)
    return record


def _usable_price(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and number > 0


def _clean_price(value: Any) -> float | None:
    return round(float(value), 6) if _usable_price(value) else None


def _clean_size(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None
