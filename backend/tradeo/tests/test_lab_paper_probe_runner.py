from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST = REPO_ROOT / "research/lab_foxhunter/probes/LAB-GAP-REV-001.json"
RUNNER_PATH = REPO_ROOT / "scripts/run_lab_paper_probe_batch.py"

spec = importlib.util.spec_from_file_location("run_lab_paper_probe_batch", RUNNER_PATH)
assert spec is not None
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)
evaluate_batch = runner.evaluate_batch


def _args(**overrides: object) -> argparse.Namespace:
    values = {
        "lab_paper_probe": True,
        "paper_only": True,
        "no_live": True,
        "max_orders_total": 2,
        "dry_run": True,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def _settings(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "trading_mode": "paper",
        "live_trading_enabled": False,
        "kill_switch_enabled": False,
        "laboratory_auto_submit_paper_orders": False,
        "ibkr_readonly": True,
        "ibkr_port": 7497,
    }
    values.update(overrides)
    return values


def _manifest(**overrides: object) -> dict[str, object]:
    values = json.loads(MANIFEST.read_text(encoding="utf-8"))
    values.update(overrides)
    return values


def test_readonly_blocks_paper_submit() -> None:
    result = evaluate_batch(args=_args(), manifests=[_manifest()], settings=_settings())

    assert result["decision"] == "LAB_PAPER_PROBE_BLOCKED_READONLY_WRITE_REQUIRED"
    assert "readonly_write_required_for_paper_submit" in result["blockers"]


def test_live_armed_blocks() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest()],
        settings=_settings(ibkr_readonly=False, live_trading_enabled=True),
    )

    assert result["decision"] == "LAB_PAPER_PROBE_BLOCKED_SAFETY"
    assert "live_armed_true" in result["blockers"]


def test_auto_submit_general_blocks() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest()],
        settings=_settings(ibkr_readonly=False, laboratory_auto_submit_paper_orders=True),
    )

    assert result["decision"] == "LAB_PAPER_PROBE_BLOCKED_SAFETY"
    assert "auto_submit_general_true" in result["blockers"]


def test_probe_disabled_blocks() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest(disabled_by_default=True)],
        settings=_settings(ibkr_readonly=False),
    )

    assert result["decision"] == "LAB_PAPER_PROBE_BLOCKED_SAFETY"
    assert "LAB-GAP-REV-001:probe_disabled" in result["blockers"]


def test_non_allowlisted_probe_blocks() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest(probe_id="LAB-OTHER")],
        settings=_settings(ibkr_readonly=False),
    )

    assert result["decision"] == "LAB_PAPER_PROBE_BLOCKED_SAFETY"
    assert "LAB-OTHER:non_allowlisted_probe" in result["blockers"]


def test_no_kill_switch_blocks() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest()],
        settings=_settings(ibkr_readonly=False, kill_switch_enabled=True),
    )

    assert result["decision"] == "LAB_PAPER_PROBE_BLOCKED_KILL_SWITCH"
    assert "kill_switch_not_ready" in result["blockers"]


def test_no_paper_account_blocks() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest()],
        settings=_settings(ibkr_readonly=False, trading_mode="live"),
    )

    assert result["decision"] == "LAB_PAPER_PROBE_BLOCKED_PAPER_ACCOUNT"
    assert "paper_account_not_verified" in result["blockers"]


def test_max_orders_total_over_two_blocks() -> None:
    result = evaluate_batch(
        args=_args(max_orders_total=3),
        manifests=[_manifest()],
        settings=_settings(ibkr_readonly=False),
    )

    assert result["decision"] == "LAB_PAPER_PROBE_BLOCKED_SAFETY"
    assert "max_orders_total_gt_2" in result["blockers"]


def test_candidate_flags_block() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest(foxhunter_candidate=True, live_candidate=True)],
        settings=_settings(ibkr_readonly=False),
    )

    assert "LAB-GAP-REV-001:foxhunter_candidate_must_be_false" in result["blockers"]
    assert "LAB-GAP-REV-001:live_candidate_must_be_false" in result["blockers"]


def test_runner_no_signal_preview_leak() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest(generate_signals=True, generate_previews=True)],
        settings=_settings(ibkr_readonly=False),
    )

    assert "LAB-GAP-REV-001:generate_signals_must_be_false" in result["blockers"]
    assert "LAB-GAP-REV-001:generate_previews_must_be_false" in result["blockers"]
    assert result["orders"] == []


def test_no_paper_only_blocks() -> None:
    result = evaluate_batch(
        args=_args(paper_only=False),
        manifests=[_manifest()],
        settings=_settings(ibkr_readonly=False),
    )

    assert "paper_only_flag_required" in result["blockers"]


def test_runner_allows_write_only_with_readonly_false_and_no_general_autosubmit() -> None:
    result = evaluate_batch(
        args=_args(),
        manifests=[_manifest(), _manifest(probe_id="LAB-GAP-REV-002")],
        settings=_settings(ibkr_readonly=False, laboratory_auto_submit_paper_orders=False),
    )

    assert result["decision"] == "LAB_PAPER_PROBE_NO_TRADE_NO_TRIGGER"
    assert result["orders"] == []
