from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts/run_lab_paper_probe_004.py"

spec = importlib.util.spec_from_file_location("run_lab_paper_probe_004", SCRIPT)
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
        "TRADEO_IBKR_ACCOUNT": "UFAKEOLD",
    }


def test_reconciliation_fixes_unique_du_managed_account(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("TRADEO_IBKR_ACCOUNT=UFAKEOLD\n", encoding="utf-8")
    env = _base_env()
    managed_probe = module._managed_probe_result(
        env,
        "PASS",
        blockers=[],
        accounts=["DUFAKEPAPER"],
        connected=True,
    )

    result = module._reconcile_account(
        env_path,
        env,
        {"status": "PASS"},
        managed_probe,
    )

    assert result["status"] == "FIXED"
    assert result["cause"] == "CONFIG_ACCOUNT_MISMATCH"
    assert result["changed_keys"] == ["TRADEO_IBKR_ACCOUNT"]
    assert module._parse_env(env_path)["TRADEO_IBKR_ACCOUNT"] == "DUFAKEPAPER"
    assert "DUFAKEPAPER" not in str(result)


def test_reconciliation_blocks_ambiguous_accounts(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("TRADEO_IBKR_ACCOUNT=UFAKEOLD\n", encoding="utf-8")
    env = _base_env()
    managed_probe = module._managed_probe_result(
        env,
        "BLOCKED",
        blockers=["managed_accounts_ambiguous"],
        accounts=["DUFAKEA", "DUFAKEB"],
        connected=True,
    )

    result = module._reconcile_account(env_path, env, {"status": "PASS"}, managed_probe)

    assert result["status"] == "BLOCKED"
    assert result["cause"] == "PAPER_ACCOUNT_AMBIGUOUS"
    assert module._parse_env(env_path)["TRADEO_IBKR_ACCOUNT"] == "UFAKEOLD"


def test_public_payload_removes_raw_managed_accounts() -> None:
    payload = module._managed_probe_result(
        _base_env(),
        "PASS",
        blockers=[],
        accounts=["DUFAKEPAPER"],
        connected=True,
    )

    public = module._public_payload(payload)

    assert "_managed_accounts_raw" not in public
    assert "DUFAKEPAPER" not in str(public)


def test_paper_account_gate_blocks_mismatch(monkeypatch) -> None:
    env = _base_env()
    monkeypatch.setattr(
        module,
        "_managed_account_probe",
        lambda _env: module._managed_probe_result(
            _env,
            "PASS",
            blockers=[],
            accounts=["DUFAKEPAPER"],
            connected=True,
        ),
    )

    result = module._paper_account_gate(env)

    assert result["status"] == "BLOCKED"
    assert "configured_account_not_managed" in result["blockers"]


def test_canary_blocked_unless_account_gate_pass() -> None:
    result = module._canary_submit_cancel(
        _base_env(),
        {"status": "BLOCKED"},
        skip_submit=False,
    )

    assert result["decision"] == "CANARY_BLOCKED_PAPER_ACCOUNT"
    assert result["orders"] == []
