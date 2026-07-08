from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/run_lab_paper_probe_003.py"

spec = importlib.util.spec_from_file_location("run_lab_paper_probe_003", SCRIPT)
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
        "TRADEO_IBKR_PORT": "7497",
    }


def test_env_overlay_gate_writes_only_allowed_keys(tmp_path: Path) -> None:
    overlay = tmp_path / "overlay.env"

    result = module._build_env_overlay_gate(base_env=_base_env(), overlay_path=overlay)

    assert result["status"] == "PASS"
    assert set(result["overlay_keys"]) == module.ALLOWED_OVERLAY_KEYS
    assert module._parse_env(overlay)["TRADEO_IBKR_READONLY"] == "false"


def test_env_overlay_gate_blocks_unsafe_base(tmp_path: Path) -> None:
    base = _base_env()
    base["TRADEO_LIVE_TRADING_ENABLED"] = "true"

    result = module._build_env_overlay_gate(base_env=base, overlay_path=tmp_path / "overlay.env")

    assert result["status"] == "BLOCKED"
    assert "base_live_trading_disabled" in result["blockers"]


def test_paper_account_gate_blocks_live_port() -> None:
    env = _base_env()
    env.update({"TRADEO_IBKR_READONLY": "false", "TRADEO_LAB_PAPER_PROBE_WRITE_ENABLED": "true", "TRADEO_IBKR_PORT": "7496"})

    result = module._paper_account_gate(env)

    assert result["status"] == "BLOCKED"
    assert "live_port_configured" in result["blockers"]


def test_canary_skips_without_paper_account_pass() -> None:
    result = module._canary_submit_cancel(
        _base_env(),
        {"status": "BLOCKED"},
        skip_submit=False,
    )

    assert result["decision"] == "CANARY_BLOCKED_PAPER_ACCOUNT"
    assert result["orders"] == []


def test_decision_report_redacts_and_blocks_promotion() -> None:
    report = {
        "generated_at": "2026-07-06T08:00:00+00:00",
        "task_id": module.TASK_ID,
        "decision": "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT",
        "mode": "LAB_PAPER_PROBE_ONLY",
        "path_used": "/tmp/repo",
        "base_env_path": "/home/vboxuser/tradeo/.env",
        "overlay_path": "/tmp/overlay.env",
        "overlay_tracked": False,
        "overlay_removed_after_run": True,
        "paper_orders_executed": 0,
        "live_orders_executed": 0,
        "foxhunter_promotion": False,
        "live_candidate_created": False,
        "paper_candidate_classic_created": False,
        "signals_generated": False,
        "previews_generated": False,
        "env_overlay_gate": {"status": "PASS"},
        "paper_account_gate": {"status": "BLOCKED"},
        "canary": {"decision": "CANARY_BLOCKED_PAPER_ACCOUNT"},
        "runner": {"decision": "LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER"},
        "no_trade_reason": "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT",
        "blockers": ["paper_account:ibkr_paper_connection_failed"],
    }

    decision = module._decision_report(report)

    assert decision["redacted"] is True
    assert decision["paper_orders_executed"] == 0
    assert decision["live_orders_executed"] == 0
    assert decision["foxhunter_promotion"] is False
