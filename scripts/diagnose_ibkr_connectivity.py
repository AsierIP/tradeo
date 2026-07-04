#!/usr/bin/env python3
"""Diagnose IBKR DNS/TCP reachability without using IBKR APIs or orders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
from typing import Any

LIVE_PORTS = {4001, 7496}
PAPER_PORTS = {4002, 7497}
DEFAULT_TIMEOUT_SECONDS = 3.0


def classify_port(port: int) -> str:
    if port in LIVE_PORTS:
        return "LIVE_PORT_RISK"
    if port == 7497:
        return "TWS_PAPER"
    if port == 4002:
        return "IB_GATEWAY_PAPER"
    return "AMBIGUOUS_PORT"


def diagnose_endpoint(host: str, port: int, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    port_classification = classify_port(port)
    result: dict[str, Any] = {
        "host": host,
        "port": port,
        "port_classification": port_classification,
        "timeout_seconds": timeout_seconds,
        "dns_status": "NOT_RUN",
        "tcp_status": "NOT_RUN",
        "decision": "NOT_RUN",
        "resolved_addresses": [],
        "orders_used": False,
        "ibkr_api_used": False,
    }
    if port_classification == "LIVE_PORT_RISK":
        result.update(
            {
                "dns_status": "BLOCKED_LIVE_PORT",
                "tcp_status": "BLOCKED_LIVE_PORT",
                "decision": "LIVE_PORT_RISK",
                "error": "live IBKR ports 7496/4001 are blocked for this diagnostic",
            }
        )
        return result

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        result.update({"dns_status": "DNS_FAIL", "tcp_status": "NOT_RUN", "decision": "DNS_FAIL", "error": str(exc)})
        return result

    addresses = []
    for info in infos:
        sockaddr = info[4]
        address = sockaddr[0]
        if address not in addresses:
            addresses.append(address)
    result["resolved_addresses"] = addresses
    result["dns_status"] = "DNS_OK"

    last_error = ""
    for info in infos:
        family, socktype, proto, _, sockaddr = info
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(timeout_seconds)
                sock.connect(sockaddr)
            result.update({"tcp_status": "TCP_OK", "decision": "TCP_OK"})
            return result
        except ConnectionRefusedError as exc:
            last_error = str(exc)
            result.update({"tcp_status": "TCP_REFUSED", "decision": "TCP_REFUSED", "error": last_error})
        except TimeoutError as exc:
            last_error = str(exc)
            result.update({"tcp_status": "TCP_TIMEOUT", "decision": "TCP_TIMEOUT", "error": last_error})
        except OSError as exc:
            last_error = str(exc)
            result.update({"tcp_status": "TCP_ERROR", "decision": "TCP_ERROR", "error": last_error})

    if not result.get("error") and last_error:
        result["error"] = last_error
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="host.docker.internal")
    parser.add_argument("--port", type=int, default=7497)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = diagnose_endpoint(args.host, args.port, args.timeout)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if payload["decision"] in {"TCP_OK", "TCP_REFUSED", "TCP_TIMEOUT", "DNS_FAIL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
