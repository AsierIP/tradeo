from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from probe_ibkr_api_session_readonly import (  # noqa: E402
    classify_probe_result,
    validate_readonly_api_probe_settings,
)


class _Settings:
    def __init__(self, *, ibkr_readonly: bool = True, ibkr_port: int = 4002) -> None:
        self.ibkr_readonly = ibkr_readonly
        self.ibkr_port = ibkr_port


def test_api_session_probe_requires_read_only() -> None:
    allowed, reason = validate_readonly_api_probe_settings(_Settings(ibkr_readonly=False))
    assert allowed is False
    assert reason == "read_only=false"


def test_api_session_probe_blocks_live_ports() -> None:
    allowed, reason = validate_readonly_api_probe_settings(_Settings(ibkr_port=4001))
    assert allowed is False
    assert reason == "live_port_risk"


def test_api_session_probe_allows_gateway_paper() -> None:
    allowed, reason = validate_readonly_api_probe_settings(_Settings(ibkr_port=4002))
    assert allowed is True
    assert reason == "IB_GATEWAY_PAPER"


def test_dss_003e_3_decision_requires_handshake_and_historical_results() -> None:
    assert classify_probe_result([], []) == "API_HANDSHAKE_FAIL"
    assert classify_probe_result([{"connected": True, "status": "OK"}], []) == "HISTORICAL_CANARY_FAIL"
    assert (
        classify_probe_result(
            [{"connected": True, "status": "OK"}],
            [{"historical_data_ok": True}, {"historical_data_ok": False}],
        )
        == "HISTORICAL_CANARY_FAIL"
    )
    assert (
        classify_probe_result(
            [{"connected": True, "status": "OK"}],
            [{"historical_data_ok": True}, {"historical_data_ok": True}],
        )
        == "API_HISTORICAL_READY"
    )
