from __future__ import annotations

from tradeo.modules.lab_foxhunter.paper_probe import (
    LabPaperProbeBatchRequest,
    LabPaperProbeEnvironment,
    build_lab_gap_probe_manifests,
    prepare_lab_paper_probe_batch,
)


def _safe_environment(**overrides: object) -> LabPaperProbeEnvironment:
    values = {
        "explicit_paper_probe_mode": True,
        "director_approved": True,
        "ibkr_readonly": True,
        "laboratory_auto_submit_paper_orders": False,
        "foxhunter_auto_submit_live_orders": False,
        "live_trading_enabled": False,
        "live_armed": False,
        "kill_switch_available": True,
        "risk_limits_available": True,
        "broker_submit_enabled": False,
        "cron_trading_enabled": False,
        "order_preview_enabled": False,
        "signal_generation_enabled": False,
    }
    values.update(overrides)
    return LabPaperProbeEnvironment(**values)


def _request(probes: tuple[dict, ...] | None = None) -> LabPaperProbeBatchRequest:
    return LabPaperProbeBatchRequest(
        batch_id="LAB-PAPER-PROBE-002",
        probes=probes or build_lab_gap_probe_manifests(),
    )


def test_lab_paper_probe_002_prepares_only_two_gap_probes() -> None:
    report = prepare_lab_paper_probe_batch(_request(), _safe_environment())

    assert report["ready"] is True
    assert report["probe_ids"] == ["LAB-GAP-REV-001", "LAB-GAP-REV-002"]
    assert report["max_batch_probes"] == 2
    assert report["paper_only"] is True


def test_lab_paper_probe_002_requires_explicit_mode() -> None:
    report = prepare_lab_paper_probe_batch(
        _request(),
        _safe_environment(explicit_paper_probe_mode=False),
    )

    assert report["ready"] is False
    assert "explicit_paper_probe_mode_required" in report["blockers"]


def test_lab_paper_probe_002_requires_director_approval() -> None:
    report = prepare_lab_paper_probe_batch(
        _request(),
        _safe_environment(director_approved=False),
    )

    assert report["ready"] is False
    assert "director_approval_required" in report["blockers"]


def test_lab_paper_probe_002_blocks_live_and_global_auto_submit() -> None:
    report = prepare_lab_paper_probe_batch(
        _request(),
        _safe_environment(
            live_armed=True,
            live_trading_enabled=True,
            laboratory_auto_submit_paper_orders=True,
            foxhunter_auto_submit_live_orders=True,
        ),
    )

    assert report["ready"] is False
    assert "live_armed" in report["blockers"]
    assert "live_trading_enabled" in report["blockers"]
    assert "global_lab_auto_submit_must_remain_disabled" in report["blockers"]
    assert "foxhunter_live_auto_submit_must_be_disabled" in report["blockers"]


def test_lab_paper_probe_002_blocks_outputs_that_look_operational() -> None:
    report = prepare_lab_paper_probe_batch(
        _request(),
        _safe_environment(
            broker_submit_enabled=True,
            order_preview_enabled=True,
            signal_generation_enabled=True,
            cron_trading_enabled=True,
        ),
    )

    assert report["ready"] is False
    assert "broker_submit_not_enabled_by_batch_preparation" in report["blockers"]
    assert "order_preview_enabled" in report["blockers"]
    assert "signal_generation_enabled" in report["blockers"]
    assert "cron_trading_enabled" in report["blockers"]


def test_lab_paper_probe_002_never_reports_orders_or_promotions() -> None:
    report = prepare_lab_paper_probe_batch(_request(), _safe_environment())

    assert report["paper_orders_sent"] is False
    assert report["live_orders_sent"] is False
    assert report["order_previews_generated"] is False
    assert report["signals_generated"] is False
    assert report["foxhunter_candidates_created"] == 0
    assert report["live_candidates_created"] == 0
    assert report["foxhunter_promotion_allowed"] is False
    assert report["live_promotion_allowed"] is False


def test_lab_paper_probe_002_blocks_more_than_two_probes() -> None:
    probes = build_lab_gap_probe_manifests()
    report = prepare_lab_paper_probe_batch(_request(probes + (probes[0],)), _safe_environment())

    assert report["ready"] is False
    assert "max_two_probes_per_batch" in report["blockers"]
    assert "duplicate_probe_id" in report["blockers"]


def test_lab_paper_probe_002_blocks_non_gap_daily_family() -> None:
    probe = dict(build_lab_gap_probe_manifests()[0])
    probe["probe_id"] = "LAB-DSS-PB-001"
    probe["strategy_source_id"] = "DSS-PB-001"

    report = prepare_lab_paper_probe_batch(_request((probe,)), _safe_environment())

    assert report["ready"] is False
    assert "probe_0_not_in_initial_allowlist" in report["blockers"]
    assert "probe_0_source_not_allowed" in report["blockers"]
    assert "probe_0_forbidden_daily_family" in report["blockers"]
