from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/run_lab_paper_probe_005.py"
MANIFEST = REPO_ROOT / "research/lab_foxhunter/probes/LAB-GAP-REV-001.json"

spec = importlib.util.spec_from_file_location("run_lab_paper_probe_005", SCRIPT)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def _base_env() -> dict[str, str]:
    return {
        "TRADEO_TRADING_MODE": "paper",
        "TRADEO_LIVE_TRADING_ENABLED": "false",
        "TRADEO_INTRADAY_LIVE_ENABLED": "false",
        "TRADEO_IBKR_READONLY": "true",
        "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS": "false",
        "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS": "false",
        "TRADEO_IBKR_ALLOW_MARKET_ORDERS": "false",
        "TRADEO_IBKR_PORT": "14002",
        "TRADEO_IBKR_ACCOUNT": "DUFAKEPAPER",
    }


def test_market_session_gate_blocks_before_regular_session() -> None:
    result = module._market_session_gate(datetime(2026, 7, 6, 8, 50, tzinfo=timezone.utc))

    assert result["status"] == "BLOCKED"
    assert result["decision"] == "NO_TRADE_SPREAD_OR_MARKET_DATA"
    assert "outside_regular_us_session" in result["blockers"]


def test_market_session_gate_passes_regular_session() -> None:
    result = module._market_session_gate(datetime(2026, 7, 6, 15, 0, tzinfo=timezone.utc))

    assert result["status"] == "PASS"
    assert result["decision"] == "MARKET_SESSION_READY"


def test_live_risk_blocks_live_port() -> None:
    env = _base_env()
    env["TRADEO_IBKR_PORT"] = "7496"

    result = module._live_risk_checks(env, {"TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED": "true"})

    assert result["status"] == "BLOCKED"
    assert "ibkr_port_not_live" in result["blockers"]


def test_trigger_manifest_gate_blocks_candidate_promotion() -> None:
    manifest = module.json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["foxhunter_candidate"] = True
    batch_gate = {
        "blockers": ["LAB-GAP-REV-001:foxhunter_candidate_must_be_false"],
    }

    result = module._trigger_manifest_gate(manifests=[manifest], batch_gate=batch_gate)

    assert result["status"] == "BLOCKED"
    assert result["no_candidate_promotion"] is False


def test_execution_blocks_market_when_gates_pass() -> None:
    result = module._execution_result(
        safety_account_gate={"status": "PASS", "blockers": []},
        trigger_manifest_gate={"status": "PASS", "blockers": []},
        batch_gate={"decision": "LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER", "blockers": []},
        market_gate={"status": "BLOCKED", "blockers": ["outside_regular_us_session"]},
    )

    assert result["decision"] == module.DECISION_BLOCKED_MARKET
    assert result["paper_orders_executed"] == 0
