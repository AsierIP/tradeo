from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def load_preflight_module():
    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "check_tradeo_operability.py"
    spec = importlib.util.spec_from_file_location("check_tradeo_operability", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_minimal_repo(root: Path, env_lines: list[str] | None = None) -> None:
    for relative in ("backend", "frontend", "scripts"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir()
    (root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (root / "backend" / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (root / "frontend" / "Dockerfile").write_text("FROM node:22-alpine\n", encoding="utf-8")
    for script in (
        "run_intraday_research_wave.py",
        "check_intraday_research_readiness.py",
        "plan_intraday_research_next.py",
        "analyze_intraday_research_forensics.py",
    ):
        (root / "scripts" / script).write_text("# fixture\n", encoding="utf-8")
    (root / ".env.example").write_text(
        "\n".join(
            env_lines
            or [
                "TRADEO_TRADING_MODE=paper",
                "TRADEO_LIVE_TRADING_ENABLED=false",
                "TRADEO_INTRADAY_PAPER_ENABLED=false",
                "TRADEO_INTRADAY_LIVE_ENABLED=false",
                "TRADEO_IBKR_READONLY=true",
                "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
                "TRADEO_KILL_SWITCH_ENABLED=true",
                "TRADEO_SECRET_KEY=do-not-print",
                "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS=false",
                "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS=false",
                "TRADEO_IBKR_ALLOW_MARKET_ORDERS=false",
                "TRADEO_RECONCILIATION_AUTO_REPAIR_PAPER_EXITS=false",
                "TRADEO_INTRADAY_EOD_EMERGENCY_MARKET_ALLOWED=false",
                "TRADEO_ALLOW_OPTIONS=false",
                "TRADEO_ALLOW_MARGIN=false",
            ]
        ),
        encoding="utf-8",
    )


def patch_external_checks(monkeypatch, module):
    monkeypatch.setattr(
        module,
        "git_repo_summary",
        lambda repo_root: {
            "root": str(repo_root),
            "branch": "main",
            "commit_sha": "abc123",
            "dirty": False,
            "tracked_changes": [],
            "untracked_changes": [],
            "git_status_exit_code": 0,
        },
    )
    monkeypatch.setattr(
        module,
        "docker_compose_check",
        lambda repo_root: {"config_ok": True, "exit_code": 0, "error": ""},
    )


def build_report(tmp_path, monkeypatch, env_lines: list[str] | None = None, **kwargs):
    module = load_preflight_module()
    write_minimal_repo(tmp_path, env_lines=env_lines)
    patch_external_checks(monkeypatch, module)
    return module, module.build_report(tmp_path, **kwargs)


def test_safe_env_is_operable_read_only(tmp_path, monkeypatch):
    _module, report = build_report(tmp_path, monkeypatch)

    assert report["schema_version"] == "tradeo.operability_preflight.v1"
    assert report["status"] == "OPERABLE_READ_ONLY"
    assert report["repo"]["branch"] == "main"
    assert report["safety"]["live_allowed"] is False
    assert report["safety"]["paper_allowed"] is False
    assert report["safety"]["orders_allowed"] is False
    assert report["safety"]["ibkr_readonly"] is True
    assert report["safety"]["kill_switch_enabled"] is True
    assert report["safety"]["execution_automation_flags_all_false"] is True


def test_live_trading_mode_blocks(tmp_path, monkeypatch):
    _module, report = build_report(
        tmp_path,
        monkeypatch,
        env_lines=[
            "TRADEO_TRADING_MODE=live",
            "TRADEO_LIVE_TRADING_ENABLED=false",
            "TRADEO_INTRADAY_PAPER_ENABLED=false",
            "TRADEO_INTRADAY_LIVE_ENABLED=false",
            "TRADEO_IBKR_READONLY=true",
            "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
        ],
    )

    assert report["status"] == "BLOCKED"
    assert "TRADEO_TRADING_MODE=live" in report["decision_reasons"]


def test_live_enabled_blocks(tmp_path, monkeypatch):
    _module, report = build_report(
        tmp_path,
        monkeypatch,
        env_lines=[
            "TRADEO_TRADING_MODE=paper",
            "TRADEO_LIVE_TRADING_ENABLED=true",
            "TRADEO_INTRADAY_PAPER_ENABLED=false",
            "TRADEO_INTRADAY_LIVE_ENABLED=false",
            "TRADEO_IBKR_READONLY=true",
            "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
        ],
    )

    assert report["status"] == "BLOCKED"
    assert "TRADEO_LIVE_TRADING_ENABLED=true" in report["decision_reasons"]


def test_intraday_live_enabled_blocks(tmp_path, monkeypatch):
    _module, report = build_report(
        tmp_path,
        monkeypatch,
        env_lines=[
            "TRADEO_TRADING_MODE=paper",
            "TRADEO_LIVE_TRADING_ENABLED=false",
            "TRADEO_INTRADAY_PAPER_ENABLED=false",
            "TRADEO_INTRADAY_LIVE_ENABLED=true",
            "TRADEO_IBKR_READONLY=true",
            "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
        ],
    )

    assert report["status"] == "BLOCKED"
    assert "TRADEO_INTRADAY_LIVE_ENABLED=true" in report["decision_reasons"]


def test_intraday_paper_enabled_blocks_without_authorization(tmp_path, monkeypatch):
    _module, report = build_report(
        tmp_path,
        monkeypatch,
        env_lines=[
            "TRADEO_TRADING_MODE=paper",
            "TRADEO_LIVE_TRADING_ENABLED=false",
            "TRADEO_INTRADAY_PAPER_ENABLED=true",
            "TRADEO_INTRADAY_LIVE_ENABLED=false",
            "TRADEO_IBKR_READONLY=true",
            "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
        ],
    )

    assert report["status"] == "BLOCKED"
    assert "TRADEO_INTRADAY_PAPER_ENABLED=true without --allow-paper-enabled" in report["decision_reasons"]


def test_intraday_paper_enabled_can_be_authorized(tmp_path, monkeypatch):
    _module, report = build_report(
        tmp_path,
        monkeypatch,
        env_lines=[
            "TRADEO_TRADING_MODE=paper",
            "TRADEO_LIVE_TRADING_ENABLED=false",
            "TRADEO_INTRADAY_PAPER_ENABLED=true",
            "TRADEO_INTRADAY_LIVE_ENABLED=false",
            "TRADEO_IBKR_READONLY=true",
            "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
        ],
        allow_paper_enabled=True,
    )

    assert report["status"] == "OPERABLE_READ_ONLY"
    assert report["safety"]["paper_allowed"] is True


def test_readonly_false_blocks(tmp_path, monkeypatch):
    _module, report = build_report(
        tmp_path,
        monkeypatch,
        env_lines=[
            "TRADEO_TRADING_MODE=paper",
            "TRADEO_LIVE_TRADING_ENABLED=false",
            "TRADEO_INTRADAY_PAPER_ENABLED=false",
            "TRADEO_INTRADAY_LIVE_ENABLED=false",
            "TRADEO_IBKR_READONLY=false",
            "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
        ],
    )

    assert report["status"] == "BLOCKED"
    assert "TRADEO_IBKR_READONLY is not true" in report["decision_reasons"]


def test_synthetic_market_data_blocks(tmp_path, monkeypatch):
    _module, report = build_report(
        tmp_path,
        monkeypatch,
        env_lines=[
            "TRADEO_TRADING_MODE=paper",
            "TRADEO_LIVE_TRADING_ENABLED=false",
            "TRADEO_INTRADAY_PAPER_ENABLED=false",
            "TRADEO_INTRADAY_LIVE_ENABLED=false",
            "TRADEO_IBKR_READONLY=true",
            "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=true",
        ],
    )

    assert report["status"] == "BLOCKED"
    assert "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=true" in report["decision_reasons"]


@pytest.mark.parametrize(
    "flag_name",
    [
        "TRADEO_LABORATORY_AUTO_SUBMIT_PAPER_ORDERS",
        "TRADEO_FOX_HUNTER_AUTO_SUBMIT_LIVE_ORDERS",
        "TRADEO_IBKR_ALLOW_MARKET_ORDERS",
        "TRADEO_RECONCILIATION_AUTO_REPAIR_PAPER_EXITS",
        "TRADEO_INTRADAY_EOD_EMERGENCY_MARKET_ALLOWED",
        "TRADEO_ALLOW_OPTIONS",
        "TRADEO_ALLOW_MARGIN",
    ],
)
def test_execution_automation_flags_block_when_true(tmp_path, monkeypatch, flag_name):
    env_lines = [
        "TRADEO_TRADING_MODE=paper",
        "TRADEO_LIVE_TRADING_ENABLED=false",
        "TRADEO_INTRADAY_PAPER_ENABLED=false",
        "TRADEO_INTRADAY_LIVE_ENABLED=false",
        "TRADEO_IBKR_READONLY=true",
        "TRADEO_ALLOW_SYNTHETIC_MARKET_DATA=false",
    ]
    env_lines.extend(f"{flag}=false" for flag in load_preflight_module().AUTOMATION_BLOCK_FLAGS)
    env_lines.append(f"{flag_name}=true")

    _module, report = build_report(tmp_path, monkeypatch, env_lines=env_lines)

    assert report["status"] == "BLOCKED"
    assert f"{flag_name}=true" in report["decision_reasons"]
    assert report["safety"]["execution_automation_flags_all_false"] is False


def test_secrets_are_redacted(tmp_path, monkeypatch):
    module, report = build_report(tmp_path, monkeypatch)
    rendered = module.render_markdown(report)
    serialized = module.json.dumps(report)

    assert "do-not-print" not in rendered
    assert "do-not-print" not in serialized
    assert "TRADEO_SECRET_KEY" in report["env"]["sensitive_keys_redacted"]


def test_missing_artifacts_do_not_break(tmp_path, monkeypatch):
    _module, report = build_report(tmp_path, monkeypatch)

    assert report["artifacts"]["latest_readiness_manifest"] is None
    assert report["artifacts"]["latest_wave_manifest"] is None
    assert report["status"] == "OPERABLE_READ_ONLY"


def test_missing_critical_file_is_not_ready(tmp_path, monkeypatch):
    module, report = build_report(tmp_path, monkeypatch)
    (tmp_path / "scripts" / "plan_intraday_research_next.py").unlink()

    report = module.build_report(tmp_path)

    assert report["status"] == "NOT_READY"
    assert any("missing critical files" in reason for reason in report["decision_reasons"])
