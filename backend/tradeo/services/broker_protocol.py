from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class BrokerPositionSnapshot:
    symbol: str
    qty: float
    avg_cost: float = 0.0


@dataclass(frozen=True, slots=True)
class BrokerOrderPreview:
    ok: bool
    symbol: str
    side: str
    qty: float
    reason: str
    details: dict[str, Any]


class BrokerGatewayProtocol(Protocol):
    def account_summary(self) -> dict[str, Any]: ...

    def positions(self) -> list[BrokerPositionSnapshot]: ...

    def open_orders(self) -> list[dict[str, Any]]: ...

    def cancel_order(self, order_id: str) -> dict[str, Any]: ...

    def preview_reduce_only_exit(
        self,
        symbol: str,
        qty: float,
        side: str,
        reason: str,
        *,
        limit_price: float | None = None,
        allow_market: bool = False,
    ) -> BrokerOrderPreview: ...

    def submit_reduce_only_exit(
        self,
        symbol: str,
        qty: float,
        side: str,
        reason: str,
        *,
        limit_price: float | None = None,
        allow_market: bool = False,
    ) -> dict[str, Any]: ...

    def fills(self, since: str | None = None) -> list[dict[str, Any]]: ...


class DisabledIbAsyncBroker:
    """Experimental adapter placeholder; cannot execute unless explicitly replaced."""

    def __init__(self, *, enabled: bool = False) -> None:
        self.enabled = enabled

    def account_summary(self) -> dict[str, Any]:
        return {"adapter": "ib_async", "enabled": self.enabled, "status": "disabled"}

    def positions(self) -> list[BrokerPositionSnapshot]:
        return []

    def open_orders(self) -> list[dict[str, Any]]:
        return []

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        return {"ok": False, "order_id": order_id, "reason": "adapter_disabled"}

    def preview_reduce_only_exit(
        self,
        symbol: str,
        qty: float,
        side: str,
        reason: str,
        *,
        limit_price: float | None = None,
        allow_market: bool = False,
    ) -> BrokerOrderPreview:
        return BrokerOrderPreview(False, symbol.upper(), side.upper(), qty, reason, {"reason": "adapter_disabled"})

    def submit_reduce_only_exit(
        self,
        symbol: str,
        qty: float,
        side: str,
        reason: str,
        *,
        limit_price: float | None = None,
        allow_market: bool = False,
    ) -> dict[str, Any]:
        return {"ok": False, "symbol": symbol.upper(), "reason": "adapter_disabled"}

    def fills(self, since: str | None = None) -> list[dict[str, Any]]:
        return []
