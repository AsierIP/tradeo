from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    script_path = next(
        parent / "scripts" / "check_paper_readiness.py"
        for parent in Path(__file__).resolve().parents
        if (parent / "scripts" / "check_paper_readiness.py").exists()
    )
    spec = importlib.util.spec_from_file_location("check_paper_readiness", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_repo(root: Path, env_lines: list[str]) -> None:
    for rel in (
        "backend/tradeo/routers",
        "backend/tradeo/tasks",
        "backend/tradeo/services",
        "backend/tradeo/modules/shared",
        "backend/tradeo/modules/intraday",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir()
    (root / "docker-compose.yml").write_text("services:\n  worker:\n    command: tradeo.tasks.worker\n", encoding="utf-8")
    (root / ".env.example").write_text("\n".join(env_lines), encoding="utf-8")
    (root / "backend/tradeo/routers/ibkr.py").write_text("/preview\nsubmit-bracket\n", encoding="utf-8")
    (root / "backend/tradeo/tasks/worker.py").write_text("laboratory_entry_job\nfox_hunter_entry_job\n", encoding="utf-8")
    (root / "backend/tradeo/services/ibkr_broker.py").write_text("# fixture\n", encoding="utf-8")
    (root / "backend/tradeo/services/paper_broker.py").write_text("# fixture\n", encoding="utf-8")
    (root / "backend/tradeo/modules/shared/entry_scanner.py").write_text("# fixture\n", encoding="utf-8")
    (root / "backend/tradeo/modules/intraday/flat_service.py").write_text("# fixture\n", encoding="utf-8")


def safe_env() -> list[str]:
    return [
        "TRADEO_TRADING_MODE=paper",
        "TRADEO_LIVE_TRADING_ENABLED=false",
        "TRADEO_INTRADAY_PAPER_ENABLED=false",
        "TRADEO_INTRADAY_LIVE_ENABLED=false",
        "TRADEO_IBKR_READONLY=true",
        "TRADEO_KILL_SWITCH_ENABLED=false",
        "TRADEO_INTRADAY_MAX_TRADES_PER_DAY=2",
        "TRADEO_INTRADAY_DAILY_LOSS_LIMIT_PCT=0.005",
        "TRADEO_MAX_POSITION_VALUE_PCT=0.10",
        "TRADEO_IBKR_MAX_ORDER_VALUE_USD=500",
        "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false",
        "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS=false",
        "TRADEO_IBKR_ALLOW_MARKET_ORDERS=false",
        "TRADEO_RECONCILIATION_AUTO_REPAIR_PAPER_EXITS=false",
        "TRADEO_INTRADAY_EOD_EMERGENCY_MARKET_ALLOWED=false",
    ]


def patch_external(monkeypatch, module):
    monkeypatch.setattr(
        module,
        "git_summary",
        lambda repo_root: {
            "root": str(repo_root),
            "branch": "feature/paper-readiness-002",
            "commit_sha": "abc",
            "origin_main_sha": "abc",
            "dirty": False,
            "tracked_changes": [],
            "untracked_changes": [],
            "git_status_exit_code": 0,
        },
    )
    monkeypatch.setattr(module, "run_command", lambda *args, **kwargs: module.CommandResult(0, "", ""))


def test_readiness_goes_shadow_go_but_orders_no_go_without_candidate(tmp_path, monkeypatch):
    module = load_module()
    write_repo(tmp_path, safe_env())
    patch_external(monkeypatch, module)

    report = module.build_report(tmp_path)

    assert report["schema_version"] == "tradeo.paper_readiness_002.v1"
    assert report["decisions"]["PAPER_INFRA_READY"] == "GO"
    assert report["decisions"]["SHADOW_NO_ORDER_READY"] == "GO"
    assert report["decisions"]["PAPER_ORDER_READY"] == "NO_GO_NO_PAPER_CANDIDATE"
    assert report["shadow_no_order_rehearsal"]["reason_no_trade"] == "NO_TRADE_NO_PAPER_CANDIDATE"
    assert report["shadow_no_order_rehearsal"]["orders_submitted"] is False
    assert report["shadow_no_order_rehearsal"]["preview_generated"] is False


def test_auto_submit_blocks_infra_and_shadow(tmp_path, monkeypatch):
    module = load_module()
    env = safe_env()
    env[env.index("TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false")] = (
        "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true"
    )
    write_repo(tmp_path, env)
    patch_external(monkeypatch, module)

    report = module.build_report(tmp_path)

    assert report["decisions"]["PAPER_INFRA_READY"] == "NO_GO"
    assert report["decisions"]["SHADOW_NO_ORDER_READY"] == "NO_GO"
    assert "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=true" in report["safety"]["blockers"]


def test_missing_limits_block_infra(tmp_path, monkeypatch):
    module = load_module()
    env = safe_env()
    env[env.index("TRADEO_INTRADAY_MAX_TRADES_PER_DAY=2")] = "TRADEO_INTRADAY_MAX_TRADES_PER_DAY="
    write_repo(tmp_path, env)
    patch_external(monkeypatch, module)

    report = module.build_report(tmp_path)

    assert report["decisions"]["PAPER_INFRA_READY"] == "NO_GO"
    assert "max_trades_per_day_defined" in report["safety"]["gaps"]


def test_sensitive_env_values_are_redacted(tmp_path, monkeypatch):
    module = load_module()
    env = safe_env() + ["TRADEO_IBKR_ACCOUNT=ACCOUNT_REDACT_ME", "TRADEO_SECRET_KEY=abcd"]
    write_repo(tmp_path, env)
    patch_external(monkeypatch, module)

    report = module.build_report(tmp_path)

    assert report["env"]["redaction_ok"] is True
    assert "ACCOUNT_REDACT_ME" not in repr(report)
    assert "TRADEO_IBKR_ACCOUNT" in report["env"]["sensitive_keys_redacted"]


def test_paper_enabled_without_explicit_approval_blocks(tmp_path, monkeypatch):
    module = load_module()
    env = safe_env()
    env[env.index("TRADEO_INTRADAY_PAPER_ENABLED=false")] = "TRADEO_INTRADAY_PAPER_ENABLED=true"
    write_repo(tmp_path, env)
    patch_external(monkeypatch, module)

    report = module.build_report(tmp_path)

    assert report["decisions"]["PAPER_INFRA_READY"] == "NO_GO"
    assert "TRADEO_INTRADAY_PAPER_ENABLED=true without explicit approval" in report["safety"]["blockers"]


def test_zero_max_trades_is_defined_fail_closed_limit(tmp_path, monkeypatch):
    module = load_module()
    env = safe_env()
    env[env.index("TRADEO_INTRADAY_MAX_TRADES_PER_DAY=2")] = "TRADEO_INTRADAY_MAX_TRADES_PER_DAY=0"
    write_repo(tmp_path, env)
    patch_external(monkeypatch, module)

    report = module.build_report(tmp_path)

    assert report["safety"]["checks"]["max_trades_per_day_defined"] is True
