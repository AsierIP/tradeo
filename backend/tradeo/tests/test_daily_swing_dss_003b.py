from __future__ import annotations

from pathlib import Path
import socket
import sys

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from diagnose_ibkr_connectivity import classify_port, diagnose_endpoint  # noqa: E402
from probe_ibkr_historical_readonly import validate_readonly_probe_settings  # noqa: E402


class _Settings:
    def __init__(self, *, ibkr_readonly: bool = True, ibkr_port: int = 7497) -> None:
        self.ibkr_readonly = ibkr_readonly
        self.ibkr_port = ibkr_port


def test_ibkr_diagnosis_rejects_live_ports() -> None:
    assert classify_port(7496) == "LIVE_PORT_RISK"
    assert classify_port(4001) == "LIVE_PORT_RISK"
    result = diagnose_endpoint("127.0.0.1", 7496)
    assert result["decision"] == "LIVE_PORT_RISK"
    assert result["tcp_status"] == "BLOCKED_LIVE_PORT"


def test_ibkr_diagnosis_dns_fail(monkeypatch) -> None:
    def fail_getaddrinfo(*_args, **_kwargs):
        raise socket.gaierror("mock dns failure")

    monkeypatch.setattr(socket, "getaddrinfo", fail_getaddrinfo)
    result = diagnose_endpoint("missing.invalid", 7497)
    assert result["decision"] == "DNS_FAIL"
    assert result["tcp_status"] == "NOT_RUN"


def test_ibkr_diagnosis_tcp_refused(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 7497))],
    )

    class RefusedSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def settimeout(self, _timeout):
            return None

        def connect(self, _sockaddr):
            raise ConnectionRefusedError("mock refused")

    monkeypatch.setattr(socket, "socket", lambda *_args: RefusedSocket())
    result = diagnose_endpoint("127.0.0.1", 7497)
    assert result["decision"] == "TCP_REFUSED"


def test_ibkr_diagnosis_tcp_timeout(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", 7497))],
    )

    class TimeoutSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def settimeout(self, _timeout):
            return None

        def connect(self, _sockaddr):
            raise TimeoutError("mock timeout")

    monkeypatch.setattr(socket, "socket", lambda *_args: TimeoutSocket())
    result = diagnose_endpoint("127.0.0.1", 7497)
    assert result["decision"] == "TCP_TIMEOUT"


def test_ibkr_probe_requires_read_only() -> None:
    allowed, reason = validate_readonly_probe_settings(_Settings(ibkr_readonly=False, ibkr_port=7497))
    assert allowed is False
    assert reason == "read_only=false"


def test_smoke_cache_does_not_mark_global_data_gate_pass() -> None:
    assert classify_port(7497) == "TWS_PAPER"
    assert classify_port(4002) == "IB_GATEWAY_PAPER"
