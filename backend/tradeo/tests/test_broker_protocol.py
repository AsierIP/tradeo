from __future__ import annotations

from tradeo.services.broker_protocol import BrokerGatewayProtocol, DisabledIbAsyncBroker


def _uses_protocol(gateway: BrokerGatewayProtocol) -> dict:
    return gateway.account_summary()


def test_disabled_ib_async_adapter_satisfies_protocol_without_execution() -> None:
    gateway = DisabledIbAsyncBroker(enabled=False)

    assert _uses_protocol(gateway)["status"] == "disabled"
    assert gateway.positions() == []
    assert gateway.open_orders() == []
    assert gateway.cancel_order("1")["reason"] == "adapter_disabled"
    preview = gateway.preview_reduce_only_exit("soun", 10, "SELL", "test")
    assert preview.ok is False
    assert preview.symbol == "SOUN"
    assert gateway.submit_reduce_only_exit("soun", 10, "SELL", "test")["ok"] is False
    assert gateway.fills() == []
