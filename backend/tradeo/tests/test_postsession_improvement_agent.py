from __future__ import annotations

from datetime import datetime, timezone
import json

from tradeo.modules.postsession.improvement_agent import PostSessionImprovementAgent, classify_finding, PostSessionFinding


def _agent(tmp_path):
    return PostSessionImprovementAgent(
        repo_root=tmp_path,
        runtime_root=tmp_path / "artifacts/runtime/postsession",
        research_root=tmp_path / "research/postsession",
        input_roots=[tmp_path / "artifacts/runtime/session"],
        now=datetime(2026, 7, 7, 21, 0, tzinfo=timezone.utc),
    )


def _finding(**overrides):
    base = {
        "finding_id": "f1",
        "title": "Low impact noise",
        "evidence": "single low-impact observation",
        "severity": 1,
        "recurrence_count": 1,
        "impact_area": "observability",
        "confidence": 0.5,
        "estimated_change_risk": 1,
        "estimated_benefit": 1,
        "component": "reporting",
        "touched_areas": ["observability"],
        "tests_available": True,
        "change_size": "small",
    }
    base.update(overrides)
    return base


def test_single_low_impact_finding_no_change(tmp_path) -> None:
    result = _agent(tmp_path).run(
        session_date=datetime(2026, 7, 7, tzinfo=timezone.utc).date(),
        findings=[_finding()],
        require_session_runtime=False,
    )

    assert result["final_decision"] == "POSTSESSION_NO_CHANGE_REQUIRED"
    assert result["counts"]["no_change"] == 1


def test_repeated_safety_finding_requires_review(tmp_path) -> None:
    result = _agent(tmp_path).run(
        session_date=datetime(2026, 7, 7, tzinfo=timezone.utc).date(),
        findings=[
            _finding(
                finding_id="safety_logging_gap",
                severity=3,
                recurrence_count=3,
                impact_area="safety",
                confidence=0.8,
                estimated_change_risk=3,
                estimated_benefit=4,
            )
        ],
        require_session_runtime=False,
    )

    assert result["final_decision"] == "POSTSESSION_PROPOSALS_READY_FOR_DIRECTOR"
    assert result["counts"]["director_review_required"] == 1


def test_safe_doc_or_test_fix_auto_fix_allowed(tmp_path) -> None:
    result = _agent(tmp_path).run(
        session_date=datetime(2026, 7, 7, tzinfo=timezone.utc).date(),
        findings=[
            _finding(
                finding_id="missing_report_test",
                severity=3,
                confidence=0.9,
                estimated_change_risk=1,
                estimated_benefit=4,
                impact_area="docs",
                component="postsession_docs",
            )
        ],
        require_session_runtime=False,
    )

    assert result["final_decision"] == "POSTSESSION_AUTO_FIXES_APPLIED"
    assert result["counts"]["auto_fixes_applied"] == 1


def test_trigger_logic_change_director_review() -> None:
    classification, reasons = classify_finding(
        PostSessionFinding.from_mapping(
            _finding(touched_areas=["trigger_logic"], severity=5, confidence=1.0),
            source="test",
        )
    )

    assert classification == "DIRECTOR_REVIEW_REQUIRED"
    assert "sensitive_area_requires_director" in reasons


def test_submit_path_change_director_or_blocker() -> None:
    classification, _ = classify_finding(
        PostSessionFinding.from_mapping(
            _finding(touched_areas=["submit"], severity=4, confidence=1.0),
            source="test",
        )
    )

    assert classification in {"DIRECTOR_REVIEW_REQUIRED", "BLOCKER_STOP_NEXT_SESSION"}


def test_raw_account_leak_blocks_next_session(tmp_path) -> None:
    result = _agent(tmp_path).run(
        session_date=datetime(2026, 7, 7, tzinfo=timezone.utc).date(),
        findings=[
            _finding(
                finding_id="raw_account_id_leak",
                title="Raw account id leak",
                severity=5,
                confidence=1.0,
                estimated_change_risk=1,
                estimated_benefit=5,
                metadata={"kind": "raw_account_id_leak"},
            )
        ],
        require_session_runtime=False,
    )

    assert result["final_decision"] == "POSTSESSION_BLOCK_NEXT_SESSION"
    assert (tmp_path / "artifacts/runtime/postsession/2026-07-07/BLOCK_NEXT_SESSION.json").exists()


def test_reconciliation_error_blocks_next_session(tmp_path) -> None:
    result = _agent(tmp_path).run(
        session_date=datetime(2026, 7, 7, tzinfo=timezone.utc).date(),
        findings=[_finding(finding_id="reconciliation_error", metadata={"kind": "reconciliation_error"})],
        require_session_runtime=False,
    )

    assert result["final_decision"] == "POSTSESSION_BLOCK_NEXT_SESSION"


def test_no_data_inconclusive_when_missing_runtime(tmp_path) -> None:
    result = _agent(tmp_path).run(
        session_date=datetime(2026, 7, 7, tzinfo=timezone.utc).date(),
        require_session_runtime=True,
    )

    assert result["final_decision"] == "POSTSESSION_INCONCLUSIVE"
    assert result["reason"] == "session_runtime_missing"
    assert not (tmp_path / "artifacts/runtime/postsession/2026-07-07/postsession_final.json").exists()


def test_auto_fix_cap_max_three(tmp_path) -> None:
    findings = [
        _finding(
            finding_id=f"safe_{idx}",
            severity=3,
            confidence=1.0,
            estimated_change_risk=1,
            estimated_benefit=4,
            component=f"docs_{idx}",
        )
        for idx in range(5)
    ]

    result = _agent(tmp_path).run(
        session_date=datetime(2026, 7, 7, tzinfo=timezone.utc).date(),
        findings=findings,
        require_session_runtime=False,
    )

    assert result["counts"]["auto_fixes_applied"] == 3
    assert len(result["auto_fixes_deferred_by_cap"]) == 2


def test_cooldown_same_component_blocks_auto_fix(tmp_path) -> None:
    runtime = tmp_path / "artifacts/runtime/postsession"
    runtime.mkdir(parents=True)
    (runtime / "cooldowns.json").write_text(
        json.dumps({"components": {"docs": {"last_changed_date": "2026-07-07"}}}),
        encoding="utf-8",
    )

    result = _agent(tmp_path).run(
        session_date=datetime(2026, 7, 7, tzinfo=timezone.utc).date(),
        findings=[
            _finding(
                finding_id="safe_docs",
                severity=3,
                confidence=1.0,
                estimated_change_risk=1,
                estimated_benefit=4,
                component="docs",
            )
        ],
        require_session_runtime=False,
    )

    assert result["final_decision"] == "POSTSESSION_NO_CHANGE_REQUIRED"


def test_duplicate_daily_run_blocked(tmp_path) -> None:
    agent = _agent(tmp_path)
    session_date = datetime(2026, 7, 7, tzinfo=timezone.utc).date()
    first = agent.run(session_date=session_date, findings=[_finding()], require_session_runtime=False)
    second = agent.run(session_date=session_date, findings=[_finding()], require_session_runtime=False)

    assert first["final_decision"] == "POSTSESSION_NO_CHANGE_REQUIRED"
    assert second["final_decision"] == "POSTSESSION_INCONCLUSIVE"
    assert second["reason"] == "duplicate_daily_run_blocked"
